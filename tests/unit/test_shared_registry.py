"""The registry of the rules that Python and TypeScript share is complete.

Each rule names a corpus, the 2 copies of the rule and the 2 tests. Each corpus
file in ``tests/fixtures/shared/`` has an entry, and each named file exists.
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHARED = ROOT / "tests" / "fixtures" / "shared"


def test_every_corpus_is_registered_and_every_file_exists() -> None:
    registry = json.loads((SHARED / "registry.json").read_text())
    named = set()
    for rule in registry["rules"]:
        for key in ("corpus", "python", "typescript", "pytest", "vitest"):
            assert (ROOT / rule[key]).is_file(), (rule["name"], key)
        assert rule["corpus"].endswith(f"{rule['name']}.json")
        named.add(Path(rule["corpus"]).name)
        assert rule["name"] in (ROOT / rule["vitest"]).read_text()
        assert f'check_corpus("{rule["name"]}"' in (ROOT / rule["pytest"]).read_text()
    corpora = {p.name for p in SHARED.glob("*.json")} - {"registry.json"}
    assert corpora == named
