---
title: Data model
summary: The records of Car Keeper, the odometer rules and the rule that decides when a job is due.
status: planned
implements:
  - custom_components/car_keeper/models.py
  - custom_components/car_keeper/store.py
  - custom_components/car_keeper/units.py
  - custom_components/car_keeper/schedule.py
  - custom_components/car_keeper/templates.py
  - custom_components/car_keeper/odometer.py
  - custom_components/car_keeper/files.py
related: [architecture, home-keeper-link, services-events]
---

# Data model

Car Keeper keeps 1 JSON document, `.storage/car_keeper`, which only `CarStore` changes. Files
(photos, receipts, documents) are in `.storage/car_keeper_files/`.

## Goals

- **G1. One write path.** Each change goes through 1 store method. That method checks the input,
  saves, and fires the events.
- **G2. An odometer that does not lie.** A reading never goes down without an admin correction,
  and each reading says where it came from.
- **G3. Pure rules.** The due and unit rules take plain values and an explicit time.
- **G4. One unit for one car.** Each number of a car is in the unit of that car.

## Non-goals

- A reading for each trip. The store keeps at most 1 reading a day from a sensor.

- More than 1 meter for a car, such as engine hours ([IDEAS.md](../../../IDEAS.md)).

## Design

### Document

| Section | Holds |
|---|---|
| `cars` | The cars, by id |
| `items` | The maintenance items, by id |
| `services` | The service records, by id |
| `readings` | The odometer readings of each car, in time order |
| `documents` | The documents and their dates, by id |
| `rules` | The live-reading rules of [home-keeper-link](home-keeper-link.md#rules) |
| `settings` | The default unit, the warning windows, the privacy switches and the default schedule |

### Car

| Field | Notes |
|---|---|
| `name`, `make`, `model`, `year`, `trim` | Text. `name` is required. |
| `fuel` | `petrol`, `diesel`, `hybrid`, `plug_in_hybrid`, `electric` or `other`. It filters the starter jobs. |
| `unit` | `km` or `mi`. |
| `vin`, `plate` | **Private.** Only an admin projection has them. |
| `photo` | A file id. The user uploads it. |
| `area_id` | A Home Assistant area. |
| `linked_device_id`, `linked_entry_ids` | The device and the config entries of the car integration, if there is one. |
| `odometer` | `source` (`manual` or `entity`), `entity_id`, `value`, `updated`, `offset`. |
| `lead_distance`, `lead_days` | The warning window. Empty means the setting. |
| `hk_asset_id` | The Home Keeper appliance. |

### Odometer

A reading is `{ts, value, source, by}`. `source` is `manual`, `entity`, `service` or `correction`.

- **Typed.** `set_odometer` accepts a value that is not below the last one. A lower value fails
  with `odometer_decreased`.
- **Bound.** `odometer.py` follows the entity. It reads the unit of the entity (`km`, `mi` or `m`)
  and converts to the unit of the car. It ignores a value that is not a number.
- **A lower value from a sensor.** 1 lower value is ignored. A second one, from a new report,
  makes a repair issue that asks an admin: a wrong sensor, or a new instrument cluster.
- **Correction.** `correct_odometer` is admin-only. It records a `correction` reading. For a new
  cluster it sets `offset`, which is added to each later sensor value.

- **Daily distance.** `schedule.daily_distance` is the average of the last 90 days of readings.

### Maintenance item

| Field | Notes |
|---|---|
| `car_id`, `name`, `template_id`, `notes`, `enabled` | |
| `kind` | `job` (an interval) or `date` (a fixed due date, such as a registration). |
| `interval_distance`, `interval_months` | At least 1 for a `job`. |
| `last_done` | `{date, reading}` of the latest service that did the job. |
| `due_date` | For `kind: date` only. |
| `lead_distance`, `lead_days` | Empty means the value of the car. |
| `parts` | A list of `{part_id, quantity}` from the appliance of the car. |
| `add_task`, `hk_task_id` | The Home Keeper task ([home-keeper-link](home-keeper-link.md)). |

### The due rule

`schedule.evaluate(item, odometer, daily_distance, today)` returns the limits and a status.

- The **distance limit** is `last_done.reading + interval_distance`. The **date limit** is
  `last_done.date + interval_months`, or `due_date`.
- A limit is `overdue` when it is passed, `soon` inside the warning window, else `ok`. The status
  of the item is the worst of its limits. The status of a car is the worst of its items.
- **First.** To compare a distance with a date, the rule divides the distance left by the daily
  distance. The limit with fewer days is `first`. With no daily distance, the date limit is first.
- An item with no `last_done` counts from the date the car was added and from the odometer at that
  time.

### Service record

A service is 1 visit to a shop, or 1 job at home. It can do many jobs.

| Field | Notes |
|---|---|
| `car_id`, `date`, `reading` | `reading` is optional and is in the unit of the car. |
| `items` | The ids of the jobs done. A service with no item is a plain log entry. |
| `shop`, `notes`, `who` | `who` is a person id. |
| `cost` | **Private.** 1 number for the visit, in the currency of Home Assistant. |
| `parts_used` | `{part_id, quantity}` for each part. |
| `files` | Receipt and photo file ids. **Private.** |
| `origin` | `car_keeper`, or `home_keeper` for a task that a user completed there. |

When a service is saved, `last_done` of each of its items becomes the latest service that did the
item. A service with an earlier date goes in the history and does not move `last_done` back. A
delete computes `last_done` again.

### Starter jobs

`templates.py` holds the built-in list: an id, a name key, the fuel types, a distance in km and a
number of months. The list has engine oil, tyre rotation, brake fluid, cabin filter, engine air
filter, wipers, 12 V battery test, coolant, spark plugs, tyre check, AdBlue, registration,
insurance and inspection. `apply_templates` copies the selected jobs into items and converts the
distance to the unit of the car, rounded to 100. The user can edit the list in
`settings.default_schedule`. The tab says that these are not the intervals of the maker.

### Document

`{car_id, kind, name, due_date, files, notes}`. `kind` is `registration`, `insurance`,
`inspection` or `other`. A document with a `due_date` makes a `date` item, so it comes due like a
job.

## Trade-offs

- **Values in the unit of the car** over **km in storage**: the user reads the numbers that they
  typed, with no rounding. The cost is 1 conversion pass when an admin changes the unit of a car.

## One-way doors

- The section names and the record fields, in storage and in the export.
- The values of `fuel`, `kind` and the reading `source`.
- The starter job ids, which stored items keep in `template_id`.
- The file directory `.storage/car_keeper_files/`.
