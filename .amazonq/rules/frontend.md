---
title: Frontend rules
summary: Rules for the Cars tab and the cards - routing through the host, markup, bundles, dialogs, i18n, layout and Home Assistant elements.
---

# Frontend rules

How the tab and the cards work is in [frontend](../../docs/design/frontend.md).

## Routing

- **The URL is the source of truth.** Every page of the tab maps to a path under
  `/home-keeper/cars`. The `route` setter is the only place that changes the view state.
- **Navigate only with `host.navigate(path, {replace})`.** The Home Keeper panel owns
  the browser history, so the tab never calls `history.pushState`. Opening a detail
  pushes. Closing a detail or deleting a car replaces, so Back moves inside the tab.
- Keep `parseRoute` and `buildPath` pure in `utils.ts`, so they unit-test and round-trip.
  An unknown path falls back to the garage. A detail URL for a deleted car shows the
  gone notice.
- **The filters of a view are `;key=value` parameters on the last path segment.** The
  Home Keeper host gives the tab only the path and drops a `?query`. A default value is
  left out of the URL.
- **A new URL segment keeps old URLs working.** A user can bookmark any tab URL.
- Dialogs are not deep-linked, except the Log service dialog at `/cars/<id>/log`.

## Markup and text

- Escape all user content with `escapeHTML` before it goes into `innerHTML`.
- All UI text comes from `t()` and `tn()` in `i18n.ts`. A lookup falls back to English and
  then to the raw key, so a missing translation never renders `undefined`.
- Every control has a stable `data-k` attribute, so a render keeps the focus, the caret
  and the typed text.

## Destructive actions

- **Each delete and each import asks first, in the shared `confirmDestructive` dialog.**
  The dialog names the record and what goes with it. There is no undo, so the question
  comes before the call.
- `frontend/test/destructive-scan-parity.test.js` scans the source for each call of a
  function that deletes, removes or imports. A call outside a `confirmDestructive` call
  fails, unless the allowlist in that test names it with a reason.

## Bundles and the cards

- 2 ES module bundles ship from `frontend/dist/` at `/car_keeper_static`: the tab
  (`cars-tab.js`, loaded by the Home Keeper panel) and the cards (`car-keeper-card.js`).
  Each URL carries a content hash in `?v=`.
- **Deliver the card bundle by 1 path only**: a Lovelace resource, or
  `frontend.add_extra_js_url` when the resources are in YAML or the resource write fails
  (`card.py`). Both paths together are a race in the scoped element registry of Home
  Assistant 2026.9.
- The cards work for every user. A card types a reading and marks a job done, and shows no
  other control.
- On a cold frontend a card element can upgrade after the dashboard renders. The e2e
  helper `openCard` retries with a reload. Do not remove the retry.
- **Never tear down the tab registration or the card resource on unload.** Only the Home
  Keeper link removes the tab, when Home Keeper goes away. Only `async_remove_entry`
  removes the card resource.
- `max_height` is a number of pixels. Above it, the list of a card scrolls inside the card.
  With no `max_height`, the card grows with its content.

## Layout

- **Only CSS picks the layout.** Breakpoints are viewport `@media` queries. The phone
  layout starts below 700 px. Nothing in a render function reads the viewport.
- Review each changed surface at desktop and phone width
  ([pr-workflow.md](pr-workflow.md#screenshots-desktop-and-phone)).
- State shown by color has a text equivalent.
- Do not declare a widget role that you have not implemented.

## Home Assistant elements

- **Use only HA elements that the Home Keeper panel page registers.** Check with
  `customElements.get('<tag>')` in the e2e container. Otherwise build from plain DOM and
  theme variables.
- **Probe a real element before you design against it.** `observedAttributes` tells you
  what it still reads. Assert on rendered pixels, not markup, where HA draws.
- Every style rule reads a `--ck-*` token, and each token resolves to a Home Assistant
  theme variable with a literal color only as the fallback.
