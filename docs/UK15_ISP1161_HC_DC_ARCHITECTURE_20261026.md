# DANA-emu: ISP1161A1 architecture-level HC/DC integration (2026-10-26)

## Outcome and scope

**The user instructed: implement the ISP1161 chip coherently, not one new MMIO error at a time.** This increment therefore expands the physical device controller from a hard-coded list of a few UK1.5 register accesses to an **indexed Host Controller and Device Controller control-register model**, with independent command/data ports, 16/32-bit bus transactions, Host PIO FIFO storage, root-hub/USB state and independent reset domains. The original firmware now runs past its Host command `27` identifying the chip, checks revision `0x61xx`, executes further HC and DC initialization **without any further fail-closed MMIO block** during an independently observed 30 simulated seconds.

This is **not yet the entirety of USB device hardware**. The connected-device USB host packet/PTD scheduling engine, downstream external peripheral models, DC endpoint ping-pong data-transfer engine, physical USB signalling and physical DMA requests/acknowledgement are **not yet implemented**. It would be misleading to call the USB PHY or enumerated downstream devices PASS merely because register and FIFO-PIO cases work. The emulator product remains the sole priority, and the Palm OS graphical desktop is not yet authenticated.

## Original semiconductor documentation

Primary: Philips Semiconductors [ISP1161A1 Rev.03, 23 December 2004](https://drive.google.com/file/d/1mYRvC1TUSisXnkZm97exyj78fmn3VKw_/view), at the user's project Drive `ALPHASMART/Dana/DATASHEETS`. Rev.02 is also retained there: https://drive.google.com/file/d/1qdGOIUQm_YST0iYlff99RQsZpScDfWW_/view.

- **HC §10, Table 7 (pages 44–45)** indexes the 32-bit OHCI registers, 16-bit DMA/interrupt controls, root hub with two downstream ports, scratch/ChipID, software reset and FIFO buffer controls.
- **HC §10.5.1, Table 46 (page 70): `0x27` HcChipID is a 16-bit READ, reset `0x6123`**. A preceding general example refers to early engineering version `0x6110`; it must not override the Rev03 silicon ID table.
- **HC §10.5.3** software reset: command `A9` followed by `F6` to data port, resets HC registers but **preserves HC internal buffer memory and does not reset DC**.
- **HC §10.6:** separate 4KiB HC buffer RAM, ITL0/ITL1 and ATL, TransferCounter, PIO command/data FIFO ports `40/C0`, `41/C1`.
- **DC §13, Table 75 (pages 90–92):** indexed DC registers including `B0` unlock, `B2/B3` scratch, `B6/B7` device address, `B8/B9` mode, `BA/BB` hardware, `C2/C3` 32-bit interrupt-enable, `C0` 32-bit interrupt status, `F6` DC-only reset, 16 endpoint configuration/status indexes, DMA control.
- **DC §13.3.5, Table 106 (page 106): `B5` Device Chip ID is also `0x6123`**.
- **Bus §8:** A1=0 selects HC, A1=1 selects DC; A0=1 command, A0=0 data. 32-bit register data is transferred as two successive 16-bit words, **low first then high**, regardless of M68000 instruction width.

Corroboration: actual Linux [`drivers/usb/host/isp116x-hcd.c`](https://github.com/torvalds/linux/blob/master/drivers/usb/host/isp116x-hcd.c) and [`isp116x.h`](https://github.com/torvalds/linux/blob/master/drivers/usb/host/isp116x.h), plus U-Boot board initialization. These implement **HC host** access, not a full DC. EmuTOS is a guest OS, not an ISP1161 hardware reference.

## Original Ghidra reverse engineering: scope widened past the first fault

Ghidra 12.1.3 run on T against the **same original private UK1.5 image** `UK15_private.raw` SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. Existing project `DanaUK15RelocatedTemp`, `68000:BE:32:default`, ROM base `10000000`. Script `ghidra_scripts/DanaUK15ISP1161HCInitAudit.java` selectively mapped private original ROM segment at `10300000–1030FFFF` and decoded **actual CPU instruction boundaries**:

```asm
10301A76 MOVE.W #$0027,$1F000002 ; HC command ChipID
10301A7E MOVE.W $1F000000,D0    ; HC data, 6123
10301A84 ANDI.W #$FF00,D0
10301A88 CMPI.W #$6100,D0       ; original checks manufacturer code
10301AB0 MOVE.W #$00A9,$1F000002 ; HC software-reset command
10301AB8 MOVE.W #$00F6,$1F000000 ; HC reset value
10301AC6 MOVE.W #$0027,$1F000002 ; HC ID again after reset
10301ACE MOVE.W $1F000000,D3
10301AE8 MOVE.W #$00A8,$1F000002 ; HC scratch write
```

Native ROM static scan identified **28 distinct HC direct command immediates** and **9 distinct DC direct command immediates**; map recorded in the single T work area. This supports the architecture change rather than adding only `0x27`.

## Actual product integration in original main, not a side emulator

Source `src/mame/skeleton/alphasdana.cpp` on existing `main`, three implementation commits:

1. [`5c822aeba24cd2eb71ee8a12d3e2c026a892211d`](https://github.com/SamDelorean/DANA-emu/commit/5c822aeba24cd2eb71ee8a12d3e2c026a892211d): all Table 7 HC register-command decode, 16/32-bit phases, correct ChipID, HC software reset, writable and W1C OHCI interrupt operations, root port state for disconnected peripherals, SOF virtual 1 ms timer, 4 KiB true RAM for ITL/ATL PIO transfer, 4 KiB total allocation guard, DMA/interrupt/scratch controls.
2. [`f6cbadb542cf264831c58556ed355370193dfeba`](https://github.com/SamDelorean/DANA-emu/commit/f6cbadb542cf264831c58556ed355370193dfeba): the same physical mapping extends DC Table 75 control register commands, 16 endpoints' configuration/status, 32-bit DC interrupt-enable/status low/high transactions, DMA register storage, device address, scratch, GOSUSP sequencing and F6 DC-only software reset. Separate 2462-byte DC RAM state reserved. **DC endpoint FIFO payload transfer and USB endpoint scheduling are NOT implemented, and there is no fake data from a USB host.**
3. [`fc01a0c585736033553b8c0112d13f0f569b16f1`](https://github.com/SamDelorean/DANA-emu/commit/fc01a0c585736033553b8c0112d13f0f569b16f1): genuine two-port Root Hub NDP=2 at HC reset, no phantom devices attached; HcFmRemaining derived from emulated millisecond phase while HC operational, rather than always returning zero.

No change to the original private firmware, the single DIAG structure, `main`-only workflow, or installed operative `bin/dana-diag`. New host/device persistent registers, FIFO, command phase and reset states are covered by MAME save-state registration.

## Functional evidence — not just static tests

All testing on the **only existing T DIAG**:

`/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`.

Physical MAME bus/real-driver test source [`tests/isp1161_hc_dc_bus.lua`](https://github.com/SamDelorean/DANA-emu/blob/main/tests/isp1161_hc_dc_bus.lua), initial [`953fba69`](https://github.com/SamDelorean/DANA-emu/commit/953fba69bc08f86579e0ec7b5a8b0e1b6bac25d5), extended [`fd67de3f`](https://github.com/SamDelorean/DANA-emu/commit/fd67de3f49aa69878494bfea78451066e9b68df0). It uses MAME's *production* program-space read_u16/write_u16 on physical HC addresses `1F000000/2`, DC addresses `1F000004/6`, and tests values rather than faking internal register classes. **33/33 PASS** on T, covering:

- HC and DC separately returning manufacturer ChipID `0x6123`.
- HC HcRevision 32-bit lower/upper word ordering.
- HC OHCI register write/read frame interval and root hub descriptor.
- HC scratch and µP IRQ state/enable.
- Host buffer allocation and true two-word 4-byte ATL FIFO PIO roundtrip, HcBufferStatus.
- DC unlock, scratch and USB address readback.
- DC read/write mode and hardware configuration.
- Endpoint configuration and status/image without creating USB events.
- DC 32-bit IRQ enable and interrupt status, lower/upper word ordering.
- DC DMA configuration register readback.
- HC software reset `A9/F6` preserves DC scratch; DC `F6` reset preserves HC scratch.

[Updated regression `tests/isp1161_uk15_dc_test.py`](https://github.com/SamDelorean/DANA-emu/blob/main/tests/isp1161_uk15_dc_test.py) checks source production structure and, given the original ROM path and candidate binary in environment, executes **all 33 real MAME bus cases**, 2/2 Python tests PASS. Existing production tests `pwm1_uk15_test.py`, `rtc_uk15_test.py`, `csd_rop_read_protection_test.py`, `pctlr_uk15_test.py` all separately PASS.

**Final Clang21 MAME build/link PASS**, 19.73 sec. Final original physical UK1.5 `-rom` bounded 30-second execution PASS with no physical `DANA_PHYSICAL_BLOCKED` entries; authentic `palm POWERED` splash remains with 4,161 dark pixels in frames 60–240.

**Final source SHA256:** `c50baf64a7a33e4cc0eb50240c7788d7480a7db6bd0a2a64704dd7216d7083a9`.

**Staged candidate `source/danadiagd`:** `1c141495c39fa0365a0fa299500912ea22140c811f237e4e376f5deb2f66efa5`.

**Installed operative `bin/dana-diag`:** `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` **unchanged**. Original ROM unchanged as above.

All T artifacts remain under `work/uk15_qualify_20261025/isp1161_full_hc_20261026/`: Ghidra listing, host/DC register regression scripts, 33-case output, final build log, native RAM images, and CPU traces.

## Other real boot finding (NOT a new USB command failure)

At the end of the bounded 30-second original ROM run, guest CPU frequently executes `0x1007B090`. Ghidra original `ghidra_scripts/DanaISP1161HostWaitAudit.java` disassembled:

```asm
1007B082 MOVE.W ($FFFFF202).W,D5
1007B086 ANDI.W #$8000,D5
1007B090 MOVE.W ($FFFFF202).W,D0
1007B094 ANDI.W #$8000,D0
1007B098 CMP.W D0,D1
1007B09A BEQ.B 1007B090
1007B09C MOVE.W ($FFFFF202).W,D5
1007B0A4 SUBQ.L #1,D2
1007B0A6 BNE.B 1007B08E
```

This is **DragonBall VZ PLLFSR CLK32 32,768 Hz phase-count delay**, not a USB Host register operation and not automatically a CPU hang. Subsequent passive MAME read-tap `clk32_read_metrics.txt` saw **81,800 genuine bit15 changes across 420 frames** (2,337,939 reads), confirming the clock is actually oscillating and guest code observes it changing. Thus the new architectural ISP1161 integration avoids attributing unrelated boot delays to USB. A long timer/delay argument and original boot progression remain to be analyzed before attributing Palm OS desktop absence to the USB controller.

## Important remaining hardware capabilities

The implementation covers **HC/DC register-control plane and HC PIO FIFO**, but does **not** yet provide a complete packet-level USB simulator:

- No real connected-device OHCI Host schedule/PTD execution with packets, enumeration, error handshakes, port attach/detach, and downstream USB peripherals.
- No physical DC endpoint ping-pong FIFO read/write transactions, USB SETUP and IN/OUT requests from an attached upstream host; DC SRAM exists as save-backed state but is not yet active payload storage.
- No actual USB DMA request/acknowledge handshake or verified INT1/INT2 external pin wiring to the DragonBall VZ GPIO/IRQ multiplexer.
- Host controller frame-related and root-hub state is a software timing model; exact analog PHY timings, port-power electrical behaviour and suspend/wakeup transitions are not independently verified.

These are **explicit architectural work items**, not arbitrary missing-command patches; do not mark them PASS or invent a connected USB device. Palm OS graphical desktop still **NOT booted**. Installed operative remains unchanged. Keep the product as DANA-emu and work directly in its existing `main` and one T DIAG.
