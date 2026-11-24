"""Unit tests for the pure model: the document and the version check."""

from __future__ import annotations

import ex.models as m
import pytest
from hypothesis import given
from hypothesis import strategies as st


def test_normalize_adds_each_missing_section() -> None:
    assert m.normalize_state(None) == m.empty_state()
    assert m.normalize_state([]) == m.empty_state()
    state = m.normalize_state(
        {"cars": {"c": {"id": "c"}}, "items": [], "readings": {"c": [1]}}
    )
    assert state["cars"] == {"c": {"id": "c"}}
    assert state["items"] == {}
    assert state["readings"] == {"c": [1]}
    for name in m.RECORD_SECTIONS:
        assert m.normalize_state({name: {"x": {}}})[name] == {"x": {}}


def test_normalize_keeps_known_settings_and_fixes_the_unit() -> None:
    assert m.normalize_state({"settings": {"unit": "mi", "x": 1}})["settings"] == {
        "unit": "mi",
        "x": 1,
        "templates": {},
    }
    assert m.normalize_state({"settings": {"unit": "parsec"}})["settings"] == {
        "unit": "km",
        "templates": {},
    }
    assert m.normalize_state({"settings": [], "readings": {"c": {}}}) == {
        **m.empty_state(),
        "readings": {"c": []},
    }
    assert m.normalize_state({"settings": {"templates": []}})["settings"] == {
        "unit": "km",
        "templates": {},
    }


def test_error_keeps_the_key_and_string_placeholders() -> None:
    err = m.CarKeeperError("car_not_found", id=7)
    assert err.key == "car_not_found"
    assert err.placeholders == {"id": "7"}
    assert str(err) == "car_not_found"


@pytest.mark.parametrize(
    ("version", "minimum", "expected"),
    [
        ("0.35.0", "0.35.0", True),
        ("0.38.0b5", "0.35.0", True),
        ("0.35.0b7", "0.35.0", False),
        ("0.34.9", "0.35.0", False),
        ("1.0", "0.35.0", True),
        ("0.35", "0.35.0", True),
        ("0.35", "0.35.1", False),
        (" 0.35.0 ", "0.35.0", True),
        ("V0.36.0", "0.35.0", True),
        ("0.35.0", "0.35.0a1", True),
        ("0.35.0a1", "0.35.0", False),
        ("0.35.0.b1", "0.35.0", False),
        ("0.35.0b10", "0.35.0b9", True),
        ("v0.36.0", "0.35.0", True),
        ("0.36.0.dev601", "0.35.0", True),
        ("0.35.0.dev601", "0.35.0", False),
        ("0.35.0rc1", "0.35.0", False),
        ("0.35.0a1", "0.35.0b1", True),
        ("0.35.0b2", "0.35.0b1", True),
        ("0.35.0b1", "0.35.0b2", False),
        (None, "0.35.0", True),
        ("", "0.35.0", True),
        ("main", "0.35.0", True),
        ("0.x.0", "0.35.0", True),
        ("0.35.0-weird", "0.35.0", True),
        ("0.36.0", "garbage", True),
    ],
)
def test_version_at_least(version: str | None, minimum: str, expected: bool) -> None:
    assert m.version_at_least(version, minimum) is expected


@given(
    st.tuples(*(st.integers(0, 50) for _ in range(3))),
    st.tuples(*(st.integers(0, 50) for _ in range(3))),
)
def test_version_order_matches_tuple_order(a: tuple, b: tuple) -> None:
    left = ".".join(map(str, a))
    right = ".".join(map(str, b))
    assert m.version_at_least(left, right) is (a >= b)
