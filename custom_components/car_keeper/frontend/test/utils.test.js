import { describe, expect, it } from 'vitest';
import { buildPath, escapeHTML, parseRoute, routeTo } from '../src/utils.ts';

describe('escapeHTML', () => {
  it('escapes each special character', () => {
    expect(escapeHTML(`<a href="x">'&'</a>`)).toBe('&lt;a href=&quot;x&quot;&gt;&#39;&amp;&#39;&lt;/a&gt;');
  });
  it('turns null and undefined into an empty string', () => {
    expect(escapeHTML(null)).toBe('');
    expect(escapeHTML(undefined)).toBe('');
    expect(escapeHTML(0)).toBe('0');
  });
});

describe('parseRoute and buildPath', () => {
  const r = (view, id = '', log = false, params = {}) => ({ view, id, log, params });

  it('opens the garage for an empty or unknown path', () => {
    expect(parseRoute('')).toEqual(r('garage'));
    expect(parseRoute('/nope')).toEqual(r('garage'));
    expect(parseRoute('/car')).toEqual(r('garage'));
    expect(parseRoute('/car/a/b/c')).toEqual(r('garage'));
    expect(parseRoute('/add/x')).toEqual(r('garage'));
    expect(parseRoute(undefined)).toEqual(r('garage'));
  });

  it('reads each view, the car and the Log dialog', () => {
    expect(parseRoute('/add')).toEqual(r('add'));
    expect(parseRoute('/settings/?q=1')).toEqual(r('settings'));
    expect(parseRoute('/car/c%201')).toEqual(r('car', 'c 1'));
    expect(parseRoute('/car/c1/log')).toEqual(r('car', 'c1', true));
    expect(parseRoute('/car/c1/other')).toEqual(r('car', 'c1', false));
  });

  it('reads the parameters', () => {
    expect(parseRoute('/settings;a=1;b=x%20y')).toEqual(r('settings', '', false, { a: '1', b: 'x y' }));
    expect(parseRoute('/;=x;bad;k=')).toEqual(r('garage', '', false, { k: '' }));
  });

  it('builds a path with sorted parameters and no empty value', () => {
    expect(buildPath(r('garage', '', false, { b: '2', a: 'x y', c: '' }))).toBe('/;a=x%20y;b=2');
    expect(buildPath(r('garage'))).toBe('/');
    expect(buildPath(r('settings'))).toBe('/settings');
    expect(buildPath(r('car', 'c 1', true))).toBe('/car/c%201/log');
    expect(buildPath(routeTo('car', 'c1'))).toBe('/car/c1');
  });

  it('round-trips', () => {
    for (const route of [
      r('garage'),
      r('add'),
      r('settings', '', false, { a: '1' }),
      r('car', 'x/y', false),
      r('car', 'c1', true, { k: 'v' }),
    ]) {
      expect(parseRoute(buildPath(route))).toEqual(route);
    }
  });
});
