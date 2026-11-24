"""The coordinator: the read path of the entities, and the runtime data of the entry.

Car Keeper has no external data to poll. The store tells the coordinator about
each change, and the coordinator sends the document to its entities. The
coordinator also holds the parts of a loaded entry that the services, the
websocket commands and the syncs use.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN
from .store import CarStore

if TYPE_CHECKING:
    from .home_keeper import HomeKeeperLink

_LOGGER = logging.getLogger(__name__)


class CarCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Sends the Car Keeper document to the entities after each change."""

    config_entry: ConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, store: CarStore
    ) -> None:
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN)
        self.store = store
        # Set by async_setup_entry.
        self.home_keeper: HomeKeeperLink
        self.tab_registered = False

    async def _async_update_data(self) -> dict[str, Any]:
        """Return the document. A local read never fails."""
        return self.store.state

    @callback
    def async_store_changed(self) -> None:
        """Send the changed document to the entities."""
        self.async_set_updated_data(self.store.state)


def find_coordinator(hass: HomeAssistant) -> CarCoordinator | None:
    """The coordinator of the loaded entry, or None."""
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if isinstance(coordinator, CarCoordinator):
            return coordinator
    return None
