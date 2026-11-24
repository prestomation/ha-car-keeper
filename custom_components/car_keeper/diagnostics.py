"""Diagnostics of Car Keeper.

The download has the config entry, the tab state, the counts and the Car Keeper
document. A user attaches the download to a public issue, so it redacts the VIN
and the plate of each car. That is a rule for a support file. It is not access
control: every user can read the VIN and the plate in Home Assistant.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import CarKeeperConfigEntry

TO_REDACT = {"vin", "plate"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: CarKeeperConfigEntry
) -> dict[str, Any]:
    """The diagnostics of the config entry."""
    coordinator = entry.runtime_data
    state = coordinator.store.state
    return {
        "entry": {
            "title": entry.title,
            "version": entry.version,
            "options": dict(entry.options),
        },
        "tab_registered": coordinator.tab_registered,
        "home_keeper_reason": coordinator.home_keeper.reason,
        "revision": coordinator.store.revision,
        "counts": {
            name: len(value)
            for name, value in state.items()
            if isinstance(value, dict | list) and name != "settings"
        },
        "document": async_redact_data(state, TO_REDACT),
    }
