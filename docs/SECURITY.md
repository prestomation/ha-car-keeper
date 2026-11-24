---
title: Security model
summary: The access of admins and of non-admin users to each surface of Car Keeper. Every read is open to every user.
---

# Security model

In Car Keeper, every Home Assistant user can read all data. Only an admin can manage the
records of the household. Every user can do the normal use of a car: type an odometer
reading and log a service.

## The rule

- **Every read is open.** Every user can read each car with its VIN and its plate, each
  job, each service with its shop, its notes and its cost, and each setting. The entity
  attributes, the event payloads, the cards and the read services show the same values.
- **Record management is admin-only.** Only an admin can add, change or delete a car, a
  job, a template, a document, a rule or a setting, and run an export or an import.
- **The use of a car is open.** Every user can type an odometer reading and log a service.

The admin UI is the Cars tab of the Home Keeper panel, and that panel is admin-only. Every
user can use the cards and the entities.

## The caller

Car Keeper reads the admin flag of the Home Assistant user that makes the call. Car Keeper
trusts a call with no user, as Home Assistant does. An automation makes that kind of call.

## Services

| Service | Access | Rule |
|---|---|---|
| `add_car`, `update_car`, `delete_car` | Admin | Record management |
| `add_item`, `update_item`, `delete_item`, `apply_templates` | Admin | Record management |
| `update_service`, `delete_service` | Admin | Record management |
| `correct_odometer` | Admin | Record management: a correction can lower the odometer |
| `set_settings` | Admin | Record management |
| `export_data`, `import_data` | Admin | Whole-store operation |
| `set_odometer` | Every user | The use of a car. The value cannot go down. |
| `log_service` | Every user | The use of a car |
| `list_cars`, `get_car`, `list_items`, `list_services` | Every user | Every read is open |

The to-do list of a car follows `log_service`: every user who can use the list can check a
job.

## Websocket commands

| Command | Access |
|---|---|
| `car_keeper/get_state` | Every user |
| `car_keeper/subscribe` | Every user |
| `car_keeper/<service>` | The access of the service |

The websocket twin of each service calls the same gate as the service
(`services.async_run`), so the access cannot differ between the 2 paths.

## HTTP routes

| Route | Access |
|---|---|
| `/car_keeper_static` | Public. Home Assistant serves a static path before authentication, so the path holds only the built bundles. |

## Diagnostics

The diagnostics download redacts the VIN and the plate of each car. A user attaches the
download to a public issue. The redaction is a rule for that support file. It is not
access control: every Home Assistant user can read the VIN and the plate.

## Credentials

Car Keeper has no credential and sends no data out of Home Assistant.
