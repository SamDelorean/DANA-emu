# DANA-emu VZ RTC sourced from the MAME host clock (2026-10-26)

## Implemented and native-tested (not a proposal)

**User direction:** simplify the RTC by reading the host clock. Applied to the **existing single** `src/mame/skeleton/alphasdana.cpp` in `main`, no other branch/worktree, no Codex, no firmware edits and no replacement of the installed `bin/dana-diag`.

**Authoritative source code commits:**
- `55260c5bbf06dc558b6160fa52861f61e4044ff2`: clock source conversion, host RTC-compatible guest time offset, IRQ unchanged.
- `ec16133fc19281113aee0f77862523fc4732d2ca`: refresh both 68000 word lanes, including isolated seconds-word reads.
- `d3eba34f8aa287324d246f637fb36a5d5892f2af`: update actual-source C++20 tests for host synchronization, guest write offset, RTCEN disable/resume, IRQ, minute/day rollover.

## Design — host-seeded clock, coherent MAME time base

`machine().current_datetime(system_time&)` is the **native MAME RTC interface**, as confirmed in this same T MAME source at `src/emu/machine.cpp`. It calls `systime.set(m_base_time + machine().time().seconds())`: **host wall-clock anchored when the machine starts, advancing according to MAME simulated time**, not `std::time` called on each word read. This distinction is intentional: pause, fast-forward, rewind and `-nothrottle` respect the emulator time domain; a manual OS time adjustment midway through the run is not automatically followed.

At every actual `RTCTIME` word read, `rtc_sync_from_host()` samples `host.local_time.hour/minute/second`, adds `m_rtc_offset_seconds`, applies 24-hour modulo and encodes Motorola MC68VZ328 `HOURS[28:24]`, `MINUTES[21:16]`, `SECONDS[5:0]`. **Both high and low 68000 word reads update**, including isolated seconds-word reads. Hardware RTCEN=0 freezes the register. Original firmware writes to RTCTIME update a **guest-specific seconds offset**, so subsequent reads retain the programmed time without attempting to change the host clock or alter MAME global RTC devices. Re-enable RTCEN reanchors that offset to the frozen value. The existing 1-second callback remains only for RTC interrupt/event status and midnight day-carry; **it no longer increments the time register**. Day and offset are save-state registered.

Reference implementations:
- [CloudpilotEmu/POSE `EmRegsVZ::rtcHourMinSecRead`](https://github.com/cloudpilot-emu/cloudpilot-emu/blob/master/src/cloudpilot/emulator/hardware/EmRegsVZ.cpp), reads machine/host time on RTC register access.
- [Motorola MC68VZ328UM](https://drive.google.com/file/d/1UuxWG0rYc0n7RoLerqYTt9mlBpU45L6Y/view) §11.2.1, 11.2.6–8, original PDF held at `ALPHASMART/Dana/DATASHEETS`.
- Ghidra original UK1.5 `CURPC=0x1007FD26` `TST.L ($FFFFFB00).W`, followed by conditional RTCTIME write, RTCIENR=000A, RTCCTL=0080; already authenticated in `docs/UK15_RTC_NATIVE_PASS_20261026.md`.

## Real execution and regression results

Single T DIAG:
`/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`

Exact T source SHA256 `ebe6fd73f4f6df903a9d3946ef5c129c1cd8d9229def69d2276e6822eb927408` synchronized from GitHub `main@ec16133fc`.

Production-extracted C++20 tests on T:
- `tests/rtc_uk15_test.py` **PASS 1/1**. Includes fixed host 11:42:57, time-read progression, invalid RTC value rejection, guest time write offset retained across host advancement, fractional/word lane writes, RTCEN freeze/re-enable, RTC minute interrupt W1C, day rollover, unimplemented RTC rate fail-closed. An initial **real** test failed on isolated seconds-only read (case16); the source was corrected in `ec16133fc` and then all tests passed.
- `tests/isp1161_uk15_dc_test.py` **PASS 1/1**.
- `tests/csd_rop_read_protection_test.py` **PASS 1/1**.
- `tests/pctlr_uk15_test.py` **PASS 1/1**.

Clang21 MAME full incremental compile/link **PASS** (return code 0, 18.82s). Staged test candidate `source/danadiagd` SHA256 **`dec1db909b171896d15a25116cad409f89d4b7d99816d06f36cf288e3e5cf026`**. Installed operative **unchanged** `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. Original private UK1.5 ROM unchanged SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.

Native physical `-rom` bounded 1800-frame observer **PASS through original RTC**; logs:
```text
DANA_RTC_IEN value=000a
DANA_RTC_CONTROL value=0080 rtcen=1 refreq=0
```
Guest reaches same actual next MMIO read-block, not an RTC regression:
```text
DANA_PHYSICAL_UNIMPLEMENTED_MMIO read address=fffff500 mask=ffff
DANA_PHYSICAL_BLOCKED reason=MMIO_READ_UNIMPLEMENTED address=fffff500 data=0000 pc=1007f1f2
DANA_PHYSICAL_CPU curpc=1007f1ec ir=0278 sp=0007ec2a sr=2000
```
Previously reverse-engineered by Ghidra as `1007F1EC ANDI.W #$FFEF,($FFFFF500).W`, a read-modify-write of the Motorola PWM1 control register. The authentic `palm POWERED` 560x160 monochrome framebuffer remains 4,161 active pixels throughout frames 60–240; Palm OS desktop has **NOT** been booted. No PWM1 code was added.

T proof:
`work/uk15_qualify_20261025/rtc_host_20261026/{build.log,native.err,native_metrics.txt}`; prior directed output logs in the single T DIAG. The observer's zero exit is its bounded script exit, NOT Palm graphical boot success.

## Limitations

- MAME host-seeded clock advances in **emulated seconds**, not live wall-clock seconds during pauses. It does not follow a user changing computer system time mid-session; for that behavior an explicit real-time host clock sync option would be needed.
- Battery retention across emulator process restarts depends on save-state; this does not introduce an RTC-specific disk file or NVRAM.
- Full RTC alarm and subsecond interrupt generator remain unimplemented and fail closed. Native observed RTC configuration is fully supported.
