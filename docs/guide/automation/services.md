# Services and events

Each Car Keeper data action is a `car_keeper.*` service. An automation, a script or a
voice assistant can do what the Cars tab does.

## Services

| Service | Who can call it | What it does |
|---|---|---|
| `car_keeper.set_settings` | Admins | Changes the distance unit of a new car. |

The full list of the services and their fields is in the
[API reference](https://prestomation.github.io/ha-car-keeper/developer/api).

## Events

Each change fires a `car_keeper_<noun>_<verb>` event on the Home Assistant bus.

| Event | When it fires |
|---|---|
| `car_keeper_settings_updated` | A setting changes. |

The payload of each event is in [EVENTS.md](https://github.com/prestomation/ha-car-keeper/blob/main/docs/EVENTS.md).
