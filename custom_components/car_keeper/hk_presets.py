"""Registers the car presets of Car Keeper in Home Keeper.

:func:`presets.transition` decides when to call. This class feeds it the events of
Home Assistant and runs the calls 1 at a time. A run registers while Car Keeper runs and
removes the presets after the stop, by the state when the run starts:

* ``start`` at setup, and ``stop`` at unload;
* ``service_added`` and ``service_removed`` when Home Keeper adds or removes
  ``register_presets``, so a Home Keeper that loads after Car Keeper gets the presets;
* ``ask`` on ``home_keeper_register_companions`` and each time Home Keeper becomes
  available.

A Home Keeper with no ``register_presets`` (0.35.0 to 0.38.0b4) gets no call, no
repair issue and no log line above debug. A refused call logs a warning, because each
row passes the Home Keeper check in the tests.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EVENT_SERVICE_REGISTERED, EVENT_SERVICE_REMOVED
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_send

from . import presets
from .const import (
    DOMAIN,
    HOME_KEEPER_DOMAIN,
    HOME_KEEPER_EVENT_REGISTER_COMPANIONS,
    SIGNAL_STORE_CHANGED,
)
from .home_keeper import HomeKeeperLink
from .store import CarStore

_LOGGER = logging.getLogger(__name__)


class PresetSync:
    """Keeps the presets of Car Keeper in Home Keeper for the run."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: CarStore,
        link: HomeKeeperLink,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._store = store
        self._link = link
        self.state = presets.Link()
        self._lock = asyncio.Lock()
        self._unsubs: list[Callable[[], None]] = []

    def _has_service(self) -> bool:
        return self._hass.services.has_service(
            HOME_KEEPER_DOMAIN, presets.SERVICE_REGISTER
        )

    @callback
    def async_start(self) -> None:
        """Listen to Home Keeper, and register now if it has the service."""

        @callback
        def _service(event: Event[Any]) -> None:
            if (
                event.data.get("domain") == HOME_KEEPER_DOMAIN
                and event.data.get("service") == presets.SERVICE_REGISTER
            ):
                added = event.event_type == EVENT_SERVICE_REGISTERED
                kind = "service_added" if added else "service_removed"
                self._feed(presets.Event(kind))

        @callback
        def _ask(*_args: Any) -> None:
            self._feed(presets.Event("ask"))

        self._unsubs += [
            self._hass.bus.async_listen(EVENT_SERVICE_REGISTERED, _service),
            self._hass.bus.async_listen(EVENT_SERVICE_REMOVED, _service),
            self._hass.bus.async_listen(HOME_KEEPER_EVENT_REGISTER_COMPANIONS, _ask),
            self._link.async_add_listener(_ask),
        ]
        self._feed(presets.Event("start"))
        if self._has_service():
            self._feed(presets.Event("service_added"))

    async def async_stop(self) -> None:
        """Stop the listeners and take the presets out of Home Keeper."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()
        self.state, call = presets.transition(self.state, presets.Event("stop"))
        if call == presets.UNREGISTER and self._has_service():
            async with self._lock:
                await self._unregister()

    @callback
    def _feed(self, event: presets.Event) -> None:
        before = self.state
        self.state, call = presets.transition(self.state, event)
        if call is not None:
            self._entry.async_create_background_task(
                self._hass, self._run(), "car_keeper presets"
            )
        if presets.status(before) != presets.status(self.state):
            self._changed()

    @callback
    def _changed(self) -> None:
        # The tab and the cards read the state again on this signal.
        async_dispatcher_send(self._hass, SIGNAL_STORE_CHANGED, self._store.revision)

    async def _run(self) -> None:
        async with self._lock:
            if not self._has_service():
                return
            # The state when the lock is free decides, not the call that queued this
            # run. So the last run always matches the newest state, and a run that
            # waited past the stop removes the presets.
            if not self.state.running:
                await self._unregister()
                return
            try:
                response = await self._hass.services.async_call(
                    HOME_KEEPER_DOMAIN,
                    presets.SERVICE_REGISTER,
                    presets.registration(DOMAIN),
                    blocking=True,
                    return_response=True,
                )
            except (HomeAssistantError, ValueError, vol.Invalid) as err:
                _LOGGER.warning("Home Keeper refused the car presets: %s", err)
                self._feed(presets.Event("refused", error=str(err)))
                return
            ids = (response or {}).get("preset_ids")
            clean = tuple(str(i) for i in ids) if isinstance(ids, list) else ()
            self._feed(presets.Event("accepted", preset_ids=clean))

    async def _unregister(self) -> None:
        try:
            await self._hass.services.async_call(
                HOME_KEEPER_DOMAIN,
                presets.SERVICE_UNREGISTER,
                {"domain": DOMAIN},
                blocking=True,
            )
        except (HomeAssistantError, ValueError, vol.Invalid) as err:
            _LOGGER.debug("Cannot remove the car presets: %s", err)
