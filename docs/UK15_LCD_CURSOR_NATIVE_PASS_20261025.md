# UK1.5 LCD cursor registers — Ghidra-derived, implemented and native-CPU PASS (2026-10-25)

## Scope and manufacturer documentation

**Closed native register blocker:** `0xFFFFFA18` LCXP (LCD cursor X position) and the adjacent cursor registers used in the *same original ROM function*: `0xFFFFFA1A` LCYP, `0xFFFFFA1C` LCWCH, `0xFFFFFA1F` LBLKC. These are part of the existing MC68VZ328 LCD controller, not a new peripheral.

Primary source: Motorola/Freescale [MC68VZ328UM](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf) §8.3.5–8.3.8 (PDF pages 139–142, manual pages 8-12–8-15). Fields and resets:
- LCXP R/W word reset 0000, defined bits `C3FF`: CC[15:14] modes + X position [9:0], reserved [13:10] read zero.
- LCYP R/W word reset 0000, defined bits `01FF`: Y position [8:0].
- LCWCH R/W word reset 0101, defined bits `1F1F`: width [12:8] and height [4:0], zero size disables cursor.
- LBLKC R/W odd/even 8-bit byte at `FFFFFA1F` reset 7F: bit7 blink enable, [6:0] divisor. No fabricated LCD cursor blink timer or visual overlay is claimed.

Ghidra 12.1.3 original UK1.5 ROM instructions (source private 64KiB boot slice, 68000 BE at `0x10000000`):
```asm
10005B7A MOVE.W ($FFFFFA18).W,D0
10005B7E ANDI.W #$C000,D0
10005B82 OR.W (A1),D0
10005B84 MOVE.W D0,($FFFFFA18).W
10005B88 MOVE.W ($0002,A1),($FFFFFA1A).W
10005BA4 MOVE.W D1,($FFFFFA1C).W
10005BC0 MOVE.B D0,($FFFFFA1F).W
10005C02 MOVE.W ($FFFFFA18).W,D0
10005C0A MOVE.W D0,($FFFFFA18).W
```
Full protected Ghidra listing on T: `work/uk15_qualify_20261025/ghidra_uk15_lcdcursor_audit.txt`. Image `UK15_private.raw` SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, unchanged; no ROM bytes published.

## Single production controller / code / tests

- Source file `src/mame/skeleton/alphasdana.cpp` on existing `main`, code commits `78f08458415fa9a4990c9646a90928da3684ba35`, `013d2c5fa2d22c56b69fee8c7c03d52d684618db` (no branches/worktrees).
- Added LCXP/LCYP/LCWCH register state, exact reset and defined-bit masks, real 68000 word and high/low byte write preservation, save-state, both normal R-direct and physical-mode MMIO mappings; 8-bit LBLKC reuses the existing LCD byte handler macro with correct odd/low `umask16(0x00ff)`.
- Existing DMA/screen path, RAM/FLASH/USB/other MMIO untouched. This implements and validates **register semantics**, not pixel cursor drawing, frame-paced blink modulation or Palm UI rendering.
- Source SHA256 **`5e982803d41cec450b0c24790e12aa888fde865cce699c6de6933ffadd0eb46b`**, verified on T after syncing pinned source.
- Regression commit `451211c8db75c0de87d081f4d4f5d83860f5c578`, `tests/lcd_cursor_uk15_test.py`: actual source-extracted C++20 handlers, manufacturer-defined reset, reserved bits, word/high/low lanes, R-direct and physical-mode address mappings, state save registration. **1/1 PASS** on T.
- Incremental **Clang21 full MAME build/link PASS**, return code 0, 18.7 sec.
- Staged `source/danadiagd` SHA256 **`acf3bf9ec8e1c8e31a215de8889e0c47acfad6eed25846d169bc4251ee6e6877`**.
- Installed `bin/dana-diag` SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`** unchanged before and after both tests.
- Sole T DIAG remains `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`. No Codex or installation.

## Native CPU proof, not only absence of a fault

Reused original authentic UK1.5 ROM in `-rom` physical mode, no CPU patch/quickload. First 240-frame bounded general observer: no `MMIO_READ_UNIMPLEMENTED` or other `DANA_PHYSICAL_BLOCKED`; that absence alone is **not** the PASS criterion.

Ran a **second passive focused MAME read/write tap**, limited to cursor `FFFFFA18–FFFFFA1F`, reset vectors and selected CPU frame snapshots. Both runs reused **same compiled candidate without recompilation**. T logs:
`work/uk15_qualify_20261025/lcd_cursor_ghidra_20261025/{directed_test.log,build.log,native.err,trace.txt,observer_cursor.run.lua,native_cursor.err,native_cursor_taps.txt}`.

Actual 68000 read/write tap, corroborating Ghidra and CPU continuation:

```text
LCD_READ  a=fffffa18 d=00000000 m=0000ffff curpc=10005b7a pc=10005b7e
LCD_WRITE a=fffffa18 d=00000000 m=0000ffff curpc=10005b84 pc=10005b88
LCD_WRITE a=fffffa1a d=00000000 m=0000ffff curpc=10005b88 pc=10005b8e
LCD_WRITE a=fffffa1c d=00000404 m=0000ffff curpc=10005ba4 pc=10005ba8
LCD_WRITE a=fffffa1e d=0000bfbf m=000000ff curpc=10005bc0 pc=10005bc4
LCD_READ  a=fffffa18 d=00000000 m=0000ffff curpc=10005c02 pc=10005c06
LCD_WRITE a=fffffa18 d=00000000 m=0000ffff curpc=10005c0a pc=10005c0e
```
`fffffa1e` is the **bus word base** for the write to physical **odd address `FFFFFA1F`**, mask `00FF`; no phantom `FFFFFA1E` register was implemented. Firmware executed an **additional cursor setup** at `CURPC=0x10078D42`, with repeats of LCXP/LCYP/LCWCH/LBLKC. MAME trace at frame 240:
```text
FRAME_240 ... curpc=1000cad6 pc=10017eb6 sp=0000393e sr=00002700
```
This establishes that authentic CPU progressed past the previously fatal first cursor read and executed subsequent firmware; it does **not** imply successful full Palm OS GUI, visual cursor overlay, accurate LCD DMA for Palm OS, or complete boot.

## Status

**LCXP / LCYP / LCWCH / LBLKC CPU-side MMIO behavior: native PASS for observed ROM usage, registered and validated.** The original ROM continues running through 240 frames without another fail-closed MMIO block in this bounded test. Cursor **pixel rendering** and **blink cadence** are not implemented/validated; Palm OS graphic UI is **NOT independently proven**. Do not invent a 'next blocker' in absence of CPU halt. To progress the actual emulator, observe graphical state/display DMA and boot lifecycle from real guest state rather than another speculative MMIO patch.
