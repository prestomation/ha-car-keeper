---
title: Data model
summary: The storage document of Car Keeper, its records, the store that is its only write path, and the export and import.
implements:
  - custom_components/car_keeper/models.py
  - custom_components/car_keeper/store.py
  - custom_components/car_keeper/import_export.py
related: [architecture, odometer-schedule, services-events]
source_hash: a244c93e9b71
---

# Data model

Car Keeper keeps 1 JSON document, `.storage/car_keeper`, which only `CarStore` changes.

## Goals

- **G1. One write path.** Each change goes through 1 store method. That method checks the
  input, saves, and fires the events.
- **G2. Pure rules.** The builders and the import plan take plain values and an explicit time.
- **G3. A load never fails.** A missing or damaged section loads as an empty section.
- **G4. One unit for one car.** Each number of a car is in the unit of that car.
- **G5. A round trip keeps the data.** An import of an export gives the same document.

## Non-goals

- A file for each car, or a migration step for a new section.
- More than 1 meter for a car, such as engine hours ([IDEAS.md](../../IDEAS.md)).

## Design

### Document

| Section | Holds |
|---|---|
| `cars` | The cars, by id |
| `items` | The maintenance jobs, by id |
| `services` | The service records, by id |
| `readings` | The odometer readings of each car, in time order |
| `settings` | `unit` (of a new car) and `templates` (the starter job overrides) |

`models.normalize_state` runs on each load. It adds each missing section, and replaces a
value of the wrong type with the empty value.

### Records

| Record | Fields |
|---|---|
| Car | `name`, `make`, `model`, `year`, `trim`, `fuel`, `unit`, `vin`, `plate`, `area_id`, `notes`, `lead_distance`, `lead_days`, `odometer`, `photo`, `created`, `hk_asset_id` |
| Item | `car_id`, `name`, `kind` (`job` or `date`), `interval_distance`, `interval_months`, `due_date`, `lead_distance`, `lead_days`, `notes`, `enabled`, `add_task`, `template_id`, `start`, `last_done`, `hk_task_id`, `notified` |
| Service record | `car_id`, `date`, `reading`, `items`, `shop`, `notes`, `who`, `cost`, `parts_used`, `logged`, `origin`, `hk_completions` |
| Reading | `ts`, `value`, `source` (`manual`, `entity`, `service`, `correction`), `by` |

- `models.build_car`, `models.build_item` and `models.build_service` check the input of a
  service and make the record. The update builders return the record and the names of the
  fields that changed.
- A new car gets the warning window of its unit: 1,000 km or 600 miles, and 30 days.
- A new item counts from `start`: today and the odometer of today, or the last date and
  reading that the admin gives.
- `last_done` is not input. It follows from the history (`history.refresh`).
- `hk_asset_id`, `hk_task_id`, `notified` and `hk_completions` are bookkeeping of the syncs
  and of the due check.

### The store

- A store method changes `state`, then `_commit` saves, adds 1 to `revision`, fires the
  events and tells each listener. A failed listener is logged, and the next one still runs.
- An update that changes no field fires no event.
- `CarStore.log_service` with a reading above the odometer moves the odometer to it.
- `CarStore.update_car` with a new `unit` converts the odometer, the readings, the
  intervals, the warning distances and the service readings 1 time.
- `CarStore.delete_car` deletes the items, the service records and the readings of the car.
- `CarStore.check_due` stores in `notified` the last due point that fired an event, so each
  `item_due_soon` and `item_overdue` fires 1 time for each due point.
- `store.now` and `store.today` are the only clocks.

### Export and import

`import_export.export_document` returns `{format, version, data, skipped}`. `NOT_EXPORTED`
names each stored field that the export leaves out, with the reason: the Home Keeper ids,
the photo, `notified` and `last_done`, which the history gives again.

`import_export.plan_import` is an upsert. A car matches by id, then by VIN, then by name.
An item matches by id, then by its car and its name. It never deletes a record. A sensor
that the install does not have makes a typed odometer, with a warning. An error blocks the
whole import. `import_export.apply_plan` writes the plan and computes `last_done` again.

Hypothesis tests prove 3 fixed points: an import of an export into an empty document gives
the document, an import into the same document changes nothing, and an export of an import
of an export is the first export.

## Trade-offs

- **Values in the unit of the car** over **km in storage**: the user reads the numbers that
  they typed. The cost is 1 conversion pass when an admin changes the unit of a car.
- **`last_done` computed from the history** over **a field that the user sets**: a delete
  or an edit of a service record can never leave a wrong value.

## One-way doors

- The storage key `car_keeper`, the version `1.1`, the section names and the record fields.
- The values of `fuel`, `kind` and the reading `source`.
- The export `format` 1 and the keys of `data`.
