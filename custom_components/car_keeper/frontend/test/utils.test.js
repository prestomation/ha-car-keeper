import { describe, expect, it } from 'vitest';
import { buildPath, escapeHTML, parseRoute } from '../src/utils.ts';

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
  it('opens the garage for an empty or unknown path', () => {
    expect(parseRoute('')).toEqual({ view: 'garage', params: {} });
    expect(parseRoute('/nope')).toEqual({ view: 'garage', params: {} });
  });
  it('reads the view and the parameters', () => {
    expect(parseRoute('/settings;a=1;b=x%20y')).toEqual({ view: 'settings', params: { a: '1', b: 'x y' } });
    expect(parseRoute('/garage;=x;bad;k=')).toEqual({ view: 'garage', params: { k: '' } });
    expect(parseRoute('/settings/?q=1')).toEqual({ view: 'settings', params: {} });
  });
  it('builds a path with sorted parameters and no empty value', () => {
    expect(buildPath({ view: 'garage', params: { b: '2', a: 'x y', c: '' } })).toBe('/garage;a=x%20y;b=2');
  });
  it('round-trips', () => {
    const route = { view: 'settings', params: { status: 'overdue', q: 'a;b=c' } };
    expect(parseRoute(buildPath(route))).toEqual(route);
  });
});
