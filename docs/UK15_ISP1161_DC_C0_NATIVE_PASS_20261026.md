# UK1.5 original Ghidra ISP1161 DC command C0 — native PASS (2026-10-26)

## Status

**Resolved the actual first USB DC command C0 blocker in canonical `main`, no Codex.** Ghidra disassembly, manufacturer datasheet and executable-source directed regression agree. Original ROM `-rom` runs the formerly blocked C0 and both 16-bit data reads from physical DC port; **next independent first failure** is the 32-bit RTC time register, `FFFFFB00`, not USB. Palm OS's authentic **palm POWERED** framebuffer remains on screen, but the full Palm OS desktop has NOT booted.

## Primary manufacturer source and Drive location

- Philips Semiconductors `ISP1161A1`, Rev. 03 (23 December 2004), §8.3 16/32-bit register protocol, Figure 13, §8.6.3 interrupts, §13.3.6 `Read Interrupt Register (R: C0H)` and Tables 108-109: **32-bit DcInterrupt, read 2 consecutive 16-bit words low then high**; reset=0; bit fields for endpoints [23:8], BUSSTATUS bit7, short packet, SOF, EOT, suspend, resume and reset. Upon completed read RESET, RESUME, SP_EOT, EOT, SOF clear; endpoint bits need their individual DcEndpointStatus reads; BUSSTATUS reflects the true physical USB link.
- The same protocol is corroborated by Philips Rev.02 (25 August 2003).
- Motorola `MC68VZ328UM`, original Rev.0: DragonBall VZ CPU and physical memory map.
- **Already uploaded/verified Drive project folder:** `ALPHASMART/Dana/DATASHEETS` (ID `11bKTw_mNBy_bZUpxfyIbStue-Gm2FaQK`).
    - Rev03 PDF: https://drive.google.com/file/d/1mYRvC1TUSisXnkZm97exyj78fmn3VKw_/view ; SHA256 `7d7f573be009ad16148c6f0fb007959233ea0743ea91cc069f414e6333daa9f8` (614152 bytes).
    - Rev02 PDF: https://drive.google.com/file/d/1qdGOIUQm_YST0iYlff99RQsZpScDfWW_/view ; SHA256 `b403e3010cebd0ab3f2b511254d277240bcb1b9957a15f9e75b1ef3c4205c40a` (3066441 bytes).
    - Motorola user manual: https://drive.google.com/file/d/1UuxWG0rYc0n7RoLerqYTt9mlBpU45L6Y/view ; 7223788 bytes, original previously existing in user's Drive and **copied** into the project DATASHEETS folder since external mirrors returned 403/404. Existing original not altered.
- Reference index `ISP1161_FUENTES_IMPLEMENTACIONES_UK15_20261026.md` is also stored in Drive DATASHEETS with source code links and trace identity.

## Available implementation code compared

- **Linux** `drivers/usb/host/isp116x-hcd.c` and `isp116x.h` (https://github.com/torvalds/linux/tree/master/drivers/usb/host): real 16-bit HC command/data FIFO, register32 low/high transactions, interrupt reads; **Host Controller only**, not ISP1161 Device Controller C0.
- **U-Boot** `board/sc3/sc3.c`, `initUsbHost` (https://github.com/sslab-gatech/opensgx/blob/master/qemu/roms/u-boot/board/sc3/sc3.c): original ISP1161 HC initialization, not Device.
- No verified external full Device Controller emulator source was found. Accordingly, C0 implementation uses **Philips DC documentation plus actual ROM sequence**, not an imported HC-only model or speculative USB endpoint interrupts.

## Authentic Ghidra and machine evidence

Existing exact `DanaUK15AfterPCTLRExact.java` disassembled:
```asm
10081732 LINK.W A6,#0
10081736 MOVE.W #$00C0,$1F000006  ; DC command port
1008173E MOVEQ #0,D0
10081740 MOVE.W $1F000004,D0      ; DC data low word
10081746 MOVEQ #0,D1
10081748 MOVE.W $1F000004,D1      ; DC data high word
1008174E SWAP D1
10081750 CLR.W D1
10081752 OR.L D0,D1
10081754 MOVE.L D1,D0
10081756 UNLK A6
10081758 RTS
```
The guest reads the **LOW** and then **HIGH** words. They are combined into a 32-bit value. This sequence exactly matches Philips Fig.13 and §13.3.6.

## Minimal production change and tests

- Existing single controller `src/mame/skeleton/alphasdana.cpp`, commit **`a4062c963cd58bd1c5c479dd391be246f6171a3f`**. Added `m_isp_dc_interrupt` (real persistent register status, reset zero), `m_isp_dc_read_snapshot` and `m_isp_dc_read_phase` with save/reset registration. C0 selects a 32-bit snapshot; first DC DATA read yields low 16-bit, second yields high 16-bit and retires read transaction. Preserves HC state and other DC write commands. Fails closed on incomplete repeated commands or unsupported subsequent reads. Clears only manufacturer-listed read-clear event bits `0x005B`, not endpoint bits or USB BUSTATUS; **does not synthesize phantom USB packets, bus events or interrupts**.
- Actual source-extracted C++20 regression updated at **`1006ad3efa2db5e6ccb52b2580aa1eb7da06644b`**, `tests/isp1161_uk15_dc_test.py`: reset, word order, transaction count, interrupt clear vs persistent bits, HC isolation, prior B0/BA/B8, invalid commands. **1/1 PASS**.
- Prior `pctlr_uk15_test.py` **1/1 PASS** and `csd_rop_read_protection_test.py` **1/1 PASS**.
- Incremental real MAME **Clang21 full build and link PASS**, return 0, 19.23 s.
- Source SHA256 **`44e926bcad3138b62f0fede2d8c3d78466fb70f08a785a3b1876aac1bf0e3dba`**, byte-identical to pinned GitHub commit. Candidate `source/danadiagd` SHA256 **`7c7599d32693afdc9706ae0e9ba2536abb22663eeca7aa2e4b13cf09ce7f4756`**.
- Installed `bin/dana-diag` SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`**, **unchanged**. Private authentic UK1.5 ROM `UK15_private.raw` SHA256 **`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`**, **unchanged**; no ROM published.
- Canonical T DIAG `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag` only. Native 1800-frame bounded observer logs `work/uk15_qualify_20261025/isp1161_c0_20261026/{build.log,native.err,native_metrics.txt,test_*.log,ghidra_next_rtc.txt}`. Exit 0 is observer exit, **not** successful Palm boot.

**Original CPU native transactions observed:**
```text
DANA_ISP1161_DC_INTERRUPT phase=low value=0000
DANA_ISP1161_DC_INTERRUPT phase=high value=0000
```
Zero is the physical **reset/no-generated-events state** of the implemented register, not a user-space override or test-injected event. The source supports event bits if real event generation is implemented later; it does not claim USB enumeration, endpoint activity or full device-controller functionality.

## Next real independent guest event — Ghidra verified

```text
DANA_PHYSICAL_UNIMPLEMENTED_MMIO read address=fffffb00 mask=ffff
DANA_PHYSICAL_BLOCKED reason=MMIO_READ_UNIMPLEMENTED address=fffffb00 data=0000 pc=1007fd2a
DANA_PHYSICAL_CPU curpc=1007fd26 ir=4ab8 sp=0007ec5a sr=2004
```

Ghidra `DanaUK15AfterUSBC0.java` on original ROM:
```asm
1007FD26 TST.L  ($FFFFFB00).W
1007FD2A LEA    (0x10,SP),SP
1007FD2E BNE.B  1007FD36
1007FD30 MOVE.L (-0x1A,A6),($FFFFFB00).W
1007FD3A MOVE.W #$000A,($FFFFFB10).W
1007FD40 MOVE.W #$0080,($FFFFFB0C).W
```
Manufacturer `MC68VZ328UM` §11.2.1 / Table 3-1 identifies `FFFFFB00` as **32-bit RTCTIME**, real-time clock time-of-day, reset value partially undetermined `XXXX00XX` (RTC is always enabled). **Do not pretend RTCTIME is a generic zero register** or implement next RTC behavior in this closed USB C0 change; it needs proper read/write/time progression, day rollover and initialization semantics. This is the next authentic blocker, not an unknown USB status register.

**Final scope: C0 native PASS; Palm OS graphical desktop remains unproven.**
