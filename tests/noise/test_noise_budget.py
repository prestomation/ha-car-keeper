"""Noise budget: how much each action writes to the logbook, the recorder and the store.

Each test is 1 named scenario. It does 1 action on the shared Home Assistant and checks
the counts against ``baseline.json``: logbook rows, flips to and from unavailable,
``car_keeper_*`` events, store writes and entry reloads. Some scenarios are pinned at
0. A loop that writes on each restart or each tick fills the logbook of a user, and no
other test sees it.

The scenarios run in file order and share state. Run the file whole, with
``bash ci/test-noise.sh``.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from conftest import Baseline, HomeAssistantClient, check, measure

CK = "car_keeper"


def _run(
    ha: HomeAssistantClient, baseline: Baseline, name: str, action: Any, **kw: Any
) -> Any:
    measured, result = measure(ha, action, **kw)
    check(baseline, name, measured)
    return result


# --- Startup and quiet time ----------------------------------------------------------


def test_cold_start(ha: HomeAssistantClient, baseline: Baseline) -> None:
    # Counts since the probe set up, which is before Car Keeper. Must run first.
    boot = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=10)
    _run(ha, baseline, "cold_start", None, reset=False, since=boot)


def test_idle(ha: HomeAssistantClient, baseline: Baseline) -> None:
    _run(ha, baseline, "idle", lambda: None)


# --- Settings ------------------------------------------------------------------------


def test_noop_set_settings(ha: HomeAssistantClient, baseline: Baseline) -> None:
    _run(ha, baseline, "noop_set_settings", lambda: ha.call(CK, "set_settings", {}))


def test_set_settings_unit(ha: HomeAssistantClient, baseline: Baseline) -> None:
    def action() -> None:
        ha.call(CK, "set_settings", {"unit": "mi"})
        ha.call(CK, "set_settings", {"unit": "km"})

    _run(ha, baseline, "set_settings_unit", action)


# --- Cars, odometer and service records -----------------------------------------------


def test_add_car(
    ha: HomeAssistantClient, baseline: Baseline, shared: dict[str, Any]
) -> None:
    def action() -> Any:
        return ha.call(
            CK,
            "add_car",
            {"name": "Noise car", "odometer": 10000, "starter_jobs": ["engine_oil"]},
        )

    shared["car"] = _run(ha, baseline, "add_car", action)["car"]


def test_idle_with_a_car(ha: HomeAssistantClient, baseline: Baseline) -> None:
    _run(ha, baseline, "idle_with_a_car", lambda: None)


def test_noop_update_car(
    ha: HomeAssistantClient, baseline: Baseline, shared: dict[str, Any]
) -> None:
    car = shared["car"]

    def action() -> None:
        ha.call(CK, "update_car", {"car_id": car["id"], "name": car["name"]})

    _run(ha, baseline, "noop_update_car", action)


def test_set_odometer(
    ha: HomeAssistantClient, baseline: Baseline, shared: dict[str, Any]
) -> None:
    def action() -> None:
        ha.call(CK, "set_odometer", {"car_id": shared["car"]["id"], "value": 10500})

    _run(ha, baseline, "set_odometer", action)


def test_log_service(
    ha: HomeAssistantClient, baseline: Baseline, shared: dict[str, Any]
) -> None:
    car_id = shared["car"]["id"]
    items = ha.call(CK, "list_items", {"car_id": car_id})["items"]

    def action() -> None:
        ha.call(
            CK,
            "log_service",
            {"car_id": car_id, "items": [i["id"] for i in items], "reading": 10600},
        )

    _run(ha, baseline, "log_service", action)


def test_reads_are_silent(
    ha: HomeAssistantClient, baseline: Baseline, shared: dict[str, Any]
) -> None:
    car_id = shared["car"]["id"]

    def action() -> None:
        ha.call(CK, "list_cars")
        ha.call(CK, "get_car", {"car_id": car_id})
        ha.call(CK, "list_items", {"car_id": car_id})
        ha.call(CK, "list_services", {"car_id": car_id})
        ha.ws({"type": "car_keeper/get_state"})

    _run(ha, baseline, "reads_are_silent", action)


def test_delete_car(
    ha: HomeAssistantClient, baseline: Baseline, shared: dict[str, Any]
) -> None:
    def action() -> None:
        ha.call(CK, "delete_car", {"car_id": shared["car"]["id"]})

    _run(ha, baseline, "delete_car", action)
