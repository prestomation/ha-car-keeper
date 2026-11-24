"""The to-do list of each car: the jobs that are ``soon`` or ``overdue``.

A check of an item logs a service for that job, at today and the odometer of now.
That is ``log_service``, which every user can call, so every user can check an
item. The list has no other write: a new item, a rename and a delete come from the
jobs of the car.
"""

from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import CarKeeperConfigEntry
from .const import DOMAIN
from .coordinator import CarCoordinator
from .entity import CarEntity, async_track_cars
from .models import CarKeeperError
from .schedule import OK

PARALLEL_UPDATES = 0


class JobsTodoList(CarEntity, TodoListEntity):
    """The jobs of a car that are due."""

    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(self, coordinator: CarCoordinator, car_id: str) -> None:
        super().__init__(coordinator, car_id, "jobs")

    @property
    def todo_items(self) -> list[TodoItem]:
        """The jobs that are soon or overdue, the worst first."""
        summary = self.summary()
        items = self.coordinator.store.state["items"]
        out = []
        for item_id, evaluation in summary["items"].items():
            if evaluation["status"] == OK:
                continue
            item = items[item_id]
            out.append(
                TodoItem(
                    summary=item["name"],
                    uid=item_id,
                    status=TodoItemStatus.NEEDS_ACTION,
                    due=None,
                    description=item.get("notes") or None,
                )
            )
        return sorted(out, key=lambda t: str(t.summary).casefold())

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """A check logs a service for the job at today and the odometer of now."""
        if item.status != TodoItemStatus.COMPLETED:
            raise ServiceValidationError(
                translation_domain=DOMAIN, translation_key="todo_only_check"
            )
        car = self.car
        data = {
            "items": [item.uid],
            "reading": (car.get("odometer") or {}).get("value"),
        }
        try:
            await self.coordinator.store.log_service(self.car_id, data)
        except CarKeeperError as err:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key=err.key,
                translation_placeholders=err.placeholders,
            ) from err


async def async_setup_entry(
    hass: HomeAssistant,
    entry: CarKeeperConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add the to-do list of each car."""
    entry.async_on_unload(
        async_track_cars(
            hass,
            entry.runtime_data,
            async_add_entities,
            lambda coordinator, car_id: [JobsTodoList(coordinator, car_id)],
        )
    )
