"""Build the seed document for the browser tests and the frontend fixture.

Run from the repository root:

    python3 tests/e2e/seed/build_seed.py

The script writes:

* ``tests/e2e/seed/car_keeper.json``: the store document that ``ci/e2e-up.sh``
  copies to ``.storage/car_keeper`` before Home Assistant starts.
* ``custom_components/car_keeper/frontend/test/fixtures/state.json``: the
  ``get_state`` reply for that store. It comes from ``projections.project_state``,
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


def main() -> None:
    state = build()
    projections = _load("projections")
    STORE_OUT.write_text(
        json.dumps(
            {"version": 1, "minor_version": 1, "key": "car_keeper", "data": state},
            indent=2,
        )
        + "\n"
    )
    reply = projections.project_state(state, tab=True, revision=1)
    STATE_OUT.write_text(json.dumps(reply, indent=2) + "\n")
    print(f"wrote {STORE_OUT.relative_to(ROOT)} and {STATE_OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
