import { describe, expect, it } from 'vitest';
import '../src/card-index.ts';
import { fakeHass, flush } from './fake-hass.js';

describe('garage card', () => {
  it('is in the card picker', () => {
    expect(window.customCards.map((c) => c.type)).toContain('car-keeper-garage-card');
  });

  it('shows the title and the empty state', async () => {
    const fake = fakeHass();
    const el = document.createElement('car-keeper-garage-card');
    el.setConfig({ type: 'custom:car-keeper-garage-card', title: 'Our <cars>' });
    document.body.appendChild(el);
    el.hass = fake.hass;
    await flush();
    expect(el.shadowRoot.querySelector('.ck-title').textContent).toBe('Our <cars>');
    expect(el.shadowRoot.querySelector('.ck-empty').textContent).toBe('No cars');
    expect(el.getCardSize()).toBe(2);
  });

  it('refuses an empty config', () => {
    const el = document.createElement('car-keeper-garage-card');
    expect(() => el.setConfig(null)).toThrow('The card configuration is not valid.');
  });
});
