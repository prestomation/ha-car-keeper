"""The odometer of a car: the pure transitions and the list of readings.

The odometer of a car is the dict ``car["odometer"]``:

* ``source``: ``manual`` (a person types it) or ``entity`` (a sensor feeds it).
* ``entity_id``: the sensor of an ``entity`` odometer.
* ``value``: the last reading in the unit of the car, or None.
* ``updated``: the time of that reading.
* ``offset``: added to each later sensor value, after a new instrument cluster.
* ``lower``: the first lower sensor value since the last accepted one, or None.

Each transition takes the odometer and returns the next odometer and the reading
to store, or no reading. A transition never changes its input.

* :func:`typed` refuses a value below the last one with ``odometer_decreased``.
* :func:`from_entity` ignores a value that is not a number, and 1 lower value. A
  second lower value asks an admin to look (``Outcome.issue``).
* :func:`corrected` sets any value, also a lower one, and can set the offset.

The readings of a car are a list in time order. A sensor keeps at most 1 reading a
day: a new sensor reading replaces a sensor reading of the same day.

This module is pure. It imports no Home Assistant code. The caller passes ``now``.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any

from . import units
from .models import CarKeeperError

MANUAL = "manual"
ENTITY = "entity"
SERVICE = "service"
CORRECTION = "correction"
SOURCES = (MANUAL, ENTITY)
READING_SOURCES = (MANUAL, ENTITY, SERVICE, CORRECTION)


def new_odometer(
    source: str = MANUAL, entity_id: str | None = None, value: float | None = None
) -> dict[str, Any]:
    """The odometer of a new car."""
    return {
        "source": source,
        "entity_id": entity_id if source == ENTITY else None,
        "value": None if value is None else units.round_reading(value),
        "updated": None,
        "offset": 0.0,
        "lower": None,
    }


def reading(value: float, ts: str, source: str, by: str | None) -> dict[str, Any]:
    """1 stored reading."""
    return {"ts": ts, "value": units.round_reading(value), "source": source, "by": by}


@dataclass(frozen=True)
class Outcome:
    """The result of 1 transition."""

    odometer: dict[str, Any]
    reading: dict[str, Any] | None = None
    issue: bool = False


def _accept(
    odometer: dict[str, Any], value: float, now: str, source: str, by: str | None
) -> Outcome:
    out = copy.deepcopy(odometer)
    out["value"] = units.round_reading(value)
    out["updated"] = now
    out["lower"] = None
    return Outcome(out, reading(value, now, source, by))


def typed(
    odometer: dict[str, Any],
    value: float,
    now: str,
    *,
    by: str | None = None,
    source: str = MANUAL,
) -> Outcome:
    """A reading that a person typed, or the reading of a service.

    A value below the last one fails with ``odometer_decreased``. An admin corrects
    the odometer with :func:`corrected`.
    """
    if value < 0:
        raise CarKeeperError("invalid_reading", value=value)
    current = odometer.get("value")
    rounded = units.round_reading(value)
    if current is not None and rounded < current:
        raise CarKeeperError("odometer_decreased", value=rounded, current=current)
    return _accept(odometer, value, now, source, by)


def from_entity(
    odometer: dict[str, Any], raw: Any, raw_unit: str | None, car_unit: str, now: str
) -> Outcome:
    """A new state of the odometer sensor.

    *raw* is the state of the sensor and *raw_unit* its unit. A value that is not a
    number, or a unit that Car Keeper cannot read, changes nothing. The offset is
    added after the conversion to the unit of the car.
    """
    try:
        number = float(raw)
    except (TypeError, ValueError):
        return Outcome(copy.deepcopy(odometer))
    if number != number or number < 0 or not units.known(raw_unit or car_unit):
        return Outcome(copy.deepcopy(odometer))
    value = units.round_reading(
        units.convert(number, raw_unit or car_unit, car_unit)
        + float(odometer.get("offset") or 0)
    )
    current = odometer.get("value")
    if current is None or value >= current:
        if current is not None and value == current:
            out = copy.deepcopy(odometer)
            out["lower"] = None
            return Outcome(out)
        return _accept(odometer, value, now, ENTITY, None)
    out = copy.deepcopy(odometer)
    if odometer.get("lower") is None:
        # 1 lower value is noise, such as a cloud that reports an old value.
        out["lower"] = value
        return Outcome(out)
    out["lower"] = value
    return Outcome(out, issue=True)


def corrected(
    odometer: dict[str, Any],
    value: float,
    now: str,
    *,
    offset: float | None = None,
    by: str | None = None,
) -> Outcome:
    """An admin correction: any value, also a lower one, and a new offset."""
    if value < 0:
        raise CarKeeperError("invalid_reading", value=value)
    outcome = _accept(odometer, value, now, CORRECTION, by)
    if offset is not None:
        outcome.odometer["offset"] = units.round_reading(offset)
    return outcome


def bound(
    odometer: dict[str, Any], source: str, entity_id: str | None
) -> dict[str, Any]:
    """The odometer with a new source. The value and the readings stay."""
    if source not in SOURCES:
        raise CarKeeperError("invalid_field", field="source")
    if source == ENTITY and not entity_id:
        raise CarKeeperError("field_required", field="entity_id")
    out = copy.deepcopy(odometer)
    out["source"] = source
    out["entity_id"] = entity_id if source == ENTITY else None
    out["lower"] = None
    return out


def add(readings: list[dict[str, Any]], new: dict[str, Any]) -> list[dict[str, Any]]:
    """The list of readings with *new* in time order.

    A sensor reading replaces a sensor reading of the same day, so a sensor keeps
    at most 1 reading a day.
    """
    out = [dict(r) for r in readings]
    if new["source"] == ENTITY:
        day = str(new["ts"])[:10]
        out = [
            r for r in out if not (r["source"] == ENTITY and str(r["ts"])[:10] == day)
        ]
    out.append(dict(new))
    out.sort(key=lambda r: str(r["ts"]))
    return out


def convert_odometer(odometer: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    """The odometer in the unit *new*."""
    out = copy.deepcopy(odometer)
    for key in ("value", "offset", "lower"):
        if out.get(key) is not None:
            out[key] = units.round_reading(units.convert(out[key], old, new))
    return out


def convert_readings(
    readings: list[dict[str, Any]], old: str, new: str
) -> list[dict[str, Any]]:
    """The readings in the unit *new*."""
    return [
        {**r, "value": units.round_reading(units.convert(r["value"], old, new))}
        for r in readings
    ]
