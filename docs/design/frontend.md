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
source_hash: d4c0143fccce
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

- Management in a card.
- A router or a component framework.

## Design

### Bundles

- `frontend_assets.async_register` serves `frontend/dist/` at `/car_keeper_static`. Home
  Assistant serves a static path before authentication, so the path holds only the built
  bundles. CI builds them, and git ignores them.
- `cars-tab.js` defines `home-keeper-cars-tab`. The Home Keeper panel imports it.
- `car-keeper-card.js` defines `car-keeper-garage-card` and adds it to the card picker.
- `card.async_register_card` adds the card bundle as a Lovelace resource of type `module`,
  or with `frontend.add_extra_js_url` when the resources are in YAML. Only 1 path runs.
  `card_resource.plan_card_resource` is the pure plan that leaves exactly 1 resource row.

### The tab

The Home Keeper panel sets `hass`, `narrow`, `route` and `host`. `utils.parseRoute` reads
the path, and `utils.buildPath` writes it. The filters of a view are `;key=value`
parameters on the last segment, because the host gives the tab only the path. The tab reads
`get_state` and reads it again after each `changed` message of `subscribe`.

### Text and style

- `i18n.ts` picks the table of the Home Assistant language, then its base language, then
  English. `t` and `tn` fall back to English, then to the key.
- `styles.ts` defines `--ck-*` tokens from the Home Assistant theme variables.

## Trade-offs

- **Plain custom elements** over **a framework**: the bundles stay small and match Home
  Keeper Library.

## One-way doors

- The element names `home-keeper-cars-tab` and `car-keeper-garage-card`.
- The bundle names `cars-tab.js` and `car-keeper-card.js`, and the Lovelace resource path
  under `/car_keeper_static`.
