"""The pure model of the Car Keeper document: the sections and the records.

The document has 1 section for each kind of record. Each record is a plain
JSON-serializable dict. :func:`normalize_state` runs on each load, so a new
section needs no migration step. The builders check the input of a service and
make the record that the store writes.

This module is pure. It imports no Home Assistant code. A function that needs the
time takes it from its caller.
"""

from __future__ import annotations

import re
from datetime import date as _date
from typing import Any

from .const import UNIT_KM, UNITS
from .units import (
    DEFAULT_LEAD_DAYS,
    DEFAULT_LEAD_DISTANCE,
    round_interval,
    round_reading,
)

# The sections of the document that hold records by id.
RECORD_SECTIONS = ("cars", "items", "services")

FUELS = ("petrol", "diesel", "hybrid", "plug_in_hybrid", "electric", "other")
ITEM_KINDS = ("job", "date")
MAX_NAME = 100
MAX_TEXT = 200
MAX_NOTES = 4000
MAX_PARTS = 50
MAX_INTERVAL = 1_000_000
MAX_MONTHS = 240
MAX_LEAD_DAYS = 365
MAX_COST = 10_000_000
#: The keys of a car that a service can set. ``unit`` and ``odometer`` change
#: through their own store methods.
CAR_FIELDS = (
    "name",
    "make",
    "model",
    "year",
    "trim",
    "fuel",
    "vin",
    "plate",
    "engine_code",
    "transmission_code",
    "first_registered",
    "area_id",
    "notes",
    "lead_distance",
    "lead_days",
)
ITEM_FIELDS = (
    "name",
    "kind",
    "interval_distance",
    "interval_months",
    "due_date",
    "lead_distance",
    "lead_days",
    "notes",
    "enabled",
    "add_task",
    "parts",
)
SERVICE_FIELDS = ("date", "reading", "items", "shop", "notes", "who", "cost")


class CarKeeperError(Exception):
    """A user-facing error. ``key`` is in ``strings.json`` ``exceptions``."""

    def __init__(self, key: str, **placeholders: Any) -> None:
        super().__init__(key)
        self.key = key
        self.placeholders = {k: str(v) for k, v in placeholders.items()}


def default_settings() -> dict[str, Any]:
    """The settings of a new document."""
    return {"unit": UNIT_KM, "templates": {}}


def empty_state() -> dict[str, Any]:
    """A new, empty document."""
    return {
        **{name: {} for name in RECORD_SECTIONS},
        "readings": {},
        "settings": default_settings(),
        "sync": empty_sync(),
    }


def empty_sync() -> dict[str, list[dict[str, Any]]]:
    """The work that waits for Home Keeper.

    ``undo`` holds the Home Keeper completions ``{task_id, ts}`` to delete, and
    ``stock`` the part counts ``{asset_id, part_id, delta}`` to move. The sync
    removes each entry when Home Keeper accepts it.
    """
    return {"undo": [], "stock": []}


def normalize_state(data: Any) -> dict[str, Any]:
    """The document *data* with each missing section added.

    A value of the wrong type is replaced with the empty value, so a damaged file
    loads as far as it can.
    """
    state = empty_state()
    if not isinstance(data, dict):
        return state
    for name in (*RECORD_SECTIONS, "readings"):
        value = data.get(name)
        if isinstance(value, dict):
            state[name] = value
    settings = data.get("settings")
    if isinstance(settings, dict):
        state["settings"] = {**state["settings"], **settings}
    if state["settings"].get("unit") not in UNITS:
        state["settings"]["unit"] = UNIT_KM
    if not isinstance(state["settings"].get("templates"), dict):
        state["settings"]["templates"] = {}
    for car_id, value in list(state["readings"].items()):
        if not isinstance(value, list):
            state["readings"][car_id] = []
    sync = data.get("sync")
    if isinstance(sync, dict):
        for key in ("undo", "stock"):
            if isinstance(sync.get(key), list):
                state["sync"][key] = [e for e in sync[key] if isinstance(e, dict)]
    return state


_VERSION = re.compile(r"v?(\d+(?:\.\d+)*)\.?(?:(a|b|rc|dev)(\d+))?")


def _version_key(version: str) -> tuple[tuple[int, ...], bool, int] | None:
    """The sort key of a version such as ``0.38.0b5``, or None if it is not one.

    A pre-release sorts below its release: ``0.35.0b1`` is below ``0.35.0``.
    """
    match = _VERSION.fullmatch(version.strip())
    if match is None:
        return None
    numbers = tuple(int(part) for part in match.group(1).split("."))
    # A longer pad sorts each pair the same way.
    numbers += (0,) * (3 - len(numbers))  # pragma: no mutate
    # The tag and its number are both there or both missing.
    if match.group(2) is None:  # pragma: no mutate
        # Only a pre-release compares the last number.
        return numbers, True, 0  # pragma: no mutate
    return numbers, False, int(match.group(3))


def version_at_least(version: str | None, minimum: str) -> bool:
    """Whether *version* is *minimum* or later.

    A pre-release of a later release passes: ``0.38.0b5`` is at least ``0.35.0``.
    A pre-release of *minimum* itself does not pass. A version that cannot be read
    passes, because then the check of the panel tab module decides.
    """
    have = _version_key(version) if version else None
    want = _version_key(minimum)
    if have is None or want is None:
        return True
    return have >= want


# ── Field checks ─────────────────────────────────────────────────────────────


def text(data: dict[str, Any], key: str, limit: int = MAX_TEXT) -> str:
    """A text field, stripped, at most *limit* characters."""
    value = data.get(key)
    if value is None:
        return ""
    value = str(value).strip()
    if len(value) > limit:
        raise CarKeeperError("field_too_long", field=key, limit=limit)
    return value


def required_text(data: dict[str, Any], key: str, limit: int = MAX_NAME) -> str:
    """A text field that cannot be empty."""
    value = text(data, key, limit)
    if not value:
        raise CarKeeperError("field_required", field=key)
    return value


def number(
    data: dict[str, Any],
    key: str,
    *,
    low: float = 0,
    high: float | None = None,
    whole: bool = False,
) -> float | int | None:
    """A number field in a range, or None when it is empty."""
    value = data.get(key)
    if value is None or value == "":
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise CarKeeperError("invalid_field", field=key) from None
    if out != out or out < low or (high is not None and out > high):
        raise CarKeeperError("out_of_range", field=key, low=low, high=high or "")
    if whole:
        if out != int(out):
            raise CarKeeperError("invalid_field", field=key)
        return int(out)
    return out


def date_field(data: dict[str, Any], key: str) -> str | None:
    """A ``YYYY-MM-DD`` field, or None when it is empty."""
    value = data.get(key)
    if value is None or value == "":
        return None
    text_value = str(value)[:10]
    try:
        _date.fromisoformat(text_value)
    except ValueError:
        raise CarKeeperError("invalid_date", field=key, value=value) from None
    return text_value


def choice(
    data: dict[str, Any], key: str, options: tuple[str, ...], default: str
) -> str:
    """A field with a fixed list of values."""
    value = data.get(key)
    if value is None or value == "":
        return default
    if value not in options:
        raise CarKeeperError("invalid_field", field=key)
    return str(value)


# ── Cars ─────────────────────────────────────────────────────────────────────


def _car_values(data: dict[str, Any], unit: str) -> dict[str, Any]:
    year = number(data, "year", low=1886, high=2200, whole=True)
    lead = number(data, "lead_distance", high=MAX_INTERVAL)
    days = number(data, "lead_days", high=MAX_LEAD_DAYS, whole=True)
    return {
        "name": required_text(data, "name"),
        "make": text(data, "make", MAX_NAME),
        "model": text(data, "model", MAX_NAME),
        "year": year,
        "trim": text(data, "trim", MAX_NAME),
        "fuel": choice(data, "fuel", FUELS, "petrol"),
        "vin": text(data, "vin", 32).upper(),
        "plate": text(data, "plate", 32),
        "engine_code": text(data, "engine_code", 32),
        "transmission_code": text(data, "transmission_code", 32),
        "first_registered": date_field(data, "first_registered"),
        "area_id": text(data, "area_id") or None,
        "notes": text(data, "notes", MAX_NOTES),
        "lead_distance": round_interval(lead)
        if lead is not None
        else DEFAULT_LEAD_DISTANCE[unit],
        "lead_days": days if days is not None else DEFAULT_LEAD_DAYS,
    }


def build_car(
    data: dict[str, Any], *, car_id: str, today: str, default_unit: str
) -> dict[str, Any]:
    """A new car. The odometer starts with the ``odometer`` value of *data*."""
    unit = choice(data, "unit", UNITS, default_unit)
    odometer = number(data, "odometer", high=10_000_000)
    return {
        "id": car_id,
        **_car_values(data, unit),
        "unit": unit,
        "odometer": {
            "source": "manual",
            "entity_id": None,
            "value": None if odometer is None else round_reading(odometer),
            "updated": None,
            "offset": 0.0,
            "lower": None,
        },
        "photo": None,
        "created": today,
        "hk_asset_id": None,
    }


def update_car(
    car: dict[str, Any], data: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """The car with the fields of *data*, and the names of the fields that changed."""
    merged = {
        **{k: car.get(k) for k in CAR_FIELDS},
        **{k: v for k, v in data.items() if k in CAR_FIELDS},
    }
    values = _car_values(merged, car["unit"])
    changed = sorted(k for k, v in values.items() if car.get(k) != v)
    return {**car, **values}, changed


def clean_parts(value: Any, field: str = "parts_used") -> list[dict[str, Any]]:
    """A list of Home Keeper parts ``{asset_id, part_id, quantity}``, checked.

    The ids name a part of a Home Keeper appliance. The quantity is 1 when it is
    not given.
    """
    if not isinstance(value, list) or len(value) > MAX_PARTS:
        raise CarKeeperError("invalid_field", field=field)
    out = []
    for part in value:
        if (
            not isinstance(part, dict)
            or not part.get("asset_id")
            or not part.get("part_id")
        ):
            raise CarKeeperError("invalid_field", field=field)
        quantity = number(part, "quantity", low=0, high=10_000)
        out.append(
            {
                "asset_id": str(part["asset_id"]),
                "part_id": str(part["part_id"]),
                "quantity": quantity if quantity is not None else 1,
            }
        )
    return out


# ── Items ────────────────────────────────────────────────────────────────────


def _item_values(data: dict[str, Any]) -> dict[str, Any]:
    kind = choice(data, "kind", ITEM_KINDS, "job")
    distance = number(data, "interval_distance", low=1, high=MAX_INTERVAL)
    months = number(data, "interval_months", low=1, high=MAX_MONTHS, whole=True)
    due = date_field(data, "due_date")
    lead = number(data, "lead_distance", high=MAX_INTERVAL)
    if kind == "job" and distance is None and months is None:
        raise CarKeeperError("interval_required")
    if kind == "date" and due is None:
        raise CarKeeperError("field_required", field="due_date")
    return {
        "name": required_text(data, "name"),
        "kind": kind,
        "interval_distance": round_interval(distance) if distance is not None else None,
        "interval_months": months if kind == "job" or months else None,
        "due_date": due if kind == "date" else None,
        "lead_distance": round_interval(lead) if lead is not None else None,
        "lead_days": number(data, "lead_days", high=MAX_LEAD_DAYS, whole=True),
        "notes": text(data, "notes", MAX_NOTES),
        "enabled": bool(data.get("enabled", True)),
        "add_task": bool(data.get("add_task", True)),
        "parts": clean_parts(data.get("parts") or [], "parts"),
    }


def build_item(
    data: dict[str, Any],
    *,
    item_id: str,
    car: dict[str, Any],
    today: str,
    template_id: str | None = None,
) -> dict[str, Any]:
    """A new item of *car*. It counts from today and the odometer of today."""
    values = _item_values(data)
    if values["kind"] == "date":
        values["interval_distance"] = None
    start_date = date_field(data, "last_date") or today
    start_reading = number(data, "last_reading", high=10_000_000)
    if start_reading is None:
        start_reading = (car.get("odometer") or {}).get("value")
    return {
        "id": item_id,
        "car_id": car["id"],
        **values,
        "template_id": template_id,
        "start": {"date": start_date, "reading": start_reading},
        "last_done": None,
        "hk_task_id": None,
        "notified": None,
    }


def update_item(
    item: dict[str, Any], data: dict[str, Any]
) -> tuple[dict[str, Any], list[str]]:
    """The item with the fields of *data*, and the names of the fields that changed."""
    merged = {
        **{k: item.get(k) for k in ITEM_FIELDS},
        **{k: v for k, v in data.items() if k in ITEM_FIELDS},
    }
    values = _item_values(merged)
    if values["kind"] == "date":
        values["interval_distance"] = None
    changed = sorted(k for k, v in values.items() if item.get(k) != v)
    return {**item, **values}, changed


# ── Service records ──────────────────────────────────────────────────────────


def _service_values(
    data: dict[str, Any], car: dict[str, Any], items: dict[str, Any], today: str
) -> dict[str, Any]:
    done = data.get("items") or []
    if not isinstance(done, list):
        raise CarKeeperError("invalid_field", field="items")
    ids: list[str] = []
    for item_id in done:
        item = items.get(str(item_id))
        if item is None or item["car_id"] != car["id"]:
            raise CarKeeperError("item_not_found", id=item_id)
        if str(item_id) not in ids:
            ids.append(str(item_id))
    reading_value = number(data, "reading", high=10_000_000)
    return {
        "date": date_field(data, "date") or today,
        "reading": round_reading(reading_value) if reading_value is not None else None,
        "items": ids,
        "shop": text(data, "shop"),
        "notes": text(data, "notes", MAX_NOTES),
        "who": text(data, "who") or None,
        "cost": number(data, "cost", high=MAX_COST),
    }


def build_service(
    data: dict[str, Any],
    *,
    service_id: str,
    car: dict[str, Any],
    items: dict[str, Any],
    today: str,
    now: str,
    origin: str | None = None,
) -> dict[str, Any]:
    """A new service record of *car*."""
    return {
        "id": service_id,
        "car_id": car["id"],
        **_service_values(data, car, items, today),
        "parts_used": clean_parts(data.get("parts_used") or []),
        "logged": now,
        "origin": origin,
        "hk_completions": {},
    }


def update_service(
    service: dict[str, Any],
    data: dict[str, Any],
    car: dict[str, Any],
    items: dict[str, Any],
    today: str,
) -> tuple[dict[str, Any], list[str]]:
    """The service record with the fields of *data*, and the fields that changed."""
    merged = {
        **{k: service.get(k) for k in SERVICE_FIELDS},
        **{k: v for k, v in data.items() if k in SERVICE_FIELDS},
    }
    values = _service_values(merged, car, items, today)
    changed = sorted(k for k, v in values.items() if service.get(k) != v)
    return {**service, **values}, changed
