# Planned architecture — Dana-stable and Dana-diag

**Binding build architecture, 2026-10-13:** from D1.1 there are **two independent reduced MAME builds**: `Dana-stable` and `Dana-diag`. Each has its own SUBTARGET, BUILDDIR, executable, configuration and evidence; both use the same Dana MAME machine/CPU/device sources. Build them sequentially, exactly `-j3` each, in an isolated Dana-only MAME source snapshot that neither touches nor shares generated build products with AS2K. D6.1 later hardens launchers, persistent storage and user-facing deployment, **not** the creation of the two builds. Frozen commands and tests: [D0.6 candidate](D0_6_FIRST_MAME_DRIVER_CANDIDATE.md). None has actually been built.

**Status: initial specification. Neither variant has been implemented.**

## One shared engine, two products

The project uses **reduced MAME**, reusing the Motorola 68000 core, device scheduler, address mapping, debugger, and available device implementations where appropriate. The **MC68VZ328** device must be modeled faithfully. **First check whether a reusable VZ/NEO driver already exists in the actual MAME work revision**, and adapt it instead of duplicating it when applicable. Only MC68328/MC68EZ328 devices were found in MAME trees audited to date; native VZ support has not been demonstrated. The existing MC68EZ328 is not itself a substitute for the VZ device.

Shared logic will model RAM and chip selects, VZ MMIO, LCD, SPI1/2, UART1, GPIO, Timer1, IRQ, and Dana's ST auxiliary microcontroller. **One hardware model for both variants**: do not introduce variant-specific hardware patches just to satisfy separate tests.

### Stable product

Lightweight everyday emulator: scaled 560 × 160 LCD, working keyboard, selectable image loading, and comprehensible error messages; reset, pause, save/restore, and removable-media controls only when their underlying services are genuinely implemented. Straightforward installation and launch experience, following the AS2K-stable philosophy.

### Diagnostic product

The same engine and guest-visible behavior, with **opt-in instrumentation**: PC/SR/SP, exceptions, IRQ vectors, MMIO reads/writes, GPIO, SPI1/2, UART, framebuffer and memory regions. Machine-readable logs, event/interval-triggered traces, hashed snapshots and reproducible failures. Ideally, use native MAME debugger facilities and headless runs for automated testing.

The diagnostic profile must not alter memory ordering, peripheral state, or guest firmware inputs. Stable and diagnostic variants must isolate configuration, NVRAM, SD images and snapshots.

## Distinct firmware profiles

**R — RAM/EmuTOS (first target):** explicitly recreate the 4 MiB post-DanaRun/dbztool RAM state at 0x00000000–0x003FFFFF and load an EmuTOS-Dana image. This is **not** equivalent to original power-on reset. Confirm the exact image format and entry point before programming the loader.

**P — Stock Palm/Flash (later):** reconstruct reset, chip selects, boot ROM and Flash memory. Firmware extracted from US/UK 1.2/1.5 updaters **has not been established to be a complete physical dump**. Such an image cannot simply be placed at an arbitrary bus address and declared a boot ROM.

**O — Patched OS3K (later):** run adapted NEO firmware on validated virtual hardware. Do not build this firmware in the emulator repository; it belongs to DANA-OS3K.

## Compatibility and reuse

- MAME engine and peripherals: [SamDelorean/mame-as3k](https://github.com/SamDelorean/mame-as3k), as a reference; do not modify or destroy the existing AS2K emulator.
- NEO/NEO 2 research: [MAME code and firmware-first NEO emulator audit](NEO_NEO2_REUSE_AUDIT.md). The VZ CPU family is shared, but board peripherals differ; the Rust project [neo-re/alpha-emu](https://github.com/ioma8/neo-re/tree/master/alpha-emu) is a **reference**, not the product's MAME base.
- Generic VZ model: [original POSE EmRegsVZ](https://github.com/cloudpilot-emu/pose-original) and [CloudpilotEmu](https://github.com/cloudpilot-emu/cloudpilot-emu).
- Dana-specific model: [Retro68 / EmRegsVZAlphaSmart](https://github.com/csnover/Retro68/tree/palmos/PalmUtils/poser/SrcShared/Hardware) and EmSPISlaveSTMicro.
- Observed hardware usage: [EmuTOS-Dana](https://github.com/davidgiven/emutos/tree/dana), including initialization, GPIO, ST, SD and LCD.
- RAM bootstrap: [dbztool](https://github.com/davidgiven/dbztool).
- Commit-pinned sources: [SOURCES](SOURCES.md).

**Licensing restriction:** POSE/Retro68 and EmuTOS include GPLv2+ code; CloudpilotEmu/POSE64 use GPLv3. Do not copy these files into differently licensed MAME devices without a license-compatibility review. Documentation and observable behavior contracts are references for future implementation.

## Subsystem order

CPU/memory/loader engine → PLL/timer/IRQ/UART → LCD framebuffer → ST/SPI2/keyboard → interactive EmuTOS boot → SPI1 SD → touchscreen → additional RAM/physical Flash/power/USB/IR as required by OS3K.

## Product acceptance principle

The value comes from reproducing tests against real guest firmware, not implementing every feature of the original Palm platform or winning upstream MAME acceptance. Admit each feature only when supported by a verified need; do not implement cosmetic features that conceal a lack of internal fidelity.
