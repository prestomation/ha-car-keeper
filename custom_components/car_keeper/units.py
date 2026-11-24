"""Distance units: km, miles and metres.

Each value of a car is in the unit of that car. A value from a sensor comes in the
unit of the sensor, and :func:`convert` puts it in the unit of the car. A change of
the unit of a car converts each stored value 1 time (``readings.change_unit``).

``frontend/src/units.ts`` is the same rule in TypeScript. The golden corpus
``tests/fixtures/shared/units.json`` holds the 2 copies together.

This module is pure. It imports no Home Assistant code.
"""

from __future__ import annotations

import math

from .const import UNIT_KM, UNIT_MI

#: The length of 1 unit, in metres.
METRES: dict[str, float] = {UNIT_KM: 1000.0, UNIT_MI: 1609.344, "m": 1.0}

#: The default warning window of a new car, in the unit of the car.
DEFAULT_LEAD_DISTANCE: dict[str, int] = {UNIT_KM: 1000, UNIT_MI: 600}
DEFAULT_LEAD_DAYS = 30


def known(unit: str | None) -> bool:
    """Whether Car Keeper can read a distance in *unit*."""
    return unit in METRES


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """*value* in *from_unit*, as a value in *to_unit*.

    Raise ``ValueError`` for a unit that Car Keeper cannot read.
    """
    if from_unit not in METRES or to_unit not in METRES:
        raise ValueError(f"unknown unit {from_unit!r} or {to_unit!r}")
    if from_unit == to_unit:
        return float(value)
    return float(value) * METRES[from_unit] / METRES[to_unit]


# The rounding is half up, with the same float operations as ``units.ts``. Python
# ``round`` rounds half to even, and JavaScript ``Math.round`` does not, so neither
# is used here.


def round_reading(value: float) -> float:
    """An odometer value, rounded to 1 decimal."""
    return math.floor(float(value) * 10 + 0.5) / 10


def round_interval(value: float) -> int:
    """A distance interval or a warning window, rounded to a whole unit."""
    return math.floor(float(value) + 0.5)


def round_template(value: float) -> int:
    """A starter interval in the unit of the car, rounded to 100."""
    return math.floor(float(value) / 100 + 0.5) * 100


def group_digits(value: float) -> str:
    """A whole number with a comma between each group of 3 digits: ``15,000``.

    The tab, the cards and the Home Keeper task names show an interval this way.
    """
    number = round_interval(value)
    sign = "-" if number < 0 else ""
    digits = str(abs(number))
    groups: list[str] = []
    while len(digits) > 3:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    groups.insert(0, digits)
    return sign + ",".join(groups)
