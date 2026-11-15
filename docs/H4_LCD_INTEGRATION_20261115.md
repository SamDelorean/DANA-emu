# H4: MC68VZ328 LCD integration and native qualification

H4 is functionally qualified for the documented digital LCD capabilities in the
single canonical `dana-diag`. Real 68000 instructions generate guest framebuffers
and configure 1, 2 and 4 bpp; DMA consumes the same SDRAM storage, and MAME presents
completed controller frames. The existing UK1.5/AlphaWord, EmuTOS and peripheral
campaigns pass. **This is not certification of an individual panel's optical or
electrical characteristics.** H5 was not started.

## Installed identity and continuity

| Artifact | SHA-256 |
|---|---|
| Sole installed `runtime/diag/bin/dana-diag` | `cf25eaafa08201862bd07f7cd3a7af64844f9a79ed6cecca39ddc676336c51a0` |
| `src/mame/skeleton/alphasdana.cpp` | `1b97c2dc4610d3681c09517114106e85f22d851d07953193edb192eec3f8c3f6` |
| Integrated companion `alphasdana_lcd.h` | `c5aea1caef43bdd2f1243d3581967333a6e2854c557daa9065e373107191eda3` |
| H2 companion, limited LCD clock/pad hooks | `8e5e1dd0c7a60e345aa104bc6f25018aff451f0290b45e8840ea505a4748b5a5` |
| Unchanged NOR companion | `01839189766e59e3acedc21204312227de03087016c3caefd1438d2dc242a3f0` |
| Unchanged UART companion | `bf9eddcc21c359f1b7735b5739bc97de5dbfd6769a328755a4321d5cf2585803` |
| Pre-H4 operative, retained compressed privately | `d2cc5e10c82919c69077521564a59665dff6c654326e263342dd59aeb1569ae0` |

Work started on clean `main` at H3 commit
`9536a8d08b341387fdd89c92fe663af05685c8dc` in
`/home/spc/Projects/alphasmart/DANA-emu` on `spc-HP-t640-Thin-Client`.
Only the existing MAME source cache/build artifact was used, with Clang 21.1.8;
incremental compilation and link returned 0. After qualification, the result was
installed atomically at the same operative path. No branch, clone, worktree,
alternate emulator installation, tool installation or host-system reconfiguration
was created. Final whitespace cleanup removed one trailing blank line from the H2
header without changing C++ tokens or the tested executable; its compiled-header
SHA is retained separately in the receipts. Original UK1.5 remained unchanged, SHA-256
`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.

## Manufacturer contract and reused components

Primary authority is [MC68VZ328UM](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf),
chapter 8, tables 8-1 through 8-20, chapter 9 and section 19.3.13, read together with
[MC68VZ328UMAD](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf).
The downloaded manuals have SHA-256
`6db7d790ca690d312959a9aaa6391db2525be5a3aa34ada99d720334e400b842` and
`f699ae346e0fb1998a3148c2adb37beb34ea64d124dccf7629b6930e2c0d9b6f`.
The addendum removes color-STN claims: this is a monochrome LCD controller.

The implementation reuses the existing driver, H2 PLL/LCDCLK and GPIO graph,
chip-select/SDRAM storage, MAME scheduler/save manager/screen infrastructure, H3
NOR socket and the qualified 68000 diagnostic encoder/bootstrap. The pinned MAME
`mc68328lcd` and classic/EZ scanout were consulted; an EZ controller was not
substituted for VZ. Existing Ghidra LCD/cursor results were reused, including
UK1.5's real `LPICF=08`, `LVPW=23`, `LXMAX=0230`, `LYMAX=009F`, `LRRA=0050`,
`LCKCON=82` initialization and cursor accesses. No ROM import or global Ghidra
reanalysis was needed. No POSE/Retro68 GPL implementation was copied.

### Registers

All addresses below begin `FFFF`; existing and added handlers retain M68000
big-endian word/byte lanes and participate in save-state.

| Register/address | Reset; defined bits | Integrated behavior |
|---|---|---|
| LSSA `FA00–03` | `00000000`; `FFFFFFFE` | Even start address; high address bits fixed over an image, 20-bit scan counter |
| LVPW `FA05` | `FF`; `FF` | Word stride independent of pixel depth |
| LXMAX/LYMAX `FA08/0A` | `03F0/01FF`; `03F0/01FF` | Actual pixel width and height-minus-one |
| LCXP/LCYP/LCWCH `FA18/1A/1C` | `0000/0000/0101`; `C3FF/01FF/1F1F` | Position, zero-size disable, black/white/reverse/transparent cursor |
| LBLKC `FA1F` | `7F`; `FF` | Frame-counted blink, half-period BD+1 frames |
| LPICF `FA20` | `00`; `0F` | 1/2/4 bpp and 1/2/4/8 data lanes; GS=3 remains reserved |
| LPOLCF `FA21` | `00`; `0F` | Digital data/LLP/LFRM/LCLK polarities |
| LACDRC `FA23` | `00`; `FF` | Frame/line source and full seven-bit toggle divisor |
| LPXCD `FA25` | `00`; `3F` | LCDCLK/(PCD+1), preserving fractional frequency |
| LCKCON `FA27` | `00`; `FF` | LCDON; remaining seven bits are manufacturer-defined temporary storage |
| LRRA `FA28–29` | `00FF`; `03FF` | 16-bit VZ refresh adjustment, not EZ's byte register |
| LPOSR `FA2D` | `00`; `0F` | Pixel panning independent of bpp |
| LGPMR `FA33` | `84`; `FF` | Two selectable intermediate digital densities in 2 bpp |
| PWMR `FA36–37` | `0000`; `07FF` | PF0 LCONTRAST, LLP/pixel/LCD clock sources, 8-bit PWM and saved phase |
| RMCR `FA38` | `00`; `80` | Frame-boundary self-refresh entry/exit |
| DMACR `FA39` | `62`; `F7` | Eight-word FIFO burst length and low watermark |

**No LCD IRQ/status register is defined by this VZ interrupt controller.** H4
creates no interrupt source, vector or acknowledgement register. `LFRCM@FA31`
was removed on VZ and remains absent. Reserved DMA configurations are not coerced
into a fabricated successful configuration; qualified values obey table 8-20.

### Scanout, timing and grayscale

The DMA master reads the existing RAM/physical CS decode into the eight-word FIFO.
The shift path consumes these captured words, MSB first, with word stride,
panning, big-endian data and the documented fixed upper image address bits.
There is no second guest framebuffer region or host-written substitute image.
Tests modify the framebuffer using guest instructions while scanout is running.
Physical-mode tests also read upper SDRAM and distinguish 8/16 MiB aliasing.

The virtual-time line/frame periods follow Motorola's formula:

`Tframe = (12 + width + LRRA) × (LYMAX + 1) × (LPXCD + 1) / LCDCLK`.

Changing the H2 PLL/divisors retimes the beam and FIFO deadline; disabling the PLL
freezes their phase until the existing interrupt-driven wake sequence recovers it.
CPU STOP alone does not stop independent LCD clocks. MAME screen delivery has a
1 Hz backend floor for programmed frame periods of at least one second; the
independent LCD scan events retain the full register-derived period and hold the
completed output between guest frames. Native qualification below covers the
documented Dana geometry and the tested clock configurations. LCDOFF halts before the next
fill DMA. RMCR enters/exits at a frame boundary: data/shift clock become inactive
while line/frame signaling continues. Completed digital frames are handed to
MAME/SDL, so host presentation does not combine cursor-blink phases from different
guest frames. The reset/off host delivery cadence is not a running LCD clock.

Motorola density codes 0..F are respectively:
`0, 1/8, 1/5, 1/4, 1/3, 2/5, 4/9, 1/2, 5/9, 3/5, 2/3, 3/4, 4/5, 7/8, 14/15, 1`.
They are **not** an arbitrary linear `code/15` palette. At 2 bpp, pixels 0/3 are
white/black and 1/2 use LGPMR's low/high nibbles. At 4 bpp the pixel selects the
density directly. Cursor reverse acts on pixel bits before palette mapping.
The preview represents these digital duties between the existing display
endpoints; it does not predict the unknown glass luminance/gamma/bias response.

PC0..3 carry LD0..3, PC4 LFRM, PC5 LLP, PC6 LCLK and PC7 LACD. The eight-lane
controller mode additionally multiplexes PK4..7 onto LD4..7. PF0 can select
LCONTRAST. GPIO selection retains its existing precedence. These are MCU pad
functions, **not newly measured Dana PCB nets**. The manual has conflicting
descriptive lane-order prose; the illustrated MSB-first mapping and previously
qualified framebuffer orientation are retained without inventing board reversals.

### Hardware configurations

| `LCD_PANEL` setting | Commercial documentation | Digital qualification |
|---|---|---|
| 0: Dana original 2002 | 8 MiB RAM / 4 MiB NOR; 560×160, four grays | Same VZ registers; 1/2/4-bpp controller capability remains separate from installed glass |
| 1: Dana revised 2003 | 16/8 MiB; 560×160, sixteen grays | Same controller; all modes/densities qualified |
| 2: Dana Wireless 2003 | 16/8 MiB; 560×160, sixteen grays | Same controller; radio/SDIO untouched |

This LCD documentation-profile option is independent of PHYSRAM, NOR capacity and
firmware selection. It is not a newly certified complete-machine variant selector.
In particular, running digital 4 bpp with setting 0 does not certify sixteen
optical gray levels on original Dana glass. The existing [variant sources and
matrix](DANA_EMU_INCREMENTAL_WORK_PLAN.md#dana-hardware-variants--one-emulator--three-machine-profiles-2026-11-15)
remain authoritative for marketed specifications.

## Native results and regressions

See [machine-readable evidence](H4_NATIVE_RESULTS_20261115.json). All final checks
use the installed SHA above; no host memory/MMIO writes stand in for CPU tests.

| Campaign | Result |
|---|---|
| Installed LCD | **51/51 scenarios PASS**, every captured 560×160 surface compared byte for byte |
| Explicit physical SDRAM selection | **2/2 PASS**, 8 MiB alias and independent 16 MiB addresses checked by 68000 |
| Candidate LCD | 45 initial final-build runs plus eight strengthened checks; see harness correction below |
| Existing H2 | **29/29 PASS**, including PLL, IRQ, watchdog, sleep and save-state |
| Existing H3 NOR | **41 + 34 = 75 PASS**, 8/4 MiB profiles, protection, timed operations, persistence and state guards |
| UART/IrDA | **9 targeted native regressions PASS**, both UARTs, SIR, dual source, state/clock/IRQ |
| USB | HC printer, DC, faults, PTD bus and authentic AlphaWord print **PASS** |
| Original guests/UI | UK1.5/AlphaWord, 81/81 keys, five chords, pen, RTC/calendar, two SDs/persistence, PWM1/audio, EmuTOS, SDL/F12 and sound UI **PASS** |
| Original power cycle | UK1.5 suspend/wake and CPU recovery **PASS** |
| Installed checks after replacement | **8/8 PASS**: both NOR profiles, H2 sleep/state, UART dual, USB HC, original printing, original power and SDL/XTest/F12 |

The candidate regression orchestrator completed **48 campaign/check invocations**;
this count includes composite campaigns and the existing static cursor test, and
must not be described as 48 independent CPU-native tests.

Measured by CPU reads of CLK32 Timer1 and real dedicated GPIO outputs:

- Three frame periods: expected approximately 1,237 CLK32 ticks at 79.46993865 Hz.
- LCONTRAST LCD/pixel/line-source periods: measured 64/65/2639 ticks, expected
  64.7589/64.7589/2638.9249 within the native measurement tolerance.
- LACD line/frame-source periods: measured 1319/13195 ticks, expected
  1319.4625/13194.6245.
- Native paired pin samples verify LPOLCF changes; GPIO/8-lane LCD mux and all
  four cursor modes, including 2-bpp reverse before LGPMR, pass.

**Harness correction retained transparently:** the initial `ram8` label did not
explicitly select PHYSRAM and therefore was not proof of 8 MiB. The final harness
sets that input explicitly and the guest checks the +8 MiB alias. The 16 MiB case
checks two independently written locations. Both strengthened installed runs pass;
earlier raw receipts are annotated rather than silently relabelled. Initial
bring-up also corrected the observer output binding, a diagnostic branch encoding,
test panning allocation, and completed-frame delivery before final qualification.

Private evidence remains in `local-evidence/runtime-compare/h4-20261115`, plus the
existing keyboard, serial, USB and calendar evidence families under their H4 case
prefixes. Vendor images, Ghidra exports, saved sessions, audio, screenshots and
print job content remain private. The authentic 10,409-byte AlphaWord PostScript
regression retains SHA-256
`792013e870ceeba0de25c1476b0132286befcca35da05478b2acfcb4dfd8e6b8`.

Reproduction uses the existing build and one process at a time:

```sh
python3 tests/run_lcd_campaign.py --prefix YOUR_UNIQUE_CASE --installed
python3 tests/run_lcd_regressions.py --prefix YOUR_UNIQUE_REGRESSION --installed
```

The new registers, FIFO, partial line/output surfaces, beam origin/fractional
phase, DMA counters, self-refresh, blink/frame state and contrast clock phase are
serialized. Native save/load and save/load while PLL-suspended pass. Compatibility
with historical versions' differently structured save-states is not promised.

## Physical boundaries and closure

**NO VERIFICADO:** glass identity and optical four/sixteen-level response,
LCD bias voltages, external contrast IC/serial protocol and exact board wiring,
backlight electrical behavior, semiconductor-specific spatial/temporal FRC phase,
and cycle-by-cycle external-bus arbitration/electrical setup/hold measurements.
The manual specifies digital density ratios but not its proprietary FRC phase;
the emulator uses a deterministic density sequence and does not claim a measured
silicon waveform. Functional DMA/refresh timing is qualified; this is not a
gate-level or analog certification.

UK1.5/EmuTOS establish existing GPIO panel/control use, while PF0's documented VZ
PWM is distinct from Dana's externally serialized contrast path. H4 does not
invent a voltage model, replace that external device with an SDL filter, claim
new physical continuity, or turn outstanding USB Computer/Beam/SDIO/Wi-Fi
qualification into PASS. There is no LCD interrupt to emulate.

The same Drive master `1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l` is updated in place:
**14 sheets, 1,020 exact formulas, all prior history and variant entries preserved**;
H4 is appended as history row 55. Readback SHA-256
`0a79e116047652a7873056771ac5446deede1f697955b8a1a1b340ebd8e7bf76`.
The existing atlas `1xiNMO0Oz4Ng6qk2--O6WoNtQ77z9ox0Y` retains its 14 sheets,
two formulas and physical-net data; only the LCD contract/reference entries are
updated. Readback SHA-256
`6884a26bdf9f11c6265734c35abae6c9923a6c09e906dbb864949fb3573683ed`.
Both returned file bytes were checked after upload. No replacement master exists.

**H4 digital functional closure: PASS within these documented and demonstrated
boundaries. Development stops at H4; H5 is not started.**
