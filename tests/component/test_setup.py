"""Component tests: setup, unload, the Home Keeper tab, the companion, diagnostics."""

from __future__ import annotations

import sys

from homeassistant.helpers import issue_registry as ir

from custom_components.car_keeper.api_surface import SERVICE_NAMES
from custom_components.car_keeper.const import DOMAIN, LANGUAGES
from custom_components.car_keeper.diagnostics import (
    async_get_config_entry_diagnostics,
)

ALICE = "p_alice"

TABS = "home_keeper_panel_tabs"


async def test_setup_registers_every_service(hass, setup_entry) -> None:
    for service in SERVICE_NAMES:
        assert hass.services.has_service(DOMAIN, service), service


async def test_tab_is_registered_with_home_keeper(hass, setup_entry) -> None:
    tabs = hass.data[TABS].tabs()
    assert len(tabs) == 1
    tab = tabs[0]
    assert tab.companion == DOMAIN and tab.id == "cars"
    assert tab.element == "home-keeper-cars-tab"
    assert tab.icon == "mdi:car-wrench" and tab.order == 60 and tab.host_api == 1
    assert tab.module_url.startswith("/car_keeper_static/cars-tab.js?v=")
    assert set(tab.titles) == set(LANGUAGES)
    assert tab.titles["en"] == "Cars" and tab.titles["de"] == "Autos"
    assert setup_entry.runtime_data.tab_registered is True
    assert _issues(hass) == set()


async def test_unload_removes_services_and_the_tab(hass, setup_entry) -> None:
    assert await hass.config_entries.async_unload(setup_entry.entry_id)
    await hass.async_block_till_done()
    for service in SERVICE_NAMES:
        assert not hass.services.has_service(DOMAIN, service)
    assert hass.data[TABS].tabs() == []
    assert await hass.config_entries.async_setup(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert len(hass.data[TABS].tabs()) == 1


async def test_companion_registration(hass, setup_entry) -> None:
    companion = hass.data["home_keeper_fake"]["companions"][DOMAIN]
    assert companion == {
        "domain": DOMAIN,
        "name": "Car Keeper",
        "icon": "mdi:car-wrench",
        "description": "Cars, odometers, maintenance jobs and service history.",
        "config_entry_id": setup_entry.entry_id,
        "docs_url": "https://github.com/prestomation/ha-car-keeper",
        "capabilities": ["import_export"],
    }
    calls = hass.data["home_keeper_fake"]["calls"]
    before = sum(1 for name, _ in calls if name == "register_companion")
    hass.bus.async_fire("home_keeper_register_companions")
    await hass.async_block_till_done()
    after = sum(1 for name, _ in calls if name == "register_companion")
    assert after == before + 1


async def test_companion_registration_survives_a_schema_error(
    hass, setup_entry
) -> None:
    import voluptuous as vol

    from custom_components.car_keeper import home_keeper

    async def _handler(_call) -> None:
        raise AssertionError("the schema refuses the data first")

    # A Home Keeper whose service schema does not know a field of Car Keeper.
    hass.services.async_register(
        "home_keeper", "register_companion", _handler, schema=vol.Schema({})
    )
    await home_keeper.async_register_companion(hass, setup_entry)


def _issues(hass) -> set[str]:
    registry = ir.async_get(hass)
    return {
        issue_id
        for (domain, issue_id) in registry.issues
        if domain == DOMAIN and registry.issues[(domain, issue_id)].active
    }


async def _car_keeper_entry(hass):
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = MockConfigEntry(domain=DOMAIN, options={"unit": "km"})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_repair_issue_cycle(hass, persons, monkeypatch) -> None:
    """No Home Keeper entry, then a loaded one, then an old one, then none."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    entry = await _car_keeper_entry(hass)
    link = entry.runtime_data.home_keeper
    assert _issues(hass) == {"home_keeper_not_set_up"}
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "home_keeper_not_set_up")
    assert issue.translation_key == "home_keeper_not_set_up"
    assert issue.learn_more_url.startswith("https://github.com/prestomation/")
    assert entry.runtime_data.tab_registered is False
    assert hass.services.has_service(DOMAIN, "set_settings")

    hk = MockConfigEntry(domain="home_keeper", title="Home Keeper")
    hk.add_to_hass(hass)
    assert await hass.config_entries.async_setup(hk.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert _issues(hass) == set()
    assert entry.runtime_data.tab_registered is True
    assert link.available
    assert len(hass.data[TABS].tabs()) == 1

    # A Home Keeper with no panel_tabs module is too old.
    monkeypatch.setitem(sys.modules, "custom_components.home_keeper.panel_tabs", None)
    await link.async_refresh()
    assert _issues(hass) == {"home_keeper_too_old"}
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "home_keeper_too_old")
    assert issue.translation_placeholders == {"version": "0.35.0"}
    assert hass.data[TABS].tabs() == []
    monkeypatch.delitem(sys.modules, "custom_components.home_keeper.panel_tabs")

    await link.async_refresh()
    assert _issues(hass) == set() and len(hass.data[TABS].tabs()) == 1

    assert await hass.config_entries.async_unload(hk.entry_id)
    await hass.async_block_till_done(wait_background_tasks=True)
    assert _issues(hass) == {"home_keeper_not_set_up"}
    assert hass.data[TABS].tabs() == []


async def test_old_home_keeper_version_is_too_old(
    hass, persons, hk_entry, monkeypatch
) -> None:
    from homeassistant import loader

    integration = await loader.async_get_integration(hass, "home_keeper")
    monkeypatch.setitem(integration.manifest, "version", "0.34.9")
    entry = await _car_keeper_entry(hass)
    assert _issues(hass) == {"home_keeper_too_old"}
    assert entry.runtime_data.tab_registered is False
    # A beta of a later version passes.
    monkeypatch.setitem(integration.manifest, "version", "0.38.0b5")
    await entry.runtime_data.home_keeper.async_refresh()
    assert _issues(hass) == set()
    assert entry.runtime_data.tab_registered is True


async def test_missing_home_keeper(hass, persons, monkeypatch) -> None:
    from homeassistant.loader import IntegrationNotFound

    from custom_components.car_keeper import home_keeper

    async def _not_found(hass, domain):
        raise IntegrationNotFound(domain)

    monkeypatch.setattr(home_keeper, "async_get_integration", _not_found)
    entry = await _car_keeper_entry(hass)
    assert entry.state.value == "loaded"
    assert _issues(hass) == {"home_keeper_missing"}
    reply = await hass.services.async_call(
        DOMAIN, "set_settings", {"unit": "mi"}, blocking=True, return_response=True
    )
    assert reply == {"settings": {"unit": "mi", "templates": {}}}
    issue = ir.async_get(hass).async_get_issue(DOMAIN, "home_keeper_missing")
    assert issue.translation_placeholders == {
        "url": "https://github.com/prestomation/ha-home-keeper#installation"
    }


def _card_resources(hass) -> list[dict]:
    from homeassistant.components.lovelace.const import LOVELACE_DATA

    return [
        item
        for item in hass.data[LOVELACE_DATA].resources.async_items()
        if "car-keeper-card.js" in str(item.get("url"))
    ]


async def test_resources_read_the_mode_of_an_older_home_assistant(hass) -> None:
    """Before Home Assistant 2026.2, the Lovelace data has `mode` only."""
    from types import SimpleNamespace

    from homeassistant.components.lovelace.const import LOVELACE_DATA

    from custom_components.car_keeper.card import _storage_resources

    resources = object()
    hass.data[LOVELACE_DATA] = SimpleNamespace(mode="storage", resources=resources)
    assert _storage_resources(hass) is resources
    hass.data[LOVELACE_DATA] = SimpleNamespace(mode="yaml", resources=resources)
    assert _storage_resources(hass) is None
    # A newer Home Assistant sets `resource_mode`, and it wins over `mode`.
    hass.data[LOVELACE_DATA] = SimpleNamespace(
        mode="yaml", resource_mode="storage", resources=resources
    )
    assert _storage_resources(hass) is resources


def _extra_card_urls(hass) -> list[str]:
    from homeassistant.components.frontend import DATA_EXTRA_MODULE_URL

    urls = hass.data[DATA_EXTRA_MODULE_URL].urls
    return [u for u in urls if "car-keeper-card.js" in u]


async def test_card_is_a_lovelace_resource_and_not_a_module(hass, setup_entry) -> None:
    """Storage mode uses only the resource: both paths race (Home Keeper #368)."""
    await hass.async_block_till_done()
    rows = _card_resources(hass)
    assert len(rows) == 1
    assert rows[0]["type"] == "module"
    assert rows[0]["url"].startswith("/car_keeper_static/car-keeper-card.js?v=")
    assert _extra_card_urls(hass) == []
    # A reload keeps the 1 row and adds no module URL.
    assert await hass.config_entries.async_reload(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert _card_resources(hass) == rows
    assert _extra_card_urls(hass) == []
    # The removal of the integration removes the row.
    assert await hass.config_entries.async_remove(setup_entry.entry_id)
    await hass.async_block_till_done()
    assert _card_resources(hass) == []
    # A new entry in the same run delivers the card again.
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    again = MockConfigEntry(domain=DOMAIN, data={}, options={}, unique_id=DOMAIN)
    again.add_to_hass(hass)
    assert await hass.config_entries.async_setup(again.entry_id)
    await hass.async_block_till_done()
    assert len(_card_resources(hass)) == 1


async def test_card_is_a_module_when_resources_are_yaml(
    hass, persons, hk_entry, monkeypatch
) -> None:
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    from custom_components.car_keeper import card

    monkeypatch.setattr(card, "_storage_resources", lambda hass: None)
    entry = MockConfigEntry(domain=DOMAIN, data={}, options={}, unique_id=DOMAIN)
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    urls = _extra_card_urls(hass)
    assert len(urls) == 1
    assert urls[0].startswith("/car_keeper_static/car-keeper-card.js?v=")
    assert _card_resources(hass) == []
    assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert _extra_card_urls(hass) == []


async def test_diagnostics_redact_the_vin_and_the_plate(hass, setup_entry) -> None:
    store = setup_entry.runtime_data.store
    store.state["cars"]["c1"] = {
        "id": "c1",
        "name": "Civic",
        "vin": "1HGCM82633A004352",
        "plate": "ABC-123",
    }
    data = await async_get_config_entry_diagnostics(hass, setup_entry)
    text = str(data)
    for secret in ("1HGCM82633A004352", "ABC-123"):
        assert secret not in text, secret
    assert data["document"]["cars"]["c1"]["name"] == "Civic"
    assert data["counts"]["cars"] == 1 and data["tab_registered"] is True
    assert data["home_keeper_reason"] is None
    assert data["entry"]["options"] == {"unit": "km"}
