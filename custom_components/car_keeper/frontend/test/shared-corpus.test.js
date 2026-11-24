import { describe, expect, it } from 'vitest';
import REGISTRY from '../../../../tests/fixtures/shared/registry.json';
import SCHEDULE from '../../../../tests/fixtures/shared/schedule.json';
import UNITS from '../../../../tests/fixtures/shared/units.json';
import { addMonths, dailyDistance, evaluate } from '../src/schedule.ts';
import { convert, groupDigits, roundInterval, roundReading, roundTemplate } from '../src/units.ts';

// The golden corpus: the Python tests write each case with the output of the Python
// code (tests/unit/shared_corpus.py). This file replays the same cases against the
// TypeScript copy, so the 2 copies of a shared rule cannot drift apart.

describe('the registry of shared rules', () => {
  it('names this file for each rule', () => {
    expect(REGISTRY.rules.map((r) => r.name).sort()).toEqual(['schedule', 'units']);
    for (const rule of REGISTRY.rules) expect(rule.vitest).toBe('custom_components/car_keeper/frontend/test/shared-corpus.test.js');
  });
});

describe('units corpus', () => {
  it('has cases', () => expect(UNITS.length).toBeGreaterThan(50));
  it.each(UNITS)('$value $from -> $to', (c) => {
    const converted = convert(c.value, c.from, c.to);
    expect(converted).toBe(c.converted);
    expect(roundReading(converted)).toBe(c.reading);
    expect(roundInterval(converted)).toBe(c.interval);
    expect(roundTemplate(converted)).toBe(c.template);
    expect(groupDigits(converted)).toBe(c.grouped);
  });
});

describe('schedule corpus', () => {
  const [corpus] = SCHEDULE;
  it('has cases', () => expect(corpus.evaluate.length).toBeGreaterThan(100));
  it('evaluate gives the same limits and status', () => {
    for (const c of corpus.evaluate) {
      const got = evaluate(c.item, c.odometer, c.daily, c.today, c.lead_distance, c.lead_days);
      expect(got, JSON.stringify(c)).toEqual(c.out);
    }
  });
  it('dailyDistance gives the same value', () => {
    for (const c of corpus.daily_distance) expect(dailyDistance(c.readings, c.today)).toBe(c.out);
  });
  it('addMonths gives the same date', () => {
    for (const c of corpus.add_months) expect(addMonths(c.date, c.months)).toBe(c.out);
  });
});
