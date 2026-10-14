# AlphaSmart NEO / NEO 2 reuse audit for DANA-emu

**Initial review: 2026-10-13.** This note distinguishes existing emulation, actual firmware, and board-specific hardware. **It does not modify code or run tests.** Canonical Dana hardware research: [DANA-OS3K](https://github.com/SamDelorean/Dana-OS3K).

## Verified findings

1. **NEO and Dana share the MC68VZ328 DragonBall VZ family.** Public NEO teardown notes identify `MC68VZ328PV` (or the AG revision) at approximately 33 MHz: https://hackaday.io/project/25732-hacking-the-alphasmart-neo/log/62397-whats-inside ; https://hackaday.com/2020/11/05/alphasmart-neo-teardown-this-is-the-way-to-write-without-distractions/ . Exact silicon-revision equivalence across NEO, NEO 2 and Dana **requires board/datasheet verification**. Sharing a CPU **does not mean sharing external peripherals or board mapping**.
2. **The inspected official MAME and AS3K fork trees contained neither a complete NEO/NEO 2 driver nor an `MC68VZ328` device type.** `src/mame/skeleton/alphasma3k.cpp` is the **AlphaSmart 3000 / MC68EZ328** driver, marked nonworking. `src/devices/machine/mc68328.cpp` registers `MC68328` and `MC68EZ328`, not VZ. `hash/alphasmart_kapps.xml` catalogs System 3/NEO applets/SmartApplets, **not** a NEO machine emulator. These findings describe the **inspected trees**, not an unpushed local branch on T or another external WIP.
3. **An open NEO emulator does exist outside MAME:** [ioma8/neo-re, alpha-emu](https://github.com/ioma8/neo-re/tree/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu). Its module README describes **firmware-first** execution, loading actual System 3 firmware, bounded 68k instruction execution, MMIO tracing, GUI/headless operation, scripted keypresses and LCD captures. The repository-level README retains an older summary calling it a SmartApplet emulator; **prefer the current `alpha-emu` README and code**, and do not treat the author's reported tests as locally verified PASS.
4. **Retro68/POSE contains Dana-specific board emulation** in addition to the common VZ model: `EmRegsVZAlphaSmart`, `EmSPISlaveSTMicro`, ADC, and GPIO/USB references. POSE/Retro68 uses GPL; check licensing before copying. Additional links: [sources.lock.json](../research/sources.lock.json).

## NEO code to inspect before designing VZ in MAME

Pinned NEO repository: **`ioma8/neo-re` @ `732814871fe493e80ed1ab1f959d8dad174ee540`** (master at the time of inspection).

| File | Extract | Limitation |
|---|---|---|
| [alpha-emu/README.md](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/README.md) | Firmware-first boot, headless tests, commands, LCD and keyboard evidence | Author's experimental documentation, not our PASS |
| [src/firmware.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/firmware.rs) | System 3 image format, vectors, segments and loader | These are **NEO** ROM formats; do not map Palm/Dana ROM to those addresses |
| [src/memory.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/memory.rs) | MMIO decoder, initialization, timers, register mirrors and RAM model | NEO-specific external peripheral mapping |
| [src/keyboard.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/keyboard.rs) | Physical NEO keyboard matrix and events | **Dana uses an auxiliary ST over SPI2**, not the same matrix wiring |
| [src/lcd.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/lcd.rs) | NEO LCD controller, ports and capture | **Dana uses the 560×160 VZ LCD framebuffer**, not two NEO external controllers |
| [src/firmware_session.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/firmware_session.rs) | Firmware state/session and test engine | Adapt concepts; do not copy uncritically |
| [src/gui.rs](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu/src/gui.rs) | Visualization and headless/GUI control | Our goal is reduced MAME, not a port of the Rust GUI |
| [docs/2026-04-20-alpha-emu-memory-map.md](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/docs/2026-04-20-alpha-emu-memory-map.md) | Author-documented memory/MMIO effects | Not the Dana memory map |
| [docs/2026-04-22-alpha-emu-headless-usage.md](https://github.com/ioma8/neo-re/blob/732814871fe493e80ed1ab1f959d8dad174ee540/docs/2026-04-22-alpha-emu-headless-usage.md) | Reproducible test interfaces | Reproduce and validate later in our environment |

NEO README figures: 33 MHz target CPU; left LCD ports `0x01008000..02` and right LCD ports `0x01000000..02`; keyboard matrix `0xFFFFF419`, selection `0xFFFFF411`; internal window `0xFFFFF000..0xFFFFFFFF` with a low alias; Small ROM at `0x00400000` and System 3 ROM data. **NEO's external LCD-controller addresses DO NOT correspond to Dana's integrated LCD**, even though some internal DragonBall VZ registers are shared.

**ioma8/neo-re license:** no root `LICENSE` file was observed during directory inspection. Treat code as **read-only reference material** until reuse rights are verified; public availability on GitHub does not automatically authorize copying/relicensing.

## Dana reuse matrix

| Function | NEO / NEO 2 | Dana | Reusable material |
|---|---|---|---|
| CPU | DragonBall VZ for NEO; verify exact NEO 2 silicon | DragonBall VZ | **MAME** 68000 core + VZ register behavior validated against external evidence |
| Internal MMIO | VZ clock, timers, IRQ, GPIO, UART | VZ peripherals configured differently | Register layout/reset states and width/address tests; not board-specific values |
| RAM and Flash | NEO map with OS3K | Dana RAM and PalmCard/Flash | Mapping algorithms, diagnostics and separately specified loader |
| LCD | Dual-port external controllers in NEO | Monochrome 560×160 VZ LCD DMA | Display patterns and common CPU registers; not NEO LCD circuitry |
| Keyboard | GPIO-connected matrix | Auxiliary ST on SPI2 | Host input/harness concepts; Dana controller based on Retro68/EmuTOS evidence |
| SD | Stock NEO lacks Dana's integrated slots | Two slots; one controlled by EmuTOS | Dana SPI1/SD subsystem and wiring only |
| Diagnostics | MMIO traces, LCD snapshots, `alpha-emu` scripts | Instrumented MAME DIAG | Test design without changing the emulator engine |
| ABI/OS | NEO System 3 / OS3K | Stock Palm today; patched OS3K-Dana later | Useful in the **firmware** phase, not as forced virtual-hardware behavior |

## D0 instruction before writing code

1. Inspect actual **existing MAME drivers separately**: `mc68328.cpp/h`, `mc68328lcd.cpp/h`, `alphasma3k.cpp`, and `alphasmart_kapps.xml`. Do not claim the last is a NEO machine driver.
2. Read the `neo-re/alpha-emu` code statically, distinguishing **VZ core** access from NEO external peripherals. Prepare a common-VZ/NEO/Dana comparison table.
3. Cross-check **POSE EmRegsVZ** and **Retro68 EmRegsVZAlphaSmart/EmSPISlaveSTMicro** against real **EmuTOS-Dana** sequences.
4. Design the first VZ device **within MAME**, then the Dana board profile. Verify any NEO/VZ WIP driver in the actual T MAME branch before implementation.
5. Document sources, licenses, maps and tests. Do not modify AS2K, DANA-OS3K or physical ROM.

## Status

**Reuse documented; code neither imported nor compiled.** No complete NEO/NEO2 driver was found in the inspected MAME trees. The `neo-re` NEO emulation is an external reference, not an existing MAME component. Shared components are CPU/register architecture; board-peripheral distinctions are explicit.
