#!/usr/bin/env bash
# The upgrade tier (tests/upgrade). It copies the oldest supported Home Keeper and
# the newest one, then runs the 2-phase upgrade test: the oldest Home Assistant
# with the oldest Home Keeper, then the newer ones, on 1 config dir.
#
#   bash ci/test-upgrade.sh                 # upgrade to HA stable and Home Keeper main
#   HA_TAG=beta bash ci/test-upgrade.sh     # upgrade to the HA beta
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ck-upgrade-hk.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
OLD_REF="${HK_OLD_REF:-v$(sed -n 's/^HOME_KEEPER_MIN_VERSION = "\(.*\)"/\1/p' "$ROOT/custom_components/car_keeper/const.py")}"
NEW_REF="${HK_NEW_REF:-main}"
SRC="$ROOT/tests/integration/.home_keeper/custom_components/home_keeper"
for pair in "old:$OLD_REF" "new:$NEW_REF"; do
  name="${pair%%:*}"
  ref="${pair#*:}"
  HOME_KEEPER_REF="$ref" bash "$ROOT/ci/fetch-home-keeper.sh"
  cp -a "$SRC" "$WORK/$name"
done
cd "$ROOT"
HK_OLD_DIR="$WORK/old" HK_NEW_DIR="$WORK/new" \
  python -m pytest tests/upgrade -v -rxX -p no:socket -p no:pytest_socket -p no:homeassistant "$@"
