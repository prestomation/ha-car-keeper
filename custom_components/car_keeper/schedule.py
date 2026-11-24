"""The due rule: when a job is due, and its status.

:func:`evaluate` takes 1 item, the odometer of its car, the daily distance and the
date of today. It returns the limits of the item and its status:

* The **distance limit** is the reading of the base plus ``interval_distance``,
  rounded to 1 decimal as a reading is.
* The **date limit** is the date of the base plus ``interval_months``, or the
  ``due_date`` of a date item.
* The base is ``last_done``, or ``start`` for an item that was never done.
* A limit is ``overdue`` when the odometer or today is at or past it, ``soon``
  inside the warning window, else ``ok``. The status of the item is the worst of
  its limits. The status of a car is the worst of its items.
* **First.** The rule divides the distance left by the daily distance to compare
  it with a date. The limit with fewer days is first. With no daily distance, the
  date limit is first.

``frontend/src/schedule.ts`` is the same rule in TypeScript. The golden corpus
``tests/fixtures/shared/schedule.json`` holds the 2 copies together.

This module is pure. It imports no Home Assistant code. Each date is a string
``YYYY-MM-DD`` and the caller passes ``today``.
"""

from __future__ import annotations

import calendar
import datetime as dt
from collections.abc import Iterable, Mapping
from typing import Any

from .units import round_reading

OK = "ok"
SOON = "soon"
OVERDUE = "overdue"
STATUSES = (OK, SOON, OVERDUE)
RANK = {OK: 0, SOON: 1, OVERDUE: 2}

#: The days of readings that the daily distance reads.
DAILY_WINDOW_DAYS = 90
#: The shortest span of readings that gives a daily distance.
DAILY_MIN_DAYS = 7


def parse_date(value: str) -> dt.date:
    """The date of ``YYYY-MM-DD``, or of the date part of an ISO timestamp."""
    return dt.date.fromisoformat(value[:10])


def add_months(value: str, months: int) -> str:
    """*value* plus *months*. A day past the end of the month moves to its last day."""
    day = parse_date(value)
    total = day.year * 12 + day.month - 1 + months
    year, month = divmod(total, 12)
    last = calendar.monthrange(year, month + 1)[1]
    return dt.date(year, month + 1, min(day.day, last)).isoformat()


def days_between(start: str, end: str) -> int:
    """The days from *start* to *end*. Negative when *end* is earlier."""
    return (parse_date(end) - parse_date(start)).days


def worst(statuses: Iterable[str]) -> str:
    """The worst status of *statuses*, or ``ok`` for none."""
    return max(statuses, key=lambda s: RANK[s], default=OK)


def daily_distance(readings: Iterable[Mapping[str, Any]], today: str) -> float | None:
    """The average distance a day over the last 90 days, or None.

    The rule uses the readings of the window, from the first to the last. It needs
    a span of 7 days or more. A distance that goes down gives 0.
    """
    start = parse_date(today) - dt.timedelta(days=DAILY_WINDOW_DAYS)
    points = sorted(
        (parse_date(str(r["ts"])), float(r["value"]))
        for r in readings
        if parse_date(str(r["ts"])) >= start
    )
    if len(points) < 2:
        return None
    span = (points[-1][0] - points[0][0]).days
    if span < DAILY_MIN_DAYS:
        return None
    return max(0.0, (points[-1][1] - points[0][1]) / span)


def date_due(item: Mapping[str, Any], lead_days: int) -> str | None:
    """The next due date of a date item, or None when it is done for good.

    With no service, it is ``due_date``. A service on a day after the warning window
    of a due date opens moves the job to the next due date. With
    ``interval_months``, the due dates repeat from ``due_date``. Without it, the job
    has no next due date.
    """
    due = item.get("due_date")
    done = item.get("last_done")
    if not due or not done:
        return due
    months = item.get("interval_months")
    step = 0
    current = str(due)
    while days_between(str(done["date"]), current) <= lead_days:
        if not months:
            return None
        step += 1
        current = add_months(str(due), int(months) * step)
    return current


def _limit_status(left: float, lead: float) -> str:
    if left <= 0:
        return OVERDUE
    if left <= lead:
        return SOON
    return OK


def evaluate(
    item: Mapping[str, Any],
    odometer: float | None,
    daily: float | None,
    today: str,
    *,
    lead_distance: float,
    lead_days: int,
) -> dict[str, Any]:
    """The limits and the status of 1 item.

    *lead_distance* and *lead_days* are the warning window that applies: the value
    of the item, else of the car. The reply keys are always there. A limit that the
    item does not have is None.
    """
    base = item.get("last_done") or item.get("start") or {}
    out: dict[str, Any] = {
        "status": OK,
        "first": None,
        "distance_limit": None,
        "distance_left": None,
        "date_limit": None,
        "days_left": None,
        "eta_days": None,
    }
    if not item.get("enabled", True):
        return out
    statuses = []
    distance_days: float | None = None
    interval = item.get("interval_distance")
    if interval and base.get("reading") is not None and odometer is not None:
        limit = round_reading(float(base["reading"]) + float(interval))
        left = round_reading(limit - float(odometer))
        out["distance_limit"] = limit
        out["distance_left"] = left
        statuses.append(_limit_status(left, lead_distance))
        if daily:
            distance_days = max(0.0, left) / daily
        elif left <= 0:
            distance_days = 0.0
    date_limit = None
    if item.get("kind") == "date":
        date_limit = date_due(item, lead_days)
    elif item.get("interval_months") and base.get("date"):
        date_limit = add_months(str(base["date"]), int(item["interval_months"]))
    if date_limit:
        days = days_between(today, date_limit)
        out["date_limit"] = date_limit
        out["days_left"] = days
        statuses.append(_limit_status(days, lead_days))
    if date_limit is not None and distance_days is not None:
        out["first"] = "distance" if distance_days < out["days_left"] else "date"
    elif date_limit is not None:
        out["first"] = "date"
    elif out["distance_limit"] is not None:
        out["first"] = "distance"
    etas = [d for d in (distance_days, out["days_left"]) if d is not None]
    out["eta_days"] = min(etas) if etas else None
    out["status"] = worst(statuses)
    return out


def sort_key(name: str, evaluation: Mapping[str, Any]) -> tuple[int, float, str]:
    """The order of the jobs of a car: the worst status, then the nearest limit.

    A job with no known time to its limit comes after the ones with a time.
    """
    eta = evaluation.get("eta_days")
    return (
        -RANK[evaluation["status"]],
        float(eta) if eta is not None else float("inf"),
        name.casefold(),
    )
