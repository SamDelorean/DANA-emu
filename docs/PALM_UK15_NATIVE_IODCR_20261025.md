# Palm OS UK1.5 cold-reset native — ICE pair PASS, IODCR 16-bit write is first real blocker

**Evidence recorded 2026-10-25.** This chat performed hardware research and authentic UK1.5 execution on T. Codex performs CODING ONLY from this closed contract. Authentic 68k Small ROM CPU reset continues but **Palm OS graphical UI HAS NOT BOOTED**. This is a native `UPDATER_DERIVED_RESET_EXPERIMENT`; NOR chip electrical geometry and unknown image tail are not yet qualified. Commercial firmware bytes are never committed.

## Reproducible tested state

- CodeX-published ICE commit: `main@4ab1bd07ed307a2f44ef2fe1acd5116ffe279110`, edited `src/mame/skeleton/alphasdana.cpp`. Exact Git blob `fb53f6c5a6af68a7e164a2741a1090ce8f06a64f`; **driver SHA256 `1275509bbe091e23fd67d3a42d00cce0b332c662ef66224edcbbc024bce8e0e2`**, checked on T. Previous source SHA256 `207bf697be4ddafc90ab4b36103d15963f7871b22a1c72ba1dd3cf1a0dceaea1` verified before patch; six additive ICE-related source hunks, no unrelated driver changes.
- SOLE T project: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`, `source/src/mame/skeleton/alphasdana.cpp`. Clang 21.1.8 incremental MAME build/link **PASS**:
  `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21`.
- Staged candidate `source/danadiagd` SHA256 **`ea3644db575bbf0d41fc53cadf5b9df25e7f9174c07446bfb635f0a6281329e2`**; **NOT INSTALLED**. Sole qualified installed `bin/dana-diag` **UNCHANGED**, SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`**.
- Original privately extracted vendor UK 1.5 `Flas` raw byte stream: `0x5d0000`=6,094,848 bytes, SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`; actual authentic SmallROM starts at file offset zero. No padding, rewriting or `-quickload`.
- Native MAME invocation: `source/danadiagd asmdana -rom <verified private UK15.raw> -video none -sound none -nothrottle -skip_gameinfo -nowriteconfig -autoboot_script <private observer.run.lua> -autoboot_delay 0 -log -oslog`. The script terminates after bounded frame collection; **MAME process return code 0 is NOT a Palm OS boot PASS**.
- Private T traces under `diag/work/uk15_qualify_20261025/ice_20261025_132911/{build.log,native.err,trace.txt}`. No private ROM bytes uploaded or published.

## Authentic guest CPU evidence

```text
DANA_PHYSICAL_IMAGE bytes=6094848 ... read_only=1 topology=linear_array_unqualified
DANA_PHYSICAL_COVERAGE classification=UPDATER_DERIVED_RESET_EXPERIMENT supplied=00000000-005cffff unknown_tail=BLOCKED reset_decode_window=01000000 geometry=UNQUALIFIED
DANA_PHYSICAL_RESET vectors=firmware CSA=00b0 CSCTRL2=1000 CSCTRL3=9c00
DANA_PHYSICAL_VECTOR_READ address=00000000 data=0000 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000002 data=0316 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000004 data=1000 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000006 data=02a2 mask=ffff
DANA_PLLCR value=24a3 clko_enabled=0 pfsel=87 clock_tree_unchanged=1
DANA_ICE ICEMCR data=0008 mask=ffff value=0008 normal_mode=1
DANA_ICE ICEMSR data=0007 mask=ffff value=0000 normal_mode=1
DANA_PHYSICAL_UNIMPLEMENTED_MMIO write address=fffff008 mask=ffff
DANA_PHYSICAL_BLOCKED reason=MMIO_WRITE_UNIMPLEMENTED address=fffff008 data=0000 pc=10005182
DANA_PHYSICAL_CPU curpc=1000517c ir=117c sp=00000316 usp=00000000 sr=2704 a4=10000338
```

Additional Lua real guest bus sequence (masks shown, private data omitted except documented value):
1. `CURPC=1000514C` SCR byte @ `FFFFF000`, mask `FF00` — PASS.
2. `CURPC=10005152` WATCHDOG word `0000` @ `FFFFFB0A` — PASS.
3. `CURPC=10005158` PLLCR word RMW result `24A3` @ `FFFFF200` — PASS.
4. `CURPC=1000515E` ICEMCR `0008` @ `FFFFFD0C` — **NATIVE PASS**.
5. `CURPC=10005164` ICEMSR `0007` @ `FFFFFD0E` — **NATIVE PASS**, returns clean status `0000`.
6. `CURPC=1000516A` IVR byte @ `FFFFF300`; `CURPC=10005170` IMR word @ `FFFFF304`; `CURPC=10005176` IMR word @ `FFFFF306` — existing handlers accepted native writes.
7. **FIRST NEW TRUE BLOCK**: **`CURPC=0x1000517C`**, guest **16-bit WRITE `0x0000`, mask `0xFFFF`, address `0xFFFFF008`**. `pc=0x10005182` is prefetched NEXT PC, not failing instruction address. `IR=0x117C` is the prefetched next instruction's context, not evidence of a write-size mismatch. This record does not assert a fully disassembled mnemonic at `CURPC=1000517C` because only bus+register tracing, not fresh independent binutils disassembly, was executed in this intervention.

## Primary manufacturer research, exact hardware interpretation

**Motorola MC68VZ328 Integrated Processor User's Manual** (Rev 0 02/2000), **section 5.2.4**, **Table 5-4**, and programmer's memory map **Table 3-1**:
https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf

- **IODCR** — **I/O Drive Control Register**, **16-bit read/write** at **`0xFFFFF008–0xFFFFF009`**; **hardware reset `0x1FFF`**.
- Defined field mask **`0x1FFF`**; bits **15–13 reserved**, should read as zero and not store illegal one values.
- Bit **12 AB** = address bus drive strength (with A[23:20] controlled by PF group); bit **11 DB** = upper data bus strength (lower bus from PA group); bit **10 CB** = bus-control signal strength; bits **9..0** = port-group drive strength PM, PK, PJ, PG, PF, PE, PD, PC, PB, PA.
- For every defined control bit, **0 means 2 mA drive**, **1 means 4 mA drive**. At cold reset all defined bits=1, thus 4 mA. The authentic firmware's **`MOVE-like word write 0x0000` selects the 2 mA low-drive option across all defined groups**, consistent with Motorola's documented power-saving recommendation.
- Drive-current strength is an **electrical pad property**; a word write of `0x0000` does **not** change internal GPIO DATA/DIR/SEL, address selection, RAM/Flash content, CPU registers, or logic-level pin assignments. In current functional MAME emulator mode, storing correctly and returning readable field state is sufficient for this observed power-saving operation; **do not claim physical electrical current simulation**. If later code needs analog pad-current or timing impact, qualify separately.
- **Current source gap:** current driver's physical program map has SCR at `FFFFF000` and ID register at `FFFFF004`, **but no IODCR `FFFFF008` decoder**. It therefore correctly blocks unknown MMIO. Implement the source-backed explicit IODCR decoder only; do not blindly map whole 4 KiB system register page as writeable RAM.

Relevant indexed source at lines 2995–3037 in the official PDF https://docs.rs-online.com/6394/0900766b801cf944.pdf ; same primary NXP PDF. The web screenshot renderer intermittently returned cache-miss; text extraction from the official manual and corroborating HTML mirrors confirmed the register/fields. This is primary-source-backed, not guessing based on the hexadecimal address.

## CLOSED CODING TASK for Codex ONLY

One limited hardware increment in `main` and the **single** `src/mame/skeleton/alphasdana.cpp`:
- Declare **`m_iodcr` as a 16-bit state**, **reset `0x1FFF`** in the physical/reset lifecycle consistent with known-good behavior, save with MAME save-state.
- Map exactly `0xFFFFF008–0xFFFFF009` in **existing physical high MMIO view** using correct 68k big-endian word and byte lanes / `mem_mask`. Read back defined bits; WRITE selected lanes only and mask undefined bits 15–13 to zero. The observed native word `0x0000` must produce readback `0x0000`.
- Treat IODCR as **pad drive-strength configuration only**; do NOT alter `m_gpio` state, `PFSEL`, logical bus, PLL clocks, RAM, CS decoding or keyboard handling. No fabricated analog current/pin voltage behavior.
- Keep SCR, WATCHDOG, PLLCR, ICE registers, ST 81-key keyboard, SD, LCD, EmuTOS, and user Flash authenticity/unknown-tail protection intact. Minimal focused local tests on reset/read/write, high/low bytes, reserved masks; exact sourced behavior not a generic 4-KiB MMIO RAM overlay.
- Codex publishes implementation and test summary to **existing `main`**, without branch/clone/worktree/new emulator; **this ChatGPT chat** owns *next* Clang21 T build, UK1.5 `-rom` native qualification and first next true CPU block research. Do not preimplement any later register from hypothesized 68k flow. Keep only installed DIAG intact until proven genuine full Palm OS UI.
- Return code SHAs and change summary only, not a new general plan. **This document does not itself authorize any future Remote Commander T invocation.**

**Current status**: published ICE pair native PASS (ICEMCR=0008, ICEMSR W1C=0007 yielding 0000), IVR/IMR accepted; **IODCR `0xFFFFF008` first real blocker**, PALM OS UI **NOT BOOTED**.
