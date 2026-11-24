---
title: Ideas
summary: The roadmap of Car Keeper, what comes after the first release, the risks, the one-way doors and the open questions.
---

# Ideas

Nothing in this file is built. The design of the first release is in
[docs/design/](docs/design/architecture.md).

## Roadmap

### Phase 0: repository

1. Scaffold from the integration template and copy the Library parts
   ([repository](docs/design/repository.md)).
2. Get every test tier and every CI job green with an empty integration.

### Phase 1: first release

1. Cars with a typed or bound odometer, and the odometer sensor of each car.
2. Jobs with a distance and a time interval, the due rule, and the starter jobs.
3. Log service with many jobs, the reading, the shop and the cost.
4. The Home Keeper link: the tab, the repair issue, a managed appliance for each car and a managed
   task for each job, with the sync both ways.
5. The Cars tab: garage, car detail, Add car with entity detection, Log service, settings.
6. The 2 cards, the summary entities and the to-do list of each car.
7. Private fields and the projection tests.
8. Export and import through Home Keeper, diagnostics, 17 languages, a guide and screenshots.

### Phase 2: after the first release

1. Parts and stock in the tab, with parts used on a service.
2. Documents with files, and receipt photos.
3. Live-reading rules (tyre pressure, distance to service) and the preset review dialog.
4. Car rows for the Home Keeper preset catalog, by pull request to Home Keeper
   ([companion-presets](docs/research/companion-presets.md)).
5. The Upcoming, History and Parts lists for all cars.

### Later

1. **Fuel log.** Fill-ups with the reading, the volume and the price. Consumption and cost per
   distance. A fill-up also feeds the odometer.
2. **Trip log.** Business and private distance. It needs a strong privacy model first.
3. **More meters.** Engine hours for a mower, a boat or a generator. This is the shared meter idea
   of Home Keeper issue 598.
4. **Other vehicles.** A type on the car record: motorbike, trailer, bike. Each has its own
   starter jobs.
5. **Tyre sets.** Summer and winter sets with the distance of each, and a job to change them.
6. **Model packs.** Starter jobs for 1 model, which a community keeps. Only with a clear source
   and license.
7. **Import from logbook apps.** CSV files of LubeLogger, Fuelio, Drivvo and Spritmonitor.
8. **Use the device of the car integration.** Put the Car Keeper entities and the appliance on the
   device that Tesla or Volvo made, for 1 device page.
9. **Recall and inspection lookups** by VIN, from a public service. It sends the VIN out, so it
   must be an explicit choice.
10. **A forecast date in the Home Keeper calendar** for a distance job. It needs a change in Home
    Keeper.
11. **A preset extension point in Home Keeper**, if a second companion needs it.
12. **Shared cost reports** with the Home Keeper spend summary.

## Risks

1. **Two places hold the state of a job.** Car Keeper has `last_done`, and the Home Keeper task
   has a baseline and completions. A missed event makes them differ. The reconcile pass is the
   answer, and it needs strong tests.
2. **The display unit of the odometer sensor.** A user can set a display unit on a sensor. The
   Home Keeper tasks read the attribute `reading`, which does not change. I did not test that a
   usage task reads an attribute.
3. **An odometer from a car cloud can stop.** BMW stopped third-party access in 2025. A car must
   go back to a typed odometer with no loss of data.
4. **A wrong starter interval can harm an engine.** The tab must say that the defaults are not the
   schedule of the maker, at the place where the user accepts them.
5. **Private fields leak in small places**: an event payload, a log line, a diagnostics file, a
   device field. The projection test must walk each of them.
6. **Home Keeper changes.** The link uses `managed_by`, usage tasks, `set_task_meter` and the
   panel tab API. A Docker tier against Home Keeper `main` finds a break early.
7. **An appliance of the kind `existing` with `managed_by`.** I read that both exist. I did not
   test them together.
8. **The effort for 17 languages** for each new string, from the first release.

## One-way doors

The design docs list them where they apply. The ones to decide first:

1. The domain `car_keeper` and the tab id `cars`.
2. The storage document and the export format.
3. The `source` namespace and the `managed_by` block that Home Keeper stores on each task and
   appliance.
4. The service and event names.
5. The entity unique ids and the attribute `reading`.
6. The values in the unit of the car, not in km.

## Open questions

1. Does the schedule live in Car Keeper with a mirror task, as designed, or only in Home Keeper
   tasks?
2. Is `log_service` open to every user, or admin-only?
3. Is the cost on 1 Home Keeper completion, or divided across the jobs?
4. Does a date job (registration, insurance) use a one-off task, or a yearly fixed task?
5. What is the lowest Home Keeper version to support?
6. Do the car preset rows go to Home Keeper before or after the first release of Car Keeper?
7. Is the name of the tab "Cars" or "Vehicles"?
8. Does a user who is not an admin see the shop and the notes of a service?
