import { describe, expect, it } from 'vitest';
import '../src/tab-index.ts';
import { fakeHass, fixture, flush } from './fake-hass.js';

function mount(opts) {
  const fake = fakeHass(opts);
  const el = document.createElement('home-keeper-cars-tab');
  document.body.appendChild(el);
  el.host = { apiVersion: 1, navigate: () => undefined, showToast: () => undefined };
  el.route = { path: '' };
  el.hass = fake.hass;
  return { el, fake };
}

describe('Cars tab', () => {
  it('shows the empty garage', async () => {
    const { el } = mount();
    await flush();
    expect(el.shadowRoot.querySelector('.ck-empty h2').textContent).toBe('No cars');
  });

  it('loads again after a change message', async () => {
    const { fake } = mount();
    await flush();
    fake.push();
    await flush();
    expect(fake.calls('get_state').length).toBe(2);
  });

  it('shows the error of a failed read', async () => {
    const { el } = mount({ replies: { get_state: () => Promise.reject(new Error('boom <b>')) } });
    await flush();
    const alert = el.shadowRoot.querySelector('[role="alert"]');
    expect(alert.textContent).toContain('boom <b>');
    expect(alert.querySelector('b')).toBeNull();
  });

  it('renders the garage view of a document with cars', async () => {
    const state = fixture();
    state.cars = { c1: { id: 'c1', name: 'Civic' } };
    const { el } = mount({ state });
    await flush();
    expect(el.shadowRoot.querySelector('[data-view="garage"]')).not.toBeNull();
  });
});
