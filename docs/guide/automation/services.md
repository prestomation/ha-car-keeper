# Services and events

Each Car Keeper data action is a `car_keeper.*` service. An automation, a script or a
voice assistant can do what the Cars tab does.

## Services

| Service | Who can call it | What it does |
|---|---|---|
| `car_keeper.add_car` | Admins | Adds a car, with its odometer and the starter jobs. |
| `car_keeper.update_car` | Admins | Changes a car. A new unit converts each value of the car. |
| `car_keeper.delete_car` | Admins | Deletes a car with its jobs and history. |
| `car_keeper.set_odometer` | Every user | Stores a reading. It cannot be below the last one. |
| `car_keeper.correct_odometer` | Admins | Stores any reading, and an offset for a new instrument cluster. |
| `car_keeper.add_item` | Admins | Adds a maintenance job. |
| `car_keeper.update_item` | Admins | Changes a job. |
| `car_keeper.delete_item` | Admins | Deletes a job. |
| `car_keeper.apply_templates` | Admins | Adds starter jobs to a car. |
| `car_keeper.log_service` | Every user | Adds a service record and marks its jobs done. |
| `car_keeper.update_service` | Admins | Changes a service record. |
| `car_keeper.delete_service` | Admins | Deletes a service record. |
| `car_keeper.set_settings` | Admins | Changes the unit of a new car and the starter jobs. |
| `car_keeper.export_data` | Admins | Returns all data for the Home Keeper export. |
| `car_keeper.import_data` | Admins | Adds and updates data from an export. |
| `car_keeper.list_cars` | Every user | Returns the cars with their status. |
| `car_keeper.get_car` | Every user | Returns 1 car with its jobs and history. |
| `car_keeper.list_items` | Every user | Returns the jobs with their limits. |
| `car_keeper.list_services` | Every user | Returns the service records. |

The full list of the services and their fields is in the
[API reference](https://prestomation.github.io/ha-car-keeper/developer/api).

## Events

Each change fires a `car_keeper_<noun>_<verb>` event on the Home Assistant bus.

| Event | When it fires |
|---|---|
| `car_keeper_car_added`, `_updated`, `_removed` | A car changes. |
| `car_keeper_odometer_updated` | A reading is stored. |
| `car_keeper_item_added`, `_updated`, `_removed` | A job changes. |
| `car_keeper_item_due_soon` | A job enters its warning window. |
| `car_keeper_item_overdue` | A job reaches a limit. |
| `car_keeper_service_logged`, `_updated`, `_removed` | A service record changes. |
| `car_keeper_settings_updated` | A setting changes. |
| `car_keeper_data_imported` | An import is written. |

The payload of each event is in [EVENTS.md](https://github.com/prestomation/ha-car-keeper/blob/main/docs/EVENTS.md).
