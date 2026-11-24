import { readdirSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { describe, expect, it } from 'vitest';
import { scan } from './destructive-scan-lib.js';

// Every call of a function that deletes, removes or replaces data must sit under a
// confirmation (`confirmDestructive`). A new delete button that calls the action at
// once fails this test. The rule is the same as in Home Keeper.
//
// It reads `src/*.ts` as text, so it is a `*-parity` test and the mutation run skips
// it (see `vitest.stryker.config.js`). `destructive-scan-lib.test.js` tests the
// scanner itself on small snippets.

// A call that is allowed to run without a question. The key is
// `file::function that holds the call::callee`. Each entry says why, and an entry
// that no call needs any more fails the test, so this list cannot collect dead names.
const ALLOW = {};

const SRC = resolve(__dirname, '../src');
const files = readdirSync(SRC)
  .filter((f) => f.endsWith('.ts'))
  .map((name) => ({ name, source: readFileSync(resolve(SRC, name), 'utf8') }));

describe('destructive actions are confirmed', () => {
  const { violations, stale } = scan(files, ALLOW);

  it('has no call that runs a delete without a confirmation', () => {
    const lines = violations.map((v) => `${v.file}:${v.line} ${v.where} calls ${v.callee}`);
    expect(lines, 'wrap it in confirmDestructive(...), or add a reasoned ALLOW entry').toEqual([]);
  });

  it('has no allowlist entry that nothing needs', () => {
    expect(stale).toEqual([]);
  });

  it('gives every allowlist entry a real reason', () => {
    for (const [key, reason] of Object.entries(ALLOW)) {
      expect(reason.length, key).toBeGreaterThan(40);
    }
  });

  it('keeps every destructive websocket command inside api.ts', () => {
    // A direct `sendMessagePromise({ type: 'car_keeper/delete_...' })` would bypass the
    // names that the scan follows. The tab calls the helpers of `api.ts`.
    const direct = files
      .filter((f) => f.name !== 'api.ts')
      .filter((f) => /['"`]car_keeper\/(delete_|remove_|import_data)/.test(f.source))
      .map((f) => f.name);
    expect(direct).toEqual([]);
  });
});
