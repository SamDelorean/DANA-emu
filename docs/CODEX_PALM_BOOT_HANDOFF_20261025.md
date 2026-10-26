# Codex takeover — DANA-emu authentic Palm OS boot (2026-10-25)

## CURRENT VERIFIED 2026-10-26 — VZ EMUBRK + MOTOROLA B-RECORD BOOTSTRAP NATIVE PASS (incl. stock Palm ROM); USB CONTROL/HC PTD UNCHANGED

**Authoritative evidence:** `docs/VZ328_BOOTSTRAP_NATIVE_PASS_20261026.md` commit `5df212e49fd11271b91cf0fe5e998eca9fe034ba`. User wants the same functional bootstrap path as AS2K without redesigning other systems. **Motorola VZ ≠ HC11**: manufacturer's MC68VZ328UM §17.1.1–17.1.3 uses EMUBRK LOW sampled with RESET, on-chip vector SP=FFFCFFFC PC=FFFFFF00, UART1/2 19200 8N1, uppercase ASCII B-record with CR and exec record COUNT=00, IBUFF 32B at 00FFFFC0. VZ UART baud and protocol NOT equal AS2K's HC11 7812.5 or MODA/MODB. Separate `src/mame/skeleton/vz328_bootstrap.h` commit `90cb992` is real B-record parser, strict count/mode/address, no SREC spoof; original MAME `alphasdana.cpp` changes commits `b0878c8`, `5c9ba60`, `b19aec5` add selectable EMUBRK pin (normal HIGH default), hardware vectors, real CPU-visible IBUFF, B-record `-quickload .b` with simulated bootstrap reset, legitimate write via AS_PROGRAM bus, CPU PC execution from B record. Crucially **stock original private ROM can stay installed** while B-record injector enters bootstrap; no ROM/CPU-runtime modification, no alternate emulator or branch. **REAL native CPU PASS** with B file `tests/fixtures/vz328_ibuff_payload0.b` (write 4E71/60FE at 00FFFFC0; execution COUNT=0). MAME CPU seen looping at CURPC=00FFFFC2 at frames1,3,12; RESET PC read=FFFFFF00. Works both no ROM and with original UK1.5 `-rom` present; real untouched UK1.5 boot -rom without B files 1800 frames unchanged/no MMIO block. C++ parser tests PASS including Motorola UART2 register example, invalid records. ISP1161 HC/DC 33/33 and PWM1/RTC/CSD/PCTLR regressions PASS. Clang21 MAME full compile+link PASS 18.83s. Final source SHA `42885f69ebbb70c4540e9e222a1754a7f3230b7ba747e87f5645225b75ef00d9`, final candidate `source/danadiagd` SHA `6f2eb8a7789bfa6930c14363ca696a3272dad50c114000517c0d888873f53d49`, installed operative `bin/dana-diag` SHA `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` untouched, original ROM `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. ONE T DIAG evidence `work/uk15_qualify_20261025/vz_bootstrap_20261026`. **DO NOT overclaim** real live UART RX/TX 19200bps/@/echo/multiport selection, IBUFF return-to-bootstrap or complete SDRAM initialization: the implemented test transport is Quickload B-file, model of silicon bootstrap interpreter, not serial bitstream. Native EMUBRK strap and actual Dana PCB pins need physical qualification. The actual ISP1161 is separate external USB chip and has no silicon-bootstrap function; HC/DC 33 register and Host PTD works but actual USB device attachment/DC endpoint payload/DMA INT pins still not complete. Keep emu product central, no endless gates or Codex, main-only, no live binary replacement. Original Palm desktop NOT booted.

---

## LATEST VERIFIED — ISP1161 PTD TRANSACTION ENGINE IN ACTUAL MAME, NATIVE PIO/SOF PASS; BOOTSTRAP IS CPU UART NOT USB (2026-10-26)

**Read FIRST:** `docs/ISP1161A1_PTD_NATIVE_AND_VZ_BOOTSTRAP_20261026.md`, commit `e881cf10e263d3bacf6d0cf3980578b2b1fd81a9`. User prioritizes **real fidelity and possible future processor bootstrap** without serial error-fix campaigns. The native bootstrap hardware in MC68VZ328, per Motorola §17.1.1, is **EMUBRK asserted low + RESET**, then **UART1/UART2 19200 8N1 Motorola B-records**, internal 32-byte instruction buffer at `FFFFC0`; **NOT a USB ISP1161 bootstrap port**. Dana PCB EMUBRK/RESET/UART routing remains UNVERIFIED. Current `main` newly includes `src/mame/skeleton/isp1161_ptd.h` commit `71ff4d79`: real Philips Rev03 8-byte PTD decode, typed packet callback, SETUP/OUT/IN, ACK/NAK/STALL/timeout/CRC, toggle/ActualBytes/CompletionCode/Active, packet length and 4-byte alignment checks. Connected to original MAME ISP1161 HC SRAM ATL and ITL0/ITL1 via `src/mame/skeleton/alphasdana.cpp` commit `b423149d`, SOF frame processing, FIFO buffer-status Full/Done, µP interrupt status, state save; **no fabricated USB device/connection**. Production C++ test `tests/isp1161_ptd_engine_test.cpp` commit `7ef53bb2` PASS; **actual MAME 68000 PIO test** `tests/isp1161_ptd_native_bus.lua` commit `d2740b32` PASS, saw ATL upload Full=0004, after 5 frames Done=0020, physical PTD readback low word `5000` (DeviceNotResponding CC5 to unconnected device), correct untouched other header words. Existing HC/DC physical MAME bus 33/33 PASS and PWM1/RTC/CSD/PCTLR regressions PASS. T single DIAG Clang21 MAME full build/link PASS 19.2s. True unchanged original ROM 30s 1800 frames no MMIO block, but palm POWERED splash remains (4161 pixels), desktop NOT booted. Tested hashes: `alphasdana.cpp` `02592fc46c46fad7e63410458c033d05cdd9db9a4feeed079508bdcb30b9a929`, PTD header `47ddafaae843b9fa4dfc2fc63c9719f6ea887bca6e440e7780d8b656dcdad614`, candidate `source/danadiagd` `a51fdbf2b660f74bc1065bff6e1eb3402554fe09c4c5c6da81a182c698d07f1f`, operative `bin/dana-diag` `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` UNCHANGED, original ROM `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. One T DIAG logs `work/uk15_qualify_20261025/isp1161_ptd_engine_20261026`. IMPORTANT LIMIT: no attached USB peripheral backend wired, DC ping-pong endpoint payload, DMA and real ISP1161 INT-to-VZ pins. Do NOT CLAIM THE ENTIRE USB SILICON IS COMPLETE OR THAT ROM BOOTS DESKTOP. The existing `docs/ISP1161A1_FULL_DEVICE_SINGLE_UNIT_CONTRACT_20261026.md` remains the single integrated architectural target; progress is actual code, not a proposal. No Codex, branch, alternative DIAG, firmware modification or operational replacement.

---

## AUTHORITATIVE 2026-10-26 — STOP ONE-COMMAND PATCHING; ISP1161 HC/DC ARCHITECTURE PROVEN, 33/33 MAME BUS PASS

**New authoritative engineering report:** `docs/UK15_ISP1161_HC_DC_ARCHITECTURE_20261026.md` commit `bf748918d50df0b26c7c74dc48b6e781744ab11c`. User explicitly directed implementation of **the coherent whole ISP1161 chip**, not finding and patching one MMIO error at a time. With Philips Rev03 datasheet PDF already in Drive `ALPHASMART/Dana/DATASHEETS`, Linux `isp116x-hcd.c` and original UK1.5 Ghidra, modeled both independent HC/DC register control planes (Philips Tables 7 and 75), real command/data port offsets, 16-/32-bit phases low then high, HC `ChipID=6123`, independent HC A9/F6 and DC F6 resets, HC 4KiB PIO FIFO memory, 2-port root hub disconnected state, SOF 1ms and frame remaining, HC µP IRQ/scratch/status, DC address/scratch/mode/hardware/IRQ enable/status/endpoint configs/DMACFG, DC independent 2462B RAM reserved. Code commits `main@5c822aeba24cd2eb71ee8a12d3e2c026a892211d`, `main@f6cbadb542cf264831c58556ed355370193dfeba`, `main@fc01a0c585736033553b8c0112d13f0f569b16f1`, final source SHA256 `c50baf64a7a33e4cc0eb50240c7788d7480a7db6bd0a2a64704dd7216d7083a9`. Exact Ghidra on original private UK1.5 ROM `10301A76 MOVE.W #0027,$1F000002`, `10301A7E MOVE.W $1F000000,D0`, manufacturer-high-byte check `0x61`, software HC reset `10301AB0 A9` then `10301AB8 F6`, scratch verification. Manufacturer ISP1161A1 Rev03 HC ChipID 0x6123 (not older example 0x6110), same for DC B5. Extended real MAME physical bus test `tests/isp1161_hc_dc_bus.lua` **33/33 PASS**, Python wrapper `tests/isp1161_uk15_dc_test.py` **2/2 PASS**, PWM1/RTC/CSD/PCTLR **4/4 regression suites PASS**, T Clang21 MAME full build/link PASS 19.73s, final candidate `source/danadiagd` SHA256 `1c141495c39fa0365a0fa299500912ea22140c811f237e4e376f5deb2f66efa5`, original installed `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` **unchanged**, original private UK1.5 SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. Original native ROM 1800 frames/30s **no physical MMIO blocks**; Palm Powered splash persists 4161 dark pixels; no Palm desktop GUI PASS. Ghidra original 1007B090 loop is **PLLFSR CLK32 phase delay**, not ISP1161; passive tap proved 81800 CLK32 transitions/420 frames, so not static oscillator hang either. **DO NOT repeatedly invent an ISP1161 bug**. Host and DC control-plane PASS ≠ **full silicon emulation**: USB transaction/PTD/schedule engine with attach/detach/peripherals, DC endpoint ping-pong data payload, real DMA and external INT pin wiring all remain explicit architectural capabilities NOT IMPLEMENTED. Preserve one `main`, one T DIAG `work/uk15_qualify_20261025/isp1161_full_hc_20261026` and no Codex unless user approves. Next analysis should focus on root-cause boot state and planned USB data-plane as a subsystem, not one-off register error increments.

---

## CURRENT VERIFIED PWM1 NATIVE PASS; ISP1161 HC C0? NO — COMMAND 0027 NEXT (2026-10-26)

**Primary evidence:** `docs/UK15_PWM1_NATIVE_PASS_20261026.md` commit `1108bc438776cb36f8f79deb54038f18c7239176`. The temporary T remote connection issue ended and the original task was actually RETRIED. Source `main@8c276b9e18d933996902b7b4abaa4d02fb07099a` (SHA256 `4f49394f900ce7717a2e4f0a24b05ad4b5ca49c5a500ebd6021cc6290c16625c`) maps true Motorola PWM1 control `FFFFF500–FFFFF501`, reset `0020`, read-before-write of real Ghidra `1007F1EC ANDI.W #$FFEF,($FFFFF500).W`; explicitly does NOT fake FIFO/audio/interrupts. Independent source-extracted production C++ test PASS and persisted test `tests/pwm1_uk15_test.py` `main@8ba6af28b06389ff260bfb652ce55c67e4473d46` 1/1 PASS on T; RTC/ISP1161 DC/CSD/PCTLR regressions 4/4 PASS; T Clang21 MAME build/link PASS (19.68 s). Authentic ROM `-rom` CPU executed full PWM1 RMW and logged `DANA_PWM1_CONTROL value=0020 enabled=0 fifo_available=1`. Staged candidate `source/danadiagd` SHA256 `b090e572905a284ee840fa705aa35fbe3e47b52a60cc75b35da4a7dba4b8e04c`, original operative `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` untouched, unchanged private UK1.5 ROM `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. **New first genuine hardware blocker** `ISP1161_COMMAND_UNIMPLEMENTED` at **HOST** command port `1F000002`, word `0027`, `CURPC=10301A76`, next PC `10301A7E`; this is HC (A1=0), not prior DC C0. Meaning of command 0027 is NOT yet qualified; must research Philips Rev03 datasheet and Linux isp116x host code plus original Ghidra code at ROM offset 0x301A76. Palm Powered splash still visible; no Palm desktop/GUI boot. Evidence located in sole T DIAG `work/uk15_qualify_20261025/pwm1_20261026/`. No Codex, no new diag, no branches, no live executable replacement.

---

## CURRENT — RTC NOW HOST-SEEDED, NATIVE PASS, PWM1 NEXT (2026-10-26)

**Authoritative report:** `docs/UK15_RTC_HOST_CLOCK_NATIVE_PASS_20261026.md` commit `73bae00a`. User requested using the **host RTC** rather than an independent RTC second counter. Implemented in canonical `src/mame/skeleton/alphasdana.cpp` commits `main@55260c5bbf06dc558b6160fa52861f61e4044ff2` and `main@ec16133fc19281113aee0f77862523fc4732d2ca`, updated directed test `main@d3eba34f8aa287324d246f637fb36a5d5892f2af`. Uses `machine().current_datetime(system_time&)`: MAME core returns **host local wall-clock seeded at machine start + emulated elapsed time**. Extracts 24h/HH/MM/SS into authentic Motorola RTCTIME 32-bit register on both high and low word reads; guest writes stored using per-device `m_rtc_offset_seconds`; soft reset and save-state supported; RTCEN freeze/re-enable reanchors offset. 1Hz callback now **only** raises interrupt status and day rollover, never manually increments time. Independent CloudpilotEmu reference `rtcHourMinSecRead` host sourced. An initial real directed test caught standalone seconds-only reads not refreshing; fixed at `ec16133`. Final RTC production test **1/1 PASS**; ISP1161 DC/CSD ROP/PCTLR regressions **3/3 PASS**; Clang21 MAME full build/link PASS 18.82s; authentic UK1.5 original `-rom` executes RTC reads and writes RTCIENR=000A/RTCCTL=0080, then reaches the **same verified next blocker PWM1** `MMIO_READ_UNIMPLEMENTED` `FFFFF500`, `CURPC=1007F1EC` original Ghidra `ANDI.W #$FFEF,($FFFFF500).W`. Source SHA256 `ebe6fd73f4f6df903a9d3946ef5c129c1cd8d9229def69d2276e6822eb927408`, test candidate `source/danadiagd` SHA256 `dec1db909b171896d15a25116cad409f89d4b7d99816d06f36cf288e3e5cf026`, original installed operative `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` UNCHANGED, original ROM SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. Single T DIAG logs `work/uk15_qualify_20261025/rtc_host_20261026/`. **Palm OS desktop still not booted** (real palm POWERED splash persists); no PWM work performed here. IMPORTANT: MAME's host RTC is seeded at machine start and moves with emulated time; mid-session host OS clock changes are not polled live. No new branches, copies, Codex or installed executable changes.

---

## CURRENT GPT — UK1.5 RTC NATIVE PASS; PWM1 NEXT (2026-10-26)

**Verified report** `docs/UK15_RTC_NATIVE_PASS_20261026.md`, commit `8017db6`. Based on original UK1.5 Ghidra (`1007FD26 TST.L ($FFFFFB00).W` conditional `MOVE.L`, writes RTCIENR=000A and RTCCTL=0080), Motorola MC68VZ328UM chapter11 **already in project Drive** `ALPHASMART/Dana/DATASHEETS/MC68VZ328UM.pdf` ID `1UuxWG0rYc0n7RoLerqYTt9mlBpU45L6Y`, and independent CloudpilotEmu/POSE `EmRegsVZ.cpp`, implemented physical RTCTIME 32-bit big-endian high/low at FB00..FB03, RTCCTL FB0C, RTCISR FB0E W1C, RTCIENR FB10, 1Hz MAME virtual-time timer, HH:MM:SS ranges, 9-bit day rollover and genuine RTC low interrupt bit4, narrow unsupported IRQ controls fail-closed. Battery RTC time not reset on warm reset; cold emulator session deterministic 00:00:00 because real time undefined. Code `main@fff8caefc6e941ecf9bde5da4364ef283a07bb85`, source SHA256 `24bc0545d4ef6219a36bb4e2ba7e6c1145225f6f6fd2906e2a427bf4f7b80097`. Directed actual-production handler test `main@738bc72` PASS 1/1, prior ISP1161/CSD/PCTLR regression 3/3 PASS, Clang21 MAME native full build/link PASS 19.5s, candidate `source/danadiagd` SHA256 `a8f278eef1d8c7b654283e65713f2b914489be8658bdced06c870b1e3e005758`. Original installed `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged; original private UK1.5 SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. Native logged RTCIENR 000A and RTCCTL 0080 after passing previously blocked RTCTIME; TST.L saw nonzero virtual clock so conditional original time-writing branch not taken; write semantics separately tested. **New first real native blocker** `MMIO_READ_UNIMPLEMENTED` `0xFFFFF500`, `CURPC=1007F1EC`, `IR=0278`, `SP=0007EC2A`, `SR=2000`. Actual Ghidra 12.1.3 transcript `rtc_20261026/ghidra_after_rtc.txt` proves `1007F1EC ANDI.W #$FFEF,($FFFFF500).W`, an **RMW of Motorola PWM1 control** clearing bit4; write not yet executed. Next hardware scope PWM1 register semantics, not another RTC hack. Only canonical T DIAG path `work/uk15_qualify_20261025/rtc_20261026`. Palm OS original palm POWERED splash still displayed; **NOT booted desktop**. Temporarily no Codex. No new emulator copies, branch changes or operative installations.

---

## LATEST VERIFIED — UK1.5 ISP1161 DC COMMAND C0 NATIVE PASS; RTC NEXT (2026-10-26)

**New canonical report:** `docs/UK15_ISP1161_DC_C0_NATIVE_PASS_20261026.md` commit `c9f1c8b`. Three primary PDFs are now **actually in Drive `ALPHASMART/Dana/DATASHEETS`** folder ID `11bKTw_mNBy_bZUpxfyIbStue-Gm2FaQK`: ISP1161A1 Philips Rev03 `1mYRvC1TUSisXnkZm97exyj78fmn3VKw_`, Rev02 `1qdGOIUQm_YST0iYlff99RQsZpScDfWW_`, original Motorola MC68VZ328UM `1UuxWG0rYc0n7RoLerqYTt9mlBpU45L6Y` (this one copied from an earlier original PDF already in user's Drive, no changed bytes). Official Philips Rev03 §13.3.6 + §8.6.3 define DC command **`C0` Read DcInterrupt** as one 32-bit register in **two** ordered LOW then HIGH 16-bit reads, reset all zeros, clearing only specified event bits on read, endpoint bits independent. Linux `isp116x-hcd.c`/`isp116x.h` and U-Boot `board/sc3/sc3.c` were inspected as real ISP1161 drivers but implement **HC only**, not the Device Controller. Original UK1.5 Ghidra `10081736 MOVE.W #C0,$1F000006`, then `10081740` and `10081748` 16-bit reads from `$1F000004`. Existing single `alphasdana.cpp` commit `main@a4062c963cd58bd1c5c479dd391be246f6171a3f`: no new chip, adds exact DC 32-bit interrupt read transaction state, reset zero, save-state, correct low/high sequence, read-to-clear mask `0x5b`, no manufactured USB interrupt events. Directed actual-handler test `main@1006ad3efa2db5e6ccb52b2580aa1eb7da06644b` PASS 1/1, PCTLR PASS 1/1, CSD/ROP PASS 1/1. Single DIAG T Clang21 MAME complete build/link PASS 19.23 s, source SHA `44e926bcad3138b62f0fede2d8c3d78466fb70f08a785a3b1876aac1bf0e3dba`, staged candidate SHA `7c7599d32693afdc9706ae0e9ba2536abb22663eeca7aa2e4b13cf09ce7f4756`, original installed operative SHA `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` **untouched**, original private UK1.5 SHA `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. Real native CPU logged `DANA_ISP1161_DC_INTERRUPT phase=low value=0000` and `phase=high value=0000`, and advanced. **Next first real blocker:** `MMIO_READ_UNIMPLEMENTED` at `0xFFFFFB00`, `CURPC=1007FD26`, `IR=4AB8`, `SP=0007EC5A`, `SR=2004`. Existing Ghidra ran again and proved `1007FD26 TST.L ($FFFFFB00).W` followed by conditional initialization write to RTCTIME, `RTCIENR`, `RTCCTL`. Motorola identifies `FFFFFB00` as **32-bit RTCTIME**; RTC initialization/clock semantics are NOT implemented here. Palm Powered splash persists and Palm OS desktop still NOT BOOTED. C0 is CLOSED native; next scope RTCTIME. Logs `work/uk15_qualify_20261025/isp1161_c0_20261026`. Code remains on `main`, no Codex, no duplicate DIAG, no live operative replacement.

---

## LATEST DIRECT GPT NATIVE — VZ PCTLR FIXED; ISP1161 DC COMMAND C0 NEXT (2026-10-26)

**Authoritative report:** `docs/UK15_PCTLR_NATIVE_PASS_20261026.md` (commit `d6ace725`). Real UK1.5 ROM Ghidra PC `1007D12A` originally writes byte `9F` at **`FFFFF207` PCTLR**; Motorola MC68VZ328UM §4.5.4 and Linux MC68VZ328.h confirm reset `1F`, `PCEN=bit7`, `WIDTH=bits4:0`. **0x9F means PCEN=1, WIDTH=31 (continuously active CPUCLK)**. Production `main@51eef322` added proper 8-bit low/odd bus-lane register, reset, save, defined-mask readback, rejects other PCEN+partial-duty modes instead of fake CPU sleeps. Actual production handler directed test `main@efe73b0` 1/1 PASS, CSD protected RAM regression 1/1 PASS, Clang21 incremental MAME build/link PASS; source SHA `7a6fcd54efb42ad60e8b64ad8b78eeaddd7e19115cc6a431f872cbf8b16cef6a`, candidate `source/danadiagd` SHA `e1d67fcd46fa4b5035728a1dd5ade49257e30691cf2003029d757460ac4a8d40`, original installed `bin/dana-diag` SHA `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged, original ROM SHA `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. **Native PCTLR PASS:** `DANA_PCTLR value=9f pcen=1 width=31 cpuclk_full_duty=1`; authentic CPU advanced and hit **new** independent `ISP1161_DC_COMMAND_UNIMPLEMENTED` word `00C0` at `1F000006`, `CURPC=10081736`, next `PC=1008173E`, `IR=33FC`, `SP=0007EC76`, `SR=2000`. Same private Ghidra project ran exact disasm: `10081736 MOVE.W #$C0,$1F000006` then planned but **unexecuted** reads at `10081740` and `10081748` from data port `1F000004`. No USB C0 code implemented yet. Do not invent return words. Logs in sole T DIAG `work/uk15_qualify_20261025/pctlr_gpt_20261025/`. Still no Palm OS full desktop PASS or installation update. Temporary Codex pause remains in effect.

---

## CURRENT GPT VERIFICATION — ORIGINAL UK1.5 CSD.ROP WRITE FIX NATIVE PASS (2026-10-25)

**Technical evidence and references:** `docs/UK15_CSD_UPSIZ_NATIVE_PASS_20261025.md` commit `91c671b3`. Genuine UK1.5 firmware `CSD=0x2283`, `CSCTRL1=0x4150` (EUPEN=0x4000, DUPS2=0x0010, DSIZ3=0x0040), CSD 16MiB. Motorola VZ UM §6.3.5 formula and **independent CloudpilotEmu/POSE production `EmRegsVZ::GetDynamicHeapSize`** yield **2MiB unprotected low SDRAM**, even though CSD ROP=1. Previous forbidden supervisor stack write `0x0007EC96` (<2MiB) must pass; high protected region must remain read-only. Implementation `main@12e775a7` + manufacturer/Cloudpilot parity `main@0e8d5bb3`; final source SHA256 `661f9c288f7cdb136e19344ea9c8261557f99000fc20165fe057071aa3a8d235`, directed test commits `6a6541de`, `3e2c6db7` 1/1 PASS, CSD DSIZ3 1/1 PASS, T Clang21 full build/link PASS. Test candidate `source/danadiagd` SHA256 `c9f772636cb6dc528b790914cbdb1c110635367382b6e32a13c8f68ca85eacee`; original operative `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged; original UK1.5 SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. **NATIVE CPU genuinely advanced** past stack write and hit new independent `MMIO_WRITE_UNIMPLEMENTED` on bus base `FFFFF206`, mask `00FF`, actual physical **PCTLR `FFFFF207`**, data `9F`, `CURPC=1007D12A`, next `PC=1007D12E`. Ghidra 12.1.3 actual original instruction: `1007D12A MOVE.B D0,($0207,A0)`, preceded by `ORI.B #$80,D0`, `A0=FFFFF000`. **Do not fake PCTLR clock/sleep behavior.** The correct next separate task is qualifying original PCTLR power control. No Palm desktop boot PASS. Ghidra and native records at `work/uk15_qualify_20261025/csd_upsiz_ghidra_20261025` in the ONE T DIAG. EmuTOS is a guest OS, not a hardware register model. User has temporarily disabled Codex; no Codex needed for completed CSD increment.

---

## LATEST GPT GHIDRA + NATIVE — REAL PALM POWERED SPLASH; CSD ROP READ PASS; WRITE NOT CLEARED (2026-10-25)

**Authoritative evidence:** `docs/UK15_GHIDRA_LCD_SPLASH_CSD_ROP_20261025.md` (commit `78755377`). Actual original UK1.5 CPU executed Ghidra-verified `0x10005996` LCD initializer, programmed LSSA `00003B00`, LPICF08, VPW35, LCD on82, 560×160 mono. Original guest SDRAM at `0x3B00` contains genuine **palm POWERED** splash image, sampled as 11,200 bytes by passive MAME reads and reconstructed privately on T (`palm_uk15_frame_060.png`); 4,161 active pixels, stable frames 60–240. Existing LCD renderer parameters exactly match, no host-made splash or LCD redesign. Ghidra proved the sampled `0x10018054..1001807e` is real memory-fill routine, not idle; `0x1000cad6` is an RTE. **30-second native run** exposed CSD.ROP=1 reading a stack at `0007EC40` incorrectly blocked by old `!(csd & 0x6000)`. Motorola CSD.ROP=bit13 is write protection, not read denial. Minimal `src/mame/skeleton/alphasdana.cpp` code `main@f9dc4c2`, test `main@69f6298` 1/1 PASS, T Clang21 full build PASS, source SHA256 `cfcdca886f8d38843a667d91baa719d66498abce6fe65b31ad2454e10e0c75ab`, candidate `source/danadiagd` SHA256 `a0f5081ea50e4c5f9e3f2d5fb63c41b082701b9f5a4242311ad7f4b32f6d1b7f`. Original private ROM SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. Installed operative `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged. **READ NATIVE PASS**, but new real **WRITE protected** blockage after CPU progress: `EXTERNAL_WRITE_OR_PROTECTION` `0x0007EC96`, `data=ECBA`, `CURPC=1008ECB8`, `IR=4E4F` (TRAP #15), `SP=0007EC98`, `SR=2000`, CSD=2283. Passive CSD register tap verified native `CURPC=1007A100` sets ROP; **Ghidra exact instruction** `1007A100 ORI.W #$2000,($FFFFF116).W`; authentic firmware deliberately enables RAM protected-area bit. **DO NOT BYPASS CSD ROP on writes** without qualifying Motorola §6.2.1 UPSIZ/window and DRAM mode. All evidence in sole T DIAG `work/uk15_qualify_20261025/{lcd_display_ghidra_20261025,lcd_rop_read_fix_20261025}`. Palm OS desktop and installed GUI remain unproven; user-facing original splash is real framebuffer only. This header supersedes older first-blocker instructions below.

---

## LATEST GPT VERIFIED — UK1.5 LCD CURSOR MMIO NATIVE PASS (2026-10-25)

**Canonical evidence** `docs/UK15_LCD_CURSOR_NATIVE_PASS_20261025.md` (commit `e6dd2ec`). Using Ghidra 12.1.3 original authentic UK1.5 68000 code, Motorola MC68VZ328UM §8.3.5–8.3.8, implemented manufacturer's LCD cursor regs **within existing LCD**: LCXP `FFFFFA18` 16bit reset0000 maskC3FF, LCYP `FA1A` 16bit reset0000 mask01FF, LCWCH `FA1C` 16bit reset0101 mask1F1F, LBLKC `FA1F` 8bit reset7F. R-direct + physical register mappings, save-state, lane-accurate 68000, existing framebuffer untouched. Code commits `78f0845` & `013d2c5`, source SHA256 `5e982803d41cec450b0c24790e12aa888fde865cce699c6de6933ffadd0eb46b`; focused compiled actual-production-handler test `tests/lcd_cursor_uk15_test.py` (`451211c`) 1/1 PASS; sole T DIAG Clang21 MAME build/link PASS 18.7s, staged `source/danadiagd` SHA256 `acf3bf9ec8e1c8e31a215de8889e0c47acfad6eed25846d169bc4251ee6e6877`. Original private UK1.5 unchanged SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`; installed live `bin/dana-diag` unchanged SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. **Second native run used passive read/write MAME taps**: actual `LCXP` word read at **`CURPC=10005B7A`**, writes at 10005B84 (LCXP), 10005B88 (LCYP), 10005BA4 (LCWCH value0404), 10005BC0 (`LBLKC=BF` at odd FA1F, low-byte maskFF); later again at 10078D42. At frame240 CPU **`CURPC=1000CAD6`**, not trapped in previous cursor MMIO; no `DANA_PHYSICAL_BLOCKED` in bounded test. **Only register read/write semantics proven**: the hardware cursor's visual pixel compositing and blink cadence are NOT implemented/validated; no authentic Palm OS graphical UI PASS yet. Do not assert a new MMIO blocker when none was observed. Logs at `work/uk15_qualify_20261025/lcd_cursor_ghidra_20261025/`. Follow-ups should inspect actual LCD display state and guest boot progress rather than speculatively patch registers. No Codex/Ghidra project duplication/install performed.

---

## LATEST AUTHORITATIVE — GHIDRA ISP1161 DC REAL NATIVE PASS; LCXP NEXT (2026-10-25)

**Evidence/document:** `docs/UK15_GHIDRA_ISP1161_DC_NATIVE_20261025.md` (commit `137ed066`). **Ghidra 12.1.3 was actually executed** on T against the correct original UK1.5 ROM slice, language 68000:BE:32, base 10000000. It conclusively identified `1F000004/006` as the **device-controller (DC) data/command pair of the same Philips ISP1161**; original instructions `10003064 MOVE.W #B0,$1F000006`, `1000306C MOVE.W #AA37,$1F000004`, followed by BA/0F04 and B8/0020→0000. This is not another peripheral. Code `main@6f740477` extends **existing** HC/ISP1161 with separate manufacturer-backed DC startup state and preserves HC; directed actual-source C++20 regression `main@963c47c9` **1/1 PASS**, Clang21 MAME build **PASS**. Original physical `-rom` CPU confirmed all five DC startup writes, including M68000 discarded `CLR.W` read, and advanced. Source SHA256 `f5ddffb06a85c1d7f51d1bd9170eafc3abb17dc7aa54afcba093dfd2c5dcaa66`; candidate `source/danadiagd` SHA256 `019ba04e20b297ce640227934b2b45afbc0d4611f222e399bd6063985c933733`; original installed `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged. **New first real blocker** is `MMIO_READ_UNIMPLEMENTED` at `0xFFFFFA18`, `CURPC=0x10005B7A`, `PC=0x10005B7E`, `IR=3038`, `SP=00003A6E`, `SR=2709`. Ghidra separately traced the original LCD cursor function: `MOVE.W ($FFFFFA18).W,D0`, mask `C000`, OR cursor X, write same address; subsequent `FA1A` (LCYP), `FA1C` (LCWCH), `FA1F` (LBLKC). MC68VZ328UM confirms **LCXP 16-bit LCD cursor X register**; integrate with *existing LCD subsystem*, not an invented MMIO filler. Full LCD cursor implementation **NOT DONE**. Host and device USB packets NOT proven. Palm OS GUI **NOT BOOTED**. Original ROM never published/modified. Sole canonical T DIAG; native logs `work/uk15_qualify_20261025/ghidra_isp1161_dc_20261025`. Current firmware progress is native CPU only.

---

## LATEST GPT NATIVE — SYNCHRONIZED MAIN SOURCE, EXTERNAL BUS BLOCKER (2026-10-25)

**Authoritative report:** `docs/UK15_MAIN_SYNC_NATIVE_20261025.md` (commit `a0c3a37`). Sole canonical T DIAG source and ISP1161 regression synchronized byte-for-byte to latest implementation `main@2943ba6` source SHA256 `195de28abdded94c45713348b7fa6cf44e1fd26a06f7e0c3ef7e8e08e7f6c21a`. Directed ISP1161 test 1/1 PASS; incremental Clang21 build/link PASS. Candidate `source/danadiagd` SHA256 `6536fd35aa88dfcf7d7b40582bc5ef2316f0afa3add96bc4276611f907e03e79` only (NOT installed). Operative `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged; original private UK1.5 SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` unchanged. Original CPU passed SDRAM IP/RE/MR and observed ISP1161 initialization and M68000 `CLR.W` read-before-write. **First ACTUAL new blocker:** `EXTERNAL_WRITE_OR_PROTECTION` `0x1F000006`, word write `0x00B0`, `CURPC=0x10003064`, prefetched `PC=0x1000306C`, `IR=33FC`, `SP=00003A92`, `SR=2700`. ROM-derived disassembly is `MOVE.W #$00B0,$1F000006`; subsequent `$1F000004/$1F000006` instructions have NOT executed. **Do not invent a peripheral or extend the ISP1161 map without hardware evidence**; investigate physical external address decoding/schematic first. **Palm OS GUI NOT BOOTED.** Logs in `work/uk15_qualify_20261025/main_sync_20261025`. No Codex, no other DIAG, no installed binary changes.

---

## GPT DIRECT IMPLEMENTATION — PCDIR NATIVE PASS; PCDATA NEXT (2026-10-25)

**Current authority:** `docs/PALM_UK15_NATIVE_PCDIR_PASS_20261025.md` (one native-tested PCDIR increment, executed without Codex). Final production controller SHA256 `2b1d94b5246db4befb501d4f81902b19a43c6abc9b1602b50def9ac6f7d8a5fc`; code commits `ed04e0d` + `976c53d`, regression test `db56a6e`. T Clang21 full build/link PASS; same-source staged candidate `537de93f8bd345a66015631561666b83d3ea3f61918961924533e124fcdb7380`, original installed operative hash `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged. Original UK1.5 `-rom` CPU bus writes `0x00` at `0xFFFFF410`, high `FF00` byte, `CURPC=0x100051A0`, and advances: **PCDIR NATIVE PASS**. The immediately following **real** odd/low byte write at `0xFFFFF411`, mask `00FF`, `CURPC=0x100051A6`, is **blocked explicitly** as `PCDATA_WRITE_UNIMPLEMENTED`; prefetched `PC=0x100051AC`, `IR=117C`, `SP=00000316`, `SR=2704`. An intermediate test reached `0xFFFFF610` while the missing PCDATA low lane was silently ignored; this is **NOT** the first faithful blocker and MUST NOT be treated as next task. PCDATA is NOT IMPLEMENTED, only fail-closed; research actual manufacturer behavior before coding. No Palm GUI boot. Existing T operative unchanged. No Codex or new remote task authorized by this handoff.

---

## IODCR NATIVE PASS — NEXT REAL BLOCKER PCDIR (2026-10-25)

**LATEST AUTHORITATIVE GPT T EXECUTION:** `docs/PALM_UK15_NATIVE_PCDIR_20261025.md` (commit `03063ab8`), with manufacturer-verified closed Codex task. Codex IODCR `main@613fc465` controller SHA256 `5a627f2e97564a3452f0a70ec99e6023b8d34a14c6a8afabe289b1321644fab7` is present in the sole T DIAG. **The previously built `source/danadiagd` candidate SHA256 `01a9d6eb817221537f03dc6041b5efae061c5af512d519f3a19427a77ccc2872` was reused WITHOUT recompilation.** Private UK1.5 SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` and existing read-only CPU observer reused, with verified hashes. Installed `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged. Real M68000 bus writes `0x0000`, mask `0xFFFF`, to IODCR `0xFFFFF008` at `CURPC=0x1000517C` and continues: **IODCR NATIVE PASS** (no independent subsequent readback claimed). **New first real blocker** guest `CURPC=0x100051A0`, prefetched `PC=0x100051A6`, `IR=0x117C`, `SR=0x2704`, byte high/even write `0x00`, MAME mask `0xFF00`, at `0xFFFFF410`: `MMIO_WRITE_UNIMPLEMENTED`. Manufacturer MC68VZ328UM §10.4.3.1, Table 10-12 confirms **PCDIR (Port C Direction Register)**, 8-bit R/W reset `0x00`; 0=input, 1=output; dedicated LCD pins use `PCSEL` and ignore DIR pin behavior. **NEXT CODEX CODE ONLY:** implement real PCDIR in physical MMIO, reset/save and true 8-bit semantics; preserve preexisting nearby PCPDEN/PCSEL, R-direct, LCD/SD/ST etc. No speculative PCDATA or generic MMIO RAM. Codex local tests + publish `main`; GPT handles next T compilation and native first-blocker analysis. Original UK1.5 Palm OS UI has **NOT BOOTED**. This note grants no remote authorization.

---

## IODCR code delivery — GPT native validation pending

Implemented only the closed IODCR increment from
`PALM_UK15_NATIVE_IODCR_20261025.md`. Canonical base:
`d13b074455eb6006defd87b7d7bf5f9aeb8d5926`.
Old driver SHA256:
`1275509bbe091e23fd67d3a42d00cce0b332c662ef66224edcbbc024bce8e0e2`.
New driver SHA256:
`5a627f2e97564a3452f0a70ec99e6023b8d34a14c6a8afabe289b1321644fab7`.

Eight additive production lines implement m_iodcr (u16), reset 1FFF, save-state
registration, masked read and lane-selected write, plus exactly one physical
word decoder at FFFFF008–FFFFF009. Defined mask is 1FFF; bits15..13 read zero
and cannot be stored. Each defined bit describes 2 mA (0) versus 4 mA (1)
pad-drive configuration. No electrical current/voltage simulation is claimed.
No GPIO DATA/DIR/SEL, PFSEL, RAM, Flash, CS or clock behavior is changed.
The high/even and low/odd bytes use the existing 16-bit MAME bus masks.
The observed full-word 0000 write should read back 0000 after this change.

Local verification executed:
- `python3 tests/iodcr_register_test.py`: PASS. Compile-time evaluation of actual
  production handlers/state/reset verifies 1FFF reset and reset re-entry,
  original UK word write, high/low byte preservation, reserved-bit rejection,
  zero-mask access and bit-select writes. This is not a guest/native test.
- Full driver g++14 C++20 `-fsyntax-only -Werror` with existing MAME headers:
  PASS; no object/executable or new candidate SHA generated.
- Every preexisting out-of-class handler unchanged, excluding additive
  save/reset/map integration: PASS. SCR, WATCHDOG, PLLCR, ICE and the existing
  physical coverage/peripheral handlers are preserved.
- `git diff --check`: PASS. ICE tests and unrelated closed suites were NOT rerun.

Codex did no T calls, native compilation, candidate execution or installation.
The supplied ea3644... native candidate and IODCR fault are GPT's historical
measurements before this correction, not measurements of the new code.

### GPT continuation

Match old source SHA above in the sole existing T DIAG, apply only this IODCR
increment, then compile the same staged `source/danadiagd` incrementally with
the established Clang21 cache. Keep installed `bin/dana-diag` intact (last
qualified SHA `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`).
Reuse the unchanged original UK1.5 stream, physical `-rom` and bounded observer,
within GPT's own current authorization. Do not reapply prior ICE/PLL patches.
Expected but NOT YET natively observed: full-word 0000 to FFFFF008 at
CURPC=1000517C is accepted and leaves IODCR readback 0000.
Return the actual next CPU transaction/blocker with CURPC/PC/IR/SP/SR,
address/data/mask, full CLI, build result, candidate SHA and operative hash.
No next peripheral is predicted or implemented by this increment. Do not
claim Palm UI boot from instruction progress or observer exit code 0.


## CODEX CLOSED IODCR IMPLEMENTATION — LATEST T NATIVE RESULT (2026-10-25)

**Authoritative new research / real native failure:** `docs/PALM_UK15_NATIVE_IODCR_20261025.md` commit `ae61602`, prepared HERE, not delegated to Codex. Canonical ICE implementation `main@4ab1bd07` source SHA256 `1275509bbe091e23fd67d3a42d00cce0b332c662ef66224edcbbc024bce8e0e2` verified and built Clang21 in sole T DIAG; native staged candidate SHA256 `ea3644db575bbf0d41fc53cadf5b9df25e7f9174c07446bfb635f0a6281329e2`; installed operating binary SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged. Real UK1.5 M68000 reset SSP `00000316`, PC `100002A2`, native SCR, WATCHDOG, PLLCR, ICEMCR=0008, ICEMSR write0007=>0000, IVR and IMR both words PASS. **First new native block `CURPC=1000517C`** is 16-bit write `0000`, mask `FFFF`, to `FFFFF008` (`IODCR`), `MMIO_WRITE_UNIMPLEMENTED`; prefetch PC `10005182`, SR `2704`. Manufacturer **MC68VZ328UM §5.2.4 Table5-4**: IODCR 16-bit I/O drive-strength register at `FFFFF008-9`, reset `1FFF`, writable mask `1FFF`, 0 selects 2mA pads, 1 selects 4mA. This operation changes electrical drive strength only, NOT GPIO logical latches/selection, CS, RAM or clocking.

**CODEX CODE ONLY, ONE CLOSED INCREMENT**: add m_iodcr default/reset `0x1FFF`, state saving, physical high-MMIO decoder at `FFFFF008`, correct word/high/low byte-lane read/write and defined bits masked `0x1FFF`; no invented analog pad currents or generic MMIO RAM. Preserve every previously closed path/byte coverage. Focused local tests & publish main; GPT handles T compile and native UK1.5 -rom and investigates next actual CPU bus failure. Do NOT research with Ghidra or implement speculative registers. Real Palm UI is not reached. This note adds no remote authorization.

---


## ICE pair code delivery — GPT native validation pending

Closed implementation of the ICEMCR/ICEMSR contract in
`PALM_UK15_NATIVE_ICE_20261025.md`. Codex performed coding, local checks and
publication only; GPT owns Clang21 compilation, T execution and analysis.
Base: canonical main `c5d6787b272a9d7d82f656a1c0a0edb03541ec02`.
Old driver SHA256:
`207bf697be4ddafc90ab4b36103d15963f7871b22a1c72ba1dd3cf1a0dceaea1`.
New driver SHA256:
`1275509bbe091e23fd67d3a42d00cce0b332c662ef66224edcbbc024bce8e0e2`.

Added two explicit physical word decoders: FFFFFD0C–FFFFFD0D (ICEMCR) and
FFFFFD0E–FFFFFD0F (ICEMSR), both reset zero and saved independently.
ICEMCR applies documented mask 005F with proper selected-lane merging;
HMDIS=0008 is accepted and read back, with no ROM/SDRAM/ordinary decode change.
Clearing HMDIS also leaves normal mode unchanged. Requests for SWEN, BBIEN,
SB, PBEN or CEN terminate with `ICE_CONTROL_MODE_UNIMPLEMENTED` before state
commit; their actual stopwatch/breakpoint/IRQ machinery is not fabricated.

ICEMSR follows the VZ manufacturer order: EMUEN=bit3, event flags=bits2..0.
Flags use W1C within the written lanes; reserved bits remain zero. A write
0007 cannot set EMUEN and cannot manufacture events. EMUEN=1 requests stop
with `ICE_EMULATION_MODE_UNIMPLEMENTED` before committing the mode or flag
changes. No ICE interrupts, hard-map or hidden CPU state modifications were
added. Registers remain ordinary readable state in the supported normal mode.
The transition logs are `DANA_ICE ICEMCR ...` / `DANA_ICE ICEMSR ...` and include
data, lane mask, resulting value and normal-mode classification.

Local verification:
- `python3 tests/ice_register_test.py`: PASS. Constant evaluation of actual
  production handlers covers reset reads, native ICEMCR=0008 plus next static
  ICEMSR=0007, word/high/low/zero masks, reserved bits, selective W1C, unchanged
  HMDIS normal decode intent, every unsupported control bit and EMUEN guard.
  Seeded flags are test fixtures, not emulated event generation.
- Complete driver g++14 C++20 `-fsyntax-only -Werror` against existing MAME
  headers: PASS. No object, linked binary or candidate SHA produced locally.
- Every preexisting out-of-class method is byte-identical except additive
  save/reset/map integration. This includes physical reset/coverage, SCR,
  WATCHDOG, PLLCR/PLLFSR, clocks, IRQ, LCD, ST and SD implementations.
- `git diff --check`: PASS. No unrelated closed suites rerun.

### GPT continuation: build and next real CPU blocker

Match the old source hash above on the same T DIAG, apply only this increment
and build the staged `source/danadiagd` incrementally using the established
Clang21 cache/command. Keep installed `bin/dana-diag` intact, historical SHA
`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
Use the unchanged UK1.5 original raw stream, SHA
`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`,
physical `-rom`, bounded observer and no register injection or firmware patch.
Follow GPT's own explicit T authorization; this handoff grants none.

Expected, not yet natively measured after this code change: the word write
0008 to FFFFFD0C at CURPC=1000515E should read back 0008, then word write
0007 to FFFFFD0E at CURPC=10005164 should leave normal-mode status 0000.
Record accepted transactions, actual next CPU address/data/mask and
CURPC/PC/IR/SP/SR, CLI/build log, candidate SHA and installed SHA readback.
IVR/IMR continuation or a next missing peripheral must be demonstrated, not
predicted. No new native blocker or Palm UI PASS is claimed by Codex.
The prior candidate aa02f3... is historical, not the newly compiled binary.


## CURRENT CODEX-ONLY CONTRACT: ICEMCR + ICEMSR — PLLCR NATIVE PASS (2026-10-25)

**New real T test and hardware research conducted HERE:** complete `docs/PALM_UK15_NATIVE_ICE_20261025.md` before making code edits (commit `4809dbb`). Published CodeX PLLCR `fb68ce6` exact source SHA256 `207bf697be4ddafc90ab4b36103d15963f7871b22a1c72ba1dd3cf1a0dceaea1`, Clang21 native build PASS, staged candidate SHA256 `aa02f3b4fcfbe3e661d6bd7532cd6ca179d9264b1219a92253a81eff8e84a708`; previous sole installed `bin/dana-diag` unchanged `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. Guest UK1.5 original ROM reset SSP `00000316` PC `100002A2`; SCR, WATCHDOG and **PLLCR 24B3→24A3 now all native PASS**. NEW first native blocked write **`FFFFFD0C`, ICEMCR, `0008`, `CURPC=1000515E`, `SR=2700`**. Next immediate original disassembly `MOVE.W #0007,(FFFFFD0E)` ICEMSR remains unexecuted.

**CODEX WORK ONLY:** implement **both adjacent ICE initialization registers** as **one source-backed, cohesive hardware module** in the current single `alphasdana.cpp` (not two fake gates). Motorola **MC68VZ328UM chapter 16 Tables16-4,16-6** ICEMCR 16-bit reset 0000 bits6/4/3/2/1/0, HMDIS bit3; ICEMSR 16-bit reset0000 EMUEN **bit3**, three W1C interrupt flags **bits2/1/0**. `0008` sets ICEMCR HMDIS, and `0007` clears ICEMSR flags while preserving normal (not ICE) mode. Caution: Linux MC68VZ328.h header bit labels for ICEMSR conflict with VZ primary manual, do not use secondary header bit mapping uncritically. Map `FFFFFD0C-F`, accurate 68k lanes, reset/save, guard unsupported genuine ICE/breakpoint/real hardmap behaviors (do not fabricate them). Preserve all previous peripherals and guest execution. Codex publishes `main` source and local tests; **GPT compiles/tests on T and analyzes NEXT first real MMIO failure**. No Codex Ghidra general investigation, no extra branches/trees/alternate emulator, no artificial PC or BigROM entry. Still no Palm OS GUI.

---


## PLLCR code delivery — GPT native validation pending

Closed contract implemented from `PALM_UK15_NATIVE_PLLCR_20261025.md`.
Codex performs implementation/local checks/publication; GPT owns T compilation,
native execution and analysis. No Codex T calls were made in this increment.

Base: canonical main `8e41f5dd449c1170adcebc46be1094203c48c0d2`.
Old driver SHA256:
`3bd7383160278ea67b00f2f827670d2dcca82704a2bdbe6aa32d844ea3643730`.
New driver SHA256:
`207bf697be4ddafc90ab4b36103d15963f7871b22a1c72ba1dd3cf1a0dceaea1`.

Added a physical-only 16-bit PLLCR decoder at FFFFF200–FFFFF201, reset 24B3,
saved register state, lane-selected writes and reserved-zero mask 3FBB.
The observed ANDI.W transaction can now read 24B3 and write 24A3. CLKEN bit4
only gates the requested CLKO output. Its logical enabled state also requires
PFSEL bit2=0 (peripheral selected), computed from the existing live PFSEL
value. No new pin waveform or calibrated electrical output is claimed.
The transition log is `DANA_PLLCR value=... clko_enabled=... pfsel=...
clock_tree_unchanged=1`; it reports output gating, not a changed CPU frequency.
No change to PFSEL handlers, PLLFSR, CPU clock updates or peripheral timers.

Unsupported writes are rejected before committing the attempted value:
- DISPLL change: `PLL_SLEEP_MODE_UNIMPLEMENTED`.
- LCDCLKSEL/SYSCLKSEL/PRESC1/PRESC2 change:
  `PLL_CLOCK_MODE_UNIMPLEMENTED`.
- WKSEL change: `PLL_WAKE_DELAY_UNIMPLEMENTED`.
These modes are not silently latched as working hardware. This is the closed
CLKEN transition implementation, not a complete PLL sleep/divider model.
SCR, WATCHDOG, original coverage, IRQ, LCD, keyboard, SPI/SD and the installed
operative are preserved. ICE handlers were not implemented speculatively.

Local verification executed:
- `python3 tests/pllcr_register_test.py`: PASS. Compile-time evaluation of the
  actual production handlers for reset read, native ANDI.W result, byte lanes,
  reserved bits, zero-mask write, CLKO/PFSEL gating, and guarded modes with
  unmodified register state after rejection. No synthetic guest execution.
- Full driver C++20 g++14 `-fsyntax-only -Werror` with existing MAME headers:
  PASS. No object, linked candidate or executable SHA produced by Codex.
- Exact comparison of production PLLFSR, clock formula, SCR, WATCHDOG, Flash
  read/write, Timer1 scheduling and SD-line methods: unchanged, PASS.
- `git diff --check`: PASS. No unrelated closed suite replayed.

### Ready for GPT: one incremental build and UK1.5 native retry

Match the old source SHA above in the sole existing T DIAG tree before applying
this increment; do not reapply SCR/WATCHDOG/coverage patches already qualified.
Build the same staged `source/danadiagd` with the established Clang21 command
and cache. Record its new SHA. Preserve `bin/dana-diag` and its original SHA
`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
Use only original UK1.5 raw SHA
`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`,
physical `-rom`, bounded run, existing observer and no guest-state injection.
Use GPT's current explicit T authorization; this document grants none.

Expected but not yet measured after this code change: PLLCR READ=24B3 and
WRITE=24A3 at CURPC=10005158, with no clock-tree retuning. Return the actual
next CPU transaction including CURPC/PC/IR/SP/SR, address/data/mask, build log,
CLI and candidate SHA. ICE writes remain static predictions until observed.
No native continuation or Palm UI PASS is claimed by this source delivery.
The prior candidate hash d6285e... is historical and is not the new binary.


## NEW AUTHORITY — WATCHDOG NATIVE PASS; PLLCR NATIVE READ FIRST BLOCKER (2026-10-25)

**Read the complete precise researched coding contract:** `docs/PALM_UK15_NATIVE_PLLCR_20261025.md` (commit `eefcbd5`). This ChatGPT chat has compiled and executed published Codex WATCHDOG commit `8b184b0` on sole T DIAG using authentic private UK1.5 -rom reset (not -quickload): source SHA256 `3bd7383160278ea67b00f2f827670d2dcca82704a2bdbe6aa32d844ea3643730`, staged candidate SHA256 `d6285e2947f2cba0c452bc00ba34d276020d26504c155b8d7b91db202b1bbf5c`, build/link PASS. Real CPU reads original SSP `00000316`, reset PC `100002a2`, executes accepted SCR, WATCHDOG writes; **first native subsequent failure** is 16-bit **PLLCR READ `0xFFFFF200`**, `CURPC=10005158`, instruction `ANDI.W #$FFEF,($0200,A0)`, next/preferred `PC=1000515C`, `SR=2704`. Motorola manual §4.4.1 Table 4-2 documents `PLLCR reset 0x24B3`; mask clears bit4 `CLKEN` → `0x24A3`, enabling CLKO output, not disabling PLL. `PLLFSR` at `0xFFFFF202` is already present and separate.

**NEXT CODEX CODE ONLY:** in same `src/mame/skeleton/alphasdana.cpp` implement true read/write 16-bit `PLLCR` at `0xFFFFF200`, reset `0x24B3`, lane-accurate write, state save, bit fields per Motorola, preserve real high MMIO and prior SCR/WATCHDOG behavior; do not fake SYSCLK divider/PLL sleep if demanded later. Build staged Clang21, native `-rom` UK1.5, report next **real CPU** MMIO/blocker, not inferred future ICE; no new gate, file branches, Ghidra work, firmware copying or alternate DIAG. Previous only installed operating binary SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` still untouched. No Palm GUI yet. Research stays in this chat.

---


## WATCHDOG guarded register delivery — GPT native validation pending

**CODEX: LOCAL IMPLEMENTATION/STATIC CHECKS ONLY. GPT: T BUILD, NATIVE RUN,
AND ANALYSIS.** Base is canonical main
`06ef23b0c536aca77daef9c4980a7325065123ce`. The previous SCR native PASS and
WATCHDOG transaction in `PALM_UK15_NATIVE_WATCHDOG_20261025.md` are delivered
research, not measurements made by Codex in this increment.

Implemented physical-only 16-bit decoder FFFFFB0A–FFFFFB0B, reset value 0001,
EN/ISEL control-lane updates, INTF W1C, reserved-bit masking, and CNTR clear on
any selected-lane write. A zero lane mask is not a write. Physical save state
includes the register. R-direct has no added MMIO decoder or running guard.
No interrupt routing, peripheral or firmware patch was added.

**Explicitly guarded subset allowed by the closed contract:** RTC-derived
count advancement and watchdog IRQ/reset expiry are NOT implemented or qualified.
An explicit write retaining EN=1 suspends with
`WATCHDOG_ENABLED_CLOCK_UNIMPLEMENTED`. At physical reset, a one-second
observation deadline also stops a watchdog left enabled without service. This
is a diagnostic deadline, NOT an emulated expiry, RTC phase, IRQ or reset. Any
actual write cancels that deadline; a disabling write proceeds normally.
Readback reports the stored register fields (CNTR starts/clears to zero);
no enabled-timer progress is claimed. The delivered register is not a complete
RTC/watchdog timing model. GPT must not label enabled timing/IRQ/reset PASS.
If enabled operation is required, return a closed timing/IRQ specification
rather than suppressing the guard or claiming a generic write success.

Expected native continuation (NOT YET OBSERVED): UK1.5 MOVE.W #0 at
CURPC=10005152 should disable WATCHDOG, cancel the guard and leave readback 0000.
PLLCR at FFFFF200 and ICE accesses remain predictions only. Do not implement
them until GPT delivers their next observed fault and closed hardware contract.

Local checks executed:
- Complete driver g++14 C++20 -fsyntax-only -Werror with existing MAME headers:
  PASS, no object or executable produced.
- `python3 tests/watchdog_register_test.py`: PASS, constant evaluation of actual
  production read/write/guard methods: native disable value, high/low/zero lane,
  status W1C, ISEL, reserved bits, CNTR clear, disabled callback and explicit
  enabled-mode guard. No guest CPU execution or timer-expiry PASS.
- `python3 tests/d8_5_physical_boot_test.py ConstantEvaluation`: PASS.
- `git diff --check`: PASS. No unrelated closed suites rerun.

Driver SHA256:
`3bd7383160278ea67b00f2f827670d2dcca82704a2bdbe6aa32d844ea3643730`.
No new binary SHA, native PC/SR or next blocker exists for this increment.
No Codex T calls, compilation on T, binary installation or firmware changes.
The delivered GPT operative hash remains historical until its next readback.

### GPT continuation

Apply only this watchdog increment to source matched against old SHA
`ac32db33a52abe8c81479fef2605ecc52ee9e62ec1477a2131a63cc55e3b72ec`.
Build the same DIAG incrementally with the existing Clang21 cache, run the
candidate without replacing the installed operative, and reuse the exact
original UK1.5 stream and observer. Respect GPT's own current remote-call
approval; this handoff grants none. Verify the FFFFFB0A=0000 word write passes,
record actual next address/value/mask and CURPC/PC/IR/SP/SR, preserve original
firmware and operative, and report the next closed correction to Codex.


## CURRENT VERIFIED UK1.5 DMAP NATIVE RESULT — WATCHDOG NEXT (2026-10-25)

**IMPORTANT: actual native test now performed by this ChatGPT chat, not CodeX**. Owner authorized a new set of five remote calls. Four were used; we did not need another. `main` Codex SCR patch `a6badeb` source SHA256 `ac32db33a52abe8c81479fef2605ecc52ee9e62ec1477a2131a63cc55e3b72ec` verified as ONLY scr_w edit, installed in SAME existing T DIAG source and compiled with Clang21 (actual compiler/link PASS), CANDIDATE `source/danadiagd` SHA256 `cdd98381dba484396ba709468cffa137b97bd8a0e955e9006ed9931b2b1ed499`, **NOT DEPLOYED** (previous only operating `bin/dana-diag` intact SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`). 0x5D0000 original unpadded UK1.5 Flas stream SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` verified and loaded via actual `-rom`; CPU reset from Small ROM SSP=0x00000316 and PC=0x100002A2. SCR write to FFFFF000 now PASS in CPU execution. NEW TRUE FIRST FAIL is **WATCHDOG** `0xFFFFFB0A`, guest `MOVE.W #0,($0B0A,A0)` at `CURPC=10005152`, 16-bit write `0000`, mask `FFFF`, CPU `SR=2704`; `DANA_PHYSICAL_BLOCKED reason=MMIO_WRITE_UNIMPLEMENTED ... pc=10005158` reports the prefetched NEXT PC, not failed opcode. MAME process exit 0 is observer stop, **NOT PALM BOOT**. No guest UI.

**AUTHORITATIVE RESEARCH & CODING INPUT**: `docs/PALM_UK15_NATIVE_WATCHDOG_20261025.md` contains real T traces, reset & candidate hashes, Motorola MC68VZ328UM §11.2.5 WATCHDOG bit/semantic contract, and static ONLY next disassembly (PLLCR, ICE, IVR, IMR). **Codex implement only the now proven missing 16-bit WATCHDOG register @ FFFFFB0A**, reset 0001, correct enable/counter/INTF/ISEL semantics, physical MMIO decode, preserving user-valid SCR fix and all existing peripheral code. Compile existing DIAG incremental, retry real UK1.5 -rom, return first new native block (do not pre-implement PLLCR/ICE just because they follow statically). No other research/Ghidra in Codex. No new branch/tree/clone, no modified ROM, no operating executable replacement until qualified. The user researches hardware HERE.

---


## Current code delivery — SCR.DMAP fix, GPT native validation pending

Implemented the closed finding in `PALM_UK15_NATIVE_SCR_DMAP_20261025.md`.
Only production method changed: `alphasdana_state::scr_w(u8)`. Removed the
incorrect DMAP=0 terminal block and replaced its misleading comment. The exact
status W1C/control assignment is unchanged; reset SCR=0x1C, save state, canonical
high MMIO map, coverage, CPU and every other driver byte are preserved.
DMAP=1 alias completeness is not claimed or implemented by this change.

Base: canonical `main@206364acf8d6065d0264ef43cc9bcccffe3d6118`, synchronized
before edits. Old driver SHA256:
`9b0e03909c21717758f9f75a31540b28f5943b377b2a0f000f7788b18885783e`.
New driver SHA256:
`ac32db33a52abe8c81479fef2605ecc52ee9e62ec1477a2131a63cc55e3b72ec`.

Local checks executed:
- `python3 tests/d8_5_physical_boot_test.py ConstantEvaluation`: PASS, including
  reset SCR, native UK F0->10 case with no CPU suspension, both DMAP values,
  selective W1C clearing/preservation, and prior coverage/decode controls.
- Complete driver C++20 `-fsyntax-only -Werror` against existing MAME headers,
  g++14: PASS; no object or executable generated.
- Entire production driver comparison excluding scr_w: byte-identical, PASS.
- `git diff --check`: PASS. No unrelated suites rerun.

**Workflow explicitly set by user: Codex develops code and performs local
verification; GPT compiles on T, runs native tests and analyzes results.**
This supersedes earlier instructions in this document assigning T compilation
or native execution to Codex. No T tool calls or installed-file modifications
were performed for this correction. No new executable SHA or next bus blocker
is claimed. The native receipt remains unchanged historical evidence.

### Ready-to-copy instruction for GPT

Use the SCR correction identified by new driver SHA above, applying only the
scr_w diff to the verified existing source on T. Do not reapply the earlier
coverage patch. Compile incrementally in the same DIAG/cache using the existing
qualified Clang21 command, measure the candidate SHA and run the exact same
UK1.5 original 0x5D0000 stream through physical `-rom`, without installation or
changes to the operating binary. Follow the user's current T authorization;
this handoff grants none. Record PC/CURPC/IR/SP/SR, address/data/mask and the
first actual next blocker. Absence of SCR_DMAP_MODE is expected but not yet
natively measured. WATCHDOG at FFFFFB0A and PLLCR at FFFFF200 remain static
predictions: do not implement or report them as encountered without evidence.
Return the trace and a closed correction specification to Codex. Palm UI is
still unproven; preserve the original operative hash and original firmware.

## ÚLTIMO RESULTADO REAL, AUTORITATIVO PARA CODEX — UK1.5 NATIVO EN T, SCR.DMAP (2026-10-25)

**Este párrafo sustituye cualquier instrucción histórica que ordene a Codex investigar firmware o implementar arranque Big ROM asistido.** La investigación de hardware se hace en este chat; **Codex solo codifica un cambio concreto**.

**EVIDENCIA:** `docs/PALM_UK15_NATIVE_20261025.json` (ejecución nativa real) y `docs/PALM_UK15_NATIVE_SCR_DMAP_20261025.md` (**causa documental y contrato de codificación completo; léelo primero**). Se compiló en T el parche de cobertura `main@07443b2` con Clang21, sin errores; candidato SHA256 `a335583ebb7cc1f29fd7b8d6f5f22f1ddfb72a2e964b668db40ebbd4e09b5984`, binario operativo intacto `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. Se extrajo privadamente UK1.5 120/120 Flas, `0x5D0000` bytes, SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, sin relleno ni publicación ROM. CPU hizo vectores reales SSP=`00000316`, reset PC=`100002A2`, Small ROM ejecutó a `CURPC=1000514C` y se bloqueó erróneamente cuando escribió `SCR=F0` en `FFFFF000` (motivo `SCR_DMAP_MODE`). **Manual Motorola cap.5:** DMAP=0 elimina alias duplicados `XXFFF000`, pero mantiene los registros en `FFFFF000`. El código actual `scr_w` bloquea esta operación válida.

**SIGUIENTE INCREMENTO CODEX CERRADO:** Cambiar SOLO `alphasdana_state::scr_w(u8)`: preservar W1C y reset SCR, retirar bloqueo por `DMAP=0` y comentario falso; conservar decodificación interna superior. Compilar incrementalmente con Clang21 en único DIAG y repetir UK1.5 `-rom` en binario candidato sin instalar, devolviendo el primer próximo bloqueo real con CURPC/máscara. No hacer Ghidra, investigación abierta, refactor ni nuevas ramas; no preimplementar Watchdog/PLLCR basándose en predicción estática. El último código intacto de Small ROM predice escritura al WATCHDOG `FFFFFB0A`, luego PLLCR `FFFFF200`, pero **AÚN NO EXISTE PRUEBA NATIVA** para esos registros. El firmware no ha arrancado Palm OS hasta su UI. La autorización previa para Commander ya agotó 5/5 llamadas y no se renueva mediante estos documentos.

---


**This file is the complete executable work brief for Codex. Start implementation, not a proposal or additional handoff.** User-facing conversation: Spanish. Git commits, code and repository technical records: English.


## Handoff para GPT — ejecutar UK1.5 y analizar el primer bloqueo real

**Solicitud actual: realizar la ejecución y su análisis en GPT. No reabrir la investigación de firmware ya entregada ni delegar otro plan a Codex.**

### Estado concreto que se entrega

El código de cobertura está implementado en `main`. Procedencia local:
`23830f56bd14cfa49ddc5a9436fb72a570b7e93b`; al publicarlo por la conexión GitHub
el SHA del commit cambia. Verificar el contenido del controlador mediante SHA256
`9b0e03909c21717758f9f75a31540b28f5943b377b2a0f000f7788b18885783e`.
Base canónica anterior: `0a159bd2d208c32eab6c987e2880cd78fe00a3a5`.
No ramas, clones ni worktrees nuevos.

Cambios funcionales exclusivamente en `src/mame/skeleton/alphasdana.cpp`:
acepta tamaños pares originales, conserva la asignación exacta, registra cobertura
para streams no potencia de dos, bloquea lecturas no suministradas con
`FLASH_BYTES_NOT_SUPPLIED`, y registra palabras/máscaras de los vectores reales.
Para el stream parcial usa una ventana experimental de reset de 16 MiB, con
bits bajos de dirección; **esto no acredita capacidad, cableado o espejos del chip**.
No convierte el tamaño del stream en un módulo, no agrega bytes y no altera
el reset ni los registros CPU. CSA/CSD/DRAM y protecciones siguen como estaban.

`tests/d8_5_physical_boot_test.py` actualiza únicamente la evaluación de tamaños
y prueba último word disponible, primer word ausente, ausencia de wrap y CSA
programada. Las pruebas enfocadas y compilación de cabeceras pasan; no hubo
compilación/enlace Clang21 ni ejecución UK. La suite histórica completa no se
ha declarado PASS: sus fallos de preservación anteriores siguen documentados.

### Fuente privada ya resuelta: usar UK1.5 coherente

Leer `docs/PALM_UK_SMALLROM_RESEARCH_20261025.md` y el registro JSON existente.
Archivo Drive `1LY_Ykm3RysWe4vutxWeFRnwSTCxlIcFg`,
`AlphaSmart_Dana1_5_Flash.zip`, SHA256
`1a0256e35c11c7455a58738f05218e1e290b8d381a5742467f1a512ac25c14fc`.
Ruta esperada en T: `/home/spc/Projects/Dana-OS3K/firmware/research-only/`.
Contenedor anidado: `Dana UK 1.5 update/ROMUpdater_enUK150R1.ZIP`;
PRC `ROMUpdater_enUK150R1.prc`. Reutilizar `resources` y `payload` de
`tools/palm_updater_audit.py`: 120 recursos Flas, quitar solamente el checksum
final validado por suma de bytes de cada recurso y concatenar por ID.
Resultado exacto: **6,094,848 bytes / 0x5D0000**, SHA256
`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.
Cobertura suministrada: `[0x00000000,0x005CFFFF]`.

Small ROM auténtico UK en offset 0, Big ROM UK en 0x8000. Valores de entrada
**esperados del archivo, todavía no medidos en una ejecución UK**:
SSP/campo initStack=0x00000316, PC=0x100002A2; JMP PC-relativo a
0x10000316. La entrada declarada del Big ROM es 0x1000C80A.
No mezclar UK/US, no agregar cola FF, no inyectar registros y no usar quickload.
El prefijo Small ROM ya fue encontrado: no seguir afirmando que falta de todas
las fuentes. La geometría física completa continúa sin acreditar.

### Único entorno y protección del operativo

T: `spc-HP-t640-Thin-Client`, ID conocido
`dee0b4b6-578a-41a5-88de-73dbeb808983`; su disponibilidad actual debe comprobarse.
DIAG: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`.
Fuente en `source/`, instalado `bin/dana-diag`; único artefacto intermedio de
la misma compilación `source/danadiagd`. No ejecutar otro emulador.
Último instalado verificado y restaurado:
`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
Última fuente T conocida antes del incremento rechazado:
`beb460df6e04013d1bc24c542b89276a088cf06fc0e96e52fedd566c57cc7eda`.
Si algo difiere, reconciliar sin sobreescribir trabajo del usuario.

**Autorización remota pendiente.** Las cinco llamadas anteriores se consumieron
en el ensayo US; no autorizaron esta nueva campaña. La revisión automática
rechazó expresamente el intento UK por falta de autorización renovada para
compilar, sustituir temporalmente el ejecutable instalado y ejecutar firmware.
La llamada rechazada no hizo nada en T. Este handoff no renueva el cupo y no
permite eludir el rechazo con otros canales. Obtener consentimiento explícito
para el número de llamadas y el procedimiento de calificación temporal antes
de actuar remotamente. Conservar el original y restaurarlo si el candidato
no queda calificado; no promover un candidato por el simple exit code 0.

### Ejecución concreta pendiente, una vez autorizada

1. Verificar hashes y ausencia de otra compilación; preservar el operativo.
   Integrar el diff del controlador contra la fuente verificada del mismo árbol.
   Preparar únicamente el stream privado UK exacto y el observador ya publicado.
2. Inspeccionar `make -n` y compilar con la caché existente. La orden calificada
   anterior es:
   `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21`.
   Exigir un alcance incremental: controlador, archivo y enlace necesarios;
   no REGENIE ni reconstrucción general sin una causa concreta.
3. Medir SHA del candidato. Ejecutar únicamente el DIAG con perfil
   `asmdana -rom PRIVATE_UK15.raw`, sin `-quickload`, sin parches de firmware.
   Utilizar un límite de tiempo externo que termine realmente el proceso.
   El observador existente requiere `DANA_PALM_TRACE=PRIVATE_LOG`; para autoboot
   usar `-autoboot_script PRIVATE_OBSERVER.lua -autoboot_delay 0`.
   Ya usa SP y `emu.add_machine_stop_notifier`, con suscripción retenida;
   **su corrección completa todavía requiere validación nativa**.
4. Reutilizar debugger/trace nativo y logs del controlador para registrar los
   cuatro accesos de reset, SSP/PC/SR, salto Small ROM, cambios MMIO y primera
   dependencia no resuelta. CURPC es la dirección relevante; IR puede contener
   la siguiente instrucción prefetched. No tomar lecturas del debugger como
   accesos CPU ni ocultar el primer bloqueo. Guardar CLI, errores y códigos
   reales. Si llega a LCD, guardar evidencia del framebuffer del invitado.
5. GPT analiza la evidencia contra el contrato Motorola y la investigación
   entregada. Un fallo local inequívoco puede corregirse dentro del alcance y
   autorización restantes; una discrepancia de hardware no investigada se
   devuelve con dirección, máscara/anchura, registros y última instrucción.
   No inventar respuestas MMIO, sectores o una interfaz Palm anfitriona.

### Entrega y aceptación

Devolver commit/rama y archivos, salida de compilación, SHA candidato, CLI,
SSP/PC/SR **medidos**, primer salto, última instrucción correcta, primer bloqueo
concreto y estado/hash del operativo. Actualizar estos mismos documentos y
`docs/PALM_UPDATER_DERIVED_COLD_BOOT_20261025.json`.
Solo declarar arranque completo si Palm OS genera su UI mediante CPU y
framebuffer emulados. Si no puede ejecutarse, clasificar como bloqueo de acceso;
si se ejecuta y encuentra dependencia no soportada, reportar bloqueo técnico
real. Nunca convertir un ensayo parcial en PASS de Palm OS.

## UK1.5 coverage implementation — current coding result

**IMPLEMENTED / STATIC_PASS / REMOTE_AUTO_REVIEW_BLOCKED / NOT_NATIVE_TESTED.**
Based strictly on the delivered UK research, the existing physical loader now
accepts even raw stream lengths in its original 128 KiB–16 MiB bounds. It
allocates exactly the supplied byte count; the existing generic cartridge API
retains this exact size. Non-power-of-two inputs log supplied coverage and
`UPDATER_DERIVED_RESET_EXPERIMENT`; they do not declare a chip capacity.
Partial-stream reads use the existing maximum 16 MiB reset decode window as
an explicitly unqualified experimental address window, then enforce the exact
supplied boundary. They never modulo by the stream length or read allocation
padding. A missing word logs address, array offset, lane mask and supplied size,
then suspends with `FLASH_BYTES_NOT_SUPPLIED`. The established power-of-two
array aliases and configured chip-select/DRAM/protection rules remain intact.
No physical mapping fidelity is claimed by admitting this experiment.

Reset still fetches the original words through the CPU bus; those four reads
now log values and masks. No SSP/PC injection, guest-byte modifications, RAM
seed or synthetic prefix was added. Existing native snapshots and the fixed
Lua observer provide the remaining compact CPU/MMIO trace on an authorized
run. No peripheral implementation or reset/lifecycle method was changed.

The exact original UK1.5 nested PRC was processed using the existing parser:
120 Flas chunks, every byte-sum valid, 6,094,848 bytes, SHA256
`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.
Private original stream is `/workspace/work/palm-uk/UK15.raw`, outside Git.
Its supplied array coverage is 0x00000000–0x005CFFFF. This is preparation of
already researched bytes, not new firmware or hardware research.

Checks executed: full driver g++14 C++20 `-fsyntax-only -Werror` with pinned
MAME headers PASS; focused existing constant-evaluation test PASS, extended for
partial final word, first missing word, no modulo wrap and programmed CSA;
existing Lua mock PASS; comparison of all existing out-of-class peripheral and
lifecycle methods PASS; whitespace check PASS. The old historical preservation
suite was not rerun or relabelled as passing. No object or binary was built.

**Remote action rejected, not executed.** Automatic approval review rejected
exact-match staging, incremental Clang21 build and the same canonical DIAG's
native candidate qualification because the prior Commander quota is exhausted
and renewed remote authorization is absent. It also identified temporary
replacement of the installed emulator for qualification as requiring explicit
approval. No T source/image/binary was modified by the rejected call. No native
SSP/PC/SR, instruction trace, LCD output, candidate binary SHA or new guest
blocker exists for UK1.5 yet. The final delivery is therefore BLOCKED at remote
execution, not a claim of a firmware or hardware failure.

The same existing JSON receipt records this increment under
`uk15_coverage_increment`. `main` was synchronized to exact checkpoint
0a159bd2d208c32eab6c987e2880cd78fe00a3a5 through GitHub readback before editing;
no branch, clone or worktree was created. The single operating executable
remains unmodified; its SHA must be freshly checked on an authorized preflight.

## INSTRUCCIÓN RECTORAL ACTUAL — INVESTIGACIÓN AQUÍ; CODEX EXCLUSIVAMENTE DESARROLLO (2026-10-25)

**Decisión expresa del usuario:** la investigación del firmware, ingeniería inversa y conclusiones de hardware se realizan en ESTA conversación de ChatGPT. **Ghidra está instalado en T y es una herramienta de NUESTRA investigación**, no un paquete de tareas de descubrimiento indefinido que Codex deba asumir. **Codex solo desarrolla, compila, prueba e integra cambios de código cerrados y especificados a partir de hallazgos entregados aquí.** Esta sección tiene autoridad sobre cualquier instrucción anterior del archivo que pida a Codex investigar con Ghidra o diseñar una vía de arranque asistido.

### HALLAZGO MATERIAL Y NUEVA FUENTE AUTÉNTICA

**YA ENCONTRAMOS el Small ROM en el ZIP original del usuario, dentro de los ACTUALIZADORES UK 1.5 y UK 1.2.** Investigación directamente reproducida aquí sobre los bytes privados del archivo Drive. Ver informe con tamaños y SHA, checksums 391/391, doble PalmCard, comienzo del código de arranque, distinción UK/US y limitaciones de geometría: **[docs/PALM_UK_SMALLROM_RESEARCH_20261025.md](PALM_UK_SMALLROM_RESEARCH_20261025.md)**. No pedir a Codex repetirla ni especular que el primer bloque 0x8000 falta de todas las fuentes.

Resultado esencial: `ROMUpdater_enUK150R1.prc` contiene 6,094,848 bytes `Flas` concatenados, **Small ROM en offset 0**, Big ROM en **offset 0x8000**. El encabezado Small ROM posee `initStack=0x00000316, resetVector=0x100002A2, signature=FEEDBEEF, hdrVersion=5, flags=0x0040`; en `0x100002A2` hay `JMP (0x72,PC)` que salta al código real de la imagen en `0x10000316`. Big ROM en 0x8000 con entrada `0x1000C80A`. `ROMUpdater_enUK120R2.prc` también incluye Small ROM desde offset 0 y Big ROM en 0x8000, con el mismo vector Small `0x100002A2` y Big `0x1000C776`. Las versiones estadounidenses contienen solo el encabezado Big ROM desde offset cero; **NO mezclar UK Small con US Big** para simular una ROM genuina. Los archivos privados originales se conservan íntegros. Es contenido de paquetes oficiales, pero no está acreditado que incluya todos los sectores/bytes de la Flash física completa.

### ÚNICO OBJETIVO DE PRODUCTO: RESET FÍSICO FIEL MC68VZ328

El único `bin/dana-diag` debe ejecutar vectores reales suministrados por un firmware original desde la selección CSA0 del DragonBall VZ, seguir el Small ROM auténtico, configurar CS/DRAM/MMIO genuinos y arrancar Palm OS con LCD/teclado procesados por el invitado. No inyectar SSP/PC, falsear bootloader, construir cabecera Small ROM, cambiar 0x0 a RAM para ignorar error, generar pantalla Palm en anfitrión, ni presentar un arranque asistido como fiel. Manual Motorola MC68VZ328UM caps. 6, 9.3; comprobar topología de Flash mediante registros y evidencia antes de acreditar fidelidad eléctrica.

### PRÓXIMO CONTRATO DE CODIFICACIÓN PARA CODEX

**Entrada autorizada para implementar:** en la rama `main` del único `SamDelorean/DANA-emu` trabajar solamente sobre el controlador físico existente y utilidades de diagnóstico estrictamente necesarias para una **prueba de cold reset nativo a partir de la IMAGEN UK1.5 coherente de un único actualizador original**. No inventar prefijo: el original UK *sí lo contiene*. El `firmware_load` actual rechaza longitudes no potencia de dos: la imagen UK1.5 `0x5D0000` y UK1.2 `0x3C0000` son contenidos originales de los paquetes, pero **no dimensiones certificadas del chip**. Implementar una prueba de memoria **con cobertura explícita de bytes conocidos** que detecte y detenga cualquier lectura de regiones no proporcionadas, manteniendo los flujos de selección de Flash y vectores por reset real; no aceptar relleno como bytes originales, no ocultar accesos desconocidos, no modificar firmware ni comandos NOR sin fuente. Calificar como `UPDATER_DERIVED_RESET_EXPERIMENT` hasta demostrar el mapa físico completo. No reemplazar el DIAG instalado antes de PASS real. Mantener funcionalidades cerradas de 81 teclas, LCD, doble SD, UART, táctil y EmuTOS.

**Criterio de devolución a ESTA conversación:** Codex entrega exclusivamente diff/commit, compilación incremental y TRAZA REAL de CPU SSP/PC/SR y primer acceso MMIO/Flash/RAM o avance hasta UI, con la dirección de instrucción correcta. Nos encargamos AQUÍ de interpretar la evidencia, decidir requisitos físicos y diseñar el siguiente incremento cerrado. No solicitar a Codex plan general, búsqueda de fuentes, nueva investigación de firmware, tareas en Ghidra ni otra arquitectura. Sus llamadas a T dependen de autorizaciones explícitas en su entorno; esta transferencia no otorga permisos nuevos.

**Código existente protegido:** `bin/dana-diag` instalado y calificado SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. No ramas paralelas, clones, nuevos DIAG ni publicación de bytes comerciales.

---

## HISTORICAL RESEARCH — 2026-10-25 — POSE Big ROM file structure (NOT AUTHORIZED AS BOOT STRATEGY)

**This section adds NEW research and supersedes any inference that the contents at byte 0 of `Dana_US15_Flas.raw` are original physical address zero. Preserve the 5/5 exhausted T Commander budget and the currently qualified installed executable. This source-based analysis is NOT a Palm boot or a native test.**

### A. The PalmCard at payload offset zero is a ROM CARD HEADER — not evidence of physical reset location

Two independent source implementations identify the initial fields of a PalmCard (`CardHeaderType`) as `initStack`, `resetVector`, `signature`, `hdrVersion`, `flags`, and a **separate `bigROMOffset`**. The Debian `romeo` ROM inspector prints those exact fields and its Big ROM and HAL offsets (read-only code):
- https://sources.debian.org/src/romeo/0.5.0-9/output.c/#L45 (see `Output_CardHeader`; the website's rendered source line is around `818-873`).
- `cloudpilot-emu/pose-original@97b10711fe4ca50c1bd47072378eaab26ba8e81d`, `SrcShared/EmROMReader.cpp`, `AcquireCardHeader`, and `SrcShared/Hardware/EmBankROM.cpp`, `Card::CheckCardHeader` / `LoadROM`.

Our **existing verified private header bytes** (NOT included in Git): US1.5 offset 0 = `000048fe 1000c80a feedbeef 00050040`, US1.2 = `0000486a 1000c776 feedbeef 00050040`. Thus `hdrVersion=5`, `flags=0x0040`. POSE `EmROMReader::AcquireCardHeader` explicitly identifies `flags & 0x0040` as **68VZ328**, consistent with Dana's MCU. `0x48FE`/`0x486A` are the card-header init-stack fields, not proof that this header was located at physical Flash offset zero.

**Prior Codex analysis (already recorded elsewhere in this same handoff)** independently confirmed candidate base **`0x10008000`** from literal use in each updater `code/1` and each header at byte `0x68`. It checked coherent entry instruction paths when using that base: US1.5 `0x1000C80A - 0x10008000 = 0x480A`, US1.2 `0x1000C776 - 0x10008000 = 0x4776`. Under WRONG zero-origin placement the offsets became `0xC80A` / `0xC776`, and US1.5 entered `PrvConvertIToA`, where a real `CLR.B (A4)` targeted zero. This **explains the old observed 0-address write** without allowing any Flash writes or changing address zero to RAM. The absolute physical boot region `0x10000000..0x10007fff` is still **unverified/missing**; check actual ROM header structure for the precise meaning of `0x68` and do not infer physical geometry exclusively from this literal.

### B. A ready-made REFERENCE IMPLEMENTATION of the missing-SmallROM case exists: POSE

Pinned official-origin emulator code: **`cloudpilot-emu/pose-original@97b10711fe4ca50c1bd47072378eaab26ba8e81d`, `SrcShared/Hardware/EmBankROM.cpp`, function `EmBankROM::LoadROM`**:
https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Hardware/EmBankROM.cpp

It explicitly handles ROM files containing BOTH **Small ROM + Big ROM** and files containing **only Big ROM**. Its algorithm: validate PalmCard header; derive `bigROMOffset` from header for modern versions (or `0x3000` for v1), determine whether a second valid card header exists at the advertised offset; if only Big ROM, reserve the missing prefix in an emulator buffer, relocate the supplied Big ROM accordingly, fill unknown prefix with `0xff` and COPY ONLY the Big ROM header into Small ROM's header position for emulation. It then detects VZ compatibility and derives a *temporary* ROM base from `cardHeader.resetVector & 0xFFF00000` until chip selects are configured. **This is a POSE emulation convenience, NOT proof of authentic Small ROM bytes or physical power-on reset code.** Do not copy GPL implementation into BSD-licensed MAME: reimplement the behavioral contract independently if necessary.

Corroboration: older xcopilot-derived emulators also document that many POSE `.rom` files omit Small ROM; old Palm debugger documentation distinguishes its SmallROM bootstrap from BigROM. These corroborate architecture **across Palm devices**, not Dana's exact protected sector size. Source references:
- https://www.cypherpunks.ca/zaurus/ (section `QCopilot`; generic Palm, not VZ-specific);
- https://www.cs.trinity.edu/~jhowland/class.files.cs3194.html/palm-docs/Development%20Tools%20Guide.pdf (SmallROM vs BigROM; consult only necessary excerpt).
- Historical Dana-source verification in `SamDelorean/Dana-OS3K`, `docs/05-ROM-DANA-ACTUALIZADORES.md`; the original update `Flas` resource data and checksums are already validated.

### C. Exact next engineering task for Codex (DO THE WORK, not another plan)

**C1 — one read-only source/firmware inspection** (no hardware/emulator run needed): reuse `tools/palm_updater_audit.py` (already exists, supports `--candidate-base 0x10008000`) and the actual private US1.5/US1.2 PRCs. Independently parse `CardHeaderType` field offsets using POSE `EmROMReader.cpp` / Palm header definitions, including `bigROMOffset`, `checksumBytes`, and `halCodeOffset`. Determine whether the source stream is solely Big ROM and the actual missing-prefix extent. Check for a second valid PalmCard at advertised offset; compare US1.2 vs US1.5; validate entry branch and disassembly from offsets `0x480A` / `0x4776`. Produce **only hashes/field values/disassembly observations**, not private ROM bytes. Investigate original update programming destination offsets if the header alone does not settle exact physical position.

**C2 — HISTORICAL NOTE; DO NOT IMPLEMENT AN ASSISTED BIG ROM BOOT.** The previously contemplated POSE-compatible Big ROM synthetic startup is explicitly **withdrawn by the user's latest hardware-fidelity mandate**. Keep the POSE source above as a structural clue only: use it to distinguish PalmCard metadata, Big ROM, and missing Small ROM; do not add an alternate boot profile, inject SSP/PC, fabricate first-sector vectors or change the physical loader to accept an updater as a complete ROM. Instead, use Ghidra on T to identify the original boot block's address, NOR sector layout and updater write coverage, and recover genuine bytes if present. If absent, document the precise region and evaluate a *read-only* authenticated hardware dump only with explicit owner consent.

**C3 — prioritize authenticated physical cold boot as the ONE product target.** Once genuine complete SmallROM contents become available, map full Flash, execute actual CPU reset fetch at original physical vectors and prove transitions from SmallROM to BigROM and then Palm UI. Never quietly use BigROM-assisted injected PC as physical reset, or treat a padded Flash array as a recovered dump. Protect canonical installed DIAG SHA `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`; stage/atomically install only a verified successor.

**C4 — acceptance:** (a) read-only exact header/layout report; (b) visible native MAME 68k PC/SP/SR and guest-produced Palm framebuffer via hardware accesses in the one DIAG; (c) interactive Palm keyboard events using the qualified ST/SPI2, then Palm startup/launcher; (d) no regression to current keyboard/SD/LCD/EmuTOS. For physical fidelity additionally demand byte-authenticated SmallROM and actual reset fetch. On any blocked step, deliver *one* decisive actual guest CPU+bus blocker and the minimum further evidence—not a new program of gates.

**Key distinction (CURRENT)**: The sole accepted product is authentic MC68VZ328 cold reset through real boot ROM. BigROM-only POSE workarounds are useful for understanding file format but expressly NOT allowed as an implementation or interim boot deliverable. No additional T calls are authorized from this handoff; actual Codex machine access and permissions must come from the user.

---

## Current native result — 2026-10-25, authorized five-call T intervention

**INCREMENTAL_BUILD_PASS / US15_NATIVE_ROOT_CAUSE_CONFIRMED /
ORIGINAL_BINARY_RESTORED / PALM_UI_NOT_BOOTED.**

The user explicitly renewed authorization for **up to five Desktop Commander
calls** after the source-only stage below. Exactly **5/5** were used:
preflight, exact-match staging plus make dry-run, incremental build/qualification,
process output, and error readback plus native retry. No sixth call or remote
operation remains running from this intervention.

Preflight independently verified installed SHA
`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`,
original driver SHA
`bcd61b82ae7259613a853b329b3b0586e13b68387e3192c24fde3c1e72afbe4b`,
and original US15/US12/US15 PRC sizes and hashes. Only the two exact-matching
physical diagnostic methods were replaced in the existing T source. Modified
driver SHA is
`beb460df6e04013d1bc24c542b89276a088cf06fc0e96e52fedd566c57cc7eda`.
The old private US15 attempt was still running after **09:41:20**; only its
verified wrapper/timeout/emulator PIDs 25124/25198/25199 were terminated, avoiding
its wrapper automatically launching the next obsolete trial.

The make dry-run selected one driver compilation. Actual **Clang 21.1.8 build
exit 0** compiled `alphasdana.cpp`, archived `libmame_danadiag.a` and linked the
same `danadiagd` intermediate, using the existing cache and command recorded in
[the existing receipt](PALM_UPDATER_DERIVED_COLD_BOOT_20261025.json).
Candidate executable SHA:
`7d5f9bbe05311e093ea1e4f512927977daba1b459a3a00d41ad9417b147c763e`.
No donor tree, emulator variant or new branch was created.

Candidate tests used only the canonical `bin/dana-diag` path, with an exact
non-executable backup and unconditional restoration. The first US15 and US12
attempts exited **3** because this MAME exposes **no `emu.register_stop`**.
They did enumerate the actual CPU states, including SP and excluding A7, but
failed before guest tracing. This was an observer defect, not a new guest
hardware failure. A second defect was fixed locally: autoboot scripts run after
machine start, so registration of a later start callback cannot attach to the
current session. The final source observer starts immediately and uses
`emu.add_machine_stop_notifier`, retaining its subscription. Its updated mocked
API test rejects unsupported API names. **That final observer fix has not been
redeployed or retested natively; the five calls are exhausted.**

The fifth call repeated **US15 without Lua or debugger**, using the same
preexisting padded zero-origin experimental array; no new or repaired image was
created. One virtual second, **process exit 0**, produced:
```
DANA_PHYSICAL_WRITE address=00000000 data=0000 mask=ff00
DANA_PHYSICAL_BLOCKED reason=FLASH_COMMAND_SET_UNVERIFIED address=00000000 data=0000 pc=1000c812
DANA_PHYSICAL_CPU curpc=1000c80e ir=244c sp=000048fe usp=00000000 sr=2704 a4=00000000
DANA_PHYSICAL_DECODE csa=00b0 csd=0200 csgba=0000 csgbd=0000 csugba=0000 csctrl=0000/1000/9c00 dram=0000/0000/003c/0000
```
This **natively confirms CLR.B (A4) at 0x1000C80E**, writing the upper byte lane
at address zero with A4=0. It is the static PrvConvertIToA instruction found
below. `IR=244C` is the *next prefetched instruction*, not CLR.B's opcode:
pinned MAME `m68000-sdf.cpp::clr_b_ais_df` advances m_ir/m_pc before issuing
the data write. CURPC, lane mask, register and disassembly must be considered
together. No RAM/Flash bypass is justified by this failure. US12 has matching
static placement evidence but **no successful native trace** in this campaign.

**Remaining authenticated-input dependency:** the updater payload's evidenced
placement at 0x10008000 leaves the original initial Flash prefix and separate
reset/header contents unidentified, preceding offset 0x8000. No part geometry,
protected-sector values, physical reset vectors or bytes were invented. Correct
payload placement alone does not establish a complete physical Flash image.
The root cause of the old first write is now observed, but authentic Palm UI
boot remains **false**, not a PASS inferred from exit code 0.

Final readback independently measured restored canonical binary SHA
`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
The candidate was **not promoted**. Its intermediate and private build/receipt
files remain inside the same DIAG root at `work/palm-boot-5080ce9`.
No unrelated ST81, SD or GUI campaign was rerun. Existing peripheral code is
unchanged; diagnostic success does not requalify all peripherals.

## Historical source-only result — 2026-10-25 (before renewed T authorization)

**STATIC_ROOT_CAUSE_EVIDENCE / DIAGNOSTICS_IMPLEMENTED / PALM_NOT_BOOTED.**

The previous write is explained by a concrete image-layout discrepancy, rather
than evidence that address zero should accept RAM writes during CSA boot:

| Check | US 1.5 | US 1.2 |
| --- | --- | --- |
| Verified Flas resources, consecutive IDs, valid byte sums | 119, 2000–2118 | 75, 2000–2074 |
| Concatenated payload size | 0x5C8000 | 0x3A8000 |
| Header PC field | 0x1000C80A | 0x1000C776 |
| Entry offset under previous zero-origin array | 0xC80A | 0xC776 |
| Nearby byte clear through A4 | 0xC80E | 0xC77A |
| Entry offset with payload base 0x10008000 | 0x480A | 0x4776 |
| PC-relative entry jump target (payload offset) | 0x48FE | 0x486A |
| Updater code/1 literal 0x10008000 offset | 0x978 | 0x900 |

Downloaded the exact source archive through connected Drive file
`1LY_Ykm3RysWe4vutxWeFRnwSTCxlIcFg`; archive, both PRCs and both extracted
payload hashes match section 1. No originals modified, padded image created,
ROM uploaded, or firmware bytes committed. Private reports and temporary bytes
are outside the repository in `/workspace/work/palm-boot/`.

At the old US15 entry, linear disassembly gives a move from D0 to D3, conditional
backward branch, then **CLR.B through A4 at guest 0x1000C80E**, inside
PrvConvertIToA. This matches a zero write through a reset-valued A4 and the old
prefetch PC 0x1000C812. The previous receipt does not contain CURPC, IR, A4 or
lane mask, so this is static identification of the consistent offending
instruction, not a newly observed native bus trace. A CLR.B bus transaction
must not be described as a guest word-write solely from the 16-bit handler.

Both payload headers contain 0x10008000 at offset 0x68; the updater explicitly
loads that address before reading version metadata. With this base, both PC
fields land on a coherent entry jump rather than the conversion routine. In
US15 the entry proceeds to the payload's 0x48FE startup dispatch, computes its
base using the PC-relative offset at 0x48FA, then uses header offset 0x7A
(0x7063A) to dispatch to board startup. That entry jumps to payload 0x71A2E:
real VZ MMIO initialization, followed by CSA group base 0x10000000,
CSA=0x018D, and checks for a separate Palm header at guest 0x10000000
(and 0x10400000 for the other bank). Later instructions initialize CSD and
DRAM/SDRAM. These are disassembled instructions, not executed events.

**Missing authenticated input:** with the evidenced 0x10008000 payload
placement, no original bytes have been recovered for the preceding Flash
0x00000000–0x00007FFF region (guest 0x10000000–0x10007FFF once mapped),
including its reset vectors and separate initial card header. The exact
physical part, sector protection and contents remain unverified. The archive
alone does not establish these missing bytes. Do not fill that prefix, move
PC/SP from the host, or reinterpret the updater header as physical reset
vectors. Placement evidence does not establish a complete chip image.

Implementation in the same driver: terminal physical failures now record native
CURPC/IR/SP/USP/SR/A4 and CSA/CSD/group/control/DRAM state; rejected writes also
record the lane mask. No extra guest memory reads, memory decoding changes,
Flash write bypass, CPU state injection or changes to existing peripheral
functions. `tools/palm_boot_observer.lua` uses the actual `SP` binding, lists
available bindings, retains read/write taps, limits output to 512 events and
marks UI boot unproven. `tools/palm_updater_audit.py` verifies resource structure,
consecutive IDs, byte-sum checksums and hashes; optional binutils disassembly
is written only to the explicitly chosen private report.

Executed validation:
- Full driver: g++ 14, C++20 `-fsyntax-only -Werror` against the existing MAME
  donor headers, PASS. **No Clang21 object/link or native executable built.**
- Six parser error/ordering/checksum tests, PASS.
- Lua mocked API test via `texlua`, PASS (SP, unavailable optional bindings,
  unchanged CPU values, byte-lane logging, event cap and trace close).
- Existing D8.5 constant-evaluation test, PASS. Its old preservation suite has
  eight failure records across three test methods, identically reproduced
  against untouched `f73aba8` and the new driver; zero errors. It predates later
  ST81/SD/reset changes. Do not report the whole historical suite as PASS.
- Whole-driver text comparison against f73aba8 after removing just
  physical_block/physical_w: identical, PASS; git diff whitespace check PASS.

Repository continuity: checkpoint 3dde150 is the parent of starting f73aba8;
the cached origin/main ba40acd is an ancestor 160 commits behind. Renamed the
provided local `work` branch to `main`; no branch, clone or worktree created.
`git fetch origin main` failed because the configured proxy refused connection;
remote HEAD freshness and push are not verified.

Access correction: Cloud has neither T filesystem nor its Clang21 build cache.
Desktop Commander discovery subsequently found `spc-HP-t640-Thin-Client` online,
ID `dee0b4b6-578a-41a5-88de-73dbeb808983`. Discovery only; no process launched,
T file read/written, build, replacement or guest run. Section 5's explicit
exhausted remote-call authorization remains in force. The installed binary
hash is still historical, not independently remeasured in this intervention.

Reproduce static auditing (set LD_LIBRARY_PATH for the existing cached binutils):
```
python3 tools/palm_updater_audit.py PRIVATE_US15.prc --candidate-base 0x10008000 --objdump M68K_OBJDUMP --output PRIVATE_REPORT.json
python3 tests/palm_updater_audit_test.py
texlua tests/palm_boot_observer_test.lua
```
Native CLI **not run** (requires authentic complete Flash and authorized T access):
```
DANA_PALM_TRACE=PRIVATE_TRACE /home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag/bin/dana-diag asmdana -rom PRIVATE_AUTHENTIC_FULL_FLASH -autoboot_script tools/palm_boot_observer.lua -seconds_to_run 2 -log
```
Do not use either extracted updater payload as PRIVATE_AUTHENTIC_FULL_FLASH.

## 0. Product outcome and exact starting point

**Deliver a working AlphaSmart Dana stock Palm OS startup in the one existing MAME-based `dana-diag`.** Use actual MC68VZ328 68k instruction execution, actual reset/Flash/DRAM/chip-select/MMIO and the already present user-owned Palm firmware. Reach a genuine, guest-generated Palm OS startup/UI if achievable from these files. If the files lack necessary boot sectors or other original hardware behavior, prove that exact missing dependency with CPU/disassembly/bus evidence; never invent code, suppress blocked accesses, or report a successful boot without genuine guest execution.

- Repository: https://github.com/SamDelorean/DANA-emu ; **work on the existing canonical `main`**, pinned initial checkpoint `3dde150819bf8c49fda6d0d71f00b9ce63173a34`. Refresh the head safely and reconcile real changes before editing.
- Sole authoritative emulator tree on authorized T computer: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`. MAME source: `.../diag/source`. One installed executable: `.../diag/bin/dana-diag`. Build intermediate `source/danadiagd` is NOT another authorized installed emulator.
- **Current qualified installed binary SHA256:** `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. Verify exact SHA before any installation. Retain a rollback path and never replace the operating executable with a failing candidate.
- Published driver: `src/mame/skeleton/alphasdana.cpp` (MC68VZ328 M68000 subclass, 32-bit address space, R-direct loader, physical Flash/reset mode, chip select and SDRAM, GPIO, clocks, IRQ, LCD, pen, UART1, SPI2/ST, SPI1/dual SD). Inspect `src/mame/skeleton/alphasdana_sd.h` and `alphasdana_sd_image.h` where applicable.
- **Known qualified, do not rebuild or retest gratuitously:** actual guest CPU+SPI2 native keyboard **81/81 scan codes, 86 releases, 5/5 chords** and installed EmuTOS-Dana boot smoke. Dual-SD guest read/write and close/reopen persistence previously qualified, as well as existing LCD/GUI-025/026; preserve features. Interactive EmuTOS text rendering was not proven by the most recent keyboard smoke. Prior qualification is not proof of Palm boot.

## 1. Private original firmware already present on T — do not ask user to reacquire it

Directory: `/home/spc/Projects/Dana-OS3K/firmware/research-only/`.

| File | Exact original bytes / SHA256 / significance |
| --- | --- |
| `Dana_US15_Flas.raw` | 6,062,080 B (`0x5C8000`); `fbba62000334bdb2faf352bdb899591c999528b3d631a4645c2dfce581e11059`. Concatenated Palm updater resource content, **NOT proven full physical Flash**. |
| `Dana_US12_Flas.raw` | 3,833,856 B (`0x3A8000`); `6169f44e8ddaf003bd5b98ea3424b19dfecf82f2681263feae078ab566b3370d`. Same limitation. |
| `DanaUpdate_enUS150R1.prc` | 6,085,164 B, SHA256 `53086494a233522d1773107a21f465835dca20e2cfd2076f2b45d0349558a342`. Resource DB `appl/asmt`, 119 consecutive `Flas` resources. |
| `DanaUpdate_enUS120.prc` | 3,855,501 B, SHA256 `1d4e19a41a68962bd6bce91cd9ed891bdedbf5eb24a296d3acf7221438fda1d6`. 75 `Flas` resources. |
| `AlphaSmart_Dana1_5_Flash.zip` | 9,453,509 B, SHA256 `1a0256e35c11c7455a58738f05218e1e290b8d381a5742467f1a512ac25c14fc`. Official-source updater archives/instructions. |

The `Flas` records concatenate in ID order; each resource contains payload + four-byte *byte-sum* checksum, NOT CRC32. The raw concatenated content contains `FE ED BE EF` at offset `0x8`, `PalmCard` metadata, Palm OS and AlphaSmart strings. This demonstrates **firmware data**, not a complete readout of protected boot sectors or physical NOR chip geometry. Do not commit original ROM/PRC/ZIP or derived ROM bytes to public Git, paste private bytes into issue logs, or write to a physical Dana.

The big-endian first two longwords in each extracted raw image are **candidate vectors**, not independently verified physical reset mapping:
- US1.5: SSP=`0x000048fe`, reset PC=`0x1000c80a`.
- US1.2: SSP=`0x0000486a`, reset PC=`0x1000c776`.

## 2. Last actual native Palm run — NOT BOOTED

Result text: `docs/PALM_UPDATER_DERIVED_COLD_BOOT_20261025.json`; immutable corresponding handoff prefix at `docs/HANDOFF.md`, latest current content only. User-owned emulator-only trial padded US1.5 with `0xFF` to **8 MiB** and US1.2 to **4 MiB** in private `/tmp/DANA_PALMOS_NATIVE_BOOT.3YyuVIg0/` solely to explore existing physical loader (which enforces complete power-of-two geometry). **This padded tail is invented/unknown**, NOT a recovered physical dump. Do not promote this experiment into a stock-ROM reference.

One recorded US1.5 run loaded the 8MiB temporary array in physical `-rom` profile, not EmuTOS `-quickload`. Native log:
```
DANA_PHYSICAL_IMAGE bytes=8388608 ... topology=linear_array_unqualified
DANA_PHYSICAL_RESET vectors=firmware CSA=00b0 CSCTRL2=1000 CSCTRL3=9c00
DANA_PHYSICAL_BLOCKED reason=FLASH_COMMAND_SET_UNVERIFIED address=00000000 data=0000 pc=1000c812
```
This proves physical-mode loading/reset and CPU-origin bus activity at a guest PC. **It does not establish Palm OS boot**. At `PC=0x1000c812`, firmware attempted a word write to physical address 0, which the current driver classified as Flash (boot CSA still selected). Root cause is **UNKNOWN**: absent boot region? firmware image not mapped as original? correct CSA reset decode? guest stack/address remap expectation? actual NOR/DRAM timing? Diagnose from disassembly and documented VZ behavior; do NOT decide by intuition.

The observer itself had an independent error: Lua `cpu.state["A7"]` is NIL in this MAME CPU state binding. Therefore its guest.trace was not produced. Fix observer by listing valid CPU state names or using available `SP` binding; do not mistake observer failure for guest hardware failure. The published receipt has **no US1.2 guest execution/trace**. Never claim US1.2 passed.

No Palm UI, OS boot, external ROM write, or new production emulator installation occurred in this native Palm attempt.

## 3. Code regions needing precise examination

In `src/mame/skeleton/alphasdana.cpp` inspect and trace these concrete functions:
- `firmware_load`: `-rom` takes a power-of-two linear 128KiB–16MiB byte array; rejects updater-sized partial images and checks reset PC at bytes4–7. Treating a PRC or Flash-content fragment as a complete power-of-two NOR array is **not justified**.
- `physical_reset`, `machine_reset`, `program_map`, `cpu_space_map`: profile selection, vector fetch, SCR, CSA at reset, CPU state.
- `physical_r`, `physical_w`: current `boot = !(m_cs_select[0] & 1)`; this routes all ordinary low writes to Flash until guest reprograms CSA. `physical_w` stops on `FLASH_COMMAND_SET_UNVERIFIED`. Determine whether this correctly reproduces the MC68VZ328 reset remap and initial DRAM availability; preserve fail-closed unsupported behavior until real evidence supports change.
- `cs_r/cs_w`, `cs_select_*`, `cs_hit/cs_size/cs_base`, `dram_r/dram_w`, `physical_mmio_r/w`, `physical_block`: first guest-visible failure and precise decoding.
- `GENERIC_SOCKET` in machine config, `DANA_VZ_CPU` address-width variant and scheduler. Avoid a new CPU engine, fake Palm system calls or host-side display painting.

For *real* MC68VZ328 reset vector, CSA/CSB/CSD initial mapping, DRAM/SDRAM, PalmCard and original Dana-specific boot behavior, read source references first:
- `research/sources.lock.json` and `docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md` (existing Motorola manual/addendum contract).
- `docs/D8_5_PHYSICAL_BOOT_IMPLEMENTATION.md`; `docs/GENERAL_WORK_PLAN.md`, `docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md` and `docs/DANA_DIAG_EXCLUSIVE_TEST_POLICY.md` (current rules).
- `https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/05-ROM-DANA-ACTUALIZADORES.md` (authentic updater structure and known limits).
- `https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/01-HARDWARE-DANA.md`.
- Pinned MAME donor `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`, `src/mame/palm/palm.cpp`, MC68EZ328 device as conceptual reference only.
- Original POSE `EmRegsVZ` and pinned Motorola `M68VZ328Hwr` via `research/sources.lock.json`; POSE reference defaults are NOT automatically Motorola official reset defaults. Review per-file license before reusing code.
- EmuTOS-Dana `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b` for board hardware accesses, NOT an authentic Palm boot substitute.

## 4. Do the work now — single boot objective, modular diagnosis only if helpful

1. **Inspect the actual checked-out T source/binary and the private firmware.** Verify hashes, no second emulator, no uncommitted user work overwritten. If T is not connected to this Codex environment, do as much source/firmware analysis and implementation as actually possible, then report the exact inaccessible requirement; do not invent execution or claim background progress.
2. **Resolve the earliest failing CPU bus transaction**, not a generic survey. Decode and disassemble first ~100 68k instructions from genuine image origin near raw offset `0xC80A` for 1.5, inspect jump/branch destinations and the first memory write, decode actual CPU state (PC/SR/SSP and effective address) using correct MAME APIs. Understand whether a valid stock Palm startup requires a separately protected boot sector or initial low RAM alias. Analyze updater's programming offsets and check whether the first longwords are genuine reset vectors or PalmCard metadata. Cross-check chip-select control values and runtime bus trace against pinned Motorola/Dana evidence.
3. **Implement the smallest real hardware correction** if and only if supported by authentic source/guest behavior. Integrate in the current `src/mame/skeleton/alphasdana.cpp`, without app-specific hooks or bypassing Flash write rejection. If original full dump is a hard requirement, state which sector/range and proof establishes it. A private test-only temporary image with missing bytes clearly marked hypothetical may be used to isolate the cause, but must never be presented as physical ROM fidelity.
4. **Build ONLY the existing reduced DANA DIAG** incrementally using the established Clang21/MAME build cache and inspect/record actual compiler output and hashes; no new branches/clones/worktrees/alternative emulators. Keep the old installed binary safe until a candidate has credible functional evidence. CPU guest trace must identify how far authentic Palm OS reaches; isolate a real Flash/remap/MMIO blockage and fix from evidence. Run US1.5 first, US1.2 for contrast when useful.
5. **Product acceptance:** success requires actual CPU-executed stock Palm OS reaching Palm UI with guest-driven framebuffer/input, no invented ROM vectors, fake MMIO, hidden exceptions or host-rendered screen. Prove first stages separately (valid image vector, first genuine instructions, DRAM chip selects, Palm initialization, LCD) but do not confuse partial steps with finished product. Preserve working EmuTOS R-direct / ST81 keyboard / SD regression with **targeted** tests only where changed behavior could affect them. Never rerun closed large suites just to produce activity.
6. **Report exact verifiable outputs:** commit(s) on canonical `main` (unless current authorization or repository safety requires leaving a reviewed diff), source changes, authentic image SHA (not bytes), binary SHA, MAME full CLI, native CPU PC/SSP/SR/bus sequence and first unresolved MMIO/register or guest UI evidence; PASS/FAIL/BLOCKED and the one remaining blocker. Update the existing handoff/status in-place without proliferating plans, trackers or artificial gates. Never claim an OS boot if only the loader or a synthetic guest succeeded.

## 5. Hard working constraints

- **Single working DANA DIAG product**; no new branch, clone, isolated version, parallel emulator, or alternate stable build. No Codex work in AS2K, Pro or EmuTOS/OS3K firmware repos; they are read-only references unless user explicitly expands scope.
- Protect the previously qualified 81-key ST keyboard, dual SD read/write, LCD, pen, GUI and EmuTOS boot. Do not replace known-good operating executable on a FAIL.
- Never write to a real physical Dana, host disk image outside disposable copies, user's original updater/ROM files or private firmware, and do not distribute copyrighted Palm ROM bytes.
- No blind address padding/mirroring, switching to synthetic RAM entry, patching Palm binaries, hardcoded success checks, CPU state shortcuts or ignoring exceptions to pretend Palm boots.
- Maximize **real product progress in one intervention**: focused module diagnosis is allowed where needed, but not artificial per-register gates or a stream of test-harness-only tasks.
- This handoff alone does not grant new **Remote Desktop Commander** privileges: the last ChatGPT intervention exhausted its five specifically authorized remote calls. Codex should use only the machine access and permissions the user explicitly supplies in its own environment, otherwise report BLOCKED access precisely. Do not claim that publishing these instructions executed Codex.

**Begin now with the private US1.5 source image and the first write at `PC=0x1000C812`. Work toward real Palm OS boot instead of offering another work plan.**
