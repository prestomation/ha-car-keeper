"""Docker integration: Car Keeper loads next to the real Home Keeper.

The container has the real Home Keeper component (``ci/fetch-home-keeper.sh``)
and a seeded config entry for each integration, so both load at startup.
"""

from __future__ import annotations

from pathlib import Path

import pytest

DOMAIN = "car_keeper"
DIST = Path(__file__).resolve().parents[2] / "custom_components" / DOMAIN / "frontend"
DIST = DIST / "dist"


def test_both_config_entries_are_loaded(api):
    entries = api.get("/api/config/config_entries/entry").json()
    states = {e["domain"]: e["state"] for e in entries}
    assert states.get("home_keeper") == "loaded", states
    assert states.get(DOMAIN) == "loaded", states


def test_services_registered(api):
    resp = api.get("/api/services")
    assert resp.status_code == 200
    domains = {block["domain"]: block for block in resp.json()}
    assert DOMAIN in domains
    assert {"set_settings", "add_car", "log_service", "list_cars"} <= set(
        domains[DOMAIN]["services"]
    )


def test_a_car_gets_its_entities(api):
    resp = api.post(
        "/api/services/car_keeper/add_car?return_response",
        json={"name": "Entity car", "odometer": 4321},
    )
    assert resp.status_code == 200, resp.text
    car_id = resp.json()["service_response"]["car"]["id"]
    try:
        states = api.get("/api/states").json()
        ours = {
            s["entity_id"]: s
            for s in states
            if str(s["attributes"].get("friendly_name", "")).startswith("Entity car")
        }
        domains = sorted({e.split(".")[0] for e in ours})
        assert domains == ["binary_sensor", "sensor", "todo"], ours
        odometer = next(s for s in ours.values() if "reading" in s["attributes"])
        # Home Assistant shows the state in its own unit. `reading` is in the car unit.
        assert odometer["attributes"]["reading"] == 4321.0
    finally:
        api.post("/api/services/car_keeper/delete_car", json={"car_id": car_id})
    states = api.get("/api/states").json()
    left = [
        s["entity_id"]
        for s in states
        if str(s["attributes"].get("friendly_name", "")).startswith("Entity car")
        and s["state"] != "unavailable"
    ]
    assert left == []


def test_get_state_and_the_tab(ws):
    state = ws("car_keeper/get_state")
    assert state["success"], state
    result = state["result"]
    assert result["tab"] is True and result["settings"]["unit"] == "km"
    tabs = ws("home_keeper/get_panel_tabs")
    assert tabs["success"], tabs
    rows = tabs["result"]
    rows = rows["tabs"] if isinstance(rows, dict) else rows
    tab = next(t for t in rows if t["companion"] == DOMAIN)
    assert tab["id"] == "cars" and tab["element"] == "home-keeper-cars-tab"
    assert tab["module_url"].startswith("/car_keeper_static/cars-tab.js")
    assert tab["title"] == "Cars"


def test_no_repair_issue_with_home_keeper(ws):
    issues = ws("repairs/list_issues")
    assert issues["success"], issues
    ours = [i for i in issues["result"]["issues"] if i["domain"] == DOMAIN]
    assert ours == []


def test_companion_is_registered(api):
    resp = api.post("/api/services/home_keeper/list_companions?return_response")
    assert resp.status_code == 200, resp.text
    text = str(resp.json()["service_response"])
    assert DOMAIN in text and "import_export" in text


@pytest.mark.parametrize("bundle", ["cars-tab.js", "car-keeper-card.js"])
def test_bundles_served(api, bundle):
    if not (DIST / bundle).exists():
        pytest.skip(f"frontend/dist/{bundle} is not built")
    resp = api.get(f"/car_keeper_static/{bundle}")
    assert resp.status_code == 200
    assert len(resp.text) > 100
