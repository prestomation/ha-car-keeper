---
title: Architecture
summary: What Car Keeper is, the split into admin and usage, the planned modules and the index of the design docs.
status: planned
implements:
  - custom_components/car_keeper/__init__.py
  - custom_components/car_keeper/const.py
  - custom_components/car_keeper/config_flow.py
  - custom_components/car_keeper/diagnostics.py
  - custom_components/car_keeper/backend_i18n.py
  - custom_components/car_keeper/manifest.json
related: [data-model, home-keeper-link, services-events, frontend, repository]
---

# Architecture

Car Keeper is a planned Home Assistant integration (domain `car_keeper`) for the maintenance of
the cars of a household. It records each car, its odometer, its maintenance jobs and its service
history. It is a companion of Home Keeper, as Home Keeper Library is. No code exists yet: this doc
and the docs in its index are the design.

The request that started it is Home Keeper issue 599: a Vehicles tab with time-based and
sensor-based maintenance, which borrows the parts and stock framework.

## Goals

- **G1. Distance or time, whichever comes first.** A job has a distance interval, a time interval,
  or both. It is due at the first limit.
- **G2. Works with no sensor.** A car with a typed odometer has every feature. A car integration
  only removes the typing.
- **G3. Home Keeper does the reminders.** Each job is a Home Keeper task. Car Keeper builds no
  notification, calendar or to-do system of its own.
- **G4. Private fields stay private.** Only an admin can read the VIN, the plate, the costs and
  the documents.
- **G5. Testable core.** The rules for intervals, units, readings, projections and sync plans run
  without Home Assistant, so the unit tier and the mutation gate check them.
- **G6. Services first.** Each data action is a `car_keeper.*` service, so automations and voice
  can do what the tab does.
- **G7. Useful without the tab.** If Home Keeper is missing or too old, the store, the services,
  the cards and the entities still work.

## Non-goals

- A sidebar panel of its own. The admin UI is a tab in the Home Keeper panel.
- A cloud connection to a car. Car Keeper reads entities that other integrations make.
- The schedule of a car maker. The starter jobs are common intervals that the user edits.
- Fuel logs, trip logs and cost per distance in the first release ([IDEAS.md](../../../IDEAS.md)).
- More than 1 config entry. The manifest sets `single_config_entry`.

## Design

### Admin and usage

| | Admin | Usage |
|---|---|---|
| Who | Admin users | Every user |
| Where | The Cars tab in the Home Keeper panel | Dashboard cards, entities, open services |
| What | Add and edit cars, jobs, parts, documents and settings. Read the VIN, the plate and the costs. | See what is due. Type an odometer reading. Mark a job done. |

Do not mix the 2. A card never edits a car. The tab is never the only way to do a data action.

### Module map

| Layer | Planned modules | Rule |
|---|---|---|
| Pure core | `const.py`, `models.py`, `units.py`, `schedule.py`, `templates.py`, `events.py`, `projections.py`, `import_export.py`, `task_plan.py`, `detect.py`, `card_resource.py`, `backend_i18n.py` | No Home Assistant import. |
| Boundary | `store.py`, `coordinator.py`, `odometer.py`, `files.py` | Talks to storage, the bus, the state machine and the file system. |
| Glue | `__init__.py`, `services.py`, `websocket_api.py`, `home_keeper.py`, `task_sync.py`, `asset_sync.py`, `rules.py`, `frontend_assets.py`, `card.py`, `config_flow.py`, `diagnostics.py` | Registers and connects. No rules. |
| Platforms | `sensor.py`, `binary_sensor.py`, `todo.py`, with `entity.py` | `const.PLATFORMS` lists them. |

- `schedule.py` computes the next due point and the status of a job ([data-model](data-model.md)).
- `units.py` converts km, miles and metres.
- `detect.py` maps the entities of a known car integration to uses, by translation key.
- `task_plan.py` is the pure planner of the Home Keeper sync
  ([home-keeper-link](home-keeper-link.md)).

### Setup

`async_setup_entry` runs these steps in order:

1. Read the string tables in an executor job, and load the store.
2. Make the coordinator and store it as `entry.runtime_data`.
3. Register the static path, the card, the websocket commands and the file views.
4. Forward the platforms and register the services.
5. Start the odometer followers, which copy a bound entity into the store.
6. Start `home_keeper.HomeKeeperLink`. It adds the tab and the companion row, or shows a repair
   issue.
7. Start the task sync and the asset sync, and run 1 reconcile pass.

`async_unload_entry` unloads the platforms, removes each service and stops the followers and the
syncs. The static path and the card resource stay, because most unloads are half of a reload.

### Config entry and options

The config flow checks Home Keeper first and stops with the reason if the check fails. It asks for
the default distance unit, with the unit system of Home Assistant as the default. The options flow
returns `config_flow.merge_flow_input`, so no stored key is lost. Car Keeper has no credential.

### Manifest

`dependencies`: `frontend`, `http`, `person`. `after_dependencies`: `home_keeper`, `lovelace`.
`integration_type`: `service`. `iot_class`: `local_push`. `requirements`: none.

### Translations

17 languages, the set of Home Keeper: ca, cs, da, de, en, es, fi, fr, it, nb, nl, pl, pt-BR, ru,
sv, uk and zh-Hans. Exceptions are in `strings.json`. Text that is not an exception, such as task
names and starter job names, is in `backend_strings/<lang>.json`.

### Diagnostics

The diagnostics give the options, the tab state, the counts and the store document. They redact
the VIN, the plate, the notes, the shop names and the file names.

### Design doc index

| Doc | Subject |
|---|---|
| [data-model](data-model.md) | The storage document, the records, the odometer and the schedule rules |
| [home-keeper-link](home-keeper-link.md) | The check, the tab, the appliance, the tasks, the parts and the sync |
| [services-events](services-events.md) | Services, events, entities, projections, import and export |
| [frontend](frontend.md) | The Cars tab, the cards, the routes and the look |
| [repository](repository.md) | The scaffold, the test tiers, the CI and the guardrails |

## Trade-offs

- **A companion integration** over **a change to Home Keeper**: cars get fields, an odometer and a
  history that an appliance does not have, and Home Keeper stays general. The cost is a second
  install and the sync.
- **A tab in the Home Keeper panel** over **a panel of its own**: 1 admin place for the home.
- **1 document for all cars** over **a file for each car**: 1 save is 1 consistent state. The
  design size is 20 cars with 30 years of history.

## One-way doors

- The domain `car_keeper`, the static path `/car_keeper_static` and the tab path
  `/home-keeper/cars`.
- The storage key `car_keeper` and its version.
- The service names and fields, and the event names and payloads.
- The `source` namespace `car_keeper` on a Home Keeper task and appliance.
