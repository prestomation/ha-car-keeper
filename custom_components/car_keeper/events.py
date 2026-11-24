"""The pure payload builders of the Car Keeper bus events.

Each event is ``car_keeper_<noun>_<verb>``. The store fires it after the save,
so a change from the tab, a service or a Home Keeper task fires the same event.
Every user can listen to the bus, and every read is open to every user, so a
payload can hold each value of a record. A payload copies each list, so a caller
never aliases the stored document.

This module is pure. It imports no Home Assistant code.
"""

from __future__ import annotations

from typing import Any


def settings_event_data(
    changed_fields: list[str], origin: str | None
) -> dict[str, Any]:
    """The payload of ``settings_updated``."""
    return {"changed_fields": list(changed_fields), "origin": origin}


def car_event_data(car: dict[str, Any], origin: str | None) -> dict[str, Any]:
    """The payload of ``car_added`` and ``car_removed``."""
    return {"car_id": car["id"], "name": car["name"], "origin": origin}


def changed_data(base: dict[str, Any], changed_fields: list[str]) -> dict[str, Any]:
    """A ``*_updated`` payload: the spine and the names of the changed fields."""
    return {**base, "changed_fields": list(changed_fields)}


def odometer_event_data(
    car: dict[str, Any], reading: dict[str, Any], origin: str | None
) -> dict[str, Any]:
    """The payload of ``odometer_updated``."""
    return {
        "car_id": car["id"],
        "name": car["name"],
        "value": reading["value"],
        "unit": car["unit"],
        "source": reading["source"],
        "origin": origin,
    }


def item_event_data(item: dict[str, Any], origin: str | None) -> dict[str, Any]:
    """The payload of ``item_added`` and ``item_removed``."""
    return {
        "car_id": item["car_id"],
        "item_id": item["id"],
        "name": item["name"],
        "origin": origin,
    }


def due_event_data(
    car: dict[str, Any], item: dict[str, Any], evaluation: dict[str, Any]
) -> dict[str, Any]:
    """The payload of ``item_due_soon`` and ``item_overdue``."""
    return {
        "car_id": car["id"],
        "car_name": car["name"],
        "item_id": item["id"],
        "name": item["name"],
        "status": evaluation["status"],
        "first": evaluation["first"],
        "distance_limit": evaluation["distance_limit"],
        "distance_left": evaluation["distance_left"],
        "date_limit": evaluation["date_limit"],
        "days_left": evaluation["days_left"],
        "unit": car["unit"],
    }


def service_event_data(service: dict[str, Any], origin: str | None) -> dict[str, Any]:
    """The payload of ``service_logged`` and ``service_removed``."""
    return {
        "car_id": service["car_id"],
        "service_id": service["id"],
        "date": service["date"],
        "reading": service.get("reading"),
        "items": list(service.get("items") or []),
        "shop": service.get("shop") or "",
        "cost": service.get("cost"),
        "origin": origin,
    }


def data_imported_event_data(
    counts: dict[str, dict[str, int]], origin: str | None
) -> dict[str, Any]:
    """The payload of ``data_imported``."""
    return {
        "counts": {name: dict(value) for name, value in counts.items()},
        "origin": origin,
    }
