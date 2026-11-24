---
title: Events reference
summary: The bus events of Car Keeper for integrators. When each event fires, with its payload and an example automation.
---

# Events reference

Car Keeper fires a Home Assistant bus event for each change to its data. Automations and
other integrations use these events. Each event observes a change that a service already
makes, so an event needs no service of its own.

A pure function in `events.py` builds each payload. The store fires the event after it
saves the change. So a change from the tab, a card, a service or a Home Keeper task fires
the same event.

`api_surface.py` has the same catalog in `EVENTS` and `PAYLOAD_SPINES`.
`tests/unit/test_api_surface.py` calls the real builders and compares the keys.

## Event catalog

Names follow `car_keeper_<noun>_<verb>`.

| Event | Fires when |
|---|---|
| `car_keeper_car_added` | A car is added. |
| `car_keeper_car_updated` | A field of a car changes. The payload has `changed_fields`. |
| `car_keeper_car_removed` | A car is deleted with its jobs, service records and readings. |
| `car_keeper_odometer_updated` | A reading is stored: typed, from a sensor, from a service or a correction. |
| `car_keeper_item_added` | A job is added. |
| `car_keeper_item_updated` | A field of a job changes. The payload has `changed_fields`. |
| `car_keeper_item_removed` | A job is deleted. |
| `car_keeper_item_due_soon` | A job enters its warning window. It fires 1 time for each due point. |
| `car_keeper_item_overdue` | A job reaches a limit. It fires 1 time for each due point. |
| `car_keeper_service_logged` | A service record is added. |
| `car_keeper_service_updated` | A service record changes. The payload has `changed_fields`. |
| `car_keeper_service_removed` | A service record is deleted. |
| `car_keeper_settings_updated` | A setting of Car Keeper changes. |
| `car_keeper_data_imported` | An import is written. |

## Payloads

Every user can read all Car Keeper data, so a payload can hold each value of a record.
Each payload except the due events has `origin`: the origin marker of the caller, or `None`.

| Payload | Keys |
|---|---|
| Car | `car_id`, `name` |
| Odometer | `car_id`, `name`, `value`, `unit`, `source` |
| Job | `car_id`, `item_id`, `name` |
| Due | `car_id`, `car_name`, `item_id`, `name`, `status`, `first`, `distance_limit`, `distance_left`, `date_limit`, `days_left`, `unit` |
| Service record | `car_id`, `service_id`, `date`, `reading`, `items`, `shop`, `cost` |
| Settings | `changed_fields` |
| Import | `counts` |

`first` is `distance` or `date`: the limit that comes first. A distance is in the unit of the
car, and `unit` is `km` or `mi`.

## Example automation

```yaml
automation:
  - alias: Tell me when a car job is overdue
    trigger:
      - platform: event
        event_type: car_keeper_item_overdue
    action:
      - service: persistent_notification.create
        data:
          title: "{{ trigger.event.data.car_name }}"
          message: "{{ trigger.event.data.name }} is overdue."
```
