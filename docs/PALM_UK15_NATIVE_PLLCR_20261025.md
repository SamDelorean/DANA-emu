# DANA UK1.5 real native cold boot: WATCHDOG PASS, PLLCR 16-bit read is next blocker (2026-10-25)

**Work ownership:** Research, analysis and native qualification by this ChatGPT conversation; **Codex implements only closed code tasks.** Not a Palm OS GUI boot. **No commercial firmware bytes stored in GitHub.**

## Source and build attestation

- GitHub `main@8b184b063a5b3d1688e5096e9cedcbc5538ab498`, WATCHDOG implementation published by Codex. Existing driver blob `2594e4cd9217c9ceaef0f83c76603ab93daf7992`, SHA256 `3bd7383160278ea67b00f2f827670d2dcca82704a2bdbe6aa32d844ea3643730` — **exactly matched before build**; compared against previous T source `ac32db33a52abe8c81479fef2605ecc52ee9e62ec1477a2131a63cc55e3b72ec`. Seven focused source hunks: watchdog state, saved state, reset/guard timer, handler and explicit physical MMIO at `0xFFFFFB0A`. No other source change detected in this patch review.
- T device: `spc-HP-t640-Thin-Client`, existing **sole** MAME DIAG `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`. MAME source `source/src/mame/skeleton/alphasdana.cpp`. Original qualified installed **`bin/dana-diag` unchanged**, SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
- Owner-supplied UK1.5 vendor `Flas` raw `0x5D0000` = 6,094,848 B, hash `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. Small ROM at byte 0; Big ROM at 0x8000. No synthetic SSP/PC, padding, mixed US ROM, fabricated NOR content, or write to original firmware.
- Exact incremental build cmd inside existing `source`: `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21`. **Clang 21.1.8 compiler, archive, link PASS**.
- New staged candidate (NOT installed) `source/danadiagd` SHA256 `d6285e2947f2cba0c452bc00ba34d276020d26504c155b8d7b91db202b1bbf5c`.
- Native MAME CLI executed on candidate: `danadiagd asmdana -rom <private_original_UK15.raw> -video none -sound none -nothrottle -skip_gameinfo -nowriteconfig -autoboot_script <private_observer.run.lua> -autoboot_delay 0 -log -oslog`. Runs 240 bounded frames and exits **rc=0** by observer, **NOT a boot success**.
- Private run evidence only on T: `diag/work/uk15_qualify_20261025/watchdog_20261025_123933/{build.log,native.err,trace.txt}`.

## Authentic guest CPU observed

```text
DANA_PHYSICAL_IMAGE bytes=6094848 ... read_only=1 topology=linear_array_unqualified
DANA_PHYSICAL_COVERAGE classification=UPDATER_DERIVED_RESET_EXPERIMENT supplied=00000000-005cffff unknown_tail=BLOCKED reset_decode_window=01000000 geometry=UNQUALIFIED
DANA_PHYSICAL_RESET vectors=firmware CSA=00b0 CSCTRL2=1000 CSCTRL3=9c00
DANA_PHYSICAL_VECTOR_READ address=00000000 data=0000 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000002 data=0316 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000004 data=1000 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000006 data=02a2 mask=ffff
DANA_PHYSICAL_UNIMPLEMENTED_MMIO read address=fffff200 mask=ffff
DANA_PHYSICAL_BLOCKED reason=MMIO_READ_UNIMPLEMENTED address=fffff200 data=0000 pc=1000515c
DANA_PHYSICAL_CPU curpc=10005158 ir=0268 sp=00000316 usp=00000000 sr=2704 a4=10000338
```

**Native memory-tap proves first two nonvector CPU writes in sequence:**
- `CURPC=1000514c`: high-byte WRITE to `0xFFFFF000`, mask `FF00`, accepted SCR, previous correction PASS.
- `CURPC=10005152`: full-word WRITE `0x0000` to `0xFFFFFB0A`, mask `FFFF`, accepted WATCHDOG-disable operation, **Codex WATCHDOG implementation native PASS for this path**.
- `CURPC=10005158`: `ANDI.W #$FFEF,($0200,A0)` with A0 `0xFFFFF000`; CPU first attempts 16-bit **READ** from `0xFFFFF200`. Driver's generic unmapped physical MMIO reader rejects. **THIS IS THE NEW FIRST NATIVE BLOCKER**, not `WATCHDOG_ENABLED_CLOCK_UNIMPLEMENTED`.
- `pc=1000515c` is prefetch/exception-observer PC, not beginning of offending instruction. `ir=0268` is current next/opcode context; do not confuse it with the logged memory transaction.
- **No evidence of Palm UI framebuffer yet.** MAME rc=0 was test observer exit, not Palm OS boot.

## Research for exact register behavior: Motorola MC68VZ328UM §4.4.1, Table 4-2

Primary official manual: https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf , pp. 4-8 to 4-9 (PDF zero-index pages 75–76); secondary Linux MC68VZ328.h `PLLCR_ADDR=0xFFFFF200`, `PLLCR_CLKEN=0x0010`, `PLLCR_DISPLL=0x0008`: https://codebrowser.dev/linux/linux/arch/m68k/include/asm/MC68VZ328.h.html .

- `PLLCR` is a **16-bit read/write register** at `0xFFFFF200`; reset value **`0x24B3`**.
- Bits 13–11 LCDCLKSEL, 10–8 SYSCLKSEL, 7 PRESC1, 5 PRESC2; bit 4 **CLKEN**, `1` = clock output CLKO disabled, `0` = CLKO enabled (provided PFSEL bit2 selects its function). Bit 3 **DISPLL**, `1` = disable PLL and enter sleep, `0` = PLL enabled. Bits 1–0 WKSEL set wake-up delay. Reserved bits 15–14, 6 and 2 should be zero.
- The *observed next instruction* `ANDI.W #$FFEF,(PLLCR)` clears **CLKEN bit 4**, NOT DISPLL bit 3. With documented reset value `0x24B3`, result is **`0x24A3`**. Thus this initial firmware step is **enabling the CLKO pin output** (subject to PFSEL), **not putting the CPU to sleep and not retuning the PLL frequency**. Mask `0xFFEF` changes no other PLL fields.
- The MAME driver already models `PLLFSR @ FFFFF202` separately with reset `0x0347`; do not confuse it with `PLLCR`. Clock generator/prescaler behavior must not be fabricated in order to pass this one recorded bit-4 change. If future firmware writes divider bits or DISPLL, their hardware effects require specific documented modelling/guarded errors.
- After PLLCR, **static ORIGINAL firmware disassembly only** (not executed this run) indicates ICEMCR `FFFFFD0C` and ICEMSR `FFFFFD0E` writes, then IVR and IMR, already separately implemented. Do not claim these were native-failed today.

## NEXT ONE CLOSED CODE INCREMENT FOR CODEX

**Research here completed for the observed PLLCR issue; Codex code only.** In the single main DIAG, implement the true VZ **16-bit PLLCR register `0xFFFFF200`** with reset `0x24B3`, real readable/writable bit fields and correct M68000 word lane semantics, persist via `save_item`, mapped in the physical high MMIO. For the exact native change (bit4 `CLKEN:1->0`), preserve/observe true state. Keep existing PLLFSR `0xFFFFF202` separate and unchanged, as well as accepted SCR/WATCHDOG, physical ROM coverage and all keyboard/SD/LCD/EmuTOS handlers. Fail/guard if a future firmware transaction would require unmodeled true PLL frequency or sleep behavior; do not silently fake those modes, set guessed clock rates, paint UI or inject guest PC. After focused code/static verification, incremental Clang21 build and UK1.5 native `-rom` test on staged `source/danadiagd` must pass `CURPC=0x10005158` and return the **next actual** CPU blocker. Keep installed `bin/dana-diag` SHA untouched unless full qualified Palm UI boot is proven. No extra DIAG, isolated branch, synthetic guest or new source research. Report hashes, guest PC/SR/SSP, decoder/transaction and actual next blocker back to *this* research chat. Preserve original commercial files private.

**Acceptance now:** WATCHDOG native PASS, PLLCR read FAILED due absent MMIO implementation; GUI Palm OS not yet booted. Next coding task is PLLCR, no other peripheral assumptions.
