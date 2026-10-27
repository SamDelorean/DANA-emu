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
