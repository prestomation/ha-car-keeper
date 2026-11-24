---
title: Cars tab and cards
summary: The Cars tab in the Home Keeper panel, the dashboard cards, the routes, the text and the look.
status: planned
implements:
  - custom_components/car_keeper/frontend_assets.py
  - custom_components/car_keeper/card.py
  - custom_components/car_keeper/card_resource.py
  - custom_components/car_keeper/frontend/src/tab*.ts
  - custom_components/car_keeper/frontend/src/card*.ts
  - custom_components/car_keeper/frontend/src/api.ts
  - custom_components/car_keeper/frontend/src/utils.ts
  - custom_components/car_keeper/frontend/src/schedule.ts
  - custom_components/car_keeper/frontend/src/i18n.ts
  - custom_components/car_keeper/frontend/src/markup.ts
  - custom_components/car_keeper/frontend/src/styles.ts
related: [architecture, services-events, home-keeper-link]
---

# Cars tab and cards

The frontend is 2 ES modules: the Cars tab, which the Home Keeper panel loads for admins, and the
card bundle, which any user adds to a dashboard. Both are plain custom elements with no runtime
framework, as in the Library. The mockup in [docs/mockups/](../../mockups/car-keeper-mockup.html)
shows each screen at desktop and phone width, in light and dark.

## Goals

- **G1. The URL is the state.** Every page of the tab has a URL, and Back and Forward move inside
  the tab.
- **G2. Same data, same rules.** The tab and the cards read 1 projected state from `get_state`, so
  a card never has a field that its user cannot read.
- **G3. Works on a phone.** Each view works at phone width. To type the odometer and to log a
  service are built for a phone in a garage.
- **G4. It looks like Home Keeper.** The tab uses the theme variables of Home Assistant and the
  components of the Library tab.
- **G5. Translated.** Every label comes from the locale tables of the 17 languages.

## Non-goals

- Management in a card. A card types a reading and marks a job done, and no more.
- A router or a component framework.
- A photo from the web. The user uploads the photo of a car.

## Design

### The tab

The Home Keeper panel sets `hass`, `narrow`, `route` and `host` on `home-keeper-cars-tab`. The tab
moves only with `host.navigate`, and shows notices with `host.showToast`. A job links to its Home
Keeper task with `host.taskLink`, and a car to its appliance with `host.applianceLink`.

| Path | View |
|---|---|
| `/garage` (default) | The cars as cards: photo, odometer, next job, status. A status filter. The preset nudge. |
| `/cars/<id>` | Car detail: header, odometer, upcoming, service history, parts and stock, documents and dates, car settings. |
| `/cars/<id>/log` | The Log service dialog over the detail page. |
| `/add` | The Add car flow: source, car and entities, schedule. |
| `/upcoming`, `/history`, `/parts` | The same lists for all cars. |
| `/settings` | Units, privacy, reminders, Home Keeper, default schedule, data. |

Filters are `;key=value` parameters on the last segment, as in
`/history;car=crv;kind=oil;q=ballard`, because the host gives the tab only the path.

### Views

- **Upcoming rows.** A row has the job, its interval, 1 bar for each limit and the status. With 2
  limits the row marks the one that is first. `schedule.ts` is the same rule as `schedule.py`, and
  a shared fixture file tests both.
- **Odometer control.** For a typed odometer it is the main input. For a bound odometer it is
  read-only while the entity has a value, and it has a **Correct** action. A lower value shows the
  reason and what to do, not only "invalid".
- **Log service.** The user selects 1 or more jobs. The dialog fills the date, the odometer, the
  last shop and the parts of the jobs. On a phone it is a sheet from the bottom.
- **Add car.** Step 1 lists the devices that `detect_cars` returns, and "Enter by hand". Step 2
  shows the fields and each mapped entity with its value now. Step 3 lists the starter jobs for
  the fuel type, with a checkbox and both intervals, and the note to check the manual.
- **Parts and stock.** The stock control and the low-stock chip are the Home Keeper look. The
  numbers come from `home_keeper.list_assets`, and a change calls `home_keeper.adjust_part_stock`.
- **Preset review.** A dialog like the preset dialog of Home Keeper. Each row has the rule in
  plain words, the matched entities, the reading now against the limit, and its source: a Home
  Keeper preset or a Car Keeper rule.
- **Private fields.** The plate and the VIN have a lock icon. The tab is admin-only, so it shows
  them in full.

Each view is a free function that returns HTML, and `tab.ts` renders it and keeps the focus, as
the Library does. Dialogs are a separate layer, so a data push does not clear a form. All user
content goes through `escapeHTML`.

### The cards

| Card | Shows | Config keys |
|---|---|---|
| `car-keeper-garage-card` | 1 row for each car: status dot, name, odometer, next job. | `title`, `cars`, `min_height`, `max_height` |
| `car-keeper-card` | 1 car: the odometer, the next jobs with 1 slim bar each, a check button, the dates. A pencil types the odometer of a car with no sensor. | `car`, `title`, `show`, `min_height`, `max_height` |

`min_height` and `max_height` work as on the Home Keeper task card: the card grows to
`max_height`, then its list scrolls inside the card, with a fade at the bottom edge. Both cards
have a visual editor. A card calls `set_odometer` and `log_service` and no admin service.

### Delivery, text and style

- `frontend_assets.async_register` serves `frontend/dist/` at `/car_keeper_static`.
  `card.async_register_card` adds the card bundle as a Lovelace resource of type `module`, or with
  `frontend.add_extra_js_url` in YAML mode. Only 1 path runs.
- `i18n.ts` picks the table of the Home Assistant language, then its base language, then English.
  It formats a distance in the unit of the car and money in the currency of Home Assistant.
- `styles.ts` defines `--ck-*` tokens from the Home Assistant theme variables, with the same
  fallbacks as the `--hkl-*` tokens of the Library. The phone layout starts below 700 px, in CSS
  only. A status has a color and a word, never a color alone.

## Trade-offs

- **The due rule in TypeScript too** over **a status only from the server**: the tab can show the
  bars for a reading that the user is typing. The cost is 2 copies of the rule, which the shared
  fixtures hold together.
- **2 cards** over **1 card with modes**: each has a short config and a clear editor.
- **Read the whole state** over **query each view**: every list and filter works on local data.
  The design size is 20 cars.

## One-way doors

- The element names `home-keeper-cars-tab`, `car-keeper-card` and `car-keeper-garage-card`, and
  the bundle names.
- The tab paths and the `;key=value` filter keys, because a user can bookmark them.
- The card config keys.
- The Lovelace resource path under `/car_keeper_static`.
