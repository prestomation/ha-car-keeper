---
title: Repository, tests and CI
summary: How the repository starts from the integration template, and which rules, test tiers, CI jobs and guardrails come from the Library.
status: planned
implements:
  - pyproject.toml
  - ci/*
  - .github/workflows/*
  - tests/**
related: [architecture, frontend]
---

# Repository, tests and CI

Car Keeper follows the Library in its rules, its test tiers, its CI, its docs and its release
flow. This doc says where each part comes from, so that the first code PR is a known list of
steps.

## Goals

- **G1. Same rules as the Library.** A contributor who knows Home Keeper or the Library finds the
  same gates here.
- **G2. Every tier from the first PR.** The unit, component, Docker and browser tiers run before
  the first feature is written.
- **G3. Real Home Keeper in the tests.** The Docker and browser tiers run against a real Home
  Keeper, at its `main` and at the minimum version.

## Non-goals

- A new test or docs tool. The tools of the template and the Library are copied, not written
  again.
- A website before the first release.

## Design

### Scaffold

1. Copy [ha-integration-template](https://github.com/prestomation/ha-integration-template) into
   the repository.
2. Run `python scripts/rename.py car_keeper "Car Keeper" --prefix ck --repo
   prestomation/ha-car-keeper`. It renames the domain, the element names, the CSS prefix and the
   URLs, and stamps the design docs.
3. Remove the example panel of the template, because the admin UI is a tab. Keep its card
   delivery.
4. Copy from the Library the parts that the template does not have: `home_keeper.py` with the
   check and the repair issues, `tests/component/fake_home_keeper`, `ci/fetch-home-keeper.sh`, the
   seeded Home Keeper config entry of the Docker tier, and the tab host stub of the browser tier.
5. Replace this design set's `status: planned` lines with the `source_hash` that `ci/docs.py
   stamp` writes, as each file is built.

### Rules and docs

`AGENTS.md`, `CLAUDE.md`, `RELEASE.md`, `IDEAS.md` and the 9 files of `.amazonq/rules/` come from
the Library, with the domain and the names changed: writing style (ASD-STE100) and glossary, PR
workflow, CHANGELOG and release, testing, CI and Home Assistant versions, architecture, services
and events, frontend, and dev docs. `ci/docs.py` keeps the caps: design 150 lines, reference 300,
rules 200, and 100 characters a prose line. The glossary gets the terms of this project: car, job,
service, reading, odometer, limit, warning window.

### Test tiers

| Tier | Where | What it runs |
|---|---|---|
| Unit | `tests/unit` | The pure core with plain values: the due rule, units, readings, projections, the planner, import and export. Hypothesis for the due rule and the unit round trip. |
| Component | `tests/component` | Home Assistant in process with the fake Home Keeper: setup, config flow, each service as admin and as a user, events, entities, the sync both ways with no loop. `blockbuster` fails a blocking call. |
| Integration | `tests/integration` | Docker, a real Home Assistant and the real Home Keeper: the lifecycle, the surfaces, the repair issue, and the Home Assistant log gate. |
| Frontend unit | `frontend/test` with vitest | Views as pure functions in jsdom, the due rule against the shared fixtures, locale parity. |
| Browser | `tests/e2e` with Playwright | The tab inside the real Home Keeper panel, and the cards, at desktop and phone width. Screenshots for `docs/images/` and the walkthrough capture. |

The component tier and the Docker tier never share a pytest run.

### CI workflows

From the Library, with the same names: `lint.yml` (ruff, strict mypy, vale, `docs-audit`),
`test.yml` (unit, component, frontend, hassfest, the oldest Home Assistant), `integration.yml`,
`e2e.yml`, `mutation.yml`, `pytest_coverage.yml`, `hacs.yml`, `preview-release.yml`,
`release.yml`, `walkthrough-preview.yml`, `docs-preview.yml`, `docs-deploy.yml` and the nightly
`ha-beta.yml`.

### Guardrails to copy

| Guardrail | What it catches here |
|---|---|
| Mutation gate at 80% on changed code | A test of the due rule that asserts nothing. `only_mutate` lists the pure modules. |
| Pure core test | A Home Assistant import in `schedule.py`, `units.py` or another pure module. |
| API-surface drift | A service, event, entity or view that is not in `api_surface.py`. |
| Exact shapes | A record key that changes name on 1 side of a round trip. |
| Translation parity | A missing key or a different placeholder in 1 of the 17 languages. |
| Localized exceptions | A user-facing error with no `translation_key`. |
| Projection tests | A private field in a reply for a user who is not an admin. This guardrail is new: 1 test walks every reply and every event payload for the VIN and the plate of a seeded car. |
| Home Assistant log gate | A warning from `custom_components.car_keeper` in the Docker tier. |
| CHANGELOG release gap, release consistency, publish gate | A version, a CHANGELOG section and a tag that disagree. |
| Pinned actions | A third-party action that is not pinned in a job that can write. |
| Docs audit | A design doc that no longer matches its code, or a file that no doc covers. |

### Release flow

As the Library: betas use the next release number, a feature PR bumps `manifest.json` and
`PANEL_VERSION` and has the `preview-release` label, and `release.yml` builds `car_keeper.zip` for
HACS. `hacs.json` sets `zip_release` and the minimum Home Assistant version of Home Keeper.

## Trade-offs

- **Template first, then Library parts** over **a copy of the Library**: the template has the
  current CI and no book code to remove. The cost is step 4.
- **The real Home Keeper in 2 tiers** over **the fake only**: the sync depends on the behavior of
  Home Keeper, and a fake cannot show a change there.

## One-way doors

- The repository layout that HACS reads: `custom_components/car_keeper/`, `hacs.json` and the zip
  name.
- The minimum Home Assistant version in `hacs.json`.
