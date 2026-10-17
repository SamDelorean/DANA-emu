# D0.2 — MC68EZ328 (MAME) versus MC68VZ328 (Dana) register comparison

**Date: 2026-10-13. Status: documentary SPEC_READY, not functional PASS.** This was a static-only increment. MAME, T, Ghidra and firmware were not modified.

## 1. Finding

**MAME's DragonBall EZ is a reuse foundation, not a drop-in replacement for VZ.** Both share a 68000 CPU core and register families, but differ in chip selects and DRAM, reset values, IRQ priorities, GPIO, Timer2, SPI1, UART2 and LCD DMA.

**Source authority:** Motorola MC68VZ328UM manual **plus MC68VZ328UMAD addendum** → open POSE/Retro68 implementations → accesses observed in EmuTOS-Dana → extrapolations from MAME EZ. POSE initialization values are **not** assumed to be physical reset values where they conflict with manufacturer documentation.

### Immutable sources

- **ME:** [MAME mc68328.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.cpp) and [mc68328.h](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.h), especially lines 113–330 and 370–559.
- **PV:** [POSE EmRegsVZ.cpp](https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Hardware/EmRegsVZ.cpp), kInitial68VZ328RegisterValues table, lines 73–335; [M68VZ328Hwr.h](https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Palm/Platform/Core/Hardware/IncsPrv/M68VZ328Hwr.h).
- **ET:** [EmuTOS-Dana bios/dana.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c), lines 42–98, 201–305 and 308–370.
- **DZ:** [dbztool danainit.sh](https://github.com/davidgiven/dbztool/blob/d32702383c2ea3523ea58599c52345435c74e900/danainit.sh), chip-select and DRAM references *after* bootstrap.
- **UM:** [Motorola MC68VZ328UM/D](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), tables 3-1/3-2 and chapters 6–14.
- **AD:** [Official MC68VZ328UMAD/D addendum](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf), corrections to CSCTRL, LRRA, SPI1 and UART.

### Address convention

Table offsets are added to **0xFFFFF000**. For example, offset 0x700 gives address **0xFFFFF700**. Access widths are in bits. Values marked **POSE** indicate its modeled reset, not a confirmed manufacturer value; **AD** and **UM** indicate manufacturer sources. The 4 MiB RAM contents and registers configured by dbztool/EmuTOS are **not** the power-on electrical reset state.

## 2. Register-by-register MMIO contract

| Function | VZ offset(s) | Width | MAME EZ equivalent | Observed/corrected VZ reset | Difference or effect to model |
|---|---|---|---|---|---|
| SCR | 000 | 8 | Yes; MAME EZ starts at 0x0C | **0x1C UM/PV** | Different RESET; do not inherit EZ |
| Chip ID | 004–007 | 32 total | EZ revision reads, not VZ ID | Chip ID 0x56 in PV | CPU identity, verify datasheet |
| CS A/B/C/D base | 100,102,104,106 | 16 each | Yes | 0x0000 each PV/UM | Similar bases; physical effects vary by model |
| CSUGBA upper group | 108 | 16 | **Not EZ**; classic MC68328 places mask A here | 0x0000 PV | Different register at the same offset |
| CSCTRL1 | 10A | 16 | **Not EZ**; classic MC68328 has mask B | **0x0000 AD** | VZ groups and bank control |
| CSCTRL2 | 10C | 16 | No | **0x1000 AD**; POSE incorrectly uses 0x0000 | Critical reset correction |
| CSA / CSB / CSC / CSD | 110/112/114/116 | 16 each | Yes, EZ-specific masks | 0x00B0 / 0 / 0 / 0x0200 UM/PV | Windows/bus/DRAM and external signals |
| EMUCS | 118 | 16 | Yes | 0x0060 UM/PV | Emulation chip select |
| CSCTRL3 | 150 | 16 | Not EZ | **0x9C00 AD**; POSE incorrectly uses 0x0000 | Critical reset correction |
| PLLCR | 200 | 16 | Yes; MAME EZ 0x2400 | 0x24B3 **POSE** | Recalculate clock and VZ model |
| PLLFSR | 202 | 16 | Yes; MAME EZ 0x0123 | **0x0347 UM**; POSE's 0x0123 is not the VZ reset | Bit15 **CLK32 changes over virtual oscillator time**; bit14 PROT sticky until reset; QC/PC 11:0 mask |
| PCTLR | 207 | 8 | Yes | 0x1F **POSE** | Power/STOP states to cross-check |
| IVR | 300 | 8 | Yes | 0x00 UM/PV | ET writes 0x40 before enabling IRQ |
| ICR | 302 | 16 | Yes | 0x0000 UM/PV | ET writes 0x8000 |
| IMR | 304–307 | 32 (two 16-bit words) | Yes | 0x00FFFFFF UM/PV | ET masks first, later enables Timer1/UART1 |
| ISR | 30C–30F | 32 | Yes | 0x00000000 UM/PV | Status is distinct from pending |
| IPR | 310–313 | 32 | Yes | 0x00000000 UM/PV | Real pending, priority and acknowledgment |
| ILCR | 314 | 16 | **Not EZ** | 0x6533 UM/PV | Programmable VZ IRQ levels |
| GPIO A–G | 400–433, discontinuous | 8 per register | Partially shared | Per-register POSE table | Distinct multiplexing, pull-up/down and external inputs |
| GPIO J/K/M | 438–44B, discontinuous | 8 per register | **Not in EZ class**; some exist in classic MC68328 | Per-register POSE table | Dana ST, SD, LCD on J/K pins |
| Timer1 TCTL/TPRER/TCMP/TCR/TCN/TSTAT | 600/602/604/606/608/60A | 16 each | Yes | 0000/0000/FFFF/0000/0000/0000 PV/UM | ET configures compare, prescaler and ack |
| Timer2, same sequence | **610/612/614/616/618/61A** | 16 each | **Not EZ**; classic MC68328 places Timer2 at **60C** | 0000/0000/FFFF/0000/0000/0000 PV/UM | Do not copy the MC68328 Timer2 location |
| SPI1 RX/TX/CTRL/INT/TEST/SPC | **700/702/704/706/708/70A** | **16 each** | **Not in EZ class**; classic MC68328 maps SPIS at 700 | 0x0000 each PV/UM | **Critical: VZ SPI1 is master/slave and serves SD** |
| SPI2 DATA/CTRL | 800/802 | 16 each | EZ SPIM exists at these offsets | 0x0000 each PV/UM | Dana ST/ADC; validate bitfields/XCH |
| UART1 USTCNT/UBAUD/URX/UTX/UMISC | 900/902/904/906/908 | 16 each | Yes (only EZ UART) | 0000/**0002**/0000/0000/0000 | **AD corrects BAUD1**; EZ MAME and POSE use 003F |
| UART1 noninteger prescaler | 90A | 16 | Not in inspected EZ | 0x0000 POSE | New baud-rate adjustment |
| UART2 CONTROL/BAUD/RX/TX/MISC/PRESC/HMARK | 910/912/914/916/918/91A/91C | 16 each | **Not EZ** | 0000/**0002**/0000/0000/0000/0000/**0102** | **AD corrects BAUD2; UM says HMARK 0102 (POSE 0000)** |
| LCD LSSA | A00 | 32 | Yes | 0x00000000 POSE/UM | Physical framebuffer address, not host pointer |
| LCD LVPW, LXMAX, LYMAX | A05/A08/A0A | 8/16/16 | Yes | FF/03F0/01FF POSE | ET writes 35/560/159 for Dana |
| LCD LPICF, LPOLCF, LACDRC, LPXCD, LCKCON | A20/A21/A23/A25/A27 | 8 each | Yes | 0/0/0/0/0 POSE | ET writes 8/0/0/3/0x80 |
| **LCD LRRA** | **A28** | **16** | EZ MAME has an 8-bit register at **A29** | **0x00FF AD** | **Width and position corrected by AD** |
| LCD LGPMR / PWMR | A33 / A36 | 8 / 16 | EZ subsets only, different semantics | 84 / 0000 POSE | Grayscale and contrast modes |
| LCD RMCR / DMACR | A38 / A39 | 8 each | Not in inspected EZ | 00 / 62 POSE/UM | VZ-specific LCD DMA |
| RTC/watchdog control | B00–B1C | 8/16/32 by register | Partial | Consult UM+AD | **AD corrects RTCCTL and STPWCH to 16 bits** |
| **DRAMMC/DRAMC/SDCTRL/SDPWDN** | **C00/C02/C04/C06** | **16 each** | **Not in MAME EZ** | **0000/0000/003C/0000 per UM** | **POSE puts 003C on DRAMC and 0000 on SDCTRL; reset mismatch** |
| ICEM/hardware debug | D00–D0E | 16/32 | No equivalent | Zero in POSE | Keep bootstrap/debug separate from host debugger |

**Bit-level equivalence is not claimed for every register.** D0.2 fixes the map, widths, critical resets, and integration effects/risks. VZ masks, read behavior, timing and bus restrictions are verified under D1–D4 implementation contracts against UM+AD rather than invented.

## 3. Dana GPIO configuration and risks

| VZ port | 8-bit offsets (DIR/DATA/PUEN/SEL) | POSE reset in order | Observed Dana function |
|---|---|---|---|
| B | 408/409/40A/40B | 00/00/FF/FF | PB6 ST reset; PB5 SD0 power |
| C | 410/411/412/413 | 00/00/FF/FF | LCD PDEN/SEL and pins; C412 is pulldown |
| D | 418/419/41A/41B (plus 41C–41F) | 00/00/FF/FF, others 00 | Experimental ST/SD switches; port polls ST |
| E | 420/421/422/423 | 00/00/FF/FF | PE3 ST chip select |
| F | 428/429/42A/42B | 00/00/FF/8F | PF1 pen IRQ, PF2 SD1 CS, PF6 contrast |
| G | 430/431/432/433 | 00/00/3D/08 | PG2 touchscreen CS |
| J | 438/439/43A/43B | 00/00/FF/EF | PJ3 SD0 CS |
| K | 440/441/442/443 | 00/00/FF/FF | PK2 ST ready, PK6/PK3 contrast, PK7/PK4 LCD |

These are **POSE-modeled resets**, not proof of actual Dana board electrical levels. Cross-check board connections against EmuTOS and Retro68; do not substitute the NEO keyboard matrix for ST.

## 4. Relevant errata and discrepancies: blockers to copying registers

| ID | Incorrect secondary-source assumption | Official VZ value to use |
|---|---|---|
| ERR01 | POSE CSCTRL2=0x0000 | **0x1000**, 0xFFFFF10C, 16 bits (AD) |
| ERR02 | POSE CSCTRL3=0x0000 | **0x9C00**, 0xFFFFF150, 16 bits (AD) |
| ERR03 | POSE UBAUD1/2=0x003F | **0x0002**, 0xFFFFF902 and 0xFFFFF912 (AD) |
| ERR04 | Early manual gives 8-bit LRRA at A29 | **16 bits at 0xFFFFFA28**, reset 0x00FF (AD) |
| ERR05 | Early manual gives 8-bit SPI1 RX/TX | **16 bits** at 0xFFFFF700 and 0xFFFFF702 (AD) |
| ERR06 | POSE DRAMC=0x003C; SDCTRL=0x0000 | **DRAMC=0x0000; SDCTRL=0x003C** (UM) |
| ERR07 | POSE UART2 FIFO HMARK=0x0000 | **0x0102 at 0xFFFFF91C** (UM) |
| ERR08 | Classic MC68328 Timer2 uses offset 60C | **VZ Timer2 begins at 610** |
| ERR09 | Treat 700 as generic EZ SPI slave | **VZ SPI1 RX/TX/CTRL/INT/TEST/SPC occupies 700–70A** |
| ERR10 | Treat 4 MiB RAM and EmuTOS PC as electrical reset | **Post-bootstrap state**, not hardware reset |

These discrepancies are **documentary findings**, not measured real-hardware defects or confirmed POSE runtime failures.

## 5. Observable contract for later increments

- **D1 chip selects/DRAM:** RAM-only profile permits 4 MiB of preinitialized RAM and documented CPU/PC/SP. Cold boot must model real reset and programmable CS/DRAM without inventing physical Flash regions. Inspect [danainit.sh](https://github.com/davidgiven/dbztool/blob/d32702383c2ea3523ea58599c52345435c74e900/danainit.sh) writes before deciding layout.
- **D2.1 PLL:** ET waits for PLLFSR bit 15 to alternate in delay_us. Model virtual clock events, not an instruction-dependent forced constant.
- **D2.2 IRQ:** IVR=0x40, ICR=0x8000, IMR initially 0x00FFFFFF; UART1/Timer1 interrupts must actually reach the guest.
- **D2.3 Timer1:** ET programs prescaler, compare, TCTL1=0x33 and acknowledges TSTAT1. Virtual time governs ticks.
- **D2.4 UART1:** ET checks UTX1 bit 13 and writes a byte to offset 907; console output must be observable.
- **D3 LCD:** LSSA points to guest RAM; 560×160×1bpp = 11200 unpadded bytes; LPICF=8, LVPW=35, LXMAX=560, LYMAX=159, LCKCON=0x80.
- **D4 SPI2/ST:** ET writes SPICONT2=0x2200, SPIDATA2 and SPICONT2=0x2307; 0xAA handshake; PB6/PE3/PK2 GPIO and a state machine cross-checked with Retro68.
- **D7 SPI1/SD:** 16-bit bus, ready/busy and PJ3 CS, PB5 power; do not replace SPI with high-level disk calls.

## 6. Items deliberately not closed

- Exact install location and SHA of the **physical T MAME checkout**: first authorized remote preflight; no exploratory Commander calls.
- Full bitfield set for every VZ peripheral: to be established by that subsystem's contract and tests.
- Built EmuTOS-Dana guest ROM and SHA: **D0.3**, the next task at this document's historical cursor.
- Addresses of all physical Dana Flash/ROM banks: unknown; do not invent cold boot.
- Stable/diag support and EmuTOS startup: **zero functional tests** at the time of this research.

## 7. Conclusion

**D0.2: SPEC_READY (register map/width/critical resets and differences documented).** This status does not approve code or validate hardware functionality.

**Historical next increment: D0.3 — specify the EmuTOS-Dana binary, format/relocation and reproducible recipe without launching compilation on T.** For the current cursor consult [canonical continuity](CANONICAL_CONTINUITY_AND_RULES.md). This document does not authorize D1 or Commander.
