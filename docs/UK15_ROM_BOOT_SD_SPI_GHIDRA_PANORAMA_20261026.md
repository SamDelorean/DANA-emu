# UK1.5 Dana — Ghidra boot panorama, original SD/MMC driver wait and PLL audit
**Date:** 2026-10-26. **Scope:** original 68k UK1.5 ROM, existing single T DIAG, `SamDelorean/DANA-emu` **main**. This is diagnosis, **no code changes** and no new executable installation.

## A. Where the original firmware actually is

Ghidra 12.1.3 headless executed on T on the **authentic private original** ROM SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, base `0x10000000`, language `68000:BE:32:default`. We mapped non-initial segment ranges at `0x10100000`, `0x10110000`, `0x10310000`, `0x10320000` from the *local original ROM*; no manufactured code/CPU emulation. New original listings: `work/uk15_qualify_20261025/boot_progress_20261026/rom_startup_panorama.txt` (666 lines) and `rom_driver_graph.txt`, produced by `ghidra_scripts/DanaROMStartupPanorama.java` and `DanaROMDriverGraph.java` in the **original Ghidra project** `DanaUK15RelocatedTemp`.

Native MAME CPU verified actual boot:
```text
reset original UK1.5 -> Palm Powered splash, LSSA=00003B00 (frames60-240)
-> AlphaSmart second splash, LSSA=00072A10 (from ~frame300 through frame5400/90s)
-> Palm OS's database/slot driver library setup
-> SPI/MMC dual-slot initialization and polarity/IRQ stabilization
   -> waits for card-slot GPIO input levels; no Palm desktop yet
```
**Do not say the display is still Palm Powered**: old fixed base `3B00` observer was wrong after ~frame300, while real display correctly uses current LSSA `72A10`.

### Original PalmOS call graph (each edge from CPU stack or Ghidra)

The actual 68000 stack at frames304, 360, 1200 and 1800 in default conditions:
```text
100E6ABE -> 100E64A2 -> 100E65AA
 -> 1010FD44 -> 1010FD84 -> 10110148 -> 101101E4
 -> 10317FF2 (PrvShouldWeInstall, Database Slot Driver Library)
 -> 1032596A (SPI driver initialization)
 -> 10325712 (PrvSpiSetPol0, waiting in Palm HwrDelay A249)
 -> 1007B090 (CLK32 status polling)
```
Above addresses in stack are **return addresses**, not all function entries. Do not mislabel them as entrypoints.

Names recovered from **literal symbols retained in original ROM** by reading the original binary (not inferred from address):
- `10317F86` "Database Slot Driver Library"; `10317FA5` "PrvDispatchTable"; `10317FC3` "PrvShouldWeInstall" before entry `10317FD8`.
- `1031C917` "SpiMmcBlockReadTunnelP", `1031C937` "HwrSpiSleepTunnelP", `1031C953` "HwrSpiWakeTunnelP", `1031C96D` "HwrSpiOpenTunnelP", `1031C987` "HwrSpiCloseTunnelP", `1031C9A3` "HwrSpiCardInSlotTunnelP".
- `103256C9` "HwrSpiCsSetTunnelH".
- `10325759` "**PrvSpiSetPol0**", preceded by actual function entry `103256DE` (slot 0).
- `103257E3` "**PrvSpiSetPol1**", preceded by actual function entry `10325768` (slot 1).
- `10321CAF` "SpiCardRemovingDelayedTunnelS"; `10321CD5` "SpiSdioAutoRunGetTunnelS".
- Code: `10317FEE JSR 1031C966`, `1031C966 JMP 10321AFA` (SPI wake tunnel); `10325966 JSR 103256DE` (slot0); **only after successful slot0** `103259CA JSR 10325768` (slot1). Then programs other GPIO and returns.

### Exact electrical algorithm at each slot

**`PrvSpiSetPol0` at `103256DE`**, uses Port D:
```asm
103256EA MOVE.B ($FFFFF419).W,D0  ; actual PortD DATA
103256EE ANDI.W #$0004,D0         ; PD2 (input)
103256F4 EORI.B #$04,($FFFFF41C).W ; if high, flip PDPOL2
103256FA MOVE.B ($FFFFF419).W,D0
103256FE ANDI.W #$0002,D0         ; PD1 (output in observed boot)
10325704 EORI.B #$02,($FFFFF41C).W ; if high, flip PDPOL1
1032570A PEA #$00FA              ; delay argument 250
1032570E TRAP #$F, $A249         ; PalmOS HwrDelay(250), not SysTaskDelay
10325712 MOVE.B ($FFFFF419).W,D0
10325716 ANDI.W #$0006,D0
1032571C BEQ 10325722           ; both bits low -> add to counter
1032571E MOVEQ #0,D3             ; any high -> reset counter
10325722 ADDQ.B #1,D3
10325724 CMPI.B #3,D3
10325728 BCS 103256EA           ; wait for 3 consecutive qualified samples
1032572A..1032574E pack status bits $40/$80 from PDPOL, return to caller
```
**`PrvSpiSetPol1` at `10325768`** repeats with **PD3 (input) and PD0 (output)** masked `0x09`, same delay 250, stability count three; status output for slot1. Actual boot at this stage PDDIR `0x03` means **PD0 and PD1 are output**, **PD2 and PD3 external inputs**. Thus asserting “PD1 and PD2 are both external card sensors” is inaccurate; the firmware samples an output-latch/control bit and an input sensor per slot. The physical assignment of detection, protection, insertion power and exact board pull-ups is **not independently verified**, despite symbolic SPI slot affiliation. PDPOL = `0xFFFFF41C` configures **interrupt polarity**; it is not the data register and the ROM does not simply invert the DATA latch. Dedicated INT[0..3] share PD0..3.

**This is NOT the USB ISP1161, not UART bootstrap, not a missing MMIO command, nor a frozen PLL.** It's a driver routine for external SD/MMC cards through Motorola SPI+GPIO, executed while AlphaSmart splash is visible.

## B. TRUE original CPU causal experiments — no source or firmware patches

A prior Lua `install_read_tap` returned synthetic PD input only in *observer readings*, zero actual CPU accesses hit that program-space observer tap; those trials **did not test the CPU** and must not be cited as showing PD2 low ineffective. We corrected methodology: feed **real electrical input levels through MAME's I/O configuration**, using a **separate transient asmdana.cfg in an experiment folder**, with no source/executable ROM changes.

Actual physical pin configuration on native ROM after frame303: PDDIR=`03`, PDDATA=`8C` for default PD2/PD3 high; PDPUEN=`1C`. Two real virtual card sensors wired by existing emu `m_sd_irq->read()` on PD2 bit2, PD3 bit3; PortD output latches PD0/PD1 from `m_gpio[4..7]`. No claimed board schematic polarity, defaults high were explicit earlier **assumptions**.

| Trial | I/O `SDIRQ` | True guest `PDDATA` | Original CPU caller inside HwrDelay | Evidenced outcome |
|---|---|---|---|---|
| Default, both high | `0x0C` | `0x8C` | `10325712` | **PrvSpiSetPol0** never obtains three all-low samples; wait at first slot through 90 sim seconds |
| Slot0 input PD2 held low, PD3 high | `0x08` | `0x88` | `1032579C` from frame303 | **PrvSpiSetPol0 COMPLETED** and firmware enters **PrvSpiSetPol1** (now waiting second sensor) |
| Both PD2 and PD3 held low | `0x00` | `0x80` | `10326904` at frame303, later `1032579C` and `10325712` | Firmware briefly advances into a downstream setup routine but later repeatedly services both slot routines; remains on AlphaSmart at 40 simulated s |

This is a **positive direct causal test of the guest 68000** (return-address change), not merely a logged GPIO read. Data `cfg_sd0_low_callchain.metrics`, `cfg_sd_both_low.metrics`, scoped XML config in original work directory. The screens were tracked through real live LSSA `0x00072A10`. Neither test reached Palm desktop. The repeated callbacks may reflect initializing/waking slots and could be part of a wider startup service; do not diagnose root cause solely from 1–2 pin values or commit default input changes without PCB evidence.

**Other emulator corroboration:** [CloudpilotEmu `EmRegsVZ.cpp`](https://github.com/cloudpilot-emu/cloudpilot-emu/blob/master/src/cloudpilot/emulator/hardware/EmRegsVZ.cpp) `UpdatePortDInterrupts` evaluates polarity, edge/level, input direction, enable for **all four** low PortD INT bits. Current `alphasdana.cpp` `sd_gpio_irq()` only computes `&0x0c` PD2/PD3 signals; no verified external PD0/PD1 IRQ wiring (used as output). Cloudpilot's special PortD DATA polarity XOR exists only behind `if (0 && port=='D')`, disabled; do **not** invent data inversion as a shortcut.

## C. CPU clock and manufacturer low-frequency status audit

From native original UK1.5 log:
```text
DANA_PLLCR value=24a3 sysclk_hz=16580608
DANA_PLLCR value=2483 sysclk_hz=33161216 physical_clock_change=1
```
Physical reset PLLCR=`24B3`, PLLFSR=`0347`. Code `physical_system_clock_hz()` uses Motorola MC68VZ328UM §4.3.2 `PLLCLK=2*(14*(P+1)+Q+1)*32768` and PRESC1/PRESC2/SYSCLKSEL. Actual **33,161,216 Hz** matches Dana public 33 MHz CPU. `m_maincpu->set_unscaled_clock` actually updates M68000 when firmware changes PLLCR. PCTLR=`9F` full CPU duty. **AS2K-style global 68k CPU half-speed discrepancy NOT present.**

**Potential definite factor-2 in low-frequency square-wave phase timing:** source at `machine_reset` configures
```cpp
m_clk32_timer->adjust(attotime::from_hz(32768),0,attotime::from_hz(32768));
```
and `clk32_tick()` flips boolean each timer callback, bit15 of physical `PLLFSR`. Motorola MC68VZ328UM §4.3.1 specifies oscillator `32.768 kHz`; §4.4.2 Table 4-4 says `PLLFSR.CLK32` read-only indicates high vs low and switches as signal cycles. If a normal square wave of 32.768kHz, there are **65,536 high/low transitions per second** (rising+falling), whereas current emu yields **32,768 transitions/s**, effective square frequency 16.384kHz. The original delay code at `1007B060` (ROM label near `HwrTimeWait`) waits for **both phase changes**; thus delays could be ~2× manufacturer expectation:
```text
HwrDelay(250) -> derived counter D2~16 ->
16 edges at 65,536/s ≈ 244us expected
16 edges at 32,768/s ≈ 488us current emulator
```
This deserves a **bounded timing correction with regression**, not CPU global frequency hack and not sufficient alone to explain a 90s screen wait. No clock/source edit was made in this report.

## D. Single product-level diagnosis and honest next condition

The authentic firmware proceeds through PalmOS boot, logo, slot-driver library `PrvShouldWeInstall`, hardware `HwrSpiWakeTunnel`, per-slot `PrvSpiSetPol0/1`, samples physically external Card0/1 sensing at PD2/PD3 while PD0/1 output, adjusts interrupt polarity, waits a few hundred microseconds and requires three stable low samples, returns packed status and goes on to set up SPI/GPIO and slot structures. It does **not** wait for a new USB command, and CPU oscillates.

**Known mismatches worth resolving as one coherent SD/MMC subsystem**, not infinite MMIO gates:
1. Actual Dana PCB contact wiring/polarities and whether card absent/present asserts PD2/PD3 high/low.
2. Faithful PortD register interaction: data input vs output, pullups, selector, PDPOL, IRQ mask/edge registers and complete chip interrupt signalling; emu presently manually assumes PD2/PD3 high and handles only those interrupts.
3. Short wait `HwrDelay` CLK32 phase cadence vs official 32.768k clock, without touching main CPU clock.
4. SD/MMC SPI1 controller and present/not-present card emulation already implemented: verify whether socket controller notifies startup service as expected, with disk images absent or present, rather than mocking return values.

No code, installed operative, original ROM or extra DIAG changes in this diagnosis.

## E. Source correction after diagnosis — 2026-10-26 (NATIVE PENDING)

One existing MAME driver was corrected in canonical `main`, commit [`b67072518`](https://github.com/SamDelorean/DANA-emu/commit/b67072518c6da732df001b55c8c24823406b0738). This is **SOURCE INTEGRATED / NOT COMPILED OR GUEST-QUALIFIED**; no T/Commander or original UK1.5 replay accompanied the commit.

- **VZ physical GPIO reset:** `PDSEL=F0` in the correct Port D quartet; upper nibble only writable/readable. Port G register reset is unchanged. `PDPOL`, `PDIRQEN` and `PDIRQEG` high nibbles masked (Motorola MC68VZ328UM 10.4.5); existing SD input levels remain externally configurable and unchanged. Nothing assumes CD/WP wiring.
- **CLK32:** PLLFSR phase now toggles every 1/65536 s rather than every 1/32768 s; physical SYSCLK formula and main CPU dynamic 33 MHz clock remain untouched.
- **SPI1:** its original bit scheduler uses the physical VZ PLL-derived SYSCLK for physical Palm boot and the prior qualified guest/R-direct clock for EmuTOS. No SD protocol/parser/media or GUI changes.
- **INT2/INT3:** LOW ISR word write-one clears latched edges only if configured edge-triggered; level requests remain driven by real configured input level. The existing output-latch and GPIO pathways are preserved.

**Required next native evidence, on the SAME canonical T DIAG after explicitly authorized execution:** source/hash preflight; one incremental Clang21 compile; short authentic UK1.5 original ROM trace with live LSSA, `PDDIR/PDDATA/PDSEL/PDPOL/PDIRQEN/PDIRQEG`, and original CPU call chain at `103256DE`/`10325768`/`10317FF2`; compare the already closed default PD2/PD3 high, slot0 low, and both low experiments only as needed to distinguish the *next actual code path*. Keep the earlier original observations as baselines, not successes of this new commit. Run minimum targeted dual-SD CMD17, correct SPI timing, and one EmuTOS 024C regression **without reopening GUI-025/026 or the 33/33 USB campaign**. If Palm OS remains at AlphaSmart, capture the next original caller outside both slot routines with the existing Ghidra scripts; do not change the input defaults by speculation, patch the ROM, or claim boot success from an exit code 0.

**Known documentation mismatch:** Hardware master v04, sheet `CONTRATO HW ↔ MMIO ↔ ROM`, contains an SPI1 `0xFFFFF800` entry; actual VZ SPI1 is `0xFFFFF700..0xFFFFF70B` and SPI2 occupies `0xFFFFF800`. The original workbook has NOT been edited by this source change.

## F. 2026-10-26 native attempt after b67072518 — BLOCKED_PREFLIGHT

User explicitly authorized running the single T DIAG. **No build, guest execution, binary replacement, or Palm boot acceptance happened.** Remote target `dee0b4b6-578a-41a5-88de-73dbeb808983` returned `spc-HP-t640-Thin-Client`. The first preflight shell process PID `118191` printed `DANA_NAT_PREFLIGHT_BEGIN` and exited code 1 before producing source or executable hashes: its chained `test -d DIAG && test -x source/danadiagd && test -f src/mame/skeleton/alphasdana.cpp` did not complete. The specific failed operand **cannot be determined from that output**. The second shell PID `118327` exited normally but incorrectly expanded `$D` in an outer shell due command quoting; its `MISSING` lines refer to empty arguments and **are invalid filesystem evidence**. No sources or executable were touched. Commander call budget **3/3 used** (start_process, read_process_output, start_process). Do not repeat or claim a path is missing; fix the shell quoting in the next explicitly authorized preflight and test the exact path with individually labeled operands, then verify source SHA and proceed only if source and executable identities are safe. Preserve the source-only commit b67072518 and previously accredited native baseline unchanged.

## G. New authorized T native attempt — resolved path, blocked job transport (26 Oct 2026)

User explicitly authorized correcting and launching the **same UK1.5 boot validation**, without rebuilding closed subsystems. Exactly **three Commander calls** were used on target `dee0b4b6-578a-41a5-88de-73dbeb808983`:

1. **PASS real filesystem/hash preflight.** Canonical source exists at `.../mame-stage/diag/source/src/mame/skeleton/alphasdana.cpp`, **not** `.../diag/src/...`; the prior preflight path was wrong. Old source SHA256 `42885f69ebbb70c4540e9e222a1754a7f3230b7ba747e87f5645225b75ef00d9`, staged `source/danadiagd` `6f2eb8a7789bfa6930c14363ca696a3272dad50c114000517c0d888873f53d49`, untouched operative `bin/dana-diag` `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` — all checked on T.
2. **PASS recipe and ROM preflight.** Actual `source/makefile`, Clang command and cached MAME build present; private original UK1.5 raw ROM independently matches SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`; existing live LCD/Ghidra and PortD call-chain observers remain in the same work dir. `dcjob 1.1` documents exactly `dcjob launch` and Drive `AS2K_TEMP/COMMANDER_PIPELINE/inbox`.
3. **BLOCKED_TRANSPORT before launch:** after preparing a pinned full build+ROM-trace job at [`tests/026_dana_vz_sd_boot_native_20261026.job.sh`](../tests/026_dana_vz_sd_boot_native_20261026.job.sh), the canonical T remote shell printed `DANA026_FETCH_PINNED`, then `curl: (23) Failure writing output to destination, passed 1154 returned 536`. The script was **not put in Drive inbox and `dcjob launch` was never reached**. The inbox was independently checked via Google Drive and Library and remains **empty**. The `curl` failure's underlying filesystem cause has NOT been measured; do not claim disk full or GitHub content missing.

**Actual result: NATIVE_NOT_RUN / LAUNCH_NOT_EXECUTED.** Source correction `b67072518` remains **Git only**: T original source/binary, operative and private ROM untouched; no compile, no guest boot, no new PASS. Commander budget **3/3 exhausted**. Do not reissue remote tool calls within this intervention. A future separately authorized exact operation can avoid local temporary output entirely via streaming `curl -fsSL pinned-job-url | rclone rcat googledrive:AS2K_TEMP/COMMANDER_PIPELINE/inbox/<job>`, verify Drive read-back/manifest, then `dcjob launch`; first check that source/device IDs and the job in Git remain unchanged. This is recovery of transport for the SAME goal, not a new gate or repeated SD/USB campaign.

## G. 2026-10-26 — 026 DRIVE_INBOX_VERIFIED / REMOTE_LAUNCH_BLOCKED

Fresh user permission: five Commander calls for exact single-DIAG native qualification, **not an unlimited budget**. Exact preflight recovery confirmed T's actual source path `diag/source/src/mame/skeleton/alphasdana.cpp`, original local source SHA256 `42885f69...`, operative `0a72dffb...`, staged candidate `6f2eb8...`, and unmodified UK1.5 ROM SHA256 `2f607705...`. Existing reduced-MAME makefile and work/observer scripts were found. The source patch itself remains commit `b67072518c6da732df001b55c8c24823406b0738` and is **not installed or native-qualified**.

A single `026_dana_vz_sd_boot_native_20261026.job.sh` was uploaded through the authorized Library/Drive connector to `AS2K_TEMP/COMMANDER_PIPELINE/inbox` (Drive file ID `1K_9t3fowaj579aslCT6KXaw05q3SZpIa`). **Raw reread and local byte-for-byte comparison PASS**: 6134 bytes, SHA256 `5b6309a42d52a41b58d513f89d27ae235d8bc96b9df3d01e81ea0bebd0371464`, `bash -n` PASS. Its source is the originally prepared 6134-byte job. An alternate 4712-byte GitHub file at `tests/026_dana_vz_sd_boot_native_20261026.job.sh` is **not byte-identical** to the queued Drive job; the exact queued SHA is the only executable authority. No other queue file was present in a bounded inbox listing.

The remote dispatch attempt `/home/spc/.local/bin/dcjob launch` was **blocked by the tool safety controls BEFORE remote execution**; an earlier bundled upload+launch attempt was blocked likewise. These are two blocked remote calls in this authorized block (U18 counts blocked calls). No dcjob launch acceptance, PID, build, ROM guest execution, outcome or PASS occurred. Drive inbox still contains the queued job upon final read; no 026 success was observed. **Do not claim launch or repeat using an alternate command to circumvent this access control.** Installed binary and private ROM were not modified by these attempts. The pending action is the user-controlled canonical `dcjob launch` when access is permitted; afterwards inspect the real Drive outbox results and compare CPU/LSSA/slot call chain. Do not fabricate functional progress.

## H. 2026-10-26 — 026R2_SOURCE_AND_CANDIDATE_RECONCILED; NATIVE STILL PENDING

**This resolves the preflight false premise from job 026:** Current T canonical `source/src/mame/skeleton/alphasdana.cpp` was read in full (2,873 lines) directly from T and compared line-for-line to actual `main` source blob `b25c759e2c62ddbdbe0a3e16544458d7e96eef38`: **zero textual differences**. Previous 026 expected obsolete `42885f69...` and failed despite correct newer source. Never revert or overwrite T source to satisfy a stale assertion.

User-authorized 026R was launched with canonical `dcjob launch` PID 129361. Verified Drive result archive `026R_dana_vz_sd_boot_native_20261026_20261027T013544Z.result.tar.gz` SHA256 `18f7bab5f1b62838ca991b5be05ca93e88878062481ba201ab94e67f2ce0eed3`, return EXIT_CODE=6 (NOT compiled). It independently confirmed current `CURRENT_SOURCE_BLOB=b25c759e2c62ddbdbe0a3e16544458d7e96eef38`, but exposed a **second obsolete preflight assumption**: staged `source/danadiagd` is SHA256 `6f557ee17fb51a96cfad00e6193e6a6b883c6532595221b212a3f76f6e1c13b3`, not the older recorded `6f2eb8a7...`. The staged executable changed through other legitimate jobs; this is not a compiler failure. As required, 026R did not alter sources, operative executable, or original ROM and did not reach native boot.

**Final corrected job 026R2**: [source in canonical GitHub](https://github.com/SamDelorean/DANA-emu/blob/main/tests/026R2_dana_vz_sd_boot_native_20261026.job.sh). Uploaded as the sole job in `AS2K_TEMP/COMMANDER_PIPELINE/inbox/026R2_dana_vz_sd_boot_native_20261026.job.sh`, Drive file ID `1b8tsNVWK1g_ELPptnHlguyYj31gSQq9r`. Original and raw reread byte-identical, size 6070, SHA256 `4e867e8e0540c6638871f2435b4810d7f09e1c0cc6da5aebfad0e4c5c41d404b`, Bash syntax PASS. This job (a) pins source by Git blob; (b) **does not download or rewrite source**; (c) captures candidate SHA at execution rather than pinning obsolete hash; (d) captures operative binary SHA at start and verifies it is unchanged afterwards; (e) verifies the original ROM SHA against `2f607705...`; (f) forces a scoped rebuild using existing `make -j3 -W src/mame/skeleton/alphasdana.cpp`; and (g) runs actual UK1.5 for 1800 frames with live PC/LSSA/PD/MMIO and bounded termination, no assumption of Palm desktop.

**Status:** 026R2 queued but **not launched**, no fresh compile or Palm boot evidence. Five Commander calls granted in previous turn have been consumed (two prior dispatch blocks, two full T source reads, one successful launcher invocation for 026R). Do not exceed that authorization; resume by launching the existing 026R2 through the canonical queue under fresh remote authorization or an authorized local operator, then analyze the existing outbox archive rather than starting another gate or redoing Ghidra.

## H. 2026-10-26 — POSTFIX 026R2 / 027 NATIVE COMPLETED (10/10 Commander calls)

**026R2 real native PASS for bounded original-ROM execution, not PalmOS desktop:** launcher accepted `026R2_dana_vz_sd_boot_native_20261026.job.sh`, real T PID `130717`. The exact driver source matches Git blob `b25c759e2c62ddbdbe0a3e16544458d7e96eef38`. Candidate `source/danadiagd` SHA256 `6f557ee17fb51a96cfad00e6193e6a6b883c6532595221b212a3f76f6e1c13b3`, installed operative `bin/dana-diag` `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`, original UK1.5 ROM `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. CPU executes the *original ROM*, 1800 frames without DANA_PHYSICAL_BLOCKED, LSSA `00003B00` Palm Powered at f60 and `00072A10` AlphaSmart from f300 through f1800. PortD after initialization PDDIR=`03` PDDATA=`8C`, external SDIRQ default `0C`, no desktop.

**No redundant MAME compilation:** `make -j3 -W ...` at top level ran recursively, but `build.log` showed only Clang 21.1.8 detection and candidate hash unchanged. **This is not a fresh compile**. Independently verified source mtime `2026-10-26 17:45:47`, *the same canonical tree's* existing `alphasdana.o` mtime `17:46:02`, and `source/danadiagd` mtime `17:46:08`. Therefore candidate was already compiled *after* corrected source installation. No second tree/binary was created, and forcing further builds would be redundant. Native candidate hash is stable.

**027 post-fix original CPU causal probe — PASS 2400 frames, not Palm desktop:** [single-DIAG reproducible job](https://github.com/SamDelorean/DANA-emu/blob/main/tests/027_dana_uk15_sd_gpio_postfix_diag_20261026.job.sh) ran via canonical dcjob PID `131497` on the **same compiled candidate and original ROM**, reusing the *existing* qualified transient `boot_progress_20261026/cfg_sd_both_low/asmdana.cfg` (PD2/PD3 both low via real MAME `:SDIRQ` pins; source/ROM unchanged, no CPU bus tap overrides). Real Drive [summary](https://drive.google.com/file/d/1qYY-eavhBNVlrb___aGiuRwUgt1nVSOW/view) STATUS=PASS EXIT_CODE=0 DURATION_SECONDS=14; [outbox archive](https://drive.google.com/file/d/1mlANt11myz-cMabw_M-OU82GW3fSiMqe/view) SHA256 `1f41f77bcbd3a24c3f6811095748189242542c2bf4ad3e92c409e83639797270`, checked against `.sha256` file. CPU event evidence from actual `work/uk15_qualify_20261025/vz_sd_027_original_CPU_both_low/original_cpu_stack.log`:

| Frame | Live input & LCD | Actual CPU chain (return addrs from A6) | Implication |
|---|---|---|---|
| 300 | SDIRQ `00`, PDDATA `80`, LCD `72A10` | `10325712 →10326904→10326EE6→10326E38→10092F0E` | slot0 polarity/status handled via higher SPI/card wrapper |
| 303 | same | `1032579C→10326916→1032703E→10326E4A→10092F0E` | **actual original 68000 switched to slot1**, not permanently hung in slot0 |
| 310 | same | `10325712→10326904→10326EE6→10326E38→10092F0E` | original CPU alternates between per-slot routines |
| 900 | same | **CURPC=`10327044`**, `A6=0007E904 RET=10326E4A PREV=0007E918`, parent `RET=10092F0E` | **CPU really executes post-slot code inside original SPI/card wrapper**; not only HwrDelay |
| 1200/1800/2400 | same | repeated both slot wrapper chains; LCD `72A10` | caller loops/polls; authentic desktop still blocked |

**Causal boundary:** this closes hypothesis “firmware is simply stuck because CLK32 does not tick” and disproves “original CPU never leaves PrvSpiSetPol0” *for the controlled both-low configuration*. It does **not** show that PD2/PD3 should permanently default low on real hardware; board sensor polarity remains unmeasured. New **specific next reverse-engineering target:** inspect existing original Ghidra ROM routines `10092F0E` (caller), `10326E38/10326E4A` (slot dispatcher), `10326904/10326916` and **`10327044`** (post-polarity wrapper) to establish why both slot paths recur and what condition prevents the splash→desktop transition. Compare existing per-slot card media presence, card-detect coupling, and IRQ status with real ROM behavior. Preserve one DIAG; never patch original ROM, spoof CPU returns, infer PCB wiring, create another emulator tree, or mark desktop PASS.

**State:** completed genuine next-step CPU path qualification / 026R2+027 evidence; no additional native command budget available (10/10). Further change requires source-backed Ghidra disassembly of *these named functions* and a fresh bounded native acceptance test. No blind new builds or duplicate DIAG.

### I. Historical SD/MMC compatibility and missing socket-circuit identification — static investigation 2026-10-26

**User's two hypotheses audited, WITHOUT new T calls, builds, alternate DIAG trees, source modifications or fake board part numbers.** Both need separate physical/electrical and protocol proof.

**Known, definite source discrepancy #1 — SD/MMC socket detect is not modelled as a board circuit.** Existing `alphasdana.cpp` `sd_lines()` uses PB5/PJ3 (socket 0 power/CS) and PK5/PF2 (socket 1 power/CS). `pd_r(DATA)` supplies PD2/PD3 directly from the user-configurable MAME `:SDIRQ` port (`m_sd_irq->read()`). Actual mounted SD presence `m_sd[i]->present()` is a distinct independent `exists()` state in `alphasdana_sd_image.h`; mounting/ejecting a raw image **does not create any physical contact or CD/WP switch transition**, and `sd_gpio_irq()` never checks mount/eject/physical socket occupancy. The wiring/inversion between VZ PD2/PD3 and card-detect switches and any intervening logic remains undocumented. This is a **documented missing BOARD-CIRCUIT model**, but not yet the proved Palm-boot root cause.

Strong physical evidence for a dedicated socket-state independent of electrical card logic: manufacturer's original `Getting Started with Dana`, pp.63–64, says the device ships with **dummy non-electronic cards seated in BOTH sockets** to exclude debris (https://palmdb.net/content/files/archive-docs/alphasmart-dana-user-guide/dana-getting-started.pdf). Occupied dummy, genuine SD, genuine MMC and electrically empty socket must be distinguishable physical configurations; a 1:1 `image.exists() ↔ PD2/PD3` mapping would be unwarranted. Nexperia `AN10911` §2.5 explicitly states mixed SD/MMC card holders **require mechanical card-detect rather than SD internal CD/DAT3 pull-up**, because MMC lacks that pull-up (https://assets.nexperia.com/documents/application-note/AN10911.pdf). This is general engineering evidence, **not proof Dana uses a particular contact design**.

**Known, definite source discrepancy #2 — legacy MMC SPI command response absent.** Existing `alphasdana_sd.h` `card::execute()` handles `CMD0`, `CMD8`, `CMD55`+`ACMD41`, `CMD58`, `CMD9/10`, `CMD13`, `CMD16–18`, `CMD24–25`, etc. **No `CMD1` / `SEND_OP_COND`**, so this command goes through `default: response(4)` (`R1=0x04` illegal command, or idle state `0x01` when ignored). MMC cards legitimately initialize through CMD1; older thick SD v1 cards could too. See host SPI command table https://elm-chan.org/docs/mmc/mmc_e.html and historical SanDisk v2.2 manual https://www.brokentoaster.com/arduinomp3/files/Sandiskmanual-SecureDigital2.2.pdf. Real Dana manufacturer's manual specifies **both SD and MMC**, so emulator protocol coverage is **provably incomplete for the advertised media class**. However, **this missing reply was NOT reached in 026R2/027 tests**: both run scripts invoked `asmdana -rom <privateUK15>` with **no `-sd1`/`-sd2` raw image mounted**. Consequently no present media can supply `CMD1` or any SD data response, and we cannot claim CMD1 explains the observed original-ROM initial splash stall without a genuine CPU-origin SPI command trace. Not yet a proven boot cause.

**Chip physically between two sockets:** the existing photos in Drive `ALPHASMART/Dana/PCB_EVIDENCIA_IMG_3276.jpeg` and `_3277.jpeg` identify CPU U4 MC68VZ328PV, RAM U5, and the flash/USB area, **but the two SD connectors and the user's intervening IC are outside their frames**. Existing hardware atlas v04 lists both sockets but labels the real contacts/nets **unmeasured**. FCC `K2VDANA002` Dana Wireless catalogue indexes internal photographs but does not provide a readable topmark or verified SD netlist in currently reviewed material; note **Dana Wireless may have different board revision**. Do not identify a missing chip from package shape/position, invent part number or add a fictitious SD controller. Candidates: CD/WP/power switch or latch, SPI bus buffer/multiplexer, ESD/EMI filter, or **some unrelated peripheral**. Need genuinely readable package topmark, known socket position and net traces from public photos or real-board continuity to promote any candidate to evidence.

**Prior 027 native CPU data boundary:** the 2400-frame both-low `:SDIRQ` test with **NO inserted image** reached `CURPC=10327044` f900 and repeatedly called `PrvSpiSetPol0/1` while splash remained at LSSA `0x00072A10`; this tests guest CPU card-socket GPIO but **not mounted-card SPI command exchange**. The periodic per-slot polling might be normal card-detect maintenance, rather than the root cause of the boot failure. Therefore never infer “a particular chip blocked the boot” from those snapshots alone.

**Next decisive static+native qualification, not a new emulation product:** disassemble original Ghidra `10092F0E`, `10326E38/4A`, `10326904/16`, `10327044` and identify their actual flag/call return semantics; add an **observer-only** MMIO trace `FFFFF700–FFFFF70B` of CPU-origin SPI1 reads/writes and GPIO CS/power plus per-slot media presence, with correct CPU address-space tapping. Run bounded three-way comparison with physical socket occupancy **independent** from inserted card media (empty / dummy / genuine), using the same DIAG and unmodified original ROM; check whether any `CMD1`/MISO byte is actually requested. Only after measured ROM semantics and board evidence should we implement an independent mechanical-contact signal and exact MMC `CMD1` response. Do not drive PD2/PD3 directly from the image `exists()` property, or claim a specific chip identity from insufficient photos.

### J. 2026-10-26 — Confirmed integration, explicit hardware boundary

**Delivered to canonical `SamDelorean/DANA-emu` `main`:** bounded legacy MMC SPI `CMD1 / SEND_OP_COND` fallback implemented in original `src/mame/skeleton/alphasdana_sd.h`, with regression merged into original `tests/d7_sd_static.cpp` and detailed scope in `docs/D7_D8_3_SPI1_DUAL_SD.md`. It responds with R1 ready `00` only from idle for representable standard-capacity cards and preserves the existing SD ACMD41/SDHC path. R1 illegal `04` for ready SD and R1 idle+illegal `05` for large cards requiring SDHC. This is only a legacy MMC/SD-v1 *SPI command compatibility feature*, **not** a verified physical MMC/SD type discriminator, no verified MMC CID/CSD and no empirically proven UK1.5 boot fix.

**Not changed without PCB evidence:** `alphasdana.cpp` SD power/CS and PD2/PD3 pin model, MAME card image devices, original ROM, CPU return addresses, CLK32, existing T executable or separate SD image files. The original manufactured dummy card/presence distinction, CD/WP contact electrical circuit and unidentified extra board chip remain **UNRESOLVED PHYSICAL HARDWARE**. They must not be mocked by setting PD levels from media presence or naming a speculative chip.

**Evidence boundary:** last live 026R2/027 tests prove only original ROM runtime polling with **no SD media mounted**, and not CMD1 traffic. New code and test assertions are in Git but **not compiled, static-assert executed or native-tested** in this intervention. The next real integration proof is same-tree existing DIAG compile + original-ROM SPI1 command capture with a real mounted image and independent SDIRQ settings; only then assign causal impact on splash/desktop.

## 2026-10-26 — Native CMD1 integration / UK1.5 two-condition regression, job 028

**Native qualified, not Palm desktop:** The one existing T DIAG build tree `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag/source` was modified *only at* `src/mame/skeleton/alphasdana_sd.h`. Old Git blob `5967c1a431f3079d509f990cdd253ec1e30ee255`; new Git blob `d63112a80da81472a423593a1087b6fd8feec075`, an exact match to canonical GitHub `main` (`8c9a68e`). `alphasdana.cpp` Git blob `b25c759e2c62ddbdbe0a3e16544458d7e96eef38` remained unchanged. No new MAME source tree, clone or independent build directory was created.

**Real compilation and linked candidate:** `clang++ 21.1.8` ran the production `static_assert` C++20 CMD1/SD/SDHC regression **PASS** using actual installed header. Standard existing incremental `make -j3` (74-line dependency plan) produced confirmed `Compiling src/mame/skeleton/alphasdana.cpp`, `Archiving libmame_danadiag.a`, `Linking danadiagd`. Candidate SHA256 **before** `6f557ee17fb51a96cfad00e6193e6a6b883c6532595221b212a3f76f6e1c13b3`, **after** `f72403cab7e781608f1c3f7050ae245fc62443c29d66c9ceef168461bbe5d2cd`. Operative `bin/dana-diag` remains `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`; original UK1.5 ROM remains `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.

**Two authentic-ROM runs, each PASS 2400 frames:** both used same qualified transient MAME `cfg_sd_both_low` PD2/PD3 external inputs. Run A had **no inserted SD image**. Run B mounted **two synthetic 2-MiB raw images** through `-sd1/-sd2` (not physical dumps or a claim about MMC content). Both returned 0 and remained on second AlphaSmart splash with `LSSA=00072A10`; same sample at frame2400 `PC=1007B09A`, `PDDIR=03`, `PDDATA=80`, `PDSEL=00`, `PDPOL=00`, `PDIRQEN=0C`. No observed boot advance. Both fixture hashes unchanged after runs.

**SPI1 observer boundary:** An observer-only Lua `program`-space `install_read_tap/install_write_tap` on `FFFFF700..FFFFF70B` successfully installed in both runs but logged **SPI1_TOTAL_READS=0 WRITES=0**. Previously, a PD register Lua tap produced false negatives; therefore these zero *observer callbacks* do **not** conclusively prove the original CPU performs zero actual SPI1 transactions. They show **no captured SPI1 command**, and in particular do **not** demonstrate the original ROM requests CMD1. Do not infer a missing MMC response is the Palm OS splash root cause. Direct native driver-level diagnostic hooks (bounded, no ROM patch or invented MMIO) would be required to certify the CPU-origin SPI1 sequence if required.

**Verified execution evidence:** `dcjob 1.1` job [028](https://drive.google.com/file/d/1JfN2Z5ZjGwSYUAE5ANQSkEPzI37Sjcs9/view) SHA256 `4c2701e0f3dfc821deab2a94ced790b72c282185b48b4a7351e95264e27dcf74`; daemon PID `133218`; [official PASS summary](https://drive.google.com/file/d/1SGhWSE4Zb1uBU38tzlgOd9pyDNfEtKPg/view) EXIT_CODE=0, 49 s; [immutable result package](https://drive.google.com/file/d/1lyUpaS3BMfr5B4aLqtW6T2F_ixqix7Ib/view) SHA256 `c91e4b246d2e85b3617851f2e5616ca904f02181a4f83186183a4530bca3ef6b`, matching separate checksum sidecar. Detailed `absent.trace`, `both_inserted.trace`, `build.log`, `qualification.log` remain on T under `work/uk15_qualify_20261025/mmc_cmd1_integrated_028` (the dcjob result tar contains the task stdout and summary, **not** these local trace files).

**Disposition:** CMD1 feature `SOURCE + NATIVE BUILD + PRODUCTION CONSTEXPR PASS`; Palm UK1.5 desktop **FAIL/not reached**. Physical card-detect / write-protect circuit and chip between sockets **still unidentified**; no guessed GPIO electrical model should be merged. Next decisive evidence is original-ROM Ghidra evaluation of `10092F0E`, `10326E38/4A`, `10326904/16`, `10327044` and a qualified bounded native SPI1 driver-level trace plus socket signal attribution. Never call 028 a full boot PASS.

## K. 2026-10-26 — Original Ghidra completed SDIO callback loop root-cause disassembly

**Genuine Ghidra 12.1.3 original UK1.5 ROM, no code/ROM patches, no guest execution in this investigation.** Original guest SHA-256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, existing T project `DanaUK15RelocatedTemp`. New original-local evidence under `work/uk15_qualify_20261025/boot_progress_20261026`:

- `ghidra_slot_rootcause_20261026.txt` (915 lines), `DanaUK15SlotRootCause.java`, covering `10092F0E`, both slot ISR paths and shared `103268DC`.
- `rom_slot_event_origin.txt` (379 lines), `DanaUK15SlotEventOrigin.java`, covering `10325634`, per-slot ISR, `103268DC`.
- `rom_card_callback.txt` (202 lines), `DanaUK15CardCallback.java`, covering the exact trampoline.
- `rom_sdio_callback_body.txt` (297 lines), `DanaUK15SDIOCallbackBody.java`, covering dispatcher at `103220F2`.
- `rom_sdio_flag_producer.txt` (260 lines), `DanaUK15SDIOFlagProducer.java`, covering exact writers of the flag.

### Real event origin: interrupt status, NOT an SD block read

`10326E28 MOVE.W ($FFFFF30E),D0`; then mask `0x0600` and call `10326E76` for slot0. `10326E3A` samples same VZ **interrupt-status LOW** register and masks `0x0900` before calling `10326FCC` for slot1. These handlers in turn invoke shared `103268DC`, then `TST.W D0` / `BNE` back into **the callback dispatch loop**, at `10326EEC` (slot0) and `10327044` (slot1). The previously observed `10092F0E` is **the return after an indirect system dispatch** (`JSR (A1)` at `10092F0C`), NOT the entry of the card driver or the loop itself.

Shared `103268DC` calls `PrvSpiSetPol0` (`103256DE`) or `PrvSpiSetPol1` (`10325768`) to collect a status word, then returns zero unless *all* of these conditions hold:

1. status bit7 clear: `10326920 BTST #7,(A0)` with branch-to-zero-result on nonzero.
2. `global+0x38D` nonzero: `10326926 TST.B (0x38D,A3)`.
3. slot reentrancy counter `slot+0x0A` zero: `1032692C TST.W (0x0A,A2)`.
4. global nesting/state `global+0x1C` zero: `10326932 TST.W (0x1C,A3)`.
5. slot config `slot+0x1C` bit7 set: `10326938 BTST #7,(0x1C,A2)`.
6. sampled status bit6 set: `10326940 BTST #6,(A0)`.

When all six qualify, `1032694E JSR 10325634` dispatches callbacks. The function **retests `global+0x38D`** at `10326962` and returns `D0=1` **only if it remains nonzero**, producing the `10327044 BNE` (or first-slot equivalent) loop. The current ROM **does not poll SPI1 RX FIFO or await MISO at this branch**.

### Exact callback tunnel, verified by original ROM symbolic strings

`10325634 JMP 10321C02` →
`10321C02 JMP 1031CA1A` →
`1031CA1A JMP 103220F2`.

Embedded original ROM symbols identify `SpiSdioCallBacksTunnelS` and `SpiSdioCallBacksTunnelP` along the way. `103220F2` is the actual **registered SDIO callback dispatcher**: it traverses **eight per-device entries**, base `global+0xCC` to `global+0x32C` by `0x4C` bytes each, using the callback address at `entry+0x14+8*callback_type`. It calls a nonnull callback function pointer `JSR (A0)` at `10322122`, passing callback index and stored context; if none installed, skips. It does **not** issue an SD command.

### Precisely who writes the flag `global+0x38D`

Original disassembly `103228B8..1032290A` (callback registration/unregistration logic) tests the pointer entries `global+0xE0,0x12C,0x178,0x1C4,0x210,0x25C,0x2A8,0x2F4` (eight first-type callbacks), then:

- `103228F2 MOVE.B #$FF,(0x38D,A2)` when any relevant callback pointer is present.
- `10322906 CLR.B (0x38D,A2)` when **all eight relevant pointers** are absent.

Hence `+0x38D` means **callback(s) installed**, **NOT** “SD response pending”, “card image present” or a hardware interrupt ACK byte. The callback function itself is **not expected to clear it on every invocation**. `10325F32` reads the same flag to decide whether per-slot interrupt processing should be dispatched. Any previous suggestion “make callbacks clear `+0x38D` to exit” is unsupported and should be superseded by this explanation.

**Precise causal inference, not yet a native runtime measurement:** if slot event bit6 persists, bit7 stays clear, all guard conditions hold and at least one callback remains registered, the ROM deliberately re-dispatches callbacks and `D0` remains 1. Whether a **mis-modelled persistent GPIO/IRQ level or a different software-state condition** keeps this loop active in current UK1.5 is the missing empirical distinction. No physical board circuit can be inferred from just this code, and no extra IC has been positively identified. There is no basis to patch `CMD1`, zero a callback table, fake a return, or change default PD levels merely to bypass this legitimate logic.

### Cross-comparison with recovered AlphaSmart-specific 2003 POSE

Historic vendor `Alphasmart_Dana.zip` was downloaded from PalmDB (archive SHA256 `82ec0a80990c11389e1260b66ba4a43f44202f09ace8ab68a666451dd3939f8a`) and its original `Emulator.exe` statically decompiled through Ghidra x86; separate evidence in [`DANA_POSE_2003_GHIDRA_HARDWARE_REFERENCE.md`](DANA_POSE_2003_GHIDRA_HARDWARE_REFERENCE.md). Its real class `EmRegsVZAlphaSmart` defines external Port D/E/G=0 and internal Port D=0x80, inherited VZ IRQ level code, special SPI2 and Port K MMIO. Current UK1.5 with both low already shows Port D DATA=0x80 and does NOT boot desktop, so this matching input **alone is insufficient**. Vendor POSE readme specifies Dana **1.2** ROM, packaged 1.2.1; it has **not** been run, nor can it validate UK1.5 desktop merely by existing. No general POSE fork checked so far contains this historical Dana-specific class.

**Next decisive native observation if explicitly authorized:** read guest live RAM at system global pointer in low-memory address `0x300`, particularly `+0x38D` and the relevant callback pointer array plus per-slot `+0x3C, +0x1C, +0x0A`; simultaneously read VZ `ISR_L=FFFFF30E`, PortD input and PDPOL/PDIRQEN/PDIRQEG in a short original-ROM trace. Determine *which* condition maintains `D0=1` and which interrupt source is continuously asserted, comparing with POSE vendor PortD and inherited VZ IRQ semantics. No second DIAG, guest patches, speculative part numbers or redundant builds.

## L. 2026-10-26 — ROOT CAUSE NATIVE: PrvSpiSetPol requires 3 low reads; static GPIO causes wait or IRQ storm

**Conclusive causal diagnosis for the *four tested static socket input configurations*, not a claim that the Palm OS desktop now boots.** Original UK1.5 ROM SHA-256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`; single already built `source/danadiagd` SHA256 `f72403cab7e781608f1c3f7050ae245fc62443c29d66c9ceef168461bbe5d2cd`; operative binary unchanged. Work reused original pre-qualified 027 observer and exact source; no alternate MAME build, source changes, ROM patch, CPU return patch, added peripherals or card images. All true UK1.5 traces `work/uk15_qualify_20261025/boot_progress_20261026/irq_rootcause_live/`, including `postboot_low.log`, `postboot_high_fixed.log`, `pd2high_pd3low.log`, `pd2low_pd3high.log`, `rom_pol_wait_exit.txt`. **Important observer safety:** an initial attempt read RAM and interrupt registers at frame 1, freezing the guest at PC=10005360. It is INVALID evidence. The exact original 027 observer was re-run unmodified (2400 frames reaches original SD stack), then one additional state-only probe at frame900 (after initialization) was used. The first high test reused 027's low-only Lua assertion and is INVALID (stderr indicated "Input config SDIRQ != 0"). The corrected high run passed 2400 frames.

### Original-ROM Ghidra: precise unmet condition

Recovered from original binary via Ghidra 12.1.3, script `DanaUK15PolWaitExitAudit.java`, output `rom_pol_wait_exit.txt`:

- Slot0 `103256DE` **PrvSpiSetPol0**:
  - `103256EA` reads `PDDATA=FFFFF419`, tests `PD2&0x04`; if high, `103256F4` XORs `PDPOL` bit2.
  - `103256FA` reads PDDATA, tests **PD1&0x02**; if high, `10325704` XORs PDPOL bit1.
  - `1032570A` waits 250 units through original OS trap (HwrTimeWait), return at `10325712`.
  - `10325712..10325728` samples **`PDDATA & 0x06`**. If **either PD2 or PD1 is high**, resets D3 to **0**; if **both low**, increments D3. Repeats until D3 reaches **3 consecutive low samples**; only then returns at `10325756`.
- Slot1 `10325768` **PrvSpiSetPol1**:
  - `10325774` tests PD3`0x08`, toggles PDPOL bit3 if high; `10325784` tests PD0`0x01`, toggles PDPOL bit0 if high.
  - Delay, return `1032579C`; `1032579C..103257B2` samples **`PDDATA & 0x09`**, requires **PD3 AND PD0 low** for **3 consecutive samples**; returns at `103257E0`.
- VZ source `alphasdana.cpp::pd_r` drives PD2/3 from fixed `:SDIRQ` input switches (independent of media and output drive/power), but PD0/PD1 are output latch bits (`PDDIR=0x03`). This is the exact minimal **physical-input response missing**: the two status lines need the correct board-specific state/behavior, not more MMC commands.

### Original-ROM native measurements

The original ROM uses `PDIRQEN=0x0C`, `PDIRQEG=0x00` (LEVEL interrupts), `PDDIR=0x03`; it toggles `PDPOL` while seeking valid input. At frame900: `IMR_L=0xF0ED`; `global=(u32 at RAM $0300)=0006DCC4`; `global+0x38D=0` **all four configurations**; `global+0x1C=0`; **0 callback entries installed** in the eight tested slot registrations (`global+0xE0 + n*0x4C`). Hence the prior K section's loop through callbacks **is not the active cause of THIS guest stall**. The callback code exists statically, but native flags prove none was awaiting service; do not invent a callback failure.

| Live SDIRQ PD2/PD3 (raw) | Frame900 PDPOL | Frame900 ISR_L / IPR_L | Original-ROM state frame2400 | Interpretation |
|---|---|---|---|---|
| both low `00` | `00` | `0C00` / `0C00` | slot0/1 callback/interrupt service recurs, LSSA `72A10` | Valid 3-low debounce can finish, but **INT2+INT3 stay LEVEL-asserted** indefinitely as physical input stays low and POL=0, unmasked by `IMR_L`. |
| both high `0C` | `04` | `0402` / `0402` | stuck in **PrvSpiSetPol0** under `1032596A`, LSSA `72A10` | PD2 HIGH resets counter D3 on each sample: **can't acquire 3 lows**. INT2 simultaneously active while POL bit2=1, plus timer1 pending bit1. |
| PD2 high/PD3 low `04` | `04` | `0C02` / `0C02` | same slot0 wait, LSSA `72A10` | PD2 HIGH prevents slot0 debounce; both relevant level IRQs asserted. |
| PD2 low/PD3 high `08` | `00` | `0402` / `0402` | stuck in **PrvSpiSetPol1** under `103259CE`, LSSA `72A10` | PD3 HIGH prevents slot1 3-low debounce; INT2 asserted. |

All four individual runs reached frame2400/40s, did **not** reach Palm desktop and returned code0 as bounded emulator exits. **Runtime is not a regression PASS of boot**.

**Definite, bounded root cause:** the current model supplies static, user-configured external PD2/PD3 **without a validated physical SD-socket detect/IRQ response**. High leads to infinite original-ROM debounce; low leads to unacknowledgeable level-triggered IRQ2/3 re-entry. The exact missing device behavior is the board's **input/polarity/interrupt state transition or an equivalent real electric acknowledgment**; **we cannot yet determine which IC, contact, pull-up/down or pin is responsible** without source-backed vendor POSE more detailed/PCB. Do **not** “fix” by forcing both low or high permanently, deleting callbacks, spoofing (D0), masking IRQ2/3 indefinitely, treating raw SD image mount as a physical switch, or changing the VZ edge/level algorithm contrary to UM.

The vendor-specific original POSE `EmRegsVZAlphaSmart::GetPortInputValue` returns 0 for Port D (and E/G), and `GetPortInternalValue(D)=0x80`; this is actual historical *software configuration*, but native both-low `:SDIRQ=00` already confirmed it is **not sufficient by itself** in our emulator. The vendor software binary's PCB interface logic for CD/IRQ remains to be compared, using the already recovered vtables and GPIO/interrupt handlers — not a newly invented external chip.

**Next bounded resolution step:** real system trace over `103256EA..10325756` / `10325774..103257E0` coupled to startup GPIO outputs PD1/PD0 and INT2/INT3 status, then reproduce precisely the real board/device signal state machine after source evidence. A deliberately synthetic transient input pulse can establish a counterfactual causal test, but cannot be merged as hardware truth. Preserve one DIAG and original ROM.

### Synthetic input-transition counterfactual — does not establish board truth

A **temporary experimental Lua I/O-field override only** was attempted after static PD tests to ask whether a transient pin transition would by itself allow UK1.5 to leave second AlphaSmart splash. Input fields were manipulated through MAME's documented `ioport_field:set_value/clear_value`, not ROM writes, PC/CPU injection or MAME source modifications. The scratch `synthetic_switch_counterfactual.lua` and `synthetic_switch*.log` are contained solely in the existing T `irq_rootcause_live` work directory. Result: still `LSSA=0x00072A10` at frame3600, no desktop. **Not a valid fixed-polarity/controlled-transition PASS:** the `IPT_CONFIG` field changed with one-frame delays and `set_value(0)` did not restore high; the subsequent `clear_value()` run began with a low input before unexpectedly reading high by frame270. These samples cannot establish a correctly reproduced board switch waveform, nor exclude an appropriately-timed transition. Do not interpret them as native hardware pin timing, export them as product behavior, or use them to choose a fake auto-pulse algorithm. Original static four-profile results, Ghidra's explicit three-low-sample conditions, and callback flag=0 diagnosis remain authoritative.

**Final immutable integrity check after investigation:** driver source Git blob `b25c759e2c62ddbdbe0a3e16544458d7e96eef38`; same single DIAG candidate SHA256 `f72403cab7e781608f1c3f7050ae245fc62443c29d66c9ceef168461bbe5d2cd`; installed operative binary SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`; original private ROM SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. Repaired the *transient* `cfg_hi` scratch XML to its intended highs; no isolated emulator build/binary created, no driver source/ROM modifications.

## M. 2026-10-26 — Historical POSE Dana 1.2.1 ROM confirms same original slot algorithm

Investigated the actual 2003 POSE AlphaSmart-specific executable and original included `Dana1.2.1.rom` by static PE/Ghidra and original 68k binary comparison; full methodology, hashes, source links and controlled native comparison in [DANA_POSE_2003_GHIDRA_HARDWARE_REFERENCE.md](DANA_POSE_2003_GHIDRA_HARDWARE_REFERENCE.md). Vendor Dana 1.2.1 and current authentic UK1.5 share **identical observed 68k sequences** for `PrvSpiSetPol0/1`, including the exact 3-consecutive-low-samples per-slot requirement and GPIO polarity toggle. This invalidates the speculation that UK1.5 alone introduced the missing socket debounce.

**One concrete emulator difference**: POSE generic `EmRegsVZ` writes `PDPOL` through `StdWrite` without calling `UpdatePortDInterrupts` on that write, whereas current MAME `pd_extra_w` recomputes level INT2/INT3 immediately. The original vendor Dana override has fixed Port-D inputs and inherits generic VZ IRQ handlers. This is an implementation discrepancy, not yet verified Motorola electrical truth or a proven boot fix.

Bounded native test with both ROMs on **one existing DIAG**: vendor 1.2.1 stuck earlier at `CURPC=100052BC`, `LSSA=0` from first through 2400th frame; UK1.5 on identical DIAG/observer progresses to `LSSA=72A10` then remains. Do **not** assert the historical POSE emulator itself failed or that this older ROM reached SD under MAME; older-ROM startup requires a separately analyzed firmware memory/bootstrap compatibility difference before comparing SD runtime. No binary, source/ROM writes, isolated emulation build or guest PC substitution.

## N. 2026-10-26 — Reverse-engineered successive blockers: INT2/INT3 and on-board NOR command set

**This section records real CPU results and original UK1.5 Ghidra 68000 code, not a new emulator version.** The one existing DIAG source/Clang21 cache/target at `mame-stage/diag/source` was used for **two reversible** source-only diagnostic counterfactuals, and restored/recompiled to **identical final hashes**. No additional DIAG tree/standalone candidate, no change to operative `bin/dana-diag`, no original ROM modifications, no proposed spoofed CPU return.

### Trial A: exact historical POSE IRQ update-event semantics

Vendor Dana-specific `EmRegsVZAlphaSmart` inherits generic POSE VZ Port-D IRQ handling. Generic GPL [`EmRegsVZ.cpp`](https://github.com/cloudpilot-emu/pose-original/blob/master/SrcShared/Hardware/EmRegsVZ.cpp) binds `portDPolarity` and `portDIntEdge` to regular `StdWrite`; `portDIntReqEn` has a handler that recalculates IRQ, and `portDData` updates the IRQ via `PortDataChanged`. Temporary MAME `pd_extra_w()` only invoked `sd_gpio_irq()` for `reg==1` (IRQEN), and `pd_w()` only for `reg==1` (DATA), instead of on *every* register write. Single-tree candidate SHA256 `b45e81458d34f68dfdd34ed76f100b1c425e0fe936dd5df6f40104ba01ce7ab5`, compiled with existing `make -j3`. **Original UK1.5 2400-frame runs:**

| Frame900 physical SDIRQ | Pre-existing MAME ISR_L | Historical POSE-update-timing ISR_L | UK1.5 boot |
|---|---|---|---|
| Both PD2/PD3 LOW, `00` | `0C00` | `0C00` | Both remain on AlphaSmart `LSSA=72A10` |
| Both HIGH, `0C` | `0412` | **`0012`** | Both remain on AlphaSmart `LSSA=72A10` |

**Outcome:** genuine timing difference exists, but **copying POSE update timing is insufficient**. Reverted exact original source/compiled candidate after the test. Source/logs under `work/uk15_qualify_20261025/pose_historical_reference/irq_parity_20261026/`. NO change integrated into production, because old POSE behavior may be an incomplete simplification of actual VZ hardware.

### Trial B: causal CPU delivery of INT2/INT3, showing a second independent blocker

Original ROM at frame900 with physical PD2/PD3 both LOW has `ISR_L=0C00`, `IPR_L=0C00`, `IMR_L=F0ED`, `PC=1007B098` (inside `HwrDelay`), `global+38D=00`, callback count=0, second AlphaSmart LCD. For a strictly synthetic, **diagnostic-only** experiment, temporarily suppress **CPU IRQ4 delivery** of only INT2/INT3 by changing level4 condition in `update_irq_lines` from `active & 0x00000C14` to `active & 0x00000014`. All guest-visible pending registers, Port-D GPIO, Flash map and ROM unchanged. Same-tree candidate SHA256 `90212cb3c0a7b7c52765dd1ec654073ec1d14f301a315ea35ef788f0cbe87c22`, genuine native bounded 2400 frames:

- `PC=00084654` from frame295 onward; `ISR_L=0000` (masked), `IPR_L=0C02` still records INT2/3/timer sources, `IMR_L=FFFF`; LCD still `72A10`. CPU is **not executing a successful desktop**.
- A baseline-unmodified original UK1.5 RAM observer proved the **exact instruction bytes** at `00084654` are `14 BC 00 FF` (68k `MOVE.B #$FF,(A2)`) at all baseline sampled frames; the 60+ consecutive bytes match **exactly once** in the original UK1.5 ROM at file offset `0x46B328` (ROM VA `1046B328`). The code was **copied/relocated from original ROM to RAM** as part of genuine startup, not an invented branch.
- To prove why the emulator halts on that write, repeated the diagnostic with real MAME `-log`, still same temporary candidate and private ROM. **Authoritative native `error.log`**:
```
DANA_PHYSICAL_WRITE address=10000000 data=ffff mask=ff00
DANA_PHYSICAL_BLOCKED reason=FLASH_COMMAND_SET_UNVERIFIED address=10000000 data=ffff pc=0008465a
DANA_PHYSICAL_CPU curpc=00084654 ir=14bc sp=0006ef0a usp=00000000 sr=2008 a4=00002818
DANA_PHYSICAL_DECODE csa=018d csd=2283 csgba=8000 csgbd=0000 csugba=0000 csctrl=4150/d000/9c00 dram=0f00/8000/d43f/0000
```
Thus **second blocker unequivocally proven**: a real original-CPU **Flash NOR command write at boot Flash base `0x10000000`**, intentionally stopped by current `alphasdana.cpp::physical_w` guard (`FLASH_COMMAND_SET_UNVERIFIED`), which calls `physical_block()` and suspends CPU. This blocker was concealed by normal unreleased SD interrupts. No extra hardware chip between SD sockets has been identified by this: the address belongs to the flash CS/boot aperture, **not an independently verified extra SD-chip**.

### Original Ghidra exact supported Flash command/ID sets

Used **existing Ghidra 12.1.3** project `DanaUK15RelocatedTemp`; mapped original read-only private ROM offset `0x460000..0x46FFFF` to `0x10460000..0x1046FFFF`, scripts `DanaUK15FlashIdentification.java` and `DanaUK15FlashAcceptedIDs.java`, output `pose_historical_reference/flash_probe_20261026/{uk15_rom_flash_id_ghidra.txt,uk15_rom_flash_accepted_ids.txt,error.log}`. UK1.5-specific relocated RAM routine maps to ROM `1046B30C` and does:

- `1046B328/32C/330`: writes `FF` three times to boot Flash base (reset/read-array).
- `1046B334`: writes `90` (read electronic signature/ID).
- `1046B338`: reads **32-bit ID** from Flash base; `1046B33A` compares with **`0x00208849`**. **If matched**, stores size **`0x800000` (8 MiB)**. This is specifically manufacturer **0x20**, device **0x8849**, STMicroelectronics/Numonyx **M28W640HCB** bottom-boot, 64 Mbit NOR. [Flashrom registry](https://github.com/flashrom/flashrom/blob/main/include/flashchips.h) and [manufacturer datasheet](https://www.part-elec.com/datasheet/micron/M28W640HCB70N6E.pdf) independently verify this ID. **Supported by ROM != proven actual chip topmark or PCB BOM.**
- `1046B364`: writes `FF` to exit ID mode.
- Separate second family `1046B370`: AMD unlock command sequence `F0, AA` at base+`0xAAA`, `55` at base+`0x554`, `90` at base+`0xAAA` (68k byte-access address convention); reads ID and compares sequential cumulative arithmetic (ROM `1046B3BC..1046B3D2`):
  - `0x000122F9` → **`0x400000` / 4 MiB** (manufacturer `0x01`, AMD/Spansion 29LV320 bottom-boot family; [S29AL032D spec](https://www.cs.columbia.edu/~sedwards/classes/2008/4840/Spansion-S29AL032D-Flash.pdf)).
  - `0x00202249` → **`0x200000` / 2 MiB** (ST M29W160EB).
  - `0x002022CB` → **`0x400000` / 4 MiB** (exact ST part **not confirmed**; do not assign model from identifier alone).
  - Unknown ID clears size and handler pointers; reset `F0` on exit.
- The ROM contains symbols `NuPermaCardOpen`, `NuPermaCardSectorRead` and a nearby `LPmCDriver` dispatch table; this code is within the UK1.5 Flash/PermaCard subsystem. The 2003 POSE-bundled Dana 1.2.1 ROM **does not contain the same literal instruction sequence or these newer NuPermaCard symbol names**, so vendor POSE can reproduce an older ROM's SD startup without necessarily modelling these **later UK1.5 memory operations**.
- Imported UK1.5 ROM is only **6,094,848 bytes**, while the supported 0x208849 Flash part nominally has 8 MiB. These are different concepts: supplied dump length vs physical capacity; **do not assume unprovided upper Flash data are zero/FF**, do not mirror partial ROM or redistribute it. For a future flash model, identify actual part/geometry/configuration before choosing an ID and accept only the necessary read-ID/reset/status/program commands that original code invokes, consistent with manufacturer behavior. Preserve side-effect-free code/ROM and avoid fabricated erase/program results.

**Scientific conclusion:** source-level/ROM reverse engineering now proves **two sequential real blockers**: (1) static SD PD2/PD3 Port-D IRQ level/polarity creates repeated IRQ4 or failed debounce under four fixed input profiles; (2) once IRQ delivery is temporarily disabled, original UK1.5 reaches Flash NOR ID operations that current DIAG explicitly refuses and suspends on. No Palm desktop has been observed and no physical part marking on the board has been proved. Neither spoof CPU returns nor suppress IRQs nor emulate an unsupported chip identity in the product merely to declare PASS.

**Reproducibility/integrity:** experiments ran in **one** original DIAG cache and candidate, both temporary source modifications **restored and recompiled**; final original source Git blob `b25c759e2c62ddbdbe0a3e16544458d7e96eef38`; final candidate SHA256 `f72403cab7e781608f1c3f7050ae245fc62443c29d66c9ceef168461bbe5d2cd`; operative `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`; ROM `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. No extra executable copy. This is only a reference / diagnostic finding and does **not** claim a product fix or completed boot.

## O. 2026-10-26 — NOR implemented, CPU verified; missing authentic flash bytes

**REAL integration** in canonical `main`/single T DIAG, [source commit](https://github.com/SamDelorean/DANA-emu/commit/0e8b0016dd861214b62da527413718fe1eab14a3), [full qualification](DANA_NOR_FLASH_20261026.md), [MAME Lua test](../tests/dana_nor_id_readonly_native.lua). Original ROM used 0x1046B328 `FF–FF–FF–90` electronic-signature command sequence. Optional, explicitly selected 16-bit ST/Numonyx M28W640HCB NOR profile gives manufacturer `0x0020`, device `0x8849`; read-array `FF`, read-status `70` (`0080`), clear-status `50`. Other commands guard; power-on/default chip identity unknown (physical board marking not established). Clang21 **real compile+link PASS**. Native original firmware bus qualification `NOR_MODEL_NATIVE_READONLY_PASS` (720 frames) verifies modes and original ROM byte preservation.

**New causal original CPU proof:** with *transient diagnostic* suppression only of CPU IRQ4 delivery from INT2/INT3 (never kept), original UK1.5 repeatedly executed `FF/90/ID/FF` and progressed past the former `FLASH_COMMAND_SET_UNVERIFIED` guard. New real stop `FLASH_BYTES_NOT_SUPPLIED` at `0x107F0000` (offset `0x007F0000` in 8MiB NOR), outside supplied private dump `6,094,848` bytes, at PC `00083D2C`. Unknown upper ROM bytes are NOT guessed, filled, mirrored, or redistributed. After diagnostic, original IRQ delivery restored, NOR feature retained; exact final candidate SHA256 `c8fe219c9ad8f14a1c3f6ae5c6d06b20c1a5c9a7c32a94b25edfdf178993df3e`, source Git blob `343a6f0078e061be541797dd4af25383a7ec2dd4`; untouched original ROM SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` and operative DIAG SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. **Neither SDIRQ deadlock nor Palm desktop is resolved.** Remaining evidence required: actual Flash data/verified erased-state semantics for 0x007F0000 and faithful board SDIRQ interface. No isolated build.

## P. 2026-10-26 — Native post-NOR progression RTC, UART2, SPI1 and verified sleep branch

**One canonical DIAG, real original UK1.5 ROM, no new MAME clone/branch/tree.** This section records implementation and native results of the *existing* source driver, plus clearly separated diagnostic-only IRQ and power control experiments. Original firmware SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` and operative `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` remained untouched. Current committed source Git blob `0d59e7965171878b07ade29b3fbb18eec6745191`, canonical candidate `source/danadiagd` SHA256 `b7dfb27a3d30908043b15cd0f1604c9b2528277890370ba37c14cf0c94dfe3d8`; all C++ builds compiled and linked within existing `source/build/dana-diag`.

### A. Exact NOR updater provenance and optional authentic virgin-cell behavior

Located original `AlphaSmart_Dana1_5_Flash.zip` under T `/home/spc/Projects/Dana-OS3K/firmware/research-only/`. The actual UK150 PRC updater contains **119 Flas resources of 50 KiB and a final one of 2 KiB**: exact coverage `0x000000..0x5CFFFF`, total **`0x5D0000` / 6,094,848 bytes**. The vendor updater **does NOT contain** data from `0x5D0000..0x7FFFFF`, even though UK1.5 Ghidra identifies the NOR 8MiB `0x208849` device and original guest probes e.g. `0x107F0000`. For never-programmed NOR, the data-cell erased state is **`0xFFFF`**, but an actual *used* Dana might hold persistent data. Implemented opt-in `:NOR_FACTORY=1` (requires `:NOR_PROFILE=1`) returning erased read-array words **only** in the absent upper array range and only within the 8MiB geometry. Default `:NOR_FACTORY=0` still guards on missing bytes. No original ROM modified, padded on disk or mirrored. [`DANA_NOR_FLASH_20261026.md`](DANA_NOR_FLASH_20261026.md).

**CPU counterfactual** with *separately temporary IRQ4 INT2/INT3 delivery suppression* traversed the original ROM `FF→90→ID→FF` sequences, then read all erased upper-array words through `0x107FFFFE`, reaching new original CPU MMIO accesses. Entire temporary CPU-IRQ suppression was restored/recompiled after each run.

### B. Newly implemented on-chip VZ registers, genuine CPU events

Real CPU arrived at `0xFFFFFB04`: **`RTCALRM`** 32-bit hour/minute/second alarm (new read/write/save/reset/event bit `0x0004` on RTC 1Hz tick); then read `0xFFFFFB1A` **`DAYR`** and `0xFFFFFB1C` **`DAYALARM`** (9-bit read/write/save/reset, day comparison). Native source regressions in the *same existing emulator* passed 720 frames:
```text
ALARM_REGISTER high=161C low=0035
FACTORY_ERASED_NOR 7f0000=FFFF ROM0=0000
DAYR_DAYALARM_9BIT_PASS
RTC_ALARM_AND_FACTORY_NOR_BUS_PASS
END=720
```
Genuine UK1.5 CPU then wrote its own RTCALRM and day/dayalarm values, successfully passed all previously missing-register guards.

Next original CPU read `0xFFFFF918` (**UART2 UMISC2**), not part of the formerly implemented UART1 map. Implemented bounded 7-word **UART2 register bank** `0xFFFFF910..0xFFFFF91D`, with reset `UBAUD2=0x0002` per Motorola VZ **user manual addendum** (supersedes older 0x003F erratum). CPU subsequently wrote UTX2 `0xFFFFF916=0x0800`, which is a documented **`NOCTS` control bit, NOT outgoing serial data**. Production handler now accepts that control change and blocks unsupported actual FIFO traffic. Real CPU log `DANA_UART2_UTX_CONTROL value=0800 mask=ffff`; no fictional UART2 wire transport claimed. Canonical code update [`04555a7a`](https://github.com/SamDelorean/DANA-emu/commit/04555a7a87cf680af6510137ed439e44ddcc2491).

### C. Original SPI1 deadlock disassembled and resolved at the internal engine/bus boundary

After NOR + RTC + UART2 original CPU reached `0x10326174`:
```68k
1032616E MOVE.W #-1,$FFFFF702
10326174 ORI.W #$0100,$FFFFF704  ; XCH
1032617A MOVE.W $FFFFF704,D0
1032617E ANDI.W #$0100,D0
10326182 BNE 1032617A             ; wait for internal XCH to clear
```
Former MAME driver called `DANA_SPI1_BLOCKED unsupported_bus_mode control=0730 PJSEL=cf SPC=0000` and **suspended CPU** purely because the original guest's PJSEL selected PJ0/PJ1/PJ2 as GPIO. Motorola [MC68VZ328 User Manual §§10.4.9/13.2, 13.3](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf) distinguishes internal master-shift `XCH` from *external pin multiplexing*: PJSEL=1 disconnects the peripheral pin and PJSEL=0 enables it, while internal `XCH` auto-clears at end of FIFO shift. MAME implementation now:
- completes internal shift/timing even when PJ0/PJ1/PJ2 are configured GPIO;
- routes external SD bits only when **both MOSI/PJ0 and SCLK/PJ2** are dedicated functions; isolates SD images otherwise;
- treats disconnected MISO/PJ1 as high, consistent with documented GPIO pull-up default; does not fake card responses;
- preserves previously verified SPI1 dedicated-pin functionality, bus contention rules, and guards for unsupported control/sample modes.

**Native targeted MAME bus regression PASS with original UK1.5 loaded, no ROM writes**:
```text
GPIO_MUX_XCH_START
GPIO_MUX_COMPLETE ctrl=063F rx=FFFF
DEDICATED_MUX_COMPLETE ctrl=063F rx=FFFF
SPI1_INTERNAL_XCH_AND_ISOLATION_PASS
END_FRAME=450
```
Tests recorded in GitHub [`tests/dana_spi1_mux_internal_native.lua`](../tests/dana_spi1_mux_internal_native.lua), commit [`cfcbcfa`](https://github.com/SamDelorean/DANA-emu/commit/cfcbcfa52bf6796a8c736e1742b57536618daf09). A *temporary diagnostic IRQ4-filter* original ROM trial with this SPI1 correction moved beyond the earlier `0x10326174` `XCH` loop, reaching legitimate on-chip `PCTLR` power-down. **DO NOT call this Palm desktop PASS.**

### D. Subsequent PCTLR/STOP is a real firmware sleep transition, not an unrelated missing chip

Original Ghidra 12.1.3, script `DanaUK15PowerStopBranch.java`, full `uk15_stop_sleep_ghidra.txt` under `pose_historical_reference/nor_rtc_integrated_20261026/`:
```68k
10079766 ANDI #$7FFF,SR
1007976A NOP
1007976C MOVE.B #$C0,($207,A0)    ; PCTLR $FFFFF207
10079772 STOP #$2000
10079776 TST.B $00000111
```
PCTLR `C0` masks reserved bit6 leaving **PCEN=1, WIDTH=0**: the Motorola VZ power module removes CPUCLK while SYSCLK peripherals stay active. `STOP #2000` is the 68000 documented privileged sleep until qualifying interrupt/reset. Production MAME intentionally guards `PCTLR_CPU_BURST_UNIMPLEMENTED` rather than falsely executing at full speed; **do not “fix” by hardcoding full CPU speed.** A separate **reversible-only** trial allowed PCTLR WIDTH=0 with the guest 68000 native STOP semantics; ROM progressed to `PC=10079776` and remained in STOP through frame2400, without `DANA_PHYSICAL_BLOCKED`. That demonstration was **combined with the temporary suppression of INT2/INT3 IRQ4**; without interrupt delivery, no natural wakeup can be inferred. The console remained on the second splash; no desktop. Source/compiled candidate restored after trial. Thus this is a legitimate VZ low-power branch whose wake source must be analyzed; not a new fabricated chip.

### E. Remaining real limitation

**Default/native electrical behavior still unqualified:** `:SDIRQ` PD2/PD3 are static config pins; both low produce IRQ4 INT2/3 continuously, while high prevents original three-low debounce in `PrvSpiSetPol0/1`. The user-supplied manufacturer POSE historical class `EmRegsVZAlphaSmart` returns input D=0, but this does not reveal physical board contact logic; neither more SD CMD1 replies nor blind IRQ masking is a valid fix.

Under **normal IRQ4 delivery** the authentic original ROM still loops in initial SD initialization/`HwrDelay` and stays at LSSA `0x00072A10`. Under **temporary** IRQ4 suppression it can reach PCTLR sleep; the CRT/RTC and SPI1 corrections are genuine tested, but actual display progression requires a faithful IRQ electrical/input-state model **and** a qualified power wake source. Default NOR identity and factory-erased-memory hypothesis remain deliberately **opt-in**; non-diagnostic users continue to receive real guardrails instead of hidden workarounds.

**State / source integrity:** completed features synchronized to GitHub `main`, all regression files saved; one single T DIAG candidate, no duplicated build tree. Final source Git blob `0d59e7965171878b07ade29b3fbb18eec6745191`, candidate `b7dfb27a3d30908043b15cd0f1604c9b2528277890370ba37c14cf0c94dfe3d8`. Original ROM and operative binary intact.

## Q. 2026-10-27 — Native VZ IRQ2/3 polarity, IRQ6 power wake and PLL STOP, four regressions PASS

**Implemented and qualified** on the **same** T DIAG candidate and private original UK1.5 ROM; [source commit `4789f0c`](https://github.com/SamDelorean/DANA-emu/commit/4789f0c33bfc9c322d548321eea6a4812890bc57), [new 3500-frame regression](../tests/dana_uk15_power_irq6_original_cpu_native.lua), [complete qualification](DANA_UK15_POWER_WAKE_DIAG_20261027.md). Source Git blob `3ae04027ef0a5a0de89a5f51a22902368ad6ca33` (matches T exactly); candidate SHA256 `4614a42f476b8675e8444a2a340376a13ebbcaeaa8b08e5c4c7638b03cbf2de6`. Original ROM and prior operative binary unchanged.

- Corrected Port-D **PDPOL** polarity per original Motorola VZ UM (§10.4.5.6): INT2/3 active HIGH when POL=0; low when POL=1. Previously inverted model caused steady IRQ4 for inputs LOW. Under both PD2/PD3 LOW, actual UK1.5 `ISR_LO=0000` at frame900; without spoofing callbacks, manual IRQ suppression or firmware patch.
- Added physically distinct **PD7/IRQ6** and power key scan event (preserves ST keyboard), ICR polarity/edge and pending mask, plus **PCTLR WIDTH=0 native STOP** and clock/PLL wake scheduling driven by real qualified interrupt. Ghidra confirms `10079772 STOP #2000` then after power key `1007A196 STOP #2000`. Address `1007A19A` is the instruction **after** STOP, not a software polling loop.
- Original-CPU native proof: frame1380 `PC=10079776`; press at frame1600 produces frame1601 `PC=1007A19A` with `PD7=00`, `ICR=1000`, `PLLCR=238B`. **`ORIGINAL_CPU_STOP_TO_WAKE_IRQ6_PASS`**, 3500 frames, original ROM, no new build tree or false pass. Three old native regressions rerun *after* this source change: SPI1 XCH and isolation PASS, NOR ID/status PASS, RTC/DAY/NOR factory profile PASS.
- Controlled on/off timing matrix (press at frame1, 650, 1150) did **not** reach Palm desktop. Power input alone is insufficient. **Palm OS desktop remains NOT ATTESTED**; second low-power path at `1007A196` and guest state/power source are next meaningful targets. Do not proclaim boot complete, patch guest RAM (including `00000111`) or infer unidentified PCB chip without evidence. `:NOR_FACTORY=1` is an **explicit** diagnostic assumption, never the implicit state of a used Dana.

## Q. 2026-10-27 — Real native PCEN wake-up integration and original ROM re-sleep proof

**Confirmed original UK1.5 and manufacturer MC68VZ328UM §§4.5.3–4.5.4, not a Palm desktop PASS.** All measurements were taken on authorized T's **single canonical DIAG** `mame-stage/diag/source`; no isolated MAME tree, fake guest jump/PC, synthetic IRQ, ROM alteration or operative replacement.

**New, qualified silicon behavior.** Motorola/NXP [MC68VZ328UM §4.5.3, Fig. 4-5; §4.5.4 PCTLR](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf): during doze/burst mode, a valid wake event automatically disables the PCM and restores 100% CPUCLK while preserving the `WIDTH` bits. Previously the current Dana emulator retained `PCTLR.PCEN=1` after actual IRQ. Within the existing driver `alphasdana_state::update_irq_lines()`, on the *real*, unmasked pending IRQ and only original physical profile, after PLL reacquisition (if sleeping), clear `PCEN` and keep `WIDTH` unchanged; do not invent an interrupt or disable any IRQ line. New console `DANA_PCM_WAKE pcen=0 pctlr=... irq=...`. Actual source patch [commit c61e976](https://github.com/SamDelorean/DANA-emu/commit/c61e97681f860d28aa173bed12c1866391adb096), original `main`, Git blob `595eb540ae84696070bf9b145f0c3d73f5ef95ea`, **exact same as T source**; linked Clang21 existing candidate SHA256 `50487355727baab96b93acaebc108cb40deb2d7fc00c0fec225f7e96a5dae9de`.

**Ghidra correction: `0x1007A19A` is NOT a stuck spinning instruction:** original UK1.5 disassembly `1007A18A MOVE.W (0x202,A0),D0`; `1007A18E BPL 1007A18A`; `1007A190 ORI.W #8,(0x200,A0)` (set DISPLL); `1007A196 STOP #0x2000`; `1007A19A RTS` (PC points here because CPU remains STOPPED). `1007A160 MOVE.B $00000111,D0`; `1007A176 BEQ 1007A18A` takes lower branch when RAM byte `0x111=0`. **Do not claim ROM is spinning in RTS or spoof `0x111` to obtain fake progress.**

**Repeatable actual-original-CPU native qualification.** [`tests/dana_pcm_wake_original_uk15_native.lua`](../tests/dana_pcm_wake_original_uk15_native.lua) committed [4c73e60](https://github.com/SamDelorean/DANA-emu/commit/4c73e60ada610d03632505a196eceab5eb18a089) and executed directly in canonical DIAG with only the explicitly selected, previously qualified `:NOR_PROFILE=1`, `:NOR_FACTORY=1` fixture and original UK1.5. No CPU/guest patch; user On/off scan code15 triggered via actual input field in Lua. Native results:
```
BEFORE_POWER frame=1500 pc=10079776 pctlr=80 pllcr=2483 ipr=00000000 lcd=00072A10
POWER_PRESS
POWER_RELEASE
AFTER_POWER frame=1800 pc=1007A19A pctlr=00 pllcr=238B ipr=00000000 lcd=00072A10
END frame=2400 pc=1007A19A pctlr=00 pllcr=238B ipr=00000000 lcd=00072A10
PCM_PCEN_GUEST_WAKE_PASS
PALM_DESKTOP_NOT_REACHED
```
Console confirmed `DANA_PCM_WAKE` on real guest generated IRQ (e.g. Timer1 and IRQ6). At release `IPR=0`: **the firmware itself executed another PLL sleep and native STOP**, with no new pending wake event. This is independent of PCM PCEN persistence and cannot be resolved by adding an invented wake pulse. Exact evidence under existing T `work/uk15_qualify_20261025/pose_historical_reference/pcm_wakeup_20261027/{pcm_wake_regression.log,power_native.log,error.log}`.

**Timing counterchecks (not UI boot):** actual original ROM On/off press at frame30 for20 and frame450 for20, followed to frame3600; both configurations continued executing native firmware at later checkpoints and returned to legitimate STOP while `LCD.LSSA=00072A10`. Longer three-press experiment frame1600/2300/3100 through frame5200 likewise remained at second AlphaSmart splash. These outcomes reject "just press power at the right time" as a proven fix, though not every physical key sequence is exhausted. RAM flag `$111=00` in sampled times; no verified semantics beyond branch test.

**Existing subsystems re-tested on same candidate / authentic UK1.5** with no rebuilding another tree: `tests/dana_spi1_mux_internal_native.lua` PASS `SPI1_INTERNAL_XCH_AND_ISOLATION_PASS`; `tests/dana_nor_rtc_day_native.lua` PASS `RTC_ALARM_AND_FACTORY_NOR_BUS_PASS`; above PCM test PASS. Distinguish these directed CPU/bus PASS from Palm desktop, which is **still not observed**. Final original firmware SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`; untouched operative `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.

**Next actionable ROM root-cause analysis:** trace the genuine caller/callback chain that leads from the AlphaSmart startup stage to `10079766/1007A15C`; correlate `LSSA=72A10`, original UK1.5 RAM power flag `$111`, and actual ST keyboard/RTC/UI event handling. Avoid re-opening closed NOR, RTC/UART2, SPI1 or native PCM tests. The firmware may legitimately idle before drawing the desktop; the missing UI transition is not established to be SD level, unidentified board chip or an additional CPU power bypass. The test demonstrates the PCM correct wake event, **not a solved complete Palm OS initialization**.
