"""The shape of each read reply, with the computed due values.

Every read is open to every user, so this module hides no field. It shapes the
document for a reader: it copies each record, so a caller cannot change the
stored document, and it adds the values that the reader needs and the document
does not store: the evaluation of each item (``schedule.evaluate``), and the
status, the next job and the daily distance of each car. The tab, the cards, the
entities and the read services use the same functions, so they show the same
data.

This module is pure. It imports no Home Assistant code. The caller passes
``today``.
"""

from __future__ import annotations

import copy
from typing import Any

from . import schedule, templates


def lead(item: dict[str, Any], car: dict[str, Any]) -> tuple[float, int]:
    """The warning window of *item*: its own value, else the value of its car."""
    distance = item.get("lead_distance")
    days = item.get("lead_days")
    return (
        float(distance if distance is not None else car.get("lead_distance") or 0),
        int(days if days is not None else car.get("lead_days") or 0),
    )


def evaluate_item(
    state: dict[str, Any], item: dict[str, Any], today: str, daily: float | None
) -> dict[str, Any]:
    """The evaluation of 1 item."""
    car = state["cars"][item["car_id"]]
    distance, days = lead(item, car)
    return schedule.evaluate(
        item,
        (car.get("odometer") or {}).get("value"),
        daily,
        today,
        lead_distance=distance,
        lead_days=days,
    )


def car_summary(state: dict[str, Any], car_id: str, today: str) -> dict[str, Any]:
    """The computed values of 1 car and of each of its items.

    ``next_item_id`` is the first job in the order of ``schedule.sort_key``.
    ``due_count`` counts the jobs that are ``soon`` or ``overdue``. ``cost_total``
    is the sum of the costs of the service records of the car.
    """
    daily = schedule.daily_distance(state["readings"].get(car_id) or [], today)
    items = [i for i in state["items"].values() if i["car_id"] == car_id]
    evaluations = {i["id"]: evaluate_item(state, i, today, daily) for i in items}
    active = [i for i in items if i.get("enabled", True)]
    ordered = sorted(
        active, key=lambda i: schedule.sort_key(i["name"], evaluations[i["id"]])
    )
    with_limit = [
        i
        for i in ordered
        if evaluations[i["id"]]["distance_limit"] is not None
        or evaluations[i["id"]]["date_limit"] is not None
    ]
    statuses = [evaluations[i["id"]]["status"] for i in active]
    costs = [
        s["cost"]
        for s in state["services"].values()
        if s["car_id"] == car_id and s.get("cost") is not None
    ]
    return {
        "status": schedule.worst(statuses),
        "cost_total": round(sum(costs), 2),
        "daily_distance": daily,
        "next_item_id": with_limit[0]["id"] if with_limit else None,
        "due_count": sum(1 for s in statuses if s != schedule.OK),
        "items": evaluations,
    }


def project_state(
    state: dict[str, Any],
    *,
    today: str,
    tab: bool,
    revision: int,
    presets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """The whole document for a reader, with the computed values.

    Each car gets a ``summary`` key and each item a ``due`` key. The reply also has
    the starter jobs with the overrides of the settings, the tab state, the state of
    the car presets in Home Keeper, the revision and today.
    """
    out = copy.deepcopy(state)
    for car_id, car in out["cars"].items():
        summary = car_summary(state, car_id, today)
        evaluations = summary.pop("items")
        car["summary"] = summary
        for item_id, evaluation in evaluations.items():
            out["items"][item_id]["due"] = evaluation
    out["starter_jobs"] = templates.effective(state["settings"].get("templates") or {})
    out["tab"] = tab
    out["presets"] = presets if presets is not None else {}
    out["revision"] = revision
    out["today"] = today
    return out


def project_car(state: dict[str, Any], car_id: str, today: str) -> dict[str, Any]:
    """1 car with its items, its service records and its readings."""
    car = copy.deepcopy(state["cars"][car_id])
    summary = car_summary(state, car_id, today)
    evaluations = summary.pop("items")
    car["summary"] = summary
    items = []
    for item in state["items"].values():
        if item["car_id"] == car_id:
            items.append({**copy.deepcopy(item), "due": evaluations[item["id"]]})
    services = [
        copy.deepcopy(s) for s in state["services"].values() if s["car_id"] == car_id
    ]
    services.sort(key=lambda s: (s["date"], s.get("logged") or ""), reverse=True)
    return {
        "car": car,
        "items": sorted(items, key=lambda i: schedule.sort_key(i["name"], i["due"])),
        "services": services,
        "readings": copy.deepcopy(state["readings"].get(car_id) or []),
    }
