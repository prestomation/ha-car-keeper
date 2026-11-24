---
title: Services, events and entities
summary: The planned services with their gates, the events, the entities, the read projections, and the import and export.
status: planned
implements:
  - custom_components/car_keeper/services.py
  - custom_components/car_keeper/services.yaml
  - custom_components/car_keeper/websocket_api.py
  - custom_components/car_keeper/api_surface.py
  - custom_components/car_keeper/events.py
  - custom_components/car_keeper/projections.py
  - custom_components/car_keeper/import_export.py
  - custom_components/car_keeper/sensor.py
  - custom_components/car_keeper/binary_sensor.py
  - custom_components/car_keeper/todo.py
  - custom_components/car_keeper/entity.py
related: [architecture, data-model, home-keeper-link, frontend]
---

# Services, events and entities

Every surface that another integration, an automation or the frontend can use is in this doc, and
later in `api_surface.py`. A test compares `api_surface.py` with what the code registers.

## Goals

- **G1. Every data action is a service.** A websocket command is a twin of a service and never
  replaces it.
- **G2. One gate.** `services.async_run` applies the admin gate for the service and for its
  websocket twin.
- **G3. A reply never leaks.** Every read goes through `projections.py`, and a test reads it as an
  admin and as a user who is not an admin.
- **G4. Every state change fires an event** from the store, named `car_keeper_<noun>_<verb>`.

## Non-goals

- A REST API of its own. The only HTTP views are for files.
- An entity for each job. Home Keeper already makes a due sensor, an overdue sensor and a button
  for each task.

## Design

### Services

Admin-only, because they change the records of the household or read private fields:

| Service | Does |
|---|---|
| `add_car`, `update_car`, `archive_car`, `delete_car` | Car records. `add_car` can take a list of starter job ids. |
| `set_car_photo` | Links an uploaded file. |
| `add_item`, `update_item`, `delete_item`, `apply_templates` | Maintenance items. |
| `update_service`, `delete_service` | Changes history. |
| `correct_odometer` | A lower reading, or an offset for a new cluster. |
| `add_document`, `update_document`, `delete_document` | Documents and their dates. |
| `add_rule`, `delete_rule` | Live-reading rules. |
| `set_settings` | Units, warning windows, privacy switches, default schedule. |
| `export_data`, `import_data` | The Home Keeper export contract. |

Open to every user, because they are the normal use of a car:

| Service | Does | Limit for a user who is not an admin |
|---|---|---|
| `list_cars`, `get_car`, `list_items`, `list_services` | Read, through the projections. | No private field. |
| `set_odometer` | Records a typed reading. | The value cannot go down. |
| `log_service` | Records a service and marks its jobs done. | Cannot attach a file. The cost is stored but not returned. |

Each service that changes data returns the id of the record. Each user-facing error has a
`translation_key`.

### Websocket commands and HTTP views

- `car_keeper/get_state` returns the projected state for the caller. `car_keeper/subscribe` sends
  `changed` after each store change. Both are open.
- `car_keeper/detect_cars` is admin-only. It lists the devices of known car integrations and the
  entities that `detect.py` maps to a use.
- Each service has a twin `car_keeper/<service>` with the same gate.
- `POST /api/car_keeper/upload` is admin-only and stores a file. `GET /api/car_keeper/file/<id>`
  needs a signed path. A user who is not an admin can sign only a car photo.

### Events

| Event | Fires when |
|---|---|
| `car_keeper_car_added`, `_updated`, `_removed` | A car changes. |
| `car_keeper_odometer_updated` | A reading is stored. Payload: `car_id`, `value`, `unit`, `source`. |
| `car_keeper_item_added`, `_updated`, `_removed` | A job changes. |
| `car_keeper_item_due_soon`, `car_keeper_item_overdue` | A job enters the status. It fires 1 time for each due point. |
| `car_keeper_service_logged`, `_updated`, `_removed` | The history changes. |
| `car_keeper_document_added`, `_updated`, `_removed` | A document changes. |
| `car_keeper_settings_updated` | A setting changes. |

Every user can listen to the bus, so no payload has the VIN, the plate, a cost, a shop, a note or
a file name. A payload has ids, the car name, the job name, dates, readings and statuses.

### Entities

For each car, on the device of the car:

| Entity | State | Notes |
|---|---|---|
| `sensor` odometer | The reading, in the unit of the car | Device class `distance`, state class `total_increasing`. The attribute `reading` is the same number and does not follow a display unit that a user sets. Home Keeper tasks read that attribute. |
| `sensor` next job | The name of the job that is due first | Attributes: `distance_left`, `days_left`, `due_date`, `status`. |
| `sensor` jobs due | The count of jobs that are `soon` or `overdue` | Attribute: the list of names. |
| `binary_sensor` maintenance | On when a job is overdue | Device class `problem`. |
| `todo` list | The jobs that are `soon` or `overdue` | A check logs the job at the reading of now. |

The odometer sensor restores its value from the store at start, so Home Keeper never sees it as
unavailable after a restart.

### Projections

`projections.project_state(doc, caller)` builds every reply.

| Field | Admin | Other users |
|---|---|---|
| `vin`, `plate` | yes | no. With the setting on, `plate_tail` has the last 3 characters. |
| `cost`, `shop`, service `files`, service `notes` | yes | no, unless the setting "Show costs" is on (cost only) |
| Documents and their files | yes | only the name and the due date |
| Car photo, name, odometer, jobs, statuses | yes | yes |

### Import and export

Car Keeper joins the Home Keeper export (`INTEGRATING.md` §11). `export_data` returns `{format,
version, data, skipped}` and copies the files into `files_dir`. `import_data` is an upsert by id,
then by the natural key (the VIN, then the name of a car). It has a `dry_run`. It never deletes a
record that is not in the document.

- Exported: cars with their private fields, items, services, readings, documents, rules and
  settings.
- Not exported: `hk_asset_id`, `hk_task_id` and completion times. The reconcile pass makes them
  again.
- Next to an area id and a person id, the export has the name. An entity id that does not exist on
  import gives a warning and a typed odometer.

## Trade-offs

- **`log_service` open** over **admin-only**: the person who drives the car to the shop can record
  it. The cost is that a user can write a wrong service, which an admin can delete.
- **Private fields in the export** over **a redacted export**: an export is a backup, and only an
  admin can run it.

## One-way doors

- Each service name and field, each event name and payload key.
- The entity unique ids, and the attribute `reading` that Home Keeper tasks use.
- The export `format` number and the keys of `data`.
- The websocket command names and the 2 HTTP paths.
