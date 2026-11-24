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
    """Run each service once."""
    _service(api, "set_settings", {"unit": "km"})


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
