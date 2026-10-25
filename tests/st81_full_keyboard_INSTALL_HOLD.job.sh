#!/usr/bin/env bash
# Single, complete native 81-key Dana keyboard qualification and SAME-DIAG deployment.
# Only a freshly authorized T intervention may set DANA_ST81_NATIVE_AUTHORIZED=YES.
# This job never rebuilds MAME, creates alternate DIAGs, or changes other peripherals.
set -Eeuo pipefail
if [[ "${DANA_ST81_NATIVE_AUTHORIZED:-}" != YES ]]; then
  echo 'ST81_HOLD: fresh explicit T authorization required' >&2
  exit 40
fi
ROOT=/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag
SRC="$ROOT/source"
OPER="$ROOT/bin/dana-diag"
CANDIDATE="$SRC/danadiagd"
DRIVER_BLOB=35a6a786932adb993e3e37f9df8d4a50176eed83
RUNNER_REV=df32f081bc30a1057c6cbc642a91e28b147a0930
RUNNER_BLOB=1e5aac6fc9ba15d833602c3ab77c90fafd3551c7
INSTALLED_SHA=254c834e1a1137bc52044171685971d190b69e2b7b78c6ba992d2c582ed6eda6
CANDIDATE_SHA=0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a
STAGE=''
cleanup() { if [[ -n "$STAGE" ]]; then rm -f "$STAGE"; fi; }
trap cleanup EXIT

# Fail closed: the old working writable-SD emulator remains installed.
test "$(sha256sum "$OPER" | cut -d' ' -f1)" = "$INSTALLED_SHA"
test "$(sha256sum "$CANDIDATE" | cut -d' ' -f1)" = "$CANDIDATE_SHA"
test "$(git hash-object "$SRC/src/mame/skeleton/alphasdana.cpp")" = "$DRIVER_BLOB"

# One unique evidence directory, but no alternate emulator tree.
EVIDENCE=$(mktemp -d /tmp/DANA_ST81_ALL81_PRODUCT_XXXXXXXX)
echo "ST81_EVIDENCE=$EVIDENCE"
curl -fsSL --max-time 40 \
  "https://raw.githubusercontent.com/SamDelorean/DANA-emu/$RUNNER_REV/tests/st81_native_guest_all81.py" \
  -o "$EVIDENCE/runner.py"
test "$(git hash-object "$EVIDENCE/runner.py")" = "$RUNNER_BLOB"
python3 -m py_compile "$EVIDENCE/runner.py"

# ONE complete 81-key real M68000 guest CPU/SPI2 campaign, no rebuilds.
# Guest quickload and complete scan/chord testing are inside runner.py.
set +e
ST81_NATIVE_OUTPUT="$EVIDENCE/session" SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 330s \
  python3 "$EVIDENCE/runner.py" >"$EVIDENCE/native.stdout" 2>"$EVIDENCE/native.stderr"
RC=$?
set -e
echo "ST81_NATIVE_RC=$RC"
if [[ -f "$EVIDENCE/session/keyboard.json" ]]; then
  cat "$EVIDENCE/session/keyboard.json"
fi
if [[ "$RC" -ne 0 ]]; then
  echo "ST81_NOT_QUALIFIED; operational D7.5 unchanged" >&2
  exit 41
fi

python3 - "$EVIDENCE/session/keyboard.json" <<'PY'
import json,sys
a=json.load(open(sys.argv[1]))
assert a['status']=='PASS',a.get('status')
assert a['expected']==81
assert a['host_seen_count']==81 and not a['host_missing']
assert a['ui_menu_frames']==0 and a['ui_active_frames']==0
assert a['paused_frames']==0
assert len(a['seen'])==81 and not a['missing']
assert len(a['chords'])==5 and a['releases']>=81
assert a['cpu_spi2_reads']>0 and a['cpu_guest_poll_count_mod65536']>0
print('ST81_FULL_81_PHYSICAL_KEYS_PRESS_RELEASE_CHORDS_GUEST_CPU_PASS')
PY

# ONLY a complete 81-key guest CPU PASS may replace the single operational DIAG.
# Native EmuTOS typing is a separate unqualified usability claim, not fabricated here.
test "$(sha256sum "$OPER" | cut -d' ' -f1)" = "$INSTALLED_SHA"
STAGE="$ROOT/bin/.dana-diag-ST81-$$"
install -m 700 "$CANDIDATE" "$STAGE"
test "$(sha256sum "$STAGE" | cut -d' ' -f1)" = "$CANDIDATE_SHA"
mv -f "$STAGE" "$OPER"
STAGE=''
cmp -s "$OPER" "$CANDIDATE"
echo "ST81_SINGLE_DIAG_INSTALLED_PASS=$CANDIDATE_SHA"
echo "ST81_EVIDENCE=$EVIDENCE"
