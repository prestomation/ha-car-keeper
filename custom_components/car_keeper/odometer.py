"""The odometer follower: it copies the state of each bound sensor into the store.

A car with an ``entity`` odometer names a sensor. :class:`OdometerFollower` listens
to the state of each of these sensors, and to each store change, which can bind or
unbind a sensor. Each new state goes to ``CarStore.entity_reading``, which applies
``readings.from_entity``. A second lower value shows a repair issue for the car.
An admin correction (``correct_odometer``) deletes the issue.

A sensor that goes away or that has no number changes nothing: the car keeps its
last reading.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.const import ATTR_UNIT_OF_MEASUREMENT
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .coordinator import CarCoordinator

_LOGGER = logging.getLogger(__name__)


class OdometerFollower:
    """Follows the odometer sensor of each bound car."""

    def __init__(self, hass: HomeAssistant, coordinator: CarCoordinator) -> None:
        self._hass = hass
        self._coordinator = coordinator
        self._bound: dict[str, str] = {}
        self._unsub_states: Callable[[], None] | None = None
        self._unsub_store: Callable[[], None] | None = None

    def _wanted(self) -> dict[str, str]:
        """The bound sensor of each car, by car id."""
        out = {}
        for car_id, car in self._coordinator.store.state["cars"].items():
            odometer = car.get("odometer") or {}
            if odometer.get("source") == "entity" and odometer.get("entity_id"):
                out[car_id] = str(odometer["entity_id"])
        return out

    @callback
    def async_start(self) -> None:
        """Listen, and read each bound sensor 1 time now."""
        self._unsub_store = self._coordinator.store.async_add_listener(self._rebind)
        self._rebind()
        for car_id, entity_id in self._bound.items():
            state = self._hass.states.get(entity_id)
            if state is not None:
                self._schedule(car_id, state.state, state.attributes)

    @callback
    def async_stop(self) -> None:
        """Stop listening."""
        if self._unsub_store is not None:
            self._unsub_store()
            self._unsub_store = None
        if self._unsub_states is not None:
            self._unsub_states()
            self._unsub_states = None

    @callback
    def _rebind(self) -> None:
        wanted = self._wanted()
        if wanted == self._bound:
            return
        new = {c: e for c, e in wanted.items() if self._bound.get(c) != e}
        self._bound = wanted
        if self._unsub_states is not None:
            self._unsub_states()
            self._unsub_states = None
        if wanted:
            self._unsub_states = async_track_state_change_event(
                self._hass, sorted(set(wanted.values())), self._changed
            )
        for car_id, entity_id in new.items():
            state = self._hass.states.get(entity_id)
            if state is not None:
                self._schedule(car_id, state.state, state.attributes)

    @callback
    def _changed(self, event: Event[EventStateChangedData]) -> None:
        state = event.data["new_state"]
        if state is None:
            return
        for car_id, entity_id in self._bound.items():
            if entity_id == state.entity_id:
                self._schedule(car_id, state.state, state.attributes)

    @callback
    def _schedule(self, car_id: str, raw: Any, attributes: Any) -> None:
        unit = attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        self._coordinator.config_entry.async_create_background_task(
            self._hass, self._apply(car_id, raw, unit), "car_keeper odometer"
        )

    async def _apply(self, car_id: str, raw: Any, unit: str | None) -> None:
        if car_id not in self._coordinator.store.state["cars"]:
            return
        outcome = await self._coordinator.store.entity_reading(car_id, raw, unit)
        if outcome.issue:
            self._coordinator.raise_odometer_issue(
                car_id, float(outcome.odometer["lower"])
            )
