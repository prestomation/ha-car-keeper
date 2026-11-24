"""The read projection: every read is open, and a reply hides no field.

Every Home Assistant user can read all Car Keeper data, also the VIN, the plate,
the costs, the shops and the notes. A change that hides a field from a user who
is not an admin fails here.
"""

from __future__ import annotations

import ex.models as m
import ex.projections as pr


def _seeded() -> dict:
    state = m.empty_state()
    state["cars"]["c1"] = {
        "id": "c1",
        "name": "Civic",
        "vin": "1HGCM82633A004352",
        "plate": "ABC-123",
        "notes": "garage door code 1234",
    }
    state["services"]["s1"] = {
        "id": "s1",
        "car_id": "c1",
        "shop": "Ballard Auto",
        "cost": 84.5,
        "notes": "rotated tyres",
        "files": ["receipt.jpg"],
    }
    state["documents"]["d1"] = {"id": "d1", "car_id": "c1", "name": "Insurance"}
    return state


def _leaves(value: object, path: str = "") -> dict[str, object]:
    if isinstance(value, dict):
        out: dict[str, object] = {}
        for key, item in value.items():
            out.update(_leaves(item, f"{path}.{key}" if path else str(key)))
        return out
    if isinstance(value, list):
        out = {}
        for index, item in enumerate(value):
            out.update(_leaves(item, f"{path}[{index}]"))
        return out
    return {path: value}


def test_a_non_admin_read_returns_every_field() -> None:
    state = _seeded()
    reply = pr.project_state(state, tab=True, revision=1)
    stored = _leaves(state)
    got = _leaves(reply)
    missing = {path for path in stored if got.get(path) != stored[path]}
    assert not missing, f"the reply hides or changes these fields: {sorted(missing)}"
    for secret in ("1HGCM82633A004352", "ABC-123", "Ballard Auto", 84.5):
        assert secret in got.values()


def test_the_reply_is_a_copy() -> None:
    state = _seeded()
    reply = pr.project_state(state, tab=True, revision=1)
    reply["cars"]["c1"]["name"] = "Changed"
    reply["services"]["s1"]["files"].append("x")
    assert state["cars"]["c1"]["name"] == "Civic"
    assert state["services"]["s1"]["files"] == ["receipt.jpg"]
