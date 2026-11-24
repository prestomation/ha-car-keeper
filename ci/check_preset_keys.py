#!/usr/bin/env python3
"""Check that each key of the car preset rows is still in its integration.

``presets.SOURCES`` pins the English translation file of each row to a commit. This
script reads the file at that commit and says which keys of the row are not in the
``entity`` section of their platform. A source with ``match: text`` is a code file
that names the keys, and the key must be in it as a quoted string. With ``--branch``
it reads the branch in the URL instead, so a weekly run finds a key that upstream
removed or renamed.

    python3 ci/check_preset_keys.py            # the pinned commits
    python3 ci/check_preset_keys.py --branch   # the newest upstream files

The downloaded files are data: the script only reads their JSON.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PRESETS = ROOT / "custom_components" / "car_keeper" / "presets.py"


def load_presets() -> Any:
    """Load presets.py alone. The package ``__init__`` imports Home Assistant."""
    spec = importlib.util.spec_from_file_location("ck_presets", PRESETS)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # A dataclass reads its module from sys.modules.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def pinned_url(url: str, ref: str) -> str:
    """The raw URL with its branch part replaced by *ref*."""
    prefix = "https://raw.githubusercontent.com/"
    if not url.startswith(prefix):
        raise ValueError(f"not a raw GitHub URL: {url}")
    owner, repo, _branch, rest = url[len(prefix) :].split("/", 3)
    return f"{prefix}{owner}/{repo}/{ref}/{rest}"


def missing_keys(row: dict[str, Any], translations: dict[str, Any]) -> list[str]:
    """The ``platform.key`` of each key of *row* that *translations* does not have."""
    entity = translations.get("entity") or {}
    out = []
    for duty in row["duties"]:
        platform = duty.get("platform", "sensor")
        known = entity.get(platform) or {}
        out += [f"{platform}.{key}" for key in duty["keys"] if key not in known]
    return out


def missing_in_text(row: dict[str, Any], text: str) -> list[str]:
    """The keys of *row* that are not a quoted string in the code *text*."""
    return [
        f"{duty.get('platform', 'sensor')}.{key}"
        for duty in row["duties"]
        for key in duty["keys"]
        if f'"{key}"' not in text
    ]


def _fetch(url: str, tries: int = 4) -> str:
    """Read *url*. GitHub answers 429 to fast reads, so wait and try again."""
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return str(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            if err.code != 429 or attempt == tries - 1:
                raise
            time.sleep(5 * (attempt + 1))
    raise AssertionError("unreachable")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--branch", action="store_true", help="read the branch")
    args = parser.parse_args(argv)
    presets = load_presets()
    failed = False
    for row in presets.ROWS:
        source = presets.SOURCES[row["domain"]]
        url = source["url"] if args.branch else pinned_url(source["url"], source["ref"])
        try:
            text = _fetch(url)
            if source.get("match") == "text":
                missing = missing_in_text(row, text)
            else:
                missing = missing_keys(row, json.loads(text))
        except (OSError, ValueError) as err:
            print(f"{row['domain']}: cannot read {url}: {err}")
            failed = True
            continue
        if missing:
            failed = True
            print(f"{row['domain']}: missing {', '.join(missing)} in {url}")
        else:
            print(f"{row['domain']}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
