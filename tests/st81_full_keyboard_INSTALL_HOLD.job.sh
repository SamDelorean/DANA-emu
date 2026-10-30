#!/usr/bin/env bash
# Historical filename retained. Run full Palm/AlphaWord/81-key qualification.
# This entry point never installs an executable based solely on packet tests.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec python3 "$ROOT/tests/run_keyboard_campaign.py" "$@"
