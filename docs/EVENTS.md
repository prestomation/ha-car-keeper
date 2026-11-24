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
| `car_keeper_settings_updated` | A setting of Car Keeper changes. |

## Payloads

Every user can read all Car Keeper data, so a payload can hold each value of a record.

### `car_keeper_settings_updated`

| Key | Type | Notes |
|---|---|---|
| `changed_fields` | `list[str]` | The settings that changed, such as `unit`. |
| `origin` | `str \| None` | The origin marker of the caller. |

## Example automation

```yaml
automation:
  - alias: Tell me when the Car Keeper settings change
    trigger:
      - platform: event
        event_type: car_keeper_settings_updated
    action:
      - service: persistent_notification.create
        data:
          message: "Car Keeper settings changed: {{ trigger.event.data.changed_fields }}"
```
