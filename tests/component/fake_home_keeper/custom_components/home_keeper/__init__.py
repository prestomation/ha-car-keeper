"""A small fake of Home Keeper for the component tier of Car Keeper.

Car Keeper calls the Home Keeper task services (``add_task``, ``update_task``,
``delete_task``, ``complete_task``, ``delete_completion``, ``set_task_meter``,
``set_task_consumable``, ``list_tasks``), the appliance services (``add_asset``,
``update_asset``, ``update_managed_asset``, ``list_assets``, ``adjust_part_stock``)
and ``register_companion``. It also imports ``panel_tabs``. This fake has the same
service names, fields, replies and events as Home Keeper, and keeps the tasks and
the appliances in memory. A completion has the ``ts`` of its ``completed_at``, as
in Home Keeper.

The fake is used in place of the real Home Keeper because the real one has its
own storage, frontend, entity platforms and the Babel requirement, and it
reloads its entry on some task changes. That makes each test slower and less
exact about which call Car Keeper made. The Docker tier runs Car Keeper with
the real Home Keeper, so the contract is also checked against the real code.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.typing import ConfigType

DOMAIN = "home_keeper"
DATA = "home_keeper_fake"


def fake_data(hass: HomeAssistant) -> dict[str, Any]:
    """The records and the calls of the fake."""
    return hass.data.setdefault(
        DATA, {"tasks": {}, "assets": {}, "companions": {}, "calls": []}
    )


def _event_data(task: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "task_id": task["id"],
        "name": task["name"],
        "device_id": task.get("device_id"),
        "recurrence_type": task.get("recurrence_type"),
        "source": task.get("source"),
        "managed_by": task.get("managed_by"),
        **extra,
    }


def _ts(value: Any) -> str:
    if isinstance(value, dt.datetime):
        when = value
    elif value:
        when = dt.datetime.fromisoformat(str(value))
    else:
        when = dt.datetime.now(dt.UTC)
    if when.tzinfo is None:
        when = when.replace(tzinfo=dt.UTC)
    return when.isoformat()


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the fake services."""
    data = fake_data(hass)
    tasks: dict[str, dict[str, Any]] = data["tasks"]
    assets: dict[str, dict[str, Any]] = data["assets"]

    def _record(name: str, call: ServiceCall) -> None:
        data["calls"].append((name, dict(call.data)))

    def _task(task_id: str) -> dict[str, Any]:
        if task_id not in tasks:
            raise ServiceValidationError(f"unknown task: {task_id}")
        return tasks[task_id]

    async def add_task(call: ServiceCall) -> dict[str, Any]:
        _record("add_task", call)
        task = {
            **{k: v for k, v in call.data.items() if k != "last_completed"},
            "id": uuid.uuid4().hex,
            "source": dict(call.data.get("source") or {}),
            "sensor": dict(call.data.get("sensor") or {}) or None,
            "completions": [],
        }
        tasks[task["id"]] = task
        hass.bus.async_fire("home_keeper_task_created", _event_data(task))
        return {"task_id": task["id"]}

    async def update_task(call: ServiceCall) -> None:
        _record("update_task", call)
        task = _task(call.data["task_id"])
        task.update({k: v for k, v in call.data.items() if k != "task_id"})
        hass.bus.async_fire("home_keeper_task_updated", _event_data(task))

    async def delete_task(call: ServiceCall) -> None:
        _record("delete_task", call)
        task = tasks.pop(call.data["task_id"], None)
        if task is not None:
            hass.bus.async_fire("home_keeper_task_deleted", _event_data(task))

    async def complete_task(call: ServiceCall) -> None:
        _record("complete_task", call)
        task = _task(call.data["task_id"])
        ts = _ts(call.data.get("completed_at"))
        entry = {"ts": ts}
        for key in ("cost", "note", "who", "reading"):
            if key in call.data:
                entry[key] = call.data[key]
        task["completions"].append(entry)
        if "reading" in call.data and task.get("sensor"):
            task["sensor"]["baseline"] = call.data["reading"]
        extra = {k: v for k, v in entry.items() if k != "ts"}
        hass.bus.async_fire(
            "home_keeper_task_completed",
            _event_data(task, completed_at=ts, origin=call.data.get("origin"), **extra),
        )

    async def delete_completion(call: ServiceCall) -> None:
        _record("delete_completion", call)
        task = _task(call.data["task_id"])
        task["completions"] = [
            c for c in task["completions"] if c["ts"] != call.data["ts"]
        ]
        hass.bus.async_fire(
            "home_keeper_task_uncompleted",
            _event_data(task, ts=call.data["ts"], origin=call.data.get("origin")),
        )

    async def set_task_meter(call: ServiceCall) -> None:
        _record("set_task_meter", call)
        _task(call.data["task_id"])["sensor"]["baseline"] = call.data["baseline"]

    async def set_task_consumable(call: ServiceCall) -> None:
        _record("set_task_consumable", call)
        task = _task(call.data["task_id"])
        if call.data.get("parts"):
            task["source"]["parts"] = list(call.data["parts"])
        else:
            task["source"].pop("parts", None)

    async def list_tasks(call: ServiceCall) -> dict[str, Any]:
        return {"tasks": [dict(t) for t in tasks.values()]}

    async def add_asset(call: ServiceCall) -> None:
        _record("add_asset", call)
        asset = {**call.data, "id": uuid.uuid4().hex, "parts": []}
        assets[asset["id"]] = asset

    async def update_asset(call: ServiceCall) -> None:
        _record("update_asset", call)
        asset = assets[call.data["asset_id"]]
        locked = (asset.get("managed_by") or {}).get("locked_fields") or []
        for key, value in call.data.items():
            if key != "asset_id" and key not in locked:
                asset[key] = value

    async def update_managed_asset(call: ServiceCall) -> None:
        _record("update_managed_asset", call)
        asset = assets[call.data["asset_id"]]
        if "name" in call.data:
            asset["name"] = call.data["name"]

    async def list_assets(call: ServiceCall) -> dict[str, Any]:
        return {"assets": [dict(a) for a in assets.values()]}

    async def adjust_part_stock(call: ServiceCall) -> dict[str, Any]:
        _record("adjust_part_stock", call)
        asset = assets.get(call.data["asset_id"])
        part = next(
            (
                p
                for p in (asset or {}).get("parts", [])
                if p["id"] == call.data["part_id"]
            ),
            None,
        )
        if part is None:
            raise ServiceValidationError("unknown part")
        part["stock"] = (part.get("stock") or 0) + call.data["delta"]
        return {"stock": part["stock"]}

    async def register_companion(call: ServiceCall) -> None:
        _record("register_companion", call)
        data["companions"][call.data["domain"]] = dict(call.data)

    for name, handler, response in (
        ("add_task", add_task, SupportsResponse.OPTIONAL),
        ("update_task", update_task, SupportsResponse.NONE),
        ("delete_task", delete_task, SupportsResponse.NONE),
        ("complete_task", complete_task, SupportsResponse.NONE),
        ("delete_completion", delete_completion, SupportsResponse.NONE),
        ("set_task_meter", set_task_meter, SupportsResponse.NONE),
        ("set_task_consumable", set_task_consumable, SupportsResponse.NONE),
        ("list_tasks", list_tasks, SupportsResponse.ONLY),
        ("add_asset", add_asset, SupportsResponse.NONE),
        ("update_asset", update_asset, SupportsResponse.NONE),
        ("update_managed_asset", update_managed_asset, SupportsResponse.NONE),
        ("list_assets", list_assets, SupportsResponse.ONLY),
        ("adjust_part_stock", adjust_part_stock, SupportsResponse.OPTIONAL),
        ("register_companion", register_companion, SupportsResponse.NONE),
    ):
        hass.services.async_register(DOMAIN, name, handler, supports_response=response)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: Any) -> bool:
    """Load the config entry. The services exist without it, as in Home Keeper."""
    hass.bus.async_fire("home_keeper_register_companions")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: Any) -> bool:
    """Unload the config entry."""
    return True
