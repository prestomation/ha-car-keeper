# Overview

Car Keeper is a Home Assistant integration for the maintenance of the cars of a household.
It is a companion of [Home Keeper](https://github.com/prestomation/ha-home-keeper).

## What Car Keeper records

- **Cars.** Each car has a name, a fuel type and the fields of its papers.
- **Odometer.** Type the reading of a car, or bind it to a sensor of a car integration.
- **Jobs.** A job has a distance interval, a time interval or both.
- **Service records.** Each record has its date and reading. It also has the jobs, the shop
  and the cost.

## Who can do what

Every Home Assistant user can read all Car Keeper data. That includes the VIN and the plate
of each car and the cost of each service record. Every user can type an odometer reading
and log a service. Only an admin can add,
change or delete a car, a job or a setting.

| Place | Who | What |
|---|---|---|
| The **Cars** tab of the Home Keeper panel | Admins | Add and edit cars, jobs and settings. |
| Dashboard cards | Every user | See what is due. Type a reading. Mark a job done. |
| Services and entities | Every user and every automation | Read the data and log a service. |

## Next steps

1. Read [Installation](installation.md).
2. To use Car Keeper from an automation, read [Services and events](../automation/services.md).
