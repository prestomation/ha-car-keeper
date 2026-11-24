# Car Keeper

[![HACS Validation][hacs-validation-shield]][hacs-validation]
[![HA Version][ha-version-shield]][ha-version]
[![License][license-shield]](LICENSE)

Car Keeper is a Home Assistant integration for the maintenance of the cars of a household.
It is a companion of [Home Keeper](https://github.com/prestomation/ha-home-keeper), as
[Home Keeper Library](https://github.com/prestomation/ha-home-keeper-library) is.

**Status: beta.** The first release is in progress.

## Features

- Keeps a list of your cars, each with an odometer that comes from a sensor or that you type.
- Tracks maintenance jobs that are due by distance, by time, or by the one that comes first.
- Keeps the service history: the reading, the shop and the cost.
- Makes a Home Keeper task for each job, so Home Keeper does the to-do list, the calendar, the
  notifications and the parts stock.
- Shows the cars in a **Cars** tab of the Home Keeper panel for admins, and on dashboard cards
  for every user.

## Documentation

| Document | Subject |
|---|---|
| [User guide](docs/guide/start/overview.md) | Installation and use |
| [docs/INTEGRATING.md](docs/INTEGRATING.md) | Services and events for automations and integrations |
| [docs/SECURITY.md](docs/SECURITY.md) | Who can read and write what |
| [docs/DEVELOPING.md](docs/DEVELOPING.md) | Tests and guardrails for contributors |
| [docs/design/architecture.md](docs/design/architecture.md) | The design docs |
| [IDEAS.md](IDEAS.md) | The roadmap and the open questions |

The idea comes from
[Home Keeper issue 599](https://github.com/prestomation/ha-home-keeper/issues/599).

## License

MIT. See [LICENSE](LICENSE).

[hacs-validation-shield]: https://img.shields.io/github/actions/workflow/status/prestomation/ha-car-keeper/hacs.yml?branch=main&label=HACS&style=for-the-badge
[hacs-validation]: https://github.com/prestomation/ha-car-keeper/actions/workflows/hacs.yml
[ha-version-shield]: https://img.shields.io/badge/Home%20Assistant-2026.1%2B-blue.svg?style=for-the-badge
[ha-version]: https://www.home-assistant.io/
[license-shield]: https://img.shields.io/github/license/prestomation/ha-car-keeper.svg?style=for-the-badge
