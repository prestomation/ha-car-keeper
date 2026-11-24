"""Docker integration: the sync with the real Home Keeper, both ways.

A car becomes a managed appliance and a job becomes a managed task. A service in
Car Keeper completes the task, a delete undoes it, and a completion in Home Keeper
logs a service in Car Keeper. The test cleans up after itself, so the other tests
of this tier see no extra records.
"""

from __future__ import annotations

import time
from typing import Any

CK = "car_keeper"
HK = "home_keeper"


def _call(api, domain: str, service: str, data: dict | None = None) -> Any:
    """Call a service. A reply that Home Keeper is reloading is tried again."""
    deadline = time.monotonic() + 30
    while True:
        resp = api.post(
            f"/api/services/{domain}/{service}?return_response", json=data or {}
        )
        if resp.status_code == 400 and "return_response" in resp.text:
            resp = api.post(f"/api/services/{domain}/{service}", json=data or {})
        if "isn't loaded" not in resp.text or time.monotonic() > deadline:
            break
        time.sleep(0.5)
    assert resp.status_code == 200, (service, resp.status_code, resp.text)
    body = resp.json()
    return body.get("service_response") if isinstance(body, dict) else body


def _wait(check, timeout: float = 15) -> Any:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        last = check()
        if last:
            return last
        time.sleep(0.5)
    raise AssertionError(f"timed out, last value: {last!r}")


def _home_keeper_loaded(api) -> bool:
    """Home Keeper reloads its entry after some task changes. Wait for the end."""
    entries = api.get("/api/config/config_entries/entry").json()
    return any(e["domain"] == HK and e["state"] == "loaded" for e in entries)


def _ours(api, kind: str, car_id: str) -> list[dict]:
    rows = _call(api, HK, f"list_{kind}")[kind]
    if kind == "assets":
        return [a for a in rows if (a.get("managed_by") or {}).get("car_id") == car_id]
    return [
        t
        for t in rows
        if ((t.get("source") or {}).get(CK) or {}).get("car_id") == car_id
    ]


def test_the_sync_with_the_real_home_keeper(api):
    _wait(lambda: _home_keeper_loaded(api), timeout=60)
    car = _call(
        api, CK, "add_car", {"name": "Sync car", "odometer": 30000, "vin": "SYNCVIN"}
    )["car"]
    car_id = car["id"]
    try:
        job = _call(
            api,
            CK,
            "add_item",
            {
                "car_id": car_id,
                "name": "Sync oil",
                "interval_distance": 10000,
                "interval_months": 12,
            },
        )["item"]
        _call(
            api,
            CK,
            "add_item",
            {"car_id": car_id, "name": "Sync wipers", "interval_months": 12},
        )
        _call(
            api,
            CK,
            "add_item",
            {
                "car_id": car_id,
                "name": "Sync plates",
                "kind": "date",
                "due_date": "2099-03-01",
            },
        )
        (asset,) = _wait(lambda: _ours(api, "assets", car_id))
        assert asset["name"] == "Sync car" and "SYNCVIN" not in str(asset)
        tasks = _wait(
            lambda: (rows := _ours(api, "tasks", car_id)) and len(rows) == 3 and rows
        )
        by_name = {t["name"]: t for t in tasks}
        oil = by_name["Sync oil"]
        assert oil["recurrence_type"] == "sensor"
        assert oil["sensor"]["mode"] == "usage"
        assert oil["sensor"]["target"] == 10000
        assert oil["sensor"]["baseline"] == 30000
        assert oil["sensor"]["also_every"]["unit"] == "months"
        assert by_name["Sync wipers"]["recurrence_type"] == "floating"
        assert by_name["Sync plates"]["recurrence_type"] == "one-off"
        assert oil["managed_by"]["integration"] == CK

        service = _call(
            api,
            CK,
            "log_service",
            {"car_id": car_id, "items": [job["id"]], "reading": 31000, "cost": 20},
        )["service"]

        def _completions() -> list[dict]:
            task = next(t for t in _ours(api, "tasks", car_id) if t["id"] == oil["id"])
            return task.get("completions") or []

        (done,) = _wait(_completions)
        assert done.get("reading") == 31000 and done.get("cost") == 20
        _wait(
            lambda: _call(api, CK, "get_car", {"car_id": car_id})["services"][0][
                "hk_completions"
            ]
        )
        _call(api, CK, "delete_service", {"service_id": service["id"]})
        _wait(lambda: _completions() == [])

        _call(
            api,
            HK,
            "complete_task",
            {"task_id": oil["id"], "reading": 32000, "cost": 15},
        )
        logged = _wait(
            lambda: _call(api, CK, "get_car", {"car_id": car_id})["services"]
        )
        assert logged[0]["origin"] == "home_keeper"
        assert logged[0]["reading"] == 32000 and logged[0]["items"] == [job["id"]]
        time.sleep(2)
        assert len(_completions()) == 1
    finally:
        _call(api, CK, "delete_car", {"car_id": car_id})
    _wait(lambda: _ours(api, "tasks", car_id) == [])
    released = _wait(
        lambda: [
            a
            for a in _call(api, HK, "list_assets")["assets"]
            if a["id"] == asset["id"] and a.get("managed_by") is None
        ]
    )
    _call(api, HK, "delete_asset", {"asset_id": released[0]["id"]})
    _wait(lambda: _home_keeper_loaded(api), timeout=60)
