---
sidebar_position: 1
slug: /intro
title: Introduction
---

# Car Keeper

Car Keeper is a Home Assistant integration for the maintenance of the cars of a household.
It records the odometer and the service history of each car.

**Car Keeper requires [Home Keeper](https://github.com/prestomation/ha-home-keeper).**
Install and set up Home Keeper first. Car Keeper adds a **Cars** tab to the Home Keeper
panel.

## Features

- **Jobs.** A job has a distance interval, a time interval or both. It comes due at the first
  limit.
- **Odometer.** Type the reading, or bind the odometer to a sensor of a car integration.
- **Service history.** Each service has the date, the reading, the shop and the cost.
- **Home Keeper tasks.** Each job is a Home Keeper task with reminders and parts.
- **Cards and entities.** Every user gets dashboard cards and the sensors of each car.

## Next steps

- Read the [overview](/docs/guide/overview), then [Installation](/docs/guide/installation).
- To use Car Keeper from an automation or another integration, read the
  [Developer Guide](/developer/integrating).
