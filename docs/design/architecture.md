---
title: Architecture
summary: What Car Keeper is, the split into admin and usage, the modules and the index of the design docs.
implements:
  - custom_components/car_keeper/__init__.py
  - custom_components/car_keeper/const.py
  - custom_components/car_keeper/config_flow.py
  - custom_components/car_keeper/diagnostics.py
  - custom_components/car_keeper/backend_i18n.py
  - custom_components/car_keeper/coordinator.py
  - custom_components/car_keeper/manifest.json
related: [data-model, home-keeper-link, services-events, frontend]
source_hash: 0b2f910dbb1d
---

# Architecture

Car Keeper is a Home Assistant integration (domain `car_keeper`) for the maintenance of the
cars of a household. It is a companion of Home Keeper, as Home Keeper Library is. The request
that started it is Home Keeper issue 599: a Vehicles tab with time-based and sensor-based
maintenance, which borrows the parts and stock framework.

## Goals

- **G1. Distance or time, whichever comes first.** A job has a distance interval, a time
  interval, or both. It is due at the first limit.
- **G2. Works with no sensor.** A car with a typed odometer has every feature. A car
  integration only removes the typing.
- **G3. Home Keeper does the reminders.** Each job is a Home Keeper task. Car Keeper builds
  no notification, calendar or to-do system of its own.
- **G4. Every read is open.** Every Home Assistant user can read all data, also the VIN,
  the plate and the costs. Only record management is admin-only.
- **G5. Testable core.** The rules for intervals, units, readings and sync plans run without
  Home Assistant, so the unit tier and the mutation gate check them.
- **G6. Services first.** Each data action is a `car_keeper.*` service, so automations and
  voice can do what the tab does.
- **G7. Useful without the tab.** If Home Keeper is missing or too old, the store, the
  services, the cards and the entities still work.

## Non-goals

- A sidebar panel of its own. The admin UI is a tab in the Home Keeper panel.
- A cloud connection to a car. Car Keeper reads entities that other integrations make.
- The schedule of a car maker. The starter jobs are common intervals that the user edits.
- Fuel logs, trip logs and cost per distance ([IDEAS.md](../../IDEAS.md)).
- More than 1 config entry. The manifest sets `single_config_entry`.

## Design

### Admin and usage

| | Admin | Usage |
|---|---|---|
| Who | Admin users | Every user |
| Where | The Cars tab in the Home Keeper panel | Dashboard cards, entities, open services |
| What | Add, edit and delete cars, jobs, documents and settings. | Read all data. Type an odometer reading. Log a service. |

Do not mix the 2. A card never edits a car. Each data action of the tab is also a service.

### Module map

| Layer | Modules | Rule |
|---|---|---|
| Pure core | `const.py`, `models.py`, `events.py`, `projections.py`, `card_resource.py`, `backend_i18n.py`, `api_surface.py` | No Home Assistant import. |
| Boundary | `store.py`, `coordinator.py` | Talks to storage and the bus. |
| Glue | `__init__.py`, `services.py`, `websocket_api.py`, `home_keeper.py`, `frontend_assets.py`, `card.py`, `config_flow.py`, `diagnostics.py` | Registers and connects, with no rules of its own. |

`tests/unit/test_pure_core.py` checks the pure core row against the code.

### Setup

`async_setup_entry` runs these steps in order:

1. Read the string tables in an executor job, and load the store.
2. Make the coordinator and store it as `entry.runtime_data`.
3. Register the static path, the card resource and the websocket commands.
4. Forward the platforms and register the services.
5. Start `home_keeper.HomeKeeperLink`. It adds the tab and the companion row, or shows a
   repair issue.

`async_unload_entry` unloads the platforms and removes each service. The static path and
the card resource stay, because most unloads are half of a reload.

### Config entry and options

The config flow checks Home Keeper first and stops with the reason if the check fails. It
asks for the distance unit of a new car, with the unit system of Home Assistant as the
default. The options flow returns `config_flow.merge_flow_input`, so no stored key is lost.
Car Keeper has no credential.

### Manifest

`dependencies`: `frontend`, `http`. `after_dependencies`: `home_keeper`, `lovelace`.
`integration_type`: `service`. `iot_class`: `local_push`. `requirements`: none.

### Translations

17 languages, the set of Home Keeper: `const.LANGUAGES`. Exceptions are in `strings.json`.
Text that is not an exception, such as the tab title, is in `backend_strings/<lang>.json`.
`backend_i18n.preload` reads every table in an executor job at setup.

### Diagnostics

The diagnostics download has the options, the tab state, the Home Keeper reason, the counts
and the document. A user attaches the download to a public issue. So the download redacts
the VIN and the plate. That rule is for the support file. It is not access control.

### Design doc index

| Doc | Subject |
|---|---|
| [data-model](data-model.md) | The storage document and the store |
| [home-keeper-link](home-keeper-link.md) | The check, the tab, the companion and the repair issue |
| [services-events](services-events.md) | Services, events, websocket commands and the API surface |
| [frontend](frontend.md) | The Cars tab, the cards and the delivery of the bundles |

The approved design of the first release is in
[docs/research/first-release](../research/first-release/architecture.md). Each part moves
into these docs when it is built.

## Trade-offs

- **A companion integration** over **a change to Home Keeper**: cars get fields, an odometer
  and a history that an appliance does not have, and Home Keeper stays general. The cost is
  a second install and the sync.
- **A tab in the Home Keeper panel** over **a panel of its own**: 1 admin place for the home.
- **Every read open** over **admin-only private fields**: the household shares its cars, and
  1 projection for all users keeps the code simple. The cost is that a guest account on a
  wall tablet can read the VIN and the plate.

## One-way doors

- The domain `car_keeper`, the static path `/car_keeper_static` and the tab path
  `/home-keeper/cars`.
- The config entry option `unit`.
- `const.HOME_KEEPER_MIN_VERSION`, which users read in the repair issue.
