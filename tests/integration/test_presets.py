"""Docker integration: the car presets in the real Home Keeper.

A Home Keeper with ``register_presets`` lists the presets of Car Keeper in its picker,
with the ids of ``tests/fixtures/presets.json``. An older Home Keeper has no such
service: Car Keeper then says ``no_service`` and registers nothing. A lane that sets
``CK_EXPECT_PRESETS=1`` must have the service, so a wrong pin fails here.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

GOLDEN = Path(__file__).resolve().parents[1] / "fixtures" / "presets.json"


def _has_service(api) -> bool:
    services = api.get("/api/services").json()
    return any(
        row["domain"] == "home_keeper" and "register_presets" in row["services"]
        for row in services
    )


def _state(ws) -> dict:
    reply = ws("car_keeper/get_state")
    assert reply["success"], reply
    return reply["result"]


def _wait_status(ws, word: str, timeout: float = 20) -> dict:
    deadline = time.monotonic() + timeout
    presets = {}
    while time.monotonic() < deadline:
        presets = _state(ws)["presets"]
        if presets.get("status") == word:
            return presets
        time.sleep(0.5)
    raise AssertionError(f"presets never became {word}: {presets!r}")


def test_the_car_presets_are_in_the_home_keeper_picker(api, ws) -> None:
    golden = json.loads(GOLDEN.read_text(encoding="utf-8"))
    if not _has_service(api):
        assert os.environ.get("CK_EXPECT_PRESETS") != "1", (
            "this lane must run a Home Keeper with register_presets"
        )
        presets = _wait_status(ws, "no_service")
        assert presets["preset_ids"] == []
        return
    presets = _wait_status(ws, "registered")
    assert presets["preset_ids"] == golden["preset_ids"]
    assert presets["error"] is None
    reply = ws("home_keeper/list_declarative_presets")
    assert reply["success"], reply
    ours = [
        p
        for p in reply["result"]["presets"]
        if p.get("source") == "companion" and p["id"].startswith("car_keeper/")
    ]
    assert [p["id"] for p in ours] == golden["preset_ids"]
    for preset in ours:
        assert preset["default_spec"]["selection"]["target_integration"]
        assert preset["brand"]
