# DANA-emu

**Start of any future session:** read [CANONICAL_CONTINUITY_AND_RULES.md](docs/CANONICAL_CONTINUITY_AND_RULES.md) first. It preserves the authoritative D1.1 cursor and the separate Dana-stable/Dana-diag builds, all AS2K/Commander/Drive constraints, the English-only Git policy and the pre-action checklist; do not ask the user to reconstruct these rules. No remote authorization is inherited.

**Independent, reduced AlphaSmart Dana emulator based on MAME.**

An engineering project to reproduce **AlphaSmart Dana / MC68VZ328 (DragonBall VZ)** hardware and provide a test platform for **DANA-OS3K**. It follows the AS2K emulator philosophy: two reduced variants, one shared core, and functional evidence before closing increments.

## Defined products

| Variant | Intended contract | Status |
|---|---|---|
| **dana-stable** | Everyday-use emulator: supported image/ROM loading, screen, keyboard, control interface, session-state persistence, and straightforward launch and installation | **Initial design; not implemented** |
| **dana-diag** | Instrumented test bench: CPU/MMIO traces, IRQ, RAM, GPIO, SPI, UART, LCD, snapshots, and reproducible runs | **Initial design; not implemented** |

**Two separately compiled Dana products from D1.1, sharing one hardware codebase and completely isolated from AS2K.** Never mix variant state, storage media, or configurations. Instrumentation must not falsify the behavior observed by guest firmware.

## Execution priorities

1. Emulate **DragonBall VZ and Dana peripherals** using MAME infrastructure.
2. Validate first with **EmuTOS-Dana** loaded into RAM, as a reference for LCD, ST/SPI2 keyboard, clock, and other peripheral routines.
3. Develop the test-bench functions actually required by our tests, distinguishing stable from diag.
4. Run **patched OS3K/NEO firmware** on the same validated virtual hardware. Emulation of the stock Palm/Dana Flash boot path is a separate profile whose physical mapping is not yet finalized.

The goal is **not** to emulate Palm OS for its own sake, implement Atari TOS, or obtain acceptance into upstream MAME. Independent publication and upstream contributions are optional. Do not replace MMIO with hooks that simulate successful results.

## Publication and repository use

This repository documents an implementation **not yet built** and contains no ROMs, commercial firmware, or copied third-party code. The project is unaffiliated with AlphaSmart, Palm, or MAMEDev. Linked external implementations retain their respective copyright holders and licenses; **linking to code does not authorize copying it**.

**[Provenance, risk, and GitHub Actions cost review](docs/PUBLICATION_REVIEW_20261013.md).** A public repository is not automatically an open-licensed project: the license for future project-owned code and the obligations associated with incorporating MAME/EmuTOS/POSE must be reviewed before redistribution.

## Documentation

- [Stable/diag architecture](docs/ARCHITECTURE.md).
- [**Authoritative incremental master plan**](docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md): micro-increments, peripheral-specific tests, regressions, and PASS/FAIL/BLOCKED criteria.
- [Historical D0–D8 plan index](docs/INCREMENTAL_PLAN.md): historical mappings superseded in detail by the master plan.
- [AS2K operating rules](docs/WORKFLOW_AS2K.md).
- [Technical sources and pinned revisions](docs/SOURCES.md).
- [**D0.1 — MAME/VZ reuse audit**](docs/D0_1_MAME_VZ_REUSE_AUDIT.md): documentary SPEC_READY.
- [**D0.2 — EZ/VZ register contract**](docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md): SPEC_READY; VZ MMIO mapping and manufacturer errata.
- [**D0.3 — EmuTOS-Dana guest image/loader**](docs/D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md): SPEC_READY source/build recipe, image binary/hash unavailable. **D0.4 documented.**
- [**D0.4 — RAM/CPU/bus entry contract**](docs/D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md): SPEC_READY documentation.
- [**D0.5 — Deterministic test harness and evidence**](docs/D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md): SPEC_READY documentary.
- [**D0.6 — First independent Dana-stable/Dana-diag MAME builds**](docs/D0_6_FIRST_MAME_DRIVER_CANDIDATE.md): SPEC_READY documentary; next D1.1 pending explicit approval.
- [Cross-conversation continuation point](docs/HANDOFF.md).

## Relationship to other repositories

- **[DANA-OS3K](https://github.com/SamDelorean/Dana-OS3K)**: hardware and firmware research, OS3K adaptation, and the master source manifest.
- **[DANA-emu](https://github.com/SamDelorean/DANA-emu)**: emulator development only.
- **[EmuTOS-Dana](https://github.com/davidgiven/emutos/tree/dana)** and **[POSE-Dana (Retro68)](https://github.com/csnover/Retro68/tree/palmos/PalmUtils/poser)**: hardware references, subject to their licenses.
- **[MAME-AS3K](https://github.com/SamDelorean/mame-as3k)**: existing MAME/DragonBall EZ infrastructure, **not a working Dana emulator**.

## Handoff status — 2026-10-13

**Documentary preparation.** This project does not yet have an MC68VZ328 driver in MAME, a Dana executable, or an EmuTOS-on-emulator test. No Commander calls were made during this preparation. **D0.1 reached documentary SPEC_READY**, with a pinned GitHub revision and reuse map; the T checkout remains unverified. **Current next increment: D1.1 — two independent, isolated Dana-stable and Dana-diag builds (not yet authorised).** D0.1–D0.6 are SPEC_READY documentation only; guest binary/hash and actual build remain unverified. No Dana emulator has been tested. Consult the [master plan](docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md) and [HANDOFF](docs/HANDOFF.md).
