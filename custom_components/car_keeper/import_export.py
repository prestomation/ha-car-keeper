"""The Car Keeper section of the Home Keeper export and import.

:func:`export_document` returns ``{format, version, data, skipped}``. ``data`` has
the cars, the items, the service records, the readings and the settings. It leaves
out the fields that only 1 install knows or that the code computes again, and
:data:`NOT_EXPORTED` gives the reason for each.

:func:`plan_import` reads a document and returns the records to write and a
report. It is an upsert: a record matches by its id, then a car by its VIN, then
by its name, and an item by its car and its name. It never deletes a record that
is not in the document. The store writes the plan (``CarStore.import_plan``), so
an import of an export gives the same document.

This module is pure. It imports no Home Assistant code.
"""

from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from . import history
from .const import UNITS

FORMAT = 1

#: The stored fields that the export leaves out, with the reason for each.
NOT_EXPORTED: dict[str, dict[str, str]] = {
    "cars": {
        "hk_asset_id": "The Home Keeper appliance id of 1 install. The sync makes it.",
        "photo": "A file of 1 install. A photo is not in the export.",
    },
    "items": {
        "hk_task_id": "The Home Keeper task id of 1 install. The sync makes it again.",
        "notified": "The last due event that fired. The due check makes it again.",
        "last_done": "Computed again from the service records.",
    },
    "services": {
        "hk_completions": "The Home Keeper completions of 1 install.",
    },
}

#: The fields of each record that the import reads. Each other key is dropped.
FIELDS: dict[str, tuple[str, ...]] = {
    "cars": (
        "id",
        "name",
        "make",
        "model",
        "year",
        "trim",
        "fuel",
        "unit",
        "vin",
        "plate",
        "area_id",
        "notes",
        "lead_distance",
        "lead_days",
        "odometer",
        "created",
    ),
    "items": (
        "id",
        "car_id",
        "name",
        "kind",
        "interval_distance",
        "interval_months",
        "due_date",
        "lead_distance",
        "lead_days",
        "notes",
        "enabled",
        "add_task",
        "template_id",
        "start",
        "parts",
    ),
    "services": (
        "id",
        "car_id",
        "date",
        "reading",
        "items",
        "shop",
        "notes",
        "who",
        "cost",
        "parts_used",
        "logged",
        "origin",
    ),
}
#: The bookkeeping fields that a new record gets, with their start value.
BOOKKEEPING: dict[str, dict[str, Any]] = {
    "cars": {"hk_asset_id": None, "photo": None},
    "items": {"hk_task_id": None, "notified": None, "last_done": None},
    "services": {"hk_completions": {}},
}


def export_document(state: dict[str, Any], version: str) -> dict[str, Any]:
    """The export of the whole document."""
    data: dict[str, Any] = {}
    for section, fields in FIELDS.items():
        data[section] = [
            {key: copy.deepcopy(record.get(key)) for key in fields}
            for record in sorted(state[section].values(), key=lambda r: r["id"])
        ]
    data["readings"] = {
        car_id: copy.deepcopy(rows)
        for car_id, rows in sorted(state["readings"].items())
    }
    data["settings"] = copy.deepcopy(state["settings"])
    return {"format": FORMAT, "version": version, "data": data, "skipped": {}}


def _problem(level: str, path: str, key: str, **params: Any) -> dict[str, Any]:
    return {"level": level, "path": path, "key": key, "params": params}


def _check_car(record: Mapping[str, Any], path: str) -> list[dict[str, Any]]:
    problems = []
    if not isinstance(record.get("id"), str) or not record.get("id"):
        problems.append(
            _problem("error", f"{path}.id", "import_missing_field", field="id")
        )
    if not isinstance(record.get("name"), str) or not record.get("name", "").strip():
        problems.append(
            _problem("error", f"{path}.name", "import_missing_field", field="name")
        )
    if record.get("unit") not in UNITS:
        problems.append(
            _problem("error", f"{path}.unit", "import_bad_value", field="unit")
        )
    if not isinstance(record.get("odometer"), Mapping):
        problems.append(
            _problem(
                "error", f"{path}.odometer", "import_missing_field", field="odometer"
            )
        )
    return problems


def plan_import(
    state: dict[str, Any],
    document: Any,
    *,
    entity_ids: set[str],
) -> dict[str, Any]:
    """The records to write for *document*, and the report.

    The reply is ``{report, writes}``. ``report`` has ``ok``, ``counts`` (created,
    updated and unchanged for each section) and ``problems``. ``writes`` maps each
    section to the records to put in it. With an ``error`` problem, ``writes`` is
    empty. An odometer that names an entity that this install does not have becomes
    a typed odometer, with a ``warning``.
    """
    problems: list[dict[str, Any]] = []
    writes: dict[str, dict[str, Any]] = {"cars": {}, "items": {}, "services": {}}
    readings: dict[str, list[dict[str, Any]]] = {}
    counts = {
        name: {"created": 0, "updated": 0, "unchanged": 0}
        for name in ("cars", "items", "services", "readings")
    }
    report = {"ok": False, "counts": counts, "problems": problems}
    if not isinstance(document, Mapping) or not isinstance(
        document.get("data"), Mapping
    ):
        problems.append(_problem("error", "", "import_not_a_document"))
        return {"report": report, "writes": {}, "readings": {}, "settings": None}
    if not isinstance(document.get("format"), int) or document["format"] > FORMAT:
        problems.append(
            _problem(
                "error",
                "format",
                "import_format_too_new",
                format=document.get("format"),
            )
        )
        return {"report": report, "writes": {}, "readings": {}, "settings": None}
    data = document["data"]

    # Cars: by id, then by VIN, then by name.
    car_ids: dict[str, str] = {}
    by_vin = {c["vin"]: c["id"] for c in state["cars"].values() if c.get("vin")}
    by_name = {c["name"].casefold(): c["id"] for c in state["cars"].values()}
    for index, raw in enumerate(data.get("cars") or []):
        path = f"cars[{index}]"
        if not isinstance(raw, Mapping):
            problems.append(_problem("error", path, "import_not_a_record"))
            continue
        found = _check_car(raw, path)
        problems += found
        if found:
            continue
        record: dict[str, Any] = {k: copy.deepcopy(raw.get(k)) for k in FIELDS["cars"]}
        target = (
            record["id"]
            if record["id"] in state["cars"]
            else by_vin.get(record.get("vin") or "")
            or by_name.get(record["name"].casefold())
        )
        car_ids[record["id"]] = target or record["id"]
        record["id"] = car_ids[record["id"]]
        odometer = dict(record["odometer"])
        if (
            odometer.get("source") == "entity"
            and odometer.get("entity_id") not in entity_ids
        ):
            problems.append(
                _problem(
                    "warning",
                    f"{path}.odometer.entity_id",
                    "import_entity_missing",
                    entity_id=odometer.get("entity_id"),
                )
            )
            odometer = {**odometer, "source": "manual", "entity_id": None}
        record["odometer"] = odometer
        _put(state, writes, counts, "cars", record)

    known_cars = set(state["cars"]) | set(writes["cars"])
    item_ids: dict[str, str] = {}
    by_car_name = {
        (i["car_id"], i["name"].casefold()): i["id"] for i in state["items"].values()
    }
    for index, raw in enumerate(data.get("items") or []):
        path = f"items[{index}]"
        if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str):
            problems.append(_problem("error", path, "import_not_a_record"))
            continue
        record = {k: copy.deepcopy(raw.get(k)) for k in FIELDS["items"]}
        record["car_id"] = car_ids.get(str(record["car_id"]), record["car_id"])
        if record["car_id"] not in known_cars:
            problems.append(_problem("error", f"{path}.car_id", "import_unknown_car"))
            continue
        name = str(record.get("name") or "")
        target = (
            record["id"]
            if record["id"] in state["items"]
            else by_car_name.get((record["car_id"], name.casefold()))
        )
        item_ids[record["id"]] = target or record["id"]
        record["id"] = item_ids[record["id"]]
        _put(state, writes, counts, "items", record)

    known_items = set(state["items"]) | set(writes["items"])
    for index, raw in enumerate(data.get("services") or []):
        path = f"services[{index}]"
        if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str):
            problems.append(_problem("error", path, "import_not_a_record"))
            continue
        record = {k: copy.deepcopy(raw.get(k)) for k in FIELDS["services"]}
        record["car_id"] = car_ids.get(str(record["car_id"]), record["car_id"])
        if record["car_id"] not in known_cars:
            problems.append(_problem("error", f"{path}.car_id", "import_unknown_car"))
            continue
        record["items"] = [
            item_ids.get(str(i), str(i)) for i in record.get("items") or []
        ]
        missing = [i for i in record["items"] if i not in known_items]
        if missing:
            problems.append(_problem("error", f"{path}.items", "import_unknown_item"))
            continue
        _put(state, writes, counts, "services", record)

    for car_id, rows in (data.get("readings") or {}).items():
        target = car_ids.get(str(car_id), str(car_id))
        if target not in known_cars or not isinstance(rows, list):
            problems.append(
                _problem("error", f"readings.{car_id}", "import_unknown_car")
            )
            continue
        stored = state["readings"].get(target) or []
        have = {(r["ts"], r["value"], r["source"]) for r in stored}
        new = [
            dict(r)
            for r in rows
            if isinstance(r, Mapping)
            and (r.get("ts"), r.get("value"), r.get("source")) not in have
        ]
        if new or target not in state["readings"]:
            merged = sorted([*stored, *new], key=lambda r: str(r["ts"]))
            readings[target] = merged
            counts["readings"]["created"] += len(new)
        counts["readings"]["unchanged"] += len(rows) - len(new)

    settings = (
        data.get("settings") if isinstance(data.get("settings"), Mapping) else None
    )
    if any(p["level"] == "error" for p in problems):
        return {"report": report, "writes": {}, "readings": {}, "settings": None}
    report["ok"] = True
    return {
        "report": report,
        "writes": writes,
        "readings": readings,
        "settings": dict(settings) if settings is not None else None,
    }


def _put(
    state: dict[str, Any],
    writes: dict[str, dict[str, Any]],
    counts: dict[str, dict[str, int]],
    section: str,
    record: dict[str, Any],
) -> None:
    old = state[section].get(record["id"])
    if old is None:
        writes[section][record["id"]] = {
            **copy.deepcopy(BOOKKEEPING[section]),
            **record,
        }
        counts[section]["created"] += 1
        return
    merged = {**old, **record}
    if merged == old:
        counts[section]["unchanged"] += 1
        return
    writes[section][record["id"]] = merged
    counts[section]["updated"] += 1


def apply_plan(state: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    """The document with *plan* written. ``last_done`` follows from the history."""
    out = copy.deepcopy(state)
    for section, records in plan["writes"].items():
        out[section].update(copy.deepcopy(records))
    out["readings"].update(copy.deepcopy(plan["readings"]))
    if plan.get("settings"):
        out["settings"] = {**out["settings"], **plan["settings"]}
    out["items"].update(
        history.refresh(out["items"], out["services"], list(out["items"]))
    )
    return out
