# Technical sources for building the emulator

**Frozen local manifest:** [research/sources.lock.json](../research/sources.lock.json). Copied from the DANA-OS3K manifest on 2026-10-13; it includes exact commit SHAs and immutable links to all priority files. It is not a copy of third-party code.

| Priority | Repository and pinned revision | What DANA-emu should extract |
|---|---|---|
| **Base** | [SamDelorean/mame-as3k, c4e48388](https://github.com/SamDelorean/mame-as3k/tree/c4e48388ca620472643110db2941ce70aa5f3c07) | MAME 68000 CPU, DragonBall 68328/EZ, LCD, infrastructure and debugger. No identified VZ device |
| **NEO / NEO 2 (firmware-first; outside MAME)** | [ioma8/neo-re, 73281487](https://github.com/ioma8/neo-re/tree/732814871fe493e80ed1ab1f959d8dad174ee540/alpha-emu) | System 3 ROM/boot model, VZ MMIO, PLL/timers, traces, NEO keyboard/LCD, GUI and headless testing. **Not** a MAME driver; NEO board peripherals differ from Dana. Verify license before reusing code |
| **Real board** | [davidgiven/emutos, dana branch, 9c42ef0f](https://github.com/davidgiven/emutos/tree/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b) | MMIO registers, LCD, GPIO, ST keyboard, SPI1/2, RAM, UART, IRQ and RAM loader model |
| **Dana-specific emulation** | [csnover/Retro68, palmos, d917b67b](https://github.com/csnover/Retro68/tree/d917b67b16bef7bcf5c75a74f617710c32addcbc/PalmUtils/poser) | **EmRegsVZAlphaSmart** and **EmSPISlaveSTMicro**: AlphaSmart board and keyboard microcontroller models; also ADC and USB |
| **Generic VZ model** | [cloudpilot-emu/pose-original, 97b10711](https://github.com/cloudpilot-emu/pose-original/tree/97b10711fe4ca50c1bd47072378eaab26ba8e81d) | **EmRegsVZ.cpp**, reset tables, chip selects, timers, UART, IRQ, SPI, LCD and **M68VZ328Hwr.h** layout |
| **Revised VZ** | [cloudpilot-emu/cloudpilot-emu, 064d5d57](https://github.com/cloudpilot-emu/cloudpilot-emu/tree/064d5d578bcd1f9072de384d05aa217f83db2f7f) | Compare MMIO handling and POSE corrections; alternative devices |
| **Bootstrap** | [davidgiven/dbztool, d3270238](https://github.com/davidgiven/dbztool/tree/d32702383c2ea3523ea58599c52345435c74e900) | **danainit.sh** sequences for chip selects, DRAM and RAM loading. Study only; **do not execute on physical Dana** |
| **UI and automation** | [clintonthegeek/pose64, 9354edd5](https://github.com/clintonthegeek/pose64/tree/9354edd5b0a2cdadfa0f736e65d080b59500c78f) | Capture, sessions, watches and automation patterns; not an alternate MAME engine |
| **OS3K ABI** | [SamDelorean/betawise, ad557fcf](https://github.com/SamDelorean/betawise/tree/ad557fcf4efbf07fcf0ff3f398a71a7987b7a41c) | Guest firmware reference for the later OS3K phase only |

## NEO/Dana reuse distinctions

- [NEO/NEO 2 audit and actual MAME status](NEO_NEO2_REUSE_AUDIT.md).
- The audited MAME tree contains **AlphaSmart 3000 (EZ)**, not a complete NEO/NEO 2 driver. `hash/alphasmart_kapps.xml` catalogs System 3 applets and does not establish NEO machine emulation.
- The physical NEO is reported to use **DragonBall VZ**, the same family as Dana. Reuse the internal CPU/MMIO behavior contract, **not** any assumed equivalence of LCD or keyboard.
- The firmware-first `ioma8/neo-re/alpha-emu` code provides additional valuable evidence, although it is written in Rust outside MAME.

## Reuse audits closed at documentary level

- [D0.1 — MAME/EZ/VZ, POSE/Retro68 and NEO](D0_1_MAME_VZ_REUSE_AUDIT.md): **SPEC_READY**, pinned GitHub MAME revision and recorded licenses; T checkout awaiting first authorized preflight.
- [D0.2 — EZ/VZ MMIO contract](D0_2_EZ_VZ_REGISTER_CONTRACT.md): **SPEC_READY**, manufacturer errata and MAME/POSE/EmuTOS comparisons, no functional tests.
- [D0.3 — EmuTOS-Dana guest image and loader](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md): **SPEC_READY** source/build recipe, raw booter/payload layout and static constraints. **No built image or hash**.
- [D0.4 — RAM, CPU and VZ bus bootstrap](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md): **SPEC_READY** documented low-memory vector/sysvar layout, virtual PC/SSP/SR, EmuTOS startup checkpoints and unresolved image/map dependencies. No runtime test.
- [D0.5 — Deterministic MAME test harness/trace contract](D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md): **SPEC_READY** documented fixture and bounded trace schemas, independent verification, PASS/FAIL/BLOCKED taxonomy and Drive evidence requirements. No code, run or test result.

## Previously documented evidence

- [VZ MMIO, GPIO and vectors](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/09-EMULADOR-MAPA-MMIO-Y-GPIO.md).
- [Peripheral protocols and milestones](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/10-EMULADOR-PERIFERICOS-Y-HITOS.md).
- [POSE/Retro68 research and licenses](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/12-POSE-DANA-CODIGO-LIBRE-VZ.md).
- [EZ versus VZ datasheets](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/06-DATASHEET-EZ-VZ-COMPARACION.md).
- [Dana 1.2/1.5 ROM extracted from the official updater](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/05-ROM-DANA-ACTUALIZADORES.md).

## How to use these sources

**Only MAME is the foundation of the emulator to be developed.** Other implementations help establish observed behavior and design specific adaptations; do not mechanically integrate them into redistributable software when licensing is incompatible.

Modern MAME has per-file licensing, including BSD-3-Clause; EmuTOS and POSE/Retro68 use GPL-2.0-or-later; Cloudpilot/POSE64 use GPL-3.0. Distribution will require review of each file actually used and applicable obligations.

**Caution:** the existence of a VZ device in POSE does not establish that an MC68VZ328 device exists in the MAME branch we will use. The concrete Dana implementation and tests remain pending.

The local snapshot supports work even if upstream branches change; review and update the canonical source before deciding to move a pinned SHA.
