// Distance units: km, miles and metres. The same rule as `units.py`. The golden
// corpus `tests/fixtures/shared/units.json` holds the 2 copies together.

/** The length of 1 unit, in metres. */
export const METRES: Record<string, number> = { km: 1000, mi: 1609.344, m: 1 };

/** Whether Car Keeper can read a distance in *unit*. */
export function known(unit: string | null | undefined): boolean {
  return unit != null && unit in METRES;
}

/** *value* in *from*, as a value in *to*. Throws for a unit it cannot read. */
export function convert(value: number, from: string, to: string): number {
  if (!known(from) || !known(to)) throw new Error(`unknown unit ${from} or ${to}`);
  if (from === to) return value;
  return (value * METRES[from]) / METRES[to];
}

// The rounding is half up, with the same float operations as `units.py`.

/** An odometer value, rounded to 1 decimal. */
export function roundReading(value: number): number {
  return Math.floor(value * 10 + 0.5) / 10;
}

/** A distance interval or a warning window, rounded to a whole unit. */
export function roundInterval(value: number): number {
  return Math.floor(value + 0.5);
}

/** A starter interval in the unit of a car, rounded to 100. */
export function roundTemplate(value: number): number {
  return Math.floor(value / 100 + 0.5) * 100;
}

/** A whole number with a comma between each group of 3 digits: "15,000". */
export function groupDigits(value: number): string {
  const n = roundInterval(value);
  const sign = n < 0 ? '-' : '';
  let digits = String(Math.abs(n));
  const groups: string[] = [];
  while (digits.length > 3) {
    groups.unshift(digits.slice(-3));
    digits = digits.slice(0, -3);
  }
  groups.unshift(digits);
  return sign + groups.join(',');
}
