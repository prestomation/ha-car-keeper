"""The binary sensor of each car: on when a job is overdue."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import CarKeeperConfigEntry
from .coordinator import CarCoordinator
from .entity import CarEntity, async_track_cars
from .schedule import OVERDUE

PARALLEL_UPDATES = 0


class OverdueSensor(CarEntity, BinarySensorEntity):
    """On when a job of the car is overdue."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, coordinator: CarCoordinator, car_id: str) -> None:
        super().__init__(coordinator, car_id, "overdue")

    @property
    def is_on(self) -> bool:
        """Whether a job is overdue."""
        return bool(self.summary()["status"] == OVERDUE)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The names of the jobs that are overdue."""
        items = self.coordinator.store.state["items"]
        return {
            "overdue_jobs": sorted(
                items[i]["name"]
                for i, evaluation in self.summary()["items"].items()
                if evaluation["status"] == OVERDUE
            )
        }


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CarKeeperConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the binary sensor of each car."""
    entry.async_on_unload(
        async_track_cars(
            hass,
            entry.runtime_data,
            async_add_entities,
            lambda coordinator, car_id: [OverdueSensor(coordinator, car_id)],
        )
    )
