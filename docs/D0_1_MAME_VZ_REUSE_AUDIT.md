# D0.1 — MAME / DragonBall / NEO / Dana reuse audit

**Static-research closure document — 2026-10-13.**

**Status: SPEC_READY (documentary evidence completed; NO functional PASS).** This audit answers D0.1's single question: *which emulation code already exists, what can be reused, and what must still be modeled for Dana?* Nothing was implemented, compiled or executed on T; **the actual T checkout path/revision remains unverified**, so the first implementation preflight must compare it with the SHA pinned here. GitHub source availability is not evidence that the code builds or boots.

## 1. Source baseline

| Role | Repository | Immutable revision examined | Availability |
|---|---|---|---|
| **Intended MAME codebase** | [SamDelorean/mame-as3k](https://github.com/SamDelorean/mame-as3k) | **c4e48388ca620472643110db2941ce70aa5f3c07**, master at lock time | Available on GitHub; T tree/checkout/build version: **UNVERIFIED** |
| Official MAME cross-check | [mamedev/mame](https://github.com/mamedev/mame) | **98e60b54d0718171636f50e39794d861564aac08** | Accessible sources; not automatically the T baseline |
| Dana board reference | [davidgiven/emutos](https://github.com/davidgiven/emutos) | **9c42ef0f2c2fa9d1e217fced9da68901b2326e8b** (dana branch) | Port source, **not** locally built/verified guest firmware |
| VZ SoC POSE model | [cloudpilot-emu/pose-original](https://github.com/cloudpilot-emu/pose-original) | **97b10711fe4ca50c1bd47072378eaab26ba8e81d** | GPL source, behavioral reference |
| Dana-specific POSE emulation | [csnover/Retro68](https://github.com/csnover/Retro68) | **d917b67b16bef7bcf5c75a74f617710c32addcbc** | GPL source, ST and board behavioral reference |
| Firmware-first NEO (not MAME) | [ioma8/neo-re](https://github.com/ioma8/neo-re) | **732814871fe493e80ed1ab1f959d8dad174ee540** | Readable Rust source; reuse license not identified |

Provenance manifest: [research/sources.lock.json](../research/sources.lock.json); earlier NEO audit: [docs/NEO_NEO2_REUSE_AUDIT.md](NEO_NEO2_REUSE_AUDIT.md).

**No MAME version number was guessed:** the pinned **commit** is the reproducible reference. The version/build/worktree on T must be checked in the first authorized preflight; a separate exploratory Commander call is unnecessary.

## 2. MAME base: components and observed facts

### A — 68000 CPU: REUSABLE

**File:** [src/devices/machine/mc68328.h](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.h), lines 90–139. **mc68328_base_device** derives from MAME's **m68000_device** CPU core; this is the instruction/state/interrupt-acknowledgment infrastructure to study.

**Conclusion:** do NOT write another 68k CPU or adopt the NEO Rust interpreter as a separate engine. Preserve MAME's CPU, exception and debugger contracts. 68000 instruction-set compatibility does not imply equivalent reset/IRQ/MMIO behavior.

### B — DragonBall MC68328/MC68EZ328 SoC driver: ADAPTATION BASE, NOT DROP-IN VZ

**Files:**
- [mc68328.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.cpp), lines 45–46, 97–200 and 202–330.
- [mc68328.h](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.h), base definition, callbacks and specialized classes.

**Explicitly defined device types:** **MC68328** and **MC68EZ328**. No **MC68VZ328** device registration was found in the audited tree.

Existing MAME subsystems contribute shared operations and architecture:
- Internal clock/PLL/IRQ MMIO window and GPIO; handlers distinguishing 8- and 16-bit accesses and CPU maps.
- Timer1, UART, LCD control, RTC and GPIO/SPI callbacks.
- MAME framework scheduler, timers and save-state support. Implementing any register requires a VZ comparison **bit by bit**, not extrapolation.

**Concrete direct-reuse risk:**
- In `mc68328_base_device::base_internal_map()` (around line 170), registers **0x800/0x802** connect to **SPIM**, whereas the MC68328 variant maps **SPIS** at **0x700** (around line 309 in mc68328.cpp).
- In [EmuTOS-Dana bios/dana.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c), lines 84–91, **SPI1** uses **0xFFFFF700–0xFFFFF70A**, and **SPI2** uses **0xFFFFF800/0xFFFFF802**. These assignments cannot automatically inherit MC68328/EZ mapping.
- VZ has additional/different chip-select resources, DRAM control, GPIO, two UARTs, two SPI controllers and timers. Merely renaming the device type is insufficient.

**D0.1 decision:** assess factoring/reusing MAME handlers **without altering existing MC68328/EZ behavior**. D0.2 defines registers that match, differ or are new; D1 determines C++ design and submits it to tests.

### C — Existing LCD: reusable infrastructure, NOT a ready-made Dana renderer

**Files:**
- [mc68328lcd.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/video/mc68328lcd.cpp) (BSD-3-Clause; MC68328_LCD device).
- [mc68328lcd.h](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/video/mc68328lcd.h).

Provides **flm_w, llp_w, lsclk_w, ld_w, lcd_info_changed and video_update**; handles bitmap, palette, dimensions and scanlines from SoC signals. This connection pattern can be adapted to VZ **if its LCD DMA/register behavior produces compatible signals**. Dana's actual screen is **560 × 160, 1 bpp**, and guest firmware configures its framebuffer via **LSSA**.

**What D3 must prove:** visible output is read from guest RAM according to VZ register/address configuration; displaying a host-generated 560×160 image is insufficient.

### D — MAME Palm driver: CPU/LCD/input integration pattern

**File:** [src/mame/palm/palm.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/palm/palm.cpp), around lines 575–690.

Useful examples include a CPU wired into `machine_config`, `address_map`, GPIO/SPI/LCD callbacks, input ports, `screen_update`, serializable state and separate peripherals. **Do not** treat Palm GPIO wiring as Dana wiring; `palm.cpp` is an architecture example, not a Dana driver.

### E — AlphaSmart 3000 driver: NOT NEO/NEO2

**File:** [src/mame/skeleton/alphasma3k.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/skeleton/alphasma3k.cpp), lines 1–9 and 97–121.

This **AlphaSmart 3000** skeleton uses **MC68EZ328**, a provisional 16 MHz configuration and **two KS0066/HD44780 controllers**; it is neither the MC68VZ328 device nor Dana's LCD. It explicitly records an IPL failure. Do not treat that boot behavior as a Dana qualification criterion.

[hash/alphasmart_kapps.xml](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/hash/alphasmart_kapps.xml) catalogs **System 3/NEO SmartApplets**, not hardware emulation.

## 3. Non-MAME references and their roles

### F — Original POSE: internal VZ design

[EmRegsVZ.cpp](https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Hardware/EmRegsVZ.cpp) contains **kInitial68VZ328RegisterValues**, with explicit SCR/chip-select/PLL/IRQ/GPIO initial values and LCD, SPI, UART and timer routines. [M68VZ328Hwr.h](https://github.com/cloudpilot-emu/pose-original/blob/97b10711fe4ca50c1bd47072378eaab26ba8e81d/SrcShared/Palm/Platform/Core/Hardware/IncsPrv/M68VZ328Hwr.h) provides offsets and bitfields.

**Proper use:** cross-check datasheets and existing tests, extracting read/write/side-effect contracts for D0.2. **Do not** assume POSE is cycle accurate or silently copy GPL code into BSD-licensed MAME files.

### G — Retro68/POSE Dana: ST microcontroller and board logic

- [EmRegsVZAlphaSmart.cpp](https://github.com/csnover/Retro68/blob/d917b67b16bef7bcf5c75a74f617710c32addcbc/PalmUtils/poser/SrcShared/Hardware/EmRegsVZAlphaSmart.cpp), 346 lines: derives from EmRegsVZ; wires **GetSPISlave**, GPIO E/K, ADS784x ADC and ST slave, display/backlight signals, IRQ conditions and SPI control.
- [EmSPISlaveSTMicro.cpp](https://github.com/csnover/Retro68/blob/d917b67b16bef7bcf5c75a74f617710c32addcbc/PalmUtils/poser/SrcShared/Hardware/EmSPISlaveSTMicro.cpp), 448 lines: **DoExchange, NeedsExchange, PortKOutputEnable, ButtonEvent, KeyEvent and ProcessVersionCommand**. Implements a state machine for transactions, events and keyboard codes.

**Value:** do not reconstruct ST blindly. Compare the protocol to actual guest behavior in [bios/dana.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c). Source file headers indicate **GPL-2.0-or-later**: a technical reference, not literal copy material before a licensing/distribution decision.

### H — EmuTOS-Dana: observed guest access evidence

[bios/dana.c](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c), approximately 677 lines; GPL-2.0-or-later. Defines 0xFFFFFxxx and 0xFFFFFAxx VZ MMIO addresses and actual LCD, SPI1-SD, SPI2-ST, PLL, Timer1, UART1 and GPIO sequences. The guest initializes ST and polls the keyboard.

**Proper use:** fixtures based on observable transactions. Avoid reusing TOS routines inside the MAME emulator, since doing so would conceal MMIO failures.

### I — Firmware-first NEO outside MAME

[neo-re / alpha-emu](https://github.com/ioma8/neo-re/tree/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu) models NEO hardware and executes System 3 firmware using a Rust `m68000` interpreter. It provides **VZ CPU, ROM state, MMIO, clock, LCD captures, input and headless-testing** references; see [NEO/NEO 2 audit](NEO_NEO2_REUSE_AUDIT.md).

**Fundamental differences:** NEO uses a keyboard matrix and external LCD controllers; **Dana** uses ST/SPI2 and the 560×160 VZ-integrated LCD. NEO external-controller offsets do not apply to Dana. No reuse license was identified in the inspected Cargo.toml or root directory listing: **read only** pending verification.

## 4. Reuse decision matrix

| Block | Reusable MAME infrastructure | Dana/VZ-specific extension required | Priority |
|---|---|---|---|
| 68000 CPU | Engine, exceptions, debugger | CPU mapping and VZ state | D1 |
| Program/address map | `address_map`, callbacks, bus lanes | 4 MiB guest RAM and VZ mapping; CS/DRAM control | D1 |
| 68328/EZ SoC | MMIO helpers, baseline timers/IRQ/LCD/UART/SPI | New VZ register semantics/states; preserve EZ | D0.2 / D1–D4 |
| LCD | `MC68328_LCD`, `screen_device`, callbacks | LSSA, 560×160 format, DMA and Dana display power | D3 |
| IRQ/timer | Scheduler and 68328 logic | VZ reset, sources, priority/ack and counter | D2 |
| UART | Serial interface and base handlers | Observed VZ UART1, RX/TX flags and vectors | D2 |
| SPI | SPIM interface and bus callbacks | Two VZ controllers, SPI1 SD, SPI2 ST; Dana GPIO CS | D4 / D7 |
| Keyboard | MAME host input / port-event plumbing | ST firmware protocol, physical scancodes, queue and state | D4 |
| SD card | Evaluate MAME block-image/media devices | SPI1 connection, board GPIO, insertion state | D7 |
| UI and DIAG | MAME debugger, headless and save-state | Separate profiles and Dana-specific experiment probes | D1 and D6 |
| Stock Palm/OS3K | Generic loader/ROM region and debugger | Unknown physical boot/Flash and patched ROM | D8.5 / O0 |

**Do not copy EmuTOS or Retro68 port files into MAME**, even if filenames imply perfect feature coverage. Determine design and file-specific licensing/compatibility before integration.

## 5. Exclusions and identified blockers

- **No NEO/NEO 2 or MC68VZ328 driver is confirmed in the consulted MAME revision.** This is a finding about the audited revisions, not a universal claim about every WIP branch or machine.
- **T MAME checkout path, revision and executable version: UNVERIFIED.** D0.1 was performed through GitHub. Compare them with the pinned commit in the **first authorized T job preflight** (or beforehand using Drive evidence), without consuming Commander merely for `ls`/`git status`.
- **EmuTOS-Dana binary format and fixture hash/location: UNVERIFIED.** D0.3 owns this; the presence of source code does not prove that a built image exists.
- **Detailed VZ mapping:** D0.2 owns it; D0.1 does **not** certify register reset equivalence or timer/IRQ/SPI semantics.
- **Functional qualification:** no tests on T; stable/diag remain unimplemented.

## 6. Closure, state boundaries and continuity

- **D0.1: SPEC_READY**, traceable static audit delivered, **no emulation PASS**.
- **D0.2: PENDING at the time of this audit**, next planned increment: an **MC68EZ328/MC68VZ328 register-level equivalence table** with addresses, widths, resets, side effects, sources and differences.
- **The physical T preflight is not closed** by this document. Before D1.1, demonstrate that the candidate source tree matches a recorded revision. A missing preflight **does not require Commander use during D0.1 or D0.2**.
- No MAME, AS2K, ROM or DANA-emu product source file was changed by this increment. Its only authorized change was documentary.

**Conclusion:** build on the existing 68000 core and DragonBall-family MAME devices in reduced MAME, create a VZ hardware adaptation supported by POSE/Retro68/EmuTOS cross-checks, and preserve the existing AS3000/EZ model.
