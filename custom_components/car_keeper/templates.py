"""The starter jobs: common intervals by fuel type.

These are common intervals, not the schedule of a car maker. The tab tells the
user to check the manual of the car where the user accepts them. Each starter job
has an id, the fuel types that need it, a distance in km and a number of months.
A date job (registration, insurance, inspection) has a due date that the user
gives, and repeats every 12 months. For the inspection, 12 months is the shortest
common rule (the UK MOT, many US states). The country and the age of the car decide
the real interval, such as 24 months for the German HU, and the tab says so.

An admin can change the interval of a starter job, or turn it off, with the
``templates`` setting (:func:`effective`). :func:`items_for` turns the selected
starter jobs into item data in the unit of a car, with the distance rounded to
100.

Each id is a one-way door: a stored item keeps it in ``template_id``.

This module is pure. It imports no Home Assistant code.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from . import units
from .models import FUELS, CarKeeperError

ICE = ("petrol", "diesel", "hybrid", "plug_in_hybrid", "other")
ALL = FUELS


@dataclass(frozen=True)
class Template:
    """1 starter job."""

    id: str
    fuels: tuple[str, ...]
    km: int | None
    months: int | None
    kind: str = "job"


#: The built-in starter jobs. A car with a timing chain has no belt: the user leaves
#: that job out. The names are ``template.<id>`` in backend_strings.
TEMPLATES: tuple[Template, ...] = (
    Template("engine_oil", ICE, 15000, 12),
    Template("tyre_rotation", ALL, 10000, 12),
    Template("tyre_check", ALL, None, 1),
    Template("brake_fluid", ALL, None, 24),
    Template("cabin_filter", ALL, 20000, 12),
    Template("engine_air_filter", ICE, 30000, 24),
    Template("wipers", ALL, None, 12),
    Template("battery_12v", ALL, None, 12),
    Template("coolant", ALL, 100000, 60),
    Template("spark_plugs", ("petrol", "hybrid", "plug_in_hybrid"), 60000, 60),
    Template("adblue", ("diesel",), 10000, None),
    Template(
        "timing_belt", ("petrol", "diesel", "hybrid", "plug_in_hybrid"), 100000, 72
    ),
    Template("gearbox_oil", ICE, 60000, 48),
    Template("registration", ALL, None, 12, "date"),
    Template("insurance", ALL, None, 12, "date"),
    Template("inspection", ALL, None, 12, "date"),
)
BY_ID = {t.id: t for t in TEMPLATES}


def effective(overrides: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The starter jobs with the overrides of the ``templates`` setting.

    An override is ``{km, months, enabled}``. A key that it leaves out keeps the
    built-in value.
    """
    out = []
    for template in TEMPLATES:
        override = overrides.get(template.id) or {}
        out.append(
            {
                "id": template.id,
                "fuels": list(template.fuels),
                "kind": template.kind,
                "km": override.get("km", template.km),
                "months": override.get("months", template.months),
                "enabled": bool(override.get("enabled", True)),
            }
        )
    return out


def clean_overrides(value: Any) -> dict[str, dict[str, Any]]:
    """The ``templates`` setting, checked."""
    if not isinstance(value, Mapping):
        raise CarKeeperError("invalid_field", field="templates")
    out: dict[str, dict[str, Any]] = {}
    for template_id, override in value.items():
        if template_id not in BY_ID or not isinstance(override, Mapping):
            raise CarKeeperError("template_not_found", id=template_id)
        clean: dict[str, Any] = {}
        for key, high in (("km", 1_000_000), ("months", 240)):
            if key in override:
                number = override[key]
                if number is not None and (
                    not isinstance(number, int | float) or not 1 <= number <= high
                ):
                    raise CarKeeperError("out_of_range", field=key, low=1, high=high)
                clean[key] = None if number is None else int(number)
        if "enabled" in override:
            clean["enabled"] = bool(override["enabled"])
        out[template_id] = clean
    return out


def for_fuel(fuel: str, overrides: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The enabled starter jobs that a car with *fuel* needs."""
    return [t for t in effective(overrides) if t["enabled"] and fuel in t["fuels"]]


def items_for(
    template_ids: Iterable[str],
    *,
    unit: str,
    overrides: Mapping[str, Any],
    names: Mapping[str, str],
    due_dates: Mapping[str, str] | None = None,
    today: str,
) -> list[dict[str, Any]]:
    """The item data of the selected starter jobs, in *unit*.

    *names* maps a template id to its name in the language of Home Assistant. A
    date job takes its due date from *due_dates*, else today.
    """
    rows = {t["id"]: t for t in effective(overrides)}
    out = []
    for template_id in template_ids:
        row = rows.get(template_id)
        if row is None:
            raise CarKeeperError("template_not_found", id=template_id)
        km = row["km"]
        distance = units.round_template(units.convert(km, "km", unit)) if km else None
        data: dict[str, Any] = {
            "name": names.get(template_id, template_id),
            "kind": row["kind"],
            "interval_distance": distance if row["kind"] == "job" else None,
            "interval_months": row["months"],
        }
        if row["kind"] == "date":
            data["due_date"] = (due_dates or {}).get(template_id) or today
        out.append({"template_id": template_id, "data": data})
    return out
