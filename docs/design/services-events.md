---
title: Services, events and the API surface
summary: How Car Keeper registers its services and their websocket twins from 1 model, the gate, the events and the read projection.
implements:
  - custom_components/car_keeper/services.py
  - custom_components/car_keeper/services.yaml
  - custom_components/car_keeper/websocket_api.py
  - custom_components/car_keeper/api_surface.py
  - custom_components/car_keeper/events.py
  - custom_components/car_keeper/projections.py
related: [architecture, data-model]
source_hash: f78006d58ba9
---

# Services, events and the API surface

Every surface that another integration, an automation or the frontend can use is in
`api_surface.py`. `tests/unit/test_api_surface.py` compares the model with the code.

## Goals

- **G1. Every data action is a service.** A websocket command is a twin of a service and
  never replaces it.
- **G2. One gate.** `services.async_run` applies the admin gate for the service and for its
  websocket twin.
- **G3. Every read is open.** A read returns every field to every user.
- **G4. Every state change fires an event** from the store, named `car_keeper_<noun>_<verb>`.

## Non-goals

- A REST API of its own.
- A field that a user who is not an admin cannot read.

## Design

### Services

`api_surface.SERVICES` is the model. `services.async_register_services` registers each
service with its field schema from `SERVICE_FIELDS` and its handler from
`SERVICE_HANDLERS`. `async_unload_entry` removes each name of `SERVICE_NAMES`.

| Service | Access | Does |
|---|---|---|
| `set_settings` | Admin | Changes the `unit` setting. |

`services.async_run` refuses a user who is not an admin for an `admin_only` service with
`Unauthorized`. A call with no user comes from an automation or the core, and it passes.

### Websocket commands

- `car_keeper/get_state` returns the document from `projections.project_state`, with the
  tab state and the revision. Every user can call it.
- `car_keeper/subscribe` sends `changed` with the revision after each store change.
- Each service that is not a read has a twin `car_keeper/<service>` with the same fields.
  The twin calls `async_run`, so its gate is the gate of the service.

### Events

| Event | Fires when |
|---|---|
| `car_keeper_settings_updated` | A setting changes. Payload: `changed_fields`, `origin`. |

A pure builder in `events.py` makes each payload, and the store fires it after the save.
The payload catalog for integrators is in [EVENTS.md](../EVENTS.md).

### The read projection

`projections.project_state` copies the document, so a reader cannot change the stored
document, and adds the values that a reader needs. It hides no field.

## Trade-offs

- **1 model for the runtime and the tests** over **lists in each module**: a new service
  needs 1 spec, and the drift test finds a missing part.

## One-way doors

- The service name `set_settings` and its field `unit`.
- The event `car_keeper_settings_updated` and its payload keys.
- The websocket command names `get_state` and `subscribe`.
