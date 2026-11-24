"""Docker integration: touch every surface of the integration once.

The other tests in this tier check one behavior each. This module calls the
diagnostics download, each config flow and options flow step, and every
``car_keeper`` service against the real container. The CI log gate
(``ci/check-ha-log.py``) then reads the container log. Home Assistant runs in
Python dev mode there (see ``docker-compose.yml``), so a blocking call in the
event loop, a coroutine that nobody awaited or a slow callback shows in the log.

The tests prove only that a surface runs and does not crash. The component tier
checks the results.
"""

from __future__ import annotations

DOMAIN = "car_keeper"

# Services that this tier checks only with input that fails the validation.
VALIDATION_ONLY: dict[str, dict] = {}


def _service(api, name: str, data: dict | None = None) -> dict:
    """Call a service and return its response. A 4xx or 5xx fails the test."""
    resp = api.post(f"/api/services/{DOMAIN}/{name}?return_response", json=data or {})
    assert resp.status_code == 200, (name, resp.status_code, resp.text)
    return resp.json().get("service_response") or {}


def _entry_id(api) -> str:
    entries = api.get("/api/config/config_entries/entry").json()
    return next(e["entry_id"] for e in entries if e["domain"] == DOMAIN)


def test_diagnostics_download(api):
    resp = api.get(f"/api/diagnostics/config_entry/{_entry_id(api)}")
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["revision"] >= 0 and "document" in data and "counts" in data
    assert data["tab_registered"] is True


def test_config_flow_aborts_when_the_entry_exists(api):
    resp = api.post("/api/config/config_entries/flow", json={"handler": DOMAIN})
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["type"] == "abort", result
    assert result["reason"] in ("already_configured", "single_instance_allowed")


def test_options_flow_steps(api):
    entry_id = _entry_id(api)
    base = "/api/config/config_entries/options/flow"
    form = api.post(base, json={"handler": entry_id}).json()
    assert form["type"] == "form" and form["step_id"] == "init", form
    done = api.post(f"{base}/{form['flow_id']}", json={"unit": "km"})
    assert done.json()["type"] == "create_entry", done.text


def test_every_service_is_touched(api):
    """Run each service once, in the order of the life of a car."""
    _service(
        api, "set_settings", {"unit": "km", "templates": {"wipers": {"months": 6}}}
    )
    car = _service(
        api,
        "add_car",
        {
            "name": "Surface car",
            "fuel": "petrol",
            "odometer": 1000,
            "starter_jobs": ["engine_oil", "registration"],
            "due_dates": {"registration": "2099-01-01"},
        },
    )["car"]
    car_id = car["id"]
    _service(api, "update_car", {"car_id": car_id, "make": "Test", "unit": "mi"})
    _service(api, "update_car", {"car_id": car_id, "unit": "km"})
    _service(api, "set_odometer", {"car_id": car_id, "value": 1200})
    _service(api, "correct_odometer", {"car_id": car_id, "value": 1100, "offset": 0})
    item = _service(
        api, "add_item", {"car_id": car_id, "name": "Surface job", "interval_months": 6}
    )["item"]
    _service(api, "update_item", {"item_id": item["id"], "interval_months": 7})
    _service(api, "apply_templates", {"car_id": car_id, "starter_jobs": ["wipers"]})
    service = _service(
        api,
        "log_service",
        {"car_id": car_id, "items": [item["id"]], "reading": 1300, "cost": 10},
    )["service"]
    _service(api, "update_service", {"service_id": service["id"], "shop": "Shop"})
    _service(api, "list_cars")
    _service(api, "get_car", {"car_id": car_id})
    _service(api, "list_items", {"car_id": car_id})
    _service(api, "list_services", {"car_id": car_id})
    exported = _service(api, "export_data", {"files_dir": "/tmp/ck_surface"})
    _service(api, "import_data", {"document": exported, "dry_run": True})
    _service(api, "import_data", {"document": exported})
    _service(api, "delete_service", {"service_id": service["id"]})
    _service(api, "delete_item", {"item_id": item["id"]})
    _service(api, "delete_car", {"car_id": car_id})


def test_every_service_has_a_touch(api):
    """A new service must get a call above, or an entry in VALIDATION_ONLY."""
    import re
    from pathlib import Path

    services_yaml = (
        Path(__file__).resolve().parents[2]
        / "custom_components"
        / DOMAIN
        / "services.yaml"
    )
    # A service name is a key at the start of a line. The pip install of this tier
    # has no YAML parser.
    declared = set(
        re.findall(r"^(\w+):", services_yaml.read_text(encoding="utf-8"), re.M)
    )
    source = Path(__file__).read_text(encoding="utf-8")
    missing = {
        name
        for name in declared
        if name not in VALIDATION_ONLY and f'"{name}"' not in source
    }
    assert not missing, f"no call in test_surfaces.py for: {sorted(missing)}"
