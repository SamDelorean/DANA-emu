# Original UK1.5 CSD ROP protected SDRAM — EUPEN/DUPS2 FIX NATIVE PASS (2026-10-25)

## Closed result

**The user-requested protected stack write problem is resolved and directly verified with authentic original UK1.5 native 68000 execution, not a mock boot or bypass.** CSD retains ROP=1; only the manufacturer's unprotected low bank window remains writable. Original firmware advanced past `0x0007EC96` to a separate, newly Ghidra-identified power-control register write. **Palm OS GUI still NOT BOOTED.**

Sole T DIAG location (existing): `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`. No branches, worktrees, additional MAME tree or installed-binary changes.

### Original evidence from Ghidra and native CPU

- Ghidra 12.1.3, original private UK1.5 68000 big-endian flash, original ROM SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, unchanged, updater-derived and incomplete NOR geometry (no proprietary bytes published).
- Original routine at `1007A100`: **`ORI.W #$2000,($FFFFF116).W`**, followed by `RTS`; this intentionally sets CSD.ROP. Native CSD write tap records `CSD=2283` at `CURPC=1007A100`.
- Original startup chip selects: `CSD=2283`, `CSCTRL1=4150`, CSD group base 0, 16 MiB DRAM window. Previous error: `EXTERNAL_WRITE_OR_PROTECTION` writing authentic trap stack at `0x0007EC96`, word `0xECBA`, `CURPC=0x1008ECB8` (M68000 TRAP #15 prefetch bus).
- Motorola **MC68VZ328UM** §6.3.5, Table 6-12, Example 6-1:
  `EUPEN=CSCTRL1.bit14 (0x4000)`; `DUPS2=CSCTRL1.bit4 (0x0010)`; `DSIZ3=CSCTRL1.bit6 (0x0040)`; CSD.UPSIZ bits12–11. If EUPEN=1, `UPSIZ_effective=UPSIZ[1:0] | DUPS2<<2` and `unprotected = chip_select_size / 2^(7 - UPSIZ_effective)`. With DRAM SIZ=1, DSIZ3=1, chip-select size=16MiB; EUPEN=1, DUPS2=1, UPSIZ=100b=4 -> **2MiB** unprotected. Genuine trap stack address `0x0007EC96` lies in this unprotected range; its write MUST be accepted while ROP remains set for higher addresses.
  If EUPEN=0, the documented legacy unprotected size is **32, 64, 128 or 256 KiB**, selected only by the low two UPSIZ bits, independent of bank size. Prior static formula used extended sizing for both modes and was corrected.
- Manufacturer manual: https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf. PDF screenshot of Figure 6-1 and Example 6-1 cross-checked; the region is unprotected at the **start** of the selected bank.
- Independent **Palm OS reference emulator** CloudpilotEmu (derived from POSE): `src/cloudpilot/emulator/hardware/EmRegsVZ.cpp`, `EmRegsVZ::GetDynamicHeapSize()` implements the same two-mode `EUPEN/DUPS2/DSIZ3/UPSIZ` computation, code at https://github.com/cloudpilot-emu/cloudpilot-emu/blob/master/src/cloudpilot/emulator/hardware/EmRegsVZ.cpp (lines circa 1263–1303). Linux `MC68VZ328.h` independently corroborates mask values `UPSIZ=1800`, `DUPS2=0010`, `DSIZ3=0040`, `EUPEN=4000`, `ROP=2000`.
- EmuTOS is an Atari-compatible **guest operating system**, not a DragonBall VZ peripheral/chip-select emulator. Its past R-direct validation must not be used to invent UK1.5 physical bus behavior. This source inspection guided exclusion of irrelevant OS-side modifications.

## Production integration in existing main

- Controller: `src/mame/skeleton/alphasdana.cpp`, commits `12e775a7` first extended CSD implementation, `0e8d5bb3` manufacturer/Cloudpilot legacy EUPEN=0 parity. Final authoritative **source SHA256 `661f9c288f7cdb136e19344ea9c8261557f99000fc20165fe057071aa3a8d235`**.
- `cs_ram_unprotected_bytes(bank_size,csd,csctrl1)` implements both documented modes. `cs_ram_read_allowed` and `cs_ram_write_allowed` evaluate each **bank-relative physical address** against true unprotected size; RO remains bank-wide and ROP/SOP gate **only protected** addresses. DRAM init, RAM bank contents, LCD, USB and other peripherals are unchanged.
- Focused production C++20 tests `tests/csd_rop_read_protection_test.py`, commits `6a6541de` initial exact boundary test, `3e2c6db7` legacy parity. Static assertions cover UK1.5 `0x7EC96` < `0x200000`, exact `0x200000` boundary, protection above, RO, SOP supervisor, EUPEN-off legacy 32KiB case, DUPS2 gating, and 4MiB/UPSIZ manufacturer example. **1/1 PASS** on T.
- Existing regression `tests/csd_dsiz3_window_test.py` **1/1 PASS** for CSD DSIZ3 bank-size logic.
- Final T Clang21 incremental MAME build/link **PASS**, return code 0, 18.63 s.
- Staged test binary `source/danadiagd`: SHA256 **`c9f772636cb6dc528b790914cbdb1c110635367382b6e32a13c8f68ca85eacee`**.
- Sole installed `bin/dana-diag` SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`** unchanged. Original UK1.5 private ROM SHA256 unchanged. No installer replacement.
- Local logs (private T): `work/uk15_qualify_20261025/csd_upsiz_ghidra_20261025/`, including first and final `build.log`, `final_build.log`, `native.err`, `final_native.err`, `extended_metrics.txt`, `final_extended_metrics.txt`, actual tests, and `ghidra_post_rop.txt`.

## Real native advancement / first new blocker

Native original private UK1.5 `-rom` with the same read-only 1800-frame observer. Initial `palm POWERED` screen remains stable at 4,161 dark pixels frames 60..240, and the authentic CPU proceeded beyond the former `0007EC96` stack write. The **new first fail-closed operation** recorded in both the initial and final corrected candidates is:

```text
DANA_PHYSICAL_UNIMPLEMENTED_MMIO write address=fffff206 mask=00ff
DANA_PHYSICAL_BLOCKED reason=MMIO_WRITE_UNIMPLEMENTED address=fffff206 data=9f9f pc=1007d12e
DANA_PHYSICAL_CPU curpc=1007d12a ir=4e75 sp=0007e91c sr=2608
DANA_PHYSICAL_DECODE ... csd=2283 csctrl=4150/d000/9c00 ...
```

Here `0xFFFFF206` is the **16-bit word bus base** with **low/odd byte mask `00FF`**; the physical target is **PCTLR at `0xFFFFF207`** (8-bit Motorola VZ power control register, reset `1F`). Original ROM Ghidra 12.1.3 follow-up (T `ghidra_scripts/DanaUK15PowerAfterROP.java`, `csd_upsiz_ghidra_20261025/ghidra_post_rop.txt`) proves:
```asm
1007D11C MOVEA.L #$FFFFF000,A0
1007D122 MOVE.B ($00000252).W,D0
1007D126 ORI.B #$80,D0
1007D12A MOVE.B D0,($0207,A0) ; actual PCTLR 0xFFFFF207
1007D12E RTS
```
Thus ROM writes observed `9F` to PCTLR (sets PCEN bit7, WIDTH bits4..0 retained at 1F); this is the next physical power-control work, **not part of the CSD fix and not implemented**. Do not mistake CURPC at following instruction for different hardware. Power controller execution/burst gating needs manufacturer-confirmed modeling before acceptance; do not blindly emulate sleep clock or invert RAM protection.

**Status: CSD.ROP/UPSIZ genuine native fix PASS. Palm OS complete graphical desktop NOT BOOTED.** Ghidra, Motorola, independent Cloudpilot source and live MAME evidence mutually agree.
