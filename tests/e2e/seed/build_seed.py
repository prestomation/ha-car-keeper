"""Build the seed document for the browser tests and the frontend fixture.

Run from the repository root:

    python3 tests/e2e/seed/build_seed.py

The script writes:

* ``tests/e2e/seed/car_keeper.json``: the store document that ``ci/e2e-up.sh``
  copies to ``.storage/car_keeper`` before Home Assistant starts: the sample
  garage, with 2 cars.
* ``custom_components/car_keeper/frontend/test/fixtures/state.json``: the
  ``get_state`` reply of an empty store, and ``garage.json``, the reply of the
  sample garage. It comes from ``projections.project_state``,
  the same code as the websocket command.

Every record comes from the pure ``models`` code, so the seed has the shape that
the store writes.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SEED_DIR = Path(__file__).resolve().parent
COMPONENT = ROOT / "custom_components" / "car_keeper"
STORE_OUT = SEED_DIR / "car_keeper.json"
STATE_OUT = COMPONENT / "frontend" / "test" / "fixtures" / "state.json"
GARAGE_OUT = COMPONENT / "frontend" / "test" / "fixtures" / "garage.json"
TODAY = "2026-10-15"
PKG = "custom_components.car_keeper"


def _load(name: str) -> Any:
    """Load a pure module of the component without Home Assistant."""
    parents = (("custom_components", ROOT / "custom_components"), (PKG, COMPONENT))
    for pkg, path in parents:
        if pkg not in sys.modules:
            module = types.ModuleType(pkg)
            module.__path__ = [str(path)]  # type: ignore[attr-defined]
            sys.modules[pkg] = module
    full = f"{PKG}.{name}"
    if full in sys.modules:
        return sys.modules[full]
    spec = importlib.util.spec_from_file_location(full, COMPONENT / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[full] = module
    spec.loader.exec_module(module)
    return module


def build() -> dict[str, Any]:
    """The seed document."""
    _load("const")
    models = _load("models")
    return models.empty_state()


def garage() -> dict[str, Any]:
    """A document with 2 cars, their jobs and their services, for the DOM tests."""
    models = _load("models")
    templates = _load("templates")
    history = _load("history")
    state = models.empty_state()
    cars = [
        (
            "civic",
            {
                "name": "Civic",
                "make": "Honda",
                "model": "Civic",
                "year": 2018,
                "fuel": "petrol",
                "vin": "1HGFC2F59JA000000",
                "plate": "CK 101",
                "odometer": 41800,
            },
            ["engine_oil", "tyre_rotation", "registration"],
        ),
        (
            "model3",
            {
                "name": "Model 3",
                "make": "Tesla",
                "model": "Model 3",
                "year": 2021,
                "fuel": "electric",
                "unit": "mi",
                "odometer": 18250,
            },
            ["tyre_rotation", "cabin_filter"],
        ),
    ]
    for car_id, data, jobs in cars:
        car = models.build_car(data, car_id=car_id, today=TODAY, default_unit="km")
        state["cars"][car_id] = car
        rows = templates.items_for(
            jobs,
            unit=car["unit"],
            overrides={},
            names={j: j.replace("_", " ").capitalize() for j in jobs},
            due_dates={"registration": "2026-11-01"},
            today=TODAY,
        )
        for n, row in enumerate(rows):
            item_id = f"{car_id}-{row['template_id']}"
            data_item = {
                **row["data"],
                "last_date": "2025-11-01",
                "last_reading": car["odometer"]["value"] - 9000 + n * 2000,
            }
            item = models.build_item(
                data_item,
                item_id=item_id,
                car=car,
                today=TODAY,
                template_id=row["template_id"],
            )
            state["items"][item_id] = item
    service = models.build_service(
        {
            "items": ["civic-engine_oil"],
            "date": "2026-04-02",
            "reading": 35000,
            "cost": 84.5,
            "shop": "Main Street Garage",
        },
        service_id="s1",
        car=state["cars"]["civic"],
        items=state["items"],
        today=TODAY,
        now="2026-04-02T10:00:00+00:00",
        origin=None,
    )
    state["services"]["s1"] = service
    state["items"].update(
        history.refresh(state["items"], state["services"], list(state["items"]))
    )
    return state


def main() -> None:
    state = build()
    projections = _load("projections")
    # The browser tests start from the sample garage, so each view has data.
    STORE_OUT.write_text(
        json.dumps(
            {"version": 1, "minor_version": 1, "key": "car_keeper", "data": garage()},
            indent=2,
        )
        + "\n"
    )
    reply = projections.project_state(state, today="2026-10-15", tab=True, revision=1)
    STATE_OUT.write_text(json.dumps(reply, indent=2) + "\n")
    sample = projections.project_state(garage(), today=TODAY, tab=True, revision=1)
    GARAGE_OUT.write_text(json.dumps(sample, indent=2) + "\n")
    print(f"wrote {STORE_OUT.relative_to(ROOT)} and {STATE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
