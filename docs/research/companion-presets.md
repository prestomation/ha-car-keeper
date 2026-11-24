---
title: Can a companion add presets to Home Keeper
summary: What a companion can do in Home Keeper today, why it cannot ship a preset, and 3 options to change that.
---

# Can a companion add presets to Home Keeper

**Short answer: no.** A companion cannot put a preset in the preset picker or in the Tasks tab
nudge. The preset catalog is data inside Home Keeper. But a companion can make the thing that a
preset makes: a declarative companion, through admin-only services that exist.

I read Home Keeper at commit `3ca25b9` (version 0.38.0b3). File names below are in
`custom_components/home_keeper/`. This page proposes changes. It changes nothing in Home Keeper.

## What exists

| Surface | Evidence | Gate | Use for Car Keeper |
|---|---|---|---|
| `register_companion` service | `companions.REGISTER_COMPANION_SCHEMA`: `domain`, `name`, `icon`, `description`, `config_entry_id`, `docs_url`, `capabilities`. Other keys are removed (`extra=vol.REMOVE_EXTRA`). | admin-only | A row in Settings → Companions. No preset field. |
| `add_declarative_companion`, `update_…`, `delete_…` | `api_surface.py`: `ServiceSpec(..., admin_only=True)`. The spec has `selection`, `trigger`, `task_template` and a free `preset_id` string. | admin-only | Makes 1 managed sensor task for each matched entity. |
| `list_declarative_companions` | `api_surface.py` | open | Find the specs that Car Keeper made. |
| `home_keeper/list_declarative_presets` websocket command | `websocket_api.ws_list_declarative_presets` | open | Read the catalog, with the match count and the `default_spec` of each preset. |
| Panel tab | `panel_tabs.async_register_panel_tab` (Python API) | admin sees it | The Cars tab. |
| Managed appliance and tasks | `add_asset`, `update_managed_asset`, `add_task` with `managed_by`, `set_task_consumable` | writes admin-only | A car, its jobs and its parts. |
| Triggered and sensor tasks | `recurrence_type: triggered` or `sensor`, `trigger_task`, `set_task_meter` | writes admin-only | Jobs that a condition or a meter starts. |
| Completion `reading` | `complete_task`, `update_completion` | as the completion | The odometer at a service. |
| Events | `home_keeper_task_completed` and the others in `docs/EVENTS.md` | bus | Two-way sync. |

A call from the setup of an integration has no user, so it passes the admin gate
(`docs/INTEGRATING.md` §9).

## What does not exist

1. **No way to add a catalog row at run time.** `declarative_presets.CATALOG_PRESETS` is built
   when the module loads, from `declarative_presets_catalog.INTEGRATIONS`.
   `ws_list_declarative_presets` loops over `CATALOG_PRESETS` only. The picker
   (`preset-picker.ts`) and the nudge (`preset-nudge.ts`) read that command.
2. **No translated text for an outside preset.** The task names are in
   `declarative_preset_text.DUTY_NAMES`. `declarative_presets.localized_task_template` puts text
   into the Home Assistant language only for a preset of the catalog.
3. **No shape for a distance.** The 6 shapes are `percent_low`, `life_low`, `wear_high`,
   `reading_low`, `reading_high` and `alert`. `life_low` converts time units only. `reading_low`
   compares a plain number in the unit of the entity.
4. **No upkeep for outside rows.** `ci/check_preset_keys.py` checks each row against its upstream
   file at a pinned commit. It knows only the catalog.

## Options

### Option A: Car Keeper makes its own rules

Car Keeper keeps a small catalog of its own and needs no change in Home Keeper. It has 2 forms,
and Car Keeper can use both.

- **A1: declarative companions.** Car Keeper calls `add_declarative_companion` with a spec for 1
  car: `selection.target_integration`, `selection.translation_keys` and `selection.device_ids`.
  Home Keeper watches the entities and owns the tasks. The spec shows in Settings → Companions →
  Declarative. It counts against the limit of 50 specs (`const.MAX_DECLARATIVE_COMPANIONS`). Car
  Keeper writes the task names in the Home Assistant language itself.
- **A2: Car Keeper rules.** Car Keeper watches the entity and arms a managed triggered task
  (`add_task`, `trigger_task`, `complete_task` with its origin). This is the Battery Notes glue
  pattern. It can do what no shape can: a distance countdown in the unit of the car, and a tyre
  pressure limit for each car.

One-way doors: the rule ids of Car Keeper, the `preset_id` values it writes (I propose the prefix
`car_keeper:`), and its `source` namespace on a task. Security: both forms use admin-only
services. Car Keeper calls them from an admin action in the Cars tab, or from its setup.

### Option B: car rows in the Home Keeper catalog, by pull request

I add rows for car integrations to `declarative_presets_catalog.py`, as the 5 car rows that exist.
[car-integrations.md](car-integrations.md) lists 13 candidate rows.

- Every Home Keeper user gets them, with or without Car Keeper. The nudge and the picker work with
  no new code.
- The upkeep tools check the keys each week.
- It adds no new contract. The row format stays private to Home Keeper.
- Limits: only the 6 shapes, and a new row waits for a Home Keeper release. A new duty needs its
  name in 17 languages.

The Cars tab can still offer these presets for 1 car. It reads `list_declarative_presets` and
calls `add_declarative_companion` with the `default_spec` and the device of the car in
`selection.device_ids`. Both exist today.

### Option C: a new extension point in Home Keeper

Home Keeper gets an admin-only service, for example `home_keeper.register_presets`. A companion
sends rows in the catalog format: `domain`, `brand`, `icon` and `duties` (`duty`, `shape`,
`platform`, `keys`, `limit`, `state`). For a new duty it sends the name in each language, with
`en` required.

- Home Keeper checks each row with the code that builds a catalog preset. It keeps the rows in a
  registry for the run, as `CompanionRegistry` does. The companion sends them again on
  `home_keeper_register_companions`.
- `ws_list_declarative_presets` returns them with a `provider` field. The preset id gets the
  prefix of the companion.
- The companion sends no Jinja. The shape gives the trigger and the templates. So a companion
  cannot put a template in the panel.

What Home Keeper must change: the service and its schema, a registry, `api_surface.py`, the merge
in the list command, the lookup of a preset by id in the sync, a provider chip in the picker,
tests and docs. A unit-aware distance shape is a second change.

One-way doors: the service name and fields, and above all the row format. Today the upkeep changes
that format freely. With this option it is a public contract. Also the preset id prefix, which
goes into stored specs and into the `home_keeper_preset_nudge` user data.

Security: admin-only, because a row decides which tasks the home gets and puts text in the admin
panel. An open service lets any user fill the picker. Bound each list and each string, as
`REGISTER_COMPANION_SCHEMA` does.

## Comparison

| | A: own rules | B: catalog rows | C: extension point |
|---|---|---|---|
| Home Keeper change | none | data only | new service and contract |
| Works without Car Keeper | no | yes | no |
| Distance countdown, tyre limits | yes (A2) | no | only with a new shape |
| Key upkeep | Car Keeper | Home Keeper tools | the companion |
| New one-way doors | in Car Keeper only | none | row format becomes public |

## Recommendation

**B and A2 now. C later, if a second companion needs it.**

1. Send the car rows that fit the 6 shapes to the Home Keeper catalog (B). They help every user,
   and they cost no new contract.
2. In Car Keeper, build rules (A2) only for what a shape cannot do: the odometer intervals, a
   distance countdown and tyre pressure limits.
3. Use A1 only to add a catalog preset for 1 car from the Cars tab.
4. Do not build C for 1 companion. It freezes the row format, and Car Keeper does not need it.

The mockup shows this split: each preset in the review dialog has a source chip, "Home Keeper
preset" or "Car Keeper rule".

## Not checked

1. I did not run Home Keeper. I read the code and the design docs.
2. I did not test a call of `add_declarative_companion` with `selection.device_ids` from a second
   integration.
3. I did not read the panel code of the nudge beyond its design doc, so "reads only the catalog"
   for the nudge comes from the doc and from the websocket command.
