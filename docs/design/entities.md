---
title: Entities
summary: The device of each car, its sensors, its overdue binary sensor and its to-do list of the jobs that are due.
implements:
  - custom_components/car_keeper/entity.py
  - custom_components/car_keeper/sensor.py
  - custom_components/car_keeper/binary_sensor.py
  - custom_components/car_keeper/todo.py
related: [architecture, odometer-schedule, services-events]
source_hash: 920c496bf36e
---

# Entities

Each car has 1 device, `(car_keeper, <car id>)`, with 6 entities. The entities read the
store through the coordinator, so a change shows at once with no poll.

## Goals

- **G1. Home Keeper can read the odometer.** The odometer sensor has a stable attribute
  `reading` in the unit of the car.
- **G2. Every user sees what is due.** The status, the next limits and the to-do list show
  each value of the car.
- **G3. A car and its entities live together.** A new car adds its entities, and a deleted
  car removes its device and its entities.

## Non-goals

- An entity for each job. Home Keeper makes a due sensor, an overdue sensor and a button for
  each task.

## Design

| Entity | Key | State | Attributes |
|---|---|---|---|
| `sensor` | `odometer` | The reading, in the unit of the car | `reading`, `unit`, `source`, `updated` |
| `sensor` | `next_due_distance` | The distance to the nearest distance limit | `item_id`, `job`, `distance_limit`, `status` |
| `sensor` | `next_due_date` | The nearest date limit | `item_id`, `job`, `days_left`, `status` |
| `sensor` | `status` | `ok`, `soon` or `overdue` | `next_item_id`, `next_job`, `due_count`, `due_jobs`, `daily_distance` |
| `binary_sensor` | `overdue` | On when a job is overdue | `overdue_jobs` |
| `todo` | `jobs` | The count of the jobs that are due | |

- The unique id is `<car id>_<key>`, so a rename of a car keeps each entity.
- The odometer sensor has the device class `distance` and the state class
  `total_increasing`. A display unit that a user sets does not change `reading`.
- `entity.async_track_cars` adds the entities of a new car after a store change, renames
  the device of a renamed car, and removes the device of a deleted car.
  `entity.find_device` uses `async_get_device_by_identifier` where Home Assistant has it.
- A check of a to-do item logs a service for the job, at today and the odometer of now.
  The list refuses every other change with `todo_only_check`.

## Trade-offs

- **A device of its own** over **the device of the car integration**: it works for a car
  with no integration, and it does not change a device that another integration owns.

## One-way doors

- The unique ids `<car id>_<key>` and the translation keys.
- The attribute `reading` of the odometer sensor, which Home Keeper tasks read.
