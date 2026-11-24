"""The read projection: every read is open, and a reply hides no field.

Every Home Assistant user can read all Car Keeper data, also the VIN, the plate,
the costs, the shops and the notes. A change that hides a field from a user who
is not an admin fails here. The component tier checks the same rule through the
services and the websocket command, as a user who is not an admin.
"""

from __future__ import annotations

import ex.history as h
import ex.models as m
import ex.projections as pr

TODAY = "2026-10-15"


def seeded() -> dict:
    state = m.empty_state()
    car = m.build_car(
        {
            "name": "Civic",
            "vin": "1HGCM82633A004352",
            "plate": "ABC-123",
            "notes": "garage door code 1234",
            "odometer": 20000,
        },
        car_id="c1",
        today="2026-01-01",
        default_unit="km",
    )
    state["cars"]["c1"] = car
    state["readings"]["c1"] = [
        {
            "ts": "2026-08-01T10:00:00+00:00",
            "value": 18000.0,
            "source": "manual",
            "by": None,
        },
        {
            "ts": "2026-10-01T10:00:00+00:00",
            "value": 20000.0,
            "source": "entity",
            "by": None,
        },
    ]
    for item_id, data in {
        "oil": {"name": "Oil", "interval_distance": 15000, "interval_months": 12},
        "tyres": {"name": "Tyres", "interval_distance": 4000},
        "wipers": {"name": "Wipers", "interval_months": 12, "enabled": False},
    }.items():
        item = m.build_item(data, item_id=item_id, car=car, today="2026-01-01")
        item["start"] = {"date": "2026-01-01", "reading": 15500.0}
        state["items"][item_id] = item
    state["services"]["s1"] = m.build_service(
        {
            "items": ["oil"],
            "reading": 19000,
            "shop": "Ballard Auto",
            "cost": 84.5,
            "notes": "rotated tyres",
            "date": "2026-09-01",
        },
        service_id="s1",
        car=car,
        items=state["items"],
        today=TODAY,
        now="2026-09-01T10:00:00+00:00",
    )
    state["services"]["s1"]["parts_used"] = [
        {"asset_id": "a", "part_id": "p", "quantity": 1}
    ]
    state["items"].update(
        h.refresh(state["items"], state["services"], list(state["items"]))
    )
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
    state = seeded()
    reply = pr.project_state(state, today=TODAY, tab=True, revision=1)
    stored = _leaves(state)
    got = _leaves(reply)
    missing = {path for path in stored if got.get(path) != stored[path]}
    assert not missing, f"the reply hides or changes these fields: {sorted(missing)}"
    for secret in (
        "1HGCM82633A004352",
        "ABC-123",
        "Ballard Auto",
        84.5,
        "rotated tyres",
    ):
        assert secret in got.values()
    car = pr.project_car(state, "c1", TODAY)
    got = _leaves(car)
    for path, value in _leaves(state["cars"]["c1"]).items():
        assert got[f"car.{path}"] == value, path


def test_the_reply_is_a_copy() -> None:
    state = seeded()
    reply = pr.project_state(state, today=TODAY, tab=True, revision=1)
    reply["cars"]["c1"]["name"] = "Changed"
    reply["services"]["s1"]["parts_used"].append({})
    view = pr.project_car(state, "c1", TODAY)
    view["readings"].append({})
    view["items"][0]["name"] = "x"
    assert state["cars"]["c1"]["name"] == "Civic"
    assert len(state["services"]["s1"]["parts_used"]) == 1
    assert len(state["readings"]["c1"]) == 2
    assert state["items"]["oil"]["name"] == "Oil"


def test_the_computed_values() -> None:
    state = seeded()
    summary = pr.car_summary(state, "c1", TODAY)
    assert summary["daily_distance"] == 2000 / 61
    assert summary["items"]["tyres"]["status"] == "overdue"
    assert summary["items"]["oil"]["status"] == "ok"
    assert summary["items"]["wipers"]["status"] == "ok"
    assert summary["status"] == "overdue" and summary["due_count"] == 1
    assert summary["next_item_id"] == "tyres"
    reply = pr.project_state(state, today=TODAY, tab=False, revision=7)
    assert reply["cars"]["c1"]["summary"] == {
        k: v for k, v in summary.items() if k != "items"
    }
    assert reply["items"]["tyres"]["due"] == summary["items"]["tyres"]
    assert (reply["tab"], reply["revision"], reply["today"]) == (False, 7, TODAY)
    view = pr.project_car(state, "c1", TODAY)
    assert [i["id"] for i in view["items"]] == ["tyres", "oil", "wipers"]
    assert [s["id"] for s in view["services"]] == ["s1"]


def test_lead_falls_back_to_the_car() -> None:
    car = {"lead_distance": 800, "lead_days": 20}
    assert pr.lead({"lead_distance": None, "lead_days": None}, car) == (800.0, 20)
    assert pr.lead({"lead_distance": 0, "lead_days": 0}, car) == (0.0, 0)
    assert pr.lead({}, {}) == (0.0, 0)


def test_a_car_with_no_items() -> None:
    state = m.empty_state()
    state["cars"]["c"] = m.build_car(
        {"name": "A"}, car_id="c", today=TODAY, default_unit="km"
    )
    assert pr.car_summary(state, "c", TODAY) == {
        "status": "ok",
        "cost_total": 0,
        "daily_distance": None,
        "next_item_id": None,
        "due_count": 0,
        "items": {},
    }


def test_the_cost_total_counts_only_the_car() -> None:
    state = m.empty_state()
    for car_id in ("c", "d"):
        state["cars"][car_id] = m.build_car(
            {"name": car_id}, car_id=car_id, today=TODAY, default_unit="km"
        )
    for n, (car_id, cost) in enumerate(
        [("c", 10.105), ("c", 20.2), ("c", None), ("d", 99)]
    ):
        state["services"][f"s{n}"] = {"car_id": car_id, "cost": cost}
    assert pr.car_summary(state, "c", TODAY)["cost_total"] == 30.3
