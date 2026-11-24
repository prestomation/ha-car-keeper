import { afterEach, describe, expect, it } from 'vitest';
import { formatDate, formatMoney, formatNumber, getLanguage, setLanguage, t, tn } from '../src/i18n.ts';
import { DEFAULT_LOCALE, LOCALES } from '../src/locales/index.ts';

// Behaviour of the i18n module. The translation gates (parity, leaks, key usage)
// are in `i18n-parity.test.js`, which the mutation run skips.

afterEach(() => setLanguage(DEFAULT_LOCALE));

/** Run *body* with extra keys in a locale table, then remove them. */
function withKeys(keys, body, locale = DEFAULT_LOCALE) {
  const table = LOCALES[locale];
  try {
    Object.assign(table, keys);
    body();
  } finally {
    for (const key of Object.keys(keys)) delete table[key];
  }
}

describe('setLanguage', () => {
  it('finds an exact tag, also a regional one', () => {
    setLanguage('pt-BR');
    expect(getLanguage()).toBe('pt-BR');
    setLanguage('zh_Hans');
    expect(getLanguage()).toBe('zh-Hans');
    setLanguage('UK');
    expect(getLanguage()).toBe('uk');
  });
  it('falls back to the base language, then to English', () => {
    setLanguage('de-AT');
    expect(getLanguage()).toBe('de');
    setLanguage('xx-YY');
    expect(getLanguage()).toBe('en');
    setLanguage('de');
    setLanguage(undefined);
    expect(getLanguage()).toBe('en');
  });
  it('uses the table of the language', () => {
    setLanguage('de');
    expect(t('garage.empty_title')).toBe('Keine Autos');
  });
});

describe('t and tn', () => {
  it('fills tokens, keeps unknown tokens, and falls back to the key', () => {
    withKeys({ 'tmp.x': '{a} and {b}' }, () => {
      expect(t('tmp.x', { a: 1 })).toBe('1 and {b}');
    });
    expect(t('tmp.none')).toBe('tmp.none');
  });
  it('falls back to English for a key that a language does not have', () => {
    withKeys({ 'tmp.only_en': 'English' }, () => {
      setLanguage('fr');
      expect(t('tmp.only_en')).toBe('English');
    });
  });
  it('picks the plural form', () => {
    withKeys({ 'tmp.n.one': '{n} car', 'tmp.n.other': '{n} cars' }, () => {
      expect(tn('tmp.n', 1)).toBe('1 car');
      expect(tn('tmp.n', 2)).toBe('2 cars');
    });
    expect(tn('tmp.missing', 2)).toBe('tmp.missing');
  });
});

describe('formatters', () => {
  it('formats a date, and gives an empty string for a bad value', () => {
    expect(formatDate('2026-03-04')).toBe('Mar 4, 2026');
    expect(formatDate('2026-03-04', false)).toBe('Mar 4');
    expect(formatDate('nope')).toBe('');
    expect(formatDate(null)).toBe('');
  });
  it('formats money and numbers', () => {
    expect(formatMoney(12.5, 'USD')).toBe('$12.50');
    expect(formatMoney(null, 'USD')).toBe('');
    expect(formatMoney(3, 'NOPE!')).toBe('3 NOPE!');
    expect(formatNumber(12345)).toBe('12,345');
  });
});
