---
title: Car presets in Home Keeper
summary: The preset rows that Car Keeper registers in the Home Keeper preset picker, the state machine of the registration, and how the rows stay true to their integrations.
implements:
  - custom_components/car_keeper/presets.py
  - custom_components/car_keeper/hk_presets.py
related: [home-keeper-link, frontend, services-events]
source_hash: 13641684bc7e
---

# Car presets in Home Keeper

A Home Keeper preset makes a task for each entity that a car integration reports: a
service that is due soon, a low oil life, or a warning such as low brake fluid. Car Keeper
sends the rows of the car integrations that it knows to Home Keeper. The user adds a
preset in Home Keeper, in Settings, Companions, Declarative companions, Add from preset.

## Goals

- **G1. Optional.** A Home Keeper with no `register_presets` (0.35.0 to 0.38.0b4) gets no
  call, no repair issue and no log line above debug. Everything else works.
- **G2. There for the whole run.** Home Keeper keeps the presets in memory. Car Keeper
  registers them again at each start, when the service appears and when Home Keeper
  asks its companions. It removes them when it unloads.
- **G3. Each row is true.** Each row passes the check of Home Keeper itself, and each key
  is in the file of its integration at a pinned commit.

## Non-goals

- The preset nudge: a dialog in the Cars tab that offers the presets for the device of a
  car ([IDEAS.md](../../IDEAS.md)).
- Rules that no preset shape can hold, such as a distance to service in the unit of the
  car or a tyre pressure limit. These are the live readings of `IDEAS.md`.

## Design

### The rows

`presets.ROWS` uses the format of the Home Keeper catalog with no `source` and no
`verified` key. The shapes are `life_low` (days to the service, 336 hours), `percent_low`
(oil life, 10%) and `alert` (a warning). An alert is a binary sensor in the state `on`,
except the Rivian brake fluid sensor in the state `active`.

| Integration | Duties |
|---|---|
| `volvo`, `polestar_api`, `uconnect` | Annual service. Volvo and Uconnect also have fluids, brakes and tyres. |
| `fordpass`, `mazda_cs` | Oil service. Mazda also has fluids, brakes and tyres. |
| `kia_uvo`, `mbapi2020`, `rivian` | Fluids, brake fluid, tyres, 12 V battery, warning lamps. |
| `subaru` | Warning lamps. Upstream turns them off by default. |
| `bm6_ha` | 12 V battery. |
| `tesla_fleet`, `teslemetry` | Tyres. Upstream turns them off by default. |

`annual_service` and `oil_service` are duties of Home Keeper. The 5 other duties
(`check_fluid_levels`, `check_brake_fluid`, `check_tyres`, `check_warning_lamps`,
`check_12v_battery`) go in `duty_names`, in the 17 languages. The tab shows the same
names, and `tests/unit/test_presets.py` checks that they agree.

Rows that the format cannot hold are left out: Audi, Volkswagen ID and WiCAN set no
translation key; the Polestar warnings have states with spaces; the states of the Volvo
service warning are longer than 32 characters.

### The registration

`presets.transition(link, event)` returns the new `Link` and the call to make, or None.

| Event | Call |
|---|---|
| `start` | `register` if the service is there |
| `service_added` | `register` while running, else `unregister` (an old call can leave rows) |
| `service_removed` | none; the link forgets the presets |
| `ask` (`home_keeper_register_companions`, or Home Keeper became available) | `register` while running and the service is there |
| `accepted` | none; after a stop, `unregister` |
| `refused` | none; the status is `failed` |
| `stop` | `unregister` if the service is there |

`hk_presets.PresetSync` feeds the events and runs the calls 1 at a time in a background
task. A register call replaces what Home Keeper holds, and Home Keeper fires no event
when the presets did not change. A refused call logs a warning. A status change sends the
store signal, so the tab reads the state again.

`get_state` has the key `presets`: `status` (`registered`, `no_service`, `failed`,
`waiting`), `preset_ids`, `error` and `rows` (`domain`, `brand`, `duties`). The settings
page of the tab shows it.

### Tests

- `tests/unit/test_presets_stateful.py`: the state machine against a fake Home Keeper with
  a memory registry and a queue of calls. When the queue is empty: a running Car Keeper
  is registered unless the last call failed, a stopped one leaves no row, and no service
  means nothing registered.
- `tests/unit/test_presets.py`: each row passes `preset_registry.build_registration` of
  Home Keeper at the pin of `ci/home-keeper-presets.env`. The golden file
  `tests/fixtures/presets.json` holds the call and the preset ids.
- `ci/check_preset_keys.py`: each key is in the translation file of its integration at
  the commit in `presets.SOURCES`, or in a code file for a `match: text` source. The
  `preset-keys` workflow runs it on a change and each week against the newest files.
- `tests/integration/test_presets.py`: the real Home Keeper lists the presets with the
  golden ids. The oldest lane runs Home Keeper 0.35.0 and checks `no_service`.

## Trade-offs

- **Presets through Home Keeper** over **rules of Car Keeper**: Home Keeper watches the
  entities and owns the tasks, with no new code here. The cost is the 3 shapes, which
  cannot hold a distance in the unit of the car.
- **Feature detection** over **a higher minimum version**: a user of Home Keeper 0.35.0
  keeps Car Keeper. The cost is a status line that says why there are no presets.

## One-way doors

- The preset ids `car_keeper/<domain>_<shape>[_<platform>][_<state>]`. A spec that a
  user adds keeps its `preset_id`.
- The duty ids of `DUTY_NAMES`, which go into the task names.
- The `presets` key of `get_state` and its fields.
