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
