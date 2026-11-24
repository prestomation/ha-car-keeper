"""The pure model of the Car Keeper document.

The document has 1 section for each kind of record. Each record is a plain
JSON-serializable dict. :func:`normalize_state` runs on each load, so a new
section needs no migration step.

This module is pure. It imports no Home Assistant code. A function that needs the
time takes it from its caller.
"""

from __future__ import annotations

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


def _version_key(version: str) -> tuple[tuple[int, ...], int, int] | None:
    """The sort key of a version such as ``0.38.0b5``, or None if it is not one.

    A pre-release sorts below its release: ``0.35.0b1`` is below ``0.35.0``.
    """
    head = version.strip().lstrip("v")
    release = ""
    for index, char in enumerate(head):
        if not (char.isdigit() or char == "."):
            release, rest = head[:index], head[index:]
            break
    else:
        release, rest = head, ""
    release = release.rstrip(".")
    parts = release.split(".")
    if not release or not all(part.isdigit() for part in parts):
        return None
    numbers = tuple(int(part) for part in parts)
    numbers += (0,) * (3 - len(numbers))
    if not rest:
        return numbers, 1, 0
    tag = rest.lstrip(".-")
    for prefix in ("a", "b", "rc", "dev"):
        if tag.startswith(prefix) and tag[len(prefix) :].isdigit():
            return numbers, 0, int(tag[len(prefix) :])
    return None


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
