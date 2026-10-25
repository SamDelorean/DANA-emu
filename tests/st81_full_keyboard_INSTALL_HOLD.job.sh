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
GUEST=/home/spc/DANA_EMU_ISOLATED/DIAG_EVIDENCE_ARCHIVE/DANA_GUI024C_20261023/emutos_calibrated_gem.dana
DRIVER_BLOB=35a6a786932adb993e3e37f9df8d4a50176eed83
RUNNER_REV=b0d6e8aa19f45e9505d63fc1d509e8de4f913621
RUNNER_BLOB=eb504bb248b66d09224b001a78828923d07c4c6a
INSTALLED_SHA=254c834e1a1137bc52044171685971d190b69e2b7b78c6ba992d2c582ed6eda6
CANDIDATE_SHA=0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a
GUEST_SHA=eaf3d25cd32a21a9bcfa5cb71756dba749d611c73ed88259444a8ca7aabf67cd
STAGE=''
cleanup() { if [[ -n "$STAGE" ]]; then rm -f "$STAGE"; fi; }
trap cleanup EXIT

# Fail closed: the old working writable-SD emulator remains installed.
test "$(sha256sum "$OPER" | cut -d' ' -f1)" = "$INSTALLED_SHA"
test "$(sha256sum "$CANDIDATE" | cut -d' ' -f1)" = "$CANDIDATE_SHA"
test "$(sha256sum "$GUEST" | cut -d' ' -f1)" = "$GUEST_SHA"
test "$(git hash-object "$SRC/src/mame/skeleton/alphasdana.cpp")" = "$DRIVER_BLOB"

# One unique evidence directory, but no alternate emulator tree.
EVIDENCE=$(mktemp -d /tmp/DANA_ST81_ALL81_PRODUCT_XXXXXXXX)
echo "ST81_EVIDENCE=$EVIDENCE"
curl -fsSL --max-time 40 \
  "https://raw.githubusercontent.com/SamDelorean/DANA-emu/$RUNNER_REV/tests/st81_full_keyboard_native.py" \
  -o "$EVIDENCE/runner.py"
test "$(git hash-object "$EVIDENCE/runner.py")" = "$RUNNER_BLOB"
python3 -m py_compile "$EVIDENCE/runner.py"
install -m 664 "$EVIDENCE/runner.py" "$SRC/tests/st81_full_keyboard_native.py"

# Exactly one full interactive guest-CPU campaign, not 81 independent tests.
set +e
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy timeout 330s \
  python3 "$SRC/tests/st81_full_keyboard_native.py" \
  --diag "$CANDIDATE" --guest "$GUEST" \
  --source "$SRC/src/mame/skeleton/alphasdana.cpp" \
  --output "$EVIDENCE/session" >"$EVIDENCE/native.stdout" 2>"$EVIDENCE/native.stderr"
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
assert a['guest_boot_trace_confirmed'] is True
assert a['expected_physical_keys']==81
assert a['host_inputs_seen']==81
assert len(a['scans_seen'])==81 and not a['missing']
assert len(a['chords_seen'])==5 and a['releases']>=81
assert a['guest_data_reads']>0 and a['guest_control_reads']>0
print('ST81_FULL_PHYSICAL_81_PRESS_RELEASE_MODIFIERS_CPU_SPI2_PASS')
PY

# Only on complete PASS atomically replace the one operational emulator.
test "$(sha256sum "$OPER" | cut -d' ' -f1)" = "$INSTALLED_SHA"
STAGE="$ROOT/bin/.dana-diag-ST81-$$"
install -m 700 "$CANDIDATE" "$STAGE"
test "$(sha256sum "$STAGE" | cut -d' ' -f1)" = "$CANDIDATE_SHA"
mv -f "$STAGE" "$OPER"
STAGE=''
cmp -s "$OPER" "$CANDIDATE"
echo "ST81_SINGLE_DIAG_INSTALLED_PASS=$CANDIDATE_SHA"
echo "ST81_EVIDENCE=$EVIDENCE"
