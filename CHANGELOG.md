# Changelog

All changes to this project that a user can see are in this file. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). `manifest.json` `version`
is the single source of truth (see `RELEASE.md`).

## [0.1.0b1]

### Added

- **[Home Keeper companion](https://prestomation.github.io/ha-car-keeper/docs/guide/installation).**
  Car Keeper adds a Cars tab to the Home Keeper panel and shows a repair issue when Home
  Keeper is missing or too old.
- **[Garage of cars](https://prestomation.github.io/ha-car-keeper/docs/guide/garage).**
  Add each car of the household with its make, model, fuel, VIN, plate and distance unit.
  A new car can start with common jobs for its fuel type, which you check against the
  manual.
- **[Odometer for each car](https://prestomation.github.io/ha-car-keeper/docs/guide/odometer).**
  Type the odometer reading, or let Car Keeper follow an odometer sensor of the car. A
  reading cannot go down, and a sensor that goes down twice shows a repair issue.
- **[Due jobs](https://prestomation.github.io/ha-car-keeper/docs/guide/jobs).** Each
  job is due at its distance or its time, whichever comes first. Car Keeper warns you
  1,000 km (600 miles) or 30 days before, and you can change this for each car or job.
- **[Service log](https://prestomation.github.io/ha-car-keeper/docs/guide/jobs).** Log
  a service with its date, reading, shop and cost, and the jobs that it did. Each user of
  Home Assistant can log a service and read the full history.
- **[Car entities](https://prestomation.github.io/ha-car-keeper/docs/guide/overview).**
  Each car gets an odometer sensor, the next due distance and date, a status sensor, an
  overdue binary sensor and a to-do list of the due jobs. A check on the to-do list logs
  the service.
- **[Dashboard cards](https://prestomation.github.io/ha-car-keeper/docs/guide/cards).**
  The garage card shows each car with its status and its next job. The car card lets any
  user type a reading or mark a job done. Each card can have a minimum and a maximum height.
- **[Car Keeper services](https://prestomation.github.io/ha-car-keeper/docs/guide/services).**
  An automation can type a reading or log a service with the same rules as the tab.
  Events tell an automation when a job is due soon or overdue.
- **[Home Keeper reminders](https://prestomation.github.io/ha-car-keeper/docs/guide/home-keeper).**
  Each car is an appliance in Home Keeper, and each job is a task with the reminders of
  Home Keeper. A job done in Home Keeper logs a service in Car Keeper, and a service in Car
  Keeper marks the task done.
- **[Parts and stock](https://prestomation.github.io/ha-car-keeper/docs/guide/home-keeper).**
  A job can take parts of a Home Keeper appliance, such as an oil filter. Home Keeper takes
  them off the stock when the job is done.
- **[Car integration presets](https://prestomation.github.io/ha-car-keeper/docs/guide/presets).**
  Home Keeper 0.38.0b5 and later get presets for 12 car integrations, such as Volvo, Kia
  and Mercedes-Benz. A preset makes a Home Keeper task when the car reports a service due
  soon, low oil life or a warning.
