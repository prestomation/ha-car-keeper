"""The base of the entities of each car, and the add and remove of them.

Each car has 1 device, ``(car_keeper, <car id>)``. The entities of the car are on
it, and the unique id of each entity has the car id, so a rename keeps it.
:func:`async_track_cars` adds the entities of a new car after a store change, and
removes the entities and the device of a deleted car.

Every read is open, so an entity shows each value of its car.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import projections
from .const import DOMAIN, NAME
from .coordinator import CarCoordinator
from .store import today


def device_info(car: dict[str, Any]) -> DeviceInfo:
    """The device of a car."""
    model = " ".join(str(v) for v in (car.get("model"), car.get("year")) if v)
    return DeviceInfo(
        identifiers={(DOMAIN, car["id"])},
        name=car["name"],
        manufacturer=car.get("make") or NAME,
        model=model or None,
    )


class CarEntity(CoordinatorEntity[CarCoordinator]):
    """An entity of 1 car."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: CarCoordinator, car_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.car_id = car_id
        self._attr_translation_key = key
        self._attr_unique_id = f"{car_id}_{key}"
        self._attr_device_info = device_info(coordinator.store.state["cars"][car_id])

    @property
    def car(self) -> dict[str, Any]:
        """The stored car."""
        return dict(self.coordinator.store.state["cars"].get(self.car_id) or {})

    @property
    def available(self) -> bool:
        """An entity of a deleted car is not available until the registry removes it."""
        return self.car_id in self.coordinator.store.state["cars"]

    def summary(self) -> dict[str, Any]:
        """The computed values of the car and its items."""
        return projections.car_summary(
            self.coordinator.store.state, self.car_id, today()
        )


def find_device(
    devices: dr.DeviceRegistry, car_id: str, entry_id: str
) -> dr.DeviceEntry | None:
    """The device of a car.

    Home Assistant 2026.9 added ``async_get_device_by_identifier``, and 2026.10
    deprecates ``async_get_device``. The oldest supported Home Assistant has only
    the second one.
    """
    identifier = (DOMAIN, car_id)
    by_identifier = getattr(devices, "async_get_device_by_identifier", None)
    if by_identifier is not None:
        return by_identifier(identifier, entry_id)  # type: ignore[no-any-return]
    return devices.async_get_device(identifiers={identifier})


@callback
def async_track_cars(
    hass: HomeAssistant,
    coordinator: CarCoordinator,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[CarCoordinator, str], Iterable[Entity]],
) -> Callable[[], None]:
    """Add the entities of each car now and of each new car later.

    The device of a deleted car is removed with its entities. Return the callable
    that stops the tracking.
    """
    known: set[str] = set()
    entry_id = coordinator.config_entry.entry_id

    @callback
    def _sync() -> None:
        cars = coordinator.store.state["cars"]
        new = [car_id for car_id in cars if car_id not in known]
        for car_id in new:
            known.add(car_id)
        if new:
            async_add_entities(
                [e for car_id in new for e in factory(coordinator, car_id)]
            )
        gone = [car_id for car_id in known if car_id not in cars]
        if gone:
            devices = dr.async_get(hass)
            for car_id in gone:
                known.discard(car_id)
                device = find_device(devices, car_id, entry_id)
                if device is not None:
                    devices.async_remove_device(device.id)
        # A rename of a car renames its device.
        devices = dr.async_get(hass)
        for car_id, car in cars.items():
            device = find_device(devices, car_id, entry_id)
            info = device_info(car)
            if device is not None and (
                device.name != info.get("name")
                or device.manufacturer != info.get("manufacturer")
                or device.model != info.get("model")
            ):
                devices.async_update_device(
                    device.id,
                    name=info.get("name"),
                    manufacturer=info.get("manufacturer"),
                    model=info.get("model"),
                )

    _sync()
    return coordinator.async_add_listener(_sync)


def remove_stale_entities(
    hass: HomeAssistant, entry_id: str, cars: Iterable[str]
) -> None:
    """Remove the registry entries of the entities of cars that are gone."""
    registry = er.async_get(hass)
    keep = set(cars)
    for entity in er.async_entries_for_config_entry(registry, entry_id):
        car_id = (entity.unique_id or "").split("_", 1)[0]
        if car_id and car_id not in keep:
            registry.async_remove(entity.entity_id)
