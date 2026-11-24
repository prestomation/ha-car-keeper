---
title: Architecture rules
summary: The admin and usage split, the privilege gate, the open reads, the pure core, the store chokepoint, entities, options and localized text.
---

# Architecture rules

How the integration is built is in [docs/design/architecture.md](../../docs/design/architecture.md).
This file gives the rules for code that changes it.

## Home Keeper

- **Home Keeper is an `after_dependencies` entry, never a `dependencies` entry.** The
  config flow must load and say why it stops. It aborts with `home_keeper_missing`,
  `home_keeper_not_set_up` or `home_keeper_too_old`.
- **Never raise `ConfigEntryNotReady` for Home Keeper.** A retry cannot install or update
  it. `home_keeper.HomeKeeperLink` shows a repair issue with the same reason, and turns
  the tab and the Home Keeper sync off. The store, the services, the cards and the entities
  still work ([home-keeper-link](../../docs/design/home-keeper-link.md)).
- Each call to a Home Keeper service is guarded with `has_service` and sends
  `origin: "car_keeper"`. A listener ignores an event with that origin.

## Administration and usage

- **Administration is the Cars tab of the Home Keeper panel** at
  `/home-keeper/cars/...`. Car Keeper has no sidebar panel of its own. The Home Keeper
  panel is admin-only, so the tab is admin-only.
- **Usage goes through the cards, the entities and the open services.** Never put
  management UI in a card.
- All writes go through `CarStore` (`store.py`). Entities, the tab and the cards read the
  document and never write it.
- Records are plain JSON-serializable dicts in storage, never model objects.
- **A bulk write never replaces the document.** Plan it on a snapshot, then write only what
  the plan changed, with no `await` between the merge and the save.
- A field that only a sync reads, such as a Home Keeper task id, is bookkeeping. It fires
  no event.
- The store tells its listeners after each save. The coordinator sends the document to
  the entities with `async_set_updated_data`, so an entity never waits for a poll.

## Privilege model

The admin and usage split is also the security boundary ([SECURITY.md](../../docs/SECURITY.md)).

- **One gate for both paths.** `services.async_run` refuses a non-admin caller of an
  `admin_only` service with `Unauthorized`. The service handler and the websocket twin
  both call it, so a gate cannot be on 1 path only.
- A websocket command with no service twin carries `@websocket_api.require_admin` when
  it is admin-only.
- A call with no `context.user_id` comes from an automation or the core and is trusted.
- Raise the bare `Unauthorized`. It is the 1 exception to localized exceptions, and the
  websocket and REST layers map it to `unauthorized` and 401.
- Serve only built assets as a static path. Home Assistant serves static paths before
  authentication.

### Open reads

- **Every read is open to every user.** The VIN, the plate, the costs, the shop, the notes
  and the service records are not private. Do not add an admin-only read, and do not strip
  a field from a reply, an entity attribute, an event payload or a card.
- Every read goes through `projections.py`, which shapes the reply and hides no field.
  `tests/unit/test_projections.py` reads a seeded document as a user who is not an admin
  and fails if a field is missing.
- The diagnostics download redacts the VIN and the plate. That is a rule for a support
  file that a user pastes into an issue. It is not access control.

### How to decide

Use this list for each new service, websocket command, HTTP method and event. Write the
result in the plan's Security section ([pr-workflow.md](pr-workflow.md)).

- **Open: every read**, through the projection.
- **Open: the use of a car.** `set_odometer`, `log_service` and a mark of a job as done.
- **Admin-only: record management.** Add, update and delete a car, an item, a template, a
  document, a rule or a setting.
- **Admin-only: bulk and whole-store operations**, such as import and export.
- **Admin-only: each operation that can send text to a place the caller cannot reach**,
  such as a Home Keeper appliance that the caller cannot edit.
- **An upload always needs a real admin user.** A signed URL never writes.
- **If no rule fits, ask the maintainer.** Write the answer in the plan, then add the rule
  here.

## Pure core

- The pure modules (the module map in the
  [architecture design doc](../../docs/design/architecture.md#module-map)) never import
  `homeassistant`. `tests/unit/test_pure_core.py` checks each one, and checks the module
  map against `_PURE_MODULES` in `tests/unit/conftest.py`.
- A pure function never reads a clock. The caller passes `now` (an aware ISO 8601
  timestamp) and `today` (`YYYY-MM-DD`).
- All datetimes are timezone-aware. Use `homeassistant.util.dt` at the HA boundary
  (`store.now` and `store.today`).
- The pure core raises `models.CarKeeperError(key, **placeholders)`. The key is in
  `strings.json` `exceptions`.
- `models.normalize_state` runs on each load, so a new section of the document needs no
  migration step.
- **A state machine is a pure transition function.** It takes a state and an event and
  returns the next state. A Hypothesis `RuleBasedStateMachine` tests it against the real
  code ([testing.md](testing.md#state-machines)).

## Entities and devices

- Each car has 1 device, `(car_keeper, <car id>)`. The entities of the car are on it.
- A per-car entity has the car id in its `unique_id`, so a rename keeps it.
- Use `has_entity_name` and a `translation_key`.

## Options

- The only option is `unit`, the distance unit of a new car. The config flow and the
  options flow ask for it.
- **An options flow merges. It never replaces.** Return `config_flow.merge_flow_input`
  from `async_create_entry`, never `user_input`. Home Assistant stores the result as the
  whole options object, so a raw return deletes every key that the form does not show.
- Add an `OptionSpec` to `api_surface.OPTIONS` for each key.

## Localized text

- **Every user-facing exception is localized.** The service layer turns a
  `CarKeeperError` into a `ServiceValidationError` with `translation_domain=DOMAIN`, the
  key and the placeholders. Never raise with an f-string.
  `tests/unit/test_exception_translations.py` fails on a bare raise and on a key that
  `strings.json` does not have.
- A websocket error and an HTTP view error show their message as is. Resolve it with
  `backend_i18n.resolve_exception` in the language of Home Assistant.
- Text that is not an exception and has no place in `strings.json` goes in
  `backend_strings/<lang>.json`: the tab title, the companion description and the Home
  Keeper task names.
