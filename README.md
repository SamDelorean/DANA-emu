**2026-10-29 Palm digitizer:** Original UK1.5 native 3-point calibration reaches Setup 3 of 4 with sole dana-diag. See docs/PALM_UK15_CALIBRATION_20261029.md for Ghidra evidence and manual run command. Human mouse click acceptance remains pending.

> **2026-10-29 Palm stylus native PASS:** the sole `runtime/diag/bin/dana-diag` now converts an actual stylus hardware event into PG1/IRQ5/SPI2 input; the genuine UK1.5 CPU advanced from `Setup 1 of 4` to **`Setup 2 of 4`** (framebuffer `66009CA8`, captured image inspected). Ghidra analysis and native test are preserved in `main`. Host GUI mouse confirmation remains pending; launch `tools/run-palm-uk15.sh`. See [technical evidence](docs/UK15_ROM_BOOT_SD_SPI_GHIDRA_PANORAMA_20261026.md).

> **2026-10-29 authoritative runtime:** Exactly one active Dana executable is permitted: `runtime/diag/bin/dana-diag`. This is the current instrumented emulator for Palm OS, EmuTOS and future OS3K; `main` is the only development branch. The original UK1.5 Palm OS has been requalified to `Setup 1 of 4` (native framebuffer hash `B395EBF3`) using the opt-in NOR/SDIRQ diagnostic profile. Interactive Palm touchscreen is not yet qualified. Launch with `tools/run-palm-uk15.sh` (the script runs the sole `runtime/diag/bin/dana-diag` binary using a fresh NOR/SDIRQ configuration per run). See [boot profile and exact run command](docs/PALM_UK15_INTERACTIVE_BOOT_20261029.md). Historical earlier-stage build notes below are superseded.

# DANA-emu

**[General Work Plan — permanent project direction, source reuse, Codex workflow, and operating rules](docs/GENERAL_WORK_PLAN.md)**. The current technical checkpoint remains in the [DIAG-FIRST execution ledger](docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md).

> **2026-10-17:** D1.3.1-D fixed LLVM 21 M68k MMIO-01 fixture syntax and verified the exact 30-byte assembly/disassembly on T; R6's 36/36 synthetic tests passed but no build ran. New R7 DIAG-only job, SHA verified, has been accepted by T (PID 214409); **new driver compilation and actual MMIO CPU result remain pending**. Next D1.3.1-E verify Drive result independently. Commander grant **10/10 used**. [Canonical continuity](docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md).


> **Status 2026-10-16:** D1.3.1-B implemented in **source only**: native M68000 32-bit address-space variant and selective VZ 8-bit IVR MMIO at `0xFFFFF300`, plus LLVM-assembled DIAG guest test MMIO-01 and 11 synthetic verifier methods. **No compilation or MMIO runtime PASS** yet. One source-pinned new Clang21 DIAG build/test SH is verified in Drive HOLD (R6; not dispatched). Next **D1.3.1-C** after fresh authorization for bounded Commander calls; older D1.2 RAM 9/9 real-T PASS preserved. [Current technical contract](docs/D1_3_1_VZ_MMIO_ADDRESS_DECODE_CONTRACT.md) and [canonical checkpoint](docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md).


> **2026-10-16 D1.3.1-A static audit:** MC68VZ328 canonical MMIO `0xFFFFF000..0xFFFFFFFF` requires native **32-bit-address-aware** CPU mapping, while the current standalone M68000 uses 24-bit addresses; the pinned MAME MC68EZ328 shows how the native engine exposes 32-bit address spaces. The very first diagnostic MMIO fixture targets **IVR 8-bit `0xFFFFF300`**, actual guest write/read `0x40`; no MMIO code has been changed or qualified yet. **Next D1.3.1-B** selective DIAG decoder and real CPU test; [source-backed contract](docs/D1_3_1_VZ_MMIO_ADDRESS_DECODE_CONTRACT.md). D1.2 4MiB RAM CLOSED/PASS preserved, stable deferred; Commander 0 used for this audit.


> **DANA-emu status — 2026-10-16:** `dana-diag` compiled and tested on the T; **D1.2 native 68000 4MiB post-bootstrap RAM/bus CLOSED/PASS** after R5, independently qualified RAM-01..RAM-09 **9/9 PASS** (25/25 verifier synthetic tests, D1.1 DIAG CLI regression PASS). This does **not** yet emulate DragonBall VZ MMIO, EmuTOS, LCD, keyboard or storage. Stable deferred. Next **D1.3.1 STATIC_FIRST MMIO decoder**. User Commander uses newly authorized **10-call blocks**, R5 spent 2 calls. See [canonical zero-ramp plan](docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md).


> **Latest checkpoint — 2026-10-16:** R3.8 corrected the **DIAG test harness**, not the MAME driver, to accept real ordered M68000 CPU reset vector evidence without demanding an absent Lua reset notification. R5 DIAG-only SH has passed syntax and SHA/readback verification and is safely held in Drive. **25 new Python tests and actual RAM-01..09 still pending.** Next **D1.2-R3.9** single run **only after renewed Commander authorization**, previous 5/5 calls exhausted. [Canonical plan](docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md).


> **Current checkpoint 2026-10-16:** Two user-authorized T DIAG jobs (R3/R4) completed with 17/17 synthetic verifier tests and D1.1 CLI smoke PASS; D1.2 real RAM suite still **BLOCKED in test harness**. R4 native reset vectors and `PC=$4000,SP=$8000,SR=$2700` were observed, but Lua reset notifier flag stayed false and triggered a false bootstrap assertion. Exact next **D1.2-R3.8** harness-only correction; no stable work or hardware changes. Commander **5/5 calls used**, new authorization required to rerun. [Canonical handoff](docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md).


> **Current verified checkpoint — 2026-10-16:** R2 SIGSEGV `-11` happened in **dana-stable** RAM-01; the R2 runner stopped before any DIAG RAM fixture. Corrected R3.6 STATIC_FIRST triage closed. Next **D1.2-R3.7**: run the already prepared, held DIAG-only SH once after explicit Commander authorization; DIAG RAM remains untested. [Canonical plan](docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md).


> **Latest 2026-10-16:** D1.2-R3.5 prepared DIAG-only SH in Drive hold, readback verified; **NOT launched**. R2's real D1.1 DIAG smoke PASSED but RAM-01 MAME process exited `-11` (SIGSEGV) without observation. Next exact increment **D1.2-R3.6 source-backed SIGSEGV triage**; do not repeat a 40-minute build or the same RAM-01 invocation without addressing the blocker. [Canonical checkpoint](docs/DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md).


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
