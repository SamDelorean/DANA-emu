# DANA-emu

> **Current execution plan (2026-10-16):** [DIAG-FIRST anti-gate incremental plan and zero-ramp handoff](docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md). Develop and qualify **dana-diag only**. Resume at **D1.2-R3.1**; stable deferred. Read the linked plan first; earlier dual-build directions are historical.


> **Current development mode (2026-10-16): DIAG ONLY.** [Diagnostic-first development policy and AS2K workflow](docs/DIAG_FIRST_DEVELOPMENT_POLICY.md) overrides historical dual-build requirements in older text below. Only `dana-diag` is developed and qualified; `dana-stable` will become the everyday-use version later. D1.1's two compiled binaries are historical PASS evidence only. D1.2 is pending diag-only qualification; the old dual-build R2 job was withdrawn and must not be launched.


**Start of any future session:** read [CANONICAL_CONTINUITY_AND_RULES.md](docs/CANONICAL_CONTINUITY_AND_RULES.md) first. It preserves the authoritative D1.2 cursor, D1.1 dual-build qualification, and the separate Dana-stable/Dana-diag builds, all AS2K/Commander/Drive constraints, the English-only Git policy and the pre-action checklist; do not ask the user to reconstruct these rules. No remote authorization is inherited.

**Independent, reduced AlphaSmart Dana emulator based on MAME.**

An engineering project to reproduce **AlphaSmart Dana / MC68VZ328 (DragonBall VZ)** hardware and provide a test platform for **DANA-OS3K**. It follows the AS2K emulator philosophy: two reduced variants, one shared core, and functional evidence before closing increments.

## Defined products

| Variant | Intended contract | Status |
|---|---|---|
| **dana-stable** | Everyday-use emulator: supported image/ROM loading, screen, keyboard, control interface, session-state persistence, and straightforward launch and installation | **D1.1 minimal nonworking skeleton compiled and CLI-verified; listed features not implemented** |
| **dana-diag** | Instrumented test bench: CPU/MMIO traces, IRQ, RAM, GPIO, SPI, UART, LCD, snapshots, and reproducible runs | **D1.1 separate debug skeleton compiled and CLI-verified; diagnostic hardware features not implemented** |

**Two separately compiled Dana products from D1.1, sharing one hardware codebase and completely isolated from AS2K.** Never mix variant state, storage media, or configurations. Instrumentation must not falsify the behavior observed by guest firmware.

## Execution priorities

1. Emulate **DragonBall VZ and Dana peripherals** using MAME infrastructure.
2. Validate first with **EmuTOS-Dana** loaded into RAM, as a reference for LCD, ST/SPI2 keyboard, clock, and other peripheral routines.
3. Develop the test-bench functions actually required by our tests, distinguishing stable from diag.
4. Run **patched OS3K/NEO firmware** on the same validated virtual hardware. Emulation of the stock Palm/Dana Flash boot path is a separate profile whose physical mapping is not yet finalized.

The goal is **not** to emulate Palm OS for its own sake, implement Atari TOS, or obtain acceptance into upstream MAME. Independent publication and upstream contributions are optional. Do not replace MMIO with hooks that simulate successful results.

## Publication and repository use

This repository contains a **T-verified D1.1 MAME skeleton** in two independently compiled variants, but **no working Dana guest emulator**. It contains no ROMs, commercial firmware, or copied third-party code. The project is unaffiliated with AlphaSmart, Palm, or MAMEDev. Linked external implementations retain their respective copyright holders and licenses; **linking to code does not authorize copying it**.

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
- [**D0.6 — First independent Dana-stable/Dana-diag MAME builds**](docs/D0_6_FIRST_MAME_DRIVER_CANDIDATE.md): SPEC_READY documentary specification, fulfilled at D1.1 only for build/selectability.
- [**D1.1 — T-qualified dual MAME skeleton builds**](docs/D1_1_IMPLEMENTATION_CANDIDATE.md): PASS, stable and diag `asmdana` CLI checks, source registration guard and R5 evidence; **not a guest functional PASS**.
- [Cross-conversation continuation point](docs/HANDOFF.md): exact next increment D1.2 PENDING.

## Relationship to other repositories

- **[DANA-OS3K](https://github.com/SamDelorean/Dana-OS3K)**: hardware and firmware research, OS3K adaptation, and the master source manifest.
- **[DANA-emu](https://github.com/SamDelorean/DANA-emu)**: emulator development only.
- **[EmuTOS-Dana](https://github.com/davidgiven/emutos/tree/dana)** and **[POSE-Dana (Retro68)](https://github.com/csnover/Retro68/tree/palmos/PalmUtils/poser)**: hardware references, subject to their licenses.
- **[MAME-AS3K](https://github.com/SamDelorean/mame-as3k)**: existing MAME/DragonBall EZ infrastructure, **not a working Dana emulator**.

## Handoff status — 2026-10-14

**D1.1 is PASS (minimal MAME machine registration and two independent T builds/selectability only).** [Implementation PR #5](https://github.com/SamDelorean/DANA-emu/pull/5) was merged after real T R5 tests; the separate [English documentation PR #4](https://github.com/SamDelorean/DANA-emu/pull/4) was also merged. R5 used Clang 21, `PRECOMPILE=0`, sequential `make -j3`, and both variants independently passed `-listfull`, `-listxml` and `-validate`. [Drive evidence](https://drive.google.com/file/d/1NLIydtsa6t2XTyeXG4SvleIZI-jfYeo7/view). D0.1–D0.6 remain SPEC_READY documentary only.

**Exact next increment: D1.2 PENDING — 4 MiB guest RAM and big-endian 8/16/32-bit access tests.** No RAM/MMIO/EmuTOS boot functionality has passed. The T checkout is at `/home/spc/Projects/alphasmart/DANA-emu` with a pinned, read-only donor MAME tree; new implementation or Commander execution needs fresh approval. No prior call budget transfers to D1.2. Consult the [master plan](docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md) and [canonical handoff](docs/HANDOFF.md).
