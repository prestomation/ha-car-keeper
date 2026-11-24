"""The plan that keeps Home Keeper the same as Car Keeper.

Car Keeper owns the cars, the jobs and the service history. Home Keeper owns the
reminders. Each car is 1 managed Home Keeper appliance, and each job with
``add_task`` is 1 managed Home Keeper task. :func:`plan_assets` and
:func:`plan_tasks` compare the Car Keeper document with the replies of
``list_assets`` and ``list_tasks``, and return the steps that make Home Keeper the
same. The sync (``hk_sync.py``) runs the steps, then plans again, until a plan is
empty.

A Home Keeper record is Car Keeper's when its ``managed_by`` names Car Keeper. The
link to the record of Car Keeper is ``managed_by.car_id`` for an appliance, and
``source.car_keeper.item_id`` for a task.

This module is pure. It imports no Home Assistant code. The caller gives the entity
id of each odometer sensor, the device id of each car and the time zone offset.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from typing import Any

from .const import DOMAIN

INTEGRATION = DOMAIN

#: The task fields that the user cannot change in Home Keeper. Home Keeper drops a
#: locked field from each update, also from the owner. So only the device is locked:
#: it never changes for a car. A pass writes each other field of the job again.
TASK_LOCKED_FIELDS = ("device_id",)
#: The appliance fields that only Car Keeper changes. Home Keeper takes an owner's
#: change of a locked field only for the name, so the make, the model and the area
#: stay open, and a pass writes the value of the car again.
ASSET_LOCKED_FIELDS = ("name",)
#: The Home Keeper recurrence types that Car Keeper makes.
SENSOR = "sensor"
FLOATING = "floating"
ONE_OFF = "one-off"
#: The key of the part links in the ``source`` of a Home Keeper task.
SOURCE_PARTS = "parts"
#: The fields of a task that the plan compares. Home Keeper adds more.
_TASK_COMPARED = ("name", "recurrence_type", "interval", "unit", "device_id")


def managed_by(entry_id: str, **extra: Any) -> dict[str, Any]:
    """The ownership block of a Car Keeper record in Home Keeper."""
    return {
        "integration": INTEGRATION,
        "config_entry_id": entry_id,
        "deletion_protected": True,
        **extra,
    }


def _is_ours(record: Mapping[str, Any]) -> bool:
    owner = record.get("managed_by")
    return isinstance(owner, Mapping) and owner.get("integration") == INTEGRATION


# ── Appliances ───────────────────────────────────────────────────────────────


def desired_asset(car: Mapping[str, Any], device_id: str | None) -> dict[str, Any]:
    """The appliance fields of *car*. The VIN and the plate never go to Home Keeper.

    ``list_assets`` is open to each user of Home Keeper, and the appliance is
    there for the reminders. The VIN and the plate stay in Car Keeper. Home Keeper
    takes no empty area or device, so a car with none leaves the field out.
    """
    fields: dict[str, Any] = {
        "name": car["name"],
        "manufacturer": car.get("make") or "",
        "model": car.get("model") or "",
    }
    if car.get("area_id"):
        fields["area_id"] = car["area_id"]
    if device_id:
        fields["device_id"] = device_id
    return fields


def plan_assets(
    cars: Mapping[str, Mapping[str, Any]],
    assets: list[Mapping[str, Any]],
    *,
    device_ids: Mapping[str, str | None],
    entry_id: str,
) -> dict[str, list[dict[str, Any]]]:
    """The steps that give each car 1 appliance.

    - ``adds``: a car with a device and no appliance.
    - ``binds``: an appliance of a car that the car does not know yet.
    - ``updates``: an appliance with a field that is not the field of its car.
    - ``releases``: an appliance of a car that is gone. Its ownership is removed, so
      the user keeps the appliance and the stock of its parts.
    """
    plan: dict[str, list[dict[str, Any]]] = {
        "adds": [],
        "binds": [],
        "updates": [],
        "releases": [],
    }
    by_car: dict[str, Mapping[str, Any]] = {}
    for asset in assets:
        if not _is_ours(asset):
            continue
        car_id = asset["managed_by"].get("car_id")
        if car_id in cars and car_id not in by_car:
            by_car[car_id] = asset
        else:
            plan["releases"].append({"asset_id": asset["id"]})
    for car_id in sorted(cars):
        car = cars[car_id]
        device_id = device_ids.get(car_id)
        want = desired_asset(car, device_id)
        found = by_car.get(car_id)
        if found is None:
            # Home Keeper fixes the device of an appliance when it adds it. The
            # appliance waits for the device of the car.
            if device_id is None:
                continue
            plan["adds"].append(
                {
                    "car_id": car_id,
                    "fields": {
                        **want,
                        "managed_by": managed_by(
                            entry_id,
                            car_id=car_id,
                            locked_fields=list(ASSET_LOCKED_FIELDS),
                        ),
                    },
                }
            )
            continue
        if car.get("hk_asset_id") != found["id"]:
            plan["binds"].append({"car_id": car_id, "asset_id": found["id"]})
        changed = {
            k: v for k, v in want.items() if k != "device_id" and found.get(k) != v
        }
        if changed:
            plan["updates"].append({"asset_id": found["id"], "fields": changed})
    return plan


# ── Tasks ────────────────────────────────────────────────────────────────────


def base(item: Mapping[str, Any]) -> dict[str, Any]:
    """The date and the reading that the next limit of *item* counts from."""
    done = item.get("last_done") or {}
    start = item.get("start") or {}
    return {
        "date": done.get("date") or start.get("date"),
        "reading": done.get("reading") if done.get("date") else start.get("reading"),
    }


def desired_task(
    item: Mapping[str, Any],
    car: Mapping[str, Any],
    *,
    entity_id: str | None,
    device_id: str | None,
    date_limit: str | None,
) -> dict[str, Any] | None:
    """The task fields of *item*, or None when the item has no task.

    - A job with a distance interval is a usage task on the odometer sensor of
      the car. A time interval is the ``also_every`` backstop of the same task.
    - A job with only a time interval is a floating task.
    - A date job is a one-off task, due at *date_limit*.

    A job with a distance interval and no odometer sensor gets no task until the
    sensor is there.
    """
    if not item.get("add_task") or not item.get("enabled", True):
        return None
    fields: dict[str, Any] = {"name": item["name"], "device_id": device_id}
    months = item.get("interval_months")
    if item.get("kind") == "date":
        if date_limit is None:
            return None
        return {**fields, "recurrence_type": ONE_OFF, "due": date_limit}
    if item.get("interval_distance"):
        if entity_id is None:
            return None
        sensor: dict[str, Any] = {
            "entity_id": entity_id,
            "mode": "usage",
            "target": float(item["interval_distance"]),
            "unit": car.get("unit"),
        }
        if months:
            sensor["also_every"] = {"interval": int(months), "unit": "months"}
            sensor["combinator"] = "any"
        return {**fields, "recurrence_type": SENSOR, "sensor": sensor}
    return {
        **fields,
        "recurrence_type": FLOATING,
        "interval": int(months or 1),
        "unit": "months",
    }


def _sensor_differs(have: Any, want: Mapping[str, Any]) -> bool:
    if not isinstance(have, Mapping):
        return True
    keys = ("entity_id", "mode", "target", "unit", "also_every", "combinator")
    return any(have.get(k) != want.get(k) for k in keys)


def _task_changes(task: Mapping[str, Any], want: Mapping[str, Any]) -> dict[str, Any]:
    changed = {
        k: want[k] for k in _TASK_COMPARED if k in want and task.get(k) != want[k]
    }
    # Home Keeper keeps ``due`` as a time. Car Keeper gives a date.
    if "due" in want and str(task.get("due") or "")[:10] != want["due"]:
        changed["due"] = want["due"]
    if "sensor" in want and _sensor_differs(task.get("sensor"), want["sensor"]):
        changed["sensor"] = want["sensor"]
    if task.get("recurrence_type") != want["recurrence_type"]:
        changed["recurrence_type"] = want["recurrence_type"]
    return changed


def completed_at(service: Mapping[str, Any], offset: str) -> str:
    """The time of the Home Keeper completion of *service*, as ISO text.

    The time of logging when it is on the date of the service, else noon of that
    date. *offset* is the UTC offset of Home Assistant, such as ``+02:00``.
    """
    logged = str(service.get("logged") or "")
    if logged[:10] == service["date"]:
        when = dt.datetime.fromisoformat(logged)
    else:
        when = dt.datetime.fromisoformat(f"{service['date']}T12:00:00{offset}")
    return when.isoformat()


def plan_tasks(
    state: Mapping[str, Any],
    tasks: list[Mapping[str, Any]],
    *,
    entity_ids: Mapping[str, str | None],
    device_ids: Mapping[str, str | None],
    date_limits: Mapping[str, str | None],
    entry_id: str,
    offset: str,
) -> dict[str, list[dict[str, Any]]]:
    """The steps that give each job 1 task with its history.

    - ``adds``: a job with ``add_task`` and no task.
    - ``binds``: a task of a job that the job does not know yet.
    - ``forgets``: a job whose task the user deleted in Home Keeper.
    - ``updates``: a task with a field that is not the field of its job.
    - ``meters``: a usage task with a baseline that is not the reading of the base.
    - ``consumables``: a task whose parts are not the parts of its job.
    - ``completes``: a job of a service with no Home Keeper completion yet. The
      cost goes on the first job of the service that has a task, so the spend total
      of Home Keeper counts it 1 time.
    - ``records``: a completion that Home Keeper has and the service does not hold.
    - ``deletes``: a Car Keeper task with no job, or of a job with no task now.
    """
    items = state["items"]
    cars = state["cars"]
    plan: dict[str, list[dict[str, Any]]] = {
        key: []
        for key in (
            "adds",
            "binds",
            "forgets",
            "updates",
            "meters",
            "consumables",
            "completes",
            "records",
            "deletes",
        )
    }
    by_item: dict[str, Mapping[str, Any]] = {}
    for task in tasks:
        if not _is_ours(task):
            continue
        source_id = ((task.get("source") or {}).get(DOMAIN) or {}).get("item_id")
        if (
            isinstance(source_id, str)
            and source_id in items
            and source_id not in by_item
        ):
            by_item[source_id] = task
            continue
        plan["deletes"].append({"task_id": task["id"]})
    live: dict[str, Mapping[str, Any]] = {}
    for item_id in sorted(items):
        item = items[item_id]
        car = cars.get(item["car_id"])
        if car is None:
            continue
        linked = by_item.get(item_id)
        want = desired_task(
            item,
            car,
            entity_id=entity_ids.get(item["car_id"]),
            device_id=device_ids.get(item["car_id"]),
            date_limit=date_limits.get(item_id),
        )
        if want is None:
            if linked is not None:
                plan["deletes"].append({"task_id": linked["id"]})
            continue
        if linked is None:
            if item.get("hk_task_id"):
                plan["forgets"].append({"item_id": item_id})
                continue
            point = base(item)
            add = {
                **want,
                "source": {
                    DOMAIN: {
                        "car_id": item["car_id"],
                        "item_id": item_id,
                        "device_id": want["device_id"],
                    }
                },
                "managed_by": managed_by(
                    entry_id, locked_fields=list(TASK_LOCKED_FIELDS)
                ),
            }
            if want["recurrence_type"] == SENSOR and point["reading"] is not None:
                add["sensor"] = {**want["sensor"], "baseline": point["reading"]}
            if want["recurrence_type"] == FLOATING and point["date"]:
                add["last_completed"] = f"{point['date']}T12:00:00{offset}"
            plan["adds"].append({"item_id": item_id, "fields": add})
            continue
        live[item_id] = linked
        if item.get("hk_task_id") != linked["id"]:
            plan["binds"].append({"item_id": item_id, "task_id": linked["id"]})
        changed = _task_changes(linked, want)
        if changed:
            plan["updates"].append({"task_id": linked["id"], "fields": changed})
        reading = base(item)["reading"]
        sensor = linked.get("sensor") or {}
        if (
            want["recurrence_type"] == SENSOR
            and "sensor" not in changed
            and reading is not None
            and sensor.get("baseline") != reading
        ):
            plan["meters"].append({"task_id": linked["id"], "baseline": reading})
        parts = item.get("parts") or []
        if _links(linked) != _key(parts):
            plan["consumables"].append({"task_id": linked["id"], "parts": list(parts)})
    # The completion times that the services hold, by task, as instants. Each
    # completion of a task gets its own time, so 2 services of 1 job on 1 day never
    # share a completion.
    held: dict[str, dict[str, tuple[str, str]]] = {}
    for service_id, service in state["services"].items():
        for item_id, done in (service.get("hk_completions") or {}).items():
            if isinstance(done, Mapping) and done.get("task_id"):
                held.setdefault(str(done["task_id"]), {})[instant(done.get("ts"))] = (
                    service_id,
                    item_id,
                )
    for service_id, service in sorted(
        state["services"].items(), key=lambda kv: (kv[1]["date"], kv[0])
    ):
        done = service.get("hk_completions") or {}
        first = True
        for item_id in service["items"]:
            target = live.get(item_id)
            if target is None:
                continue
            fields: dict[str, Any] = {"task_id": target["id"]}
            if first and service.get("cost") is not None:
                fields["cost"] = service["cost"]
            first = False
            if (done.get(item_id) or {}).get("task_id") == target["id"]:
                continue
            taken = held.setdefault(target["id"], {})
            in_home_keeper = _completion_times(target)
            start_at = dt.datetime.fromisoformat(completed_at(service, offset))
            lost = _lost_completion(start_at, in_home_keeper, taken)
            if lost is not None:
                # Home Keeper has a completion of this job that no service holds:
                # the store write after the call did not happen. Write it now with
                # the time of Home Keeper, and do not complete the task again.
                taken[instant(lost)] = (service_id, item_id)
                plan["records"].append(
                    {
                        "service_id": service_id,
                        "item_id": item_id,
                        "completion": {"task_id": target["id"], "ts": lost},
                    }
                )
                continue
            when = start_at
            while (
                instant(when.isoformat()) in taken
                or instant(when.isoformat()) in in_home_keeper
            ):
                when += dt.timedelta(seconds=1)
            fields["completed_at"] = when.isoformat()
            taken[instant(fields["completed_at"])] = (service_id, item_id)
            if target.get("recurrence_type") == SENSOR and service.get("reading"):
                fields["reading"] = service["reading"]
            if str(service.get("who") or "").startswith("person."):
                fields["who"] = service["who"]
            if service.get("notes"):
                fields["note"] = service["notes"]
            plan["completes"].append(
                {"service_id": service_id, "item_id": item_id, "fields": fields}
            )
    return plan


def instant(value: Any) -> str:
    """A completion time as a UTC instant, so 2 spellings of 1 time are equal.

    A text that is not an ISO time with a zone stays as it is.
    """
    try:
        when = dt.datetime.fromisoformat(str(value))
    except ValueError:
        return str(value)
    if when.tzinfo is None:
        return str(value)
    return when.astimezone(dt.UTC).isoformat()


#: A completion that Home Keeper has counts as the lost one of a service when its
#: time is at most this far after the time of the service.
LOST_WINDOW = dt.timedelta(minutes=1)


def _lost_completion(
    base: dt.datetime, in_home_keeper: Mapping[str, str], taken: Mapping[str, Any]
) -> str | None:
    """The ``ts`` of a completion of Home Keeper that no service holds, from *base*.

    The plan gives each completion of a task its own time, at or after the time of
    its service. So a completion that no service holds, in the window after the
    time of a service with no completion, is the one that service lost.
    """
    start = base.astimezone(dt.UTC)
    for key in sorted(in_home_keeper):
        if key in taken:
            continue
        try:
            when = dt.datetime.fromisoformat(key)
        except ValueError:
            continue
        if when.tzinfo is not None and start <= when <= start + LOST_WINDOW:
            return in_home_keeper[key]
    return None


def _completion_times(task: Mapping[str, Any]) -> dict[str, str]:
    """The completions of a Home Keeper task: each instant, with its own ``ts``."""
    return {
        instant(c.get("ts")): str(c.get("ts"))
        for c in task.get("completions") or []
        if isinstance(c, Mapping)
    }


def _key(parts: list[Mapping[str, Any]]) -> list[tuple[str, str, float]]:
    return sorted(
        (str(p["asset_id"]), str(p["part_id"]), float(p.get("quantity") or 1))
        for p in parts
    )


def _links(task: Mapping[str, Any]) -> list[tuple[str, str, float]]:
    """The part links of a Home Keeper task: ``source.parts``.

    A link with no quantity takes the per-use amount of its part. Car Keeper always
    sends a quantity, so a missing one counts as 1.
    """
    links = (task.get("source") or {}).get(SOURCE_PARTS) or []
    return _key([p for p in links if isinstance(p, Mapping)])


def service_from_completion(
    data: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    """The ``log_service`` data of a Home Keeper completion of the task of *item*."""
    when = str(data.get("completed_at") or "")
    out: dict[str, Any] = {"items": [item["id"]], "date": when[:10] or None}
    if isinstance(data.get("reading"), int | float):
        out["reading"] = data["reading"]
    if isinstance(data.get("cost"), int | float):
        out["cost"] = data["cost"]
    if data.get("note"):
        out["notes"] = str(data["note"])
    if data.get("who"):
        out["who"] = str(data["who"])
    return out
