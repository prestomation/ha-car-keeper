"""The pure model of the Car Keeper document.

The document has 1 section for each kind of record. Each record is a plain
JSON-serializable dict. :func:`normalize_state` runs on each load, so a new
section needs no migration step.

This module is pure. It imports no Home Assistant code. A function that needs the
time takes it from its caller.
"""

from __future__ import annotations

import re
from typing import Any

from .const import UNIT_KM, UNITS

# The sections of the document that hold records by id.
RECORD_SECTIONS = ("cars", "items", "services", "documents")


class CarKeeperError(Exception):
    """A user-facing error. ``key`` is in ``strings.json`` ``exceptions``."""

    def __init__(self, key: str, **placeholders: Any) -> None:
        super().__init__(key)
        self.key = key
        self.placeholders = {k: str(v) for k, v in placeholders.items()}


def default_settings() -> dict[str, Any]:
    """The settings of a new document."""
    return {"unit": UNIT_KM}


def empty_state() -> dict[str, Any]:
    """A new, empty document."""
    return {
        **{name: {} for name in RECORD_SECTIONS},
        "readings": {},
        "settings": default_settings(),
    }


def normalize_state(data: Any) -> dict[str, Any]:
    """The document *data* with each missing section added.

    A value of the wrong type is replaced with the empty value, so a damaged file
    loads as far as it can.
    """
    state = empty_state()
    if not isinstance(data, dict):
        return state
    for name in (*RECORD_SECTIONS, "readings"):
        value = data.get(name)
        if isinstance(value, dict):
            state[name] = value
    settings = data.get("settings")
    if isinstance(settings, dict):
        state["settings"] = {**state["settings"], **settings}
    if state["settings"].get("unit") not in UNITS:
        state["settings"]["unit"] = UNIT_KM
    return state


_VERSION = re.compile(r"v?(\d+(?:\.\d+)*)\.?(?:(a|b|rc|dev)(\d+))?")


def _version_key(version: str) -> tuple[tuple[int, ...], bool, int] | None:
    """The sort key of a version such as ``0.38.0b5``, or None if it is not one.

    A pre-release sorts below its release: ``0.35.0b1`` is below ``0.35.0``.
    """
    match = _VERSION.fullmatch(version.strip())
    if match is None:
        return None
    numbers = tuple(int(part) for part in match.group(1).split("."))
    # A longer pad sorts each pair the same way.
    numbers += (0,) * (3 - len(numbers))  # pragma: no mutate
    # The tag and its number are both there or both missing.
    if match.group(2) is None:  # pragma: no mutate
        # Only a pre-release compares the last number.
        return numbers, True, 0  # pragma: no mutate
    return numbers, False, int(match.group(3))


def version_at_least(version: str | None, minimum: str) -> bool:
    """Whether *version* is *minimum* or later.

    A pre-release of a later release passes: ``0.38.0b5`` is at least ``0.35.0``.
    A pre-release of *minimum* itself does not pass. A version that cannot be read
    passes, because then the check of the panel tab module decides.
    """
    have = _version_key(version) if version else None
    want = _version_key(minimum)
    if have is None or want is None:
        return True
    return have >= want
