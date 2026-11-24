"""Constants for Car Keeper.

Car Keeper is a companion of Home Keeper. It stores the cars of a household: the
odometer of each car, the maintenance jobs and the service history. The admin UI
is the Cars tab in the Home Keeper panel. The usage surfaces are the cards, the
entities and the open services.

This module is pure. It imports no Home Assistant code, so the unit tier can load
it.
"""

from __future__ import annotations

DOMAIN = "car_keeper"
NAME = "Car Keeper"
ICON = "mdi:car-wrench"
DOCS_URL = "https://github.com/prestomation/ha-car-keeper"

# The Home Keeper integration that Car Keeper requires.
HOME_KEEPER_DOMAIN = "home_keeper"
HOME_KEEPER_EVENT_REGISTER_COMPANIONS = "home_keeper_register_companions"
# The first Home Keeper version with every part of the contract that Car Keeper
# uses: managed appliances (0.27.0), the panel tab API (0.30.0), the companion
# export (0.31.0) and the ``parts`` list of ``set_task_consumable`` (0.35.0).
HOME_KEEPER_MIN_VERSION = "0.35.0"
HOME_KEEPER_INSTALL_URL = "https://github.com/prestomation/ha-home-keeper#installation"
# The reasons why Home Keeper cannot take the Cars tab. Each is a config flow
# abort reason and a repair issue id with the same translation key.
ISSUE_HOME_KEEPER_MISSING = "home_keeper_missing"
ISSUE_HOME_KEEPER_NOT_SET_UP = "home_keeper_not_set_up"
ISSUE_HOME_KEEPER_TOO_OLD = "home_keeper_too_old"
HOME_KEEPER_REASONS = (
    ISSUE_HOME_KEEPER_MISSING,
    ISSUE_HOME_KEEPER_NOT_SET_UP,
    ISSUE_HOME_KEEPER_TOO_OLD,
)
# The Home Keeper capability of a companion that joins the export and import.
HOME_KEEPER_CAPABILITY_IMPORT_EXPORT = "import_export"

# The entity platforms of the config entry.
PLATFORMS: list[str] = []

# PANEL_VERSION is the same string as the manifest version. release.yml checks it,
# and rollup.config.mjs reads it.
PANEL_VERSION = "0.1.0b1"

# The built bundles are in frontend/dist/ and Home Assistant serves them here.
STATIC_URL = "/car_keeper_static"
TAB_JS_FILENAME = "cars-tab.js"
CARD_JS_FILENAME = "car-keeper-card.js"
TAB_ID = "cars"
TAB_ELEMENT = "home-keeper-cars-tab"
TAB_ORDER = 60
TAB_HOST_API = 1

# The dispatcher signal of a store change. Its argument is the store revision.
SIGNAL_STORE_CHANGED = f"{DOMAIN}_store_changed"

# The storage document, ``.storage/car_keeper``.
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
STORAGE_MINOR_VERSION = 1

# The config entry option: the distance unit of a new car.
CONF_UNIT = "unit"
UNIT_KM = "km"
UNIT_MI = "mi"
UNITS = (UNIT_KM, UNIT_MI)

# The origin marker that Car Keeper sends to Home Keeper, and that it reads back
# in the events of Home Keeper to stop a loop.
ORIGIN = DOMAIN

# The bus events. Each name is ``car_keeper_<noun>_<verb>``. The pure builders in
# events.py make the payloads, and the store fires them.
EVENT_SETTINGS_UPDATED = f"{DOMAIN}_settings_updated"

# The languages of every string table: strings.json, translations/ and
# backend_strings/. The same 17 languages as Home Keeper.
LANGUAGES = (
    "ca",
    "cs",
    "da",
    "de",
    "en",
    "es",
    "fi",
    "fr",
    "it",
    "nb",
    "nl",
    "pl",
    "pt-BR",
    "ru",
    "sv",
    "uk",
    "zh-Hans",
)
