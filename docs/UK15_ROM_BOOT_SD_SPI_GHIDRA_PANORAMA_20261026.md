# UK1.5 Dana — Ghidra boot panorama, original SD/MMC driver wait and PLL audit
**Date:** 2026-10-26. **Scope:** original 68k UK1.5 ROM, existing single T DIAG, `SamDelorean/DANA-emu` **main**. This is diagnosis, **no code changes** and no new executable installation.

## A. Where the original firmware actually is

Ghidra 12.1.3 headless executed on T on the **authentic private original** ROM SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, base `0x10000000`, language `68000:BE:32:default`. We mapped non-initial segment ranges at `0x10100000`, `0x10110000`, `0x10310000`, `0x10320000` from the *local original ROM*; no manufactured code/CPU emulation. New original listings: `work/uk15_qualify_20261025/boot_progress_20261026/rom_startup_panorama.txt` (666 lines) and `rom_driver_graph.txt`, produced by `ghidra_scripts/DanaROMStartupPanorama.java` and `DanaROMDriverGraph.java` in the **original Ghidra project** `DanaUK15RelocatedTemp`.

Native MAME CPU verified actual boot:
```text
reset original UK1.5 -> Palm Powered splash, LSSA=00003B00 (frames60-240)
-> AlphaSmart second splash, LSSA=00072A10 (from ~frame300 through frame5400/90s)
-> Palm OS's database/slot driver library setup
-> SPI/MMC dual-slot initialization and polarity/IRQ stabilization
   -> waits for card-slot GPIO input levels; no Palm desktop yet
```
**Do not say the display is still Palm Powered**: old fixed base `3B00` observer was wrong after ~frame300, while real display correctly uses current LSSA `72A10`.

### Original PalmOS call graph (each edge from CPU stack or Ghidra)

The actual 68000 stack at frames304, 360, 1200 and 1800 in default conditions:
```text
100E6ABE -> 100E64A2 -> 100E65AA
 -> 1010FD44 -> 1010FD84 -> 10110148 -> 101101E4
 -> 10317FF2 (PrvShouldWeInstall, Database Slot Driver Library)
 -> 1032596A (SPI driver initialization)
 -> 10325712 (PrvSpiSetPol0, waiting in Palm HwrDelay A249)
 -> 1007B090 (CLK32 status polling)
```
Above addresses in stack are **return addresses**, not all function entries. Do not mislabel them as entrypoints.

Names recovered from **literal symbols retained in original ROM** by reading the original binary (not inferred from address):
- `10317F86` "Database Slot Driver Library"; `10317FA5` "PrvDispatchTable"; `10317FC3` "PrvShouldWeInstall" before entry `10317FD8`.
- `1031C917` "SpiMmcBlockReadTunnelP", `1031C937` "HwrSpiSleepTunnelP", `1031C953` "HwrSpiWakeTunnelP", `1031C96D` "HwrSpiOpenTunnelP", `1031C987` "HwrSpiCloseTunnelP", `1031C9A3` "HwrSpiCardInSlotTunnelP".
- `103256C9` "HwrSpiCsSetTunnelH".
- `10325759` "**PrvSpiSetPol0**", preceded by actual function entry `103256DE` (slot 0).
- `103257E3` "**PrvSpiSetPol1**", preceded by actual function entry `10325768` (slot 1).
- `10321CAF` "SpiCardRemovingDelayedTunnelS"; `10321CD5` "SpiSdioAutoRunGetTunnelS".
- Code: `10317FEE JSR 1031C966`, `1031C966 JMP 10321AFA` (SPI wake tunnel); `10325966 JSR 103256DE` (slot0); **only after successful slot0** `103259CA JSR 10325768` (slot1). Then programs other GPIO and returns.

### Exact electrical algorithm at each slot

**`PrvSpiSetPol0` at `103256DE`**, uses Port D:
```asm
103256EA MOVE.B ($FFFFF419).W,D0  ; actual PortD DATA
103256EE ANDI.W #$0004,D0         ; PD2 (input)
103256F4 EORI.B #$04,($FFFFF41C).W ; if high, flip PDPOL2
103256FA MOVE.B ($FFFFF419).W,D0
103256FE ANDI.W #$0002,D0         ; PD1 (output in observed boot)
10325704 EORI.B #$02,($FFFFF41C).W ; if high, flip PDPOL1
1032570A PEA #$00FA              ; delay argument 250
1032570E TRAP #$F, $A249         ; PalmOS HwrDelay(250), not SysTaskDelay
10325712 MOVE.B ($FFFFF419).W,D0
10325716 ANDI.W #$0006,D0
1032571C BEQ 10325722           ; both bits low -> add to counter
1032571E MOVEQ #0,D3             ; any high -> reset counter
10325722 ADDQ.B #1,D3
10325724 CMPI.B #3,D3
10325728 BCS 103256EA           ; wait for 3 consecutive qualified samples
1032572A..1032574E pack status bits $40/$80 from PDPOL, return to caller
```
**`PrvSpiSetPol1` at `10325768`** repeats with **PD3 (input) and PD0 (output)** masked `0x09`, same delay 250, stability count three; status output for slot1. Actual boot at this stage PDDIR `0x03` means **PD0 and PD1 are output**, **PD2 and PD3 external inputs**. Thus asserting “PD1 and PD2 are both external card sensors” is inaccurate; the firmware samples an output-latch/control bit and an input sensor per slot. The physical assignment of detection, protection, insertion power and exact board pull-ups is **not independently verified**, despite symbolic SPI slot affiliation. PDPOL = `0xFFFFF41C` configures **interrupt polarity**; it is not the data register and the ROM does not simply invert the DATA latch. Dedicated INT[0..3] share PD0..3.

**This is NOT the USB ISP1161, not UART bootstrap, not a missing MMIO command, nor a frozen PLL.** It's a driver routine for external SD/MMC cards through Motorola SPI+GPIO, executed while AlphaSmart splash is visible.

## B. TRUE original CPU causal experiments — no source or firmware patches

A prior Lua `install_read_tap` returned synthetic PD input only in *observer readings*, zero actual CPU accesses hit that program-space observer tap; those trials **did not test the CPU** and must not be cited as showing PD2 low ineffective. We corrected methodology: feed **real electrical input levels through MAME's I/O configuration**, using a **separate transient asmdana.cfg in an experiment folder**, with no source/executable ROM changes.

Actual physical pin configuration on native ROM after frame303: PDDIR=`03`, PDDATA=`8C` for default PD2/PD3 high; PDPUEN=`1C`. Two real virtual card sensors wired by existing emu `m_sd_irq->read()` on PD2 bit2, PD3 bit3; PortD output latches PD0/PD1 from `m_gpio[4..7]`. No claimed board schematic polarity, defaults high were explicit earlier **assumptions**.

| Trial | I/O `SDIRQ` | True guest `PDDATA` | Original CPU caller inside HwrDelay | Evidenced outcome |
|---|---|---|---|---|
| Default, both high | `0x0C` | `0x8C` | `10325712` | **PrvSpiSetPol0** never obtains three all-low samples; wait at first slot through 90 sim seconds |
| Slot0 input PD2 held low, PD3 high | `0x08` | `0x88` | `1032579C` from frame303 | **PrvSpiSetPol0 COMPLETED** and firmware enters **PrvSpiSetPol1** (now waiting second sensor) |
| Both PD2 and PD3 held low | `0x00` | `0x80` | `10326904` at frame303, later `1032579C` and `10325712` | Firmware briefly advances into a downstream setup routine but later repeatedly services both slot routines; remains on AlphaSmart at 40 simulated s |

This is a **positive direct causal test of the guest 68000** (return-address change), not merely a logged GPIO read. Data `cfg_sd0_low_callchain.metrics`, `cfg_sd_both_low.metrics`, scoped XML config in original work directory. The screens were tracked through real live LSSA `0x00072A10`. Neither test reached Palm desktop. The repeated callbacks may reflect initializing/waking slots and could be part of a wider startup service; do not diagnose root cause solely from 1–2 pin values or commit default input changes without PCB evidence.

**Other emulator corroboration:** [CloudpilotEmu `EmRegsVZ.cpp`](https://github.com/cloudpilot-emu/cloudpilot-emu/blob/master/src/cloudpilot/emulator/hardware/EmRegsVZ.cpp) `UpdatePortDInterrupts` evaluates polarity, edge/level, input direction, enable for **all four** low PortD INT bits. Current `alphasdana.cpp` `sd_gpio_irq()` only computes `&0x0c` PD2/PD3 signals; no verified external PD0/PD1 IRQ wiring (used as output). Cloudpilot's special PortD DATA polarity XOR exists only behind `if (0 && port=='D')`, disabled; do **not** invent data inversion as a shortcut.

## C. CPU clock and manufacturer low-frequency status audit

From native original UK1.5 log:
```text
DANA_PLLCR value=24a3 sysclk_hz=16580608
DANA_PLLCR value=2483 sysclk_hz=33161216 physical_clock_change=1
```
Physical reset PLLCR=`24B3`, PLLFSR=`0347`. Code `physical_system_clock_hz()` uses Motorola MC68VZ328UM §4.3.2 `PLLCLK=2*(14*(P+1)+Q+1)*32768` and PRESC1/PRESC2/SYSCLKSEL. Actual **33,161,216 Hz** matches Dana public 33 MHz CPU. `m_maincpu->set_unscaled_clock` actually updates M68000 when firmware changes PLLCR. PCTLR=`9F` full CPU duty. **AS2K-style global 68k CPU half-speed discrepancy NOT present.**

**Potential definite factor-2 in low-frequency square-wave phase timing:** source at `machine_reset` configures
```cpp
m_clk32_timer->adjust(attotime::from_hz(32768),0,attotime::from_hz(32768));
```
and `clk32_tick()` flips boolean each timer callback, bit15 of physical `PLLFSR`. Motorola MC68VZ328UM §4.3.1 specifies oscillator `32.768 kHz`; §4.4.2 Table 4-4 says `PLLFSR.CLK32` read-only indicates high vs low and switches as signal cycles. If a normal square wave of 32.768kHz, there are **65,536 high/low transitions per second** (rising+falling), whereas current emu yields **32,768 transitions/s**, effective square frequency 16.384kHz. The original delay code at `1007B060` (ROM label near `HwrTimeWait`) waits for **both phase changes**; thus delays could be ~2× manufacturer expectation:
```text
HwrDelay(250) -> derived counter D2~16 ->
16 edges at 65,536/s ≈ 244us expected
16 edges at 32,768/s ≈ 488us current emulator
```
This deserves a **bounded timing correction with regression**, not CPU global frequency hack and not sufficient alone to explain a 90s screen wait. No clock/source edit was made in this report.

## D. Single product-level diagnosis and honest next condition

The authentic firmware proceeds through PalmOS boot, logo, slot-driver library `PrvShouldWeInstall`, hardware `HwrSpiWakeTunnel`, per-slot `PrvSpiSetPol0/1`, samples physically external Card0/1 sensing at PD2/PD3 while PD0/1 output, adjusts interrupt polarity, waits a few hundred microseconds and requires three stable low samples, returns packed status and goes on to set up SPI/GPIO and slot structures. It does **not** wait for a new USB command, and CPU oscillates.

**Known mismatches worth resolving as one coherent SD/MMC subsystem**, not infinite MMIO gates:
1. Actual Dana PCB contact wiring/polarities and whether card absent/present asserts PD2/PD3 high/low.
2. Faithful PortD register interaction: data input vs output, pullups, selector, PDPOL, IRQ mask/edge registers and complete chip interrupt signalling; emu presently manually assumes PD2/PD3 high and handles only those interrupts.
3. Short wait `HwrDelay` CLK32 phase cadence vs official 32.768k clock, without touching main CPU clock.
4. SD/MMC SPI1 controller and present/not-present card emulation already implemented: verify whether socket controller notifies startup service as expected, with disk images absent or present, rather than mocking return values.

No code, installed operative, original ROM or extra DIAG changes in this diagnosis.
