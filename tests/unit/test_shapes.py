"""Exact shapes of the records and replies that the pure core builds.

A round trip passes when a key has a wrong name on both sides. These tests pin
each key and each default, so a renamed key or a changed default fails.
"""

from __future__ import annotations

import ex.events as ev
import ex.models as m
import ex.projections as pr


def test_empty_state() -> None:
    assert m.empty_state() == {
        "cars": {},
        "items": {},
        "services": {},
        "readings": {},
        "settings": {"unit": "km", "templates": {}},
    }


def test_settings_event_payload() -> None:
    fields = ["unit"]
    payload = ev.settings_event_data(fields, "car_keeper")
    assert payload == {"changed_fields": ["unit"], "origin": "car_keeper"}
    assert payload["changed_fields"] is not fields


def test_state_reply() -> None:
    assert pr.project_state(
        m.empty_state(), today="2026-10-01", tab=False, revision=3
    ) == {**m.empty_state(), "tab": False, "revision": 3, "today": "2026-10-01"}
