"""Import and export: the round trip and the fixed points.

* An export of a document, imported into an empty document, gives the same
  records, apart from the fields in ``NOT_EXPORTED``.
* An import of an export into the same document changes nothing.
* An export of an import of an export is the first export.
"""

from __future__ import annotations

import copy

import ex.history as h
import ex.import_export as ie
import ex.models as m
from hypothesis import given, settings
from hypothesis import strategies as st

VERSION = "0.1.0b1"
NAMES = (
    st.text(alphabet="abcdefghij ", min_size=1, max_size=8).map(str.strip).filter(bool)
)


@st.composite
def documents(draw) -> dict:
    state = m.empty_state()
    for c in range(draw(st.integers(0, 3))):
        car = m.build_car(
            {
                "name": f"{draw(NAMES)} {c}",
                "vin": draw(st.sampled_from(["", f"VIN{c}"])),
                "unit": draw(st.sampled_from(["km", "mi"])),
                "odometer": draw(st.one_of(st.none(), st.integers(0, 90000))),
                "fuel": draw(st.sampled_from(m.FUELS)),
            },
            car_id=f"c{c}",
            today="2026-01-01",
            default_unit="km",
        )
        if draw(st.booleans()):
            car["odometer"] = {
                **car["odometer"],
                "source": "entity",
                "entity_id": "sensor.odo",
            }
        state["cars"][car["id"]] = car
        state["readings"][car["id"]] = [
            {
                "ts": f"2026-0{i + 1}-01T00:00:00+00:00",
                "value": float(i * 100),
                "source": "manual",
                "by": None,
            }
            for i in range(draw(st.integers(0, 3)))
        ]
        for i in range(draw(st.integers(0, 3))):
            item = m.build_item(
                {
                    "name": f"job {i}",
                    "interval_distance": draw(
                        st.one_of(st.none(), st.integers(1000, 20000))
                    ),
                    "interval_months": draw(st.integers(1, 24)),
                },
                item_id=f"c{c}i{i}",
                car=car,
                today="2026-01-01",
            )
            state["items"][item["id"]] = item
        items = [i for i in state["items"] if i.startswith(f"c{c}i")]
        for s in range(draw(st.integers(0, 3))):
            service = m.build_service(
                {
                    "date": f"2026-0{s + 1}-15",
                    "reading": draw(st.one_of(st.none(), st.integers(0, 90000))),
                    "items": draw(st.lists(st.sampled_from(items), unique=True))
                    if items
                    else [],
                    "cost": draw(st.one_of(st.none(), st.integers(0, 500))),
                },
                service_id=f"c{c}s{s}",
                car=car,
                items=state["items"],
                today="2026-01-01",
                now=f"2026-01-01T00:00:0{s}+00:00",
            )
            state["services"][service["id"]] = service
    state["items"].update(
        h.refresh(state["items"], state["services"], list(state["items"]))
    )
    state["settings"]["templates"] = draw(
        st.sampled_from([{}, {"engine_oil": {"km": 9000}}])
    )
    return state


def _without_bookkeeping(state: dict) -> dict:
    out = copy.deepcopy(state)
    for section, keys in ie.NOT_EXPORTED.items():
        for record in out[section].values():
            for key in keys:
                record.pop(key, None)
    return out


@settings(max_examples=150, deadline=None)
@given(documents())
def test_round_trip_into_an_empty_document(state: dict) -> None:
    exported = ie.export_document(state, VERSION)
    plan = ie.plan_import(m.empty_state(), exported, entity_ids={"sensor.odo"})
    assert plan["report"]["ok"], plan["report"]["problems"]
    imported = ie.apply_plan(m.empty_state(), plan)
    assert _without_bookkeeping(imported) == _without_bookkeeping(state)
    # last_done follows from the imported history.
    for item_id, item in imported["items"].items():
        assert item["last_done"] == state["items"][item_id]["last_done"]


@settings(max_examples=150, deadline=None)
@given(documents())
def test_import_of_an_export_into_the_same_document_is_a_fixed_point(
    state: dict,
) -> None:
    exported = ie.export_document(state, VERSION)
    plan = ie.plan_import(state, exported, entity_ids={"sensor.odo"})
    counts = plan["report"]["counts"]
    for section in ("cars", "items", "services", "readings"):
        assert counts[section]["created"] == 0 and counts[section]["updated"] == 0, (
            section
        )
    assert ie.apply_plan(state, plan) == state


@settings(max_examples=100, deadline=None)
@given(documents())
def test_export_import_export_is_the_identity(state: dict) -> None:
    first = ie.export_document(state, VERSION)
    imported = ie.apply_plan(
        m.empty_state(),
        ie.plan_import(m.empty_state(), first, entity_ids={"sensor.odo"}),
    )
    assert ie.export_document(imported, VERSION) == first


def test_a_missing_sensor_becomes_a_typed_odometer() -> None:
    state = m.empty_state()
    car = m.build_car({"name": "A"}, car_id="c", today="2026-01-01", default_unit="km")
    car["odometer"] = {
        **car["odometer"],
        "source": "entity",
        "entity_id": "sensor.gone",
    }
    state["cars"]["c"] = car
    plan = ie.plan_import(
        m.empty_state(), ie.export_document(state, VERSION), entity_ids=set()
    )
    assert plan["report"]["ok"]
    assert plan["report"]["problems"] == [
        {
            "level": "warning",
            "path": "cars[0].odometer.entity_id",
            "key": "import_entity_missing",
            "params": {"entity_id": "sensor.gone"},
        }
    ]
    assert plan["writes"]["cars"]["c"]["odometer"]["source"] == "manual"


def test_matches_a_car_by_vin_then_by_name() -> None:
    state = m.empty_state()
    for car_id, name, vin in (("x", "Civic", "VIN1"), ("y", "Golf", "")):
        state["cars"][car_id] = m.build_car(
            {"name": name, "vin": vin},
            car_id=car_id,
            today="2026-01-01",
            default_unit="km",
        )
    other = m.empty_state()
    other["cars"]["a"] = m.build_car(
        {"name": "Renamed", "vin": "VIN1"},
        car_id="a",
        today="2026-01-01",
        default_unit="km",
    )
    other["cars"]["b"] = m.build_car(
        {"name": "golf"}, car_id="b", today="2026-01-01", default_unit="km"
    )
    other["items"]["j"] = m.build_item(
        {"name": "Oil", "interval_months": 12},
        item_id="j",
        car=other["cars"]["b"],
        today="2026-01-01",
    )
    plan = ie.plan_import(state, ie.export_document(other, VERSION), entity_ids=set())
    assert set(plan["writes"]["cars"]) == {"x", "y"}
    assert plan["writes"]["cars"]["x"]["name"] == "Renamed"
    assert plan["writes"]["items"]["j"]["car_id"] == "y"
    assert plan["report"]["counts"]["cars"] == {
        "created": 0,
        "updated": 2,
        "unchanged": 0,
    }


def test_errors_block_the_import() -> None:
    def problems(document, state=None):
        plan = ie.plan_import(state or m.empty_state(), document, entity_ids=set())
        assert plan["writes"] == {} and not plan["report"]["ok"]
        return [(p["level"], p["path"], p["key"]) for p in plan["report"]["problems"]]

    assert problems([]) == [("error", "", "import_not_a_document")]
    assert problems({"format": 2, "data": {}}) == [
        ("error", "format", "import_format_too_new")
    ]
    assert problems({"format": "1", "data": {}}) == [
        ("error", "format", "import_format_too_new")
    ]
    bad_car = {
        "format": 1,
        "data": {"cars": [{"id": "", "name": " ", "unit": "ly"}, 5]},
    }
    assert problems(bad_car) == [
        ("error", "cars[0].id", "import_missing_field"),
        ("error", "cars[0].name", "import_missing_field"),
        ("error", "cars[0].unit", "import_bad_value"),
        ("error", "cars[0].odometer", "import_missing_field"),
        ("error", "cars[1]", "import_not_a_record"),
    ]
    orphans = {
        "format": 1,
        "data": {
            "items": [{"id": "i", "car_id": "nope", "name": "x"}, "x"],
            "services": [{"id": "s", "car_id": "nope"}, {"x": 1}],
            "readings": {"nope": []},
        },
    }
    assert problems(orphans) == [
        ("error", "items[0].car_id", "import_unknown_car"),
        ("error", "items[1]", "import_not_a_record"),
        ("error", "services[0].car_id", "import_unknown_car"),
        ("error", "services[1]", "import_not_a_record"),
        ("error", "readings.nope", "import_unknown_car"),
    ]
    state = m.empty_state()
    state["cars"]["c"] = m.build_car(
        {"name": "A"}, car_id="c", today="2026-01-01", default_unit="km"
    )
    unknown_item = {
        "format": 1,
        "data": {"services": [{"id": "s", "car_id": "c", "items": ["zz"]}]},
    }
    assert problems(unknown_item, state) == [
        ("error", "services[0].items", "import_unknown_item")
    ]


def test_settings_and_new_readings_merge() -> None:
    state = m.empty_state()
    state["cars"]["c"] = m.build_car(
        {"name": "A"}, car_id="c", today="2026-01-01", default_unit="km"
    )
    state["readings"]["c"] = [
        {"ts": "2026-01-01", "value": 1.0, "source": "manual", "by": None}
    ]
    document = {
        "format": 1,
        "version": "x",
        "data": {
            "readings": {
                "c": [
                    {"ts": "2026-01-01", "value": 1.0, "source": "manual", "by": None},
                    {"ts": "2025-12-01", "value": 0.5, "source": "manual", "by": None},
                ]
            },
            "settings": {"unit": "mi"},
        },
    }
    plan = ie.plan_import(state, document, entity_ids=set())
    assert plan["report"]["counts"]["readings"] == {
        "created": 1,
        "updated": 0,
        "unchanged": 1,
    }
    out = ie.apply_plan(state, plan)
    assert [r["ts"] for r in out["readings"]["c"]] == ["2025-12-01", "2026-01-01"]
    assert out["settings"] == {"unit": "mi", "templates": {}}


def test_export_shape() -> None:
    exported = ie.export_document(m.empty_state(), VERSION)
    assert exported == {
        "format": 1,
        "version": VERSION,
        "data": {
            "cars": [],
            "items": [],
            "services": [],
            "readings": {},
            "settings": {"unit": "km", "templates": {}},
        },
        "skipped": {},
    }
    for section, keys in ie.NOT_EXPORTED.items():
        assert not set(keys) & set(ie.FIELDS[section]), section
        assert all(reason for reason in keys.values())
