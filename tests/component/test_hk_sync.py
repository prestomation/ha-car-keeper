"""Component tests: the sync with Home Keeper (the fake), both ways."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

FAKE = "home_keeper_fake"


def _fake(hass: HomeAssistant) -> dict[str, Any]:
    return hass.data[FAKE]


def _calls(hass: HomeAssistant, name: str) -> list[dict[str, Any]]:
    return [data for call, data in _fake(hass)["calls"] if call == name]


async def _settle(hass: HomeAssistant) -> None:
    for _ in range(3):
        await hass.async_block_till_done(wait_background_tasks=True)


async def _car_with_job(hass, call, **item) -> tuple[dict, dict]:
    car = (
        await call(
            "add_car",
            {"name": "Civic", "make": "Honda", "odometer": 20000, "vin": "VIN7"},
        )
    )["car"]
    job = (
        await call(
            "add_item",
            {
                "car_id": car["id"],
                "name": "Oil",
                "interval_distance": 15000,
                "interval_months": 12,
                **item,
            },
        )
    )["item"]
    await _settle(hass)
    return car, job


def _store(entry):
    return entry.runtime_data.store


async def test_a_car_is_an_appliance_and_a_job_is_a_task(
    hass, setup_entry, call
) -> None:
    car, job = await _car_with_job(hass, call)
    store = _store(setup_entry)
    (asset,) = _fake(hass)["assets"].values()
    assert asset["name"] == "Civic" and asset["manufacturer"] == "Honda"
    assert "VIN7" not in str(asset)
    assert asset["managed_by"]["car_id"] == car["id"]
    assert asset["managed_by"]["config_entry_id"] == setup_entry.entry_id
    assert store.state["cars"][car["id"]]["hk_asset_id"] == asset["id"]
    (task,) = _fake(hass)["tasks"].values()
    assert store.state["items"][job["id"]]["hk_task_id"] == task["id"]
    assert task["recurrence_type"] == "sensor"
    assert task["sensor"]["entity_id"].startswith("sensor.")
    assert task["sensor"]["target"] == 15000.0
    assert task["sensor"]["baseline"] == 20000.0
    assert task["sensor"]["also_every"] == {"interval": 12, "unit": "months"}
    assert task["source"]["car_keeper"]["item_id"] == job["id"]
    assert task["device_id"] == asset["device_id"] is not None
    passes = setup_entry.runtime_data.sync.passes
    await setup_entry.runtime_data.sync.async_pass()
    assert len(_calls(hass, "add_task")) == 1
    assert setup_entry.runtime_data.sync.passes == passes + 1


async def test_a_service_completes_the_task_and_a_delete_undoes_it(
    hass, setup_entry, call
) -> None:
    car, job = await _car_with_job(hass, call)
    service = (
        await call(
            "log_service",
            {"car_id": car["id"], "items": [job["id"]], "reading": 21000, "cost": 55},
            as_="user",
        )
    )["service"]
    await _settle(hass)
    (complete,) = _calls(hass, "complete_task")
    assert complete["origin"] == "car_keeper"
    assert complete["cost"] == 55 and complete["reading"] == 21000
    stored = _store(setup_entry).state["services"][service["id"]]
    (done,) = stored["hk_completions"].values()
    task = next(iter(_fake(hass)["tasks"].values()))
    assert [c["ts"] for c in task["completions"]] == [done["ts"]]
    assert len(_store(setup_entry).state["services"]) == 1
    await call("delete_service", {"service_id": service["id"]})
    await _settle(hass)
    assert task["completions"] == []
    assert _store(setup_entry).state["sync"]["undo"] == []


async def test_a_completion_in_home_keeper_logs_a_service(
    hass, setup_entry, call
) -> None:
    _car, job = await _car_with_job(hass, call)
    task_id = _store(setup_entry).state["items"][job["id"]]["hk_task_id"]
    await hass.services.async_call(
        "home_keeper",
        "complete_task",
        {
            "task_id": task_id,
            "completed_at": "2026-10-01T10:00:00+00:00",
            "reading": 23000,
            "cost": 40,
        },
        blocking=True,
    )
    await _settle(hass)
    (service,) = _store(setup_entry).state["services"].values()
    assert service["origin"] == "home_keeper"
    assert service["items"] == [job["id"]]
    assert service["date"] == "2026-10-01"
    assert service["reading"] == 23000 and service["cost"] == 40
    assert len(_calls(hass, "complete_task")) == 1
    await hass.services.async_call(
        "home_keeper",
        "delete_completion",
        {"task_id": task_id, "ts": "2026-10-01T10:00:00+00:00"},
        blocking=True,
    )
    await _settle(hass)
    assert _store(setup_entry).state["services"] == {}
    assert _store(setup_entry).state["sync"]["undo"] == []


async def test_a_task_deleted_in_home_keeper_stops_the_task(
    hass, setup_entry, call
) -> None:
    _car, job = await _car_with_job(hass, call)
    task_id = _store(setup_entry).state["items"][job["id"]]["hk_task_id"]
    await hass.services.async_call(
        "home_keeper", "delete_task", {"task_id": task_id}, blocking=True
    )
    await _settle(hass)
    item = _store(setup_entry).state["items"][job["id"]]
    assert item["add_task"] is False and item["hk_task_id"] is None
    assert _fake(hass)["tasks"] == {}


async def test_changes_follow_and_a_deleted_car_releases_its_appliance(
    hass, setup_entry, call
) -> None:
    car, job = await _car_with_job(hass, call)
    await call("update_car", {"car_id": car["id"], "name": "Civic 2", "model": "Si"})
    await call("update_item", {"item_id": job["id"], "interval_distance": 10000})
    await _settle(hass)
    (asset,) = _fake(hass)["assets"].values()
    assert asset["name"] == "Civic 2" and asset["model"] == "Si"
    assert _calls(hass, "update_managed_asset")[-1]["name"] == "Civic 2"
    (task,) = _fake(hass)["tasks"].values()
    assert task["sensor"]["target"] == 10000.0
    await call("correct_odometer", {"car_id": car["id"], "value": 19000})
    await call("update_item", {"item_id": job["id"], "add_task": False})
    await _settle(hass)
    assert _fake(hass)["tasks"] == {}
    assert _calls(hass, "delete_task")[-1]["force"] is True
    await call("delete_car", {"car_id": car["id"]})
    await _settle(hass)
    assert asset["managed_by"] is None


async def test_parts_and_stock(hass, setup_entry, call) -> None:
    car, job = await _car_with_job(hass, call)
    (asset,) = _fake(hass)["assets"].values()
    asset["parts"] = [{"id": "filter", "stock": 3}, {"id": "oil", "stock": 10}]
    link = [{"asset_id": asset["id"], "part_id": "filter", "quantity": 1}]
    await call("update_item", {"item_id": job["id"], "parts": link})
    await _settle(hass)
    (task,) = _fake(hass)["tasks"].values()
    assert task["source"]["parts"] == link
    used = [{"asset_id": asset["id"], "part_id": "oil", "quantity": 4}]
    service = (
        await call(
            "log_service",
            {"car_id": car["id"], "items": [job["id"]], "parts_used": used},
        )
    )["service"]
    await _settle(hass)
    assert asset["parts"][1]["stock"] == 6
    await call("update_service", {"service_id": service["id"], "parts_used": []})
    await _settle(hass)
    assert asset["parts"][1]["stock"] == 10
    bad = [{"asset_id": asset["id"], "part_id": "gone", "quantity": 1}]
    await call("update_service", {"service_id": service["id"], "parts_used": bad})
    await _settle(hass)
    assert _store(setup_entry).state["sync"]["stock"] == []


async def test_removing_car_keeper_releases_the_appliances(
    hass, setup_entry, call
) -> None:
    await _car_with_job(hass, call)
    (asset,) = _fake(hass)["assets"].values()
    await hass.config_entries.async_remove(setup_entry.entry_id)
    await _settle(hass)
    assert asset["managed_by"] is None
