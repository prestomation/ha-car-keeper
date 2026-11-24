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
| Settings | `set_settings` |

A service that changes data returns its record when the call asks for a response.

### Change the unit of a new car

```yaml
action:
  - action: car_keeper.set_settings
    data:
      unit: mi
```

## Events

The events are in [EVENTS.md](EVENTS.md). Each event has an `origin` key. A call from
Home Keeper and a call from Car Keeper itself send their domain, so a listener can ignore
its own echo.

## Home Keeper

Car Keeper is a companion of Home Keeper. It uses only the services, the events and the
panel tab API of Home Keeper, as the
[Home Keeper integration guide](https://github.com/prestomation/ha-home-keeper/blob/main/docs/INTEGRATING.md)
says.
