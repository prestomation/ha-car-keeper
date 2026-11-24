---
title: Cars tab and cards
summary: The Cars tab in the Home Keeper panel, the dashboard cards, and how Car Keeper serves and registers the bundles.
implements:
  - custom_components/car_keeper/frontend_assets.py
  - custom_components/car_keeper/card.py
  - custom_components/car_keeper/card_resource.py
  - custom_components/car_keeper/frontend/src/*.ts
  - custom_components/car_keeper/frontend/src/locales/*.ts
related: [architecture, home-keeper-link]
source_hash: ff098878ff57
---

# Cars tab and cards

The frontend is 2 ES modules: the Cars tab, which the Home Keeper panel loads for admins, and
the card bundle, which any user adds to a dashboard. Both are plain custom elements with no
runtime framework, as in Home Keeper Library.

## Goals

- **G1. The URL is the state.** Every page of the tab has a URL.
- **G2. Same data everywhere.** The tab and the cards read 1 state from `get_state`.
- **G3. Translated.** Every label comes from the locale tables of the 17 languages.
- **G4. Safe markup.** All user content goes through `escapeHTML`.

## Non-goals

- Management in a card. A card has only the 2 controls of the use of a car.
- A router or a component framework.

## Design

### Bundles

- `frontend_assets.async_register` serves `frontend/dist/` at `/car_keeper_static`. Home
  Assistant serves a static path before authentication, so the path holds only the built
  bundles. CI builds them, and git ignores them.
- `cars-tab.js` defines `home-keeper-cars-tab`. The Home Keeper panel imports it.
- `car-keeper-card.js` defines `car-keeper-garage-card` and `car-keeper-car-card`, and adds
  both to the card picker.
- `card.async_register_card` adds the card bundle as a Lovelace resource of type `module`,
  or with `frontend.add_extra_js_url` when the resources are in YAML. Only 1 path runs.
  `card_resource.plan_card_resource` is the pure plan that leaves exactly 1 resource row.

### The tab

The Home Keeper panel sets `hass`, `narrow`, `route` and `host`. The `route` setter is the
only place that changes the view. The tab moves only with `host.navigate`: opening a page
pushes, and closing the Log dialog or deleting a car replaces.

| Path | View |
|---|---|
| `/` | The garage: a tile for each car with its status and its next job. |
| `/car/<id>` | 1 car: odometer, jobs, service history, car details. An unknown id shows the gone notice. |
| `/car/<id>/log` | The car with the Log service dialog open. It is the only dialog with a URL. |
| `/add` | Add car, in 3 steps: details, odometer, starter jobs. |
| `/settings` | The unit of a new car, the starter job overrides, and the car presets in Home Keeper with their status ([presets](presets.md)). |

`utils.parseRoute` reads the path, and `utils.buildPath` writes it. The filters of a view
are `;key=value` parameters on the last segment, because the host gives the tab only the
path. The tab reads `get_state`, and reads it again after each `changed` message of
`subscribe`. A change calls the websocket twin of a service (`api.call`). A refused call
shows the message of the server.

- `views.ts` makes the HTML of each view from the state. It is pure.
- `model.ts` holds the rows of each view and the 2 form state machines, Log service
  (`logReduce`) and Add car (`addReduce`). fast-check model tests run random action lists
  against each reducer and a small model.
- `dialog.confirmDestructive` asks before each delete. A store change during the question
  keeps the dialog open.
- The link to the appliance shows only for a path of Home Assistant (`views.safeLink`).
- Each control has a `data-k`, so a render keeps the focus, the caret and the typed text.

### The cards

The garage card shows each car with its odometer, its status and its next job. The car card
(`car_id`) shows 1 car and its jobs. It types a reading and marks a job done, and has no
other control. `max_height` is a number of pixels: above it, the list scrolls inside the
card. `min_height` is a number of pixels too, and keeps the card at least that tall. It is
not above `max_height`. `cleanConfig` in `card.ts` checks the config.

### Text and style

- `i18n.ts` picks the table of the Home Assistant language, then its base language, then
  English. `t` and `tn` fall back to English, then to the key.
- `styles.ts` defines `--ck-*` tokens from the Home Assistant theme variables.

## Trade-offs

- **Plain custom elements** over **a framework**: the bundles stay small and match Home
  Keeper Library.

## One-way doors

- The element names `home-keeper-cars-tab`, `car-keeper-garage-card` and
  `car-keeper-car-card`, and the card options `title`, `car_id`, `max_height` and
  `min_height`.
- The tab paths `/car/<id>`, `/car/<id>/log`, `/add` and `/settings`.
- The bundle names `cars-tab.js` and `car-keeper-card.js`, and the Lovelace resource path
  under `/car_keeper_static`.
