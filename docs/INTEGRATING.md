---
title: Integrating with Car Keeper
summary: How automations, scripts, voice assistants and other integrations use the services, events and entities of Car Keeper, for integrators.
---

# Integrate with Car Keeper

Automations, scripts, voice assistants and other integrations use 3 stable surfaces:

- **Services** change the Car Keeper data.
- **Events** fire after each change.
- **Entities** show the current state.

Do not read the storage file or call the websocket commands. The tab and the cards use
those, and they can change.

The [API reference](https://prestomation.github.io/ha-car-keeper/developer/api) lists
every service field, event payload and entity attribute. The site generates it from the
integration. Which service an admin or a user can call is in [SECURITY.md](SECURITY.md).

## Services

Each operation of the tab is a `car_keeper.*` service.

| Group | Services |
|---|---|
| Cars | `add_car`, `update_car`, `delete_car` |
| Odometer | `set_odometer`, `correct_odometer` |
| Jobs | `add_item`, `update_item`, `delete_item`, `apply_templates` |
| Service records | `log_service`, `update_service`, `delete_service` |
| Settings | `set_settings` |
| Files | `export_data`, `import_data` |
| Reads | `list_cars`, `get_car`, `list_items`, `list_services` |

A change returns its record when the call asks for a response, and a read always gives
one. Use `car_id` to name a car, because 2 cars can have the
same name.

### Feed the odometer from another sensor

```yaml
automation:
  - alias: Copy the trip computer to Car Keeper
    trigger:
      - platform: state
        entity_id: sensor.my_car_total_distance
    action:
      - action: car_keeper.set_odometer
        data:
          car_id: 0a1b2c3d4e5f
          value: "{{ trigger.to_state.state | float }}"
```

A car can also read its odometer sensor itself: set `odometer_source` to `entity` and
`odometer_entity_id` to the sensor with `update_car`.

### Log a service

```yaml
action:
  - action: car_keeper.log_service
    data:
      car_id: 0a1b2c3d4e5f
      items: [9f8e7d6c5b4a]
      reading: 42150
      shop: Main Street Garage
      cost: 84.50
    response_variable: result
```

## Entities

Each car has a device with an odometer sensor, the next due distance and date, a status
sensor, an overdue binary sensor and a to-do list of the jobs that are due. The odometer
sensor has the attribute `reading`, in the unit of the car.

## Events

The events are in [EVENTS.md](EVENTS.md). Each event has an `origin` key. A call from
Home Keeper and a call from Car Keeper itself send their domain, so a listener can ignore
its own echo.

## Home Keeper

Car Keeper is a companion of Home Keeper. It uses only the services, the events and the
panel tab API of Home Keeper, as the
[Home Keeper integration guide](https://github.com/prestomation/ha-home-keeper/blob/main/docs/INTEGRATING.md)
says.

Each car is a managed appliance in Home Keeper, and each job with `add_task` is a managed
task on that appliance. A job with a distance is a usage task on the odometer sensor of
the car. Home Keeper owns the reminders of the jobs.

- A Car Keeper record has `managed_by.integration: car_keeper`. An appliance names its car
  in `managed_by.car_id`. A task names its job in `source.car_keeper.item_id`.
- A service in Car Keeper completes the task with `origin: car_keeper`. A completion in
  Home Keeper with another origin logs a service in Car Keeper with origin `home_keeper`.
- The `parts` of a job are the part links of its task. The `parts_used` of a service move
  the stock of each part with `adjust_part_stock`.
- With Home Keeper 0.38.0b5 or later, Car Keeper calls `register_presets` with the rows
  of 12 car integrations. The preset ids start with `car_keeper/`. `get_state` gives the
  status under `presets`. An older Home Keeper gets no call.
