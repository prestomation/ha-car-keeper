"""Docker integration: a service call fires the documented bus event.

The HA config has an automation that writes the last
``car_keeper_settings_updated`` event to an ``input_text`` helper, so the test
reads, over real Home Assistant, that the event fired with the right payload. An
integrator sees the event the same way.
"""

from __future__ import annotations

import time


def _wait_for(api, prefix: str) -> str:
    deadline = time.monotonic() + 10
    state: dict = {}
    while time.monotonic() < deadline:
        state = api.get("/api/states/input_text.ck_last_event").json()
        if state.get("state", "").startswith(prefix):
            break
        time.sleep(0.5)
    return str(state.get("state"))


def test_set_settings_fires_the_settings_updated_event(api):
    for unit in ("mi", "km"):
        resp = api.post(
            "/api/services/car_keeper/set_settings?return_response",
            json={"unit": unit},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["service_response"]["settings"]["unit"] == unit
    assert _wait_for(api, "settings_updated:") == "settings_updated:['unit']"
