"""The Car Keeper store: the 1 write path for Car Keeper data.

Every change goes through a method of :class:`CarStore`. Each method checks the
input with the pure core, changes the document, saves it, fires the bus events of
the change and then tells the listeners (the coordinator, the ``subscribe``
command and the syncs). Entities, the tab and the cards read the document and
never write it.

``revision`` goes up by 1 on each change. The ``subscribe`` websocket command
sends it, and the client then reads ``get_state`` again.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import events, models
from .const import (
    EVENT_SETTINGS_UPDATED,
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

Event = tuple[str, dict[str, Any]]


class _CarStorage(Store[dict[str, Any]]):
    """The storage file, with the migration hook."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Return the document in the current version.

        Version 1.1 is the first version. ``models.normalize_state`` adds each
        missing section, so a new section needs no migration step.
        """
        return models.normalize_state(old_data)


def today() -> str:
    """Today in the time zone of Home Assistant, as ``YYYY-MM-DD``."""
    return dt_util.now().date().isoformat()


def now() -> str:
    """The time now, aware, in ISO 8601."""
    return dt_util.now().isoformat()


class CarStore:
    """Loads, saves and changes the Car Keeper document, and fires the events."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._storage = _CarStorage(
            hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_MINOR_VERSION
        )
        self.state: dict[str, Any] = models.empty_state()
        self.revision = 0
        self._listeners: list[Callable[[], None]] = []

    async def load(self) -> None:
        """Load the document, or start an empty one."""
        self.state = models.normalize_state(await self._storage.async_load())

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Call *listener* after each change. Return a callable that removes it."""
        self._listeners.append(listener)

        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                _LOGGER.exception("A Car Keeper store listener failed")

    async def _commit(self, fired: list[Event]) -> None:
        """Save, fire the events and tell the listeners."""
        await self._storage.async_save(self.state)
        self.revision += 1
        for name, data in fired:
            self.hass.bus.async_fire(name, data)
        self._notify_listeners()

    # ── Settings ─────────────────────────────────────────────────────────────

    async def set_settings(
        self, changes: dict[str, Any], *, origin: str | None = None
    ) -> dict[str, Any]:
        """Change the settings. A call that changes no value fires no event."""
        settings = self.state["settings"]
        changed = sorted(k for k, v in changes.items() if settings.get(k) != v)
        if not changed:
            return dict(settings)
        self.state["settings"] = {**settings, **{k: changes[k] for k in changed}}
        await self._commit(
            [(EVENT_SETTINGS_UPDATED, events.settings_event_data(changed, origin))]
        )
        return dict(self.state["settings"])
