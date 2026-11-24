"""Component tests: the entities of each car, the bus events, the odometer follower."""

from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import issue_registry as ir

from custom_components.car_keeper import store as store_module
from custom_components.car_keeper.const import DOMAIN
from custom_components.car_keeper.entity import find_device


def _events(hass: HomeAssistant) -> list[Event[Any]]:
    seen: list[Event[Any]] = []

    # A callback runs in the event loop in the order of the events. A plain function
    # can run in the executor, and then the order can change.
    @callback
    def _keep(event: Event[Any]) -> None:
        if event.event_type.startswith(DOMAIN):
            seen.append(event)

    hass.bus.async_listen("*", _keep)
    return seen


def _entity(hass: HomeAssistant, car_id: str, key: str) -> str:
    registry = er.async_get(hass)
    platform = {"overdue": "binary_sensor", "jobs": "todo"}.get(key, "sensor")
    entity_id = registry.async_get_entity_id(platform, DOMAIN, f"{car_id}_{key}")
    assert entity_id, key
    return entity_id


async def _car(hass, call, **data) -> dict:
    car = (await call("add_car", {"name": "Civic", "odometer": 20000, **data}))["car"]
    await hass.async_block_till_done()
    return car


async def test_entities_of_a_car(hass, setup_entry, call) -> None:
    car = await _car(hass, call)
    oil = (
        await call(
            "add_item",
            {
                "car_id": car["id"],
                "name": "Oil",
                "interval_distance": 500,
                "last_reading": 19600,
                "interval_months": 12,
            },
        )
    )["item"]
    await call(
        "add_item",
        {
            "car_id": car["id"],
            "name": "Plates",
            "kind": "date",
            "due_date": "2099-01-01",
        },
    )
    await hass.async_block_till_done()
    odometer = hass.states.get(_entity(hass, car["id"], "odometer"))
    assert odometer.state == "20000.0"
    assert odometer.attributes["reading"] == 20000.0
    assert odometer.attributes["unit_of_measurement"] == "km"
    assert odometer.attributes["source"] == "manual"
    distance = hass.states.get(_entity(hass, car["id"], "next_due_distance"))
    assert distance.state == "100.0" and distance.attributes["job"] == "Oil"
    date = hass.states.get(_entity(hass, car["id"], "next_due_date"))
    assert date.attributes["job"] == "Oil"
    status = hass.states.get(_entity(hass, car["id"], "status"))
    assert status.state == "soon" and status.attributes["due_jobs"] == ["Oil"]
    assert status.attributes["next_item_id"] == oil["id"]
    overdue = hass.states.get(_entity(hass, car["id"], "overdue"))
    assert overdue.state == "off"
    await call("set_odometer", {"car_id": car["id"], "value": 20200}, as_="user")
    await hass.async_block_till_done()
    assert hass.states.get(_entity(hass, car["id"], "overdue")).state == "on"
    assert hass.states.get(_entity(hass, car["id"], "status")).state == "overdue"
    todo = _entity(hass, car["id"], "jobs")
    assert hass.states.get(todo).state == "1"
    device = find_device(dr.async_get(hass), car["id"], setup_entry.entry_id)
    assert device.name == "Civic"


async def test_a_todo_check_logs_a_service(hass, setup_entry, call) -> None:
    car = await _car(hass, call)
    item = (
        await call(
            "add_item",
            {
                "car_id": car["id"],
                "name": "Oil",
                "interval_months": 12,
                "last_date": "2020-01-01",
            },
        )
    )["item"]
    await hass.async_block_till_done()
    todo = _entity(hass, car["id"], "jobs")
    await hass.services.async_call(
        "todo",
        "update_item",
        {"item": item["id"], "status": "completed"},
        target={"entity_id": todo},
        blocking=True,
    )
    await hass.async_block_till_done()
    view = await call("get_car", {"car_id": car["id"]})
    assert view["services"][0]["items"] == [item["id"]]
    assert view["services"][0]["reading"] == 20000.0
    assert hass.states.get(todo).state == "0"
    from homeassistant.exceptions import ServiceValidationError

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "todo",
            "update_item",
            {"item": item["id"], "rename": "x"},
            target={"entity_id": todo},
            blocking=True,
        )


async def test_delete_and_rename_follow(hass, setup_entry, call) -> None:
    car = await _car(hass, call)
    await call("update_car", {"car_id": car["id"], "name": "Civic 2", "make": "Honda"})
    await hass.async_block_till_done()
    devices = dr.async_get(hass)
    device = find_device(devices, car["id"], setup_entry.entry_id)
    assert device.name == "Civic 2" and device.manufacturer == "Honda"
    entity_id = _entity(hass, car["id"], "odometer")
    await call("delete_car", {"car_id": car["id"]})
    await hass.async_block_till_done()
    assert find_device(devices, car["id"], setup_entry.entry_id) is None
    assert er.async_get(hass).async_get(entity_id) is None


async def test_events(hass, setup_entry, call) -> None:
    seen = _events(hass)
    car = await _car(hass, call)
    item = (
        await call(
            "add_item", {"car_id": car["id"], "name": "Oil", "interval_months": 6}
        )
    )["item"]
    await call("update_item", {"item_id": item["id"], "interval_months": 6})
    await call("update_item", {"item_id": item["id"], "interval_months": 7})
    service = (
        await call(
            "log_service",
            {"car_id": car["id"], "items": [item["id"]], "reading": 20100, "cost": 10},
        )
    )["service"]
    await call("delete_service", {"service_id": service["id"]})
    await call("update_car", {"car_id": car["id"], "plate": "X"})
    await call("delete_car", {"car_id": car["id"]})
    await hass.async_block_till_done()
    names = [e.event_type.removeprefix("car_keeper_") for e in seen]
    assert names == [
        "car_added",
        "odometer_updated",
        "item_added",
        "item_updated",
        "service_logged",
        "odometer_updated",
        "service_removed",
        "car_updated",
        "item_removed",
        "car_removed",
    ]
    logged = next(e for e in seen if e.event_type == "car_keeper_service_logged").data
    assert logged["cost"] == 10 and logged["items"] == [item["id"]]
    updated = next(e for e in seen if e.event_type == "car_keeper_item_updated").data
    assert updated["changed_fields"] == ["interval_months"]


async def test_due_events_fire_once(hass, setup_entry, call, monkeypatch) -> None:
    seen = _events(hass)
    car = await _car(hass, call)
    await call(
        "add_item",
        {
            "car_id": car["id"],
            "name": "Oil",
            "interval_distance": 500,
            "last_reading": 19600,
        },
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    store = setup_entry.runtime_data.store
    await store.check_due(store_module.today())
    await store.check_due(store_module.today())
    await call("set_odometer", {"car_id": car["id"], "value": 20150})
    await hass.async_block_till_done(wait_background_tasks=True)
    due = [
        e.event_type
        for e in seen
        if "due_soon" in e.event_type or "overdue" in e.event_type
    ]
    assert due == ["car_keeper_item_due_soon", "car_keeper_item_overdue"]
    payload = next(e for e in seen if e.event_type == "car_keeper_item_overdue").data
    assert payload["status"] == "overdue" and payload["distance_left"] == -50.0


async def test_the_odometer_follows_a_sensor(hass, setup_entry, call) -> None:
    hass.states.async_set("sensor.odo", "12000", {"unit_of_measurement": "mi"})
    car = await _car(
        hass,
        call,
        odometer=None,
        odometer_source="entity",
        odometer_entity_id="sensor.odo",
        unit="km",
    )
    await hass.async_block_till_done(wait_background_tasks=True)
    store = setup_entry.runtime_data.store
    assert store.state["cars"][car["id"]]["odometer"]["value"] == 19312.1
    hass.states.async_set("sensor.odo", "unavailable", {"unit_of_measurement": "mi"})
    await hass.async_block_till_done(wait_background_tasks=True)
    assert store.state["cars"][car["id"]]["odometer"]["value"] == 19312.1
    issue_id = f"odometer_decreased_{car['id']}"
    for value in ("100", "90"):
        hass.states.async_set("sensor.odo", value, {"unit_of_measurement": "mi"})
        await hass.async_block_till_done(wait_background_tasks=True)
    issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
    assert issue is not None and issue.translation_placeholders["car"] == "Civic"
    assert store.state["cars"][car["id"]]["odometer"]["value"] == 19312.1
    await call("correct_odometer", {"car_id": car["id"], "value": 144.8})
    assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
    await call("update_car", {"car_id": car["id"], "odometer_source": "manual"})
    hass.states.async_set("sensor.odo", "99999", {"unit_of_measurement": "mi"})
    await hass.async_block_till_done(wait_background_tasks=True)
    assert store.state["cars"][car["id"]]["odometer"]["value"] == 144.8


async def test_websocket_twin_and_state(hass, setup_entry, call, ws) -> None:
    car = await _car(hass, call, vin="VIN9")
    user = await ws("user")
    await user.send_json({"id": 1, "type": "car_keeper/get_state"})
    reply = await user.receive_json()
    assert reply["success"] and reply["result"]["cars"][car["id"]]["vin"] == "VIN9"
    assert reply["result"]["cars"][car["id"]]["summary"]["status"] == "ok"
    await user.send_json(
        {"id": 2, "type": "car_keeper/delete_car", "car_id": car["id"]}
    )
    reply = await user.receive_json()
    assert not reply["success"] and reply["error"]["code"] == "unauthorized"
    await user.send_json(
        {"id": 3, "type": "car_keeper/set_odometer", "car_id": car["id"], "value": 1}
    )
    reply = await user.receive_json()
    assert reply["error"]["code"] == "odometer_decreased"
    assert "below the last reading" in reply["error"]["message"]
    await user.send_json(
        {
            "id": 4,
            "type": "car_keeper/set_odometer",
            "car_id": car["id"],
            "value": 30000,
        }
    )
    reply = await user.receive_json()
    assert reply["success"] and reply["result"]["car"]["odometer"]["value"] == 30000.0
