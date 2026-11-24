---
title: Services, events and the API surface
summary: The services and their gates, the websocket twins from 1 model, the bus events, and the open read projection.
implements:
  - custom_components/car_keeper/services.py
  - custom_components/car_keeper/services.yaml
  - custom_components/car_keeper/websocket_api.py
  - custom_components/car_keeper/api_surface.py
  - custom_components/car_keeper/events.py
  - custom_components/car_keeper/projections.py
related: [architecture, data-model, entities]
source_hash: ca6464f78de4
---

# Services, events and the API surface

Every surface that another integration, an automation or the frontend can use is in
`api_surface.py`. `tests/unit/test_api_surface.py` compares the model with the code.

## Goals

- **G1. Every data action is a service.** A websocket command is a twin of a service and
  never replaces it.
- **G2. One gate.** `services.async_run` applies the admin gate for the service and for its
  websocket twin.
- **G3. Every read is open.** A read returns every field to every user, also the VIN, the
  plate, the cost, the shop and the notes.
- **G4. Every state change fires an event** from the store, named `car_keeper_<noun>_<verb>`.

## Non-goals

- A REST API of its own.
- A field that a user who is not an admin cannot read. Diagnostics redact the VIN and the
  plate for a support file, which is not access control.

## Design

### Services

`api_surface.SERVICES` is the model. `services.async_register_services` registers each
service with its schema from `SERVICE_FIELDS` and its handler from `SERVICE_HANDLERS`.

| Access | Services |
|---|---|
| Admin: record management | `add_car`, `update_car`, `delete_car`, `correct_odometer`, `add_item`, `update_item`, `delete_item`, `apply_templates`, `update_service`, `delete_service`, `set_settings` |
| Admin: whole-store | `export_data`, `import_data` |
| Every user: the use of a car | `set_odometer`, `log_service` |
| Every user: reads | `list_cars`, `get_car`, `list_items`, `list_services` |

- A call with no user comes from an automation or the core, and it passes the gate.
- A mutation returns its record, with the computed values, when the call asks for it.
- `add_car` takes `starter_jobs` and `due_dates`. `set_settings` takes `templates`, the
  overrides of the starter jobs.
- `add_item` and `update_item` take `parts`, the Home Keeper parts that the job takes.
  `log_service` and `update_service` take `parts_used`, the more parts that the service
  used. Home Keeper takes them off the stock. A user who logs a service moves the stock,
  as a completion in Home Keeper does.
- `import_data` answers `{ok, dry_run, counts, records, problems}` with each problem as a
  message in the language of Home Assistant, as the Home Keeper import needs.

### Websocket commands

- `car_keeper/get_state` returns `projections.project_state`, with the state of the car
  presets in Home Keeper under `presets` ([presets](presets.md)). `car_keeper/subscribe`
  sends `changed` with the revision after each store change and each change of the preset
  status. Both are open.
- Each service that is not a read has a twin `car_keeper/<service>` with the same fields.
  The twin calls `async_run` with the admin flag of the connection user.

### Events

| Event | Payload |
|---|---|
| `car_added`, `car_updated`, `car_removed` | `car_id`, `name`, `origin`; `changed_fields` on update |
| `odometer_updated` | `car_id`, `name`, `value`, `unit`, `source`, `origin` |
| `item_added`, `item_updated`, `item_removed` | `car_id`, `item_id`, `name`, `origin`; `changed_fields` on update |
| `item_due_soon`, `item_overdue` | the car, the job, `status`, `first`, the limits and the days and distance left |
| `service_logged`, `service_updated`, `service_removed` | `car_id`, `service_id`, `date`, `reading`, `items`, `shop`, `cost`, `origin` |
| `settings_updated` | `changed_fields`, `origin` |
| `data_imported` | `counts`, `origin` |

Each name has the prefix `car_keeper_`. A pure builder in `events.py` makes each payload,
and the store fires it after the save. The catalog for integrators is
[EVENTS.md](../EVENTS.md).

### The read projection

`projections.project_state` copies the document and adds `summary` to each car and `due` to
each item. `projections.project_car` gives 1 car with its items in due order, its service
records and its readings. The projection hides no field. `tests/unit/test_projections.py`
and `tests/component/test_services.py` read as a user who is not an admin and fail if a
field is missing.

## Trade-offs

- **Every read open** over **private fields for admins**: the household shares its cars,
  and 1 projection serves every reader. A guest account can read the VIN and the plate.
- **`log_service` open** over **admin-only**: the person who drives the car to the shop
  records the visit. An admin can change or delete a wrong record.

## One-way doors

- Each service name and field, each event name and payload key.
- The websocket command names `get_state` and `subscribe`, and each twin name.
- The `summary` and `due` keys of a read reply.
