---
title: Home Keeper link
summary: How Car Keeper checks Home Keeper, adds the Cars tab, and keeps an appliance for each car and a task for each job in Home Keeper.
implements:
  - custom_components/car_keeper/home_keeper.py
  - custom_components/car_keeper/task_plan.py
  - custom_components/car_keeper/hk_sync.py
related: [architecture, data-model, frontend]
source_hash: ece07678f63b
---

# Home Keeper link

Car Keeper owns the cars, the jobs and the service history. Home Keeper owns the
reminders: the to-do list, the calendar, the notifications, the parts stock and the
device page. Car Keeper uses only the Home Keeper services, its events and the Python
API of the panel tab.

## Goals

- **G1. Say why.** If Home Keeper is missing, not set up or too old, the config flow stops
  with that reason, and a running Car Keeper shows a repair issue with the same reason.
- **G2. Never block setup.** Car Keeper never raises `ConfigEntryNotReady` for Home Keeper.
- **G3. Follow Home Keeper.** When Home Keeper loads, reloads or goes away, the tab, the
  issue and the sync follow with no restart.
- **G4. 1 task for each job.** A job with `add_task` has at most 1 Home Keeper task.
- **G5. Both ways, no loops.** A service in Car Keeper completes the task. A completion
  in Home Keeper logs a service. A change never comes back as a loop.
- **G6. No change to Home Keeper.** The sync uses only what Home Keeper 0.35.0 has.

## Non-goals

- A Home Keeper version range. Each version from the minimum on is supported.
- Reminders of Car Keeper's own, and a copy of the parts stock.
- Rules on live readings, such as a tyre pressure ([IDEAS.md](../../IDEAS.md)).

## Design

### The check and the tab

`home_keeper.async_check` returns `home_keeper_missing`, `home_keeper_not_set_up`,
`home_keeper_too_old` or None. Too old is a version below
`const.HOME_KEEPER_MIN_VERSION` (`0.35.0`), or no `panel_tabs` module. 0.35.0 is the first
version with managed appliances, the panel tab API, the companion export and the
`parts` list of `set_task_consumable`.

`HomeKeeperLink` runs the check at setup, on each change of a Home Keeper config entry
and when the component loads. On a pass it registers the tab (id `cars`, element
`home-keeper-cars-tab`, host API 1) and calls `register_companion`. On a failure it
removes the tab and shows the repair issue of the reason. Each time Home Keeper becomes
available, it tells its listeners, and the sync is 1 of them.

### The plan

`task_plan.py` is pure. It compares the document with `list_assets` and `list_tasks`.

| Car Keeper | Home Keeper |
|---|---|
| A car with a device | 1 managed appliance with the name, the make, the model and the area. Never the VIN or the plate: `list_assets` is open to each user. |
| A job with a distance interval | A `sensor` task in `usage` mode on the odometer sensor of the car. `target` is the interval, `baseline` the reading of the base. A time interval is `also_every` with `combinator: any`. |
| A job with only a time interval | A `floating` task in months, with `last_completed` from the base. |
| A date job | A `one-off` task, due at the next due date. |
| The parts of a job | The part links of the task (`set_task_consumable`). |
| A job of a service | 1 completion with `origin: car_keeper`, the reading on a sensor task, and the cost on the first job of the service only. |

A Home Keeper record is Car Keeper's when `managed_by.integration` is `car_keeper`. An
appliance names its car in `managed_by.car_id`. A task names its job in
`source.car_keeper.item_id`. The steps are `adds`, `binds`, `updates`, `releases` for the
appliances, and `adds`, `binds`, `forgets`, `updates`, `meters`, `consumables`,
`completes`, `deletes` for the tasks.

### The sync

`HomeKeeperSync` (`hk_sync.py`) runs a pass when Home Keeper becomes available, after
each store change, and when a device or an entity of Car Keeper is created. A pass sends
the queue of the store (`sync.undo`, `sync.stock`), then plans and runs the steps, and
plans again until a plan is empty. 1 pass runs at a time. A change during a pass makes 1
more pass.

| What occurs | What the sync does |
|---|---|
| A service is deleted, or a job is taken off it | `delete_completion` of the queued completion. |
| The parts of a service change | `adjust_part_stock` of each queued move. |
| A completion in Home Keeper, with another origin | `log_service` with the date, the reading and the cost of the event, and origin `home_keeper`. |
| A completion is undone in Home Keeper | The job comes off its service. A service with no job left is deleted. |
| A task is deleted in Home Keeper | The job keeps its data, and `add_task` goes off. |
| A car is deleted, or Car Keeper is removed | The appliance is released (`managed_by: null`). The user keeps it with its stock. |

A refused queue entry is dropped, because a second try fails the same way. A failed pass
logs a warning and waits for the next change.

### Tests

`tests/unit/test_reconcile_stateful.py` is the state machine test of the plan. Its rules
change both sides: jobs, services, and a Home Keeper user who completes or deletes a
task. After each rule the sync runs against a fake to a fixed point. The invariants: it
settles in 3 rounds or less, each job that wants a task has exactly 1, and each job of
each service has its completion on the current task. The component tier runs the sync
against a fake Home Keeper. The Docker tier runs it against the real one.

## Trade-offs

- **A usage task on Car Keeper's own odometer sensor** over **a triggered task**: Home
  Keeper shows the distance left with no new code. A car with no sensor works, because
  the sensor shows the typed reading.
- **Few locked fields** over **a lock on each field**: Home Keeper drops a locked field
  from each update, also from the owner. So a task locks only `device_id` and an
  appliance only `name`, and a pass writes the other fields of the car again.
- **A pass that plans from both sides** over **1 call for each change**: a pass also
  repairs what was lost while Home Keeper was not loaded.

## One-way doors

- The tab id `cars`, the element `home-keeper-cars-tab` and the host API version 1.
- The repair issue ids, which match the abort reasons.
- `managed_by` with `integration`, `config_entry_id`, `deletion_protected`,
  `locked_fields` and `car_id`. The task source `car_keeper` with `car_id`, `item_id`
  and `device_id`.
- The completion origin `car_keeper`, and the service origin `home_keeper`.
