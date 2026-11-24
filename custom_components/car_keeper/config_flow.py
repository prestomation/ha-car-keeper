"""The config flow and the options flow of Car Keeper.

Car Keeper has 1 config entry. The flow first checks Home Keeper. If Home Keeper
is not installed, not set up or too old, the flow stops with the reason and a
link. The only setting is the distance unit of a new car. Its default comes from
the unit system of Home Assistant. The options flow changes it, and merges its
input into the stored options, so a key that the form does not show stays.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import UnitOfLength
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import CONF_UNIT, DOMAIN, NAME, UNIT_KM, UNIT_MI, UNITS
from .home_keeper import async_check, placeholders


def _unit_schema(default: str) -> vol.Schema:
    selector = SelectSelector(
        SelectSelectorConfig(
            options=list(UNITS), translation_key=CONF_UNIT, mode=SelectSelectorMode.LIST
        )
    )
    return vol.Schema({vol.Required(CONF_UNIT, default=default): selector})


def merge_flow_input(entry: ConfigEntry, user_input: dict[str, Any]) -> dict[str, Any]:
    """The stored options with the form input on top."""
    return {**entry.options, **user_input}


class CarKeeperConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add the 1 config entry of Car Keeper."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the distance unit."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        if (reason := await async_check(self.hass)) is not None:
            return self.async_abort(
                reason=reason, description_placeholders=placeholders(reason)
            )
        if user_input is not None:
            return self.async_create_entry(
                title=NAME, data={}, options={CONF_UNIT: user_input[CONF_UNIT]}
            )
        miles = self.hass.config.units.length_unit == UnitOfLength.MILES
        default = UNIT_MI if miles else UNIT_KM
        return self.async_show_form(step_id="user", data_schema=_unit_schema(default))

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow."""
        return CarKeeperOptionsFlow()


class CarKeeperOptionsFlow(OptionsFlow):
    """Change the distance unit of a new car."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the unit form."""
        if user_input is not None:
            return self.async_create_entry(
                data=merge_flow_input(
                    self.config_entry, {CONF_UNIT: user_input[CONF_UNIT]}
                )
            )
        current = self.config_entry.options.get(CONF_UNIT, UNIT_KM)
        return self.async_show_form(step_id="init", data_schema=_unit_schema(current))
