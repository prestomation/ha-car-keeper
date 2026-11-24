---
title: Data model
summary: The storage document of Car Keeper, the store that is its only write path, and the version rule.
implements:
  - custom_components/car_keeper/models.py
  - custom_components/car_keeper/store.py
related: [architecture, services-events]
source_hash: 80ae38dce225
---

# Data model

Car Keeper keeps 1 JSON document, `.storage/car_keeper`, which only `CarStore` changes.

## Goals

- **G1. One write path.** Each change goes through 1 store method. That method checks the
  input, saves, and fires the events.
- **G2. Pure rules.** The rules take plain values and an explicit time.
- **G3. A load never fails.** A missing or damaged section loads as an empty section.

## Non-goals

- A file for each car. 1 save is 1 consistent state.
- A migration step for a new section.

## Design

### Document

| Section | Holds |
|---|---|
| `cars` | The cars, by id |
| `items` | The maintenance items, by id |
| `services` | The service records, by id |
| `documents` | The documents and their dates, by id |
| `readings` | The odometer readings of each car |
| `settings` | `unit`: the distance unit of a new car, `km` or `mi` |

`models.normalize_state` runs on each load. It adds each missing section, replaces a value
of the wrong type with the empty value, and sets a `unit` that is not known to `km`. So a
new section needs no migration step, and `_CarStorage` only calls it.

### The store

- `CarStore.load` reads the document, or starts with `models.empty_state`.
- A store method changes `state`, then `_commit` saves, adds 1 to `revision`, fires the
  events and tells each listener. A listener that fails is logged, and the next listener
  still runs.
- `CarStore.set_settings` writes only the keys that change. A call that changes no value
  fires no event.
- `store.now` and `store.today` are the only clocks. The pure core takes the time from
  its caller.

### Errors

The pure core raises `models.CarKeeperError(key, **placeholders)`. The key is in
`strings.json` `exceptions`, and `services.service_error` turns it into a localized
`ServiceValidationError`.

### Versions

`models.version_at_least` compares 2 versions such as `0.38.0b5`. A pre-release sorts
below its release. A version that it cannot read passes, so that another check decides.

## Trade-offs

- **1 document for all cars** over **a file for each car**: 1 save is 1 consistent state.
  The design size is 20 cars with 30 years of history.
- **Normalize on load** over **versioned migrations**: a new section needs no code. The
  cost is that a rename of a section needs a real migration.

## One-way doors

- The storage key `car_keeper`, the version `1.1` and the section names.
- The `settings` key `unit` and its values `km` and `mi`.
