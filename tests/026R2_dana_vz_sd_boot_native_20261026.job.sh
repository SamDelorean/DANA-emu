#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# 026R2: exact pinned source; record mutable candidate before native rebuild.
set -Eeuo pipefail
export LC_ALL=C
umask 077
D=/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag
S="$D/source"
SRC="$S/src/mame/skeleton/alphasdana.cpp"
BIN="$S/danadiagd"
OPER="$D/bin/dana-diag"
ROM="$D/work/uk15_qualify_20261025/UK15_private.raw"
O="$D/work/uk15_qualify_20261025/vz_sd_boot_20261026_026R2_candidate_reconciled"
mkdir -p "$O"
exec > >(tee "$O/qualification.log") 2>&1
on_exit() { rc=$?; echo "DANA_026R2_RESULT exit=$rc source=$(sha256sum "$SRC" 2>/dev/null | cut -d' ' -f1)"; exit "$rc"; }
trap on_exit EXIT
fail(){ printf 'BLOCKED: %s\n' "$*" >&2; exit 6; }
check_sha(){ local f=$1 expected=$2; test -f "$f" || fail "Missing $f"; local actual; actual=$(sha256sum "$f" | cut -d' ' -f1); echo "SHA256 $f $actual"; test "$actual" = "$expected" || fail "SHA mismatch on $f"; }
printf 'DANA_026R2_START objective=UK15_VZ_SD_BOOT source_blob=b25c759e2c62ddbdbe0a3e16544458d7e96eef38\n'
test -d "$D" && test -f "$S/makefile" || fail 'Not canonical one-DIAG make tree'
test -x "$BIN" && test -x "$OPER" || fail 'Expected candidate/operative binaries absent'
# T was verified by a full 2873-line, zero-diff comparison to GitHub main.
# Do not demand obsolete baseline 42885f69..., and DO NOT replace this file.
command -v git >/dev/null || fail 'git missing for immutable blob validation'
test -f "$SRC" || fail "Canonical source missing"
source_blob=$(git hash-object "$SRC")
echo "CURRENT_SOURCE_BLOB=$source_blob"
test "$source_blob" = b25c759e2c62ddbdbe0a3e16544458d7e96eef38 || fail "Local source diverged; no overwrite permitted"
# Candidate changes as other serialized jobs advance. Capture its exact
# starting identity instead of rejecting every legitimate newer build.
CAND_PRE=$(sha256sum "$BIN" | cut -d' ' -f1)
OPER_PRE=$(sha256sum "$OPER" | cut -d' ' -f1)
echo "CANDIDATE_BEFORE_SHA=$CAND_PRE"
echo "OPERATIVE_BEFORE_SHA=$OPER_PRE"
check_sha "$ROM" 2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3
command -v clang++ >/dev/null || fail 'clang++ missing'
# Source is already identical to the authorized Git blob; no download, copy or rewrite.
echo 'SOURCE_ALREADY_RECONCILED_NO_WRITE'
# Reuse exact recorded reduced MAME Clang command and existing build cache.
opts=(TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++)
cd "$S"
make -n -j3 -W src/mame/skeleton/alphasdana.cpp "${opts[@]}" > "$O/make_plan.txt" 2>&1 || fail 'make -n dependency plan failed'
plan_lines=$(wc -l < "$O/make_plan.txt")
echo "MAKE_PLAN_LINES $plan_lines"
# Do not accidentally launch a full rebuild of MAME.
if ((plan_lines>800)); then fail "Unexpected broad MAME dependency rebuild: $plan_lines lines"; fi
echo 'MAME_BUILD_START_026R'
timeout --signal=TERM --kill-after=10 900 make -j3 -W src/mame/skeleton/alphasdana.cpp "${opts[@]}" 2>&1 | tee "$O/build.log"
echo 'MAME_BUILD_DONE_026R'
test -x "$BIN" || fail 'New candidate binary not present'
newsha=$(sha256sum "$BIN" | cut -d' ' -f1)
echo "NEW_CANDIDATE_SHA256 $newsha"
echo "CANDIDATE_REBUILD_SHA_BEFORE=$CAND_PRE AFTER=$newsha"
check_sha "$OPER" "$OPER_PRE"
check_sha "$ROM" 2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3
# A native guest observer: reads live LCD LSSA, Port D registers and CPU PC,
# and terminates MAME at frame 1800. No host-rendered graphics; no ROM patching.
cat > "$O/uk15_native_observe.lua" <<'LUA'
local cpu=assert(manager.machine.devices[':maincpu'])
local mem=assert(cpu.spaces['program'])
local trace=assert(io.open(assert(os.getenv('DANA_PALM_TRACE')),'w'))
local frames=0
local function rd16(a) local ok,v=pcall(function() return mem:read_u16(a) end); return ok and v or -1 end
local function rd8(a) local ok,v=pcall(function() return mem:read_u8(a) end); return ok and v or -1 end
local function pcval()
  local ok,v=pcall(function() return cpu.state['PC'].value end)
  if ok and type(v)=='number' then return v end
  return -1
end
local function take()
  local lssa=rd16(0xfffffa00)*65536+rd16(0xfffffa02)
  trace:write(string.format('FRAME=%d LSSA=%08X PC=%08X PDDIR=%02X PDDATA=%02X PDSEL=%02X PDPOL=%02X PDIEN=%02X PDIEG=%02X PLLFSR=%04X\n',frames,lssa,pcval(),rd8(0xfffff418),rd8(0xfffff419),rd8(0xfffff41b),rd8(0xfffff41c),rd8(0xfffff41d),rd8(0xfffff41f),rd16(0xfffff202)))
  trace:flush()
end
emu.register_frame_done(function()
  frames=frames+1
  if frames==60 or frames==240 or frames==300 or frames==360 or frames==600 or frames==900 or frames==1200 or frames==1800 then take() end
  if frames>=1800 then trace:write('END_FRAMES=1800 BOOT_DESKTOP_NOT_ASSUMED\n');trace:close();manager.machine:exit() end
end)
LUA
cd "$D"
export DANA_PALM_TRACE="$O/native_boot_trace.txt"
echo 'PALM_UK15_NATIVE_START default_unmodified_external_PD_levels'
set +e
timeout --signal=TERM --kill-after=10 720 "$BIN" asmdana -rom "$ROM" -noreadconfig -video none -sound none -nothrottle -autoboot_script "$O/uk15_native_observe.lua" -seconds_to_run 45 > "$O/mame_stdout.txt" 2> "$O/mame_stderr.txt"
rc=$?
set -e
printf 'PALM_UK15_NATIVE_EXIT=%d\n' "$rc"
if [ -f "$O/native_boot_trace.txt" ]; then cat "$O/native_boot_trace.txt"; else tail -30 "$O/mame_stderr.txt"; fail 'No native CPU trace created'; fi
if [ "$rc" -ne 0 ]; then tail -45 "$O/mame_stderr.txt"; fail "MAME exited $rc"; fi
grep -q 'END_FRAMES=1800' "$O/native_boot_trace.txt" || fail 'Frame quota not met'
if grep -q 'DANA_PHYSICAL_BLOCKED' "$O/mame_stderr.txt"; then grep 'DANA_PHYSICAL_BLOCKED' "$O/mame_stderr.txt" | head -5; fail 'New physical boot blocked'; fi
check_sha "$OPER" "$OPER_PRE"
check_sha "$ROM" 2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3
test "$(git hash-object "$SRC")" = b25c759e2c62ddbdbe0a3e16544458d7e96eef38 || fail 'Source changed during build/test'
echo 'NATIVE_1800_FRAMES_PASS_NO_CONCLUSION_OF_PALM_DESKTOP_026R2'
echo "OUTPUT_DIR $O"
