"""Component tests: every service as an admin and as a user who is not an admin.

Record management is admin-only. Every read, ``set_odometer`` and ``log_service``
are open. A read as a user who is not an admin returns every field.
"""

from __future__ import annotations

import pytest
from homeassistant.exceptions import ServiceValidationError, Unauthorized

from custom_components.car_keeper.api_surface import SERVICES

ADMIN_ONLY = {spec.name for spec in SERVICES if spec.admin_only}


async def _car(call, **data):
    reply = await call(
        "add_car",
        {
            "name": "Civic",
            "vin": "1HGCM82633A004352",
            "plate": "ABC-123",
            "odometer": 20000,
            "fuel": "petrol",
            **data,
        },
    )
    return reply["car"]


def test_the_gates_are_the_design() -> None:
    assert {
        "add_car",
        "update_car",
        "delete_car",
        "correct_odometer",
        "add_item",
        "update_item",
        "delete_item",
        "apply_templates",
        "update_service",
        "delete_service",
        "set_settings",
        "export_data",
        "import_data",
    } == ADMIN_ONLY


# Valid fields, so the schema passes and the gate decides.
_FIELDS = {
    "add_car": {"name": "x"},
    "update_car": {"car_id": "x"},
    "delete_car": {"car_id": "x"},
    "correct_odometer": {"car_id": "x", "value": 1},
    "add_item": {"car_id": "x", "name": "x"},
    "update_item": {"item_id": "x"},
    "delete_item": {"item_id": "x"},
    "apply_templates": {"car_id": "x", "starter_jobs": []},
    "update_service": {"service_id": "x"},
    "delete_service": {"service_id": "x"},
    "import_data": {"document": {}},
}


@pytest.mark.parametrize("service", sorted(ADMIN_ONLY))
async def test_admin_only_services_refuse_a_user(setup_entry, call, service) -> None:
    with pytest.raises(Unauthorized):
        await call(service, _FIELDS.get(service, {}), as_="user")


async def test_add_car_with_starter_jobs(setup_entry, call) -> None:
    car = await _car(
        call,
        starter_jobs=["engine_oil", "insurance"],
        due_dates={"insurance": "2027-03-01"},
        unit="mi",
    )
    assert car["unit"] == "mi" and car["lead_distance"] == 600
    assert car["odometer"]["value"] == 20000.0
    view = await call("get_car", {"car_id": car["id"]})
    names = {i["name"]: i for i in view["items"]}
    assert names["Engine oil and filter"]["interval_distance"] == 9300
    assert names["Insurance"]["due_date"] == "2027-03-01"
    assert [r["value"] for r in view["readings"]] == [20000.0]


async def test_a_user_reads_every_field(setup_entry, call) -> None:
    car = await _car(call)
    item = (
        await call(
            "add_item", {"car_id": car["id"], "name": "Oil", "interval_months": 6}
        )
    )["item"]
    await call(
        "log_service",
        {
            "car_id": car["id"],
            "items": [item["id"]],
            "shop": "Ballard Auto",
            "cost": 84.5,
            "notes": "rotated",
        },
    )
    cars = (await call("list_cars", as_="user"))["cars"]
    assert cars[0]["vin"] == "1HGCM82633A004352" and cars[0]["plate"] == "ABC-123"
    view = await call("get_car", {"car_id": car["id"]}, as_="user")
    assert view["services"][0]["cost"] == 84.5
    assert view["services"][0]["shop"] == "Ballard Auto"
    assert view["services"][0]["notes"] == "rotated"
    assert (await call("list_services", {}, as_="user"))["services"][0]["cost"] == 84.5
    assert (await call("list_items", {"car_id": car["id"]}, as_="user"))["items"][0][
        "due"
    ]


async def test_a_user_sets_the_odometer_and_logs_a_service(setup_entry, call) -> None:
    car = await _car(call)
    item = (
        await call(
            "add_item", {"car_id": car["id"], "name": "Oil", "interval_distance": 10000}
        )
    )["item"]
    reply = await call(
        "set_odometer", {"car_id": car["id"], "value": 21000}, as_="user"
    )
    assert reply["car"]["odometer"]["value"] == 21000.0
    with pytest.raises(ServiceValidationError) as info:
        await call("set_odometer", {"car_id": car["id"], "value": 100}, as_="user")
    assert info.value.translation_key == "odometer_decreased"
    logged = await call(
        "log_service",
        {"car_id": car["id"], "items": [item["id"]], "reading": 21500},
        as_="user",
    )
    assert logged["service"]["items"] == [item["id"]]
    view = await call("get_car", {"car_id": car["id"]})
    assert view["car"]["odometer"]["value"] == 21500.0
    oil = view["items"][0]
    assert oil["last_done"]["reading"] == 21500.0
    assert oil["due"]["distance_limit"] == 31500.0


async def test_correct_odometer(setup_entry, call) -> None:
    car = await _car(call)
    reply = await call(
        "correct_odometer", {"car_id": car["id"], "value": 100, "offset": 5}
    )
    assert reply["car"]["odometer"]["value"] == 100.0
    assert reply["car"]["odometer"]["offset"] == 5.0


async def test_unit_change_converts_each_value(setup_entry, call) -> None:
    car = await _car(call, odometer=16093.44)
    item = (
        await call(
            "add_item", {"car_id": car["id"], "name": "Oil", "interval_distance": 16000}
        )
    )["item"]
    await call(
        "log_service", {"car_id": car["id"], "items": [item["id"]], "reading": 16093.44}
    )
    await call("update_car", {"car_id": car["id"], "unit": "mi"})
    view = await call("get_car", {"car_id": car["id"]})
    assert view["car"]["unit"] == "mi"
    assert view["car"]["odometer"]["value"] == 10000.0
    assert view["car"]["lead_distance"] == 621
    assert view["items"][0]["interval_distance"] == 9942
    assert view["items"][0]["last_done"]["reading"] == 10000.0
    assert view["services"][0]["reading"] == 10000.0


async def test_items_and_service_records(setup_entry, call) -> None:
    car = await _car(call)
    item = (
        await call(
            "add_item", {"car_id": car["id"], "name": "Oil", "interval_months": 6}
        )
    )["item"]
    updated = await call("update_item", {"item_id": item["id"], "interval_months": 12})
    assert updated["item"]["interval_months"] == 12
    added = await call(
        "apply_templates", {"car_id": car["id"], "starter_jobs": ["wipers"]}
    )
    assert added["items"][0]["template_id"] == "wipers"
    service = (
        await call(
            "log_service",
            {"car_id": car["id"], "items": [item["id"]], "date": "2026-01-01"},
        )
    )["service"]
    changed = await call(
        "update_service",
        {
            "service_id": service["id"],
            "date": "2026-02-01",
            "parts_used": [{"asset_id": "a", "part_id": "p"}],
        },
    )
    assert changed["service"]["date"] == "2026-02-01"
    assert changed["service"]["parts_used"] == [
        {"asset_id": "a", "part_id": "p", "quantity": 1}
    ]
    assert (await call("delete_service", {"service_id": service["id"]})) == {
        "service_id": service["id"]
    }
    view = await call("get_car", {"car_id": car["id"]})
    assert view["items"][0]["last_done"] is None
    assert (await call("delete_item", {"item_id": item["id"]})) == {
        "item_id": item["id"]
    }
    assert (await call("delete_car", {"car_id": car["id"]})) == {"car_id": car["id"]}
    assert (await call("list_cars"))["cars"] == []


async def test_errors_are_localized(setup_entry, call) -> None:
    for service, data, key in (
        ("get_car", {"car_id": "nope"}, "car_not_found"),
        ("update_item", {"item_id": "nope"}, "item_not_found"),
        ("delete_service", {"service_id": "nope"}, "service_not_found"),
        ("add_car", {"name": " "}, "field_required"),
        ("apply_templates", {"car_id": "x", "starter_jobs": []}, "car_not_found"),
        ("set_settings", {"templates": {"nope": {}}}, "template_not_found"),
    ):
        with pytest.raises(ServiceValidationError) as info:
            await call(service, data)
        assert info.value.translation_key == key, service


async def test_export_and_import(setup_entry, call) -> None:
    car = await _car(call)
    await call("add_item", {"car_id": car["id"], "name": "Oil", "interval_months": 6})
    exported = await call("export_data")
    assert exported["format"] == 1 and exported["version"] == "0.1.0b1"
    assert exported["data"]["cars"][0]["vin"] == "1HGCM82633A004352"
    preview = await call("import_data", {"document": exported, "dry_run": True})
    assert preview["ok"] and preview["dry_run"] and preview["records"] == 0
    await call("delete_car", {"car_id": car["id"]})
    preview = await call("import_data", {"document": exported, "dry_run": True})
    assert preview["records"] == 3 and (await call("list_cars"))["cars"] == []
    done = await call("import_data", {"document": exported})
    assert done["counts"]["cars"]["created"] == 1
    assert (await call("list_cars"))["cars"][0]["name"] == "Civic"
    bad = await call("import_data", {"document": {"format": 9, "data": {}}})
    assert not bad["ok"]
    assert bad["problems"][0]["message"].startswith("The export format 9 is newer")


async def test_settings(setup_entry, call) -> None:
    reply = await call("set_settings", {"templates": {"wipers": {"months": 6}}})
    assert reply["settings"]["templates"] == {"wipers": {"months": 6}}
