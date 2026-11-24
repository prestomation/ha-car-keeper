"""Component tests: the car presets in Home Keeper (the fake).

The fake Home Keeper has no ``register_presets``, as Home Keeper 0.35.0 to 0.38.0b4.
A test adds the 2 services when it needs a newer Home Keeper, before or after the
setup of Car Keeper.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import issue_registry as ir

from custom_components.car_keeper import presets
from custom_components.car_keeper.const import DOMAIN


async def _settle(hass: HomeAssistant) -> None:
    for _ in range(3):
        await hass.async_block_till_done(wait_background_tasks=True)


def _add_services(hass: HomeAssistant, *, refuse: bool = False) -> list[tuple]:
    calls: list[tuple] = []

    async def register(call: ServiceCall) -> dict[str, Any]:
        calls.append(("register", dict(call.data)))
        if refuse:
            raise ServiceValidationError("rows[0].domain: bad")
        data = call.data
        return {"preset_ids": presets.preset_ids(data["rows"], data["domain"])}

    async def unregister(call: ServiceCall) -> None:
        calls.append(("unregister", dict(call.data)))

    hass.services.async_register(
        "home_keeper",
        presets.SERVICE_REGISTER,
        register,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register("home_keeper", presets.SERVICE_UNREGISTER, unregister)
    return calls


async def _presets(ws) -> dict[str, Any]:
    client = await ws("user")
    await client.send_json_auto_id({"type": f"{DOMAIN}/get_state"})
    reply = await client.receive_json()
    assert reply["success"], reply
    return reply["result"]["presets"]


async def test_an_older_home_keeper_gets_no_call_and_no_issue(
    hass: HomeAssistant, setup_entry, ws, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG, logger="custom_components.car_keeper")
    await _settle(hass)
    out = await _presets(ws)
    assert out["status"] == presets.STATUS_NO_SERVICE
    assert out["preset_ids"] == []
    assert [r["domain"] for r in out["rows"]] == [r["domain"] for r in presets.ROWS]
    issues = ir.async_get(hass).issues
    assert not [key for key in issues if key[0] == DOMAIN]
    ours = [r for r in caplog.records if r.name.startswith("custom_components.car")]
    assert not [r for r in ours if r.levelno >= logging.INFO]


async def test_presets_register_at_setup_and_go_at_unload(
    hass: HomeAssistant, persons, hk_entry, ws
) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    calls = _add_services(hass)
    entry = MockConfigEntry(
        domain=DOMAIN, title="Car Keeper", options={"unit": "km"}, unique_id=DOMAIN
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await _settle(hass)
    registers = [data for kind, data in calls if kind == "register"]
    assert registers[0] == presets.registration(DOMAIN)
    out = await _presets(ws)
    assert out["status"] == presets.STATUS_REGISTERED
    assert out["preset_ids"] == presets.preset_ids(presets.ROWS, DOMAIN)

    assert await hass.config_entries.async_unload(entry.entry_id)
    await _settle(hass)
    assert calls[-1] == ("unregister", {"domain": DOMAIN})


async def test_a_home_keeper_that_gets_the_service_later_gets_the_presets(
    hass: HomeAssistant, setup_entry, ws
) -> None:
    await _settle(hass)
    calls = _add_services(hass)
    await _settle(hass)
    assert [kind for kind, _data in calls] == ["register"]
    assert (await _presets(ws))["status"] == presets.STATUS_REGISTERED

    # Home Keeper asks its companions again after its own setup.
    hass.bus.async_fire("home_keeper_register_companions")
    await _settle(hass)
    assert [kind for kind, _data in calls] == ["register", "register"]

    hass.services.async_remove("home_keeper", presets.SERVICE_REGISTER)
    await _settle(hass)
    assert (await _presets(ws))["status"] == presets.STATUS_NO_SERVICE


async def test_a_refused_registration_shows_failed_and_logs_a_warning(
    hass: HomeAssistant, setup_entry, ws, caplog: pytest.LogCaptureFixture
) -> None:
    await _settle(hass)
    _add_services(hass, refuse=True)
    await _settle(hass)
    out = await _presets(ws)
    assert out["status"] == presets.STATUS_FAILED
    assert "rows[0].domain" in out["error"]
    assert "Home Keeper refused the car presets" in caplog.text


async def test_diagnostics_name_the_preset_status(
    hass: HomeAssistant, setup_entry
) -> None:
    from custom_components.car_keeper.diagnostics import (
        async_get_config_entry_diagnostics,
    )

    await _settle(hass)
    out = await async_get_config_entry_diagnostics(hass, setup_entry)
    assert out["presets"] == presets.STATUS_NO_SERVICE
