#!/usr/bin/env bash
# Dana UK1.5 SD/VZ authorized native job. One existing T DIAG; do not install operative.
set -Eeuo pipefail
umask 077
D=/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag
S=$D/source
SRC=$S/src/mame/skeleton/alphasdana.cpp
BIN=$S/danadiagd
OPER=$D/bin/dana-diag
ROM=$D/work/uk15_qualify_20261025/UK15_private.raw
O=$D/work/uk15_qualify_20261025/vz_sd_026_b67072518
mkdir -p "$O"
exec > >(tee "$O/job.log") 2>&1
trap 'echo "DANA_026_JOB_EXIT=$?"' EXIT
fail() { echo "BLOCKED: $*" >&2; exit 6; }
check() {
 test -f "$1" || fail "missing $1"
 actual=$(sha256sum "$1" | cut -d' ' -f1)
 echo "SHA256 $actual $1"
 test "$actual" = "$2" || fail "SHA mismatch: $1"
}
echo DANA_026_BEGIN
test -f "$S/makefile" && test -x "$BIN" && test -x "$OPER" || fail "wrong DIAG checkout"
check "$SRC" 42885f69ebbb70c4540e9e222a1754a7f3230b7ba747e87f5645225b75ef00d9
check "$BIN" 6f2eb8a7789bfa6930c14363ca696a3272dad50c114000517c0d888873f53d49
check "$OPER" 0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a
check "$ROM" 2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3
command -v git >/dev/null || fail "git not available"
python3 - "$O/alphasdana.pinned" <<'PY'
import sys,urllib.request
url='https://raw.githubusercontent.com/SamDelorean/DANA-emu/b67072518c6da732df001b55c8c24823406b0738/src/mame/skeleton/alphasdana.cpp'
with urllib.request.urlopen(url,timeout=40) as r: data=r.read()
with open(sys.argv[1],'wb') as f: f.write(data)
print('PINNED_SOURCE_SIZE',len(data))
PY
hash=$(git hash-object "$O/alphasdana.pinned")
echo "PINNED_BLOB=$hash"
test "$hash" = b25c759e2c62ddbdbe0a3e16544458d7e96eef38 || fail "unexpected source Git blob"
cp -p "$SRC" "$O/alphasdana.previous"
cp "$O/alphasdana.pinned" "$SRC"
echo SOURCE_SYNCHRONIZED
cd "$S"
make -n -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++ > "$O/make-plan.log" 2>&1 || fail "make -n failed"
n=$(wc -l < "$O/make-plan.log")
echo "MAKE_PLAN_LINES=$n"
if (( n>800 )); then fail "Full MAME rebuild refused"; fi
echo BUILD_START
timeout --signal=TERM --kill-after=10 900 make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++ 2>&1 | tee "$O/build.log"
echo BUILD_PASS
test -x "$BIN" || fail "candidate missing after build"
h=$(sha256sum "$BIN" | cut -d' ' -f1)
echo "CANDIDATE_SHA=$h"
test "$h" != 6f2eb8a7789bfa6930c14363ca696a3272dad50c114000517c0d888873f53d49 || fail "candidate did not rebuild"
check "$OPER" 0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a
cat > "$O/observe.lua" <<'LUA'
local cpu=assert(manager.machine.devices[':maincpu'])
local bus=assert(cpu.spaces['program'])
local f=assert(io.open(assert(os.getenv('DANA_PALM_TRACE')),'w'))
local n=0
local function r(a) return bus:read_u16(a) end
emu.register_frame_done(function()
 n=n+1
 if n==60 or n==300 or n==360 or n==900 or n==1800 then
  local addr=r(0xfffffa00)*65536+r(0xfffffa02)
  local pd=r(0xfffff418);local pullsel=r(0xfffff41a);local polen=r(0xfffff41c)\n  local ok,pc=pcall(function() return cpu.state['PC'].value end)\n  f:write(string.format('FRAME=%d LSSA=%08X PC=%08X PDDIR=%02X PDDATA=%02X PDPUEN=%02X PDSEL=%02X PDPOL=%02X PDIEN=%02X PLLFSR=%04X\\n',n,addr,(ok and pc) or 0,(pd>>8)&255,pd&255,(pullsel>>8)&255,pullsel&255,(polen>>8)&255,polen&255,r(0xfffff202)))
  f:flush()
 end
 if n>=1800 then f:write('END_FRAMES=1800\n');f:close();manager.machine:exit() end
end)
LUA
export DANA_PALM_TRACE="$O/native-trace.txt"
echo ORIGINAL_PALM_BOOT_START
set +e
timeout --signal=TERM --kill-after=10 720 "$BIN" asmdana -rom "$ROM" -noreadconfig -video none -sound none -nothrottle -autoboot_script "$O/observe.lua" -seconds_to_run 45 > "$O/guest-stdout.log" 2> "$O/guest-stderr.log"
rc=$?
set -e
echo "GUEST_EXIT=$rc"
test -f "$O/native-trace.txt" || { tail -30 "$O/guest-stderr.log"; fail "no native trace"; }
cat "$O/native-trace.txt"
test "$rc" -eq 0 || { tail -30 "$O/guest-stderr.log"; fail "guest emulator exited $rc"; }
grep -q 'END_FRAMES=1800' "$O/native-trace.txt" || fail "native observer did not finish"
if grep -q 'DANA_PHYSICAL_BLOCKED' "$O/guest-stderr.log"; then grep 'DANA_PHYSICAL_BLOCKED' "$O/guest-stderr.log" | head -4; fail "guest MMIO blocked"; fi
check "$OPER" 0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a
check "$ROM" 2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3
echo NATIVE_FRAMES_PASS__PALM_DESKTOP_NOT_ESTABLISHED
echo "EVIDENCE=$O"
