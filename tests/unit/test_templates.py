"""Unit tests for the starter jobs."""

from __future__ import annotations

import ex.templates as t
import pytest
from ex.models import CarKeeperError


def test_ids_are_unique_and_stable() -> None:
    ids = [x.id for x in t.TEMPLATES]
    assert len(ids) == len(set(ids))
    assert ids == [
        "engine_oil",
        "tyre_rotation",
        "tyre_check",
        "brake_fluid",
        "cabin_filter",
        "engine_air_filter",
        "wipers",
        "battery_12v",
        "coolant",
        "spark_plugs",
        "adblue",
        "registration",
        "insurance",
        "inspection",
    ]


def test_each_template_has_an_interval() -> None:
    for template in t.TEMPLATES:
        assert template.km or template.months, template.id
        assert template.kind in ("job", "date")
        assert set(template.fuels) <= set(t.FUELS)


def test_for_fuel() -> None:
    electric = [x["id"] for x in t.for_fuel("electric", {})]
    assert "engine_oil" not in electric and "spark_plugs" not in electric
    assert "tyre_rotation" in electric and "registration" in electric
    diesel = [x["id"] for x in t.for_fuel("diesel", {})]
    assert "adblue" in diesel and "spark_plugs" not in diesel
    off = t.for_fuel("diesel", {"adblue": {"enabled": False}})
    assert "adblue" not in [x["id"] for x in off]


def test_items_for_converts_and_rounds() -> None:
    rows = t.items_for(
        ["engine_oil", "insurance", "tyre_check"],
        unit="mi",
        overrides={"engine_oil": {"km": 16000}},
        names={"engine_oil": "Oil"},
        due_dates={"insurance": "2027-02-01"},
        today="2026-10-01",
    )
    assert rows == [
        {
            "template_id": "engine_oil",
            "data": {
                "name": "Oil",
                "kind": "job",
                "interval_distance": 9900,
                "interval_months": 12,
            },
        },
        {
            "template_id": "insurance",
            "data": {
                "name": "insurance",
                "kind": "date",
                "interval_distance": None,
                "interval_months": 12,
                "due_date": "2027-02-01",
            },
        },
        {
            "template_id": "tyre_check",
            "data": {
                "name": "tyre_check",
                "kind": "job",
                "interval_distance": None,
                "interval_months": 1,
            },
        },
    ]
    dated = t.items_for(
        ["inspection"], unit="km", overrides={}, names={}, today="2026-10-01"
    )
    assert dated[0]["data"]["due_date"] == "2026-10-01"
    with pytest.raises(CarKeeperError) as info:
        t.items_for(["nope"], unit="km", overrides={}, names={}, today="2026-10-01")
    assert info.value.key == "template_not_found"


def test_effective_and_clean_overrides() -> None:
    rows = {
        x["id"]: x for x in t.effective({"wipers": {"months": 6, "enabled": False}})
    }
    assert rows["wipers"]["months"] == 6 and rows["wipers"]["enabled"] is False
    assert rows["engine_oil"] == {
        "id": "engine_oil",
        "fuels": list(t.ICE),
        "kind": "job",
        "km": 15000,
        "months": 12,
        "enabled": True,
    }
    assert t.clean_overrides({"wipers": {"months": 6.0, "enabled": 0, "x": 1}}) == {
        "wipers": {"months": 6, "enabled": False}
    }
    assert t.clean_overrides({"adblue": {"km": None}}) == {"adblue": {"km": None}}
    for bad, key in (
        ([], "invalid_field"),
        ({"nope": {}}, "template_not_found"),
        ({"wipers": []}, "template_not_found"),
        ({"wipers": {"months": 0}}, "out_of_range"),
        ({"wipers": {"km": 1_000_001}}, "out_of_range"),
        ({"wipers": {"months": "6"}}, "out_of_range"),
    ):
        with pytest.raises(CarKeeperError) as info:
            t.clean_overrides(bad)
        assert info.value.key == key, bad
