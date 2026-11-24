---
title: Odometer and due rule
summary: The odometer transitions, the units, the rule that decides when a job is due, the service history and the starter jobs, with their state machine tests.
implements:
  - custom_components/car_keeper/units.py
  - custom_components/car_keeper/readings.py
  - custom_components/car_keeper/schedule.py
  - custom_components/car_keeper/history.py
  - custom_components/car_keeper/templates.py
  - custom_components/car_keeper/odometer.py
related: [data-model, entities, frontend]
source_hash: 584fca633503
---

# Odometer and due rule

These are the rules of Car Keeper. Each is a pure function that takes plain values and the
date of today, so the unit tier and the mutation gate check it with no Home Assistant.

## Goals

- **G1. Distance or time, whichever comes first.** A job is due at the first of its limits.
- **G2. An odometer that does not lie.** A reading never goes down without an admin
  correction, and each reading says where it came from.
- **G3. Works with no sensor.** A typed odometer has every feature.
- **G4. One rule in 2 languages.** The due rule and the units have a TypeScript copy, and a
  golden corpus holds the 2 copies together.
- **G5. State machines are tested as state machines.** Each one has a Hypothesis model test.

## Non-goals

- The schedule of a car maker. The starter jobs are common intervals that the user edits.
- A reading for each trip. A sensor keeps at most 1 reading a day.

## Design

### Units

`units.convert` converts between km, miles and metres. The rounding is half up with the
same float operations as `units.ts`: a reading to 1 decimal, an interval to a whole unit, a
starter interval to 100. `units.group_digits` writes `15,000`.

### The odometer

The odometer of a car is `{source, entity_id, value, updated, offset, lower}`. Each
transition of `readings.py` returns the next odometer and the reading to store.

| Transition | Rule |
|---|---|
| `readings.typed` | A value below the last one fails with `odometer_decreased`. |
| `readings.from_entity` | Converts the sensor unit to the car unit and adds the offset. A value that is not a number changes nothing. 1 lower value is noise. A second lower value in a row asks for a repair issue. |
| `readings.corrected` | An admin sets any value and can set the offset for a new instrument cluster. |
| `readings.bound` | Changes the source. The value and the readings stay. |

`readings.add` keeps the readings in time order, with at most 1 sensor reading a day.
`OdometerFollower` (`odometer.py`) copies the state of each bound sensor into the store, and
shows the repair issue `odometer_decreased_<car id>`. A correction deletes it.

### The due rule

`schedule.evaluate` returns `status`, `first`, `distance_limit`, `distance_left`,
`date_limit`, `days_left` and `eta_days` for 1 item.

- The base is `last_done`, else `start`. The distance limit is the base reading plus
  `interval_distance`. The date limit is the base date plus `interval_months`.
- A date item is due at `due_date`. A service near or after it moves it to the next due
  date of `interval_months`. Without an interval, the job is done for good
  (`schedule.date_due`).
- A limit is `overdue` at or past it, `soon` inside the warning window, else `ok`. The
  warning window is the value of the item, else of the car (`projections.lead`).
- The rule divides the distance left by the daily distance to compare it with a date. The
  limit with fewer days is `first`. With no daily distance, the date limit is first.
- `schedule.daily_distance` is the average of the readings of the last 90 days, with a span
  of 7 days or more.
- `schedule.sort_key` orders the jobs of a car: the worst status, then the nearest limit.

### The service history

A service record can do many jobs. `history.last_done` is the latest service that did a
job: the latest date, then the highest reading, then the latest time of logging. An older
service goes in the history and does not move `last_done` back. `history.stock_moves`
gives the change of each part count between 2 versions of a service, so a delete gives the
parts back.

### Starter jobs

`templates.TEMPLATES` holds 14 common jobs with the fuel types that need them, a distance in
km and a number of months. Registration, insurance and inspection are date jobs. The
`templates` setting changes an interval or turns a job off. `templates.items_for` converts
the distance to the unit of the car and rounds it to 100.

### Tests

| State machine | Test | Invariants |
|---|---|---|
| Odometer | `tests/unit/test_odometer_stateful.py` | The value goes down only by a correction. It is the last reading. 1 sensor reading a day. The issue comes from the second lower value. |
| Job status | `tests/unit/test_status_stateful.py` | Limits, status and first match a model through drives, a job done, edits, jumps and unit changes. |
| Service visits | `tests/unit/test_history_stateful.py` | `last_done` is the latest service. The stock moves add up to the parts in use. |

`tests/fixtures/shared/registry.json` lists the shared rules. The Python tests write the
corpus, and `shared-corpus.test.js` replays it against `units.ts` and `schedule.ts`.

## Trade-offs

- **A repair issue after 2 lower values** over **a refusal of each lower value**: a cloud
  that reports an old value 1 time makes no noise, and a new instrument cluster is found.
- **2 copies of the due rule** over **a status only from the server**: the tab can show the
  limits of a reading that the user types. The corpus is the cost.

## One-way doors

- The starter job ids, which items keep in `template_id`.
- The repair issue id `odometer_decreased_<car id>`.
