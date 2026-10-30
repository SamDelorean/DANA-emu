#!/usr/bin/env bash
# Canonical Palm OS UK1.5 launcher for the single dana-diag executable.
# The experimental erased-NOR and SDIRQ fixture is explicitly selected.
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd -P)"
DIAG="$ROOT/runtime/diag"
ROM="$DIAG/work/uk15_qualify_20261025/UK15_private.raw"
PROFILE="$ROOT/config/palm-uk15/asmdana.cfg"
BIN="$DIAG/bin/dana-diag"
[[ -x "$BIN" ]] || { echo "ERROR: missing executable: $BIN" >&2; exit 1; }
[[ -s "$ROM" ]] || { echo "ERROR: missing original UK1.5 firmware: $ROM" >&2; exit 1; }
[[ -s "$PROFILE" ]] || { echo "ERROR: missing authorized profile: $PROFILE" >&2; exit 1; }
[[ -d "$DIAG/work" ]] || { echo "ERROR: missing runtime workspace" >&2; exit 1; }
CFG="$(mktemp -d "$DIAG/work/.palm-uk15-input.XXXXXXXX")"
cleanup() { rm -rf -- "$CFG"; }
trap cleanup EXIT
cp -- "$PROFILE" "$CFG/asmdana.cfg"
if ! grep -q 'tag=":NOR_PROFILE".*value="1"' "$CFG/asmdana.cfg" ||
   ! grep -q 'tag=":NOR_FACTORY".*value="1"' "$CFG/asmdana.cfg" ||
   [[ $(grep -c 'tag=":SDIRQ".*value="0"' "$CFG/asmdana.cfg") -ne 2 ]]; then
   echo "ERROR: incorrect Palm UK1.5 boot profile" >&2; exit 1
fi
cd "$DIAG"
echo "Dana Palm UK1.5 — SINGLE dana-diag; fixed NOR/SDIRQ profile; ORIGINAL ROM"
"$BIN" asmdana -rom "$ROM" -cfg_directory "$CFG" \
 -window -nomaximize -lightgun -lightgun_device lightgun -lightgunprovider sdl -nomouse "$@"
