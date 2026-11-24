"""A model test of the service history (``history.py`` and the service builders).

The machine logs, changes and deletes service records of 1 car with 3 jobs, with
parts. After each step it checks:

* ``last_done`` of each job is the latest service that did it, by date, then
  reading, then the time of logging, as a model computes it with its own sort.
* A service with an earlier date never moves ``last_done`` back.
* The sum of the stock moves of all steps is the parts that the current services
  use, so a delete gives each part back.
"""

from __future__ import annotations

import ex.history as h
import ex.models as m
from hypothesis import strategies as st
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    initialize,
    invariant,
    rule,
)
from stateful import STATEFUL

CAR = {"id": "c", "unit": "km", "odometer": {"value": 0.0}}
DATES = st.dates(
    min_value=__import__("datetime").date(2025, 1, 1),
    max_value=__import__("datetime").date(2027, 12, 31),
).map(str)
READINGS = st.one_of(st.none(), st.integers(0, 100000))
JOBS = st.lists(st.sampled_from(["oil", "tyres", "wipers"]), max_size=3, unique=True)
PARTS = st.lists(
    st.fixed_dictionaries(
        {
            "asset_id": st.just("a"),
            "part_id": st.sampled_from(["filter", "oil"]),
            "quantity": st.integers(1, 3),
        }
    ),
    max_size=2,
)


class HistoryMachine(RuleBasedStateMachine):
    services = Bundle("services")

    @initialize()
    def start(self) -> None:
        self.items = {
            i: {"id": i, "car_id": "c", "name": i, "last_done": None}
            for i in ("oil", "tyres", "wipers")
        }
        self.store: dict[str, dict] = {}
        self.count = 0
        self.moves: dict[tuple[str, str], float] = {}

    def _move(self, before: list, after: list) -> None:
        for key, value in h.stock_moves(before, after).items():
            self.moves[key] = self.moves.get(key, 0.0) + value

    def _refresh(self, ids) -> None:
        self.items.update(h.refresh(self.items, self.store, list(ids)))

    @rule(target=services, date=DATES, reading=READINGS, jobs=JOBS, parts=PARTS)
    def log(self, date, reading, jobs, parts):
        self.count += 1
        service = m.build_service(
            {"date": date, "reading": reading, "items": jobs},
            service_id=f"s{self.count}",
            car=CAR,
            items=self.items,
            today="2026-06-01",
            now=f"2026-06-01T00:00:{self.count:02d}",
        )
        service["parts_used"] = parts
        before = {i: self.items[i]["last_done"] for i in jobs}
        self.store[service["id"]] = service
        self._move([], parts)
        self._refresh(jobs)
        for item_id, old in before.items():
            new = self.items[item_id]["last_done"]
            if old is not None and date < old["date"]:
                assert new == old
        return service["id"]

    @rule(service_id=services, date=DATES, jobs=JOBS, parts=PARTS)
    def change(self, service_id, date, jobs, parts):
        if service_id not in self.store:
            return
        old = self.store[service_id]
        new, changed = m.update_service(
            old, {"date": date, "items": jobs}, CAR, self.items, "2026-06-01"
        )
        new["parts_used"] = parts
        assert set(changed) <= {"date", "items"}
        self.store[service_id] = new
        self._move(old["parts_used"], parts)
        self._refresh({*old["items"], *jobs})

    @rule(service_id=services)
    def delete(self, service_id):
        old = self.store.pop(service_id, None)
        if old is None:
            return
        self._move(old["parts_used"], [])
        self._refresh(old["items"])

    @invariant()
    def last_done_is_the_latest_service(self) -> None:
        for item_id, item in self.items.items():
            rows = [s for s in self.store.values() if item_id in s["items"]]
            if not rows:
                assert item["last_done"] is None
                continue
            rows.sort(
                key=lambda s: (
                    s["date"],
                    -1 if s["reading"] is None else s["reading"],
                    s["logged"],
                )
            )
            latest = rows[-1]
            assert item["last_done"] == {
                "date": latest["date"],
                "reading": latest["reading"],
                "service_id": latest["id"],
            }

    @invariant()
    def stock_moves_add_up(self) -> None:
        used: dict[tuple[str, str], float] = {}
        for service in self.store.values():
            for part in service["parts_used"]:
                key = (part["asset_id"], part["part_id"])
                used[key] = used.get(key, 0.0) - part["quantity"]
        assert {k: v for k, v in self.moves.items() if v} == {
            k: v for k, v in used.items() if v
        }


TestHistory = HistoryMachine.TestCase
TestHistory.settings = STATEFUL


def test_stock_moves() -> None:
    a = {"asset_id": "a", "part_id": "p", "quantity": 2}
    b = {"asset_id": "a", "part_id": "q", "quantity": 1}
    assert h.stock_moves([], [a]) == {("a", "p"): -2.0}
    assert h.stock_moves([a], []) == {("a", "p"): 2.0}
    assert h.stock_moves([a], [a]) == {}
    assert h.stock_moves([a, b], [{**a, "quantity": 3}]) == {
        ("a", "p"): -1.0,
        ("a", "q"): 1.0,
    }
    assert h.stock_moves([{"asset_id": "a", "part_id": "p"}], []) == {}


def test_last_done_and_refresh() -> None:
    services = [
        {
            "id": "1",
            "date": "2026-01-01",
            "reading": 100,
            "items": ["x"],
            "logged": "a",
        },
        {
            "id": "2",
            "date": "2026-01-01",
            "reading": None,
            "items": ["x"],
            "logged": "b",
        },
        {
            "id": "3",
            "date": "2025-12-01",
            "reading": 900,
            "items": ["x"],
            "logged": "c",
        },
    ]
    assert h.last_done("x", services) == {
        "date": "2026-01-01",
        "reading": 100,
        "service_id": "1",
    }
    assert h.last_done("y", services) is None
    items = {"x": {"id": "x", "last_done": None}}
    assert h.refresh(items, {s["id"]: s for s in services}, ["x", "gone"]) == {
        "x": {
            "id": "x",
            "last_done": {"date": "2026-01-01", "reading": 100, "service_id": "1"},
        }
    }
    fresh = h.refresh(items, {s["id"]: s for s in services}, ["x"])
    assert h.refresh(fresh, {s["id"]: s for s in services}, ["x"]) == {}
