"""The sync with Home Keeper: an appliance for each car, a task for each job.

``task_plan.py`` decides the steps. This module reads Home Keeper, runs the steps
with the Home Keeper services, and follows the Home Keeper task events:

- A completion in Home Keeper adds a service record in Car Keeper.
- An undone completion in Home Keeper takes the job off its service record.
- A deleted task makes a pass, which stops the task of the job.

Each call sends the origin ``car_keeper``, and the listeners ignore an event with
that origin, so a change never comes back as a loop. A pass runs at start, when
Home Keeper becomes available, and after each store change. 1 pass runs at a time,
and a change while it runs makes 1 more pass.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from . import projections, schedule, task_plan
from .const import DOMAIN, HOME_KEEPER_DOMAIN, HOME_KEEPER_ORIGIN, ORIGIN
from .entity import find_device

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry

    from .home_keeper import HomeKeeperLink
    from .store import CarStore

_LOGGER = logging.getLogger(__name__)

EVENT_TASK_COMPLETED = f"{HOME_KEEPER_DOMAIN}_task_completed"
EVENT_TASK_UNCOMPLETED = f"{HOME_KEEPER_DOMAIN}_task_uncompleted"
EVENT_TASK_DELETED = f"{HOME_KEEPER_DOMAIN}_task_deleted"

#: The Home Keeper services that a pass needs.
REQUIRED_SERVICES = (
    "list_tasks",
    "list_assets",
    "add_task",
    "update_task",
    "delete_task",
    "complete_task",
    "delete_completion",
    "set_task_meter",
    "set_task_consumable",
    "add_asset",
    "update_asset",
    "update_managed_asset",
    "adjust_part_stock",
)
#: A pass plans again after its steps, up to this many times.
MAX_ROUNDS = 4
#: The passes in a row that changes during a pass can ask for.
MAX_PASSES = 10


def offset_text(now: dt.datetime) -> str:
    """The UTC offset of *now* as ``+HH:MM``."""
    text = now.strftime("%z") or "+0000"
    return f"{text[:3]}:{text[3:]}"


def _item_id(data: dict[str, Any]) -> str | None:
    source = (data.get("source") or {}).get(DOMAIN) or {}
    item_id = source.get("item_id")
    return item_id if isinstance(item_id, str) else None


class HomeKeeperSync:
    """Runs the plan of ``task_plan`` against Home Keeper."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        store: CarStore,
        link: HomeKeeperLink,
    ) -> None:
        self._hass = hass
        self._entry = entry
        self._store = store
        self._link = link
        self._lock = asyncio.Lock()
        self._again = False
        # True when a change that the sync did not make came in during a round.
        self._outside = False
        # True while the sync writes its own bookkeeping to the store.
        self._writing = False
        self._unsubs: list[Any] = []
        #: The number of passes that ran. The tests read it.
        self.passes = 0

    @callback
    def async_start(self) -> None:
        """Listen to the store, the link and the Home Keeper events."""
        bus = self._hass.bus
        self._unsubs += [
            self._store.async_add_listener(self.schedule),
            self._link.async_add_listener(self.schedule),
            bus.async_listen(EVENT_TASK_COMPLETED, self._task_completed),
            bus.async_listen(EVENT_TASK_UNCOMPLETED, self._task_uncompleted),
            bus.async_listen(EVENT_TASK_DELETED, self._task_deleted),
            # A new car gets its device and its odometer sensor after the store
            # change. The appliance and the tasks wait for them.
            bus.async_listen(dr.EVENT_DEVICE_REGISTRY_UPDATED, self._registry_created),
            bus.async_listen(er.EVENT_ENTITY_REGISTRY_UPDATED, self._registry_created),
        ]
        self.schedule()

    @callback
    def _registry_created(self, event: Event[Any]) -> None:
        if event.data.get("action") != "create":
            return
        if "device_id" in event.data:
            device = dr.async_get(self._hass).async_get(event.data["device_id"])
            ours = device is not None and any(
                domain == DOMAIN for domain, _ in device.identifiers
            )
        else:
            entity = er.async_get(self._hass).async_get(event.data["entity_id"])
            ours = entity is not None and entity.config_entry_id == self._entry.entry_id
        if ours:
            self.schedule()

    @callback
    def async_stop(self) -> None:
        """Stop the listeners."""
        for unsub in self._unsubs:
            unsub()
        self._unsubs.clear()

    @callback
    def schedule(self) -> None:
        """Run a pass soon. A pass that runs now runs again after it ends."""
        if self._lock.locked():
            self._again = True
            if not self._writing:
                self._outside = True
            return
        self._entry.async_create_background_task(
            self._hass, self.async_pass(), "car_keeper home keeper sync"
        )

    def _ready(self) -> bool:
        has = self._hass.services.has_service
        return self._link.available and all(
            has(HOME_KEEPER_DOMAIN, s) for s in REQUIRED_SERVICES
        )

    async def async_pass(self) -> None:
        """Make Home Keeper the same as Car Keeper."""
        async with self._lock:
            for _ in range(MAX_PASSES):
                self._again = False
                if not self._ready():
                    return
                self.passes += 1
                try:
                    await self._run()
                except (HomeAssistantError, vol.Invalid) as err:
                    _LOGGER.warning("The Home Keeper sync stopped: %s", err)
                    return
                if not self._again:
                    return
            _LOGGER.warning("The Home Keeper sync stopped after %s passes", MAX_PASSES)

    async def _call(
        self, service: str, data: dict[str, Any], *, response: bool = False
    ) -> Any:
        return await self._hass.services.async_call(
            HOME_KEEPER_DOMAIN,
            service,
            data,
            blocking=True,
            return_response=response,
        )

    async def _run(self) -> None:
        await self._drain()
        for _ in range(MAX_ROUNDS):
            assets = (await self._call("list_assets", {}, response=True))["assets"]
            asset_plan = task_plan.plan_assets(
                self._store.state["cars"],
                assets,
                device_ids=self._device_ids(),
                entry_id=self._entry.entry_id,
            )
            tasks = (await self._call("list_tasks", {}, response=True))["tasks"]
            plan = task_plan.plan_tasks(
                self._store.state,
                tasks,
                entity_ids=self._entity_ids(),
                device_ids=self._device_ids(),
                date_limits=self._date_limits(),
                entry_id=self._entry.entry_id,
                offset=offset_text(dt_util.now()),
            )
            if not any(asset_plan.values()) and not any(plan.values()):
                return
            self._outside = False
            await self._apply_assets(asset_plan)
            await self._apply_tasks(plan)
            if self._outside:
                # A change from outside came in. The next pass plans from it.
                return
        steps = {
            f"{side}.{key}": value
            for side, steps_of in (("assets", asset_plan), ("tasks", plan))
            for key, value in steps_of.items()
            if value
        }
        _LOGGER.warning("The Home Keeper sync did not settle: %s", steps)

    # ── Inputs from the registries ───────────────────────────────────────────

    def _device_ids(self) -> dict[str, str | None]:
        devices = dr.async_get(self._hass)
        out: dict[str, str | None] = {}
        for car_id in self._store.state["cars"]:
            device = find_device(devices, car_id, self._entry.entry_id)
            out[car_id] = device.id if device else None
        return out

    def _entity_ids(self) -> dict[str, str | None]:
        registry = er.async_get(self._hass)
        return {
            car_id: registry.async_get_entity_id("sensor", DOMAIN, f"{car_id}_odometer")
            for car_id in self._store.state["cars"]
        }

    def _date_limits(self) -> dict[str, str | None]:
        state = self._store.state
        day = dt_util.now().date().isoformat()
        out: dict[str, str | None] = {}
        for item_id, item in state["items"].items():
            if item.get("kind") != "date" or item["car_id"] not in state["cars"]:
                continue
            daily = schedule.daily_distance(
                state["readings"].get(item["car_id"]) or [], day
            )
            out[item_id] = projections.evaluate_item(state, item, day, daily)[
                "date_limit"
            ]
        return out

    # ── Steps ────────────────────────────────────────────────────────────────

    async def _apply_assets(self, plan: dict[str, list[dict[str, Any]]]) -> None:
        for step in plan["adds"]:
            await self._call("add_asset", step["fields"])
        for step in plan["binds"]:
            await self._own(
                self._store.set_bookkeeping,
                "cars",
                step["car_id"],
                hk_asset_id=step["asset_id"],
            )
        for step in plan["updates"]:
            fields = dict(step["fields"])
            if "name" in fields:
                await self._call(
                    "update_managed_asset",
                    {"asset_id": step["asset_id"], "name": fields.pop("name")},
                )
            if fields:
                await self._call(
                    "update_asset", {"asset_id": step["asset_id"], **fields}
                )
        for step in plan["releases"]:
            await self._call(
                "update_asset", {"asset_id": step["asset_id"], "managed_by": None}
            )

    async def _apply_tasks(self, plan: dict[str, list[dict[str, Any]]]) -> None:
        for step in plan["deletes"]:
            await self._call("delete_task", {"task_id": step["task_id"], "force": True})
        for step in plan["forgets"]:
            await self._own(
                self._store.forget_task, step["item_id"], origin=HOME_KEEPER_ORIGIN
            )
        for step in plan["adds"]:
            reply = await self._call("add_task", step["fields"], response=True)
            await self._own(
                self._store.set_bookkeeping,
                "items",
                step["item_id"],
                hk_task_id=reply["task_id"],
            )
        for step in plan["binds"]:
            await self._own(
                self._store.set_bookkeeping,
                "items",
                step["item_id"],
                hk_task_id=step["task_id"],
            )
        for step in plan["updates"]:
            await self._call(
                "update_task", {"task_id": step["task_id"], **step["fields"]}
            )
        for step in plan["meters"]:
            await self._call("set_task_meter", step)
        for step in plan["consumables"]:
            await self._call("set_task_consumable", step)
        for step in plan["completes"]:
            fields = step["fields"]
            await self._call("complete_task", {**fields, "origin": ORIGIN})
            await self._own(
                self._store.set_completion,
                step["service_id"],
                step["item_id"],
                {"task_id": fields["task_id"], "ts": fields["completed_at"]},
            )

    async def _own(self, method: Any, *args: Any, **kwargs: Any) -> Any:
        """Run a store write of the sync. Its change does not ask for a new round."""
        self._writing = True
        try:
            return await method(*args, **kwargs)
        finally:
            self._writing = False

    async def _drain(self) -> None:
        """Send the queued undos and stock moves. A refused entry is dropped."""
        queue = self._store.state["sync"]
        for entry in list(queue["undo"]):
            await self._send(
                "undo",
                entry,
                "delete_completion",
                {"task_id": entry["task_id"], "ts": entry["ts"], "origin": ORIGIN},
            )
        for entry in list(queue["stock"]):
            await self._send("stock", entry, "adjust_part_stock", dict(entry))

    async def _send(
        self, kind: str, entry: dict[str, Any], service: str, data: dict[str, Any]
    ) -> None:
        try:
            await self._call(service, data)
        except (ServiceValidationError, vol.Invalid) as err:
            # The task or the part is gone. A second try fails the same way.
            _LOGGER.info("Home Keeper refused %s %s: %s", service, data, err)
        await self._own(self._store.sync_done, kind, entry)

    # ── Home Keeper events ───────────────────────────────────────────────────

    @callback
    def _task_completed(self, event: Event[Any]) -> None:
        data = dict(event.data)
        item_id = _item_id(data)
        if data.get("origin") == ORIGIN or item_id is None:
            return
        item = self._store.state["items"].get(item_id)
        if item is None:
            return
        completion = {
            "task_id": str(data.get("task_id")),
            "ts": str(data.get("completed_at")),
        }
        self._entry.async_create_background_task(
            self._hass,
            self._log_from_home_keeper(item, data, completion),
            "car_keeper home keeper completion",
        )

    async def _log_from_home_keeper(
        self, item: dict[str, Any], data: dict[str, Any], completion: dict[str, str]
    ) -> None:
        for service in self._store.state["services"].values():
            if completion in (service.get("hk_completions") or {}).values():
                return
        try:
            await self._store.log_service(
                item["car_id"],
                task_plan.service_from_completion(data, item),
                origin=HOME_KEEPER_ORIGIN,
                hk_completions={item["id"]: completion},
            )
        except HomeAssistantError as err:
            _LOGGER.warning("Car Keeper did not log a Home Keeper completion: %s", err)

    @callback
    def _task_uncompleted(self, event: Event[Any]) -> None:
        if event.data.get("origin") == ORIGIN or _item_id(dict(event.data)) is None:
            return
        self._entry.async_create_background_task(
            self._hass,
            self._store.remove_completion(
                str(event.data.get("task_id")), str(event.data.get("ts"))
            ),
            "car_keeper home keeper undo",
        )

    @callback
    def _task_deleted(self, event: Event[Any]) -> None:
        if _item_id(dict(event.data)) is not None:
            self.schedule()


async def async_release(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Give the appliances of Car Keeper to the user when Car Keeper is removed.

    The tasks are not touched: Home Keeper lifts their protection when the config
    entry is gone, so the user can delete them.
    """
    if not hass.services.has_service(HOME_KEEPER_DOMAIN, "list_assets"):
        return
    reply: Any = await hass.services.async_call(
        HOME_KEEPER_DOMAIN, "list_assets", {}, blocking=True, return_response=True
    )
    for asset in (reply or {}).get("assets", []):
        owner = asset.get("managed_by") or {}
        if owner.get("config_entry_id") == entry.entry_id:
            await hass.services.async_call(
                HOME_KEEPER_DOMAIN,
                "update_asset",
                {"asset_id": asset["id"], "managed_by": None},
                blocking=True,
            )
