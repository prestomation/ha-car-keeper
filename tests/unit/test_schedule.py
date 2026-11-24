"""Unit tests for the due rule, and the schedule corpus that schedule.ts replays."""

from __future__ import annotations

import random

import ex.schedule as s
import pytest
from hypothesis import given
from hypothesis import strategies as st
from shared_corpus import check_corpus

TODAY = "2026-10-15"


def _job(**kw):
    base = {
        "id": "i",
        "kind": "job",
        "enabled": True,
        "interval_distance": 15000,
        "interval_months": 12,
        "start": {"date": "2026-01-01", "reading": 10000},
        "last_done": None,
    }
    return {**base, **kw}


def _eval(item, odometer=12000.0, daily=None, today=TODAY, lead=(1000, 30)):
    return s.evaluate(
        item, odometer, daily, today, lead_distance=lead[0], lead_days=lead[1]
    )


def test_add_months_clamps_to_the_last_day() -> None:
    assert s.add_months("2026-01-31", 1) == "2026-02-28"
    assert s.add_months("2024-01-31", 1) == "2024-02-29"
    assert s.add_months("2026-11-15", 2) == "2027-01-15"
    assert s.add_months("2026-03-31", -1) == "2026-02-28"
    assert s.add_months("2026-05-10T08:00:00+00:00", 12) == "2027-05-10"


def test_days_between_and_worst() -> None:
    assert s.days_between("2026-10-15", "2026-10-20") == 5
    assert s.days_between("2026-10-20", "2026-10-15") == -5
    assert s.worst([]) == "ok"
    assert s.worst(["ok", "soon"]) == "soon"
    assert s.worst(["soon", "overdue", "ok"]) == "overdue"


def test_both_limits_ok() -> None:
    out = _eval(_job())
    assert out == {
        "status": "ok",
        "first": "date",
        "distance_limit": 25000.0,
        "distance_left": 13000.0,
        "date_limit": "2027-01-01",
        "days_left": 78,
        "eta_days": 78,
    }


def test_distance_first_with_a_daily_distance() -> None:
    out = _eval(_job(), daily=200)
    assert out["first"] == "distance" and out["eta_days"] == 65
    out = _eval(_job(), daily=100)
    assert out["first"] == "date" and out["eta_days"] == 78


def test_soon_and_overdue_by_distance() -> None:
    assert _eval(_job(), odometer=24000)["status"] == "soon"
    assert _eval(_job(), odometer=23999)["status"] == "ok"
    over = _eval(_job(), odometer=25000)
    assert over["status"] == "overdue" and over["distance_left"] == 0
    assert over["first"] == "distance" and over["eta_days"] == 0


def test_soon_and_overdue_by_date() -> None:
    assert _eval(_job(), today="2026-12-02")["status"] == "soon"
    assert _eval(_job(), today="2026-12-01")["status"] == "ok"
    assert _eval(_job(), today="2027-01-01")["status"] == "overdue"
    assert _eval(_job(), today="2027-03-01")["days_left"] == -59


def test_last_done_is_the_base() -> None:
    item = _job(last_done={"date": "2026-06-01", "reading": 20000})
    out = _eval(item, odometer=21000)
    assert out["distance_limit"] == 35000.0 and out["date_limit"] == "2027-06-01"


def test_distance_only_and_time_only() -> None:
    distance = _eval(_job(interval_months=None))
    assert distance["date_limit"] is None and distance["first"] == "distance"
    assert distance["eta_days"] is None
    time_only = _eval(_job(interval_distance=None))
    assert time_only["distance_limit"] is None and time_only["first"] == "date"


def test_no_reading_means_no_distance_limit() -> None:
    item = _job(start={"date": "2026-01-01", "reading": None})
    assert _eval(item)["distance_limit"] is None
    assert _eval(_job(), odometer=None)["distance_limit"] is None


def test_a_disabled_item_is_ok_with_no_limit() -> None:
    out = _eval(_job(enabled=False), odometer=99999)
    assert out["status"] == "ok" and out["distance_limit"] is None


def test_date_job() -> None:
    item = {"kind": "date", "due_date": "2026-11-01", "interval_months": 12}
    assert _eval(item)["date_limit"] == "2026-11-01"
    assert _eval(item)["status"] == "soon"
    done = {**item, "last_done": {"date": "2026-10-20", "reading": None}}
    assert _eval(done)["date_limit"] == "2027-11-01"
    once = {"kind": "date", "due_date": "2026-11-01", "last_done": done["last_done"]}
    assert _eval(once) == {**_eval({"kind": "date"}), "status": "ok"}


def test_date_due() -> None:
    item = {"due_date": "2027-03-01", "interval_months": 12}
    assert s.date_due(item, 30) == "2027-03-01"
    early = {**item, "last_done": {"date": "2027-02-20"}}
    assert s.date_due(early, 30) == "2028-03-01"
    very_early = {**item, "last_done": {"date": "2027-01-05"}}
    assert s.date_due(very_early, 30) == "2027-03-01"
    late = {**item, "last_done": {"date": "2028-04-10"}}
    assert s.date_due(late, 30) == "2029-03-01"
    assert (
        s.date_due({"due_date": "2027-03-01", "last_done": early["last_done"]}, 30)
        is None
    )
    assert s.date_due({"due_date": None}, 30) is None


def test_daily_distance() -> None:
    rows = [
        {"ts": "2026-09-01T10:00:00+00:00", "value": 1000},
        {"ts": "2026-10-01T10:00:00+00:00", "value": 1600},
    ]
    assert s.daily_distance(rows, TODAY) == 20.0
    assert s.daily_distance(rows[:1], TODAY) is None
    short = [rows[1], {"ts": "2026-10-05T10:00:00+00:00", "value": 1700}]
    assert s.daily_distance(short, TODAY) is None
    old = [{"ts": "2026-01-01T10:00:00+00:00", "value": 0}, *rows]
    assert s.daily_distance(old, TODAY) == 20.0
    down = [rows[0], {"ts": "2026-10-01T10:00:00+00:00", "value": 900}]
    assert s.daily_distance(down, TODAY) == 0.0
    edge = [
        {"ts": "2026-07-17T10:00:00+00:00", "value": 0},
        {"ts": "2026-07-24T10:00:00+00:00", "value": 70},
    ]
    assert s.daily_distance(edge, TODAY) == 10.0
    assert s.daily_distance(edge, "2026-10-16") is None


def test_sort_key() -> None:
    over = {"status": "overdue", "eta_days": 0}
    soon = {"status": "soon", "eta_days": 5}
    later = {"status": "ok", "eta_days": 50}
    unknown = {"status": "ok", "eta_days": None}
    names = ["d", "c", "b", "a"]
    rows = sorted(
        zip(names, [unknown, later, soon, over], strict=True),
        key=lambda r: s.sort_key(r[0], r[1]),
    )
    assert [r[0] for r in rows] == ["a", "b", "c", "d"]
    assert s.sort_key("B", later) > s.sort_key("a", later)


@given(
    st.integers(0, 300_000),
    st.integers(1, 50_000),
    st.integers(0, 2000),
)
def test_status_follows_the_distance_left(start: int, interval: int, lead: int) -> None:
    item = _job(
        interval_distance=interval,
        interval_months=None,
        start={"date": "2026-01-01", "reading": start},
    )
    for odometer in (start, start + interval - lead - 1, start + interval):
        out = _eval(item, odometer=odometer, lead=(lead, 30))
        left = start + interval - odometer
        expected = "overdue" if left <= 0 else "soon" if left <= lead else "ok"
        assert out["status"] == expected


@given(st.integers(0, 120), st.integers(1, 120))
def test_more_distance_never_improves_the_status(extra: int, step: int) -> None:
    item = _job()
    a = _eval(item, odometer=12000 + extra * 100)
    b = _eval(item, odometer=12000 + extra * 100 + step * 100)
    assert s.RANK[b["status"]] >= s.RANK[a["status"]]


def _day(rng: random.Random, year: int, first: int, last: int) -> str:
    return f"{year}-{rng.randint(first, last):02d}-{rng.randint(1, 28):02d}"


def _corpus_cases() -> list[dict]:
    rng = random.Random(599)
    cases = []
    for _ in range(300):
        kind = rng.choice(["job", "job", "job", "date"])
        start = {
            "date": f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",
            "reading": rng.choice([None, rng.randint(0, 200000)]),
        }
        item = {
            "kind": kind,
            "enabled": rng.random() > 0.05,
            "interval_distance": rng.choice([None, rng.randint(1000, 30000)]),
            "interval_months": rng.choice([None, rng.randint(1, 36)]),
            "start": start,
            "last_done": rng.choice(
                [
                    None,
                    {
                        "date": _day(rng, 2026, 1, 9),
                        "reading": rng.choice([None, rng.randint(0, 200000)]),
                    },
                ]
            ),
            "due_date": f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
            if kind == "date"
            else None,
        }
        odometer = rng.choice([None, float(rng.randint(0, 250000))])
        daily = rng.choice([None, 0.0, round(rng.uniform(1, 120), 1)])
        today = f"2026-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        lead = (rng.randint(0, 2000), rng.randint(0, 60))
        cases.append(
            {
                "item": item,
                "odometer": odometer,
                "daily": daily,
                "today": today,
                "lead_distance": lead[0],
                "lead_days": lead[1],
                "out": s.evaluate(
                    item,
                    odometer,
                    daily,
                    today,
                    lead_distance=lead[0],
                    lead_days=lead[1],
                ),
            }
        )
    readings_cases = []
    for _ in range(60):
        rows = sorted(
            (
                {
                    "ts": _day(rng, 2026, 6, 10) + "T08:00:00+00:00",
                    "value": rng.randint(0, 50000),
                }
                for _ in range(rng.randint(0, 6))
            ),
            key=lambda r: r["ts"],
        )
        today = f"2026-{rng.randint(9, 12):02d}-{rng.randint(1, 28):02d}"
        readings_cases.append(
            {"readings": rows, "today": today, "out": s.daily_distance(rows, today)}
        )
    months = [
        {"date": d, "months": m, "out": s.add_months(d, m)}
        for d in ("2026-01-31", "2024-02-29", "2026-08-31", "2026-12-15")
        for m in (1, 2, 6, 12, 13, 25)
    ]
    return [{"evaluate": cases, "daily_distance": readings_cases, "add_months": months}]


def test_schedule_corpus() -> None:
    check_corpus("schedule", _corpus_cases())


@pytest.mark.parametrize("status", s.STATUSES)
def test_ranks_are_ordered(status: str) -> None:
    assert s.RANK[status] == s.STATUSES.index(status)
