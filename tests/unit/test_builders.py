"""Unit tests for the record builders of ``models.py``."""

from __future__ import annotations

import ex.models as m
import pytest
from ex.models import CarKeeperError


def _err(fn, *args, **kwargs) -> CarKeeperError:
    with pytest.raises(CarKeeperError) as info:
        fn(*args, **kwargs)
    return info.value


def _car(**data):
    return m.build_car(
        {"name": "Civic", **data}, car_id="c", today="2026-01-02", default_unit="km"
    )


def test_build_car_shape() -> None:
    assert _car() == {
        "id": "c",
        "name": "Civic",
        "make": "",
        "model": "",
        "year": None,
        "trim": "",
        "fuel": "petrol",
        "vin": "",
        "plate": "",
        "area_id": None,
        "notes": "",
        "lead_distance": 1000,
        "lead_days": 30,
        "unit": "km",
        "odometer": {
            "source": "manual",
            "entity_id": None,
            "value": None,
            "updated": None,
            "offset": 0.0,
            "lower": None,
        },
        "photo": None,
        "created": "2026-01-02",
        "hk_asset_id": None,
    }
    car = _car(unit="mi", vin=" 1hg123 ", year="2019", odometer=1234.56, lead_days=10)
    assert car["unit"] == "mi" and car["lead_distance"] == 600
    assert car["vin"] == "1HG123" and car["year"] == 2019
    assert car["odometer"]["value"] == 1234.6 and car["lead_days"] == 10


def test_car_errors() -> None:
    assert _err(_car, name=" ").key == "field_required"
    assert _err(_car, fuel="coal").placeholders == {"field": "fuel"}
    assert _err(_car, year=1800).key == "out_of_range"
    assert _err(_car, year=2019.5).key == "invalid_field"
    assert _err(_car, year="x").key == "invalid_field"
    assert _err(_car, name="x" * 101).placeholders == {"field": "name", "limit": "100"}
    assert _err(_car, unit="ly").key == "invalid_field"
    assert _err(_car, lead_distance=-1).key == "out_of_range"


def test_update_car() -> None:
    car = _car()
    new, changed = m.update_car(
        car, {"name": "Civic 2", "plate": "AB-1", "unit": "mi", "id": "z"}
    )
    assert changed == ["name", "plate"]
    assert new["id"] == "c" and new["unit"] == "km"
    same, none = m.update_car(new, {"name": "Civic 2"})
    assert none == [] and same == new


def test_build_item_and_update() -> None:
    car = {**_car(), "odometer": {"value": 5000.0}}
    item = m.build_item(
        {"name": "Oil", "interval_distance": 15000.4, "interval_months": 12},
        item_id="i",
        car=car,
        today="2026-03-01",
        template_id="engine_oil",
    )
    assert item == {
        "id": "i",
        "car_id": "c",
        "name": "Oil",
        "kind": "job",
        "interval_distance": 15000,
        "interval_months": 12,
        "due_date": None,
        "lead_distance": None,
        "lead_days": None,
        "notes": "",
        "enabled": True,
        "add_task": True,
        "template_id": "engine_oil",
        "start": {"date": "2026-03-01", "reading": 5000.0},
        "last_done": None,
        "hk_task_id": None,
        "notified": None,
        "parts": [],
    }
    known = m.build_item(
        {
            "name": "Oil",
            "interval_months": 6,
            "last_date": "2025-12-01",
            "last_reading": 4000,
        },
        item_id="j",
        car=car,
        today="2026-03-01",
    )
    assert known["start"] == {"date": "2025-12-01", "reading": 4000.0}
    date = m.build_item(
        {
            "name": "Ins",
            "kind": "date",
            "due_date": "2026-09-01",
            "interval_distance": 100,
        },
        item_id="k",
        car=car,
        today="2026-03-01",
    )
    assert date["interval_distance"] is None and date["interval_months"] is None
    assert (
        _err(m.build_item, {"name": "x"}, item_id="z", car=car, today="2026-03-01").key
        == "interval_required"
    )
    assert _err(
        m.build_item,
        {"name": "x", "kind": "date"},
        item_id="z",
        car=car,
        today="2026-03-01",
    ).placeholders == {"field": "due_date"}
    assert (
        _err(
            m.build_item,
            {"name": "x", "interval_months": 1, "due_date": "nope"},
            item_id="z",
            car=car,
            today="2026-03-01",
        ).key
        == "invalid_date"
    )
    new, changed = m.update_item(item, {"interval_months": 6, "enabled": False})
    assert changed == ["enabled", "interval_months"] and new["start"] == item["start"]


def test_build_service() -> None:
    car = _car()
    items = {"i": {"id": "i", "car_id": "c"}, "o": {"id": "o", "car_id": "other"}}
    service = m.build_service(
        {"items": ["i", "i"], "reading": 10.04, "cost": "12.5", "shop": " A "},
        service_id="s",
        car=car,
        items=items,
        today="2026-01-02",
        now="2026-01-02T10:00:00+00:00",
        origin="car_keeper",
    )
    assert service == {
        "id": "s",
        "car_id": "c",
        "date": "2026-01-02",
        "reading": 10.0,
        "items": ["i"],
        "shop": "A",
        "notes": "",
        "who": None,
        "cost": 12.5,
        "parts_used": [],
        "logged": "2026-01-02T10:00:00+00:00",
        "origin": "car_keeper",
        "hk_completions": {},
    }
    assert _err(
        m.build_service,
        {"items": ["o"]},
        service_id="s",
        car=car,
        items=items,
        today="2026-01-02",
        now="n",
    ).placeholders == {"id": "o"}
    assert (
        _err(
            m.build_service,
            {"items": "i"},
            service_id="s",
            car=car,
            items=items,
            today="2026-01-02",
            now="n",
        ).key
        == "invalid_field"
    )
    new, changed = m.update_service(
        service, {"cost": None, "date": "2026-01-01"}, car, items, "2026-01-02"
    )
    assert changed == ["cost", "date"] and new["logged"] == service["logged"]


def test_field_helpers() -> None:
    assert m.text({"a": None}, "a") == ""
    assert m.number({"a": ""}, "a") is None
    assert m.number({"a": "5"}, "a", whole=True) == 5
    assert _err(m.number, {"a": float("nan")}, "a").key == "out_of_range"
    assert m.number({"a": 5}, "a", high=5) == 5.0
    assert _err(m.number, {"a": 6}, "a", high=5).placeholders == {
        "field": "a",
        "low": "0",
        "high": "5",
    }
    assert m.date_field({"d": "2026-01-02T10:00"}, "d") == "2026-01-02"
    assert m.choice({}, "k", ("a",), "a") == "a"
