"""The service history: which service did each job last, and the moves of stock.

A service record can do many jobs. ``last_done`` of a job is the latest service
that did it: the latest date, then the highest reading, then the latest time of
logging. A service with an earlier date goes in the history and does not move
``last_done`` back. A change or a delete of a service computes ``last_done``
again, so the value always follows from the history (:func:`last_done`).

A service can use parts. :func:`stock_moves` gives the change of each part count
between 2 versions of a service, so an edit or a delete gives the parts back.

This module is pure. It imports no Home Assistant code.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


def _order(service: Mapping[str, Any]) -> tuple[str, float, str]:
    reading = service.get("reading")
    return (
        str(service["date"]),
        float(reading) if reading is not None else -1.0,
        str(service.get("logged") or ""),
    )


def last_done(
    item_id: str, services: Iterable[Mapping[str, Any]]
) -> dict[str, Any] | None:
    """The latest service that did *item_id*, as ``{date, reading, service_id}``."""
    done = [s for s in services if item_id in (s.get("items") or [])]
    if not done:
        return None
    latest = max(done, key=_order)
    return {
        "date": latest["date"],
        "reading": latest.get("reading"),
        "service_id": latest["id"],
    }


def refresh(
    items: Mapping[str, dict[str, Any]],
    services: Mapping[str, Mapping[str, Any]],
    item_ids: Iterable[str],
) -> dict[str, dict[str, Any]]:
    """The items of *item_ids* whose ``last_done`` changes, with the new value."""
    out: dict[str, dict[str, Any]] = {}
    for item_id in item_ids:
        item = items.get(item_id)
        if item is None:
            continue
        value = last_done(item_id, services.values())
        if item.get("last_done") != value:
            out[item_id] = {**item, "last_done": value}
    return out


def _part_key(part: Mapping[str, Any]) -> tuple[str, str]:
    return (str(part["asset_id"]), str(part["part_id"]))


def stock_moves(
    before: Iterable[Mapping[str, Any]], after: Iterable[Mapping[str, Any]]
) -> dict[tuple[str, str], float]:
    """The change of each part count from *before* to *after*.

    Each list holds ``{asset_id, part_id, quantity}``. A part that a service uses
    more of has a negative change. A part that is not used any more comes back.
    A part with no change is not in the reply.
    """
    count: dict[tuple[str, str], float] = {}
    for part in before:
        key = _part_key(part)
        count[key] = count.get(key, 0.0) + float(part.get("quantity") or 0)
    for part in after:
        key = _part_key(part)
        count[key] = count.get(key, 0.0) - float(part.get("quantity") or 0)
    return {key: value for key, value in count.items() if value}
