"""The pure parts of ci/check_preset_keys.py, with no network."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "check_preset_keys", ROOT / "ci" / "check_preset_keys.py"
)
assert _spec and _spec.loader
check = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = check
_spec.loader.exec_module(check)

ROW = {
    "domain": "car",
    "duties": [
        {"duty": "a", "shape": "life_low", "keys": ["days", "gone"]},
        {"duty": "b", "shape": "alert", "platform": "binary_sensor", "keys": ["warn"]},
    ],
}


def test_pinned_url_replaces_the_branch() -> None:
    url = "https://raw.githubusercontent.com/o/r/main/custom_components/x/en.json"
    assert check.pinned_url(url, "abc") == (
        "https://raw.githubusercontent.com/o/r/abc/custom_components/x/en.json"
    )


def test_pinned_url_refuses_another_host() -> None:
    with pytest.raises(ValueError, match="not a raw GitHub URL"):
        check.pinned_url("https://example.com/o/r/main/x", "abc")


def test_missing_keys_reads_the_entity_section_of_each_platform() -> None:
    translations = {"entity": {"sensor": {"days": {}}, "binary_sensor": {"days": {}}}}
    assert check.missing_keys(ROW, translations) == [
        "sensor.gone",
        "binary_sensor.warn",
    ]
    assert check.missing_keys(ROW, {}) == [
        "sensor.days",
        "sensor.gone",
        "binary_sensor.warn",
    ]


def test_missing_in_text_needs_a_quoted_key() -> None:
    text = 'KEYS = {"days": 1, "warn": 2}  # gone'
    assert check.missing_in_text(ROW, text) == ["sensor.gone"]


def test_the_presets_module_loads_with_no_home_assistant() -> None:
    presets = check.load_presets()
    assert presets.ROWS
    assert set(presets.SOURCES) == {row["domain"] for row in presets.ROWS}
