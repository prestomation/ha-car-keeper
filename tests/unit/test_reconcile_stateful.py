"""State machine test (d): the reconcile of Car Keeper with Home Keeper.

The model has 1 car, its jobs, its service records and a fake Home Keeper. The rules
change either side: an admin adds or edits a job, a user logs or deletes a service,
and a Home Keeper user completes or deletes a task. After each rule, the sync runs
``task_plan.plan_tasks`` and applies the steps to the fake until a plan is empty.

The invariants:

- The sync settles: a plan is empty after a small number of rounds.
- Each job that wants a task has exactly 1 Car Keeper task, and the job knows its id.
- Home Keeper has no Car Keeper task without a job that wants it.
- Each job of each service has 1 completion on the task of the job, and Home Keeper
  has no completion of Car Keeper that no service holds.
- The settled task has the fields of ``task_plan.desired_task``.
"""

from __future__ import annotations

import copy
import itertools

import ex.history as history
import ex.models as models
import ex.task_plan as tp
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule
from stateful import STATEFUL

CAR = "car"
ENTITY = "sensor.car_odometer"
DEVICE = "device-car"
ENTRY = "entry"
OFFSET = "+00:00"
MAX_ROUNDS = 6


class FakeHomeKeeper:
    """The task store of Home Keeper, as far as the sync uses it."""

    def __init__(self) -> None:
        self.tasks: dict[str, dict] = {}
        self._ids = itertools.count()

    def add(self, fields: dict) -> str:
        task_id = f"t{next(self._ids)}"
        self.tasks[task_id] = {
            **copy.deepcopy(fields),
            "id": task_id,
            "completions": [],
        }
        return task_id

    def listing(self) -> list[dict]:
        return copy.deepcopy(list(self.tasks.values()))


class ReconcileMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.hk = FakeHomeKeeper()
        car = {
            "id": CAR,
            "name": "Car",
            "unit": "km",
            "odometer": {"value": 10000.0},
        }
        self.state = {
            "cars": {CAR: car},
            "items": {},
            "services": {},
            "readings": {},
            "sync": models.empty_sync(),
        }
        self.ids = itertools.count()
        self.day = 1
        self.reading = 10000.0
        self.rounds = 0

    # ── Car Keeper side ──────────────────────────────────────────────────────

    @rule(
        distance=st.sampled_from([None, 5000, 10000]),
        months=st.sampled_from([None, 6, 12]),
        add_task=st.booleans(),
    )
    def add_item(self, distance, months, add_task) -> None:
        if distance is None and months is None:
            months = 12
        item = models.build_item(
            {
                "name": f"Job {len(self.state['items'])}",
                "interval_distance": distance,
                "interval_months": months,
                "add_task": add_task,
            },
            item_id=f"i{next(self.ids)}",
            car=self.state["cars"][CAR],
            today=self._date(),
        )
        self.state["items"][item["id"]] = item
        self.sync()

    @rule(data=st.data())
    def edit_item(self, data) -> None:
        if not self.state["items"]:
            return
        item_id = data.draw(st.sampled_from(sorted(self.state["items"])))
        change = data.draw(
            st.sampled_from(
                [
                    {"add_task": True},
                    {"add_task": False},
                    {"enabled": False},
                    {"enabled": True},
                    {"name": "Renamed"},
                    {"interval_months": 3},
                    {"interval_distance": 7500},
                ]
            )
        )
        item = self.state["items"][item_id]
        if change.get("interval_distance") and item["interval_months"] is None:
            change = {**change, "interval_months": 24}
        new, _ = models.update_item(item, change)
        self.state["items"][item_id] = new
        self.sync()

    @rule(data=st.data(), drive=st.integers(0, 3000))
    def log_service(self, data, drive) -> None:
        if not self.state["items"]:
            return
        items = data.draw(
            st.lists(st.sampled_from(sorted(self.state["items"])), min_size=1)
        )
        self.reading += drive
        self.day += 1
        service = models.build_service(
            {"items": items, "reading": self.reading, "cost": 10, "date": self._date()},
            service_id=f"s{next(self.ids)}",
            car=self.state["cars"][CAR],
            items=self.state["items"],
            today=self._date(),
            now=f"{self._date()}T09:00:00+00:00",
            origin=None,
        )
        self.state["services"][service["id"]] = service
        self._refresh(service["items"])
        self.sync()

    @rule(data=st.data())
    def log_the_same_job_again_today(self, data) -> None:
        """A second service of 1 job on the same day, logged at the same time."""
        if not self.state["services"]:
            return
        first = self.state["services"][
            data.draw(st.sampled_from(sorted(self.state["services"])))
        ]
        service = models.build_service(
            {"items": first["items"][:1], "date": first["date"]},
            service_id=f"s{next(self.ids)}",
            car=self.state["cars"][CAR],
            items=self.state["items"],
            today=first["date"],
            now=first["logged"],
            origin=None,
        )
        self.state["services"][service["id"]] = service
        self._refresh(service["items"])
        self.sync()

    @rule(data=st.data())
    def delete_service(self, data) -> None:
        if not self.state["services"]:
            return
        service_id = data.draw(st.sampled_from(sorted(self.state["services"])))
        service = self.state["services"].pop(service_id)
        for done in service.get("hk_completions", {}).values():
            self.state["sync"]["undo"].append(dict(done))
        self._refresh(service["items"])
        self.sync()

    @rule(data=st.data())
    def lose_a_completion_write(self, data) -> None:
        """The store write after ``complete_task`` failed: the service forgets it."""
        held = [
            (service_id, item_id)
            for service_id, service in sorted(self.state["services"].items())
            for item_id in sorted(service["hk_completions"])
        ]
        if not held:
            return
        service_id, item_id = data.draw(st.sampled_from(held))
        del self.state["services"][service_id]["hk_completions"][item_id]
        self.sync()

    # ── Home Keeper side ─────────────────────────────────────────────────────

    @rule(data=st.data())
    def user_deletes_a_task(self, data) -> None:
        if not self.hk.tasks:
            return
        task_id = data.draw(st.sampled_from(sorted(self.hk.tasks)))
        del self.hk.tasks[task_id]
        self.sync()

    @rule(data=st.data())
    def user_completes_a_task(self, data) -> None:
        if not self.hk.tasks:
            return
        task_id = data.draw(st.sampled_from(sorted(self.hk.tasks)))
        task = self.hk.tasks[task_id]
        item_id = task["source"]["car_keeper"]["item_id"]
        self.day += 1
        ts = f"{self._date()}T18:00:00+00:00"
        task["completions"].append({"ts": ts})
        item = self.state["items"][item_id]
        service = models.build_service(
            tp.service_from_completion({"completed_at": ts}, item),
            service_id=f"s{next(self.ids)}",
            car=self.state["cars"][CAR],
            items=self.state["items"],
            today=self._date(),
            now=ts,
            origin="home_keeper",
        )
        service["hk_completions"] = {item_id: {"task_id": task_id, "ts": ts}}
        self.state["services"][service["id"]] = service
        self._refresh([item_id])
        self.sync()

    # ── The sync ─────────────────────────────────────────────────────────────

    def _date(self) -> str:
        return f"2026-{1 + self.day // 28:02d}-{1 + self.day % 28:02d}"

    def _refresh(self, item_ids) -> None:
        self.state["items"].update(
            history.refresh(self.state["items"], self.state["services"], item_ids)
        )

    def plan(self) -> dict:
        date_limits = {k: v.get("due_date") for k, v in self.state["items"].items()}
        return tp.plan_tasks(
            self.state,
            self.hk.listing(),
            entity_ids={CAR: ENTITY},
            device_ids={CAR: DEVICE},
            date_limits=date_limits,
            entry_id=ENTRY,
            offset=OFFSET,
        )

    def sync(self) -> None:
        for entry in self.state["sync"]["undo"]:
            task = self.hk.tasks.get(entry["task_id"])
            if task:
                task["completions"] = [
                    c for c in task["completions"] if c["ts"] != entry["ts"]
                ]
        self.state["sync"]["undo"] = []
        for self.rounds in range(1, MAX_ROUNDS + 1):
            plan = self.plan()
            if not any(plan.values()):
                return
            self.apply(plan)
        raise AssertionError(f"the sync did not settle: {self.plan()}")

    def apply(self, plan: dict) -> None:
        items = self.state["items"]
        for step in plan["deletes"]:
            self.hk.tasks.pop(step["task_id"], None)
        for step in plan["forgets"]:
            items[step["item_id"]]["hk_task_id"] = None
            items[step["item_id"]]["add_task"] = False
        for step in plan["adds"]:
            items[step["item_id"]]["hk_task_id"] = self.hk.add(step["fields"])
        for step in plan["binds"]:
            items[step["item_id"]]["hk_task_id"] = step["task_id"]
        for step in plan["updates"]:
            self.hk.tasks[step["task_id"]].update(copy.deepcopy(step["fields"]))
        for step in plan["meters"]:
            self.hk.tasks[step["task_id"]]["sensor"]["baseline"] = step["baseline"]
        for step in plan["consumables"]:
            self.hk.tasks[step["task_id"]]["source"]["parts"] = step["parts"]
        for step in plan["records"]:
            service = self.state["services"][step["service_id"]]
            service["hk_completions"][step["item_id"]] = dict(step["completion"])
        for step in plan["completes"]:
            fields = step["fields"]
            task = self.hk.tasks[fields["task_id"]]
            task["completions"].append({"ts": fields["completed_at"]})
            if "reading" in fields and task.get("sensor"):
                task["sensor"]["baseline"] = fields["reading"]
            service = self.state["services"][step["service_id"]]
            service["hk_completions"][step["item_id"]] = {
                "task_id": fields["task_id"],
                "ts": fields["completed_at"],
            }

    # ── Invariants ───────────────────────────────────────────────────────────

    def _wants(self, item: dict) -> bool:
        return (
            tp.desired_task(
                item,
                self.state["cars"][CAR],
                entity_id=ENTITY,
                device_id=DEVICE,
                date_limit=item.get("due_date"),
            )
            is not None
        )

    @invariant()
    def settles_fast(self) -> None:
        assert self.rounds <= 3

    @invariant()
    def one_task_for_each_job(self) -> None:
        by_item: dict[str, list[str]] = {}
        for task in self.hk.tasks.values():
            item_id = task["source"]["car_keeper"]["item_id"]
            by_item.setdefault(item_id, []).append(task["id"])
        for item_id, item in self.state["items"].items():
            if self._wants(item):
                assert by_item.get(item_id) == [item["hk_task_id"]]
            else:
                assert item_id not in by_item
        assert set(by_item) <= set(self.state["items"])

    @invariant()
    def fields_match(self) -> None:
        for item in self.state["items"].values():
            if not self._wants(item):
                continue
            task = self.hk.tasks[item["hk_task_id"]]
            want = tp.desired_task(
                item,
                self.state["cars"][CAR],
                entity_id=ENTITY,
                device_id=DEVICE,
                date_limit=item.get("due_date"),
            )
            assert want is not None
            for key in ("name", "recurrence_type", "device_id"):
                assert task.get(key) == want.get(key)
            # Home Keeper keeps the old interval of a task that is a sensor task now,
            # and does not read it.
            if "interval" in want:
                assert task.get("interval") == want["interval"]
            if "sensor" in want:
                for key in ("entity_id", "target", "also_every"):
                    assert task["sensor"].get(key) == want["sensor"].get(key)

    @invariant()
    def history_is_in_home_keeper(self) -> None:
        held: dict[str, set[str]] = {}
        for service in self.state["services"].values():
            for item_id in service["items"]:
                item = self.state["items"][item_id]
                if not self._wants(item):
                    continue
                done = service["hk_completions"][item_id]
                assert done["task_id"] == item["hk_task_id"]
                times = {c["ts"] for c in self.hk.tasks[done["task_id"]]["completions"]}
                assert done["ts"] in times
            for done in service["hk_completions"].values():
                held.setdefault(done["task_id"], set()).add(done["ts"])
        for task_id, task in self.hk.tasks.items():
            times = [c["ts"] for c in task["completions"]]
            assert len(times) == len(set(times)), "a task was completed 2 times"
            assert set(times) <= held.get(task_id, set())


ReconcileMachine.TestCase.settings = STATEFUL
TestReconcile = ReconcileMachine.TestCase
