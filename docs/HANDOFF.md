# DANA-emu — Canonical handoff and exact continuation

> **CURRENT D2.2-R1 FEATURE-BRANCH CHECKPOINT — 2026-10-17 local.** Continued from `e9a71db`, reading canonical `main@36d4f23` and the supplied native evidence review. Original D2.2 remains **BLOCKED_HARNESS_RESET_OBSERVATION**, not a Port C product failure. [R1 correction](D2_2_R1_RESET_HARNESS.md) is harness-only: separate native save/restore and reset processes, guard `register_prestart` because it runs at every reset, retain one pair of taps, and require request/native notification/post-reset CPU vectors and state. Original fixture bytes, all production/build input trees and DIAG SHA `d7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5` remain applicable. **40 offline focused tests PASS; native R1 PENDING.** No emulator, T, Commander, MAME/ROM rebuild, D3 work or merge. One new `tests/hold/006_dana_portc_reset_r1_reuse_diag.job.sh` is prepared for explicitly supplied, SHA-verified binary reuse, **LOCAL HOLD / NOT UPLOADED / NOT LAUNCHED**; new separate authorization is required. The old 005 evidence/job is preserved. Git branch push updates PR #7's diff; direct PR API access is Forbidden, so a body update cannot be claimed. E1/E2/E3/D2.1 and all qualified baselines remain closed; no old campaign is restarted.

> **CURRENT FEATURE-BRANCH CHECKPOINT — 2026-10-18, issue #9 / draft PR #7.** Read the latest `main` General Work Plan and DIAG-exclusive policy before historical text below. Canonical `main@ba40acd` records E1/E2/E3/D2.1 PASS; these closed stages were not rerun. The feature branch was fast-forwarded to `4494a7e` before implementing the [Port C continuation candidate](D2_2_PORTC_IMPLEMENTATION.md): individually decoded PCPDEN/PCSEL, native save registration, explicit dbztool-backed R-direct software profile zero, and byte-lane-aware guest observation. Raw aligned bus `F412/00FF` selects **PCSEL at F413**, not PCPDEN. **69 local isolated/static checks PASS; native runtime UNRUN.** Both official NXP PDFs were blocked by network policy, so physical reset/reserved masks/electrical qualification remain **BLOCKED_SPEC**. Do not treat the profile's zero as physical reset or POSE's FF as manufacturer evidence. PFSEL/PKSEL/PKDATA/LCD remain unmapped; no next actual hardware dependency has been observed under this candidate. A single `tests/hold/005_dana_portc_native_diag.job.sh` is prepared for DIAG only, immutable existing guest hashes, LLVM21 `-j3`, native lanes/reset/save/alias/RAM guards, two authentic guests and corruption rejection. **LOCAL HOLD; no Drive remote/connector is configured here, so NOT UPLOADED and NOT LAUNCHED.** No T, Commander, ROM rebuild, alternate emulator, merge or binary publication. Next: obtain UM+AD, resolve the manufacturer contract, verify private Drive HOLD placement and obtain separate authorization before any native T campaign. Historical pending D1.2 and dual-variant instructions below are superseded by the current canonical main checkpoint and the user's DIAG-only directive.

**MANDATORY FIRST READ:** [CANONICAL_CONTINUITY_AND_RULES.md](CANONICAL_CONTINUITY_AND_RULES.md). This contains the permanent no-drift startup protocol, remote Commander identity/call accounting, Drive pipeline, tests, isolation rules and current cursor. Do not restart past work or request the rules again.

**Updated: 2026-10-14 after the two authorized PR merges and T R5 qualification. Current technical cursor: D1.2 (PENDING; no implementation or remote authority). D1.1 is PASS for dual-build/selectability only.**

## 1. Purpose and immutable architecture

This repository, [SamDelorean/DANA-emu](https://github.com/SamDelorean/DANA-emu), is dedicated to a **reduced MAME-based emulator of AlphaSmart Dana** with two products sharing one modeled hardware engine: **dana-stable** (independently compiled everyday variant) and **dana-diag** (independently compiled diagnostic variant, later enabling opt-in instrumentation, repeatable headless tests, bounded traces and evidence). **Both distinct executable builds begin at D1.1, never wait until D6**, and share one Dana engine/codebase. They must be completely isolated from AS2K builds and files. The hardware target is Dana's **MC68VZ328 DragonBall VZ**, using the existing MAME 68000 CPU infrastructure. EmuTOS-Dana is the first guest, followed by OS3K/NEO firmware patches developed separately in [DANA-OS3K](https://github.com/SamDelorean/Dana-OS3K). MAME upstream acceptance and eventual publication are optional.

The minimal ROM-less M68000 `asmdana` skeleton compiled into two independently verified T executables (`dana-stable` and `dana-diag`) and passed targeted MAME CLI smoke in D1.1 R5. Neither a functional MC68VZ328 MAME device nor any EmuTOS-on-MAME boot or RAM/peripheral test has been demonstrated.

## 2. Authoritative controls and language

- **Plan:** [DANA_EMU_INCREMENTAL_WORK_PLAN.md](DANA_EMU_INCREMENTAL_WORK_PLAN.md), source for all gates, deliverables and state changes.
- **Workflow:** [WORKFLOW_AS2K.md](WORKFLOW_AS2K.md). Static-first, reusable MAME before new code; incremental tests and regression checks; distinct evidence PASS/FAIL/BLOCKED; Drive-first single job; machine T builds with **-j3** only when expressly authorized.
- **Commander:** no authorization carries forward from other conversations. Do not use remote calls for discovery, polling or log retrieval that GitHub/Drive can provide. Existing launch path on T is documented elsewhere; never invent a checkout path for Dana.
- **Git language policy:** all new Git artifacts must be **in English**, including docs, code comments, names, commits, branches, PRs, tests, scripts, checkpoints and CI logs. Existing Spanish history is retained. This conversation may remain in Spanish. See [PUBLICATION_ASIDE_AND_GIT_LANGUAGE_20261013.md](PUBLICATION_ASIDE_AND_GIT_LANGUAGE_20261013.md).
- **Visibility and publication:** GitHub reported this repository as `public` on 2026-10-14; no visibility setting was changed during the D1.1/translation integration. No binary release, upstream MAME contribution, firmware publication or further visibility change is authorized by this handoff.
- **Safety/licensing:** no commercial ROMs/Flash images, secrets, emulator save states or guest image binaries in Git; respect MAME and GPL third-party code licences.

## 3. Status of completed documentation increments

| Increment | Current status | Evidence | Remaining execution proof |
|---|---|---|---|
| **D0.1** — MAME/VZ/NEO reuse audit | **SPEC_READY, documentary** | [D0_1_MAME_VZ_REUSE_AUDIT.md](D0_1_MAME_VZ_REUSE_AUDIT.md) | D0.1 itself was documentary; pinned donor checkout was later verified on T in R3 |
| **D0.2** — EZ/VZ MMIO and errata | **SPEC_READY, documentary** | [D0_2_EZ_VZ_REGISTER_CONTRACT.md](D0_2_EZ_VZ_REGISTER_CONTRACT.md) | No VZ implementation or silicon test |
| **D0.3** — EmuTOS-Dana image/loader contract | **SPEC_READY, source/build recipe only** | [D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md) | No built image, SHA-256 or guest boot test |
| **D0.4** — CPU/RAM/VZ post-bootstrap profile | **SPEC_READY, documentary** | [D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md) | No guest/image/map or MAME execution |
| **D0.5** — deterministic fixture/trace and evidence | **SPEC_READY, documentary** | [D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md](D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md) | No harness code or runtime test |
| **D0.6** — first dual-build MAME candidate | **SPEC_READY, documentary** | [D0_6_FIRST_MAME_DRIVER_CANDIDATE.md](D0_6_FIRST_MAME_DRIVER_CANDIDATE.md) | No built executables |
| **D1.1** — minimum Dana machine | **PASS — registration/build/selectability** | [R5 T evidence](https://drive.google.com/file/d/1NLIydtsa6t2XTyeXG4SvleIZI-jfYeo7/view); [merged PR #5](https://github.com/SamDelorean/DANA-emu/pull/5) | No guest/MMIO/RAM function implied |
| **D1.2** — 4 MiB RAM and 68k bus reads/writes | **PENDING** | [D0.4 RAM/CPU/bus contract](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md) | No guest RAM/8/16/32-bit test |
| **D1.3 and later** | **PENDING** | Plan only | No VZ/EmuTOS functional tests |

Relevant pinned sources are in [research/sources.lock.json](../research/sources.lock.json).

## 4. Findings of D0.3 that must be preserved

- Source: [davidgiven/emutos @ 9c42ef0f2c2fa9d1e217fced9da68901b2326e8b](https://github.com/davidgiven/emutos/tree/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b), target **make dana**.
- Default cross-toolchain **m68k-atari-mint-**, **-m68000**. Outputs: **emutos.img** (raw second-stage guest) and **emutos-dana.rom** (raw first-stage plus embedded guest), with **emutos.map** containing linked locations.
- Palm helper DanaRun loads **/kernel.img** using 32-KiB blocks and redirects control with **trap #0**. This is a **post-Palm RAM execution path**, not physical Flash reset.
- The first-stage booter **copies emutos.img to 0x00002140** using 32-bit moves, then branches to 0x00002140. Despite the source comment, it **does not perform compression/decompression**.
- Linker image start/entry still needs confirmation against the **actual emutos.map**. The historical loader assumes the embedded image is aligned to four bytes and up to **256 KiB** (16-bit DBF counter); the Palm block array is also only safely sized for **at most eight 32-KiB kernel blocks** (256 KiB payload), even though KERNEL_SIZE is defined as 300 KiB.
- Drive filename search did **not** locate emutos-dana.rom, danarun or kernel.img. No output hashes exist. **Never fabricate image sizes/hashes or claim an EmuTOS build is already available on T.**

## 5. Exact next increment: D1.2 (static-first, no execution authorization)

**D1.1 is CLOSED/PASS only at its frozen build/selectability scope.** The tested implementation head `92e39eff050fa7a62486569be6a34994682ce44c` was merged in [PR #5](https://github.com/SamDelorean/DANA-emu/pull/5); the independent English translation was merged in [PR #4](https://github.com/SamDelorean/DANA-emu/pull/4). Both products compiled on T sequentially with `-j3`, Clang 21, `OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++ PRECOMPILE=0`, using the same ROM-less skeleton source and separate staging. Both passed `-listfull asmdana`, `-listxml asmdana`, and `-validate asmdana`.

- **Evidence package:** [R5](https://drive.google.com/file/d/1NLIydtsa6t2XTyeXG4SvleIZI-jfYeo7/view), SHA-256 `2f697fdffb381b3ed2f82dba596a528a5fa8aa88be07735247b608f64a3847ff`.
- **Stable executable SHA-256:** `ec055d08b66d46181d26cd9371f7f961f52732ad36f468a8aae0a4e1b7bc83d1`.
- **Diag executable SHA-256:** `dd877c9cb36c491e675b82ce2aba78548519cccf2bd16bf2a9c61cbd3000435c`.
- **Verified T Dana checkout:** `/home/spc/Projects/alphasmart/DANA-emu` (tested feature head; refresh from merged main before any future approved build).
- **Read-only MAME donor:** `/home/spc/Projects/alphasmart/as2k-stable-eeepc900-local/mame-as3k-donor` pinned at `c4e48388ca620472643110db2941ce70aa5f3c07`; keep builds under `/home/spc/DANA_EMU_ISOLATED`.
- **Scope restriction:** the device remains `MACHINE_NOT_WORKING | MACHINE_NO_SOUND`, with 1 MHz placeholder M68000 only. No ROM, actual Dana clock, 4 MiB RAM, VZ MMIO, LCD, keyboard or EmuTOS guest proof exists.

**D1.2 objective:** map 4 MiB of 68k-visible RAM and test 8/16/32-bit reads and writes, big-endian byte lanes, alignment and bounds without any additional MMIO or boot claim. Read [D0.4](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md) and the existing MAME driver first; prepare an exact synthetic guest fixture and regression contract before touching source. New executable-source implementation and T/Commander execution require **fresh user authorization**. Both earlier five-call budgets have been exhausted. `Siguiente` permits only static linear preparation, not new code, remote work or Git publication.

## 6. Starting prompt for another conversation

> Resume DANA-emu at **D1.2 PENDING**. D1.1 is closed PASS for independently compiled stable/diag MAME skeletons on T (R5 evidence; PR #5 merged); no guest functionality is claimed. Read the canonical rules, incremental plan, D0.4 and D1.1 qualification evidence. Advance only static RAM/bus planning unless new approval is given for source changes and a new T/Commander budget.
