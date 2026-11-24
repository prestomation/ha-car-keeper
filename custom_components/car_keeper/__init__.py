"""Car Keeper: the cars of a household, as a companion of Home Keeper.

Setup order:

1. Load the string tables and the store.
2. Make the coordinator.
3. Register the frontend and the websocket commands.
4. Set up the entity platforms and register the services.
5. Link to Home Keeper: the tab and the companion, or a repair issue.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType

from . import backend_i18n, card, frontend_assets, home_keeper, websocket_api
from .api_surface import SERVICE_NAMES
from .const import DOMAIN, PLATFORMS, SIGNAL_STORE_CHANGED
from .coordinator import CarCoordinator
from .services import async_register_services
from .store import CarStore

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type CarKeeperConfigEntry = ConfigEntry[CarCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the integration. It has only a config entry."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: CarKeeperConfigEntry) -> bool:
    """Set up Car Keeper from its config entry."""
    await hass.async_add_executor_job(backend_i18n.preload)
    store = CarStore(hass)
    await store.load()

    coordinator = CarCoordinator(hass, entry, store)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    entry.async_on_unload(store.async_add_listener(coordinator.async_store_changed))

    @callback
    def _send_changed() -> None:
        # The websocket subscriptions listen to the signal, not to the store,
        # so they keep working after a reload makes a new store.
        async_dispatcher_send(hass, SIGNAL_STORE_CHANGED, store.revision)

    entry.async_on_unload(store.async_add_listener(_send_changed))

    await frontend_assets.async_register(hass)
    websocket_api.async_register(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    async_register_services(hass)

    # The link checks Home Keeper now and when it changes. It adds the tab only
    # while Home Keeper can take it.
    link = home_keeper.HomeKeeperLink(hass, entry, coordinator)
    coordinator.home_keeper = link
    await link.async_start()
    entry.async_on_unload(link.async_stop)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: CarKeeperConfigEntry) -> bool:
    """Unload the config entry and remove the services."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        # The model is the list of services, so a new service is removed here
        # with no second edit.
        for service in SERVICE_NAMES:
            hass.services.async_remove(DOMAIN, service)
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: CarKeeperConfigEntry) -> None:
    """Remove the card resource when the integration is removed (not on unload)."""
    await card.async_unregister_card(hass)
