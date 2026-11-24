#!/usr/bin/env bash
# Put the Python source of Home Keeper at the presets pin next to the unit tier.
#
# tests/unit/test_presets.py checks each car preset row with the validator of Home
# Keeper (preset_registry.build_registration). That code is pure, so the unit tier
# needs only the source: no build and no Home Assistant. The copy goes to
# tests/.home_keeper_validator/, which git ignores.
#
#   bash ci/fetch-home-keeper-validator.sh
#   CK_HK_VALIDATOR=tests/.home_keeper_validator/custom_components/home_keeper \
#     bash ci/test-python-unit.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=ci/home-keeper-presets.env
. "$ROOT/ci/home-keeper-presets.env"
REPO="${HOME_KEEPER_REPO:-https://github.com/prestomation/ha-home-keeper.git}"
DEST="$ROOT/tests/.home_keeper_validator"
rm -rf "$DEST"
git init --quiet "$DEST"
git -C "$DEST" fetch --quiet --depth 1 "$REPO" "$HOME_KEEPER_PRESETS_REF"
git -C "$DEST" checkout --quiet FETCH_HEAD
rm -rf "$DEST/.git"
echo "[home-keeper] validator source at $DEST ($HOME_KEEPER_PRESETS_REF)"
