"""The presets that Car Keeper adds to the Home Keeper preset picker.

Home Keeper 0.38.0b5 and later have the admin-only service
``home_keeper.register_presets``. A companion sends rows in the format of the Home
Keeper preset catalog, with no ``source`` and no ``verified`` pin, and the task name of
each new duty in each language. Home Keeper checks each row and builds the presets.
A row holds no Jinja: the shape gives the trigger and the task text.

``ROWS`` are the rows of the car integrations that Car Keeper knows. ``SOURCES`` pins
the upstream translation file of each row (or, with ``match: text``, the code file
that names the translation keys), so ``ci/check_preset_keys.py`` can check
that each key is still there. ``DUTY_NAMES`` has the duties that Home Keeper does not
ship, in the 17 languages of Car Keeper.

Home Keeper keeps the presets in memory for the run. So Car Keeper registers again at
each start, when the service appears and when Home Keeper asks its companions. It
removes them when it unloads. :func:`transition` is the 1 rule for this, and the
state machine test runs it against a fake Home Keeper.

Pure: no Home Assistant import.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Final

# The Home Keeper service names. Their absence means a Home Keeper with no presets
# for companions: 0.35.0 to 0.38.0b4. Car Keeper then registers nothing.
SERVICE_REGISTER: Final = "register_presets"
SERVICE_UNREGISTER: Final = "unregister_presets"

# The separator that Home Keeper puts between the companion domain and a preset id.
ID_SEPARATOR: Final = "/"

# The limits of Home Keeper, so a test fails here before Home Keeper refuses a row.
MAX_ROWS: Final = 20
MAX_DUTIES: Final = 20
MAX_KEYS: Final = 20

# The duties of Home Keeper itself that the rows use. Home Keeper has their names.
HOME_KEEPER_DUTIES: Final = frozenset({"annual_service", "oil_service"})

ICON: Final = "mdi:car-wrench"

DUTY_NAMES: Final[dict[str, dict[str, str]]] = {
    "check_fluid_levels": {
        "en": "Check the fluid levels",
        "ca": "Comprovar els nivells de líquids",
        "cs": "Zkontrolovat hladiny kapalin",
        "da": "Kontrollér væskeniveauerne",
        "de": "Flüssigkeitsstände prüfen",
        "es": "Comprobar los niveles de líquidos",
        "fi": "Tarkista nestemäärät",
        "fr": "Vérifier les niveaux de liquides",
        "it": "Controllare i livelli dei liquidi",
        "nb": "Sjekk væskenivåene",
        "nl": "Vloeistofniveaus controleren",
        "pl": "Sprawdź poziomy płynów",
        "pt-BR": "Verificar os níveis de fluidos",
        "ru": "Проверить уровни жидкостей",
        "sv": "Kontrollera vätskenivåerna",
        "uk": "Перевірити рівні рідин",
        "zh-Hans": "检查液位",
    },
    "check_brake_fluid": {
        "en": "Check the brake fluid",
        "ca": "Revisar el líquid de frens",
        "cs": "Zkontrolovat brzdovou kapalinu",
        "da": "Kontrollér bremsevæsken",
        "de": "Bremsflüssigkeit prüfen",
        "es": "Revisar el líquido de frenos",
        "fi": "Tarkista jarruneste",
        "fr": "Vérifier le liquide de frein",
        "it": "Controllare il liquido dei freni",
        "nb": "Sjekk bremsevæsken",
        "nl": "Remvloeistof controleren",
        "pl": "Sprawdź płyn hamulcowy",
        "pt-BR": "Verificar o fluido de freio",
        "ru": "Проверить тормозную жидкость",
        "sv": "Kontrollera bromsvätskan",
        "uk": "Перевірити гальмівну рідину",
        "zh-Hans": "检查制动液",
    },
    "check_tyres": {
        "en": "Check the tyres",
        "ca": "Revisar els pneumàtics",
        "cs": "Zkontrolovat pneumatiky",
        "da": "Kontrollér dækkene",
        "de": "Reifen prüfen",
        "es": "Revisar los neumáticos",
        "fi": "Tarkista renkaat",
        "fr": "Vérifier les pneus",
        "it": "Controllare gli pneumatici",
        "nb": "Sjekk dekkene",
        "nl": "Banden controleren",
        "pl": "Sprawdź opony",
        "pt-BR": "Verificar os pneus",
        "ru": "Проверить шины",
        "sv": "Kontrollera däcken",
        "uk": "Перевірити шини",
        "zh-Hans": "检查轮胎",
    },
    "check_warning_lamps": {
        "en": "Check the warning lamps",
        "ca": "Revisar els llums d'avís",
        "cs": "Zkontrolovat výstražné kontrolky",
        "da": "Kontrollér advarselslamperne",
        "de": "Warnleuchten prüfen",
        "es": "Revisar los testigos de aviso",
        "fi": "Tarkista varoitusvalot",
        "fr": "Vérifier les voyants d'alerte",
        "it": "Controllare le spie di avviso",
        "nb": "Sjekk varsellampene",
        "nl": "Waarschuwingslampjes controleren",
        "pl": "Sprawdź kontrolki ostrzegawcze",
        "pt-BR": "Verificar as luzes de aviso",
        "ru": "Проверить сигнальные лампы",
        "sv": "Kontrollera varningslamporna",
        "uk": "Перевірити сигнальні лампи",
        "zh-Hans": "检查警告灯",
    },
    "check_12v_battery": {
        "en": "Check the 12 V battery",
        "ca": "Revisar la bateria de 12 V",
        "cs": "Zkontrolovat 12V baterii",
        "da": "Kontrollér 12 V-batteriet",
        "de": "12-V-Batterie prüfen",
        "es": "Revisar la batería de 12 V",
        "fi": "Tarkista 12 V:n akku",
        "fr": "Vérifier la batterie 12 V",
        "it": "Controllare la batteria a 12 V",
        "nb": "Sjekk 12 V-batteriet",
        "nl": "12V-accu controleren",
        "pl": "Sprawdź akumulator 12 V",
        "pt-BR": "Verificar a bateria de 12 V",
        "ru": "Проверить аккумулятор 12 В",  # noqa: RUF001 (the volt sign)
        "sv": "Kontrollera 12 V-batteriet",
        "uk": "Перевірити акумулятор 12 В",  # noqa: RUF001 (the volt sign)
        "zh-Hans": "检查 12 V 蓄电池",
    },
}

# ROWS_START
# Each key was read from the translation file of its integration at the commit in
# SOURCES. ci/check_preset_keys.py checks them again. Each alert is a binary sensor in
# the state on, except where a duty names a sensor and its state.
ROWS: Final[list[dict[str, Any]]] = [
    {
        "domain": "volvo",
        "brand": "Volvo Cars",
        "icon": ICON,
        "duties": [
            {
                "duty": "annual_service",
                "shape": "life_low",
                "keys": ["time_to_service"],
                "limit": 336,
            },
            {
                "duty": "check_fluid_levels",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": [
                    "oil_level_warning",
                    "washer_fluid_level_warning",
                    "coolant_level_warning",
                ],
                "state": "on",
            },
            {
                "duty": "check_brake_fluid",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["brake_fluid_level_warning"],
                "state": "on",
            },
            {
                "duty": "check_tyres",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": [
                    "tire_front_left",
                    "tire_front_right",
                    "tire_rear_left",
                    "tire_rear_right",
                ],
                "state": "on",
            },
        ],
    },
    {
        "domain": "polestar_api",
        "brand": "Polestar",
        "icon": ICON,
        "duties": [
            {
                "duty": "annual_service",
                "shape": "life_low",
                "keys": ["polestar_days_to_service"],
                "limit": 336,
            }
        ],
    },
    {
        "domain": "uconnect",
        "brand": "Uconnect (Jeep, Ram, Chrysler, Dodge, Fiat)",
        "icon": ICON,
        "duties": [
            {
                "duty": "annual_service",
                "shape": "life_low",
                "keys": ["days_to_service"],
                "limit": 336,
            },
            {
                "duty": "check_tyres",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": [
                    "wheel_front_left_pressure_warning",
                    "wheel_front_right_pressure_warning",
                    "wheel_rear_left_pressure_warning",
                    "wheel_rear_right_pressure_warning",
                ],
                "state": "on",
            },
        ],
    },
    {
        "domain": "fordpass",
        "brand": "FordPass",
        "icon": ICON,
        "duties": [
            {
                "duty": "oil_service",
                "shape": "percent_low",
                "keys": ["oil"],
                "limit": 10,
            }
        ],
    },
    {
        "domain": "mazda_cs",
        "brand": "Mazda Connected Services",
        "icon": ICON,
        "duties": [
            {
                "duty": "oil_service",
                "shape": "percent_low",
                "keys": ["dr_oil_deteriorate_level"],
                "limit": 10,
            },
            {
                "duty": "oil_service",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["oil_deteriorate_warning"],
                "state": "on",
            },
            {
                "duty": "check_fluid_levels",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["oil_level_warning"],
                "state": "on",
            },
            {
                "duty": "check_brake_fluid",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["brake_oil_level_warning"],
                "state": "on",
            },
            {
                "duty": "check_tyres",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": [
                    "front_left_tire_pressure_warning",
                    "front_right_tire_pressure_warning",
                    "rear_left_tire_pressure_warning",
                    "rear_right_tire_pressure_warning",
                    "tpms_battery_warning",
                ],
                "state": "on",
            },
        ],
    },
    {
        "domain": "kia_uvo",
        "brand": "Kia Connect / Hyundai Bluelink",
        "icon": ICON,
        "duties": [
            {
                "duty": "check_fluid_levels",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["oil_level_warning_is_on", "washer_fluid_warning_is_on"],
                "state": "on",
            },
            {
                "duty": "check_brake_fluid",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["brake_fluid_warning_is_on"],
                "state": "on",
            },
            {
                "duty": "check_tyres",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": [
                    "tire_pressure_all_warning_is_on",
                    "tire_pressure_front_left_warning_is_on",
                    "tire_pressure_front_right_warning_is_on",
                    "tire_pressure_rear_left_warning_is_on",
                    "tire_pressure_rear_right_warning_is_on",
                ],
                "state": "on",
            },
            {
                "duty": "check_12v_battery",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": [
                    "battery_auxiliary_fail_warning_is_on",
                    "auto_cut_battery_prewarning_on",
                ],
                "state": "on",
            },
        ],
    },
    {
        "domain": "rivian",
        "brand": "Rivian",
        "icon": ICON,
        "duties": [
            {
                "duty": "check_brake_fluid",
                "shape": "alert",
                "keys": ["brake_fluid_low"],
                "state": "active",
            },
            {
                "duty": "check_fluid_levels",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["wiper_fluid_state"],
                "state": "on",
            },
        ],
    },
    {
        "domain": "subaru",
        "brand": "Subaru",
        "icon": ICON,
        "duties": [
            {
                "duty": "check_warning_lamps",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["mil_eol", "mil_opl", "mil_tpms", "mil_wash"],
                "state": "on",
            }
        ],
    },
    {
        "domain": "mbapi2020",
        "brand": "Mercedes-Benz (MercedesME 2020)",
        "icon": ICON,
        "duties": [
            {
                "duty": "check_fluid_levels",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["warningwashwater", "warningcoolantlevellow"],
                "state": "on",
            },
            {
                "duty": "check_brake_fluid",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["warningbrakefluid"],
                "state": "on",
            },
            {
                "duty": "check_tyres",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["tirewarninglamp"],
                "state": "on",
            },
            {
                "duty": "check_warning_lamps",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": ["warningenginelight"],
                "state": "on",
            },
        ],
    },
    {
        "domain": "bm6_ha",
        "brand": "BM6 battery monitor",
        "icon": ICON,
        "duties": [
            {
                "duty": "check_12v_battery",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": [
                    "low_battery",
                    "voltage_problem",
                    "crank_problem",
                    "charging_system_problem",
                ],
                "state": "on",
            }
        ],
    },
    {
        "domain": "tesla_fleet",
        "brand": "Tesla Fleet",
        "icon": ICON,
        "duties": [
            {
                "duty": "check_tyres",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": [
                    "vehicle_state_tpms_soft_warning_fl",
                    "vehicle_state_tpms_soft_warning_fr",
                    "vehicle_state_tpms_soft_warning_rl",
                    "vehicle_state_tpms_soft_warning_rr",
                ],
                "state": "on",
            }
        ],
    },
    {
        "domain": "teslemetry",
        "brand": "Teslemetry",
        "icon": ICON,
        "duties": [
            {
                "duty": "check_tyres",
                "shape": "alert",
                "platform": "binary_sensor",
                "keys": [
                    "vehicle_state_tpms_soft_warning_fl",
                    "vehicle_state_tpms_soft_warning_fr",
                    "vehicle_state_tpms_soft_warning_rl",
                    "vehicle_state_tpms_soft_warning_rr",
                ],
                "state": "on",
            }
        ],
    },
]
SOURCES: Final[dict[str, dict[str, str]]] = {
    "volvo": {
        "url": "https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/volvo/strings.json",
        "ref": "927a468e1edb1639b3fbe0cf923b101af9944edc",
        "date": "2026-11-24",
    },
    "polestar_api": {
        "url": "https://raw.githubusercontent.com/pypolestar/polestar_api/main/custom_components/polestar_api/translations/en.json",
        "ref": "98ee2823bda34869ba759e80f27d18bf8ac852f7",
        "date": "2026-09-22",
    },
    "uconnect": {
        "url": "https://raw.githubusercontent.com/hass-uconnect/hass-uconnect/main/custom_components/uconnect/translations/en.json",
        "ref": "9037a6c6346568ce8e43a402b0dbb8f64c688a53",
        "date": "2026-11-23",
    },
    "fordpass": {
        "url": "https://raw.githubusercontent.com/marq24/ha-fordpass/main/custom_components/fordpass/translations/en.json",
        "ref": "ac4ed3e32a8203ee83d94f82f80fab208ca7072a",
        "date": "2026-11-23",
    },
    "mazda_cs": {
        "url": "https://raw.githubusercontent.com/fano0001/home-assistant-mazda/main/custom_components/mazda_cs/translations/en.json",
        "ref": "13a3d31845ab58ac1409799eadf83449fcc1b2dc",
        "date": "2026-11-16",
    },
    "kia_uvo": {
        "url": "https://raw.githubusercontent.com/Hyundai-Kia-Connect/kia_uvo/master/custom_components/kia_uvo/translations/en.json",
        "ref": "f57cee7a390e6e190616b11e05733014b2be9dff",
        "date": "2026-11-23",
    },
    "rivian": {
        "url": "https://raw.githubusercontent.com/bretterer/home-assistant-rivian/main/custom_components/rivian/translations/en.json",
        "ref": "ce6daf1a1a8beea5cab2917be0b99b2717493dae",
        "date": "2026-11-16",
    },
    "subaru": {
        "url": "https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/subaru/strings.json",
        "ref": "927a468e1edb1639b3fbe0cf923b101af9944edc",
        "date": "2026-11-24",
    },
    "mbapi2020": {
        # The translation key is the lowercase internal name in const.py, and the
        # translation file does not list these entities.
        "url": "https://raw.githubusercontent.com/ReneNulschDE/mbapi2020/master/custom_components/mbapi2020/const.py",
        "match": "text",
        "ref": "6976c44e63d203708e60e987d2f8d76376e74f8a",
        "date": "2026-11-16",
    },
    "bm6_ha": {
        "url": "https://raw.githubusercontent.com/danfulton72/bm6_ha/main/custom_components/bm6_ha/translations/en.json",
        "ref": "f2316edf7f47f185020a04e53728a9caf6051f0e",
        "date": "2026-11-23",
    },
    "tesla_fleet": {
        "url": "https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/tesla_fleet/strings.json",
        "ref": "927a468e1edb1639b3fbe0cf923b101af9944edc",
        "date": "2026-11-24",
    },
    "teslemetry": {
        "url": "https://raw.githubusercontent.com/home-assistant/core/dev/homeassistant/components/teslemetry/strings.json",
        "ref": "927a468e1edb1639b3fbe0cf923b101af9944edc",
        "date": "2026-11-24",
    },
}
# ROWS_END


def preset_ids(rows: list[dict[str, Any]], companion: str) -> list[str]:
    """The preset ids that Home Keeper makes from *rows*, in its order.

    Home Keeper makes 1 preset for each shape, platform and alert state of a row:
    ``<companion>/<row domain>_<shape>[_<platform>][_<state>]``, with no platform part
    for ``sensor``. A test checks this against the real Home Keeper.
    """
    out: list[str] = []
    for row in rows:
        for duty in row["duties"]:
            # No platform part for a sensor, the default platform.
            platform = duty.get("platform")
            parts = (
                row["domain"],
                duty["shape"],
                None if platform == "sensor" else platform,
                duty.get("state"),
            )
            preset_id = companion + ID_SEPARATOR + "_".join(p for p in parts if p)
            if preset_id not in out:
                out.append(preset_id)
    return out


def registration(companion: str) -> dict[str, Any]:
    """The data of the ``register_presets`` call."""
    used = {duty["duty"] for row in ROWS for duty in row["duties"]}
    names = {duty: DUTY_NAMES[duty] for duty in sorted(used) if duty in DUTY_NAMES}
    return {"domain": companion, "rows": ROWS, "duty_names": names}


# The registration lifecycle.

REGISTER: Final = "register"
UNREGISTER: Final = "unregister"

STATUS_REGISTERED: Final = "registered"
STATUS_NO_SERVICE: Final = "no_service"
STATUS_FAILED: Final = "failed"
STATUS_WAITING: Final = "waiting"


@dataclass(frozen=True)
class Link:
    """What Car Keeper knows of its presets in Home Keeper.

    *running* is true while the Car Keeper entry is set up. *service* is true while
    Home Keeper has ``register_presets``. *registered* is true after a call that
    Home Keeper accepted, until a removal or a loss of the service.
    """

    running: bool = False
    service: bool = False
    registered: bool = False
    preset_ids: tuple[str, ...] = ()
    error: str | None = None


@dataclass(frozen=True)
class Event:
    """1 input of :func:`transition`.

    *kind* is ``start``, ``stop``, ``service_added``, ``service_removed``, ``ask``
    (Home Keeper asks its companions to announce, or became available), ``accepted``
    (a register call passed, with *preset_ids*) or ``refused`` (a call failed, with
    *error*).
    """

    kind: str
    preset_ids: tuple[str, ...] = ()
    error: str | None = None


KINDS: Final = (
    "start",
    "stop",
    "service_added",
    "service_removed",
    "ask",
    "accepted",
    "refused",
)


def transition(link: Link, event: Event) -> tuple[Link, str | None]:
    """Apply *event* to *link*. Return the new link and the call to make, or None.

    A register call replaces what Home Keeper holds, so a call again is safe, and
    Home Keeper fires no event when the presets did not change.
    """
    kind = event.kind
    if kind not in KINDS:
        raise ValueError(f"unknown event {kind}")
    if kind == "start":
        new = replace(link, running=True)
        return new, REGISTER if new.service else None
    if kind == "stop":
        new = replace(link, running=False, registered=False, preset_ids=())
        return new, UNREGISTER if link.service else None
    if kind == "service_added":
        # A stopped Car Keeper removes what an old call left in Home Keeper.
        return replace(link, service=True), REGISTER if link.running else UNREGISTER
    if kind == "service_removed":
        return replace(link, service=False, registered=False, preset_ids=()), None
    if kind == "ask":
        return link, REGISTER if link.running and link.service else None
    if kind == "accepted":
        if not link.running:
            # The call ended after the stop: take the presets away again.
            return link, UNREGISTER if link.service else None
        return (
            replace(link, registered=True, preset_ids=event.preset_ids, error=None),
            None,
        )
    # refused
    return replace(link, registered=False, preset_ids=(), error=event.error), None


def status(link: Link) -> str:
    """The word for the settings page of the Cars tab."""
    if not link.service:
        return STATUS_NO_SERVICE
    if link.registered:
        return STATUS_REGISTERED
    if link.error is not None:
        return STATUS_FAILED
    return STATUS_WAITING


def project(link: Link) -> dict[str, Any]:
    """The ``presets`` key of ``get_state``. Every user can read it."""
    return {
        "status": status(link),
        "preset_ids": list(link.preset_ids),
        "error": link.error,
        "rows": [
            {
                "domain": row["domain"],
                "brand": row["brand"],
                "duties": sorted({duty["duty"] for duty in row["duties"]}),
            }
            for row in ROWS
        ],
    }
