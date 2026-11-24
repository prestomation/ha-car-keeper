---
title: Car integration reach and status
summary: How each car integration reaches the car, its limits and its maintenance status.
---

# Car integration reach and status

This page gives the reach and the status behind [car-integrations.md](car-integrations.md). I
could not read stars, open issues or release dates: the GitHub API was not available. The status
comes from the last commit date and the manifest. Region limits are mostly from memory or a
README, so read them as guesses.

## European brands

| Integration | Type | Reach | Limits | Status | Source |
|---|---|---|---|---|---|
| Audi Connect (`audiconnect`) | hacs | Audi/CARIAD cloud polling | region option (DE/US/CA/CN - guess) | active; stars/issues not checked | https://github.com/audiconnect/audi_connect_ha |
| BMW CarData (`cardata`) | hacs | Official BMW CarData: OAuth device flow + MQTT stream (cloud_push) +… | EU-registered cars only (per core removal text); README: CarData portal unavailable in some countries (e.g. Finland) | active (commit 2 days before research); stars/issues not checked (GitHub API blocked) | https://github.com/kvanbiesen/bmw-cardata-ha |
| BMW Connected Drive (core) (`bmw_connected_drive`) | core | none (was cloud polling via bimmer_connected) | n/a | REMOVED: only a stub that raises repair issue 'integration_removed'; no platforms left | https://github.com/home-assistant/core |
| BYD Vehicle (`byd_vehicle`) | hacs | BYD app cloud API (reverse engineered), polling | country selectable in config (README) | very active; stars not checked | https://github.com/jkaberg/hass-byd-vehicle |
| CarConnectivity + MQTT Home Assistant plugin (`mqtt (discovery)`) | other | Standalone Python service with connectors (VW, Skoda, Seat/Cupra, Aud… | depends on connector | maintained (not a HACS integration: standalone daemon/add-on publishing MQTT discovery); stars not checked | https://github.com/tillsteinbach/CarConnectivity-plugin-mqtt_homeassistant |
| JLR InControl (`jlrincontrol`) | hacs | JLR InControl cloud polling (jlrpy) | EU/ROW + China option; known breakage not checked | default branch stale since 2024-03; tags up to v3.0.0beta7 exist; stars not checked | https://github.com/msp1974/homeassistant-jlrincontrol |
| Mercedes MB2020 (MercedesME 2020) (`mbapi2020`) | hacs | Mercedes me cloud: OAuth + websocket push (protobuf) | Region selectable (EU/NA/AP/China per README - guess, not re-read) | active; stars/issues not checked | https://github.com/ReneNulschDE/mbapi2020 |
| MG SAIC (`mg_saic`) | hacs | SAIC iSMART cloud polling | EU / AU / ROW regions (guess) | active; stars not checked | https://github.com/ad-ha/mg-saic-ha |
| MySkoda (`myskoda`) | hacs | MySkoda cloud (REST + MQTT push) | EU | active; stars/issues not checked | https://github.com/skodaconnect/homeassistant-myskoda |
| Polestar API (`polestar_api`) | hacs | Polestar cloud GraphQL (pypolestar), polling | not checked | maintained; stars not checked | https://github.com/pypolestar/polestar_api |
| Porsche Connect (`porscheconnect`) | hacs | My Porsche cloud polling (pyporscheconnectapi) | not checked | active; stars not checked | https://github.com/CJNE/ha-porscheconnect |
| PSA Car Controller (`n/a`) | hacs | Standalone app (Docker / HA add-on flobz/psacc-ha) with own REST API… | ex-PSA EU | maintained standalone app; NOT a HA integration | https://github.com/flobz/psa_car_controller |
| Renault (core) (`renault`) | core | My Renault / Kamereon cloud polling | Renault + Dacia, EU mostly; endpoints vary per model | in core, quality_scale platinum, lib renault-api==0.6.3, codeowner @epenet | https://github.com/home-assistant/core |
| Seat/Cupra We Connect (`cupra_we_connect`) | hacs | Cupra/Seat cloud via weconnect-cupra lib, polling | EU | low activity; stars not checked | https://github.com/daernsinstantfortress/cupra_we_connect |
| Skoda (core, new) (`skoda`) | core | Skoda public API, cloud polling | not checked | in core, quality_scale bronze, lib skoda-public-api==1.4.0 | https://github.com/home-assistant/core |
| Smart #1/#3 (SmartHashtag) (`smarthashtag`) | hacs | Smart (Geely) cloud polling via pysmarthashtag | EU | active; stars not checked | https://github.com/DasBasti/SmartHashtag |
| Stellantis Vehicles (`stellantis_vehicles`) | hacs | Stellantis/PSA Connected Car API (OAuth via brand app) + MQTT for com… | Peugeot/Citroen/DS/Opel/Vauxhall (ex-PSA) EU | active; stars not checked | https://github.com/andreadegiovine/homeassistant-stellantis-vehicles |
| Volkswagen Connect (Carnet) (`volkswagencarnet`) | hacs | VW cloud (We Connect / CARIAD) polling | EU-centric (README region limits not re-read: guess) | active; stars/issues not checked | https://github.com/robinostlund/homeassistant-volkswagencarnet |
| Volkswagen We Connect ID (`volkswagen_we_connect_id`) | hacs | VW cloud via weconnect python lib, polling | EU (ID. family) - guess | looks stale (no commit for ~13 months); stars/issues not checked | https://github.com/mitch-dc/volkswagen_we_connect_id |
| Volvo (core, OAuth) (`volvo`) | core | Official Volvo Cars public API (OAuth2 application_credentials), clou… | Only models/regions supported by Volvo's public API | in core, quality_scale platinum, lib volvocarsapi==0.6.0, codeowner @thomasddn | https://github.com/home-assistant/core |
| Volvo Cars (HACS, predecessor of core) (`volvo_cars`) | hacs | Volvo public API OAuth | as core | UNMAINTAINED: README says no longer maintained, replaced by core 'volvo' | https://github.com/thomasddn/ha-volvo-cars |
| Volvo On Call (legacy core) (`volvooncall`) | core | n/a | n/a | REMOVED: directory homeassistant/components/volvooncall does not exist at this commit | https://github.com/home-assistant/core |
| volvo2mqtt (`mqtt (discovery)`) | other | Add-on/Docker: Volvo API -> MQTT discovery | as Volvo API | commits in 2026; README deprecation not found by grep; stars not checked | https://github.com/Dielee/volvo2mqtt |

## American and Asian brands

| Integration | Type | Reach | Limits | Status | Source |
|---|---|---|---|---|---|
| Ford Connect Query (marq24) (`fordconnect_query`) | hacs | Official Ford developer 'FordConnect Query' API via OAuth application… | where Ford's developer API is offered (EU focus is a guess) | active (commit 2026-11-23); stars not checked (GitHub API not enabled) | https://github.com/marq24/ha-fordconnect-query |
| FordPass (itchannel, original) (`fordpass`) | hacs | FordPass cloud polling (reverse-engineered) | global; reported broken after Ford auth changes (guess) | effectively unmaintained since mid-2024; superseded by marq24 fork; stars not checked (GitHub API not enabled) | https://github.com/itchannel/fordpass-ha |
| FordPass (marq24 fork) (`fordpass`) | hacs | FordPass app cloud API (reverse-engineered), iot_class cloud_push (we… | global Ford/Lincoln accounts; unofficial API, login flow has broken repeatedly (guess) | very active (commit 2026-11-23); stars/issues not checked (GitHub API not enabled) | https://github.com/marq24/ha-fordpass |
| Honda (HondaLink) (`unknown`) | hacs | not checked | not checked | not checked | – |
| Kia Uvo / Hyundai Bluelink (Hyundai-Kia-Connect) (`kia_uvo`) | hacs | Hyundai Bluelink / Kia Connect / Genesis Connected cloud polling | EU, USA, Canada, China, Australia/NZ, India, Brazil (region list is a guess from memory); requires active connected-ser… | active (commit 2026-11-23); stars/issues not checked (GitHub API not enabled) | https://github.com/Hyundai-Kia-Connect/kia_uvo |
| Lexus (`toyota_na / toyota`) | hacs | not checked | not checked | not checked | – |
| Lucid (`lucid`) | hacs | not checked | not checked | not checked | – |
| Mazda Connected Services (HACS successor of removed core mazda) (`mazda_cs`) | hacs | MyMazda cloud API polling (bundled pymazda fork) | North America, Europe, Japan accounts (guess); legal/DMCA risk, may break without notice | active; core 'mazda' is a removed stub at 0b790a5 (only an integration_removed repair issue, DMCA); stars not… | https://github.com/fano0001/home-assistant-mazda |
| Mitsubishi (`unknown`) | hacs | not checked | not checked | not checked | – |
| NIO (`unknown`) | hacs | not checked | not checked | not checked | – |
| Nissan Leaf (Carwings) (`nissan_leaf`) | core | Nissan Carwings / NissanConnect EV legacy cloud polling | pre-2019 Leaf/e-NV200 only; Nissan has shut down 2G/3G services and the legacy API in several regions, so largely broke… | core, quality_scale legacy, YAML-only | https://github.com/home-assistant/core |
| NissanConnect (Kamereon, dan-r) (`nissan_connect`) | hacs | NissanConnect Services (Kamereon) cloud polling | Europe only (post-2019 Leaf, Ariya, Qashqai, Juke...); no North America | maintained; stars not checked (GitHub API not enabled) | https://github.com/dan-r/HomeAssistant-NissanConnect |
| OnStar HACS integration (`onstar`) | hacs | not checked | not checked | not checked | – |
| onstar2mqtt (BigThunderSR) (`mqtt`) | other | Docker/add-on service calling the OnStar cloud API (OnStarJS, API v3)… | US and Canada OnStar accounts; active OnStar plan required; each diagnostics request wakes the car (rate limits); API v… | active; also packaged as HA add-on (BigThunderSR/homeassistant-addons-onstar2mqtt); stars not checked (GitHub… | https://github.com/BigThunderSR/onstar2mqtt |
| Rivian (Unofficial) (`rivian`) | hacs | Rivian cloud GraphQL API with websocket push (iot_class cloud_push),… | US/Canada (and wherever Rivian accounts exist); unofficial API | active; stars not checked (GitHub API not enabled) | https://github.com/bretterer/home-assistant-rivian |
| Subaru (`subaru`) | core | Subaru STARLINK (MySubaru) cloud polling | USA and Canada only; odometer needs Safety Plus, tyre pressures/health need Security Plus subscription and Gen2+ telema… | core, bronze quality scale, maintained (@G-Two, @jpettitt) | https://github.com/home-assistant/core |
| Tesla Custom Integration (`tesla_custom`) | hacs | Tesla owner/Fleet API cloud polling via teslajsonpy (optional Fleet A… | global; legacy owner-API access increasingly restricted by Tesla (guess) | commits in Nov 2026; stars/issues not checked (GitHub API not enabled) | https://github.com/alandtse/tesla |
| Tesla Fleet (`tesla_fleet`) | core | Tesla Fleet API cloud polling (OAuth application credentials, own dev… | global; Tesla Fleet API is pay-per-use beyond the free monthly credit | core, maintained (codeowner @Bre77) | https://github.com/home-assistant/core |
| TeslaMate (MQTT, manual YAML sensors) (`mqtt`) | other | Self-hosted TeslaMate logger publishes to MQTT topics teslamate/cars/… | global, self-hosted, free | active project; stars not checked (GitHub API not enabled) | https://github.com/teslamate-org/teslamate |
| TeslaMate HACS helper integrations (`unknown`) | hacs | not checked | not checked | not checked | – |
| Teslemetry (`teslemetry`) | core | Teslemetry cloud (proxy of Tesla Fleet API + Fleet Telemetry streamin… | global; paid Teslemetry subscription required | core, platinum quality scale, maintained (@Bre77) | https://github.com/home-assistant/core |
| Tessie (`tessie`) | core | Tessie cloud API polling | global; paid Tessie subscription required | core, silver quality scale, maintained (@Bre77, @stx) | https://github.com/home-assistant/core |
| Toyota (North America) (`toyota_na`) | hacs | Toyota North America OneApp cloud API (toyota-na==2.1.1), polling | USA/Canada/Mexico; also works for Lexus NA accounts (guess). Remote features need subscription; these sensors are flagg… | maintained at low pace; stars not checked (GitHub API not enabled) | https://github.com/widewing/ha-toyota-na |
| Toyota Connected Services (EU) (`toyota`) | hacs | Toyota Connected Services Europe cloud polling via mytoyota (>=2.1.4,… | Europe only (MyToyota/MyT). Lexus EU not supported here (guess) | slow / little activity since Apr 2025; stars not checked (GitHub API not enabled) | https://github.com/DurgNomis-drol/ha_toyota |
| Uconnect (Jeep/Ram/Chrysler/Dodge/Fiat/Alfa/Maserati) (`uconnect`) | hacs | Stellantis Uconnect/Mopar cloud polling (reverse-engineered brand app… | US, Canada, EU, Asia, LATAM (Brazil) per README; needs active connected-services account | active; stars not checked (GitHub API not enabled) | https://github.com/hass-uconnect/hass-uconnect |
| XPeng (`unknown`) | hacs | not checked | not checked | not checked | – |

## Brand-neutral sources

| Integration | Type | Reach | Limits | Status | Source |
|---|---|---|---|---|---|
| A Better Routeplanner (ABRP) (`abrp`) | core | Cloud push: ABRP account telemetry (fed to ABRP by OBD dongle/app or… | worldwide, EV | core at local HEAD 0b790a5 (config flow, quality_scale bronze, codeowner @mtandersson, aioabrp 0.9.0). Note:… | – |
| Apple CarPlay (HA iOS app) (`mobile_app`) | core | CarPlay UI only | worldwide | official | https://companion.home-assistant.io/docs/carplay/ |
| AutoPi (`none`) | other | Raspberry-Pi based OBD/4G dongle with cloud + local MQTT returner; HA… | EU/US | No maintained HA integration found; forum thread from 2018 | https://github.com/topeju/autopi_mqtt |
| Autoskope (`autoskope`) | core | Cloud API of Autoskope GPS trackers | DE/EU | core (has quality_scale.yaml) | – |
| BM2 battery monitor (BLE) (`ha_bm2monitor`) | hacs | HA Bluetooth to a BM2 clamp-on 12 V battery monitor. local_push. | worldwide | active; last commit 2026-11-20; manifest 1.5.0b2; 9 stars | https://github.com/andystewart999/ha_bm2monitor |
| BM6 battery monitor (BLE) (`bm6_ha`) | hacs | HA Bluetooth polling of a BM6 12 V battery monitor (encrypted GATT).… | worldwide | new; last commit 2026-11-23; manifest 1.0.4; 0 stars | https://github.com/danfulton72/bm6_ha |
| Car Scanner ELM OBD2 app (`none`) | other | Phone app + ELM327 dongle | worldwide | No direct HA export found (web search: users bridge via WiCAN; forum reports no odometer from it) | – |
| DIMO (`dimo`) | hacs | Cloud: DIMO Telemetry API (dimo-python-sdk 1.8.0). Car data arrives v… | US/EU (guess) | active; last commit 2026-11-14; manifest 1.7.2; 45 stars | https://github.com/ardevd/ha-dimo |
| Drivvo (fuel/expense log app) (`drivvo`) | hacs | Cloud: Drivvo account (unofficial API). cloud_polling. | worldwide (app popular in Brazil/EU) | active; last commit 2026-11-05; manifest 3.1.2; 3 stars | https://github.com/oOBenjaminOo/HA-drivvo |
| ELM327 BLE dongle (direct to HA Bluetooth) (`elm327_ble`) | hacs | HA Bluetooth (or ESPHome BT proxy) talks to a BLE ELM327 dongle left… | worldwide | new/small; last commit 2026-11-03; 0 stars | https://github.com/andrewgould/ha-elm327-ble |
| Enode (`enode`) | hacs | Cloud: Enode API (OAuth application_credentials + webhooks); Enode is… | EU/US EV brands (guess) | active; last commit 2026-10-23; manifest 1.3.3; 21 stars | https://github.com/evilmarty/enode |
| ESPHome / ESP32 OBD and CAN approaches (`none`) | other | ESP32 + ELM327 (BT) or CAN transceiver in the car; publishes via MQTT… | worldwide | obd2-mqtt active, last commit 2026-11-11 | https://github.com/adlerre/obd2-mqtt |
| EV chargers / OCPP (`none`) | core | n/a | n/a | skipped | – |
| Fuelio / Fuelly / aCar (`none`) | other | CSV export / Google Drive backup only | worldwide | No Home Assistant integration found (GitHub search: only CSV importers, e.g. tigattack/lubelogger-fuelio-impo… | – |
| High Mobility (`none`) | other | B2B OEM data API (fleet/insurer oriented), no consumer path | EU | No Home Assistant integration found (2 web searches + GitHub repo search returned nothing relevant) | – |
| Home Assistant Companion app: Android Auto car sensors (`mobile_app`) | core | Phone reads car hardware properties via the Android for Cars API whil… | worldwide; Android only | official; sensors disabled by default | https://github.com/home-assistant/android |
| Invoxia GPS tracker (`invoxia`) | hacs | Cloud API (gps-tracker lib) | EU/US | last commit 2025-12-30; 14 stars | https://github.com/timothyl13241/Invoxia-HA |
| Ituran (`ituran`) | core | Cloud: Ituran tracker account | Israel / LatAm | core | – |
| OBD2 BLE (dala318) (`obd2_ble`) | hacs | HA Bluetooth / ESPHome BT proxy to a BLE OBD2 dongle. | worldwide | small; last commit 2026-06-08 | https://github.com/dala318/obd2_ble |
| OVMS (Open Vehicle Monitoring System) (`ovms`) | hacs | Hardware module (OBD/CAN, own LTE/Wi-Fi) publishing OVMS v3 metrics t… | worldwide; mostly EVs (Leaf, Twizy, Zoe, i3, MG, Smart, VW e-Up ...) | active; last commit 2026-11-22; 33 stars | https://github.com/enoch85/ovms-home-assistant |
| Smartcar (`smartcar`) | hacs | Cloud: Smartcar API (OAuth2 application_credentials, user needs own f… | Smartcar coverage: North America + Europe, ~40 brands (guess, from Smartcar marketing; not checked) | active; last commit 2026-11-23; manifest version 0.1.0; NOT in core (verified: no core smartcar dir) | https://github.com/wbyoung/smartcar |
| Spritmonitor (`spritmonitor`) | hacs | Cloud: Spritmonitor.de API (user token). cloud_polling. | DE/EU | active; last commit 2026-11-11; manifest 4.7.0; 13 stars | https://github.com/matbott/home_assistant_Spritmonitor |
| StarLine (`starline`) | core | Cloud: StarLine alarm/telematics account (car alarm with CAN module) | Russia/CIS mainly | core | – |
| Torque (core, legacy) (`torque`) | core | Android app Torque Pro + ELM327 dongle; app uploads PIDs over HTTP(S)… | worldwide, Android only | core, quality_scale 'legacy', no codeowners, YAML only | – |
| Torque OBD-II (updated, HACS) (`torque_obd`) | hacs | Same Torque Pro web upload as core, with config flow, unique ids, res… | worldwide, Android only | active; last commit 2026-11-16; successor of archived JOHLC/ha-torque-2.0 (15 stars) | https://github.com/JOHLC/Home-Assistant-Torque-OBDII |
| TPMS BLE (aftermarket Bluetooth tyre sensors) (`tpms_ble`) | hacs | HA Bluetooth passive advertisements from valve-cap/internal BLE TPMS… | worldwide | active; last commit 2026-11-20; manifest 2.0.0; 86 stars; in HACS (README) | https://github.com/bkbilly/tpms_ble |
| Traccar Client (legacy webhook) (`traccar`) | core | Phone app webhook | worldwide | core | – |
| Traccar Server (`traccar_server`) | core | Self-hosted/cloud Traccar GPS server; many cheap OBD/GPS trackers rep… | worldwide | core | – |
| Victron BLE (SmartShunt / BMV / Smart Battery Sense / Orion) (`victron_ble`) | core | HA Bluetooth 'instant readout' advertisements (needs per-device encry… | worldwide; campers/vans mainly | core (has quality_scale.yaml) | – |
| WiCAN (MeatPi) OBD-II adapter (`wican`) | hacs | Hardware OBD-II/CAN dongle on car Wi-Fi/home Wi-Fi. Device runs AutoP… | worldwide | active; last commit 2026-11-23; 134 stars; README carries 'HACS Default' badge | https://github.com/jay-oswald/ha-wican |
