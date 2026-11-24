---
title: Ideas
summary: The work of Car Keeper that is not built yet, the decisions for the first release, the risks and the one-way doors.
---

# Ideas

Nothing in this file is built. The design of the parts that are built is in
[docs/design/](docs/design/architecture.md). The approved design of the first release is in
[docs/research/first-release/](docs/research/first-release/architecture.md).

## First release

The first release is `0.1.0b1`. These parts are not built yet:

1. Cars with a typed or bound odometer, and the odometer sensor of each car.
2. Jobs with a distance and a time interval, the due rule, and the starter jobs.
3. Log service with many jobs, the reading, the shop and the cost.
4. The sensors, the binary sensor and the to-do list of each car.
5. A managed Home Keeper appliance for each car and a managed task for each job, with the
   sync both ways.
6. The Cars tab: garage, car detail, Add car, Log service, settings.
7. The garage card and the car card, with `min_height` and `max_height`.
8. Export and import through Home Keeper.
9. The car presets through the Home Keeper `register_presets` service.

### Decisions

| Question | Answer |
|---|---|
| Domain and tab | `car_keeper`, the tab "Cars" at `/home-keeper/cars`. |
| Who owns the schedule | Car Keeper owns the jobs and the history. Each job is also a managed Home Keeper task. |
| Distance jobs | A Home Keeper usage task on the odometer sensor of Car Keeper. |
| Cars in Home Keeper | Each car is a managed Home Keeper appliance. |
| Presets | The Home Keeper `register_presets` service. Car Keeper rules for what no preset shape can do. |
| Units | 1 unit for each car. Values are stored in that unit, and converted 1 time on a change. |
| Warning window | 1,000 km (600 miles) or 30 days, for each car. |
| Privacy | Every read is open to every user. Record management is admin-only. `set_odometer` and `log_service` are open. |
| Cost | On the Car Keeper service and on 1 Home Keeper completion. |
| Starter intervals | Common intervals by fuel type, with a note to check the manual. |
| Photo | Only from an upload of the user. |

## After the first release

1. **Preset nudge.** A review dialog that offers the presets that match the device of a car.
2. **Document files.** Receipts, photos and documents as files.
3. **Live readings.** Tyre pressure and distance-to-service rules from the car integration.
   Each rule is 1 managed triggered task that the condition arms and clears.
4. **The Upcoming, History and Parts lists** for all cars.
5. **Service book as a PDF.** The history of 1 car as a file to give to a buyer.

## Later

1. **Fuel log.** Fill-ups with the reading, the volume and the price. Consumption and cost per
   distance. A fill-up also feeds the odometer.
2. **Trip log.** Business and private distance.
3. **More meters.** Engine hours for a mower, a boat or a generator. This is the shared meter
   idea of Home Keeper issue 598.
4. **Other vehicles.** A type on the car record: motorbike, trailer, bike. Each has its own
   starter jobs.
5. **Tyre sets.** Summer and winter sets with the distance of each, and a job to change them.
6. **Model packs.** Starter jobs for 1 model, which a community keeps. Only with a clear source
   and license.
7. **Import from logbook apps.** CSV files of LubeLogger, Fuelio, Drivvo and Spritmonitor.
8. **Use the device of the car integration.** Put the Car Keeper entities and the appliance on
   the device that Tesla or Volvo made, for 1 device page.
9. **Recall and inspection lookups** by VIN, from a public service. It sends the VIN out, so it
   must be an explicit choice.
10. **A forecast date in the Home Keeper calendar** for a distance job. It needs a change in
    Home Keeper.
11. **Shared cost reports** with the Home Keeper spend summary.

## Quality scale ledger

Car Keeper uses the practices of the Platinum quality scale, but `manifest.json` declares no
tier. A tier needs a `quality_scale.yaml` with a reason for each rule.

## Risks

1. **Two places hold the state of a job.** Car Keeper has `last_done`, and the Home Keeper task
   has a baseline and completions. A missed event makes them differ. The reconcile pass is the
   answer, and it needs strong tests.
2. **The display unit of the odometer sensor.** A user can set a display unit on a sensor. The
   Home Keeper tasks read the attribute `reading`, which does not change.
3. **An odometer from a car cloud can stop.** A car must go back to a typed odometer with no
   loss of data.
4. **A wrong starter interval can harm an engine.** The tab must say that the defaults are not
   the schedule of the maker, at the place where the user accepts them.
5. **Home Keeper changes.** The link uses `managed_by`, usage tasks, `set_task_meter` and the
   panel tab API. A Docker tier against Home Keeper `main` finds a break early.
6. **The effort for 17 languages** for each new string.
