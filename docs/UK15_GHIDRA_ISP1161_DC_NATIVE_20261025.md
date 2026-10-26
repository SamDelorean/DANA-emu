# UK1.5 ROM Ghidra 68000 audit — Philips ISP1161 DC resolved; LCD LCXP next (2026-10-25)

## Source authenticity / method

- **Original firmware:** private `UK15_private.raw` 6,094,848 B, SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. No ROM bytes added to GitHub.
- **Ghidra 12.1.3**, language `68000:BE:32:default`, same existing T Ghidra project `DanaUK15RelocatedTemp`; source segment from the verified private ROM at physical base `0x10000000`.
- Same `work/uk15_qualify_20261025/ghidra_scripts/` scripts: `DanaUK15ISP1161DCAudit.java` and `DanaUK15LCDCursorAudit.java`. Outputs: `ghidra_uk15_isp1161_dc_audit.txt`, `ghidra_uk15_lcdcursor_audit.txt`. Both actually executed under Ghidra, completed with no Ghidra script error. Java temp files in `/dev/shm/dana_ghidra_tmp` because of previously proven `EDQUOT` on `/tmp`.
- Native trace inspection is from **same existing single canonical T DIAG** `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`, not a separate branch, build environment or emulator.

## Actual ROM disassembly proves physical USB device-controller channel

Ghidra decoded `0x1000305A` as the entry of a routine using the following **absolute** M68000 16-bit device writes. Original semantics and Philips/NXP ISP1161 datasheet agree exactly; this is not an inferred unknown external peripheral:

```asm
1000305A  LINK.W A6,#0
1000305E  ORI.W #$0002,$FFFFF304
10003064  MOVE.W #$00B0,$1F000006 ; DC command (A1=1,A0=1): unlock
1000306C  MOVE.W #$AA37,$1F000004 ; DC data (A1=1,A0=0): exact unlock key
10003074  MOVE.W #$00BA,$1F000006 ; DC hardware configuration command
1000307C  MOVE.W #$0F04,$1F000004 ; observed hardware register value
10003084  MOVE.W #$00B8,$1F000006 ; DC mode command
1000308C  MOVE.W #$0020,$1F000004 ; GOSUSP=1
10003094  MOVE.W #$00B8,$1F000006 ; DC mode command again
1000309C  CLR.W  $1F000004       ; M68000 read-before-write, sets GOSUSP=0
```

The same Ghidra analysis found **23 literal occurrences** of each port `0x1F000004` and `0x1F000006` within the private 64 KiB boot slice, including other USB DC routines. Those other DC operations are not claimed emulated or native validated.

**Datasheet:** Philips ISP1161 full-speed USB host and device controller (ISP1161A1 Rev 03 2004), A1=0 selects host controller HC; A1=1 selects device controller DC; A0=0 data, A0=1 command; word-aligned 16-bit register accesses. `B0` + `AA37` unlocks device registers after suspend; `BA` is `DcHardwareConfiguration`, `B8` is `DcMode`. `DcMode.GOSUSP` is bit 5: write 1 then 0 to request suspend. Sources:
- https://www.alldatasheetpt.com/html-pdf/113590/PHILIPS/ISP1161A/3004/10/ISP1161A.html (A0/A1 physical pins)
- https://dtsheet.com/doc/203593/philips-isp1161a1bm (DC command and register summary; B0/B8/BA)
- https://docs.rs-online.com/e738/0900766b80426de6.pdf (Philips/NXP ISP1161A1 full datasheet, 13.1.3/13.1.4, device mode/hardware)
- https://dtsheet.com/doc/206877/philips-isp1161bm (unlock code AA37)

## Production code and tests actually executed

- Commit `6f74047723c24d06489df1a405b9052b1341f406` extends the **existing** ISP1161 HC data/command bus mapping from `0x1F000000–3` to `0x1F000000–7`, distinguishes HC vs DC by M68000 16-bit offsets, saves DC state, implements the manufacturer-backed **observed startup sequence only** (B0/AA37, BA/0F04, B8/0020, B8/0000), and explicitly blocks unqualified DC accesses.
- Commit `963c47c9b0676e51f3ef3373ce4c0dfcc9f03222`: `tests/isp1161_uk15_dc_test.py`, compiles **actual production HC/DC handler bodies** with Clang++21 and checks exact Ghidra sequence, HC/DC isolation, M68000 CLR.W discarded read, invalid/unobserved commands, incorrect unlock, state.
- Actual test on T: **1/1 PASS**, with `TMPDIR=/dev/shm/dana_ghidra_tmp` to avoid system temporary-disk quota; the first invocation encountered EDQUOT in `/tmp`, did **not** test the new logic, and was corrected before build and native test.
- Clang21 full incremental MAME build/link **PASS**, 18.57 sec, return 0.
- Exact source SHA256 `f5ddffb06a85c1d7f51d1bd9170eafc3abb17dc7aa54afcba093dfd2c5dcaa66`, byte-identical with pinned GitHub `6f740477...` at time of synchronization.
- Native candidate `source/danadiagd` SHA256 **`019ba04e20b297ce640227934b2b45afbc0d4611f222e399bd6063985c933733`**.
- Installed **operative unchanged**, `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
- Original ROM unchanged; no Ghidra modifications, no CPU PC injection, no quickload.
- Native logs in `work/uk15_qualify_20261025/ghidra_isp1161_dc_20261025/{directed.log,build.log,native.err,native.out,trace.txt}`.

Authentic Palm OS UK1.5 CPU on MAME actually executed:
```text
DANA_ISP1161_DC cmd=b0 value=aa37 hw=0000 mode=0000 suspend_requested=0
DANA_ISP1161_DC cmd=ba value=0f04 hw=0f04 mode=0000 suspend_requested=0
DANA_ISP1161_DC cmd=b8 value=0020 hw=0f04 mode=0020 suspend_requested=0
DANA_ISP1161_DC discarded_write_port_read cmd=b8
DANA_ISP1161_DC cmd=b8 value=0000 hw=0f04 mode=0000 suspend_requested=1
```

**Interpretation:** these transactions succeeded and the guest CPU continued. This does **NOT** mean real USB device packet transfers, suspend clocks, interrupts, endpoints or a complete USB stack are implemented or PASS.

## Next chronological native blocker, separately identified with Ghidra

```text
DANA_PHYSICAL_UNIMPLEMENTED_MMIO read address=fffffa18 mask=ffff
DANA_PHYSICAL_BLOCKED reason=MMIO_READ_UNIMPLEMENTED address=fffffa18 data=0000 pc=10005b7e
DANA_PHYSICAL_CPU curpc=10005b7a ir=3038 sp=00003a6e usp=00000000 sr=2709 a4=10000338
```

Motorola MC68VZ328 UM Table 3-1 identifies `0xFFFFFA18` as **LCXP**, LCD Cursor X Position Register, 16-bit R/W, reset `0000`; `0xFFFFFA1A` **LCYP**, `0xFFFFFA1C` **LCWCH**, `0xFFFFFA1F` **LBLKC**. Ghidra decoded the **genuine LCD cursor function** at `0x10005B42`:
```asm
10005B7A MOVE.W ($FFFFFA18).W,D0
10005B7E ANDI.W #$C000,D0
10005B82 OR.W (A1),D0
10005B84 MOVE.W D0,($FFFFFA18).W
10005B88 MOVE.W ($0002,A1),($FFFFFA1A).W
10005BA4 MOVE.W D1,($FFFFFA1C).W
10005BC0 MOVE.B D0,($FFFFFA1F).W
10005BD6 MOVE.W ($FFFFFA18).W,D0
10005BE2 MOVE.W D0,($FFFFFA18).W
```

Thus the LCXP access is not a guessed peripheral and is a **read-modify-write** preserving cursor control high bits. It must be integrated with the **existing LCD controller**, not modeled as unrelated generic MMIO RAM. Manufacturer reset values: LCXP 0000, LCYP 0000, LCWCH 0101, LBLKC 7F (see Motorola/Freescale MC68VZ328UM Table 3-1). No LCD cursor code added in this DC increment; next work should audit already existing LCD state, implement the exact cursor register semantics and masks, and validate under original ROM without skipping subsequent accesses.

**Palm OS authentic GUI still unbooted**; observer exits after finite frames and is not evidence of graphical boot.
