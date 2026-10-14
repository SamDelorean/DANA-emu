# DANA-emu — Canonical handoff and exact continuation

**MANDATORY FIRST READ:** [CANONICAL_CONTINUITY_AND_RULES.md](CANONICAL_CONTINUITY_AND_RULES.md). This contains the permanent no-drift startup protocol, remote Commander identity/call accounting, Drive pipeline, tests, isolation rules and current cursor. Do not restart past work or request the rules again.

**Updated: 2026-10-13 source review; current technical cursor D0.4.** This file supersedes older D0.3 handoff text preserved in Git history.

## 1. Purpose and immutable architecture

This repository, [SamDelorean/DANA-emu](https://github.com/SamDelorean/DANA-emu), is dedicated to a **reduced MAME-based emulator of AlphaSmart Dana** with two products sharing one modeled hardware engine: **dana-stable** (everyday UI and state management) and **dana-diag** (opt-in instrumentation, repeatable headless tests, bounded traces and evidence). The hardware target is Dana's **MC68VZ328 DragonBall VZ**, using the existing MAME 68000 CPU infrastructure. EmuTOS-Dana is the first guest, followed by OS3K/NEO firmware patches developed separately in [DANA-OS3K](https://github.com/SamDelorean/Dana-OS3K). MAME upstream acceptance and eventual publication are optional.

No functional Dana emulator, MC68VZ328 MAME device, Dana stable/diag executable or EmuTOS-on-MAME test has been demonstrated to date.

## 2. Authoritative controls and language

- **Plan:** [DANA_EMU_INCREMENTAL_WORK_PLAN.md](DANA_EMU_INCREMENTAL_WORK_PLAN.md), source for all gates, deliverables and state changes.
- **Workflow:** [WORKFLOW_AS2K.md](WORKFLOW_AS2K.md). Static-first, reusable MAME before new code; incremental tests and regression checks; distinct evidence PASS/FAIL/BLOCKED; Drive-first single job; machine T builds with **-j3** only when expressly authorized.
- **Commander:** no authorization carries forward from other conversations. Do not use remote calls for discovery, polling or log retrieval that GitHub/Drive can provide. Existing launch path on T is documented elsewhere; never invent a checkout path for Dana.
- **Git language policy:** all new Git artifacts must be **in English**, including docs, code comments, names, commits, branches, PRs, tests, scripts, checkpoints and CI logs. Existing Spanish history is retained. This conversation may remain in Spanish. See [PUBLICATION_ASIDE_AND_GIT_LANGUAGE_20261013.md](PUBLICATION_ASIDE_AND_GIT_LANGUAGE_20261013.md).
- **Publication:** publication-readiness PR #1 and English-policy PR #2 were merged, but the repo remains **private** unless its owner explicitly changes that. No visibility change or upstream contribution is implicit.
- **Safety/licensing:** no commercial ROMs/Flash images, secrets, emulator save states or guest image binaries in Git; respect MAME and GPL third-party code licences.

## 3. Status of completed documentation increments

| Increment | Current status | Evidence | Remaining execution proof |
|---|---|---|---|
| **D0.1** — MAME/VZ/NEO reuse audit | **SPEC_READY, documentary** | [D0_1_MAME_VZ_REUSE_AUDIT.md](D0_1_MAME_VZ_REUSE_AUDIT.md) | No T checkout or compile tested |
| **D0.2** — EZ/VZ MMIO and errata | **SPEC_READY, documentary** | [D0_2_EZ_VZ_REGISTER_CONTRACT.md](D0_2_EZ_VZ_REGISTER_CONTRACT.md) | No VZ implementation or silicon test |
| **D0.3** — EmuTOS-Dana image/loader contract | **SPEC_READY, source/build recipe only** | [D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md) | No built image, SHA-256 or guest boot test |
| **D0.4–D0.6** | **PENDING** | Plan only | Not started |
| **D1 and later** | **PENDING** | Plan only | No emulator code or tests |

Relevant pinned sources are in [research/sources.lock.json](../research/sources.lock.json).

## 4. Findings of D0.3 that must be preserved

- Source: [davidgiven/emutos @ 9c42ef0f2c2fa9d1e217fced9da68901b2326e8b](https://github.com/davidgiven/emutos/tree/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b), target **make dana**.
- Default cross-toolchain **m68k-atari-mint-**, **-m68000**. Outputs: **emutos.img** (raw second-stage guest) and **emutos-dana.rom** (raw first-stage plus embedded guest), with **emutos.map** containing linked locations.
- Palm helper DanaRun loads **/kernel.img** using 32-KiB blocks and redirects control with **trap #0**. This is a **post-Palm RAM execution path**, not physical Flash reset.
- The first-stage booter **copies emutos.img to 0x00002140** using 32-bit moves, then branches to 0x00002140. Despite the source comment, it **does not perform compression/decompression**.
- Linker image start/entry still needs confirmation against the **actual emutos.map**. The historical loader assumes the embedded image is aligned to four bytes and up to **256 KiB** (16-bit DBF counter); the Palm block array is also only safely sized for **at most eight 32-KiB kernel blocks** (256 KiB payload), even though KERNEL_SIZE is defined as 300 KiB.
- Drive filename search did **not** locate emutos-dana.rom, danarun or kernel.img. No output hashes exist. **Never fabricate image sizes/hashes or claim an EmuTOS build is already available on T.**

## 5. Exact next increment: D0.4 (static-first)

**Single question:** what is the precise virtual CPU, vector and RAM/bus state necessary to enter the EmuTOS-Dana image from a **synthetic post-bootstrap profile** without pretending to emulate the original Dana power-on/reset?

Document, but do not implement:

1. Physical RAM interval (4 MiB), vector table layout and lower memory needed by startup; memory write permissions and overlap guards.
2. PC, SR, SSP initial values and the distinction between loading raw **emutos.img** directly versus executing **emutos-dana.rom** through a virtual first stage. **Do not invent concrete values** for unresolved inherited Palm state.
3. Distinguish hard reset/default VZ registers (manufacturer + addendum) from loader-configured CS/DRAM state (dbztool/danainit.sh and DanaRun context).
4. First guest instructions/exception paths and MMIO touchpoints from **bios/startup.S**, **bios/dana.c**, **emutos.ld**, with explicit observability requirements (PC/SR/SP, vector, accesses).
5. A contract/checklist to be implemented in D1 after D0.4–D0.6 close. Test data and expected results must be independent of emulator hacks.

**No Commander, compilation, toolchain installation, MAME modification or firmware execution is authorized by this handoff.** Continue D0.4 only.

## 6. Starting prompt for another conversation

> Resume DANA-emu from **D0.4**. Read the canonical incremental plan, D0.3 EmuTOS-Dana guest image contract, D0.2 register contract, AS2K workflow and source lock. Complete only the static virtual RAM loader CPU/bus initial-state contract in English Git documents. Do not spend Commander calls or compile without explicit authorization.
