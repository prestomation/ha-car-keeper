#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../custom_components/car_keeper/frontend"
npm run build
