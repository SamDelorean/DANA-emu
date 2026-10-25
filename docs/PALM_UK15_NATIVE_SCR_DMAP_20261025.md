# UK1.5 ORIGINAL Small-ROM cold reset: native PASS until SCR.DMAP, then one proven hardware emulator bug

**Date 2026-10-25. Evidence from the SINGLE existing DIAG on T.** This file is research and a **closed, one-function implementation contract** for Codex. Actual firmware reverse engineering is done in this chat, not Codex. **Real Palm UI NOT BOOTED.** No commercial ROM bytes included here.

## Native execution and verified input

- Source provenance `AlphaSmart_Dana1_5_Flash.zip` original SHA256 `1a0256e35c11c7455a58738f05218e1e290b8d381a5742467f1a512ac25c14fc` found locally on T at `/home/spc/Projects/Dana-OS3K/firmware/research-only/AlphaSmart_Dana1_5_Flash.zip`.
- Private UK1.5 `ROMUpdater_enUK150R1.prc` reconstructed from **120/120 resource checksums PASS**, exact 0x5D0000 (6,094,848 bytes), SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. No padding, bytes modified, US mixing or ROM uploading.
- Main GitHub at `07443b2cd39171e0a6eedafd4fe1f1106fecccf8` already contained strict coverage patch: source file blob `225b718525beb489c4e9715b241410330b8c75d4`, SHA256 `9b0e03909c21717758f9f75a31540b28f5943b377b2a0f000f7788b18885783e`. The exact old T source blob `f3c201c8116f5a6214a3f0fbb3625e635f5cad7a`, SHA256 `beb460df6e04013d1bc24c542b89276a088cf06fc0e96e52fedd566c57cc7eda`, was matched before replacing **just the driver in the existing MAME source tree**. A private rollback copy was made. No new emulator or branch.
- Clang21 incremental `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21` completed with **zero reported errors**.
- Tested **candidate executable** `source/danadiagd` SHA256 `a335583ebb7cc1f29fd7b8d6f5f22f1ddfb72a2e964b668db40ebbd4e09b5984` directly with `asmdana -rom <private_UK15_stream> -video none -sound none -nothrottle -skip_gameinfo -nowriteconfig -autoboot_script <private_observer> -autoboot_delay 0 -log -oslog`, no `-quickload`.
- Previous installed sole `bin/dana-diag` untouched SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`. Use this as rollback baseline; experimental Clang candidate was NOT installed.
- Native machine exits code 0 after bounded observer frames, **which DOES NOT constitute Palm OS boot PASS**. CPU suspended at first blocker.
- Original native diagnostic receipt, with *no ROM bytes*, in [docs/PALM_UK15_NATIVE_20261025.json](PALM_UK15_NATIVE_20261025.json).

## Real physical reset vector sequence: observed M68000 bus reads

```text
DANA_PHYSICAL_IMAGE bytes=6094848 ... read_only=1
DANA_PHYSICAL_COVERAGE classification=UPDATER_DERIVED_RESET_EXPERIMENT supplied=00000000-005cffff unknown_tail=BLOCKED
DANA_PHYSICAL_RESET vectors=firmware CSA=00b0 CSCTRL2=1000 CSCTRL3=9c00
DANA_PHYSICAL_VECTOR_READ address=00000000 data=0000
DANA_PHYSICAL_VECTOR_READ address=00000002 data=0316
DANA_PHYSICAL_VECTOR_READ address=00000004 data=1000
DANA_PHYSICAL_VECTOR_READ address=00000006 data=02a2
```

The actual MC68VZ328 M68000 CPU read authentic UK vendor-image reset words (SSP `0x00000316`, PC `0x100002A2`), executed genuine Small ROM code and made it as far as the SCR initialization (more than 0x5000 bytes into image). This proves a legitimate guest CPU cold-reset *execution path* on current geometry hypothesis, not full physical Flash chip identification/boot and not Palm UI.

## First actual blocker and correct instruction decode

```text
DANA_PHYSICAL_BLOCKED reason=SCR_DMAP_MODE address=fffff000 data=00f0 pc=10005152
DANA_PHYSICAL_CPU curpc=1000514c ir=317c sp=00000316 usp=00000000 sr=2708 a4=10000338
DANA_PHYSICAL_DECODE csa=00b0 csd=0200 csgba=0000 csgbd=0000 ... dram=0000/0000/003c/0000
```

External MAME Lua bus tap independently observed a **high-byte write** (`mask=0xFF00`) at `0xFFFFF000`; `CURPC=0x1000514C` is the offending instruction, while `PC=0x10005152` points to the prefetched instruction and `IR=0x317C` belongs to the NEXT instruction. Private byte-level inspection of verified exact UK1.5 payload performed in this chat identifies original `0x1000514C` instruction as **`MOVE.B #$F0,($0000,A0)`**, where preceding 68k instruction loads A0 with `0xFFFFF000`. No original instruction bytes are copied here.

## CAUSAL BUG PROVEN: SCR.DMAP=0 is LEGAL and maintains high-address internal MMIO

**Motorola primary source:** MC68VZ328 Integrated Processor User's Manual **Chapter 5**, §5.1 and §5.2.1, Table 5-1:
- https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf
- Readable online mirror https://manuals.plus/m/ccba474a33eae996f589fa6a2231021961e611fa72c03ded917add1abc9361d5

`SCR` reset `0x1C`. Bit 2 `DMAP`: **1** = high `0xFFFFF000–0xFFFFFFFF` + extra 24-bit mirrored aliases `0xXXFFF000–0xXXFFFFFF`; **0** = **ONLY** high `0xFFFFF000–0xFFFFFFFF` remains mapped. Therefore setting DMAP=0 does **not** switch to nonexistent low MMIO registers, does **not** disable high hardware register addresses, and does **not** require remapping the canonical high decoder. This firmware explicitly writes `0xF0` to SCR: bits 7..5 are write-one-to-clear status flags (BETO, WPV, PRV), `BETEN=1`, `SO=0`, `DMAP=0`, `WDTH8=0`. Valid resulting `SCR=0x10` from clean reset.

**Current source bug in `src/mame/skeleton/alphasdana.cpp`:**
```cpp
void alphasdana_state::scr_w(u8 data)
{
    // DMAP=1 is the existing high internal-register decoder. Do not invent a
    // second low-register page when a firmware requests an unsupported mode.
    m_scr=(m_scr & 0xe0 & ~data) | (data & 0x1f);
    if (!(m_scr & 4)) physical_block("SCR_DMAP_MODE",0xfffff000,data);
}
```
The first assignment already reflects the documented write-one-to-clear flags and control bits (for this write); **the second conditional is incorrect and halts a legal hardware operation**. The high register decoder is already present. It should remain available with DMAP=0. The 24-bit aliases that would exist when DMAP=1 are a separate possible future completeness issue, not required to handle this *current* high-address access. Do not synthesize a "low register page" or special-case Palm OS.

## Immediate next instructions identified in authentic UK image (STATIC predictions, NOT native measurements)

Verified original byte sequence beginning at guest `0x10005152` (privately inspected, do not commit raw bytes):
1. `MOVE.W #$0000,($0B0A,A0)` with A0 still `0xFFFFF000`: writes `0xFFFFFB0A` **WATCHDOG** register, documented by MC68VZ328 headers. The present program map has no explicit Watchdog handler. **Expected probable next native blocker**, but do not assert it occurred yet.
2. `ANDI.W #$FFEF,($0200,A0)`: RMW of `0xFFFFF200` **PLLCR**, also absent from explicit physical register map. Again prediction only until native execution. Correct clock behavior requires source-backed implementation; do not fake write-only latch as calibrated PLL.

Reference https://codebrowser.dev/linux/linux/arch/m68k/include/asm/MC68VZ328.h.html (WATCHDOG at `0xFFFFFB0A`, PLLCR at `0xFFFFF200`).

## CLOSED ONE-FUNCTION CODE TASK FOR CODEX (research stays in ChatGPT)

**In the sole canonical `main` DIAG driver**, make a minimal, causal implementation:
- Change **only `alphasdana_state::scr_w(u8)`** to stop treating `DMAP=0` as fatal while **preserving W1C status semantics** and the real high-address MMIO decode. Correct the obsolete false comment, preserve reset SCR=0x1C and save state.
- Preserve all existing RAM/Flash coverage, physical reset, CPU execution, keyboard, SD, LCD/EmuTOS and the installed old binary.
- Run focused static test, compile the **same** DIAG with existing Clang21 cache, and retry **UK1.5 authentic vendor-image physical -rom reset** on a private copy; no mix with US, no padding or synthetic vectors.
- Return CPU PC/CURPC/IR/SSP/SR and **the actual next native bus blocker** (WATCHDOG may be first; do not pre-implement until observed or separately explicitly authorized). Mark guest UI NOT BOOTED unless it genuinely appears. Do not promote candidate to operating installed binary just because it progresses.
- No new tree, branch, clone, generic test campaign, Ghidra research or false PASS. This is **codifying a closed finding only**.

**ChatGPT Commander allowance for this intervention was 5/5 calls and is exhausted.** Do not make further T calls in THIS chat under the same authorization; Codex requires independent explicit machine approval if used.

**CURRENT: physical Small ROM RESET VECTOR + CODE EXECUTION PASS; SCR emulator bug conclusively diagnosed; Palm OS UI NOT BOOTED.**
