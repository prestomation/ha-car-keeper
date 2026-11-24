# Car Keeper

Car Keeper is a planned Home Assistant integration for car maintenance. It is a companion of
[Home Keeper](https://github.com/prestomation/ha-home-keeper), as
[Home Keeper Library](https://github.com/prestomation/ha-home-keeper-library) is.

**Status: design.** No code exists yet. You cannot install it.

## What it will do

- Keep a list of your cars, each with an odometer that comes from a sensor or that you type.
- Track maintenance jobs that are due by distance, by time, or by the one that comes first.
- Keep the service history: the reading, the shop, the cost and the receipt.
- Make a Home Keeper task for each job, so Home Keeper does the to-do list, the calendar, the
  notifications and the parts stock.
- Show the cars in a **Cars** tab of the Home Keeper panel for admins, and on dashboard cards
  for every user.

## Read the design

| Document | Subject |
|---|---|
| [docs/design/architecture.md](docs/design/architecture.md) | Purpose, goals, modules and the index of the design docs |
| [docs/design/data-model.md](docs/design/data-model.md) | Cars, the odometer, jobs, services and the due rule |
| [docs/design/home-keeper-link.md](docs/design/home-keeper-link.md) | How a car and its jobs live in Home Keeper |
| [docs/design/services-events.md](docs/design/services-events.md) | Services, events, entities and privacy |
| [docs/design/frontend.md](docs/design/frontend.md) | The Cars tab and the cards |
| [docs/design/repository.md](docs/design/repository.md) | The scaffold, the tests and the CI |
| [docs/research/car-integrations.md](docs/research/car-integrations.md) | What 79 car data sources can feed |
| [docs/research/companion-presets.md](docs/research/companion-presets.md) | Can a companion add presets to Home Keeper |
| [docs/mockups/car-keeper-mockup.html](docs/mockups/car-keeper-mockup.html) | The UI mockup: open the file in a browser |
| [IDEAS.md](IDEAS.md) | The roadmap, the risks and the open questions |

The idea comes from
[Home Keeper issue 599](https://github.com/prestomation/ha-home-keeper/issues/599).

## License

MIT. See [LICENSE](LICENSE).
