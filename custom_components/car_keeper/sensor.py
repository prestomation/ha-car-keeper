"""The sensors of each car: the odometer, the next due distance and date, the status.

* ``odometer``: the reading in the unit of the car. The attribute ``reading`` is the
  same number. It does not follow a display unit that a user sets, and the Home
  Keeper usage tasks of the car read it.
* ``next_due_distance``: the distance left to the nearest distance limit.
* ``next_due_date``: the nearest date limit.
* ``status``: ``ok``, ``soon`` or ``overdue``, the worst status of the jobs.

The odometer sensor reads its value from the store, so it has its value at once
after a restart and Home Keeper never sees it as unavailable.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import CarKeeperConfigEntry
from .const import UNIT_MI
from .coordinator import CarCoordinator
from .entity import CarEntity, async_track_cars
from .schedule import STATUSES

PARALLEL_UPDATES = 0


def _length(unit: str) -> str:
    return UnitOfLength.MILES if unit == UNIT_MI else UnitOfLength.KILOMETERS


class OdometerSensor(CarEntity, SensorEntity):
    """The odometer of a car."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: CarCoordinator, car_id: str) -> None:
        super().__init__(coordinator, car_id, "odometer")

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit of the car."""
        return _length(self.car.get("unit", "km"))

    @property
    def native_value(self) -> float | None:
        """The last reading."""
        return (self.car.get("odometer") or {}).get("value")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The reading in the unit of the car, and where it came from."""
        odometer = self.car.get("odometer") or {}
        return {
            "reading": odometer.get("value"),
            "unit": self.car.get("unit"),
            "source": odometer.get("source"),
            "updated": odometer.get("updated"),
        }


def _nearest(
    sensor: CarEntity, key: str
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """The item with the smallest *key* value, and its evaluation."""
    summary = sensor.summary()
    state = sensor.coordinator.store.state
    best: tuple[Any, str] | None = None
    for item_id, evaluation in summary["items"].items():
        value = evaluation.get(key)
        if value is None:
            continue
        if best is None or (value, item_id) < best:
            best = (value, item_id)
    if best is None:
        return None, None
    return state["items"][best[1]], summary["items"][best[1]]


class NextDueDistanceSensor(CarEntity, SensorEntity):
    """The distance left to the nearest distance limit."""

    _attr_device_class = SensorDeviceClass.DISTANCE
    _attr_suggested_display_precision = 0

    def __init__(self, coordinator: CarCoordinator, car_id: str) -> None:
        super().__init__(coordinator, car_id, "next_due_distance")

    @property
    def native_unit_of_measurement(self) -> str:
        """The unit of the car."""
        return _length(self.car.get("unit", "km"))

    @property
    def native_value(self) -> float | None:
        """The distance left. It is negative when the job is overdue."""
        _, evaluation = _nearest(self, "distance_left")
        return None if evaluation is None else round(evaluation["distance_left"], 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The job and its limit."""
        item, evaluation = _nearest(self, "distance_left")
        return {
            "item_id": item["id"] if item else None,
            "job": item["name"] if item else None,
            "distance_limit": evaluation["distance_limit"] if evaluation else None,
            "status": evaluation["status"] if evaluation else None,
        }


class NextDueDateSensor(CarEntity, SensorEntity):
    """The nearest date limit."""

    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: CarCoordinator, car_id: str) -> None:
        super().__init__(coordinator, car_id, "next_due_date")

    @property
    def native_value(self) -> dt.date | None:
        """The date of the nearest date limit."""
        _, evaluation = _nearest(self, "days_left")
        if evaluation is None:
            return None
        return dt.date.fromisoformat(str(evaluation["date_limit"]))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The job and the days left."""
        item, evaluation = _nearest(self, "days_left")
        return {
            "item_id": item["id"] if item else None,
            "job": item["name"] if item else None,
            "days_left": evaluation["days_left"] if evaluation else None,
            "status": evaluation["status"] if evaluation else None,
        }


class StatusSensor(CarEntity, SensorEntity):
    """The worst status of the jobs of a car."""

    _attr_device_class = SensorDeviceClass.ENUM

    def __init__(self, coordinator: CarCoordinator, car_id: str) -> None:
        super().__init__(coordinator, car_id, "status")
        self._attr_options = list(STATUSES)

    @property
    def native_value(self) -> str:
        """``ok``, ``soon`` or ``overdue``."""
        return str(self.summary()["status"])

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The next job and the jobs that are due."""
        summary = self.summary()
        items = self.coordinator.store.state["items"]
        due = sorted(
            items[i]["name"]
            for i, evaluation in summary["items"].items()
            if evaluation["status"] != "ok"
        )
        next_id = summary["next_item_id"]
        return {
            "next_item_id": next_id,
            "next_job": items[next_id]["name"] if next_id else None,
            "due_count": summary["due_count"],
            "due_jobs": due,
            "daily_distance": summary["daily_distance"],
        }


def _entities(coordinator: CarCoordinator, car_id: str) -> list[CarEntity]:
    return [
        OdometerSensor(coordinator, car_id),
        NextDueDistanceSensor(coordinator, car_id),
        NextDueDateSensor(coordinator, car_id),
        StatusSensor(coordinator, car_id),
    ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CarKeeperConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the sensors of each car."""
    entry.async_on_unload(
        async_track_cars(hass, entry.runtime_data, async_add_entities, _entities)
    )
