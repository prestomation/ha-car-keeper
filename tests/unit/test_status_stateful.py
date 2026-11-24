"""A model test of the status of a job (``schedule.evaluate``).

The machine drives 1 car with 1 job: it drives distance, lets days pass, marks the
job done, edits the intervals, jumps the odometer and changes the unit. A small
model keeps the limits in its own way, and each step checks that the real rule
gives the same limits, the same status and the same first limit.
"""

from __future__ import annotations

import datetime as dt

import ex.schedule as s
import ex.units as u
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, initialize, invariant, rule
from stateful import STATEFUL

DAY0 = dt.date(2026, 1, 1)


class StatusMachine(RuleBasedStateMachine):
    @initialize(
        distance=st.one_of(st.none(), st.integers(1000, 30000)),
        months=st.integers(1, 24),
        odometer=st.integers(0, 200000),
        lead=st.integers(0, 2000),
        lead_days=st.integers(0, 60),
    )
    def start(self, distance, months, odometer, lead, lead_days) -> None:
        self.unit = "km"
        self.today = DAY0
        self.odometer = float(odometer)
        self.interval = distance
        self.months = months
        self.lead = float(lead)
        self.lead_days = lead_days
        self.base = (DAY0, float(odometer))
        self.history = [(DAY0, float(odometer))]

    def _item(self) -> dict:
        return {
            "kind": "job",
            "enabled": True,
            "interval_distance": self.interval,
            "interval_months": self.months,
            "start": {"date": DAY0.isoformat(), "reading": self.history[0][1]},
            "last_done": {"date": self.base[0].isoformat(), "reading": self.base[1]}
            if self.base != self.history[0]
            else None,
        }

    def _daily(self) -> float | None:
        rows = [{"ts": d.isoformat(), "value": v} for d, v in self.history]
        return s.daily_distance(rows, self.today.isoformat())

    def _real(self) -> dict:
        return s.evaluate(
            self._item(),
            self.odometer,
            self._daily(),
            self.today.isoformat(),
            lead_distance=self.lead,
            lead_days=self.lead_days,
        )

    @rule(km=st.integers(0, 3000), days=st.integers(0, 60))
    def drive(self, km: int, days: int) -> None:
        self.today += dt.timedelta(days=days)
        self.odometer += km
        self.history.append((self.today, self.odometer))

    @rule()
    def done(self) -> None:
        self.base = (self.today, self.odometer)

    @rule(
        distance=st.one_of(st.none(), st.integers(1000, 30000)),
        months=st.integers(1, 24),
    )
    def edit(self, distance, months) -> None:
        self.interval = distance
        self.months = months

    @rule(km=st.integers(10000, 100000))
    def jump(self, km: int) -> None:
        self.odometer += km
        self.history.append((self.today, self.odometer))

    @rule()
    def change_unit(self) -> None:
        new = "mi" if self.unit == "km" else "km"

        def conv(value: float) -> float:
            return u.round_reading(u.convert(value, self.unit, new))

        self.odometer = conv(self.odometer)
        self.history = [(d, conv(v)) for d, v in self.history]
        self.base = (self.base[0], conv(self.base[1]))
        if self.interval is not None:
            self.interval = u.round_interval(u.convert(self.interval, self.unit, new))
        self.lead = float(u.round_interval(u.convert(self.lead, self.unit, new)))
        self.unit = new

    @invariant()
    def limits_match_the_model(self) -> None:
        real = self._real()
        date_limit = s.add_months(self.base[0].isoformat(), self.months)
        days_left = (dt.date.fromisoformat(date_limit) - self.today).days
        assert real["date_limit"] == date_limit
        assert real["days_left"] == days_left
        statuses = []
        if self.interval is None:
            assert real["distance_limit"] is None
        else:
            limit = u.round_reading(self.base[1] + self.interval)
            left = u.round_reading(limit - self.odometer)
            assert real["distance_left"] == left
            statuses.append(2 if left <= 0 else 1 if left <= self.lead else 0)
        statuses.append(
            2 if days_left <= 0 else 1 if days_left <= self.lead_days else 0
        )
        assert s.RANK[real["status"]] == max(statuses)

    @invariant()
    def first_is_the_nearest_limit(self) -> None:
        real = self._real()
        daily = self._daily()
        if self.interval is None:
            assert real["first"] == "date"
            return
        left = real["distance_left"]
        if daily:
            distance_days = max(0.0, left) / daily
        elif left <= 0:
            distance_days = 0.0
        else:
            assert real["first"] == "date"
            return
        expected = "distance" if distance_days < real["days_left"] else "date"
        assert real["first"] == expected

    @invariant()
    def done_today_is_never_overdue_by_distance(self) -> None:
        if self.base == (self.today, self.odometer) and self.interval:
            assert self._real()["distance_left"] == self.interval


TestStatus = StatusMachine.TestCase
TestStatus.settings = STATEFUL
