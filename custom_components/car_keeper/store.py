"""The Car Keeper store: the 1 write path for Car Keeper data.

Every change goes through a method of :class:`CarStore`. Each method checks the
input with the pure core, changes the document, saves it, fires the bus events of
the change and then tells the listeners (the coordinator, the ``subscribe``
command and the syncs). Entities, the tab and the cards read the document and
never write it.

``revision`` goes up by 1 on each change. The ``subscribe`` websocket command
sends it, and the client then reads ``get_state`` again.
"""

from __future__ import annotations

import copy
import logging
import uuid
from collections.abc import Callable, Iterable
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from . import (
    events,
    history,
    import_export,
    models,
    projections,
    readings,
    templates,
    units,
)
from .const import (
    EVENT_CAR_ADDED,
    EVENT_CAR_REMOVED,
    EVENT_CAR_UPDATED,
    EVENT_DATA_IMPORTED,
    EVENT_ITEM_ADDED,
    EVENT_ITEM_DUE_SOON,
    EVENT_ITEM_OVERDUE,
    EVENT_ITEM_REMOVED,
    EVENT_ITEM_UPDATED,
    EVENT_ODOMETER_UPDATED,
    EVENT_SERVICE_LOGGED,
    EVENT_SERVICE_REMOVED,
    EVENT_SERVICE_UPDATED,
    EVENT_SETTINGS_UPDATED,
    HOME_KEEPER_ORIGIN,
    STORAGE_KEY,
    STORAGE_MINOR_VERSION,
    STORAGE_VERSION,
    UNITS,
)
from .models import CarKeeperError
from .schedule import OK, OVERDUE, SOON

_LOGGER = logging.getLogger(__name__)

Event = tuple[str, dict[str, Any]]


class _CarStorage(Store[dict[str, Any]]):
    """The storage file, with the migration hook."""

    async def _async_migrate_func(
        self,
        old_major_version: int,
        old_minor_version: int,
        old_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Return the document in the current version.

        Version 1.1 is the first version. ``models.normalize_state`` adds each
        missing section, so a new section needs no migration step.
        """
        return models.normalize_state(old_data)


def today() -> str:
    """Today in the time zone of Home Assistant, as ``YYYY-MM-DD``."""
    return dt_util.now().date().isoformat()


def now() -> str:
    """The time now, aware, in ISO 8601."""
    return dt_util.now().isoformat()


def new_id() -> str:
    """A new record id."""
    return uuid.uuid4().hex


class CarStore:
    """Loads, saves and changes the Car Keeper document, and fires the events."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self._storage = _CarStorage(
            hass, STORAGE_VERSION, STORAGE_KEY, minor_version=STORAGE_MINOR_VERSION
        )
        self.state: dict[str, Any] = models.empty_state()
        self.revision = 0
        self._listeners: list[Callable[[], None]] = []

    async def load(self) -> None:
        """Load the document, or start an empty one."""
        self.state = models.normalize_state(await self._storage.async_load())

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Call *listener* after each change. Return a callable that removes it."""
        self._listeners.append(listener)

        def remove() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            try:
                listener()
            except Exception:
                _LOGGER.exception("A Car Keeper store listener failed")

    async def _commit(self, fired: list[Event]) -> None:
        """Save, fire the events and tell the listeners."""
        await self._storage.async_save(self.state)
        self.revision += 1
        for name, data in fired:
            self.hass.bus.async_fire(name, data)
        self._notify_listeners()

    # ── Lookups ──────────────────────────────────────────────────────────────

    def _get(self, section: str, key: str, record_id: str) -> dict[str, Any]:
        record = self.state[section].get(record_id)
        if record is None:
            raise CarKeeperError(f"{key}_not_found", id=record_id)
        return copy.deepcopy(record)

    def car(self, car_id: str) -> dict[str, Any]:
        """The car, or ``car_not_found``."""
        return self._get("cars", "car", car_id)

    def item(self, item_id: str) -> dict[str, Any]:
        """The item, or ``item_not_found``."""
        return self._get("items", "item", item_id)

    def service(self, service_id: str) -> dict[str, Any]:
        """The service record, or ``service_not_found``."""
        return self._get("services", "service", service_id)

    def items_of(self, car_id: str) -> list[dict[str, Any]]:
        """The items of a car."""
        return [
            copy.deepcopy(i)
            for i in self.state["items"].values()
            if i["car_id"] == car_id
        ]

    # ── Cars ─────────────────────────────────────────────────────────────────

    async def add_car(
        self,
        data: dict[str, Any],
        *,
        starter: Iterable[str] = (),
        names: dict[str, str] | None = None,
        due_dates: dict[str, str] | None = None,
        origin: str | None = None,
        by: str | None = None,
    ) -> dict[str, Any]:
        """Add a car, its first reading and the selected starter jobs."""
        day, stamp = today(), now()
        car = models.build_car(
            data,
            car_id=new_id(),
            today=day,
            default_unit=self.state["settings"]["unit"],
        )
        source = data.get("odometer_source") or readings.MANUAL
        car["odometer"] = readings.bound(
            car["odometer"], source, data.get("odometer_entity_id")
        )
        plans = []
        if starter:
            plans = templates.items_for(
                list(starter),
                unit=car["unit"],
                overrides=self.state["settings"]["templates"],
                names=names or {},
                due_dates=due_dates,
                today=day,
            )
        fired: list[Event] = [(EVENT_CAR_ADDED, events.car_event_data(car, origin))]
        new_items = []
        for plan in plans:
            item = models.build_item(
                plan["data"],
                item_id=new_id(),
                car=car,
                today=day,
                template_id=plan["template_id"],
            )
            new_items.append(item)
            fired.append((EVENT_ITEM_ADDED, events.item_event_data(item, origin)))
        self.state["cars"][car["id"]] = car
        for item in new_items:
            self.state["items"][item["id"]] = item
        value = car["odometer"]["value"]
        if value is not None:
            first = readings.reading(value, stamp, readings.MANUAL, by)
            self.state["readings"][car["id"]] = [first]
            car["odometer"]["updated"] = stamp
            fired.append(
                (EVENT_ODOMETER_UPDATED, events.odometer_event_data(car, first, origin))
            )
        await self._commit(fired)
        return copy.deepcopy(car)

    async def update_car(
        self, car_id: str, data: dict[str, Any], *, origin: str | None = None
    ) -> dict[str, Any]:
        """Change the fields of a car, its unit or the source of its odometer."""
        car = self.car(car_id)
        new, changed = models.update_car(car, data)
        if "odometer_source" in data or "odometer_entity_id" in data:
            odometer = readings.bound(
                new["odometer"],
                data.get("odometer_source") or new["odometer"]["source"],
                data.get("odometer_entity_id", new["odometer"]["entity_id"]),
            )
            if odometer != new["odometer"]:
                new["odometer"] = odometer
                changed.append("odometer")
        unit = data.get("unit")
        if unit is not None and unit != car["unit"]:
            if unit not in UNITS:
                raise CarKeeperError("invalid_field", field="unit")
            self._change_unit(new, unit)
            changed.append("unit")
        if not changed:
            return car
        self.state["cars"][car_id] = new
        await self._commit(
            [
                (
                    EVENT_CAR_UPDATED,
                    events.changed_data(
                        events.car_event_data(new, origin), sorted(changed)
                    ),
                )
            ]
        )
        return copy.deepcopy(new)

    def _change_unit(self, car: dict[str, Any], unit: str) -> None:
        """Convert each value of *car* to *unit*, 1 time."""
        old = car["unit"]
        car["unit"] = unit
        car["odometer"] = readings.convert_odometer(car["odometer"], old, unit)
        car["lead_distance"] = units.round_interval(
            units.convert(car["lead_distance"], old, unit)
        )
        self.state["readings"][car["id"]] = readings.convert_readings(
            self.state["readings"].get(car["id"]) or [], old, unit
        )
        for item in self.state["items"].values():
            if item["car_id"] != car["id"]:
                continue
            for key in ("interval_distance", "lead_distance"):
                if item.get(key) is not None:
                    item[key] = units.round_interval(
                        units.convert(item[key], old, unit)
                    )
            start = item.get("start") or {}
            if start.get("reading") is not None:
                start["reading"] = units.round_reading(
                    units.convert(start["reading"], old, unit)
                )
        for service in self.state["services"].values():
            if service["car_id"] == car["id"] and service.get("reading") is not None:
                service["reading"] = units.round_reading(
                    units.convert(service["reading"], old, unit)
                )
        ids = [
            i for i, item in self.state["items"].items() if item["car_id"] == car["id"]
        ]
        self.state["items"].update(
            history.refresh(self.state["items"], self.state["services"], ids)
        )

    async def delete_car(
        self, car_id: str, *, origin: str | None = None
    ) -> dict[str, Any]:
        """Delete a car with its items, service records and readings."""
        car = self.car(car_id)
        fired: list[Event] = []
        for item in self.items_of(car_id):
            del self.state["items"][item["id"]]
            fired.append((EVENT_ITEM_REMOVED, events.item_event_data(item, origin)))
        for service_id in [
            s for s, rec in self.state["services"].items() if rec["car_id"] == car_id
        ]:
            del self.state["services"][service_id]
        self.state["readings"].pop(car_id, None)
        del self.state["cars"][car_id]
        fired.append((EVENT_CAR_REMOVED, events.car_event_data(car, origin)))
        await self._commit(fired)
        return car

    async def set_bookkeeping(
        self, section: str, record_id: str, **values: Any
    ) -> None:
        """Write sync fields, such as a Home Keeper id. It fires no event."""
        record = self.state[section].get(record_id)
        if record is None or all(record.get(k) == v for k, v in values.items()):
            return
        record.update(values)
        await self._commit([])

    # ── The odometer ─────────────────────────────────────────────────────────

    async def _write_reading(
        self, car: dict[str, Any], outcome: readings.Outcome, origin: str | None
    ) -> None:
        car["odometer"] = outcome.odometer
        self.state["cars"][car["id"]] = car
        fired: list[Event] = []
        if outcome.reading is not None:
            self.state["readings"][car["id"]] = readings.add(
                self.state["readings"].get(car["id"]) or [], outcome.reading
            )
            fired.append(
                (
                    EVENT_ODOMETER_UPDATED,
                    events.odometer_event_data(car, outcome.reading, origin),
                )
            )
        await self._commit(fired)

    async def set_odometer(
        self,
        car_id: str,
        value: float,
        *,
        by: str | None = None,
        origin: str | None = None,
    ) -> dict[str, Any]:
        """Store a typed reading. A value below the last one fails."""
        car = self.car(car_id)
        outcome = readings.typed(car["odometer"], value, now(), by=by)
        await self._write_reading(car, outcome, origin)
        return copy.deepcopy(self.state["cars"][car_id])

    async def correct_odometer(
        self,
        car_id: str,
        value: float,
        *,
        offset: float | None = None,
        by: str | None = None,
        origin: str | None = None,
    ) -> dict[str, Any]:
        """Store an admin correction, also a lower value, and a new offset."""
        car = self.car(car_id)
        outcome = readings.corrected(
            car["odometer"], value, now(), offset=offset, by=by
        )
        await self._write_reading(car, outcome, origin)
        return copy.deepcopy(self.state["cars"][car_id])

    async def entity_reading(
        self, car_id: str, raw: Any, raw_unit: str | None
    ) -> readings.Outcome:
        """Store a new state of the odometer sensor of a car.

        The caller shows a repair issue when ``Outcome.issue`` is True.
        """
        car = self.car(car_id)
        outcome = readings.from_entity(
            car["odometer"], raw, raw_unit, car["unit"], now()
        )
        if outcome.reading is None and outcome.odometer == car["odometer"]:
            return outcome
        await self._write_reading(car, outcome, None)
        return outcome

    # ── Items ────────────────────────────────────────────────────────────────

    async def add_item(
        self, car_id: str, data: dict[str, Any], *, origin: str | None = None
    ) -> dict[str, Any]:
        """Add a maintenance item to a car."""
        car = self.car(car_id)
        item = models.build_item(data, item_id=new_id(), car=car, today=today())
        self.state["items"][item["id"]] = item
        await self._commit([(EVENT_ITEM_ADDED, events.item_event_data(item, origin))])
        return copy.deepcopy(item)

    async def apply_templates(
        self,
        car_id: str,
        template_ids: list[str],
        *,
        names: dict[str, str],
        due_dates: dict[str, str] | None = None,
        origin: str | None = None,
    ) -> list[dict[str, Any]]:
        """Add the selected starter jobs to a car."""

        car = self.car(car_id)
        day = today()
        plans = templates.items_for(
            template_ids,
            unit=car["unit"],
            overrides=self.state["settings"]["templates"],
            names=names,
            due_dates=due_dates,
            today=day,
        )
        new = [
            models.build_item(
                plan["data"],
                item_id=new_id(),
                car=car,
                today=day,
                template_id=plan["template_id"],
            )
            for plan in plans
        ]
        for item in new:
            self.state["items"][item["id"]] = item
        await self._commit(
            [(EVENT_ITEM_ADDED, events.item_event_data(i, origin)) for i in new]
        )
        return copy.deepcopy(new)

    async def update_item(
        self, item_id: str, data: dict[str, Any], *, origin: str | None = None
    ) -> dict[str, Any]:
        """Change the fields of an item."""
        item = self.item(item_id)
        new, changed = models.update_item(item, data)
        if not changed:
            return item
        self.state["items"][item_id] = new
        await self._commit(
            [
                (
                    EVENT_ITEM_UPDATED,
                    events.changed_data(events.item_event_data(new, origin), changed),
                )
            ]
        )
        return copy.deepcopy(new)

    async def delete_item(
        self, item_id: str, *, origin: str | None = None
    ) -> dict[str, Any]:
        """Delete an item. The service records keep their history."""
        item = self.item(item_id)
        del self.state["items"][item_id]
        for service in self.state["services"].values():
            if item_id in service["items"]:
                service["items"] = [i for i in service["items"] if i != item_id]
        await self._commit([(EVENT_ITEM_REMOVED, events.item_event_data(item, origin))])
        return item

    # ── Service records ──────────────────────────────────────────────────────

    def _refresh_last_done(self, item_ids: Iterable[str]) -> None:
        self.state["items"].update(
            history.refresh(self.state["items"], self.state["services"], list(item_ids))
        )

    async def log_service(
        self,
        car_id: str,
        data: dict[str, Any],
        *,
        by: str | None = None,
        origin: str | None = None,
        hk_completions: dict[str, dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Add a service record and mark its jobs done.

        A reading above the odometer moves the odometer to it. A service that
        comes from a Home Keeper completion gives *hk_completions*, so the sync
        does not complete the task again.
        """
        car = self.car(car_id)
        stamp = now()
        service = models.build_service(
            data,
            service_id=new_id(),
            car=car,
            items=self.state["items"],
            today=today(),
            now=stamp,
            origin=origin,
        )
        fired: list[Event] = []
        value = car["odometer"].get("value")
        if service["reading"] is not None and (
            value is None or service["reading"] > value
        ):
            outcome = readings.typed(
                car["odometer"],
                service["reading"],
                stamp,
                by=by,
                source=readings.SERVICE,
            )
            car["odometer"] = outcome.odometer
            self.state["cars"][car_id] = car
            assert outcome.reading is not None
            self.state["readings"][car_id] = readings.add(
                self.state["readings"].get(car_id) or [], outcome.reading
            )
            fired.append(
                (
                    EVENT_ODOMETER_UPDATED,
                    events.odometer_event_data(car, outcome.reading, origin),
                )
            )
        if hk_completions:
            service["hk_completions"] = dict(hk_completions)
        self.state["services"][service["id"]] = service
        self._queue_stock([], service["parts_used"])
        self._refresh_last_done(service["items"])
        fired.insert(
            0, (EVENT_SERVICE_LOGGED, events.service_event_data(service, origin))
        )
        await self._commit(fired)
        return copy.deepcopy(service)

    async def update_service(
        self, service_id: str, data: dict[str, Any], *, origin: str | None = None
    ) -> dict[str, Any]:
        """Change a service record. ``last_done`` follows the history."""
        service = self.service(service_id)
        car = self.car(service["car_id"])
        new, changed = models.update_service(
            service, data, car, self.state["items"], today()
        )
        if "parts_used" in data:
            parts = models.clean_parts(data["parts_used"])
            if parts != service.get("parts_used"):
                new["parts_used"] = parts
                changed.append("parts_used")
        if not changed:
            return service
        gone = [i for i in service["items"] if i not in new["items"]]
        new["hk_completions"] = {
            k: v for k, v in service.get("hk_completions", {}).items() if k not in gone
        }
        if origin != HOME_KEEPER_ORIGIN:
            self._queue_undo(service, gone)
        self._queue_stock(service.get("parts_used", []), new.get("parts_used", []))
        self.state["services"][service_id] = new
        self._refresh_last_done({*service["items"], *new["items"]})
        await self._commit(
            [
                (
                    EVENT_SERVICE_UPDATED,
                    events.changed_data(
                        events.service_event_data(new, origin), sorted(changed)
                    ),
                )
            ]
        )
        return copy.deepcopy(new)

    async def delete_service(
        self, service_id: str, *, origin: str | None = None
    ) -> dict[str, Any]:
        """Delete a service record. ``last_done`` follows the history."""
        service = self.service(service_id)
        del self.state["services"][service_id]
        if origin != HOME_KEEPER_ORIGIN:
            self._queue_undo(service, service["items"])
        self._queue_stock(service.get("parts_used", []), [])
        self._refresh_last_done(service["items"])
        await self._commit(
            [(EVENT_SERVICE_REMOVED, events.service_event_data(service, origin))]
        )
        return service

    # ── The Home Keeper sync ─────────────────────────────────────────────────

    def _queue_undo(self, service: dict[str, Any], item_ids: Iterable[str]) -> None:
        """Ask the sync to delete the Home Keeper completions of *item_ids*."""
        done = service.get("hk_completions") or {}
        for item_id in item_ids:
            if item_id in done:
                self.state["sync"]["undo"].append(dict(done[item_id]))

    def _queue_stock(
        self, before: list[dict[str, Any]], after: list[dict[str, Any]]
    ) -> None:
        """Ask the sync to move the part counts from *before* to *after*."""
        for (asset_id, part_id), delta in history.stock_moves(before, after).items():
            self.state["sync"]["stock"].append(
                {"asset_id": asset_id, "part_id": part_id, "delta": delta}
            )

    async def sync_done(self, kind: str, entry: dict[str, Any]) -> None:
        """Remove 1 entry that Home Keeper accepted from the sync queue."""
        queue = self.state["sync"][kind]
        if entry in queue:
            queue.remove(entry)
            await self._commit([])

    async def set_completion(
        self, service_id: str, item_id: str, completion: dict[str, str]
    ) -> None:
        """Write the Home Keeper completion of 1 job of a service. No event."""
        service = self.state["services"].get(service_id)
        if service is None:
            return
        service.setdefault("hk_completions", {})[item_id] = dict(completion)
        await self._commit([])

    async def forget_task(self, item_id: str, *, origin: str | None = None) -> None:
        """The user deleted the Home Keeper task of a job: stop the task."""
        item = self.state["items"].get(item_id)
        if item is None:
            return
        changed = ["add_task"] if item["add_task"] else []
        item["hk_task_id"] = None
        item["add_task"] = False
        fired: list[Event] = []
        if changed:
            fired.append(
                (
                    EVENT_ITEM_UPDATED,
                    events.changed_data(events.item_event_data(item, origin), changed),
                )
            )
        await self._commit(fired)

    async def remove_completion(self, task_id: str, ts: str) -> None:
        """A completion was undone in Home Keeper: take its job off the service.

        A service with no job left is deleted.
        """
        for service_id, service in list(self.state["services"].items()):
            for item_id, done in (service.get("hk_completions") or {}).items():
                if done.get("task_id") == task_id and done.get("ts") == ts:
                    items = [i for i in service["items"] if i != item_id]
                    if items:
                        await self.update_service(
                            service_id, {"items": items}, origin=HOME_KEEPER_ORIGIN
                        )
                    else:
                        await self.delete_service(service_id, origin=HOME_KEEPER_ORIGIN)
                    return

    # ── Settings ─────────────────────────────────────────────────────────────

    async def set_settings(
        self, changes: dict[str, Any], *, origin: str | None = None
    ) -> dict[str, Any]:
        """Change the settings. A call that changes no value fires no event."""
        settings = self.state["settings"]
        changed = sorted(k for k, v in changes.items() if settings.get(k) != v)
        if not changed:
            return copy.deepcopy(settings)
        self.state["settings"] = {**settings, **{k: changes[k] for k in changed}}
        await self._commit(
            [(EVENT_SETTINGS_UPDATED, events.settings_event_data(changed, origin))]
        )
        return copy.deepcopy(self.state["settings"])

    # ── The due check ────────────────────────────────────────────────────────

    async def check_due(self, day: str) -> None:
        """Fire ``item_due_soon`` or ``item_overdue`` 1 time for each due point."""
        fired: list[Event] = []
        dirty = False
        for car_id, car in self.state["cars"].items():
            summary = projections.car_summary(self.state, car_id, day)
            for item_id, evaluation in summary["items"].items():
                item = self.state["items"][item_id]
                status = evaluation["status"]
                key = f"{evaluation['distance_limit']}|{evaluation['date_limit']}"
                mark = None if status == OK else {"status": status, "key": key}
                if item.get("notified") == mark:
                    continue
                item["notified"] = mark
                dirty = True
                if status in (SOON, OVERDUE):
                    name = (
                        EVENT_ITEM_OVERDUE if status == OVERDUE else EVENT_ITEM_DUE_SOON
                    )
                    fired.append((name, events.due_event_data(car, item, evaluation)))
        if dirty:
            await self._commit(fired)

    # ── Import ───────────────────────────────────────────────────────────────

    async def import_plan(
        self, plan: dict[str, Any], *, origin: str | None = None
    ) -> None:
        """Write a checked import plan (``import_export.plan_import``)."""
        self.state = import_export.apply_plan(self.state, plan)
        await self._commit(
            [
                (
                    EVENT_DATA_IMPORTED,
                    events.data_imported_event_data(plan["report"]["counts"], origin),
                )
            ]
        )
