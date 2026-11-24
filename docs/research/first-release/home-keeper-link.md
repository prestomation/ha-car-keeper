---
title: Home Keeper link
summary: How Car Keeper checks Home Keeper, adds its tab, and keeps an appliance, tasks and parts in Home Keeper for each car.
status: planned
implements:
  - custom_components/car_keeper/home_keeper.py
  - custom_components/car_keeper/task_plan.py
  - custom_components/car_keeper/task_sync.py
  - custom_components/car_keeper/asset_sync.py
  - custom_components/car_keeper/rules.py
related: [architecture, data-model, services-events]
---

# Home Keeper link

Car Keeper owns the cars, the jobs and the service history. Home Keeper owns the reminders: the
to-do list, the calendar, the notifications, the parts stock and the device page. This doc says
how the 2 stay the same. The contract is the Home Keeper `docs/INTEGRATING.md`, sections 1 to 11.
Car Keeper uses only services and events, and the Python API for the tab.

## Goals

- **G1. Say why.** If Home Keeper is missing, not set up or too old, the config flow stops with
  that reason, and a running Car Keeper shows a repair issue with the same reason.
- **G2. Never block setup.** Car Keeper never raises `ConfigEntryNotReady` for Home Keeper.
- **G3. 1 task for each job.** A job with `add_task` has at most 1 Home Keeper task, bound by the
  item id in the task source.
- **G4. Both ways, no loops.** A service in Car Keeper completes the task. A completed task in
  Home Keeper makes a service. Each call sends the origin `car_keeper`, and the listeners ignore
  that origin.
- **G5. No change to Home Keeper.** The first release uses only what Home Keeper has.

## Non-goals

- Reminders of Car Keeper's own.
- A copy of the parts stock. The stock numbers live only in Home Keeper.
- A preset extension point in Home Keeper ([companion-presets](../companion-presets.md)).

## Design

### The check, the tab and the companion

`home_keeper.async_check` returns `home_keeper_missing`, `home_keeper_not_set_up`,
`home_keeper_too_old` or no reason, as the Library does. `HomeKeeperLink` runs it at setup, on
each change of the Home Keeper config entry and when the component loads. On a pass it:

- registers the tab with `panel_tabs.async_register_panel_tab`: `companion` `car_keeper`, `id`
  `cars`, `icon` `mdi:car-wrench`, `element` `home-keeper-cars-tab`, `host_api` 1, and a
  `module_url` under `/car_keeper_static` with a content hash;
- calls `register_companion` with the capability `import_export`, and again on each
  `home_keeper_register_companions` event;
- turns the syncs on.

On a failure it removes the tab, turns the syncs off and shows the repair issue.

`const.HOME_KEEPER_MIN_VERSION` is `0.38.0`, the version that this design was read against. An
older version can work: the lowest version that has each service below is not checked yet.

### A car is a managed appliance

`asset_sync` keeps 1 Home Keeper appliance for each car, with `add_asset`, `managed_by` and
`source: {"car_keeper": {"car_id": id}}`.

- Car Keeper makes a device `(car_keeper, <car id>)` for its entities. The appliance is on that
  device, so the Home Keeper task entities show on the same device page.
- The appliance gets the name, the make, the model and the area. It never gets the VIN or the
  plate: the Home Keeper `list_assets` service is open to every user.
- `locked_fields` are `name`, `manufacturer`, `model`, `area_id` and `parts`. Car Keeper writes
  the part list (name, part number, vendor, cost) with `update_managed_asset`. The user owns each
  stock number.
- When Car Keeper is removed, it calls `update_asset` with `managed_by: null`, so the user keeps
  the appliance and the stock.

### A job is a managed task

| Job | Home Keeper task |
|---|---|
| Has a distance interval | `recurrence_type: sensor`, mode `usage`. `entity_id` is the odometer sensor of the car. `target` is the interval. `baseline` is the reading of `last_done`. With a time interval too: `also_every` and `combinator: any`. |
| Time interval only | `recurrence_type: floating` with the interval in months, and `last_completed`. |
| A date (`kind: date`) | A one-off task with the due date. |

This is why a car with no sensor works: the odometer sensor of the car is an entity of Car Keeper,
and its value is the typed reading ([services-events](services-events.md#entities)). Home Keeper
sees a normal meter.

Each task has `device_id`, `source: {"car_keeper": {"car_id", "item_id", "device_id"}}` and
`managed_by` with the config entry id, `deletion_protected` and the locked fields `name`,
`recurrence_type` and `device_id`. `set_task_consumable` links the parts of the job, so a
completion takes them off the stock.

Home Keeper has no warning window for a usage task: the task arms at the limit. The `soon` status
is in Car Keeper, on its entities, its cards and its events.

### The planner and the sync

`task_plan.plan_reconcile` is pure. It takes the items, the services and the reply of
`list_tasks`, and returns steps: `adds`, `binds`, `updates` (a changed interval, name or
baseline), `completes`, `deletes` and `forgets`. `TaskSync` runs a pass at start, when Home Keeper
becomes available, and after each store change that changes an item or a service. A lock runs 1
pass at a time. Each call is guarded with `has_service` and is tried again on the next pass.

| What occurs | What the sync does |
|---|---|
| A service is saved in Car Keeper | `complete_task` for each job, with `completed_at`, `reading`, `origin`, and the cost on the first job only, so the Home Keeper spend total is right. |
| A user completes the task in Home Keeper | `home_keeper_task_completed` with no origin: Car Keeper adds a service with the date and the `reading` of the event. |
| A completion is undone in Home Keeper | `home_keeper_task_uncompleted`: Car Keeper removes the job from that service. |
| A service is deleted in Car Keeper | `delete_completion` with the stored completion time. |
| The odometer is corrected | `set_task_meter` moves the baseline of each usage task of the car. |
| The user deletes the task in Home Keeper | The item keeps its data and `add_task` goes off. |

A date job gets no `reading` in Home Keeper, because Home Keeper accepts a reading only on a
sensor task (Home Keeper issue 598). The reading stays on the Car Keeper service.

### Rules

`rules.py` runs the checks that a Home Keeper preset cannot do: a tyre pressure below the limit of
the car, and a distance to service below the warning window, in the unit of the car. A rule is 1
managed triggered task: `trigger_task` when the condition holds for 1 hour, and `complete_task`
with the origin when it clears. The Cars tab offers a rule, or a Home Keeper catalog preset for
the device of the car, in 1 review dialog.

## Trade-offs

- **A usage task on Car Keeper's own odometer sensor** over **a triggered task that Car Keeper
  arms**: Home Keeper shows the interval and the distance left with no new code, and a completion
  there records the reading. The cost is 2 places that hold the baseline, which the reconcile pass
  keeps the same.
- **A reconcile pass** over **1 call for each change**: a pass also repairs what was lost while
  Home Keeper was not loaded.
- **Its own device** over **the device of the car integration**: it works for a car with no
  integration, and it does not change a device that another integration owns.

## One-way doors

- The tab id `cars`, the element `home-keeper-cars-tab` and the host API version 1.
- The source key `car_keeper` with `car_id`, `item_id` and `device_id`.
- The `managed_by` blocks, and the repair issue ids, which match the abort reasons.
- `const.HOME_KEEPER_MIN_VERSION`, which users read in the repair issue.
