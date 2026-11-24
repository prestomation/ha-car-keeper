"""The pure payload builders of the Car Keeper bus events.

Each event is ``car_keeper_<noun>_<verb>``. The store fires it after the save,
so a change from the tab, a service or a Home Keeper task fires the same event.
Every user can listen to the bus, and every read is open to every user, so a
payload can hold each value of a record. A payload copies each list, so a caller
never aliases the stored document.

This module is pure. It imports no Home Assistant code.
"""

from __future__ import annotations

from typing import Any


def settings_event_data(
    changed_fields: list[str], origin: str | None
) -> dict[str, Any]:
    """The payload of ``settings_updated``."""
    return {"changed_fields": list(changed_fields), "origin": origin}
