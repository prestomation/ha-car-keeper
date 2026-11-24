"""The golden corpus of the rules that Python and TypeScript share.

Each rule has 1 JSON file in ``tests/fixtures/shared/``: a list of cases, each with
its input and the output of the Python code. The Python test checks that the code
still gives each output. The vitest file named in ``registry.json`` replays the
same cases against the TypeScript copy. So the 2 copies cannot drift apart.

``CK_UPDATE_CORPUS=1`` writes the files again from the Python code. Read the diff
before you commit it: a changed output is a changed rule.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SHARED = Path(__file__).resolve().parents[1] / "fixtures" / "shared"
UPDATE = os.environ.get("CK_UPDATE_CORPUS") == "1"


def check_corpus(name: str, cases: list[dict[str, Any]]) -> None:
    """Compare *cases* with the corpus file, or write it in the update mode."""
    path = SHARED / f"{name}.json"
    if UPDATE or not path.exists():
        path.write_text(json.dumps(cases, indent=1, sort_keys=True) + "\n")
        return
    stored = json.loads(path.read_text())
    assert stored == json.loads(json.dumps(cases)), (
        f"{path.name} differs from the Python code. If the rule changed on "
        "purpose, run CK_UPDATE_CORPUS=1 and change the TypeScript copy too."
    )
