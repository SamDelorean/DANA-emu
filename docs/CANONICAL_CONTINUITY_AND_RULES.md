> **MANDATORY USER DIRECTIVE — 2026-10-22: EXACTLY THE TWO ORIGINALLY PLANNED DANA PRODUCTS, NO DERIVED INSTANCES.** The project has ONLY the original product identities **`dana-diag`** and **`dana-stable`**. **Only ONE INSTANCE of `dana-diag` is authorized and active now**, for all MAME/Dana source work, incremental compilation, peripheral integration and real tests. `dana-stable` is an original planned product, NOT authorization to build, activate, or maintain it at this stage; it requires a new explicit user decision. Absolutely **NO** additional isolated emulator versions, experimental/staging binaries, duplicated MAME source/build trees, per-attempt worktrees, copied compiled-object trees, or clones under new folder names. Apply F2, then F3, then F4 to the **same DIAG working directory**, reusing qualified objects/results and preserving evidence as concise logs/hashes in Git and the existing rector. Before any future native job, check its actual filesystem effects: scripts such as `tests/hold/016_f2_stylus_only_diag.job.sh` that call `cp -a` on the MAME tree or `tempfile.mkdtemp` for another whole working tree remain RETIRED. Do not sidestep this by calling an extra version a test fixture, cache, backup, or temporary isolation. Keep historical records and evidence intact; they are not additional authorized active products. User also forbids process polling/supervision. This directive overrides older text suggesting simultaneous dual-build work or isolated build staging.

> **DANA DIAG SINGLE-TREE CLEANUP VERIFIED — 2026-10-22.** User explicitly ordered removal of redundant Dana emulator versions. On canonical T, exact qualified DIAG binary SHA256 `caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37` and driver SHA256 `e8211be78dfb2bf4cdc0ccabd444c97d715dc37d189d4f113f2f1cbf05b573e2` were checked before deletion. **45/45 duplicate top-level work/build trees deleted** under `/home/spc/DANA_EMU_ISOLATED`; zero errors, zero remaining version trees; 334031769 bytes of evidence and small archive artifacts preserved in a *single evidence-only* directory `DIAG_EVIDENCE_ARCHIVE` with provenance manifest. Report: `/home/spc/DANA_EMU_ISOLATED/DIAG_EVIDENCE_ARCHIVE/CLEANUP_20261022.json` (status COMPLETE at 2026-10-22T15:03:48Z). Retained ONE qualified DIAG work tree `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769`, ONE verified original guest `/home/spc/DANA_EMU_ISOLATED/f1_e1e2_baldoi9k` and Git source repo `/home/spc/Projects/alphasmart/DANA-emu`. No standalone `dana-stable` or other Dana build trees remain in the audited root. No compilation, guest execution, process polling, or other project cleanup was done. This is a **storage/workspace cleanup, NOT new functional qualification**. Preserve existing historical native PASS scopes; F2 remains source-integrated but unqualified. **Future jobs MUST update this single DIAG worktree in place**, recording bounded evidence rather than duplicating MAME.

> **CURRENT USER OVERRIDE — 2026-10-22, DIAG ONLY / NO EXTRA WORKTREES.** The **sole authorized active emulator/work version is `dana-diag`**. All incremental peripheral changes must target **one canonical DIAG working source/build tree** and the same DIAG executable; do not generate per-increment isolated trees, duplicate full MAME builds, per-attempt source clones, temporary emulator variants, or parallel build workspaces. Previous per-job `cp -a`/tempfile staging logic in `tests/hold/016_f2_stylus_only_diag.job.sh` **violates this current policy and is retired; DO NOT RUN IT AGAIN**. Use small bounded logs, SHA receipts and Git history instead of duplicating a 1.5 GB MAME tree. Current clean-up on canonical HP t640: launcher PID 94023 was not running (ESRCH and /proc absent); only verified F2 attempt tree `/home/spc/DANA_EMU_ISOLATED/dana_integrated_hardware_j7xxm3xq` (~1.5 GB) and launch staging `/home/spc/DANA_EMU_ISOLATED/f2_stylus_single_WLcT8C` (~2.1 MB) were deleted. Original qualified cache and other historical evidence were not touched. The user has not authorized an automatic replacement attempt, cleanup of other trees, or another runtime campaign. Prior long-term descriptions of separate `dana-stable`/DIAG outputs are **not authorization to produce or maintain a second active version now**. Preserve historical claims as history, but apply this override for current work.

# DANA-emu — Canonical continuity, universal rules, and no-drift operating contract

**Status: ACTIVE / MANDATORY READING at the beginning of every new conversation.**
**Updated: 2026-10-14. Exact technical cursor: D1.2 (PENDING; no source or remote execution authorization). D1.1 = PASS (independent T-verified build/selectability only); D0.1–D0.6 = SPEC_READY, documentation only.**

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

**Implementation repository:** https://github.com/SamDelorean/DANA-emu (`main`; GitHub reported visibility `public` on 2026-10-14; this integration did not change visibility).
**Related research/firmware repository:** https://github.com/SamDelorean/Dana-OS3K.
**Existing MAME reference:** https://github.com/SamDelorean/mame-as3k (source lock in research/sources.lock.json).

Build an independent, reduced **MAME-based AlphaSmart Dana emulator** with **two separately compiled executable products from D1.1**, sharing **the exact same hardware emulation engine** and source snapshot. The builds must not depend on, share object directories with, overwrite, or modify AS2K MAME:

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
| **D0.4**, virtual RAM bootstrap CPU/bus state | **SPEC_READY, documentation only** | docs/D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md |
| **D0.5**, deterministic harness and traces | **SPEC_READY, documentary only** | docs/D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md |
| **D0.6**, frozen first MAME candidate | **SPEC_READY, documentation only** | docs/D0_6_FIRST_MAME_DRIVER_CANDIDATE.md |
| **D1.1**, two independent Dana machine builds | **PASS — build/selectability only** | [T R5 evidence](https://drive.google.com/file/d/1NLIydtsa6t2XTyeXG4SvleIZI-jfYeo7/view); [PR #5 qualification](https://github.com/SamDelorean/DANA-emu/pull/5#issuecomment-6179533751) |
| **D1.2**, 4 MiB guest RAM and 8/16/32-bit bus tests | **PENDING — not authorized** | [D0.4 contract](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md); no guest RAM test yet |
| **D1.3+**, VZ and guest functionality | **PENDING** | no guest-visible PASS yet |

**D1.1 has passed only its defined minimal MAME build/selectability scope:** two different real binaries (`dana-stable` and `dana-diag`) were built sequentially with `-j3` on T using Clang 21 and `PRECOMPILE=0`. Both independently passed `-listfull`, `-listxml` and `-validate` for `asmdana`, with staged source/list registration checks. This is **not a functional Dana guest emulator**: there is no MC68VZ328 SoC/MMIO model, guest RAM, LCD, keyboard, or successful EmuTOS-on-MAME run. No EmuTOS-Dana image SHA is available. D0.1–D0.6 remain documentary SPEC_READY, never functional PASS.

Historical facts to preserve:

- MAME pinned baseline is SamDelorean/mame-as3k commit **c4e48388ca620472643110db2941ce70aa5f3c07**, verified available read-only in T at `/home/spc/Projects/alphasmart/as2k-stable-eeepc900-local/mame-as3k-donor`; use new Dana-owned staging for builds, never compile inside this donor checkout.
- EmuTOS-Dana commit **9c42ef0f2c2fa9d1e217fced9da68901b2326e8b**, source target **make dana**; outputs **emutos.img** and **emutos-dana.rom**, not a physical Dana Flash ROM.
- The historical Dana RAM booter copies EmuTOS to **0x00002140**, then jumps there; that address and image length must be validated against the exact build map before execution. Historic loader limitation approximately **256 KiB**, with alignment/coverage constraints, is recorded in D0.3.
- First intended guest RAM profile is **4 MiB**, from **0x00000000 through 0x003FFFFF**, in a **post-bootstrap** state. Do not confuse this with physical reset/power-on.
- The historical specific-Dana POSE adaptation is in **csnover/Retro68**, including EmRegsVZAlphaSmart and EmSPISlaveSTMicro; generic VZ registers are in POSE EmRegsVZ; Neo firmware-first reference is **ioma8/neo-re/alpha-emu**, *not a MAME NEO driver*. Review licensing before copying.
- VZ vs EZ MMIO **must** follow Motorola UM/addendum; especially chip selects, DRAM, SPI1 (16-bit data), SPI2/ST, timer/IRQ and LCD LRRA differ. Do not reintroduce corrected reset-value errors from POSE.

## 3. Strict increment lifecycle: one question, one verified result

**Canonical sequence:** STATIC_FIRST / source reuse → define one limited increment → freeze source and expected behavior → secure the required explicit execution approval → create a single self-contained SH job (when local execution is needed) → dispatch on canonical T → retrieve evidence **through Drive** → independent PASS / FAIL / BLOCKED → integrate only verified PASS → move forward.

Detailed authoritative milestones are in **docs/DANA_EMU_INCREMENTAL_WORK_PLAN.md**. They must **not** be collapsed into larger vague "gates" or reorganized ad hoc.

Before product changes, define: current cursor, one technical objective, dependencies, exact files allowed, source/base SHA, guest fixture, expected signals, bounded instrumentation, reproducible commands, functional test and regression coverage, failure/rollback behavior, and evidence location.

- **D0 documentation:** SPEC_READY closes a source-audited specification, **not** functional testing. Advance only from the latest verified D0.x specification to the next planned D0.x task; no functional PASS is implied.
- **D1.1 exception specified in its frozen acceptance contract:** PASS means *both real, separately compiled executables* register/select/validate the minimal nonworking driver on T; no guest can run yet. **D1.2 onward:** actual guest-visible evidence on T (or an expressly approved substitute) is mandatory for memory/peripheral behavior; compilation and CI structural checks alone are insufficient. FAIL and BLOCKED record exact causes.
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
3. Use Git commit archives, isolated working folders and unambiguous paths. **Do not clean, reset, stash, reclone over, or alter another project's dirty worktree.** Verified persistent Dana Git checkout on T: `/home/spc/Projects/alphasmart/DANA-emu` (D1.1 tested head `92e39eff050fa7a62486569be6a34994682ce44c`; T checkout requires normal refresh after GitHub merges). Disposable builds belong under `/home/spc/DANA_EMU_ISOLATED`, outside the read-only MAME donor.
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
- **Repository visibility:** GitHub reported `public` on 2026-10-14; this documentation/integration operation **did not change visibility**. Do not infer authorization to modify visibility, publish binary releases, submit upstream MAME changes or distribute firmware. Private ROMs, credentials and saved state remain excluded regardless of visibility.
- **Do not commit** commercial Dana/Palm/AlphaSmart ROM/Flash/updates, proprietary derivative firmware, personal media, private tokens/keys, user data, state images, test dumps or indiscriminately copied third-party code. Audit SPDX/licensing for files actually reused from MAME/POSE/Retro68/EmuTOS.
- **Do not touch** AS2K firmware, ROM Z stock, existing MAME AS2K, unrelated branches, the physical Dana, OS3K patching, Surface/Vontar/Armbian, Drive jobs belonging to other projects, or the status/cursor of another conversation's workflow.
- In a cross-project conversation, treat a Dana aside as **separate recorded information only**; never advance an AS2K increment because of Dana work or vice versa.

## 7. Immediate next task — D1.2 (not authorized for implementation)

**D1.1 is CLOSED/PASS for build/selectability only.** PR [#5](https://github.com/SamDelorean/DANA-emu/pull/5) was merged after the independent T R5 qualification and PR [#4](https://github.com/SamDelorean/DANA-emu/pull/4) separately integrated English documentation. The validated pre-merge implementation head is `92e39eff050fa7a62486569be6a34994682ce44c`, with MAME pinned at `c4e48388ca620472643110db2941ce70aa5f3c07`. The R5 Drive evidence package is [here](https://drive.google.com/file/d/1NLIydtsa6t2XTyeXG4SvleIZI-jfYeo7/view), SHA-256 `2f697fdffb381b3ed2f82dba596a528a5fa8aa88be07735247b608f64a3847ff`.

- Stable executable SHA-256: `ec055d08b66d46181d26cd9371f7f961f52732ad36f468a8aae0a4e1b7bc83d1`.
- Diag executable SHA-256: `dd877c9cb36c491e675b82ce2aba78548519cccf2bd16bf2a9c61cbd3000435c`.
- Reproducible T toolchain choice: Clang 21, `OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++ PRECOMPILE=0`, separate source/output stages, sequential `make -j3`; diagnostic variant adds `DEBUG=1`. GCC 15 failed building GENie and Clang PCH failed, both bypassed without modifying source.
- The validated skeleton remains `MACHINE_NOT_WORKING | MACHINE_NO_SOUND`, with placeholder M68000 at 1 MHz; no guest RAM, VZ, LCD, keyboard, loader or guest-runtime PASS is claimed. See [D1.1 implementation and qualification](D1_1_IMPLEMENTATION_CANDIDATE.md).

**Next exact technical increment: D1.2 — 4 MiB RAM and 68k 8/16/32-bit read/write semantics only.** Begin with static source/D0.4 contract inspection, define a bounded guest fixture, big-endian ordering, alignment and access boundaries, regression of D1.1 selection, and explicit PASS/FAIL/BLOCKED criteria. No VZ MMIO, firmware loader, fabricated guest responses or expanded hardware features in D1.2. Implementation and any T/Commander job require new, separately scoped user authorization; every prior five-call budget is exhausted. `Siguiente` does **not** authorize code writes, a remote run, publication, or new Git merges.

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

"Resume DANA-emu at D1.2 PENDING. D1.1 is closed PASS for dual-build/selectability only (R5 on T; PR #5 merged). Read canonical continuity, HANDOFF, master plan, D0.4, D1.1 evidence and source lock. Prepare the static D1.2 RAM/bus contract first; ask for fresh approval before source implementation or any T/Commander run. No previous Commander budget carries over."

**Never ask the user to reconstruct project history once these records are available in Git.**
