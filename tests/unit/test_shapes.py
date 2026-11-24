"""Exact shapes of the records and replies that the pure core builds.

A round trip passes when a key has a wrong name on both sides. These tests pin
each key and each default, so a renamed key or a changed default fails.
"""

from __future__ import annotations

import ex.events as ev
import ex.models as m
import ex.projections as pr
import ex.templates as tpl
import pytest


def test_empty_state() -> None:
    assert m.empty_state() == {
        "cars": {},
        "items": {},
        "services": {},
        "readings": {},
        "settings": {"unit": "km", "templates": {}},
        "sync": {"undo": [], "stock": []},
    }


def test_settings_event_payload() -> None:
    fields = ["unit"]
    payload = ev.settings_event_data(fields, "car_keeper")
    assert payload == {"changed_fields": ["unit"], "origin": "car_keeper"}
    assert payload["changed_fields"] is not fields


def test_state_reply() -> None:
    assert pr.project_state(
        m.empty_state(), today="2026-10-01", tab=False, revision=3
    ) == {
        **m.empty_state(),
        "starter_jobs": tpl.effective({}),
        "presets": {},
        "tab": False,
        "revision": 3,
        "today": "2026-10-01",
    }
    presets = {"status": "registered", "preset_ids": ["a"], "error": None, "rows": []}
    reply = pr.project_state(
        m.empty_state(), today="2026-10-01", tab=True, revision=1, presets=presets
    )
    assert reply["presets"] == presets


def test_normalize_keeps_the_sync_queue() -> None:
    undo = {"task_id": "t", "ts": "2026-01-01T12:00:00+00:00"}
    state = m.normalize_state({"sync": {"undo": [undo, "bad"], "stock": "bad"}})
    assert state["sync"] == {"undo": [undo], "stock": []}
    assert m.normalize_state({"sync": []})["sync"] == {"undo": [], "stock": []}


def test_clean_parts() -> None:
    assert m.clean_parts([{"asset_id": "a", "part_id": "p"}]) == [
        {"asset_id": "a", "part_id": "p", "quantity": 1}
    ]
    assert m.clean_parts([{"asset_id": 1, "part_id": 2, "quantity": 2.5}]) == [
        {"asset_id": "1", "part_id": "2", "quantity": 2.5}
    ]
    for bad in ("x", [{"asset_id": "a"}], [{"part_id": "p"}], ["x"], [{}] * 51):
        with pytest.raises(m.CarKeeperError) as err:
            m.clean_parts(bad, "parts")
        assert err.value.placeholders == {"field": "parts"}
