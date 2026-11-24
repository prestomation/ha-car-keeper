---
title: Car integrations in Home Assistant
summary: Which car integrations exist, what each can feed to a maintenance tracker, and which can become automatic presets.
---

# Car integrations in Home Assistant

This page is research for the design of Car Keeper. It answers 2 questions: which Home Assistant
integrations report data that helps car maintenance, and which of them can open maintenance tasks
with no setup.

## Method

- I read Home Assistant core at commit `0b790a5` (2026-11-24) and a shallow clone of each custom
  integration on the same day. The commit of each is in
  [car-integration-keys.md](car-integration-keys.md).
- I read `sensor.py`, `binary_sensor.py`, the string files and the manifest. I ran no code from
  these repositories.
- The page covers 79 sources. 62 have at least 1 fact that I read in source code. The others are
  marked "guess" or "not verified".
- The detail is in 3 places: the keys in [car-integration-keys.md](car-integration-keys.md), the
  reach and the status in [car-integration-reach.md](car-integration-reach.md), and the raw
  records in [data/](data/).

## Findings

1. **The odometer is the common input.** 54 of the 79 sources give an odometer. No other
   maintenance value is close to that. So the first release must work from the odometer alone.
2. **About 20 sources give a real service countdown.** These report the distance or the days to
   the next service: Volvo (core), Polestar, BMW CarData, Volkswagen (Carnet and ID), Audi,
   MySkoda, Porsche, Stellantis, Uconnect, Smart, Mazda, Toyota North America, OVMS, Drivvo and
   Spritmonitor. Kia and Hyundai give only the distance. Mercedes and Jaguar Land Rover give it
   only as attributes of another entity.
3. **Tesla gives almost nothing for service.** The 3 core integrations (`tesla_fleet`,
   `teslemetry`, `tessie`) give the odometer, 4 tyre pressures and tyre warning sensors. They give
   no service date, no battery state of health and no 12 V value.
4. **Many popular integrations give only the odometer.** Renault adds tyre pressures. Core Skoda,
   Toyota (Europe), NissanConnect and Cupra give the odometer and no service data.
5. **Oil life as a percentage is rare.** Ford (`oil`), General Motors through onstar2mqtt (`OIL
   LIFE`), Smartcar (`engine_oil`), Mazda (`dr_oil_deteriorate_level`) and WiCAN (`OIL_LIFE`) have
   it.
6. **Core changed in the last year.** `bmw_connected_drive` is now a stub that shows a repair
   issue, because BMW stopped third-party access. `volvooncall` and `mazda` are gone. A new core
   `skoda` integration and a new core `volvo` integration exist.
7. **Units and names are not consistent.** Polestar reports the odometer in metres. Renault
   reports tyre pressure in mbar. Tesla reports miles. MySkoda spells its key `milage`. So Car
   Keeper must read the unit of each entity and never assume km.
8. **Some integrations have no translation key.** BMW CarData, Volkswagen Carnet, Toyota North
   America, Smartcar and WiCAN name entities in other ways. A match by translation key does not
   work for them. They need an entity pattern, or the user selects the entity.
9. **Brand-neutral sources fill the gaps.** An OBD-II adapter (WiCAN, an ELM327 Bluetooth dongle)
   gives an odometer for many cars with no cloud service. Smartcar, DIMO and Enode give a fixed
   odometer key for many brands. A Bluetooth 12 V monitor (BM6) and Bluetooth tyre sensors add the
   values that most car clouds do not give.
10. **The Android Auto sensor is not reliable.** The companion app documents `car_odometer`, but
    only some cars report it. Apple CarPlay gives no car sensor.

## Home Keeper presets that exist

Home Keeper already ships a preset row for 5 car integrations, and 1 for a bike. I read them in
`declarative_presets_catalog.py` at Home Keeper commit `3ca25b9`.

| Domain | Duty | Shape | Keys | Limit |
|---|---|---|---|---|
| `fordconnect_query` | `oil_service` | `percent_low` | `oil` | 10% |
| `porscheconnect` | `annual_service`, `oil_service` | `life_low` | `main_service_time`, `oil_service_time` | 336 h |
| `smarthashtag` | `annual_service` | `life_low` | `days_to_service` | 336 h |
| `stellantis_vehicles` | `annual_service` | `life_low` | `days_before_maintenance` | 336 h |
| `myskoda` | `annual_service`, `oil_service` | `life_low` | `inspection`, `oil_service_in_days` | 336 h |
| `ha_bosch_ebike` | `bike_service` | `life_low` | `service_due_in_days` | 336 h |

Each row uses days or a percentage. No row uses a distance, because the `life_low` shape converts
only time units.

## What can be an automatic preset

I put each source in 1 of 4 classes. The matrix below gives the class of each.

- **Exists.** Home Keeper has the row (5 integrations).
- **Feasible.** A new catalog row works with the shapes that Home Keeper has: a time countdown
  (`life_low`), a percentage (`percent_low`) or a warning sensor (`alert`). 17 sources.
- **Car Keeper rule.** The entity helps, but a preset cannot use it. 37 sources.
- **None.** The source gives nothing for maintenance.

### Proposed new preset rows

Each row needs a check of the keys against the pinned upstream file, as the preset upkeep of Home
Keeper does. A duty with "(new)" needs a new task name in 17 languages.

| Domain | Duty | Shape | Keys | Limit |
|---|---|---|---|---|
| `volvo` | `annual_service` | `life_low` | `time_to_service` | 336 h |
| `volvo` | fluid levels (new) | `alert` | `oil_level_warning`, `brake_fluid_level_warning`, `washer_fluid_level_warning`, `coolant_level_warning` | state |
| `polestar_api` | `annual_service` | `life_low` | `days_to_service` | 336 h |
| `uconnect` | `annual_service` | `life_low` | `days_to_service` | 336 h |
| `audiconnect` | `annual_service`, `oil_service` | `life_low` | `service_inspection_time`, `oil_change_time` | 336 h |
| `volkswagen_we_connect_id` | `annual_service`, `oil_service` | `life_low` | `inspectionDue`, `oilInspectionDue` | 336 h |
| `fordpass` | `oil_service` | `percent_low` | `oil` | 10% |
| `mazda_cs` | `oil_service`, tyres (new) | `alert` | `mnt_oil_at_flg`, `mnt_tyre_at_flg` | on |
| `kia_uvo` | fluid levels (new), tyres (new) | `alert` | the `*_warning_is_on` binary sensors | on |
| `rivian` | brake fluid (new) | `alert` | `brake_fluid_low` | on |
| `subaru` | warning lamps (new) | `alert` | the warning lamp binary sensors | on |
| `mbapi2020` | fluid levels (new) | `alert` | `warningbrakefluid`, `warningwashwater`, `warningcoolantlevellow` | on |
| `bm6_ha` | 12 V battery (new) | `alert` | `crank_problem`, `charging_system_problem` | on |

The units of `service_inspection_time` (Audi) and `inspectionDue` (Volkswagen ID) are a guess: I
did not confirm that they are days. The Subaru lamps are off by default upstream.

### What needs Car Keeper logic

- **A distance countdown.** "Service in 1,500 km" needs a limit in the unit of the entity.
  `reading_low` compares a plain number, so the same row is wrong for a car that reports miles.
  Car Keeper knows the unit of each car and can compare correctly.
- **An odometer only.** The interval lives in the car record: "every 8,000 km or 6 months". This
  is the main case, and no preset can hold it.
- **A tyre pressure number.** The right limit depends on the car, and the unit is bar, psi, kPa or
  mbar.
- **An attribute.** Mercedes and Jaguar Land Rover put the countdown in attributes. A preset
  selects entities, not attributes of a named entity.
- **No translation key.** The user selects the entity in the Add car flow, and Car Keeper stores
  the entity id.

## Prior art

| Project | What it does | Lesson for Car Keeper |
|---|---|---|
| [Maintenance Supporter](https://github.com/iluebbe/maintenance_supporter) | A general tracker with a source-verified list of 39 car integrations, matched by translation key. | Match by translation key and record the verified commit. Go deeper on cars than its 2 or 3 general tasks. |
| [CARnet](https://github.com/aldoushx/ha-carnet-entretien) | A car logbook with a job catalog and a linked or typed odometer. | The same odometer model. Make each job an entity, stay local, and support miles. |
| [LubeLogger](https://github.com/hargata/lubelog) and its integration | A self-hosted vehicle logbook. The integration is read-only with fixed units. | Give "next due" as typed entities. Think of LubeLogger as an import source, not a competitor. |
| [Vehicle Service Manager](https://github.com/toxictody1337/vehicle-service-manager) | A due sensor for each job, in German and km only. | 1 due sensor for each job and 1 for the car are good. Do not ask the user for an automation to feed the odometer. |
| Drivvo and Spritmonitor integrations | Reminders from fuel log apps. | Users already know the set "distance left, days left, due". An odometer from a fuel log is old data. |
| Chore Helper and similar | Time schedules only. | "Distance or time, whichever comes first" is the reason for Car Keeper. |

## Matrix

"yes" is a fact from source code. "guess" is from docs or memory. The Preset column gives the
class from the section above.

### European brands

| Integration | Domain | Type | Odo | Service | Oil | Tyres | 12 V | Fluids | EV | Preset |
|---|---|---|---|---|---|---|---|---|---|---|
| Audi Connect | `audiconnect` | hacs | yes | yes | yes | – | – | yes | – | feasible |
| BMW CarData | `cardata` | hacs | yes | yes | yes | yes | yes | yes | yes | Car Keeper rule |
| BMW Connected Drive (core) | `bmw_connected_drive` | core | – | – | – | – | – | – | – | none |
| BYD Vehicle | `byd_vehicle` | hacs | yes | – | yes | yes | – | yes | – | Car Keeper rule |
| CarConnectivity + MQTT Home Assistant plugin | `mqtt (discovery)` | other | yes | yes | yes | – | – | yes | – | Car Keeper rule |
| JLR InControl | `jlrincontrol` | hacs | yes | yes | yes | yes | – | yes | – | Car Keeper rule |
| Mercedes MB2020 (MercedesME 2020) | `mbapi2020` | hacs | yes | yes | yes | yes | yes | yes | – | feasible |
| MG SAIC | `mg_saic` | hacs | yes | – | – | yes | yes | – | yes | Car Keeper rule |
| MySkoda | `myskoda` | hacs | yes | yes | yes | – | – | yes | – | exists |
| Polestar API | `polestar_api` | hacs | yes | yes | yes | – | – | yes | – | feasible |
| Porsche Connect | `porscheconnect` | hacs | yes | yes | yes | yes | – | – | – | exists |
| PSA Car Controller | `n/a` | hacs | – | – | – | – | – | – | – | none |
| Renault (core) | `renault` | core | yes | – | – | yes | – | – | – | Car Keeper rule |
| Seat/Cupra We Connect | `cupra_we_connect` | hacs | yes | – | – | – | – | – | – | Car Keeper rule |
| Skoda (core, new) | `skoda` | core | yes | – | – | – | – | – | – | Car Keeper rule |
| Smart #1/#3 (SmartHashtag) | `smarthashtag` | hacs | yes | yes | – | yes | – | yes | yes | exists |
| Stellantis Vehicles | `stellantis_vehicles` | hacs | yes | yes | yes | – | yes | yes | yes | exists |
| Volkswagen Connect (Carnet) | `volkswagencarnet` | hacs | yes | yes | yes | – | – | yes | – | Car Keeper rule |
| Volkswagen We Connect ID | `volkswagen_we_connect_id` | hacs | yes | yes | yes | – | – | – | – | feasible |
| Volvo (core, OAuth) | `volvo` | core | yes | yes | yes | yes | – | yes | yes | feasible |
| Volvo Cars (HACS, predecessor of core) | `volvo_cars` | hacs | yes | yes | yes | – | – | yes | yes | feasible |
| Volvo On Call (legacy core) | `volvooncall` | core | – | – | – | – | – | – | – | none |
| volvo2mqtt | `mqtt (discovery)` | other | yes | yes | – | yes | – | yes | – | Car Keeper rule |

### American and Asian brands

| Integration | Domain | Type | Odo | Service | Oil | Tyres | 12 V | Fluids | EV | Preset |
|---|---|---|---|---|---|---|---|---|---|---|
| Ford Connect Query (marq24) | `fordconnect_query` | hacs | yes | – | yes | yes | yes | yes | – | exists |
| FordPass (itchannel, original) | `fordpass` | hacs | yes | – | yes | yes | yes | yes | – | feasible |
| FordPass (marq24 fork) | `fordpass` | hacs | yes | – | yes | yes | yes | yes | – | feasible |
| Honda (HondaLink) | `unknown` | hacs | – | – | – | – | – | – | – | none |
| Kia Uvo / Hyundai Bluelink (Hyundai-Kia-Connect) | `kia_uvo` | hacs | yes | yes | yes | yes | yes | yes | yes | feasible |
| Lexus | `toyota_na / toyota` | hacs | – | – | – | – | – | – | – | none |
| Lucid | `lucid` | hacs | – | – | – | – | – | – | – | none |
| Mazda Connected Services (HACS successor of removed core mazda) | `mazda_cs` | hacs | yes | yes | yes | yes | – | yes | – | feasible |
| Mitsubishi | `unknown` | hacs | – | – | – | – | – | – | – | none |
| NIO | `unknown` | hacs | – | – | – | – | – | – | – | none |
| Nissan Leaf (Carwings) | `nissan_leaf` | core | – | – | – | – | – | – | yes | Car Keeper rule |
| NissanConnect (Kamereon, dan-r) | `nissan_connect` | hacs | yes | – | – | – | – | – | yes | Car Keeper rule |
| OnStar HACS integration | `onstar` | hacs | – | – | – | – | – | – | – | none |
| onstar2mqtt (BigThunderSR) | `mqtt` | other | yes | yes | yes | yes | yes | yes | yes | Car Keeper rule |
| Rivian (Unofficial) | `rivian` | hacs | yes | yes | – | yes | yes | yes | yes | feasible |
| Subaru | `subaru` | core | yes | – | yes | yes | – | yes | – | feasible |
| Tesla Custom Integration | `tesla_custom` | hacs | yes | – | – | yes | – | yes | – | Car Keeper rule |
| Tesla Fleet | `tesla_fleet` | core | yes | – | – | yes | – | – | yes | Car Keeper rule |
| TeslaMate (MQTT, manual YAML sensors) | `mqtt` | other | yes | – | – | yes | – | – | – | Car Keeper rule |
| TeslaMate HACS helper integrations | `unknown` | hacs | – | – | – | – | – | – | – | none |
| Teslemetry | `teslemetry` | core | yes | yes | – | yes | yes | yes | yes | Car Keeper rule |
| Tessie | `tessie` | core | yes | – | – | yes | – | – | yes | Car Keeper rule |
| Toyota (North America) | `toyota_na` | hacs | yes | yes | – | yes | – | – | – | Car Keeper rule |
| Toyota Connected Services (EU) | `toyota` | hacs | yes | – | – | – | – | – | – | Car Keeper rule |
| Uconnect (Jeep/Ram/Chrysler/Dodge/Fiat/Alfa/Maserati) | `uconnect` | hacs | yes | yes | yes | yes | yes | – | – | feasible |
| XPeng | `unknown` | hacs | – | – | – | – | – | – | – | none |

### Brand-neutral sources

| Integration | Domain | Type | Odo | Service | Oil | Tyres | 12 V | Fluids | EV | Preset |
|---|---|---|---|---|---|---|---|---|---|---|
| A Better Routeplanner (ABRP) | `abrp` | core | yes | – | – | – | – | – | yes | Car Keeper rule |
| Apple CarPlay (HA iOS app) | `mobile_app` | core | – | – | – | – | – | – | – | none |
| AutoPi | `none` | other | – | – | – | – | – | – | – | none |
| Autoskope | `autoskope` | core | – | – | – | – | – | – | – | none |
| BM2 battery monitor (BLE) | `ha_bm2monitor` | hacs | – | – | – | – | yes | – | – | Car Keeper rule |
| BM6 battery monitor (BLE) | `bm6_ha` | hacs | – | – | – | – | yes | – | – | feasible |
| Car Scanner ELM OBD2 app | `none` | other | – | – | – | – | – | – | – | none |
| DIMO | `dimo` | hacs | yes | – | yes | yes | yes | yes | yes | Car Keeper rule |
| Drivvo (fuel/expense log app) | `drivvo` | hacs | yes | yes | – | – | – | – | – | feasible |
| ELM327 BLE dongle (direct to HA Bluetooth) | `elm327_ble` | hacs | yes | – | yes | yes | yes | yes | yes | Car Keeper rule |
| Enode | `enode` | hacs | yes | – | – | – | – | – | yes | Car Keeper rule |
| ESPHome / ESP32 OBD and CAN approaches | `none` | other | guess | – | – | – | guess | – | – | Car Keeper rule |
| EV chargers / OCPP | `none` | core | – | – | – | – | – | – | – | none |
| Fuelio / Fuelly / aCar | `none` | other | – | – | – | – | – | – | – | none |
| High Mobility | `none` | other | – | – | – | – | – | – | – | none |
| Home Assistant Companion app: Android Auto car sensors | `mobile_app` | core | guess | – | – | – | – | – | guess | Car Keeper rule |
| Invoxia GPS tracker | `invoxia` | hacs | – | – | – | – | – | – | – | none |
| Ituran | `ituran` | core | yes | – | – | – | yes | – | – | Car Keeper rule |
| OBD2 BLE (dala318) | `obd2_ble` | hacs | yes | – | – | – | – | – | – | Car Keeper rule |
| OVMS (Open Vehicle Monitoring System) | `ovms` | hacs | yes | yes | – | yes | yes | – | yes | feasible |
| Smartcar | `smartcar` | hacs | yes | – | yes | yes | yes | – | yes | feasible |
| Spritmonitor | `spritmonitor` | hacs | yes | yes | – | – | – | – | – | Car Keeper rule |
| StarLine | `starline` | core | yes | – | – | – | yes | yes | – | Car Keeper rule |
| Torque (core, legacy) | `torque` | core | yes | – | – | – | – | – | – | Car Keeper rule |
| Torque OBD-II (updated, HACS) | `torque_obd` | hacs | yes | – | yes | – | yes | – | – | Car Keeper rule |
| TPMS BLE (aftermarket Bluetooth tyre sensors) | `tpms_ble` | hacs | – | – | – | yes | – | – | – | Car Keeper rule |
| Traccar Client (legacy webhook) | `traccar` | core | – | – | – | – | – | – | – | none |
| Traccar Server | `traccar_server` | core | yes | – | – | – | yes | – | – | Car Keeper rule |
| Victron BLE (SmartShunt / BMV / Smart Battery Sense / Orion) | `victron_ble` | core | – | – | – | – | yes | – | – | Car Keeper rule |
| WiCAN (MeatPi) OBD-II adapter | `wican` | hacs | yes | yes | yes | yes | – | – | – | Car Keeper rule |

## Not checked

1. Stars, open issues and release dates. The GitHub API was not available. I used commit dates and
   manifests.
2. Region limits and paid subscriptions. Most notes are from memory or a README.
3. Lucid, Honda, Lexus, Mitsubishi, NIO and XPeng: I found no integration to read.
4. The exact key strings of Subaru sensors, the Victron and BM2 enum values and the OVMS tyre
   keys.
5. JLR InControl on its v3 beta tags: I read the old default branch.
6. The units of some countdown entities, as the table of proposed rows says.
7. I ran no integration against a real car. Each fact is from source code or docs.
