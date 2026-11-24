"""Upgrade: Car Keeper keeps its data and its tab across a Home Assistant update.

Phase 1 is the oldest supported Home Assistant with the oldest supported Home
Keeper. Phase 2 is the newer of each on the same config dir (``conftest.py``).
"""

from __future__ import annotations

from typing import Any


def test_car_keeper_loads_again(upgraded: dict[str, Any]) -> None:
    client = upgraded["client"]
    states = {e["domain"]: e["state"] for e in client.entries()}
    assert states.get("car_keeper") == "loaded", states
    assert states.get("home_keeper") == "loaded", states


def test_the_document_stays(upgraded: dict[str, Any]) -> None:
    state = upgraded["client"].ws("car_keeper/get_state")
    assert upgraded["written"]["settings"] == {"unit": "mi"}
    assert state["settings"] == {"unit": "mi"}
    for section in ("cars", "items", "services", "documents", "readings"):
        assert state[section] == upgraded["before"][section], section


def test_the_tab_comes_back_with_no_repair_issue(upgraded: dict[str, Any]) -> None:
    client = upgraded["client"]
    assert client.ws("car_keeper/get_state")["tab"] is True
    issues = client.ws("repairs/list_issues")["issues"]
    assert [i for i in issues if i["domain"] == "car_keeper"] == []
