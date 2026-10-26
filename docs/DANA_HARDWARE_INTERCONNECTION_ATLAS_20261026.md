# Dana hardware interconnection atlas — single reference Excel v01 (2026-10-26)

**Primary electrical engineering master workbook, already created and verified in the project's actual Google Drive folder `ALPHASMART/Dana`:**

[**DANA_Interconexiones_Hardware_Maestro_v01_20261026.xlsx**](https://docs.google.com/spreadsheets/d/11NNx7sgBCp7KnJknjscA-lvQIRGcTNNZ/edit)

## Why this file exists

Use the same physical-IC/interconnection method as [AS2K v26](https://docs.google.com/spreadsheets/d/1o3yZ06mL5GG0HwsQrK-4GIzR7WUWRZhC/edit) and [ASPRO interconnections v01](https://docs.google.com/spreadsheets/d/1ohGHsS6CzD_Ij_C85zJihLjJgTghxwpe/edit). This is the **single Dana board connectivity workbook**, not a duplicate MAME controller or a new unbounded task campaign.

Separate ***official pin function*** from ***original ROM's demonstrated software usage*** from ***actual physical net continuity on Dana's PCB***. A functional MAME emulator test or a data sheet alone **never closes continuity**. Any unknown IC or pin mapping is labelled rather than populated with an invented value.

## Workbook sheets and contents

1. `00_Portada`: engineering summary, provenance standards, part-package warning.
2. `01_Inventario`: 18 components/functions grouped by physical IC, socket and oscillator; exact Flash/SDRAM topmarks still unknown.
3. `02_VZ_TQFP144`: **144 manufacturer-defined pins** from MC68VZ328UM Fig 20-1 (TQFP **reference only**). **The actual Dana CPU package has not been verified.** These pin numbers **must not be reused for MAPBGA** without a separate pin map.
4. `03_ISP1161_LQFP64`: **64 manufacturer-defined LQFP64 pins**, Philips Rev03 Fig 7, including bus D[15:0], A0/A1, RD/WR/CS, INT1/2, DREQ/DACK, two downstream differential pairs, upstream pair and 6MHz typical external oscillator reference. **Physical PCB wiring remains unmeasured**.
5. `04_Interconexiones`: **90 explicitly qualified candidate logical nets**, with source/destination, pin, direction, logical voltage, evidence, PCB status, emulator implementation, ROM/MMIO, verification required and URL. All `NO_MEDIDA` are **not certified physical traces**.
6. `05_Bootstrap`: VZ EMUBRK/RESET/UART1/UART2/IBUFF, electrical pad qualifications. No fictional USB bootstrap or physical UART test claim.
7. `06_Memoria_y_CS`: VZ bus, CSA/B/C/D, SDRAM mux address, RAS/CAS/WE/DQM, NOR and USB decoding.
8. `07_Registros_ROM`: **20 groups** link chips/signals to MMIO/register interfaces and ROM behavior.
9. `08_Continuidad`: **20 bounded, nondestructive physical measurements** to close board nets (topmarks; SD0/1 PD2/3; USB bus/CS/IRQ/DMA; clocks and bootstrap).
10. `09_Fuentes`: **10 source references** including official manuals, exact emulator code and AS2K/ASPRO methodological templates.

Hardware documentation:
- Motorola [MC68VZ328UM](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), ch.2, 4, 10, 13, 17, fig.20-1: pins/internal GPIO SPI1/SPI2 bootstrap clock MMIO.
- Philips [ISP1161A1 Rev03](https://www.mouser.com/datasheet/2/302/ISP1161A1-03-196942.pdf), fig.7, ch.6,8-10,13: all 64 LQFP pins, HC/DC bus, USB pins, FIFO/PTD.
- Original Dana UK1.5 ROM Ghidra call graph [`UK15_ROM_BOOT_SD_SPI_GHIDRA_PANORAMA_20261026.md`](UK15_ROM_BOOT_SD_SPI_GHIDRA_PANORAMA_20261026.md): `PrvSpiSetPol0/1`, measured CPU PD2/PD3 input behavior, PD0/PD1 output; physical card sensor identity still unknown.
- Emulator [`alphasdana.cpp`](../src/mame/skeleton/alphasdana.cpp): logical implementation of two SD-image slots, SPI1, GPIO, NOR/SDRAM and ISP1161; no inference from emulator alone to verified PCB copper.

## Project execution rule

**Read this workbook before adding peripheral chips, net connections, MMIO aliases, UART bootstrap circuitry or forcing SD pin levels.** Identify the actual part and pin package, correlate manual pin function with ROM usage, then explicitly check physical continuity if the conclusion requires a real Dana board connection. Do not repeat the previous one-register-at-a-time ISP1161 error cycle.

Only update an existing row from `NO_MEDIDA` to `MEDIDA_PCB` when measured continuity/PCB evidence is recorded; preserve the primary source and any contradictory evidence.

**Snapshot:** v01 created 2026-10-26; uploaded and metadata-verified as a **52,913-byte .xlsx file** in `ALPHASMART/Dana`. No changes to the user's existing AS2K or ASPRO spreadsheets, original Dana ROM, sole DIAG, or installed operative emulator.
