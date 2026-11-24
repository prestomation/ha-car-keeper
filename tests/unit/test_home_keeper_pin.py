"""The Home Keeper presets pin is the same in each place that uses it.

``ci/home-keeper-presets.env`` holds the commit. The workflows cannot read that file
in a matrix or in a top-level ``env``, so they repeat the SHA. This test keeps them
equal, and makes sure that no lane runs a branch where it needs the presets.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def _pin() -> str:
    text = (ROOT / "ci" / "home-keeper-presets.env").read_text(encoding="utf-8")
    match = re.search(r"^HOME_KEEPER_PRESETS_REF=([0-9a-f]{40})$", text, re.M)
    assert match, "ci/home-keeper-presets.env must hold a full commit SHA"
    return match.group(1)


def test_every_pinned_lane_uses_the_same_commit() -> None:
    pin = _pin()
    shas = set()
    for path in WORKFLOWS.glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        shas.update(
            re.findall(r"(?:HOME_KEEPER_REF|home_keeper): ([0-9a-f]{40})", text)
        )
    assert shas == {pin}


def test_the_lanes_that_expect_presets_run_the_pin() -> None:
    pin = _pin()
    for name in ("e2e.yml", "walkthrough-preview.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert f"HOME_KEEPER_REF: {pin}" in text, name
        assert 'CK_EXPECT_PRESETS: "1"' in text, name
    integration = (WORKFLOWS / "integration.yml").read_text(encoding="utf-8")
    assert f'home_keeper: {pin}\n            presets: "1"' in integration
    assert 'home_keeper: v0.35.0\n            presets: "0"' in integration


def test_the_upgrade_tier_reads_the_pin() -> None:
    script = (ROOT / "ci" / "test-upgrade.sh").read_text(encoding="utf-8")
    assert '. "$ROOT/ci/home-keeper-presets.env"' in script
    assert "HK_NEW_REF:-$HOME_KEEPER_PRESETS_REF" in script
