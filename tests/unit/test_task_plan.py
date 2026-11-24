"""Unit tests for the Home Keeper plan: appliances, tasks, completions and parts."""

from __future__ import annotations

import ex.task_plan as tp

ENTRY = "entry"
CAR = {
    "id": "c",
    "name": "Civic",
    "make": "Honda",
    "model": "Civic",
    "area_id": "garage",
    "unit": "km",
    "vin": "VIN1",
    "plate": "ABC",
    "hk_asset_id": None,
}


def _item(**kw):
    base = {
        "id": "i",
        "car_id": "c",
        "name": "Oil",
        "kind": "job",
        "interval_distance": 15000,
        "interval_months": 12,
        "enabled": True,
        "add_task": True,
        "start": {"date": "2026-01-01", "reading": 1000.0},
        "last_done": None,
        "hk_task_id": None,
        "parts": [],
    }
    return {**base, **kw}


def _plan(items, tasks, services=None, **kw):
    state = {
        "cars": {"c": CAR},
        "items": {i["id"]: i for i in items},
        "services": services or {},
    }
    args = {
        "entity_ids": {"c": "sensor.civic_odometer"},
        "device_ids": {"c": "dev"},
        "date_limits": {},
        "entry_id": ENTRY,
        "offset": "+02:00",
        **kw,
    }
    return tp.plan_tasks(state, tasks, **args)


def _ours(task_id, item_id="i", **kw):
    return {
        "id": task_id,
        "managed_by": tp.managed_by(ENTRY),
        "source": {"car_keeper": {"item_id": item_id}},
        **kw,
    }


def test_managed_by() -> None:
    assert tp.managed_by("e", car_id="c") == {
        "integration": "car_keeper",
        "config_entry_id": "e",
        "deletion_protected": True,
        "car_id": "c",
    }


def test_the_appliance_has_no_vin_and_no_plate() -> None:
    want = tp.desired_asset(CAR, "dev")
    assert want == {
        "name": "Civic",
        "manufacturer": "Honda",
        "model": "Civic",
        "area_id": "garage",
        "device_id": "dev",
    }
    assert tp.desired_asset({"name": "X", "area_id": None}, None) == {
        "name": "X",
        "manufacturer": "",
        "model": "",
    }


def test_plan_assets() -> None:
    cars = {"c": CAR, "d": {**CAR, "id": "d", "name": "Fit", "hk_asset_id": "a2"}}
    assets = [
        {"id": "x", "managed_by": {"integration": "other"}},
        {
            "id": "a2",
            "managed_by": {"integration": "car_keeper", "car_id": "d"},
            "name": "Old",
            "manufacturer": "Honda",
            "model": "Civic",
            "area_id": "garage",
            "device_id": "dev-d",
        },
        {"id": "a3", "managed_by": {"integration": "car_keeper", "car_id": "d"}},
        {"id": "a4", "managed_by": {"integration": "car_keeper", "car_id": "gone"}},
        {"id": "a5", "managed_by": None},
    ]
    plan = tp.plan_assets(
        cars, assets, device_ids={"c": "dev", "d": "dev-d"}, entry_id=ENTRY
    )
    assert plan["adds"] == [
        {
            "car_id": "c",
            "fields": {
                **tp.desired_asset(CAR, "dev"),
                "managed_by": {
                    **tp.managed_by(ENTRY, car_id="c"),
                    "locked_fields": ["name"],
                },
            },
        }
    ]
    assert plan["binds"] == []
    assert plan["updates"] == [{"asset_id": "a2", "fields": {"name": "Fit"}}]
    assert plan["releases"] == [{"asset_id": "a3"}, {"asset_id": "a4"}]
    assert tp.plan_assets(cars, [], device_ids={}, entry_id=ENTRY)["adds"] == []
    moved = {**assets[1], "device_id": "elsewhere", "name": "Fit"}
    plan = tp.plan_assets(
        {"d": cars["d"]}, [moved], device_ids={"d": "dev-d"}, entry_id=ENTRY
    )
    assert plan["updates"] == []
    bind = tp.plan_assets(
        {"d": {**cars["d"], "hk_asset_id": None}},
        assets[1:2],
        device_ids={"d": "dev-d"},
        entry_id=ENTRY,
    )
    assert bind["binds"] == [{"car_id": "d", "asset_id": "a2"}]


def test_base() -> None:
    assert tp.base(_item()) == {"date": "2026-01-01", "reading": 1000.0}
    done = _item(last_done={"date": "2026-05-01", "reading": None})
    assert tp.base(done) == {"date": "2026-05-01", "reading": None}
    assert tp.base({"start": {}, "last_done": None}) == {"date": None, "reading": None}


def _want(item, entity="sensor.o", limit=None):
    return tp.desired_task(
        item, CAR, entity_id=entity, device_id="dev", date_limit=limit
    )


def test_desired_task_kinds() -> None:
    assert _want(_item()) == {
        "name": "Oil",
        "device_id": "dev",
        "recurrence_type": "sensor",
        "sensor": {
            "entity_id": "sensor.o",
            "mode": "usage",
            "target": 15000.0,
            "unit": "km",
            "also_every": {"interval": 12, "unit": "months"},
            "combinator": "any",
        },
    }
    assert "also_every" not in _want(_item(interval_months=None))["sensor"]
    assert _want(_item(), entity=None) is None
    assert _want(_item(interval_distance=None)) == {
        "name": "Oil",
        "device_id": "dev",
        "recurrence_type": "floating",
        "interval": 12,
        "unit": "months",
    }
    date = _item(kind="date", interval_distance=None)
    assert _want(date) is None
    assert _want(date, limit="2027-03-01") == {
        "name": "Oil",
        "device_id": "dev",
        "recurrence_type": "one-off",
        "due": "2027-03-01",
    }
    assert _want(_item(add_task=False)) is None
    assert _want(_item(enabled=False)) is None


def test_completed_at() -> None:
    same = {"date": "2026-03-01", "logged": "2026-03-01T08:30:00+01:00"}
    assert tp.completed_at(same, "+02:00") == "2026-03-01T08:30:00+01:00"
    old = {"date": "2026-02-01", "logged": "2026-03-01T08:30:00+01:00"}
    assert tp.completed_at(old, "+02:00") == "2026-02-01T12:00:00+02:00"
    assert tp.completed_at({"date": "2026-02-01"}, "-05:00") == (
        "2026-02-01T12:00:00-05:00"
    )


def test_a_new_job_gets_a_task() -> None:
    plan = _plan([_item()], [])
    (add,) = plan["adds"]
    assert add["item_id"] == "i"
    fields = add["fields"]
    assert fields["sensor"]["baseline"] == 1000.0
    assert fields["source"] == {
        "car_keeper": {"car_id": "c", "item_id": "i", "device_id": "dev"}
    }
    assert fields["managed_by"]["locked_fields"] == list(tp.TASK_LOCKED_FIELDS)
    floating = _plan([_item(interval_distance=None)], [])["adds"][0]["fields"]
    assert floating["last_completed"] == "2026-01-01T12:00:00+02:00"
    assert "sensor" not in floating
    no_reading = _item(start={"date": "2026-01-01", "reading": None})
    assert "baseline" not in _plan([no_reading], [])["adds"][0]["fields"]["sensor"]
    no_date = _item(interval_distance=None, start={"date": None, "reading": None})
    assert "last_completed" not in _plan([no_date], [])["adds"][0]["fields"]


def test_binds_forgets_and_deletes() -> None:
    task = _ours("t1", sensor={"baseline": 1000.0})
    want = _want(_item(), entity="sensor.civic_odometer")
    task.update({k: v for k, v in want.items() if k != "sensor"})
    task["sensor"] = {**want["sensor"], "baseline": 1000.0}
    plan = _plan([_item()], [task])
    assert plan["binds"] == [{"item_id": "i", "task_id": "t1"}]
    assert plan["updates"] == plan["meters"] == plan["adds"] == []
    assert _plan([_item(hk_task_id="t1")], [task])["binds"] == []
    forgotten = _plan([_item(hk_task_id="t9")], [])
    assert forgotten["forgets"] == [{"item_id": "i"}] and forgotten["adds"] == []
    others = [
        {"id": "x", "managed_by": {"integration": "other"}},
        {"id": "y"},
        _ours("t2", item_id="gone"),
        _ours("t3"),
        _ours("t4", item_id=None),
    ]
    plan = _plan([_item(hk_task_id="t1")], [task, *others])
    assert plan["deletes"] == [{"task_id": "t2"}, {"task_id": "t3"}, {"task_id": "t4"}]
    off = _plan([_item(hk_task_id="t1", add_task=False)], [task])
    assert off["deletes"] == [{"task_id": "t1"}]
    orphan_car = _plan([_item(car_id="none")], [])
    assert not any(orphan_car.values())


def _linked(**sensor):
    want = _want(_item(), entity="sensor.civic_odometer")
    task = _ours("t1", **{k: v for k, v in want.items() if k != "sensor"})
    task["sensor"] = {**want["sensor"], "baseline": 1000.0, **sensor}
    return task


def test_updates_and_meters() -> None:
    renamed = _plan([_item(hk_task_id="t1", name="Oil 2")], [_linked()])
    assert renamed["updates"] == [{"task_id": "t1", "fields": {"name": "Oil 2"}}]
    retarget = _plan([_item(hk_task_id="t1", interval_distance=10000)], [_linked()])
    (step,) = retarget["updates"]
    assert step["fields"]["sensor"]["target"] == 10000.0
    assert retarget["meters"] == []
    meter = _plan([_item(hk_task_id="t1")], [_linked(baseline=500.0)])
    assert meter["meters"] == [{"task_id": "t1", "baseline": 1000.0}]
    broken = _ours("t1", name="Oil", device_id="dev", recurrence_type="sensor")
    assert "sensor" in _plan([_item(hk_task_id="t1")], [broken])["updates"][0]["fields"]
    floating = _item(hk_task_id="t1", interval_distance=None)
    switch = _plan([floating], [_linked()])["updates"][0]["fields"]
    assert switch == {"recurrence_type": "floating", "interval": 12, "unit": "months"}
    no_reading = _item(hk_task_id="t1", start={"date": "2026-01-01", "reading": None})
    assert _plan([no_reading], [_linked(baseline=5.0)])["meters"] == []


def test_consumables() -> None:
    parts = [{"asset_id": "a", "part_id": "p", "quantity": 1}]
    plan = _plan([_item(hk_task_id="t1", parts=parts)], [_linked()])
    assert plan["consumables"] == [{"task_id": "t1", "parts": parts}]
    linked = _linked()
    linked["source"]["parts"] = [{"asset_id": "a", "part_id": "p"}]
    assert _plan([_item(hk_task_id="t1", parts=parts)], [linked])["consumables"] == []
    two = [{"asset_id": "a", "part_id": "p", "quantity": 2}]
    assert _plan([_item(hk_task_id="t1", parts=two)], [linked])["consumables"]
    clear = _plan([_item(hk_task_id="t1")], [linked])
    assert clear["consumables"] == [{"task_id": "t1", "parts": []}]


def _service(**kw):
    base = {
        "car_id": "c",
        "date": "2026-03-01",
        "logged": "2026-03-01T09:00:00+02:00",
        "reading": 16000.0,
        "items": ["i", "j"],
        "cost": 80.0,
        "notes": "",
        "who": None,
        "hk_completions": {},
    }
    return {**base, **kw}


def test_a_due_date_compares_by_the_date() -> None:
    item = _item(kind="date", interval_distance=None, hk_task_id="t1")
    task = _ours(
        "t1",
        name="Oil",
        device_id="dev",
        recurrence_type="one-off",
        due="2027-03-01T00:00:00-05:00",
    )
    limits = {"i": "2027-03-01"}
    assert _plan([item], [task], date_limits=limits)["updates"] == []
    moved = _plan([item], [task], date_limits={"i": "2028-03-01"})["updates"]
    assert moved == [{"task_id": "t1", "fields": {"due": "2028-03-01"}}]


def test_completions() -> None:
    floating = _item(id="j", name="Wipers", interval_distance=None, hk_task_id="t2")
    tasks = [
        _linked(),
        _ours(
            "t2",
            item_id="j",
            name="Wipers",
            device_id="dev",
            recurrence_type="floating",
            interval=12,
            unit="months",
        ),
    ]
    services = {"s": _service(who="person.ann", notes="Full service")}
    plan = _plan([_item(hk_task_id="t1"), floating], tasks, services)
    assert plan["completes"] == [
        {
            "service_id": "s",
            "item_id": "i",
            "fields": {
                "task_id": "t1",
                "completed_at": "2026-03-01T09:00:00+02:00",
                "cost": 80.0,
                "reading": 16000.0,
                "who": "person.ann",
                "note": "Full service",
            },
        },
        {
            "service_id": "s",
            "item_id": "j",
            "fields": {
                "task_id": "t2",
                "completed_at": "2026-03-01T09:00:00+02:00",
                "who": "person.ann",
                "note": "Full service",
            },
        },
    ]
    done = {"i": {"task_id": "t1", "ts": "x"}}
    later = _plan(
        [_item(hk_task_id="t1"), floating],
        tasks,
        {"s": _service(hk_completions=done, who="Ann", cost=None)},
    )
    assert [c["item_id"] for c in later["completes"]] == ["j"]
    assert "who" not in later["completes"][0]["fields"]
    assert "cost" not in later["completes"][0]["fields"]
    stale = {"i": {"task_id": "t-old", "ts": "x"}}
    again = _plan(
        [_item(hk_task_id="t1")], tasks[:1], {"s": _service(hk_completions=stale)}
    )
    assert [c["item_id"] for c in again["completes"]] == ["i"]


def test_completions_run_in_date_order() -> None:
    services = {
        "b": _service(
            date="2026-01-01", items=["i"], logged="2026-01-01T08:00:00+02:00"
        ),
        "a": _service(
            date="2026-02-01", items=["i"], logged="2026-02-01T08:00:00+02:00"
        ),
    }
    plan = _plan([_item(hk_task_id="t1")], [_linked()], services)
    assert [c["service_id"] for c in plan["completes"]] == ["b", "a"]
    no_reading = {"s": _service(items=["i"], reading=None)}
    plan = _plan([_item(hk_task_id="t1")], [_linked()], no_reading)
    assert "reading" not in plan["completes"][0]["fields"]


def test_service_from_completion() -> None:
    item = {"id": "i"}
    assert tp.service_from_completion(
        {
            "completed_at": "2026-03-01T18:00:00+00:00",
            "reading": 42000,
            "cost": 12.5,
            "note": "Done",
            "who": "person.ann",
        },
        item,
    ) == {
        "items": ["i"],
        "date": "2026-03-01",
        "reading": 42000,
        "cost": 12.5,
        "notes": "Done",
        "who": "person.ann",
    }
    assert tp.service_from_completion({"reading": "x", "cost": None}, item) == {
        "items": ["i"],
        "date": None,
    }


def test_each_sensor_key_counts() -> None:
    want = _want(_item())["sensor"]
    assert not tp._sensor_differs({**want, "baseline": 5.0}, want)
    assert tp._sensor_differs(None, want)
    assert tp._sensor_differs("sensor", want)
    for key, other in (
        ("entity_id", "sensor.other"),
        ("mode", "threshold"),
        ("target", 1.0),
        ("unit", "mi"),
        ("also_every", {"interval": 6, "unit": "months"}),
        ("combinator", "all"),
    ):
        assert tp._sensor_differs({**want, key: other}, want), key
