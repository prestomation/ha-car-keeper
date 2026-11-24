"""A model test of the odometer transitions (``readings.py``).

A Hypothesis state machine drives the real transitions and a small model side by
side: typed readings, sensor states (also lower ones and values that are not a
number), admin corrections with an offset, a change of the source and a change of
the unit. After each step it checks the invariants:

* The value only goes down through a correction or a unit change.
* The value is the last stored reading.
* The readings are in time order, with at most 1 sensor reading a day.
* A repair issue comes only from the second lower sensor value in a row.
"""

from __future__ import annotations

import datetime as dt

import ex.readings as r
import ex.units as u
from ex.models import CarKeeperError
from hypothesis import strategies as st
from hypothesis.stateful import (
    RuleBasedStateMachine,
    initialize,
    invariant,
    precondition,
    rule,
)
from stateful import STATEFUL

START = dt.datetime(2026, 1, 1, 8, tzinfo=dt.UTC)
VALUES = st.floats(min_value=0, max_value=500_000, allow_nan=False).map(u.round_reading)


class OdometerMachine(RuleBasedStateMachine):
    """The odometer of 1 car."""

    @initialize(value=st.one_of(st.none(), VALUES), unit=st.sampled_from(["km", "mi"]))
    def start(self, value: float | None, unit: str) -> None:
        self.odometer = r.new_odometer(value=value)
        self.unit = unit
        self.readings: list[dict] = []
        self.clock = START
        self.floor = value  # The lowest value the next accepted reading may have.
        self.model_lower: float | None = None

    def _now(self, hours: int) -> str:
        self.clock += dt.timedelta(hours=hours)
        return self.clock.isoformat()

    def _store(self, outcome: r.Outcome) -> None:
        self.odometer = outcome.odometer
        if outcome.reading is not None:
            self.readings = r.add(self.readings, outcome.reading)

    @rule(value=VALUES, hours=st.integers(0, 48))
    def typed(self, value: float, hours: int) -> None:
        current = self.odometer["value"]
        try:
            outcome = r.typed(self.odometer, value, self._now(hours), by="u")
        except CarKeeperError as err:
            assert err.key == "odometer_decreased"
            assert current is not None and value < current
            return
        assert current is None or value >= current
        assert outcome.reading is not None and outcome.reading["value"] == value
        self.model_lower = None
        self._store(outcome)

    @rule(
        raw=st.one_of(VALUES, st.sampled_from(["unavailable", "unknown", None, "nan"])),
        sensor_unit=st.sampled_from(["km", "mi", "m", None, "ft"]),
        hours=st.integers(0, 30),
    )
    def sensor(self, raw: object, sensor_unit: str | None, hours: int) -> None:
        before = self.odometer
        outcome = r.from_entity(before, raw, sensor_unit, self.unit, self._now(hours))
        try:
            number = float(raw)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            number = None
        readable = (
            number is not None
            and number == number
            and u.known(sensor_unit or self.unit)
        )
        if not readable:
            assert outcome.odometer == before and outcome.reading is None
            assert not outcome.issue
            return
        value = u.round_reading(
            u.convert(number, sensor_unit or self.unit, self.unit) + before["offset"]
        )
        current = before["value"]
        if current is None or value > current:
            assert outcome.reading is not None and outcome.reading["value"] == value
            assert outcome.odometer["lower"] is None and not outcome.issue
            self.model_lower = None
        elif value == current:
            assert outcome.reading is None and not outcome.issue
            self.model_lower = None
        else:
            assert outcome.reading is None
            assert outcome.issue == (self.model_lower is not None)
            assert outcome.odometer["value"] == current
            self.model_lower = value
        self._store(outcome)

    @rule(value=VALUES, offset=st.one_of(st.none(), VALUES), hours=st.integers(0, 48))
    def correct(self, value: float, offset: float | None, hours: int) -> None:
        old_offset = self.odometer["offset"]
        outcome = r.corrected(self.odometer, value, self._now(hours), offset=offset)
        assert outcome.reading is not None and outcome.reading["source"] == "correction"
        assert outcome.odometer["offset"] == (old_offset if offset is None else offset)
        self.model_lower = None
        self.floor = value
        self._store(outcome)

    @rule(source=st.sampled_from(["manual", "entity"]))
    def bind(self, source: str) -> None:
        entity = "sensor.odo" if source == "entity" else None
        out = r.bound(self.odometer, source, entity)
        assert out["value"] == self.odometer["value"]
        assert out["entity_id"] == entity
        self.odometer = out
        self.model_lower = None

    @precondition(lambda self: self.readings)
    @rule(unit=st.sampled_from(["km", "mi"]))
    def change_unit(self, unit: str) -> None:
        if unit == self.unit:
            return
        self.odometer = r.convert_odometer(self.odometer, self.unit, unit)
        self.readings = r.convert_readings(self.readings, self.unit, unit)
        if self.odometer.get("lower") is not None:
            self.model_lower = self.odometer["lower"]
        self.unit = unit
        self.floor = self.odometer["value"]

    @invariant()
    def value_is_the_last_reading(self) -> None:
        if self.readings:
            assert self.odometer["value"] == self.readings[-1]["value"]

    @invariant()
    def readings_are_in_order_with_one_sensor_reading_a_day(self) -> None:
        stamps = [row["ts"] for row in self.readings]
        assert stamps == sorted(stamps)
        days = [row["ts"][:10] for row in self.readings if row["source"] == "entity"]
        assert len(days) == len(set(days))

    @invariant()
    def value_goes_down_only_by_a_correction(self) -> None:
        last_correction = max(
            (i for i, row in enumerate(self.readings) if row["source"] == "correction"),
            default=-1,
        )
        after = [row["value"] for row in self.readings[last_correction + 1 :]]
        # A sensor reading can replace an earlier one of the same day, so compare the
        # value with the readings after the last correction.
        assert after == sorted(after)


TestOdometer = OdometerMachine.TestCase
TestOdometer.settings = STATEFUL


def test_typed_refuses_a_negative_value() -> None:
    import pytest

    with pytest.raises(CarKeeperError) as info:
        r.typed(r.new_odometer(), -1, "2026-01-01T00:00:00+00:00")
    assert info.value.key == "invalid_reading"
    with pytest.raises(CarKeeperError) as info:
        r.corrected(r.new_odometer(), -1, "2026-01-01T00:00:00+00:00")
    assert info.value.key == "invalid_reading"


def test_bound_checks_the_source() -> None:
    import pytest

    with pytest.raises(CarKeeperError) as info:
        r.bound(r.new_odometer(), "cloud", None)
    assert info.value.placeholders == {"field": "source"}
    with pytest.raises(CarKeeperError) as info:
        r.bound(r.new_odometer(), "entity", None)
    assert info.value.key == "field_required"


def test_new_odometer_and_reading_shapes() -> None:
    assert r.new_odometer("entity", "sensor.x", 12.34) == {
        "source": "entity",
        "entity_id": "sensor.x",
        "value": 12.3,
        "updated": None,
        "offset": 0.0,
        "lower": None,
    }
    assert r.new_odometer("manual", "sensor.x")["entity_id"] is None
    assert r.reading(5.55, "t", "manual", "u") == {
        "ts": "t",
        "value": 5.6,
        "source": "manual",
        "by": "u",
    }


def test_a_sensor_value_with_an_offset_and_a_unit() -> None:
    odometer = {**r.new_odometer(value=10.0), "offset": 50.0}
    out = r.from_entity(odometer, "1609.344", "m", "mi", "2026-01-02T00:00:00+00:00")
    assert out.reading is not None and out.reading["value"] == 51.0
    same = r.from_entity(out.odometer, 1609.344, "m", "mi", "2026-01-03T00:00:00+00:00")
    assert same.reading is None and same.odometer["value"] == 51.0
