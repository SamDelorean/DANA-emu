# DANA-emu — Canonical continuity, universal rules, and no-drift operating contract

**Status: ACTIVE / MANDATORY READING at the beginning of every new conversation.**
**Updated: 2026-10-13. Exact technical cursor: D0.4 (PENDING, static documentation only).**

This document exists so the user does not need to teach the assistant the project, correct repeated process errors, restore standing rules, or audit its actions. Treat the content as the minimum mandatory baseline for future work. Any later change requires an explicit project decision supported by Git evidence; never silently reinterpret this file or advance the cursor.

## 0. First-turn protocol — execute before proposing any new work

1. Open this file first and then read **docs/HANDOFF.md**, **docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md**, **docs/WORKFLOW_AS2K.md**, **research/sources.lock.json**, and the source/evidence document for the current increment. Check the current repository main HEAD and recent commits before trusting a historical chat summary.
2. State in Spanish to the user, briefly: the repository and its purpose; current technical cursor; completed status/evidence; next single increment; constraints; whether any execution or Commander authorization exists.
3. Do **not** start from D0.1, restart earlier analyses, change architecture, or ask the user to restate these rules. Do not treat unrelated Git, publishing, or AS2K activity as permission to advance DANA-emu.
4. Apply the work plan as written. A user message such as **"Siguiente"** advances **only the next linear increment appropriate to the present phase** and never authorizes remote execution, destructive work, physical device operations, publication, or using a previous Commander budget.
5. If the latest Git evidence conflicts with any older chat or this index, preserve both facts, identify the exact inconsistency, and resolve it using the newest **verified technical artifact** and project decisions; do not invent a PASS, a file, a binary, a path, a Git revision, or a device state.
6. Keep Git artifacts in English. Conversation with the user stays in Spanish unless requested otherwise.
7. Report what was **actually done**, where it was saved, and what remains **not done**. Verification is not optional for a claimed Git write or runtime PASS.

## 1. Project objective and strict separation

**Implementation repository:** https://github.com/SamDelorean/DANA-emu (private main, when last checked).
**Related research/firmware repository:** https://github.com/SamDelorean/Dana-OS3K.
**Existing MAME reference:** https://github.com/SamDelorean/mame-as3k (source lock in research/sources.lock.json).

Build an independent, reduced **MAME-based AlphaSmart Dana emulator** with two versions sharing **the exact same hardware emulation engine**:

- **dana-stable:** everyday lightweight emulator, guest image selection, real 560x160 monochrome LCD, real keyboard interaction, session/reset/state controls and eventual easy installation.
- **dana-diag:** same guest-visible hardware behavior, opt-in instrumentation, CPU/memory/MMIO/IRQ/GPIO/SPI/LCD/UART traces, bounded logs, deterministic headless tests, reproducible snapshots and evidence.

The target hardware is **MC68VZ328 DragonBall VZ and the Dana board**. First proof target is **EmuTOS-Dana**, loaded through a clearly labelled post-bootstrap RAM profile. Later: OS3K/NEO firmware patched in DANA-OS3K. Actual Palm/Flash cold boot is a separate later requirement with a different memory/reset contract.

**MAME is the mandatory emulator foundation.** POSE, Retro68, EmuTOS-Dana, Neo work and dbztool are technical references, not a reason to switch emulation engines. Sharing the DragonBall VZ CPU with NEO does not imply identical external LCD, keyboard, SD or GPIO wiring. Protect any already working AS2K MAME components. Publication of our reduced emulator and submitting contributions to official MAME are **optional**, never the main success criterion.

## 2. Technical status — immutable until new evidence

| Increment | Status | Evidence |
|---|---|---|
| **D0.1**, MAME / EZ / VZ / NEO reuse | **SPEC_READY, documentation only** | docs/D0_1_MAME_VZ_REUSE_AUDIT.md |
| **D0.2**, EZ vs VZ register contract | **SPEC_READY, documentation only** | docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md |
| **D0.3**, EmuTOS-Dana image and loader | **SPEC_READY, source/build recipe only** | docs/D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md |
| **D0.4**, virtual RAM bootstrap CPU/bus state | **PENDING: NEXT INCREMENT** | docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md |
| **D0.5–D0.6**, harness and frozen candidate | **PENDING** | plan only |
| **D1+**, functional emulator construction/testing | **PENDING** | no PASS yet |

**No Dana emulator source/build has passed functional verification.** No MC68VZ328 MAME device, stable or diag executable, or successful EmuTOS-on-MAME run is proven in this repository. The specific machine T checkout path and revision for DANA-emu are not yet verified. No EmuTOS-Dana build artifacts or guest image SHA have been verified. Do not label documentary SPEC_READY as **PASS**. Do not claim a partial GUI/host rendering proves a real guest LCD.

Historical facts to preserve:

- MAME source baseline candidate is SamDelorean/mame-as3k commit **c4e48388ca620472643110db2941ce70aa5f3c07** (GitHub source baseline, **not** proof of T checkout).
- EmuTOS-Dana commit **9c42ef0f2c2fa9d1e217fced9da68901b2326e8b**, source target **make dana**; outputs **emutos.img** and **emutos-dana.rom**, not a physical Dana Flash ROM.
- The historical Dana RAM booter copies EmuTOS to **0x00002140**, then jumps there; that address and image length must be validated against the exact build map before execution. Historic loader limitation approximately **256 KiB**, with alignment/coverage constraints, is recorded in D0.3.
- First intended guest RAM profile is **4 MiB**, from **0x00000000 through 0x003FFFFF**, in a **post-bootstrap** state. Do not confuse this with physical reset/power-on.
- The historical specific-Dana POSE adaptation is in **csnover/Retro68**, including EmRegsVZAlphaSmart and EmSPISlaveSTMicro; generic VZ registers are in POSE EmRegsVZ; Neo firmware-first reference is **ioma8/neo-re/alpha-emu**, *not a MAME NEO driver*. Review licensing before copying.
- VZ vs EZ MMIO **must** follow Motorola UM/addendum; especially chip selects, DRAM, SPI1 (16-bit data), SPI2/ST, timer/IRQ and LCD LRRA differ. Do not reintroduce corrected reset-value errors from POSE.

## 3. Strict increment lifecycle: one question, one verified result

**Canonical sequence:** STATIC_FIRST / source reuse → define one limited increment → freeze source and expected behavior → secure the required explicit execution approval → create a single self-contained SH job (when local execution is needed) → dispatch on canonical T → retrieve evidence **through Drive** → independent PASS / FAIL / BLOCKED → integrate only verified PASS → move forward.

Detailed authoritative milestones are in **docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md**. They must **not** be collapsed into larger vague "gates" or reorganized ad hoc.

Before product changes, define: current cursor, one technical objective, dependencies, exact files allowed, source/base SHA, guest fixture, expected signals, bounded instrumentation, reproducible commands, functional test and regression coverage, failure/rollback behavior, and evidence location.

- **D0 documentation:** SPEC_READY closes a source-audited specification, **not** functional testing. Proceed linearly from D0.4 to D0.5 only after D0.4 documentation is actually complete.
- **D1 onward:** PASS requires *actual* execution and objective guest-visible evidence on T (or an expressly approved replacement test environment); compilation and CI structural checks alone are insufficient. FAIL and BLOCKED record exact causes, not guesses.
- **Never reopen PASS** without evidence of a defect; never skip a blocking dependency by inventing a stub, pre-cooked framebuffer, fake interrupt or host-side simulation of a guest system call.
- Differentiate a tool, connector, launch, test-harness, or infrastructure failure from a firmware/hardware-model functional failure. A connector error never proves a code defect.
- Every run records commit, input/executable hashes (when they actually exist), image source, arguments, logs, machine-readable result, relevant CPU/IRQ/MMIO/framebuffer evidence, regression coverage and exact status.
- Each increment must not accidentally expand into GUI, SD, Palm Flash, OS3K patching, or unrelated AS2K work.
- No unsupported estimates or progress percentages. Continue exactly from the last **verified** checkpoint.

## 4. Universal Remote Desktop Commander rules — budget, identity and authority

**Static work and Git/Drive reading do not need Commander.** Commander is an expensive finite resource reserved for a remote action that truly must occur on the authorized T.

**Canonical worker binding** (from the active operating rules):
- Machine: **spc-HP-t640-Thin-Client**, operator **spc**, home **/home/spc**.
- **Mandatory explicit deviceId:** **dee0b4b6-578a-41a5-88de-73dbeb808983** in *every* Commander tool action for T; never rely on auto-selected devices.
- Root rights through **sudo -n** are a known persistent premise; never spend calls repeating hostname, pwd, ls, find, sudo -l, groups or online status merely as preflight.
- **Canonical launcher:** **/home/spc/.local/bin/dcjob launch**. Do not use dcjob-verified-launch (not installed), run-once as an invented substitute, alternative launchers, or assume an automatic polling service exists.
- **Authorization:** request **explicit approval** for the upcoming remote intervention and respect the approved per-intervention budget. No authorizations from prior chats, AS2K/other fronts, or prior increments carry forward. The standing universal maximum is **three Commander calls per authorized intervention**, **not three pre-authorized calls**; use **only what is needed**, ideally one bundled launch. A larger budget requires fresh explicit approval. Count rejected/error calls conservatively. If all three are exhausted without a successful execution, stop, mark **BLOCKED**, analyze statically and ask for new authorization before another remote attempt.
- **No Commander for** polling, listing files, retrieving logs, probing device connectivity, checking sudo, exploratory shell use, rerunning failed jobs blind, or rereading evidence that Drive or Git already exposes.
- If a remote connector error occurs, distinguish **BLOCKED_CONNECTOR** from a genuine offline machine or a failed test. Do not change launcher, queue, OS, service, device, or unrelated jobs as a reflex.

## 5. Mandatory Drive-first SH/queue workflow

Known stable infrastructure (from the user's canonical Drive operating records):
- rclone binary: **/usr/bin/rclone**; remote: **googledrive:**; local mount **/home/spc/GoogleDrive**.
- Root: **googledrive:AS2K_TEMP/COMMANDER_PIPELINE**.
- Directories: **inbox**, **outbox**, **archive**, **failed**, **hold**.
- Runner is **dcjob version 1.1** as last verified; dispatch via its canonical launch command.
- The **shared default inbox requires EXACTLY ONE** file with extension **.job.sh** for a launch. Zero means no job; two or more means launch aborts. There is no demonstrated scheduled automatic consumer.

Rules:
1. **Before scheduling/launching:** inspect the **Drive** queue, reconcile outputs/statuses for previous jobs, and ensure that the pending job is exactly ours; **never move, execute, overwrite or delete someone else's jobs**. Compare SHA-256 before treating a file as a duplicate; quarantine exact duplicates to hold rather than deleting.
2. Prepare a complete **self-contained** job, preferably syntax-checked beforehand. Make it do all deterministic work in one launch, with its own outputs, validation and clean error classification. Avoid fragile nested quoting and accidental variable expansion.
3. Use Git commit archives, isolated working folders and unambiguous paths. **Do not clean, reset, stash, reclone over, or alter another project's dirty worktree** to satisfy a Dana preflight. Do not assume the Dana checkout exists until verified as part of the first approved productive job.
4. After authorized launch, **never use Commander to poll**. Read result bundles, log, SHA/manifest and PASS/FAIL/BLOCKED status from Drive. A reported launch PID or rc=0 does not itself prove that the job executed or passed.
5. Keep Dana jobs isolated from AS2K job queues, evidence, and files. If the default shared inbox is occupied, **do not displace foreign work**; stage the Dana job elsewhere or wait for a properly configured independent queue, documenting the block. Do not invent a remote path or runner flag.
6. When compiling on T, always specify **-j3**, never an unconstrained full-host MAME build by default. Favor an isolated **reduced MAME** build.
7. Store all detailed evidence in Drive, not in chat history or Commander output alone. Only successful, independently confirmed changes should be integrated.

**Authoritative external operating records:**
- [T640 operational baseline](https://drive.google.com/file/d/1S8yb7WBiyfTGf8zfCZSPn357Gog3hCqV/view).
- [T640 dcjob rules 2026-10-09](https://drive.google.com/file/d/1lk1YaXw54KNfQdpRmILf2UEUUWkguJ26/view).
- [Commander canonical device binding](https://drive.google.com/file/d/1L1-LfkaDEP8SjPOYOKYzz2bNx8xQiA_U/view).

These documents describe **known premises**; do not spend Remote Desktop calls repeatedly proving them. If later verified evidence changes a premise, document the new canonical state.

## 6. Project boundaries, Git, and licensing

- **All future Git artifacts in English:** docs, README edits, file/symbol names, scripts, code comments, commit messages, PRs, issues, tests, CI/checkpoint output under our control. No retroactive bulk translation of Spanish historical artifacts without an independent relevant reason. Conversation remains Spanish. See [publication/language record](PUBLICATION_ASIDE_AND_GIT_LANGUAGE_20261013.md).
- **Git repository remains private** until the user separately chooses otherwise. Publication-readiness PR #1 and language-policy PR #2 did **not** change visibility. Publishing to GitHub, CI, official MAME, releases or package managers is never implicit.
- **Do not commit** commercial Dana/Palm/AlphaSmart ROM/Flash/updates, proprietary derivative firmware, personal media, private tokens/keys, user data, state images, test dumps or indiscriminately copied third-party code. Audit SPDX/licensing for files actually reused from MAME/POSE/Retro68/EmuTOS.
- **Do not touch** AS2K firmware, ROM Z stock, existing MAME AS2K, unrelated branches, the physical Dana, OS3K patching, Surface/Vontar/Armbian, Drive jobs belonging to other projects, or the status/cursor of another conversation's workflow.
- In a cross-project conversation, treat a Dana aside as **separate recorded information only**; never advance an AS2K increment because of Dana work or vice versa.

## 7. Immediate next task — D0.4 only

**Goal:** Define the **virtual CPU/bus state for entry into EmuTOS-Dana from a synthetic post-bootstrap RAM profile**, without confusing it with MC68VZ328 electrical power-on.

Required D0.4 deliverable (English Git document):
1. Precisely describe 4 MiB RAM, lower memory, vector table, write permissions, stack and overlap checks.
2. Characterize **PC / SR / SSP** and CPU handoff for direct emutos.img versus first-stage emutos-dana.rom. **Do not invent any unresolved values** inherited from Palm OS; define verified vs hypothetical state.
3. Separate Motorola official VZ reset values (manual plus addendum) from RAM/chip-select state configured by DanaRun/dbztool.
4. List first observable instructions, exceptions and MMIO touchpoints based on EmuTOS startup sources; define trace/checks that the future MAME test must produce.
5. Record unknowns for the future real image and emutos.map, source links, exact PASS criteria for a documentary SPEC_READY close, and D0.5 handoff.

**Explicit exclusions at D0.4:** no Commander, job dispatch, compilation, modification of MAME C++, guest execution, creation of a new MAME checkout, GUI, SD, booting real Dana, or OS3K patching.

## 8. Nonnegotiable self-audit before every response / tool use

- Did I read the latest canonical Git state and current cursor rather than rely on memory or an older message?
- Am I doing exactly the current increment, with no extra gates and no restart of closed work?
- Have I applied every active user constraint, including English Git and zero Commander without new authorization?
- Have I avoided duplicating source trees, rewriting unrelated projects, misrepresenting evidence, or treating a failed runner as product FAIL?
- Did I put durable results in Git and verify them by reading back? Did I preserve the next task and correct statuses?
- Am I explaining the actual result in Spanish, compactly, including precise link(s) and what is not yet tested?
- If there was a deviation/side task, did I record it separately, without changing the authoritative technical plan?

## 9. One-line continuation command

**User prompt in the new conversation:**

"Resume DANA-emu from D0.4. Read docs/CANONICAL_CONTINUITY_AND_RULES.md first, followed by HANDOFF, the authoritative incremental plan, the source lock and D0.3. Apply all universal AS2K/Commander/Drive rules and English-only Git. Continue only the static D0.4 increment without Commander or implementation."

**Never ask the user to reconstruct project history once these records are available in Git.**
