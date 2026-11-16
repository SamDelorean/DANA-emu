> **H6 digital release — 2026-11-16.** Preserve GPT's storage-profile commit `378a1fd`; the same driver now adds optional, bounded **passive PK0/ISP1161/SPI1 observation**. Fourteen installed H6 scenarios, five monitor off/on CPU-journal pairs, original NetIF detached cleanup, save-state, actual MCU suspend/wake and a no-AF_INET/AF_INET6 audit PASS; affected H1–H5 regressions are retained. Installed SHA-256 `73550d0fc28c3189038e39fad2b5a4321dab59da8cfc416317fad18b875f4e41`. [Consolidated evidence and boundaries](H6_INTEGRATION_20261116.md); [native receipts](H6_NATIVE_RESULTS_20261116.json). The signal is **PKDATA.0 at FFFFF441, not PMDATA**; a requested level is not a measured rail or current. No radio, host-network interface, fabricated module response or SDIO-function device is added. Radio sleep/wake/IRQ/reset and physical wiring remain NO VERIFICADO. The original master/atlas/OS3K plan are updated in place with formulas/history preserved. This integral H6 is explicitly user-authorized, with a finite 20-call T budget, and supersedes older pending/authorization cursors below. **Stop after H6; no OS3K port or further product work.**

## H6 software/control evidence, without new measured nets — 2026-11-16

The original NetIF conditionally sets/clears **PK0, PKDATA FFFFF441**, using a CSA size-field condition at FFFFF110. Existing PK DIR/SEL semantics derive a digital pad level; PCB rail-enable continuity, module identity/reset/IRQ and measured current remain unverified. The passive monitor does not create a radio or network connection. The atlas's SPI1 register row is corrected to FFFFF700–F70B; SPI2 ADC/keyboard addresses are distinct. Existing photos, measured nets, formulas and variant history are preserved; the new entry is software evidence, not continuity measurement. See [H6](H6_INTEGRATION_20261116.md).

> **H5 PWM/power digital release — 2026-11-15.** H4 was verified closed/published before H5. The sole `dana-diag` now qualifies PWM1 **REPEAT 1/2/4/8, five-byte FIFO, live counter/period/duty, IRQ/IACK, SYSCLK/CLK32 and active-audio reset/save/recovery**, plus independent **PG1 and raw SPI2 power ADC A4/E4**. **22 installed H5 scenarios PASS**; original UK1.5 consumes changing ADC stimuli, classifies PG1 low/high as 4/0 and writes its charge GPIO. Palm/AlphaWord/81 keys/five chords, EmuTOS, LCD H4, SD, USB/printing, UART/IrDA and H2/H3 affected-path regressions PASS. Installed SHA-256 `6081b48e671cd677a09f3033eb2131a3cfaad8638e3d9ab742c56bf57da6e480`. [Consolidated H5 report and physical boundaries](H5_PWM_POWER_INTEGRATION_20261115.md); [native receipts](H5_NATIVE_RESULTS_20261115.json). Same Drive master: **14 sheets / 1,020 formulas / prior history retained**. Analog audio/charger/battery transfer, PWM2 board routing and unmeasured continuity remain **NO VERIFICADO**; no invented voltage, percentage or stereo channel. This authorized integral H5 supersedes older pending/call-limit cursors below. **Stop after H5; H6 not started.**

## H5 digital pin/protocol evidence; no new physical nets — 2026-11-15

Motorola PB7/PWMO1 and PM5/PWMO2 are MCU functions, not proof of Dana speaker connections. `U_SOUND` output-stage identity/continuity remains unverified. UK1.5 `HwrBatMasterRead` uses PG1 and SPI2 A4/E4; its charge routines use PJ6 direction/data. Real guest instructions and the original firmware now verify those digital protocols independently of pen contact. `U_PWR`, battery reference/voltage transfer, RC/charger/adapter net and physical PWM2 use remain unmeasured. No stereo output, percent battery, AC pin or circuit is invented. See [H5 evidence](H5_PWM_POWER_INTEGRATION_20261115.md). Existing atlas photographs, measured nets and variant history remain authoritative.

> **H4 LCD digital release — 2026-11-15.** The one `dana-diag` now qualifies **560×160 at 1/2/4 bpp**, all 16 Motorola digital densities, LGPMR, the eight-word DMA FIFO, cursor/blink, LCDCLK-derived timing, RMCR, GPIO pad mux, reset and save-state/recovery. **51 installed LCD scenarios plus two explicit RAM 8/16 MiB proofs PASS**; 29 H2 and 75 NOR cases and original UK1.5/AlphaWord/81-key/5-chord/SD/EmuTOS/audio/USB/UART/IrDA/SDL/F12 regressions are preserved. Sole installed SHA-256 `cf25eaafa08201862bd07f7cd3a7af64844f9a79ed6cecca39ddc676336c51a0`. See [H4 integration and limits](H4_LCD_INTEGRATION_20261115.md) and [native receipts](H4_NATIVE_RESULTS_20261115.json). The same Drive master retains **14 sheets / 1,020 formulas / prior history**; the existing atlas references are updated in place. Digital VZ capability, marketed four/sixteen-gray panel capability and unmeasured physical glass remain distinct. **No LCD IRQ or LFRCM is fabricated. Panel optics/bias/contrast wiring and proprietary FRC phase remain NO VERIFICADO.** This user-authorized integral H4 execution/build/install/Drive/publication supersedes older pending and call-limit cursors below. **Stop after H4; H5 is not started.**

## H4 silicon-function evidence, not new measured PCB nets — 2026-11-15

The shared VZ LCD path now qualifies PC0..3 LD0..3, PC4 LFRM, PC5 LLP, PC6 LCLK, PC7 LACD, optional eight-lane PK4..7 LD4..7 and PF0 LCONTRAST multiplexing. CPU GPIO samples, CLK32-measured frame/LACD/contrast periods and native pixel data are recorded in [H4](H4_LCD_INTEGRATION_20261115.md). These manufacturer pin functions and software tests **do not establish Dana pad-to-panel continuity**. The existing V04 atlas `1xiNMO0Oz4Ng6qk2--O6WoNtQ77z9ox0Y` updates its LCD contract row and source references only; photographed nets, topmarks, formulas and variant history are preserved. Panel optics, external serialized contrast/bias/backlight and silicon-specific FRC phase remain unmeasured. The commercial 2002 four-gray / 2003 sixteen-gray matrix is preserved independently of VZ framebuffer depth and NOR/RAM selectors.

> **H3 NOR release — 2026-11-15.** One `dana-diag` now implements the firmware-supported **M29W320DB 4 MiB** and **M28W640HCB 8 MiB** profiles: native programming/erase, correct asymmetric geometry, status/protection, virtual-time operations, persistent working copies and save-state compatibility. **75 NOR cases plus cross-profile rejection PASS**, with the original UK1.5/AlphaWord/81-key/EmuTOS/peripheral regressions and 29 H2 cases preserved. Installed SHA-256 `d2cc5e10c82919c69077521564a59665dff6c654326e263342dd59aeb1569ae0`. **U7 topmark, physical pin wiring and original 4 MiB firmware remain NO VERIFICADO**; this does not certify all three complete machine variants. See [H3_NOR_INTEGRATION_20261115.md](H3_NOR_INTEGRATION_20261115.md) and [machine-readable receipts](H3_NATIVE_RESULTS_20261115.json). The same 14-sheet/1,020-formula Drive master retains its concurrent variant matrix and history. Earlier pending/read-only/call-limit cursors below are historical. H3 is closed within these demonstrated digital profiles; development stops here and H4 is not started.

> **Dana family hardware profiles — 2026-11-15**: correlate **three** commercial board configurations without pretending that PCB IMG_3276/3277 show all of them: Dana 2002 8 MiB SDRAM / 4 MiB NOR / 4 grays; revised Dana 2003 16/8 MiB / 16 grays / SDIO; Dana Wireless 2003 16/8 MiB / 16 grays / SDIO and built-in Wi-Fi 802.11b. Existing U5 Samsung topmark proves only a photographed 8 MiB chip; U7 remains covered by V33 and must not be assigned an arbitrary 4/8 MiB part; the Wi-Fi chipset/interface and SDIO power/IRQ/pins remain **NO MEDIDOS**. [Updated atlas v04](https://docs.google.com/spreadsheets/d/1xiNMO0Oz4Ng6qk2--O6WoNtQ77z9ox0Y/edit), [2023 vendor update](https://www.macworld.com/article/167588/dana-2.html), [Wireless spec](https://www.palminfocenter.com/news/5583/alphasmart-announces-the-dana-wireless/), [SEC](https://www.sec.gov/Archives/edgar/data/1264388/000119312505041716/d10k.htm). Same one emulator, profiles future; documentation only.

# V04 — Conteo óptico de terminales U7 y U1 (26/10/2026)

> **H2 observation — 2026-11-01.** Native UK1.5 PrvSpiSetPol0/1 samples PD0/PD1 as inputs (PDDIR=00 in the observed wait). Earlier output-direction inferences do not establish board continuity. The diagnostic profile explicitly supplies LOW on PD0/PD1; this is a bench stimulus, **not a PCB-net identification**. See [H2 GPIO boundary and native evidence](H2_VZ_INTEGRATION_20261101.md).


## UART/IrDA software routing evidence — 2026-11-01

Original UK1.5 native execution selects **UART2** (`FFFFF910–FFFFF91D`) for its infrared driver, sets IRDAEN and NIPR2=`0320`, emits valid IrLAP XID frames, and reads returned SIR bytes. Motorola defines UART2 RX/TX/RTS/CTS on PJ4–PJ7 and shared UCLK on PE3. These are **silicon and firmware observations**, not measured Dana PCB continuity. The IR transceiver part number, shutdown/control wiring, optical timing and exact package-pin-to-pad nets remain unmeasured. UART1 SIR tests exercise silicon capability only; they do not establish a second board IR port. See [the serial integration evidence](UART_IRDA_INTEGRATION_20261101.md). No existing photographed connection is relabelled as measured.

**Atlas actual:** [DANA_Interconexiones_Hardware_Maestro_v04_20261026.xlsx](https://docs.google.com/spreadsheets/d/1xiNMO0Oz4Ng6qk2--O6WoNtQ77z9ox0Y/edit) (78,473 bytes), en la misma carpeta `ALPHASMART/Dana`. La nueva hoja `13_Conteo_Pines_20261026` documenta el método, comparadores de encapsulado, fotos y hojas de datos. Se preserva v03 como respaldo.

**Resultado de fotografía original `IMG_3276`:**
- **U7** presenta aproximadamente **24 terminales por cada uno de dos lados = 48 pines**, compatible con encapsulado **NOR Flash TSOP-48**, pero la pegatina V33 tapa el fabricante y código JEDEC. Candidatos *sólo por encapsulado* incluyen **SST39VF1601/3201/6401**, **Am29LV320D** y **Am29LV640M**, que comparten 48-TSOP pero ofrecen diferentes geometrías, voltajes/comandos/sectores. **No atribuir uno en particular** ni insertar sus señales en la matriz como continuidad observada.
- **U1** presenta **16 terminales por lado × cuatro = 64**, coincide con **Philips ISP1161A1 LQFP64**. Y1 marcado 6 MHz junto a U1 es evidencia adicional, no una lectura de topmark ni continuidad.
- **U5** SDRAM tiene 27×2=54, confirmado Samsung K4S641632F-TL1L; **U4** 36×4=144, Motorola MC68VZ328PV confirmado por marcado.
- El volcado privado original UK1.5 en único T DIAG mide **`0x5D0000` bytes = 6,094,848 B = 5.8125 MiB**. **Si** es una lectura íntegra de una sola NOR en U7 sin concatenación/reordenamientos, apunta a una capacidad física de al menos 8 MiB/64Mbit. **NO prueba** que ese semiconductor sea de 64 Mbit, y no hay datos para identificarlo como SST o AMD.
- Próxima corroboración segura de U7: orientación de pin1, tensión de VDD/GND, continuidades de /CE,/OE,/WE y DQ/AD con VZ, marcado bajo adhesivo o lectura JEDEC/CFI compatible *sin borrado*. Para U1: XTAL, bus RD/WR/CS, líneas USB y IRQ según datasheet. **No hacer ningún cambio en driver Flash o ISP1161 basado exclusivamente en encapsulado.**

**Fuentes externas:** [Philips ISP1161A1 Rev03 (LQFP64)](https://www.mouser.com/datasheet/2/302/ISP1161A1-03-196942.pdf), [AMD Am29LV320D (48 TSOP)](https://www.insidegadgets.com/wp-content/uploads/2012/12/AM29LV320D.pdf), [AMD Am29LV640M (48 TSOP)](https://www.farnell.com/datasheets/72290.pdf), [SST39VF6401 48-TSOP pinout](https://dtsheet.com/doc/257118/sst-sst39vf6401), original board photographs saved in Drive by the project owner. No source emulator/operative/firmware modifications.

---

# Actualización documental — fotografías PCB verificadas (v03, 26/10/2026)

**EXCEL MAESTRO VIGENTE:** [DANA_Interconexiones_Hardware_Maestro_v03_20261026.xlsx](https://docs.google.com/spreadsheets/d/1JvpHPIGhImqaCCzvyNUnGwGI69kJyD7q/edit), 74,848 bytes, 13 hojas, conservado en `ALPHASMART/Dana`. Versiones v01/v02 archivadas para comparación histórica.

**Evidencia fotográfica preservada en la misma carpeta:**
- [Vista original U1, U7, U5, Y1, J100](https://drive.google.com/file/d/1uCFZGQcwV3yqOmdih5TmbBwNeVggHoqO/view) (foto IMG_3276 del usuario).
- [Vista original U5, U4, conectores](https://drive.google.com/file/d/180r7qgo_9WoWDuZ6OjgcQoaMyTMhTdNA/view) (foto IMG_3277 del usuario).

**Corrección crítica de identidad física:** `U4` es el **Motorola DragonBall VZ MC68VZ328PV**, identificado por grabado legible en la foto. Sufijo fabricante **PV = 144-pin TQFP** (manual MC68VZ328UM Table 20-1); por ello la hoja `02_VZ_TQFP144` **sí corresponde a la variante soldada** y ya no está pendiente el encapsulado de CPU. Ninguna fotografía confirma por sí sola la continuidad de cada pin a una red.

**U5** lleva grabado legible `Samsung K4S641632F-TL1L`: SDRAM **64Mbit/8MiB por chip**, TSOP-II 54. Fotos confirman un U5 de esta capacidad en la cara visible; no extrapolar a todas las variantes/revisiones de Dana.

**U7** es un encapsulado de dos hileras tipo TSOP **con pegatina V33 ocultando el topmark**. Por ubicación y morfología es el principal **candidato a ROM/Flash**; **NO confirmado el semiconductor exacto**. `V33` no es un número de parte, JEDEC ni una capacidad; fabricante, pin-count exacto, geometría, tensión y pines de control quedan como pendientes. La hoja `11_ROM_Flash_Pendiente` conserva expresamente los campos sin inventar números de pin.

**U1** es QFP cuya marca no se lee, junto a cristal Y1 marcado **6.0MHz**. Es **candidato razonable** al ISP1161A1, no una identificación certificada. Pinout de `03_ISP1161_LQFP64` sigue siendo ficha de fabricante sin continuidad confirmada U1↔VZ.

**J100** son pads 2×4 sin poblar, relevantes para futura investigación de RESET/EMUBRK/UART: **NO asignar señales de bootstrap por cercanía** sin medir conectividad.

La nueva hoja `12_PCB_Fotos_20261026` contiene por elemento: designador U/J/Y, marcado y encapsulado visibles, nivel de certeza, usos del emulador, pruebas pendientes, fotos persistidas y datasheets; se corrigieron `00_Portada`, `01_Inventario`, las notas de pines de CPU/SDRAM/USB, `06_Memoria_y_CS`, `08_Continuidad`, `09_Fuentes` y `11_ROM_Flash_Pendiente`. El atlas mantiene separadas **evidencia del topmark**, **conexión lógica software** y **continuidad real de PCB**. Sin cambios en código del emulador, ROM ni binario operativo.

---

# Dana hardware interconnection atlas — master workbook v02 (2026-10-26)

**CURRENT MASTER — external SDRAM chip identified and full pinout integrated:** [DANA_Interconexiones_Hardware_Maestro_v02_20261026.xlsx](https://docs.google.com/spreadsheets/d/1jdLbavE8u-VQ3hVlcAYBCqBryHYAsOM5/edit). Google Drive `ALPHASMART/Dana`, 70,099 bytes, 12 worksheets. **Older v01 preserved as an archival baseline, not current master.**

## New manufacturer-grounded external-memory mapping

- **Samsung `K4S641632F-TL1L`** — exact RAM part identity provided by board owner. Datasheet: [Samsung F-revision pinout, 54-pin TSOP-II, top view, p. 4](https://www.alldatasheet.com/html-pdf/37101/SAMSUNG/K4S641632F-TL1L/1031/4/K4S641632F-TL1L.html), [organization, ordering code and refresh, p. 3](https://www.alldatasheet.com/html-pdf/37101/SAMSUNG/K4S641632F-TL1L/772/3/K4S641632F-TL1L.html).
- Physical manufacturer package: **TSOP-II 54-pin, 0.8 mm pitch**; **64 Mbit = 8 MiB per IC = 4 banks × 1M words × 16 bits**. **3.3 V** JEDEC supply and LVTTL I/O. `TL1L` listed **100 MHz CL3**, with 4K refresh cycles per 64 ms. Quantity actually soldered to Dana's PCB remains to be physically checked; don't infer 16MiB or a second chip from emulator software profiles.
- **Complete all 54 pin positions recorded** in new `10_SDRAM_K4S641632F` worksheet (DQ0–15, A0–11, BA0–1, CLK/CKE, CS/RAS/CAS/WE, LDQM/UDQM, every supply/ground and NC). Each pin includes type, function, candidate MC68VZ328 logical connection, any TQFP reference pin, evidence status and Samsung URL. **Candidate VZ-to-RAM connections are not PCB continuity measurements.** Key high-value exact RAM pins: CLK38, CKE37, /CS19, /RAS18, /CAS17, /WE16, LDQM15, UDQM39, BA0=20, BA1=21, A10/AP=22, DQ0=2 and DQ15=53.
- `01_Inventario` now names U_SDRAM; `04_Interconexiones` contains 54 new pin-level candidate nets (from 90 to **144**), `06_Memoria_y_CS` contains 11 additional records (14 to **25**), `08_Continuidad` has 9 new specific physical checks (20 to **29**), `09_Fuentes` has 4 new records (10 to **14**), and `00_Portada` counts have been updated. A small manufacturer organization/capacity formula confirms **8,388,608 bytes per single IC**.
- **ROM/Flash is still physically unidentified.** New `11_ROM_Flash_Pendiente` explicitly lists **13** groups of part-number/package/JEDEC, address/data/control, CS, voltage and bootstrap checks. The ROM image or memory address map does **not** prove the actual NOR chip model, number of ICs, pinout, or manufacturer. No invented Flash numbers have been entered. Obtain the actual **topmark/complete part number** and picture of pin1 before generating that full physical pinout.
- Original MC68VZ328 datasheet [NXP](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf) documents logical SDRAM signals PM0/SDCLK, PM1/SDCE, PM2/DQMH, PM3/DQML, PB1/SDWE, PB2/RAS0, PB4/CAS0, MA bus, while the logical bus remains multiplexed; original VZ package for Dana requires verification. The sheet marks every inferred pair **NO_MEDIDA**. Signals BA0/BA1 and CKE are explicitly not given an invented VZ physical pin.

**Implementation rule:** the semiconductor identification makes the RAM organization and manufacturer pin functions demonstrable, **not** the PCB wiring; never treat a conjectural direct VZ DQn ↔ Samsung DQn path as measured copper. Work on the one main-branch DANA emulator, not duplicate DIAG instances.

---

# Historic v01 reference — superseded by v02

**Historical first version (kept for traceability):**

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
