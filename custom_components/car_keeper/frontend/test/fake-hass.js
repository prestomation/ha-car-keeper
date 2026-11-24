// A fake `hass` for the DOM tests. `connection.sendMessagePromise` answers from a
// copy of `fixtures/state.json`, and `subscribeMessage` keeps the callback so a
// test can push a `changed` message.
import { vi } from 'vitest';
import FIXTURE from './fixtures/state.json';

export function fixture() {
  return structuredClone(FIXTURE);
}

export function fakeHass({ state = fixture(), replies = {}, language = 'en' } = {}) {
  const subs = [];
  const send = vi.fn(async (msg) => {
    const cmd = msg.type.replace('car_keeper/', '');
    if (cmd in replies) {
      const r = replies[cmd];
      return typeof r === 'function' ? r(msg) : r;
    }
    if (cmd === 'get_state') return structuredClone(state);
    return {};
  });
  const hass = {
    language,
    states: {},
    connection: {
      sendMessagePromise: send,
      subscribeMessage: vi.fn(async (cb, msg) => {
        subs.push({ cb, msg });
        return () => undefined;
      }),
    },
  };
  return {
    hass,
    send,
    state,
    subs,
    push: () => subs.forEach((s) => s.cb({ type: 'changed', revision: 2 })),
    calls: (cmd) => send.mock.calls.map((c) => c[0]).filter((m) => m.type === `car_keeper/${cmd}`),
  };
}

/** Let pending promises and timers of 0 ms run. */
export async function flush(times = 6) {
  for (let i = 0; i < times; i++) await new Promise((r) => setTimeout(r, 0));
}
