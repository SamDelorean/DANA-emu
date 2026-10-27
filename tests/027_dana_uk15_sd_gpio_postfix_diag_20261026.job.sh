#!/usr/bin/env bash
# SPDX-License-Identifier: BSD-3-Clause
# Dana 027. Observe genuine original ROM CPU with both physical SDIRQ inputs
# low using the already qualified configuration in the SAME canonical DIAG.
set -Eeuo pipefail
umask 077
D=/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag
S="$D/source"
SRC="$S/src/mame/skeleton/alphasdana.cpp"
BIN="$S/danadiagd"
OPER="$D/bin/dana-diag"
ROM="$D/work/uk15_qualify_20261025/UK15_private.raw"
P="$D/work/uk15_qualify_20261025/boot_progress_20261026"
CFG="$P/cfg_sd_both_low"
O="$D/work/uk15_qualify_20261025/vz_sd_027_original_CPU_both_low"
mkdir -p "$O"
exec > >(tee "$O/job.log") 2>&1
trap 'rc=$?; echo "DANA_027_EXIT=$rc"' EXIT
fail(){ echo "BLOCKED_DANA027: $*" >&2; exit 6; }
sha(){ local n=$1 expected=$2 actual; test -f "$n" || fail "Missing $n"; actual=$(sha256sum "$n" | cut -d' ' -f1); echo "DANA_027_SHA $n $actual"; test "$actual" = "$expected" || fail "SHA mismatch $n"; }
echo DANA_027_START_ORIGINAL_CPU
command -v git >/dev/null || fail "git unavailable"
test "$(git hash-object "$SRC")" = b25c759e2c62ddbdbe0a3e16544458d7e96eef38 || fail "unexpected source"
sha "$BIN" 6f557ee17fb51a96cfad00e6193e6a6b883c6532595221b212a3f76f6e1c13b3
sha "$OPER" 0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a
sha "$ROM" 2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3
test -f "$CFG/asmdana.cfg" || fail 'Existing both-low cfg missing'
grep -q 'tag=":SDIRQ" type="CONFIG" mask="4" defvalue="4" value="0"' "$CFG/asmdana.cfg" || fail 'PD2 not configured low'
grep -q 'tag=":SDIRQ" type="CONFIG" mask="8" defvalue="8" value="0"' "$CFG/asmdana.cfg" || fail 'PD3 not configured low'
echo EXISTING_ELECTRICAL_CONFIGURATION_VERIFIED
cat > "$O/original_cpu_stack.lua" <<'LUA'
local cpu=assert(manager.machine.devices[':maincpu'])
local bus=assert(cpu.spaces['program'])
local port=assert(manager.machine.ioport.ports[':SDIRQ'])
local f=assert(io.open(assert(os.getenv('DANA_PALM_TRACE')),'w'))
local frame=0
local checkpoints={[1]=true,[240]=true,[295]=true,[300]=true,[303]=true,
  [310]=true,[330]=true,[360]=true,[420]=true,[600]=true,[900]=true,
  [1200]=true,[1800]=true,[2400]=true}
local function rd8(addr) return bus:read_u8(addr) end
local function rd16(addr) return bus:read_u16(addr) end
local function addr(a) return string.format('%08X',a) end
emu.register_frame_done(function()
  frame=frame+1
  if checkpoints[frame] then
    local a6=cpu.state['A6'].value
    local lcd=(rd16(0xfffffa00)<<16)|rd16(0xfffffa02)
    local pins=port:read()&0x0c
    f:write(string.format('FRAME=%d SDIRQ=%02X PDDIR=%02X PDDATA=%02X PDPOL=%02X PDIEN=%02X PDIEG=%02X A6=%08X D3=%08X CURPC=%08X LCD=%08X PLLFSR=%04X\n',
      frame,pins,rd8(0xfffff418),rd8(0xfffff419),rd8(0xfffff41c),rd8(0xfffff41d),rd8(0xfffff41f),
      a6,cpu.state['D3'].value,cpu.state['CURPC'].value,lcd,rd16(0xfffff202)))
    if pins~=0 then error('Input config SDIRQ != 0') end
    if frame>=300 then
      local cur=a6
      for depth=1,10 do
        if cur<0x1000 or cur>0x100000 then break end
        local prev=bus:read_u32(cur)
        local ret=bus:read_u32(cur+4)
        f:write(string.format('STACK frame=%d depth=%d A6=%08X RET=%08X PREV=%08X\n',frame,depth,cur,ret,prev))
        if prev<=cur or prev>0x100000 then break end
        cur=prev
      end
    end
    f:flush()
  end
  if frame>=2400 then f:write('END_FRAMES=2400 DESKTOP_NOT_ASSUMED\n');f:close();manager.machine:exit() end
end)
LUA
export DANA_PALM_TRACE="$O/original_cpu_stack.log"
cd "$D"
echo DANA_027_ROM_RUN_START
set +e
timeout --signal=TERM --kill-after=10 540 "$BIN" asmdana -rom "$ROM" -cfg_directory "$CFG" -video none -sound none -nothrottle -autoboot_script "$O/original_cpu_stack.lua" -seconds_to_run 55 > "$O/guest_stdout.log" 2> "$O/guest_stderr.log"
rc=$?
set -e
echo "DANA_027_GUEST_EXIT=$rc"
if [ "$rc" != 0 ]; then tail -35 "$O/guest_stderr.log"; fail "guest exited $rc"; fi
test -s "$O/original_cpu_stack.log" || fail 'Observer did not produce trace'
grep -q 'END_FRAMES=2400' "$O/original_cpu_stack.log" || fail 'Observer did not reach frame 2400'
grep -q 'FRAME=303 SDIRQ=00' "$O/original_cpu_stack.log" || fail 'Live pin state not proven'
if grep -q 'DANA_PHYSICAL_BLOCKED' "$O/guest_stderr.log"; then grep -m4 'DANA_PHYSICAL_BLOCKED' "$O/guest_stderr.log"; fail 'Physical MMIO blockade'; fi
sha "$BIN" 6f557ee17fb51a96cfad00e6193e6a6b883c6532595221b212a3f76f6e1c13b3
sha "$OPER" 0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a
sha "$ROM" 2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3
echo DANA_027_ORIGINAL_CPU_2400_FRAMES_PASS__PALM_DESKTOP_NOT_PROVEN
cat "$O/original_cpu_stack.log"
echo "EVIDENCE_PATH=$O"
