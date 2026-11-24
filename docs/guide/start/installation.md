# Installation

Car Keeper is a custom integration for [HACS](https://hacs.xyz/).
It requires Home Assistant 2026.1 or later, and Home Keeper.

## Install Home Keeper first

1. Install Home Keeper with HACS, as its
   [installation steps](https://github.com/prestomation/ha-home-keeper#installation) say.
2. Restart Home Assistant.
3. Add the Home Keeper integration in **Settings → Devices & services → Add
   integration**.

The Cars tab needs Home Keeper version 0.35.0 or later.

## Install Car Keeper

1. In HACS, add `https://github.com/prestomation/ha-car-keeper` as a custom repository of
   the type **Integration**.
2. Download **Car Keeper** and restart Home Assistant.
3. Go to **Settings → Devices & services → Add integration**, and select **Car Keeper**.
4. Select the distance unit of a new car: kilometers or miles. The default comes from the
   unit system of Home Assistant.
5. Select **Submit**.

The Home Keeper panel then has a **Cars** tab. Open it from the Home Keeper entry in the
sidebar.

To change the unit of a new car later, open **Settings → Devices & services → Car
Keeper** and select **Configure**. A car that you added keeps its own unit.

## Setup messages

If Home Keeper is not ready, the setup stops with 1 of these messages:

| Message | What to do |
|---|---|
| Car Keeper requires Home Keeper. | Install Home Keeper from HACS, restart Home Assistant, then add Car Keeper again. |
| Add the Home Keeper integration first. | Add the Home Keeper integration, then add Car Keeper again. |
| Update Home Keeper to version 0.35.0 or later. | Update Home Keeper in HACS, restart Home Assistant, then add Car Keeper again. |

## Repair issues

If Home Keeper goes away after the setup, Car Keeper keeps its data. The cards, the
entities and the services still work. **Settings → Repairs** shows 1 of these issues:

- **Home Keeper is not installed.** Install Home Keeper from HACS and restart Home
  Assistant.
- **Home Keeper is not set up.** Add or enable the Home Keeper integration.
- **Home Keeper is too old.** Update Home Keeper.

While the issue shows, the Cars tab and the Home Keeper tasks are off. When Home Keeper is
ready again, the issue goes away. The tab and the tasks then come back with no restart.

## Data

Car Keeper is 1 JSON document in `.storage/car_keeper`. The document is in each Home
Assistant backup.
