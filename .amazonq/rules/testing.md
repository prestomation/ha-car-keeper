---
title: Testing rules
summary: Which test tier covers what, how to run each one, the fake and the real Home Keeper, the state machine tests, how to write a test that can fail, and the translation gates.
---

# Testing rules

Run the tests locally before you push. CI is not the test runner.

## Tiers and how to run them

Run the cheapest tier first.

| Tier | Where | Run |
|---|---|---|
| Unit (pure core) | `tests/unit` | `bash ci/test-python-unit.sh` |
| Component (in-process HA) | `tests/component` | `bash ci/test-python-component.sh` |
| Frontend | `tests/frontend`, `frontend/test` | `bash ci/test-frontend.sh` |
| Integration | `tests/integration` (Docker HA) | `bash ci/test-python-integration.sh` |
| Browser | `tests/e2e` (Playwright) | `bash ci/e2e-up.sh` |
| Noise budget | `tests/noise` (Docker HA) | `bash ci/test-noise.sh` |
| Upgrade | `tests/upgrade` (Docker HA, 2 boots) | `bash ci/test-upgrade.sh` |
| Mutation | the changed code | see [ci-and-ha-versions.md](ci-and-ha-versions.md#mutation-testing) |

- The unit tier needs only `pip install pytest PyYAML hypothesis`. It tests the pure core,
  the CI scripts, the docs tool, the backend strings and translation parity.
- The component tier runs a real Home Assistant through
  `pytest-homeassistant-custom-component`, with real registries and config entries and
  mocked I/O. It covers the config flow, setup and unload, every service with an admin
  and a non-admin user, the projections, the websocket commands, the entities and the
  Home Keeper sync. It also needs
  `home-assistant-frontend`, because the `frontend` dependency imports `hass_frontend` at
  setup. Its runner sets `asyncio_mode=auto`.
- `ci/setup-ci-deps.sh` installs everything into `.venv`. Run `source .venv/bin/activate`
  first.

### Home Keeper in the tests

- **The component tier uses a fake Home Keeper** in `tests/component/fake_home_keeper/`.
  It has the same service names, fields and events, and a copy of `panel_tabs.py`.
  `custom_components` is a namespace package, so the conftest puts the fake directory on
  `sys.path` and imports `custom_components` before Home Assistant starts.
- **The Docker and browser tiers use the real Home Keeper.** `ci/fetch-home-keeper.sh`
  copies it from `HOME_KEEPER_SRC`, or clones `HOME_KEEPER_REF`, into the git-ignored
  `tests/integration/.home_keeper/`, and `docker-compose.yml` mounts it. A test of the tab
  skips when that Home Keeper has no `panel_tabs.py`.
- A test that waits for the syncs uses
  `hass.async_block_till_done(wait_background_tasks=True)`. Keep each background task
  finite, or that call never returns.
- Other work can share the machine and port 8123. Wrap each local docker command in
  `flock /tmp/claude-0/docker.lock`, and give the compose project a name with `-p`.

### Blocking calls and the container log

- **The component tier runs `blockbuster`** (autouse, `tests/component/conftest.py`). It
  fails a test when a call with a frame of this integration in the stack blocks the event
  loop. It ignores Home Assistant's own blocking work. A blocking function goes through
  `hass.async_add_executor_job`. The unit tier has no event loop, so it has no such check.
- **`tests/integration/test_surfaces.py` touches each surface once**: diagnostics, every
  config and options flow step and every service. A new service needs a call there, or an
  entry in `VALIDATION_ONLY`.
- **The container runs in Python dev mode** (`docker-compose.yml`). The last step of each
  `integration.yml` lane runs `python ci/check-ha-log.py --domain car_keeper` on the
  saved log. Read the grouped report. Fix a real finding. For a message that a test causes
  on purpose, add a narrow regex and a reason to `ci/ha-log-allowlist.txt`. Never run the
  gate on a log that you have not read once.

### Pick the tier for "test against real HA"

- Home Assistant logic (store, coordinator, entities, services, events, config flow)
  goes in the **component** tier. It is real Home Assistant and about 100 times faster
  than Docker, and it can assert on internal state that REST cannot see.
- Keep the **Docker** tier for what the harness cannot do: serve the JS bundles, register
  the tab in a real Home Keeper and the card resource, and full-stack REST behavior.

### Tiers that must not share a pytest run

- **Component and Docker.** `pytest-homeassistant-custom-component` pulls in
  `pytest-socket`, which blocks the real network that the Docker tier needs. The
  component step installs the harness. The integration step does not, and its runner
  turns the socket plugins off.
- **Unit and component.** `tests/unit/conftest.py` installs stub parent packages for
  `custom_components.car_keeper`. In one pytest process, Home Assistant finds
  the stub and every component test fails with "No setup or config entry setup function
  defined". A job that wants both tiers (coverage) runs 2 invocations with
  `--cov-append`.
- `tests/unit/conftest.py` runs each pure module under its real dotted name
  (`custom_components.car_keeper.<mod>`) and registers `ex.<mod>` as an alias.
  Keep the real name: mutmut matches a mutant key to `__module__`. Keep the file in
  `tests/unit/`: as a root conftest its stubs would hide the real integration from the
  component tier.

## Noise budget

- **`tests/noise` counts what each action writes**: logbook rows, flips to unavailable,
  `car_keeper_*` events, store writes and entry reloads, against
  `tests/noise/baseline.json`. A probe integration (`tests/noise/ck_noise_probe`) counts
  them in the container.
- A pinned counter never changes in the update mode. Change a budget only on purpose:
  run `CK_NOISE_UPDATE=1 bash ci/test-noise.sh`, read the diff, and say why in the PR.
- A new service or a new sync gets a scenario.

## State machines

- **Each state machine is a pure transition function with a model test.** The odometer,
  the status of an item, a service visit, the reconcile with Home Keeper and the preset
  registration each have 1. A Hypothesis `RuleBasedStateMachine` drives the real function
  and a small model side by side, and checks the invariants after each step.
- **Test the fixed points.** A second reconcile with no change plans no step. An import of
  an export gives the same document.
- `CK_STATEFUL_EXAMPLES` sets the example count of the stateful tests. CI sets it high in
  `test.yml`. The default keeps a local run short.
- **A rule shared by Python and TypeScript has a golden corpus.** A Hypothesis test writes
  the cases to `tests/fixtures/shared/`, and a vitest test replays the same file. A change
  to a shared rule changes the corpus in the same commit. The registry of the shared rules
  is `tests/fixtures/shared/registry.json`.
- **A state machine of the tab has a fast-check model test**, as the refresh machine of
  Home Keeper has.

## Dependencies

- **A missing test dependency fails the run. It never skips.** Import every package in
  `requirements-test.txt` plainly, so a broken environment does not look like a choice.
- **A unit test that reads a repo file needs that file in `also_copy`** under
  `[tool.mutmut]`. mutmut runs the suite in a `mutants/` copy that holds only the source
  and the tests. The fault shows only on a PR that also changes mutable Python. List the
  directory: mutmut copies a bare file without its parent directory.
- A unit test that reads the component source skips inside `mutants/`, because the source
  there holds mutated strings.

## Writing a test that can fail

- **Test the shipped function, never a copy.**
- **Check that a new test can fail.** Mutate the line and watch it go red. A fake that can
  only produce the passing case reports coverage that the code does not have.
- **Pin a whole error message** with `raises_exactly` from `tests/unit/asserts.py`. A test
  that asserts only "something was raised" lets the wrong message ship.
- A round trip passes when a key has a wrong name on both sides. Pin the exact shape of
  each record and reply in `tests/unit/test_shapes.py`.
- **Test the open read.** Each read test runs as an admin and as a non-admin user, and
  asserts that the non-admin user gets every field, also the VIN, the plate and the cost.
- A known-broken contract gets `xfail(strict=True)`, never a weaker assertion.
- **A framework contract needs a Docker-tier assertion.** Device registry, entity
  registry, the panel tab API of Home Keeper and storage migration behavior are invisible
  to a test that fakes them.
- **Cross-version behavior needs an upgrade test.** `tests/upgrade` boots the oldest
  supported Home Assistant and Home Keeper on a seeded config dir, writes data, then boots
  the newer ones on the same dir. A change to the storage or the setup adds a check there.
- **Assert disappearance too.** Test a transition from both ends: present before, gone
  after.
- Never commit a real `.storage` dump with personal data. Build fixtures from synthetic
  data, and use each fixture in a test.

## The seeded fixture

- The Docker and browser tiers seed 2 config entries in
  `tests/integration/ha_config/.storage/core.config_entries`: Home Keeper and Car Keeper.
  Both load at Home Assistant startup. That is what puts the card resource into the
  served pages and the tab into the Home Keeper panel.
- Home Assistant writes to that file at run time. After a local run, restore it with
  `git checkout`. Git ignores the rest of `.storage/`.
  `tests/unit/test_integration_fixture_clean.py` fails when a key that a run wrote
  reaches git, because a dirty fixture passes locally and fails on a clean checkout.

## Browser tests

- Auth and onboarding are in `tests/e2e/global-setup.ts`. Specs share its saved state.
- **A spec owns what it creates.** Delete created records after the test, and give
  fixtures stable names, never a `Date.now()` suffix.
- The card can load after the dashboard renders, so `openCard` in
  `tests/e2e/tests/helpers.ts` retries with a reload. Keep the retry
  ([frontend.md](frontend.md#bundles-and-the-cards)).
- 1 module of the e2e harness writes the widths (`DESKTOP`, `PHONE`). No other file
  writes a width.
- Measure layout by relations (A is above B), never by coordinates. Assert that a list is
  not empty before you loop over it.
- A capture is documentation. Each surface that a capture shows needs an assertion in
  `tests/e2e/tests/` ([pr-workflow.md](pr-workflow.md#screenshots-desktop-and-phone)).

## Translations

`strings.json`, `backend_strings/en.json` and `frontend/src/locales/en.json` are the
sources. `tests/unit/test_translations_parity.py`, `tests/unit/test_backend_i18n.py` and
`frontend/test/i18n-parity.test.js` enforce for each of the 16 locales that are not English:

- the same keys as English, and the same `{token}` placeholders per key;
- no value identical to English, except the global `_INTENTIONALLY_IDENTICAL` list and a
  per-locale `_COGNATE_IDENTICAL` list of reviewed cognates;
- for the frontend, that every `t()` and `tn()` key exists, that each `tn()` base has an
  `.other` form, and that no key is unused.

Add a string to a locale only as a translation or as a reviewed cognate.
`python3 ci/i18n-coverage.py` prints coverage for information only. The 17 languages are
`const.LANGUAGES`, the same as Home Keeper.
