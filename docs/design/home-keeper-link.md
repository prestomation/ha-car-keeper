---
title: Home Keeper link
summary: How Car Keeper checks Home Keeper, adds the Cars tab, registers as a companion, and shows a repair issue.
implements:
  - custom_components/car_keeper/home_keeper.py
related: [architecture, frontend]
source_hash: 1d44b38b372a
---

# Home Keeper link

Car Keeper is a companion of Home Keeper. The contract is the Home Keeper
`docs/INTEGRATING.md`. Car Keeper uses only services, events and the Python API of the
panel tab.

## Goals

- **G1. Say why.** If Home Keeper is missing, not set up or too old, the config flow stops
  with that reason, and a running Car Keeper shows a repair issue with the same reason.
- **G2. Never block setup.** Car Keeper never raises `ConfigEntryNotReady` for Home Keeper.
- **G3. Follow Home Keeper.** When Home Keeper loads, reloads or goes away, the tab and the
  issue follow with no restart.

## Non-goals

- A Home Keeper version range. Each version from the minimum on is supported.

## Design

### The check

`home_keeper.async_check` returns `home_keeper_missing`, `home_keeper_not_set_up`,
`home_keeper_too_old` or None.

- Missing: `async_get_integration` finds no `home_keeper`.
- Not set up: Home Keeper has no loaded config entry.
- Too old: the version of the integration is below `const.HOME_KEEPER_MIN_VERSION`, or
  Home Keeper has no `panel_tabs` module. A pre-release of a later version passes.

`const.HOME_KEEPER_MIN_VERSION` is `0.35.0`. It is the first version with each part of the
contract that Car Keeper uses: managed appliances, the panel tab API, the companion export
and the `parts` list of `set_task_consumable`.

### The link

`HomeKeeperLink` runs the check at setup, on each change of a Home Keeper config entry and
when the component loads. A lock runs 1 check at a time. On a pass it:

- registers the tab with `panel_tabs.async_register_panel_tab`: companion `car_keeper`,
  id `cars`, icon `mdi:car-wrench`, element `home-keeper-cars-tab`, host API 1, and a
  `module_url` under `/car_keeper_static` with the content hash of the bundle;
- calls `register_companion` with the capability `import_export`, and again on each
  `home_keeper_register_companions` event.

On a failure it removes the tab and shows the repair issue of the reason. The issue
ids are the abort reasons, and each has the same translation key.

## Trade-offs

- **A version check and a module check** over **the module check only**: the version is the
  contract that the tasks need, and the module check finds a damaged install.

## One-way doors

- The tab id `cars`, the element `home-keeper-cars-tab` and the host API version 1.
- The repair issue ids, which match the abort reasons.
