"""Unit tests for the distance units, and the units corpus that units.ts replays."""

from __future__ import annotations

import ex.units as u
import pytest
from hypothesis import given
from hypothesis import strategies as st
from shared_corpus import check_corpus


def test_convert() -> None:
    assert u.convert(1, "mi", "km") == pytest.approx(1.609344)
    assert u.convert(1609.344, "m", "mi") == pytest.approx(1)
    assert u.convert(5, "km", "km") == 5.0
    assert u.convert(1, "km", "m") == 1000.0
    with pytest.raises(ValueError):
        u.convert(1, "parsec", "km")
    with pytest.raises(ValueError):
        u.convert(1, "km", "ly")


def test_known() -> None:
    assert u.known("km") and u.known("mi") and u.known("m")
    assert not u.known("ft") and not u.known(None)


def test_rounding_is_half_up() -> None:
    assert u.round_reading(10.25) == 10.3
    assert u.round_reading(10.24) == 10.2
    assert u.round_interval(2.5) == 3
    assert u.round_interval(3.5) == 4
    assert u.round_interval(2.49) == 2
    assert u.round_template(9320.6) == 9300
    assert u.round_template(9350) == 9400
    assert u.round_template(49.9) == 0


def test_group_digits() -> None:
    assert u.group_digits(0) == "0"
    assert u.group_digits(999) == "999"
    assert u.group_digits(1000) == "1,000"
    assert u.group_digits(1234567.6) == "1,234,568"
    assert u.group_digits(-15000) == "-15,000"


def test_defaults() -> None:
    assert u.DEFAULT_LEAD_DISTANCE == {"km": 1000, "mi": 600}
    assert u.DEFAULT_LEAD_DAYS == 30


@given(
    st.floats(min_value=0, max_value=2_000_000, allow_nan=False),
    st.sampled_from(["km", "mi", "m"]),
    st.sampled_from(["km", "mi", "m"]),
)
def test_round_trip_keeps_the_value(value: float, a: str, b: str) -> None:
    there = u.convert(value, a, b)
    assert u.convert(there, b, a) == pytest.approx(value, rel=1e-9, abs=1e-9)


@given(st.floats(min_value=0, max_value=10_000_000, allow_nan=False))
def test_round_reading_is_within_half_a_step(value: float) -> None:
    assert abs(u.round_reading(value) - value) <= 0.05 + 1e-6


_VALUES = [0, 1, 0.05, 0.15, 2.5, 99.95, 160.9344, 1000, 9320.57, 15000, 123456.789]


def test_units_corpus() -> None:
    cases = []
    for value in _VALUES:
        for a in ("km", "mi", "m"):
            for b in ("km", "mi"):
                converted = u.convert(value, a, b)
                cases.append(
                    {
                        "value": value,
                        "from": a,
                        "to": b,
                        "converted": converted,
                        "reading": u.round_reading(converted),
                        "interval": u.round_interval(converted),
                        "template": u.round_template(converted),
                        "grouped": u.group_digits(converted),
                    }
                )
    check_corpus("units", cases)
