# Dana UK1.5 genuine Palm OS RTC — native PASS and next PWM1 hardware stop (2026-10-26)

## State

**Native first MMIO blocker at `0xFFFFFB00` (32-bit RTCTIME) is CLOSED for the observed UK1.5 firmware execution.** Firmware executed its RTC setup and moved on to a different, Ghidra-verified hardware address (`0xFFFFF500`, PWM1). This is **not** Palm OS desktop boot success; the original `palm POWERED` bitmap remains visible. No fake hardware registers, no change to original ROM or installed operative, no Codex.

## Authoritative sources

- Original Motorola **MC68VZ328UM** Rev.0 user manual, §§11.1 and 11.2.1, 11.2.6–11.2.8, Tables 11-2, 11-7, 11-8, 11-10. **Actual verified Drive copy** in `ALPHASMART/Dana/DATASHEETS`: https://drive.google.com/file/d/1UuxWG0rYc0n7RoLerqYTt9mlBpU45L6Y/view. Extracted locally to `work/uk15_qualify_20261025/rtc_20261026/MC68VZ328UM.txt` from that identical 7,223,788-byte PDF.
- CloudpilotEmu/POSE, independent Palm OS emulator hardware implementation: https://github.com/cloudpilot-emu/cloudpilot-emu/blob/master/src/cloudpilot/emulator/hardware/EmRegsVZ.cpp, fields `rtcHourMinSec`, `rtcControl`, `rtcIntStatus`, `rtcIntEnable`; `rtcHourMinSecRead` gets host time, `rtcIntStatusWrite` clears bits W1C, `UpdateRTCInterrupts` propagates pending bits; actual hardware RTC bit 4 (0x10) of interrupt LOW, level 4.
- The reference POSE driver is a useful baseline but uses host time of day, whereas this emulator has a **deterministic emulated 1-second 32.768kHz oscillator domain**. The real RTC has battery-backed undefined time on power-up, not manufacturer reset 00:00:00. A new emulation session initializes it deterministically to zero; warm resets preserve `m_rtc_time` and `m_rtc_day`.
- Ghidra original private UK1.5 big-endian MC68VZ328 ROM: `0x1007FD26 TST.L ($FFFFFB00).W`, `0x1007FD2E BNE.B` and conditional `0x1007FD30 MOVE.L (-0x1A,A6),($FFFFFB00).W`, then `0x1007FD3A MOVE.W #0x000A,($FFFFFB10).W`, `0x1007FD40 MOVE.W #0x0080,($FFFFFB0C).W`. These are original 68000 instructions, not invented test code. Exact prior Ghidra transcript at `work/uk15_qualify_20261025/isp1161_c0_20261026/ghidra_next_rtc.txt`.

## Actual integrated implementation

- Controller `src/mame/skeleton/alphasdana.cpp`, `main` commit **`fff8caefc6e941ecf9bde5da4364ef283a07bb85`**.
- Added manufacturer-masked 32-bit `RTCTIME` at `FFFFFB00..FB03`, valid hours[28:24] 0–23, minutes[21:16] 0–59, seconds[5:0] 0–59, reserved bits zero; bus 68000 word access/read and partial byte-lane write handled without generic MMIO.
- Added RTCCTL `FFFFFB0C`, RTCISR `FFFFFB0E` W1C, RTCIENR `FFFFFB10`, 16-bit bus lanes, exact observed `IEN=000A`, `CTL=0080`. Ref oscillator selection RTCCTL.REFREQ is stored; 1Hz time output is derived from the nominal 32.768kHz source. Timer at 1 virtual second increments properly, carries minutes, hours and a 9-bit day count. Implements 1Hz/minute/hour/day event status; checks RTCIENR and propagates to VZ RTC interrupt low bit4/level4. Dedicated unsupported subsecond/stopwatch/alarm enable cases are **fail-closed**, not generated as fake interrupts.
- RTC is battery-backed on physical VZ and does not reset TOD/DAY on a soft reset. Storage is MAME save-state backed; generated events status reset and subsequent time progression driven by MAME virtual time. This solves the native read and setup without claiming full RTC battery model or complete alarm engine.
- Focused production C++20 regression `tests/rtc_uk15_test.py`, commit **`738bc72c4a9e64b07c89f4143c8b34c798406706`** (initial creation `0f73986`): reads/writes of real handler bodies, valid/invalid time fields, time carry, 1Hz/minute IRQ and clear W1C, 24-hour rollover, RTCEN=0 pause, byte lane register writes, rejects unsupported IRQ rates; 1/1 PASS.
- Existing regressions `isp1161_uk15_dc_test.py`, `csd_rop_read_protection_test.py`, `pctlr_uk15_test.py` all PASS (3/3), total 4/4.
- Real T `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21` PASS (full link) 19.5 sec.
- Exact tested source SHA256 **`24bc0545d4ef6219a36bb4e2ba7e6c1145225f6f6fd2906e2a427bf4f7b80097`**, byte-identical to pinned GitHub main as executed.
- Staged `source/danadiagd` test candidate SHA256 **`a8f278eef1d8c7b654283e65713f2b914489be8658bdced06c870b1e3e005758`**.
- Live operative **`bin/dana-diag` unchanged** SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. Private original UK1.5 raw ROM unchanged SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.
- ONE canonical T DIAG: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`, log path `work/uk15_qualify_20261025/rtc_20261026/{result_*.log,build.log,native.err,native_metrics.txt,ghidra_after_rtc.txt}`.

## Real native observation

MAME original ROM physical reset + prior 1800-frame observer, event-driven clock:
```text
DANA_RTC_IEN value=000a
DANA_RTC_CONTROL value=0080 rtcen=1 refreq=0
```
Original native CPU **advanced past `CURPC=1007FD26` and the following enable/control instructions**, recorded all above writes. Because the model clock is already counting at this point, the initial conditional RTCTIME write was not taken (the original `TST.L` branch detected nonzero running time), so no RTC_TIME_WRITE message is expected; this is a legitimate battery-backed nonzero-time path, not proof the conditional write path happened. The directed production test separately verifies the write path.

Actual first subsequent hardware blocker:
```text
DANA_PHYSICAL_UNIMPLEMENTED_MMIO read address=fffff500 mask=ffff
DANA_PHYSICAL_BLOCKED reason=MMIO_READ_UNIMPLEMENTED address=fffff500 data=0000 pc=1007f1f2
DANA_PHYSICAL_CPU curpc=1007f1ec ir=0278 sp=0007ec2a sr=2000
```

**Ghidra 12.1.3 was executed again on the existing original UK1.5 image project**, source script `ghidra_scripts/DanaUK15AfterRTCTime.java`; transcript `rtc_20261026/ghidra_after_rtc.txt` shows:
```asm
1007F1EC [0278FFEFF500] ANDI.W #$FFEF,($FFFFF500).W
1007F1F2 [42B80260]     CLR.L ($00000260).W
1007F1F6 [4E5E]         UNLK A6
1007F1F8 [4E75]         RTS
```

This is **a read-modify-write to 16-bit PWM1 control at `FFFFF500`**, clearing only bit4; it is *not* RTC or another generic memory address. The actual read failed, so the write part of ANDI has **not** executed yet. Motorola VZ UM PWM chapter details its correct reset and bit meanings. Do not add fake PWM registers in this RTC fix; qualify the existing PWM subsystem (not the LCD PWM) against the manual and actual ROM.

**Closed:** UK1.5 initial RTC setup and first RTCTIME block; all required directed checks and real native compilation PASS. **Open:** PWM1 control at FFFFF500 and eventual Palm OS desktop. Original palm POWERED framebuffer still unchanged 4,161 active pixels after four seconds; bounded observer exiting 0 is not complete boot.
