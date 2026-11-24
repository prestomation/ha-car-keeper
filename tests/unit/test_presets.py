"""The car preset rows and the transition table of their registration.

The rows pass the validator of Home Keeper itself when its source is there
(``ci/fetch-home-keeper-validator.sh``; CI sets ``CK_HK_VALIDATOR``). The golden file
``tests/fixtures/presets.json`` holds the call data and the preset ids, because each
preset id goes into the specs that a user makes from it. ``CK_PRESETS_UPDATE=1``
writes it again after a change that is meant.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import types
from pathlib import Path

import ex.presets as presets
import pytest

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / "tests" / "fixtures" / "presets.json"
DEFAULT_VALIDATOR = (
    ROOT / "tests" / ".home_keeper_validator" / "custom_components" / "home_keeper"
)
LANGS = {
    "en", "ca", "cs", "da", "de", "es", "fi", "fr", "it", "nb", "nl", "pl", "pt-BR",
    "ru", "sv", "uk", "zh-Hans",
}  # fmt: skip
COMPANION = "car_keeper"


def _home_keeper_registry() -> types.ModuleType | None:
    """Load ``preset_registry`` of Home Keeper with no Home Assistant, or None.

    A package with the path of the Home Keeper folder lets the relative imports of
    its pure modules work, and its ``__init__`` never runs.
    """
    where = os.environ.get("CK_HK_VALIDATOR")
    path = Path(where) if where else DEFAULT_VALIDATOR
    if not (path / "preset_registry.py").is_file():
        if where:
            raise AssertionError(f"CK_HK_VALIDATOR has no preset_registry.py: {path}")
        return None
    name = "hk_validator"
    if name not in sys.modules:
        package = types.ModuleType(name)
        package.__path__ = [str(path)]
        sys.modules[name] = package
    try:
        return importlib.import_module(f"{name}.preset_registry")
    except ModuleNotFoundError:
        # Home Keeper needs python-dateutil, which the job with no Home Assistant
        # does not install. CI sets CK_HK_VALIDATOR in the job that has it.
        if where:
            raise
        return None


def test_the_rows_pass_the_home_keeper_validator() -> None:
    registry = _home_keeper_registry()
    if registry is None:
        pytest.skip("no Home Keeper source: run ci/fetch-home-keeper-validator.sh")
    data = presets.registration(COMPANION)
    built = registry.build_registration(
        data["domain"], data["rows"], data["duty_names"]
    )
    assert built.preset_ids == presets.preset_ids(presets.ROWS, COMPANION)
    assert all(p["provided_by"] == COMPANION for p in built.presets)


def test_the_validator_refuses_a_bad_row() -> None:
    """The check above is real: the same validator refuses a row with Jinja."""
    registry = _home_keeper_registry()
    if registry is None:
        pytest.skip("no Home Keeper source: run ci/fetch-home-keeper-validator.sh")
    row = {
        "domain": "volvo",
        "brand": "{{ states }}",
        "icon": presets.ICON,
        "duties": [{"duty": "oil_service", "shape": "alert", "keys": ["a"]}],
    }
    with pytest.raises(registry.PresetRowError):
        registry.build_registration(COMPANION, [row])


def test_the_golden_file_holds_the_call_and_the_ids() -> None:
    current = {
        "registration": presets.registration(COMPANION),
        "preset_ids": presets.preset_ids(presets.ROWS, COMPANION),
        "sources": presets.SOURCES,
    }
    if os.environ.get("CK_PRESETS_UPDATE") == "1":
        GOLDEN.write_text(
            json.dumps(current, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    assert json.loads(GOLDEN.read_text(encoding="utf-8")) == current


def test_the_rows_stay_inside_the_caps() -> None:
    assert 1 <= len(presets.ROWS) <= presets.MAX_ROWS
    domains = [row["domain"] for row in presets.ROWS]
    assert len(set(domains)) == len(domains)
    for row in presets.ROWS:
        assert set(row) == {"domain", "brand", "icon", "duties"}
        assert 1 <= len(row["duties"]) <= presets.MAX_DUTIES
        for duty in row["duties"]:
            assert 1 <= len(duty["keys"]) <= presets.MAX_KEYS
            known = duty["duty"] in presets.DUTY_NAMES
            assert known or duty["duty"] in presets.HOME_KEEPER_DUTIES
        assert row["domain"] in presets.SOURCES


def test_each_source_is_pinned_to_a_commit() -> None:
    assert set(presets.SOURCES) == {row["domain"] for row in presets.ROWS}
    for source in presets.SOURCES.values():
        assert source["url"].startswith("https://raw.githubusercontent.com/")
        assert len(source["ref"]) == 40
        int(source["ref"], 16)


def test_each_new_duty_has_a_name_in_each_language() -> None:
    for duty, names in presets.DUTY_NAMES.items():
        assert set(names) == LANGS, duty
        assert all(name.strip() and "{" not in name for name in names.values())


def test_the_call_sends_only_the_duty_names_that_the_rows_use() -> None:
    data = presets.registration(COMPANION)
    used = {d["duty"] for row in presets.ROWS for d in row["duties"]}
    assert set(data["duty_names"]) == used - presets.HOME_KEEPER_DUTIES
    assert data["domain"] == COMPANION
    assert data["rows"] is presets.ROWS


def test_preset_ids_follow_the_home_keeper_rule() -> None:
    rows = [
        {
            "domain": "car",
            "duties": [
                {"duty": "a", "shape": "life_low", "keys": ["x"]},
                {"duty": "b", "shape": "life_low", "keys": ["y"]},
                {"duty": "c", "shape": "alert", "state": "on", "keys": ["z"]},
                {
                    "duty": "d",
                    "shape": "alert",
                    "platform": "binary_sensor",
                    "state": "on",
                    "keys": ["w"],
                },
                # An explicit sensor platform is the same group as no platform.
                {
                    "duty": "e",
                    "shape": "percent_low",
                    "platform": "sensor",
                    "keys": ["v"],
                },
                {"duty": "f", "shape": "percent_low", "keys": ["u"]},
            ],
        },
        {
            "domain": "van",
            "duties": [{"duty": "a", "shape": "life_low", "keys": ["x"]}],
        },
    ]
    assert presets.preset_ids(rows, "ck") == [
        "ck/car_life_low",
        "ck/car_alert_on",
        "ck/car_alert_binary_sensor_on",
        "ck/car_percent_low",
        "ck/van_life_low",
    ]


@pytest.mark.parametrize(
    ("link", "kind", "expected", "call"),
    [
        (presets.Link(), "start", presets.Link(running=True), None),
        (
            presets.Link(service=True),
            "start",
            presets.Link(running=True, service=True),
            presets.REGISTER,
        ),
        (
            presets.Link(),
            "service_added",
            presets.Link(service=True),
            presets.UNREGISTER,
        ),
        (
            presets.Link(running=True),
            "service_added",
            presets.Link(running=True, service=True),
            presets.REGISTER,
        ),
        (
            presets.Link(
                running=True, service=True, registered=True, preset_ids=("a",)
            ),
            "service_removed",
            presets.Link(running=True),
            None,
        ),
        (
            presets.Link(
                running=True, service=True, registered=True, preset_ids=("a",)
            ),
            "stop",
            presets.Link(service=True),
            presets.UNREGISTER,
        ),
        (presets.Link(running=True), "stop", presets.Link(), None),
        (
            presets.Link(running=True, service=True),
            "ask",
            presets.Link(running=True, service=True),
            presets.REGISTER,
        ),
        (presets.Link(service=True), "ask", presets.Link(service=True), None),
        (presets.Link(running=True), "ask", presets.Link(running=True), None),
        (
            presets.Link(running=True, service=True, error="x"),
            "accepted",
            presets.Link(
                running=True, service=True, registered=True, preset_ids=("a",)
            ),
            None,
        ),
        (
            presets.Link(service=True),
            "accepted",
            presets.Link(service=True),
            presets.UNREGISTER,
        ),
        (presets.Link(), "accepted", presets.Link(), None),
        (
            presets.Link(
                running=True, service=True, registered=True, preset_ids=("a",)
            ),
            "refused",
            presets.Link(running=True, service=True, error="bad"),
            None,
        ),
    ],
)
def test_transition_table(
    link: presets.Link, kind: str, expected: presets.Link, call: str | None
) -> None:
    event = presets.Event(kind, preset_ids=("a",), error="bad")
    assert presets.transition(link, event) == (expected, call)


def test_an_unknown_event_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown event"):
        presets.transition(presets.Link(), presets.Event("reload"))


@pytest.mark.parametrize(
    ("link", "word"),
    [
        (presets.Link(running=True), presets.STATUS_NO_SERVICE),
        (presets.Link(service=True, registered=True), presets.STATUS_REGISTERED),
        (presets.Link(service=True, error="x"), presets.STATUS_FAILED),
        (presets.Link(service=True), presets.STATUS_WAITING),
    ],
)
def test_status(link: presets.Link, word: str) -> None:
    assert presets.status(link) == word


def test_project_gives_every_field() -> None:
    link = presets.Link(running=True, service=True, registered=True, preset_ids=("a",))
    out = presets.project(link)
    assert out["status"] == presets.STATUS_REGISTERED
    assert out["preset_ids"] == ["a"]
    assert out["error"] is None
    assert [r["domain"] for r in out["rows"]] == [r["domain"] for r in presets.ROWS]
    first = presets.ROWS[0]
    assert out["rows"][0] == {
        "domain": first["domain"],
        "brand": first["brand"],
        "duties": sorted({d["duty"] for d in first["duties"]}),
    }


def test_the_tab_shows_the_same_duty_names() -> None:
    """The settings page of the tab names each duty as the Home Keeper task does."""
    locales = ROOT / "custom_components" / "car_keeper" / "frontend" / "src" / "locales"
    for lang in LANGS:
        table = json.loads((locales / f"{lang}.json").read_text(encoding="utf-8"))
        for duty, names in presets.DUTY_NAMES.items():
            assert table[f"duty.{duty}"] == names[lang], (lang, duty)
        used = {d["duty"] for row in presets.ROWS for d in row["duties"]}
        assert all(f"duty.{duty}" in table for duty in used), lang
