"""State machine test: the registration of the car presets in Home Keeper.

The model has a fake Home Keeper with a memory registry, as the real one has, and a
queue of calls, because the real calls run later in a background task. The rules
start and stop Car Keeper, add and remove the Home Keeper service, let Home Keeper
ask its companions, refuse the next call, and run the oldest call.

The invariants, when the queue is empty:

- Car Keeper runs, Home Keeper has the service and the last call passed: Home Keeper
  holds the presets of Car Keeper, and Car Keeper knows their ids.
- Car Keeper does not run: Home Keeper holds no preset of Car Keeper.
- Home Keeper has no service: the status is ``no_service`` and nothing is registered.
"""

from __future__ import annotations

import ex.presets as presets
from hypothesis.stateful import RuleBasedStateMachine, invariant, precondition, rule
from stateful import STATEFUL

COMPANION = "car_keeper"


class FakeHomeKeeper:
    """The preset registry of Home Keeper, as far as Car Keeper uses it."""

    def __init__(self) -> None:
        self.service = False
        self.registry: dict[str, list[str]] = {}
        self.refuse_next = False
        self.calls = 0

    def register(self, data: dict) -> list[str]:
        self.calls += 1
        if self.refuse_next:
            self.refuse_next = False
            raise ValueError("rows[0]: refused")
        ids = presets.preset_ids(data["rows"], data["domain"])
        self.registry[data["domain"]] = ids
        return ids

    def unregister(self, domain: str) -> None:
        self.calls += 1
        self.registry.pop(domain, None)


class PresetMachine(RuleBasedStateMachine):
    def __init__(self) -> None:
        super().__init__()
        self.hk = FakeHomeKeeper()
        self.link = presets.Link()
        self.queue: list[str] = []
        self.last_refused = False

    def feed(self, event: presets.Event) -> None:
        self.link, call = presets.transition(self.link, event)
        if call is not None:
            self.queue.append(call)

    @rule()
    def start(self) -> None:
        if not self.link.running:
            self.feed(presets.Event("start"))

    @rule()
    def stop(self) -> None:
        if self.link.running:
            self.feed(presets.Event("stop"))

    @rule()
    def add_service(self) -> None:
        if not self.hk.service:
            self.hk.service = True
            self.feed(presets.Event("service_added"))

    @rule()
    def remove_service(self) -> None:
        if self.hk.service:
            self.hk.service = False
            self.feed(presets.Event("service_removed"))

    @rule()
    def home_keeper_asks(self) -> None:
        self.feed(presets.Event("ask"))

    @rule()
    def refuse_next_call(self) -> None:
        self.hk.refuse_next = True

    @precondition(lambda self: bool(self.queue))
    @rule()
    def run_oldest_call(self) -> None:
        self.queue.pop(0)
        # As PresetSync._run: the service first, then the state now decides, not the
        # call that queued the run.
        if not self.hk.service:
            return
        if not self.link.running:
            self.hk.unregister(COMPANION)
            return
        try:
            ids = self.hk.register(presets.registration(COMPANION))
        except ValueError as err:
            self.last_refused = True
            self.feed(presets.Event("refused", error=str(err)))
            return
        self.last_refused = False
        self.feed(presets.Event("accepted", preset_ids=tuple(ids)))

    def settled(self) -> bool:
        return not self.queue

    @invariant()
    def a_running_car_keeper_is_registered(self) -> None:
        if not self.settled() or not (self.link.running and self.hk.service):
            return
        if self.last_refused:
            assert presets.status(self.link) == presets.STATUS_FAILED
            return
        expected = presets.preset_ids(presets.ROWS, COMPANION)
        assert self.hk.registry.get(COMPANION) == expected
        assert list(self.link.preset_ids) == expected
        assert presets.status(self.link) == presets.STATUS_REGISTERED

    @invariant()
    def a_stopped_car_keeper_leaves_nothing(self) -> None:
        if self.settled() and not self.link.running and self.hk.service:
            assert COMPANION not in self.hk.registry
        if not self.link.running:
            assert not self.link.registered

    @invariant()
    def no_service_means_nothing_registered(self) -> None:
        if not self.hk.service:
            assert not self.link.registered
            assert presets.status(self.link) == presets.STATUS_NO_SERVICE


PresetMachine.TestCase.settings = STATEFUL
TestPresets = PresetMachine.TestCase
