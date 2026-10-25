# Palm OS UK1.5 native cold-reset — IODCR PASS; PCDIR next real blocker (2026-10-25)

## Evidence and scope

This is a REAL native guest-CPU test on the only authorized T DIAG, not a local constant test, Ghidra prediction, CPU patch, or Palm OS UI PASS. The ROM remains a privately held updater-derived `Flas` stream; NOR electrical geometry and unknown image tail remain UNQUALIFIED. No commercial ROM bytes have been committed.

- Codex IODCR implementation: `main@613fc465ac26107d04ec341df40de995cc00a40e`.
- Exact controller SHA256 on T: `5a627f2e97564a3452f0a70ec99e6023b8d34a14c6a8afabe289b1321644fab7`.
- Same already-built Clang21 candidate `source/danadiagd`: SHA256 `01a9d6eb817221537f03dc6041b5efae061c5af512d519f3a19427a77ccc2872`. **No recompile for this native test.**
- Sole installed operative `bin/dana-diag`: SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`, unchanged before and after native run.
- Private `UK15_private.raw`: size 6,094,848 B, SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, verified against existing same file (no scan over /home/spc, no copy or patch).
- One existing observer: `work/uk15_qualify_20261025/observer.run.lua` (read-only CPU; bounded 240 frames; writes trace by `DANA_PALM_TRACE`). Observer records guest bus writes and CPU state; it does not write guest CPU/registers.
- Logs: `work/uk15_qualify_20261025/iodcr_gpt_20261025/{native.err,native.out,trace.txt,error.log,build.log}`. No private ROM bytes exported.
- Mode: real cold-reset `-rom`, `asmdana`, headless, same observer, `DANA_PALM_TRACE=.../trace.txt`. MAME return code 0 is due to bounded observer, **not** Palm OS GUI boot success.

## Authentic guest execution

Original reset vectors read SSP=`00000316`, PC=`100002A2`. SCR, WATCHDOG, PLLCR and ICE previously validated continued to PASS; native ICE `ICEMCR 0008` and `ICEMSR 0007=>0000` accepted, IVR/IMR retained. **IODCR formerly first blocker is now passed**. Real M68000 bus tap observed:

```text
WRITE address=fffff008 data=00000000 mask=0000ffff pc=10005182 curpc=1000517c sp=00000316 usp=00000000 sr=00002704 ir=0000117c a4=10000338
```

No `MMIO_WRITE_UNIMPLEMENTED` at IODCR in new native log; CPU advanced beyond the preceding stopped instruction. An independent subsequent IODCR readback is NOT claimed; actual accepted write and CPU continuation are the observed PASS criterion.

**FIRST NEW REAL BLOCKER**:
```text
DANA_PHYSICAL_UNIMPLEMENTED_MMIO write address=fffff410 mask=ff00
DANA_PHYSICAL_BLOCKED reason=MMIO_WRITE_UNIMPLEMENTED address=fffff410 data=0000 pc=100051a6
DANA_PHYSICAL_CPU curpc=100051a0 ir=117c sp=00000316 usp=00000000 sr=2704 a4=10000338
```

Failing guest instruction's address `CURPC=0x100051A0`, not prefetched next `PC=0x100051A6`. Real access is high/even **8-bit** write of `0x00` to `0xFFFFF410`; MAME reports `mem_mask=0xFF00` and `data=0x0000`. This report does NOT invent a disassembled mnemonic. No later register/PC is asserted.

## Manufacturer-verified register semantics

Primary manufacturer source: **Motorola/Freescale MC68VZ328 Integrated Processor User's Manual** (MC68VZ328UM Rev.0 02/2000), Table 3-1; §10.4.3, particularly §10.4.3.1 and Table 10-12, manual printed p.10-12 / PDF page index 181:
https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf

- `PCDIR` = Port C Direction Register, **8-bit R/W**, physical `0xFFFFF410`, reset `0x00`. Bits 7..0 = respective Port C pin direction: `0` INPUT, `1` OUTPUT. Every bit is defined.
- If corresponding `PCSEL` selects a dedicated function, the `DIR` bit is ignored **for pin behavior**, not a prohibition on retaining direction register state.
- Port C is multiplexed with dedicated LCD outputs `LD0..LD3, LFLM, LLP, LCLK, LACD` (§10.4.3.3 / Table 10-14). No LCD timing, port input circuit, or external pin drive is evidenced by this `PCDIR=0` write alone.
- Existing `PCPDEN=0xFFFFF412` and `PCSEL=0xFFFFF413` and their individual u8 handlers are already in `alphasdana.cpp` (R-direct; existing physical reset sets both `0xFF`). Existing code expressly says `PCDIR/PCDATA` are not implemented. This new native failure is exactly `PCDIR`, not `PCDATA`.

## Closed CODEX coding contract — PCDIR only

On the existing `main`, in the **single** canonical `src/mame/skeleton/alphasdana.cpp`:
1. Add actual `u8 m_pcdir` state, **reset `0x00`** under the appropriate existing physical/reset lifecycle, and MAME save-state registration; retain native 8-bit semantics. Use an existing Port C-specific implementation pattern if appropriate. No fabricated external pad state.
2. Add a direct physical high-MMIO view decode **only at `0xFFFFF410`**, for real `PCDIR` read and write; preserve correct 68k even/high byte lane `FF00` for this real 8-bit access. Do not map the entire `0xFFFFF400` page, create generic register RAM, or silently accept other unknown addresses. Existing `PCPDEN`, `PCSEL`, and R-direct mode must remain unchanged.
3. `PCDIR` bit state is writable 0..FF and independently readable, but the `PCSEL`-qualified effects on actual LCD/GPIO pins are **not** proved or required by the observed write of zero. Do not alter LCD signals, SPI, SD, keyboard, clocks, or the approved IODCR/ICE/PLL/WATCHDOG logic.
4. Focused local test for reset, word-lane high/even 8-bit transaction, `0x00` native write/read, arbitrary 8-bit bits, reset reentry, save registration and unaffected nearby registers/maps. Full-driver C++20 syntax check. Do not rerun closed unrelated suites.
5. Publish small scoped code and test evidence directly to existing `main` (no branches, clones or worktrees). Codex **does not call T or Ghidra**. GPT owns one subsequent Clang21 native validation, identifying the first NEXT true guest-CPU blocker with exact `CURPC/PC/IR/SP/SR`, address/data/mask, hashes, logs. Do not preimplement `PCDATA` or downstream hypothetical operations.
6. Preserve `bin/dana-diag` operative and authentic private UK1.5 source. **Palm OS GUI still NOT BOOTED**. This file does not grant future remote authorization.

**New status:** IODCR **native PASS**; **PCDIR** at `FFFFF410` first observed block; next post-PCDIR CPU behavior UNKNOWN.
