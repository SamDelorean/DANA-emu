# Dana Palm OS UK1.5 — native PLLCR PASS, first actual block ICEMCR; ICE pair implementation contract

**Date:** 2026-10-25. **Research/native CPU testing performed in this ChatGPT conversation; Codex does coding only.** No commercial Palm firmware bytes are committed. **Real Palm OS UI has NOT booted.** The native test is authentic UK updater-derived SmallROM reset under the currently unqualified physical NOR decode hypothesis.

## Canonical evidence: exact program and executable

- Current CodeX published `main@fb68ce6b69a994dbfa3317ff558e5f3440b26409`, source path `src/mame/skeleton/alphasdana.cpp`. Git blob `8c75dcbda98cd51cdeacebc0b509561e96cd15a9`; SHA256 `207bf697be4ddafc90ab4b36103d15963f7871b22a1c72ba1dd3cf1a0dceaea1`. Exact match confirmed against T before build; six focused changes only to PLLCR declaration, state, save/reset, handlers and `0xFFFFF200` map.
- **ONLY** T DIAG tree: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`. Updated `source/src/mame/skeleton/alphasdana.cpp` SHA256 as above. Incremental MAME Clang21 21.1.8 built and linked **PASS** on existing cache. Command: `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21`.
- Built/tested **candidate** `source/danadiagd` SHA256 **`aa02f3b4fcfbe3e661d6bd7532cd6ca179d9264b1219a92253a81eff8e84a708`**, **NOT INSTALLED**. Previous qualified sole `bin/dana-diag` SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`** STILL INSTALLED/UNCHANGED. Rollback copy of prior source kept privately under test run dir.
- Owner's privately extracted `ROMUpdater_enUK150R1.prc` exact authentic 120-resource raw Flas stream `0x5D0000`, SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. SmallROM original 0x0; BigROM original 0x8000, coverage `0x000000-0x005CFFFF`; no fabricated `0xFF` or original modifications.
- Actual native CPU command: `source/danadiagd asmdana -rom <private UK1.5.raw> -video none -sound none -nothrottle -skip_gameinfo -nowriteconfig -autoboot_script <private observer.run.lua> -autoboot_delay 0 -log -oslog`; bounded 240 frames, observer stopped MAME normally rc=0. **Exit code 0 DOES NOT indicate Palm OS boot.**
- Private evidence files on T: `diag/work/uk15_qualify_20261025/pllcr_20261025_131609/{build.log,native.err,trace.txt}`. Neither raw firmware nor original byte sequences are published.

## Authentic guest 68k CPU result

```text
DANA_PHYSICAL_IMAGE bytes=6094848 ... read_only=1 topology=linear_array_unqualified
DANA_PHYSICAL_COVERAGE classification=UPDATER_DERIVED_RESET_EXPERIMENT supplied=00000000-005cffff unknown_tail=BLOCKED reset_decode_window=01000000 geometry=UNQUALIFIED
DANA_PHYSICAL_RESET vectors=firmware CSA=00b0 CSCTRL2=1000 CSCTRL3=9c00
DANA_PHYSICAL_VECTOR_READ address=00000000 data=0000 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000002 data=0316 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000004 data=1000 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000006 data=02a2 mask=ffff
DANA_PLLCR value=24a3 clko_enabled=0 pfsel=87 clock_tree_unchanged=1
DANA_PHYSICAL_UNIMPLEMENTED_MMIO write address=fffffd0c mask=ffff
DANA_PHYSICAL_BLOCKED reason=MMIO_WRITE_UNIMPLEMENTED address=fffffd0c data=0008 pc=10005164
DANA_PHYSICAL_CPU curpc=1000515e ir=317c sp=00000316 usp=00000000 sr=2700 a4=10000338
```

Lua bus-tap independent read of native execution shows accepted sequential guest **SCR @ FFFFF000**, **WATCHDOG @ FFFFFB0A**, **PLLCR @ FFFFF200** and finally blocked word WRITE `0x0008` (mask `FFFF`) to **ICEMCR @ FFFFFD0C**, `CURPC=1000515E`, real instruction **`MOVE.W #$0008,($0D0C,A0)`** with `A0=FFFFF000`. MAME `pc=10005164` is prefetch/next PC, **not** the failed opcode. `SR=2700`, `SSP=00000316`. Native PLLCR PASS with correct value `0x24A3` and consistent gating output `clko_enabled=0` due `pfsel=87`; no PLL retune/sleep was requested.

**NEXT native UNEXECUTED** 68k instruction at `CURPC=10005164`: **`MOVE.W #$0007,($0D0E,A0)`** to **ICEMSR @ FFFFFD0E**, followed by IVR @ FFFFF300 and IMR @ FFFFF304 (current DIAG has existing independent handlers). This instruction is from the verified original private image / already checked 68k disassembly, **NOT a native-observed failure** yet.

## Precise ICE semantics — Motorola MC68VZ328, not generic Palm assumptions

**Primary source:** NXP/Motorola `MC68VZ328UM` https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf **chapter 16, §16.2.3 Table 16-4 ICEMCR**, **§16.2.4 Table 16-6 ICEMSR**. HTML text mirror (public readable): https://motorola.manymanuals.com/processors/mc68vz328/user-manual-32520/300 and https://motorola.manymanuals.com/processors/mc68vz328/user-manual-32520/302 .

- **ICEMCR** — `0xFFFFFD0C`, 16-bit R/W, hardware reset `0x0000`. Defined bits: **6 SWEN**, 4 BBIEN, **3 HMDIS**, 2 SB, 1 PBEN, 0 CEN. Reserved bits 15..7 and bit5 remain zero. Full defined mask `0x005F`. Requested `0x0008` sets only **HMDIS = 1**, turning OFF the ICE internal hard-map that can expose hardwired data in emulator mode. **In normal operation the hard-map is not active anyway**, so this write alone does NOT move the Dana ROM, alter CSA, write Flash, enable breakpoint compare, or enter ICE mode. Keep the state at `0x0008` and allow guest readback while preserving normal CPU memory decode. **Guard real ICE-enabled breakpoint, hard-map and level7 effects if/when genuinely requested**, rather than simulating them.
- **ICEMSR** — `0xFFFFFD0E`, 16-bit R/W/status, hardware reset `0x0000`. **IMPORTANT: use the VZ-specific Motorola UM, not an EZ-derived or Linux header shortcut**: `EMUEN = bit3 (0x0008)`, `BBIRQ = bit2 (0x0004)`, `BRKIRQ = bit1 (0x0002)`, `EMIRQ = bit0 (0x0001)`. Bits 2/1/0 are hardware event flags **W1C**. The next guest `MOVE.W #0x0007` leaves `EMUEN = 0` (normal mode) and clears any three pending emulation/interrupt flags; if reset state was 0, they remain 0. The manual describes EMUEN as read/write; avoid falsely asserting a mode transition from this `0x0007` write. Reserved 15..4 remain zero. If firmware later enables ICE (`EMUEN=1`), model required hardware or **fail closed** with a precisely named reason, rather than enabling fake breakpoints or hard-map.
- **Cross-source bit-order warning:** `linux/arch/m68k/include/asm/MC68VZ328.h` circulating versions label `ICEMSR_EMUEN 0x0001`, `ICEMSR_EMIRQ 0x0008`, contrary to the **MC68VZ328 UM's explicitly spelled out Table 16-6**. The VZ primary manual is authoritative for these bit positions. Verify against actual chip only if contradictory primary erratum is found; do NOT implement `0x0007` as forcing ICE mode on based on this secondary header.
- The CPU will perform **full-word** writes to both registers for this initialization, but must preserve correct 68k byte lanes `mem_mask`, reset/save-state, mapped high MMIO after SCR.DMAP=0. Future normal-mode readback should show `ICEMCR=0008`, `ICEMSR=0000` after the two writes (assuming no external ICE events).
- Do not default register space to generic read/write zero; this is a **two-register, source-backed decode only**, not a substitute for real bus effects. No 2nd emulator, no fake guest UI.

## One closed coding increment for Codex

**Coding ONLY** in the existing `main` `src/mame/skeleton/alphasdana.cpp`. Implement the coherent ICE setup pair **ICEMCR + ICEMSR** together, with documented values/masks, lane-accurate accesses, W1C status flags and guarded unsupported *active* ICE mode behavior. Reset state `0`, save state, map `0xFFFFFD0C–0xFFFFFD0F` individually without diverting existing MMIO; no refactor. The two adjacent setup instructions from original firmware form one logical ICE hardware initialization and can be implemented as one increment to avoid repetitive single-register gates. Do **not** invent breakpoint events/hard-map or enable hidden unconditional MMIO success. Preserve original PLLCR, SCR, WATCHDOG, ST81, double SD, LCD, EmuTOS, physical ROM byte coverage, only one DIAG.

Codex to publish source commit to `main` and local focused tests, then return one handoff for **GPT** to compile Clang21 and native UK1.5 `-rom` test on T, reporting first next real CPU/bus blocker; Codex does not do open-ended firmware research or independently change the emulator architecture. Keep sole installed `bin/dana-diag` previous SHA until genuine native qualification. If new guest execution wants a true ICE mode, return precise emulator guard and evidence for separate hardware research HERE. **Do not claim Palm OS boot from guest startup only.**

**Status: PLLCR full register path NATIVE PASS; first actual blocker ICEMCR word write; ICEMSR immediate next static known; Palm OS GUI NOT BOOTED.**
