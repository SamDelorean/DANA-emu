# DANA-emu — General Work Plan

> **D7/D8.3 INTEGRATED SPI1 / DUAL SD SOURCE — 2026-10-24: IMPLEMENTED / STATIC_PASS / NATIVE_PENDING.** On canonical main ancestry `4275fb76156a6b8e41d60935142ed7d28eb9c8b0`, integrated the VZ six-register SPI1 controller, bounded TX/RX FIFOs, per-bit scheduler and ILCR/PD interrupt path with two independent read-only raw sector-image devices (`-sd1` slot0, `-sd2` slot1). Power/CS follow PB5/PJ3 and PK5/PF2 with GPIO direction/selection. SD initialization/CSD/CID/CRC/SDSC-SDHC/sector and multiblock reads, absence, explicit WP rejection and media-bound saved state are implemented. PD2/PD3 are independent raw electrical inputs: pinned sources do not prove insertion circuitry/polarity, so no insertion interrupt is fabricated. Existing Flash/RESET/RAM/LCD/ST/SPI2/pen/timer/UART bodies and GUI-025/026 patches preserved; PB/PK only add SD notification. **12/12 new scoped static tests PASS**, including complete driver MAME-header syntax, six protocol/FIFO constant-check groups and actual extracted GPIO/IRQ logic. No native CPU SD execution, object/executable, Commander/T call, MAME/EmuTOS build, new branch/tree/clone or job launch. Installed D8.5 source/binary remain the user-reported baseline; see [integrated code and limits](D7_D8_3_SPI1_DUAL_SD.md), [immutable result data](../tests/d7_sd_status.json) and [actual static log](../tests/d7_sd_static.log). Read-only is the only implemented SD policy; writable media/SDIO/test/sample modes remain unsupported. EmuTOS is unchanged and uses only slot0. Next single action: fresh authorization for one incremental build and scoped dual-SD native campaign on the same installed DIAG. Prepared records target the SAME rector workbook; no spreadsheet was edited or replaced.

> **D8.5 implementation directive, 2026-10-24:** The user now authorizes one integrated physical firmware/reset implementation on the published canonical DIAG source. This supersedes earlier deferral/inventory-only wording for this task. Keep existing peripherals and R-direct, preserve closed GUI026, and create no additional emulator/tree/branch. The source candidate is implemented and statically checked; native qualification remains PENDING. See [D8.5 code/results and supported limits](D8_5_PHYSICAL_BOOT_IMPLEMENTATION.md). No Commander/T/build/run authorization is implied.

> **Binding update (2026-10-24):** DANA-emu is an independent hardware-faithful AlphaSmart Dana emulator, not an EmuTOS product or solely an OS3K development accessory. Original Dana Palm OS execution and physical cold boot are first-class fidelity targets. If EmuTOS does not exercise a hardware function, investigate original Palm OS and verified hardware behavior; do not polish EmuDesk as a substitute. Preserve EmuTOS 024C and CLOSED GUI-025/026 regression evidence. Next: static driver-versus-real-Dana/Palm-boot gap inventory, then the smallest evidenced hardware increment. Retain single DIAG, no isolated branches, no extra master spreadsheet and no remote execution without fresh authorization. Existing D0–D8, D8.5 and I0–I6 milestones remain in place.

**Project:** Reduced AlphaSmart Dana emulator and firmware engineering test bench  
**Implementation repository:** [SamDelorean/DANA-emu](https://github.com/SamDelorean/DANA-emu)  
**Technical foundation:** MAME, Motorola MC68VZ328 (DragonBall VZ)  
**Document purpose:** Permanent project direction, development methodology, responsibilities, functional roadmap, and non-negotiable controls  
**Established:** 2026-10-17  

**Cross-project direction (2026-10-23):** [OS3K-Dana Integrated Master Work Plan](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/INTEGRATED_MASTER_WORK_PLAN.md) is the single product-level map joining Dana OS3K, emulator, AS2K/Pro bootstrap reuse, SD/backup, power and safe installation. This repository continues to own **only emulator implementation and DIAG qualification**, and its strict single-DIAG/Commander/functional evidence rules are not overridden by cross-project architecture. This is conceptual scope only.
**Status:** General plan. Live results, open blockers, binary identities, and the next authorized action belong in the current [DIAG-FIRST execution ledger](DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md), not in this document.

## Binding emulator-testing exclusivity — 2026-10-17 (user directive)

**ONLY `dana-diag` is authorized to execute emulator/runtime tests.** `dana-stable`, reference MAME, release variants or any other emulator are **prohibited**. The **`asmdana`** system selector running inside `dana-diag` is permitted; `danadiagd` is the compilation intermediate of the same DIAG-only subtarget, not an independently authorized emulator. Static source inspection and standalone C++ register logic checks are permitted but do not qualify as emulator tests. All functional smoke, RAM, MMIO, and real EmuTOS tests must execute exclusively an SHA-identified staged `.../diag/bin/dana-diag` binary; any ambiguity is **BLOCKED**.

This overrides older plan references to stable/diag parity. See [mandatory test policy](DANA_DIAG_EXCLUSIVE_TEST_POLICY.md). **D2.1 PLLFSR run authorized with a maximum of three Commander calls**; not authority to run alternative emulators.

## Mandatory retrieval-first Codex research — user directive 2026-10-17

**Codex MUST proactively read the known project and reference repositories at their pinned revisions before implementing code. The assistant MUST place as much relevant, already verified source context as practical directly inside every copyable Codex prompt.** These are complementary obligations, not alternatives.

- Start with this repo's `research/sources.lock.json` (canonical catalog of known repositories, commit SHAs, paths and licenses), `docs/D0_2_EZ_VZ_REGISTER_CONTRACT.md`, `docs/HANDOFF.md`, `docs/DANA_DIAG_EXCLUSIVE_TEST_POLICY.md`, plus the current branch source and latest exact Drive evidence. Read source first; do not repeat the source-recovery research or overwrite a qualified stage.
- Every Codex prompt must name **specific relevant repos, immutable commit, file paths / pinned URLs, and exactly what to extract or compare**. Prioritize Motorola MC68VZ328UM/D + addendum for register truth, original EmuTOS-Dana for actual hardware accesses, POSE/Retro68 for known device behavior, pinned MAME for permissible APIs/patterns, and dbztool for post-bootstrap context. Include verified current register address/width/PC/data/mask, previous PASS and remaining uncertainty directly in the prompt.
- Codex must actually **fetch/read available source files at those pins**, not substitute general knowledge, fabricate conclusions or merely acknowledge the links. Return a **source-to-claim evidence table** with source/path/commit and differing values or uncertainties; specify any inaccessible file honestly and use only explicitly included verified extracts or accessible alternatives. Never invent missing manuals, resets, peripheral behavior or execution results.
- Read secondary-source code for behavior, but respect GPL and per-file license boundaries; **do not paste GPL-licensed POSE/Retro68/EmuTOS code into MAME** unless verified license-compatible. Implement independently from specifications and behavioral understanding.
- Keep source discovery bounded to the hardware increment; no broad irrelevant repo sweeps, no compiling other emulators, no relaunch of already completed T/ROM stages. For DANA-emu, **runtime tests ONLY `dana-diag`**.
- Deliver the exact user-visible Codex prompt on every proposed delegation (see next section). Issue/PR attachments and pointers supplement, never replace the prompt.

**Research index:** [`research/sources.lock.json`](../research/sources.lock.json). When a pin changes, document the reason, the new identity and the comparison instead of silently following a mutable branch.

## Mandatory Codex handoff — user directive 2026-10-17

**Whenever the assistant proposes, prepares, assigns, or invokes work for Codex, the user must receive the EXACT, complete, actionable Codex prompt in the chat, ready to copy and paste.** This is a persistent user-level workflow rule, not limited to this project or issue.

1. Begin from the real current state: repository, target branch/PR/issue, last qualified evidence, hard constraints, the specific next incremental goal, and no rework of completed stages.
2. Deliver the **entire literal prompt** in a single clearly delineated copyable block, **not merely a task summary or GitHub issue link**. Specify source/provenance, implementation boundaries, tests, acceptance and deliverables, and what the agent must not do.
3. An issue, PR, or handoff document supplements the prompt but **never replaces giving the prompt to the user**. Give the prompt in the same assistant response as the proposed Codex handoff, **before any Codex execution**, when such execution is available.
4. If Codex invocation is not actually available through connected tools, mark the task **PROMPT_READY / CODEX_NOT_INVOKED**; do not imply issue creation or documentation means Codex has run. The user may copy the prompt into Codex. Never promise future asynchronous completion.
5. Preserve the user's **Dana DIAG only** runtime rule, Commander budgets, Drive-first immutable/private ROM policy, STATIC_FIRST source and evidence checks, and existing release/test gates. No fake product-level PASS from synthetic checks.
6. After genuine Codex work appears, compare the implementation to this exact prompt, review the diff and only then run the authorized native DIAG campaign. Avoid creating an excessive series of microtickets.

For the currently prepared post-D2.1 work item, use [Codex-ready issue #9](https://github.com/SamDelorean/DANA-emu/issues/9) as the supporting technical contract. The exact prompt must still be printed to the user.

## 1. Mission and definition of success

Build a **working, reduced AlphaSmart Dana hardware emulator**, using **existing MAME infrastructure and previously identified MC68VZ328/Dana implementations rather than developing an emulator from scratch**.

**Primary and definitive program goal: develop and validate OS3K-Dana**, an adapted AlphaSmart NEO/OS3K firmware intended eventually to replace Palm OS on Dana hardware, while retaining OS3K's user experience and pursuing SmartApplet compatibility. The DANA-emu product is the **engineering emulator and eventual execution environment for OS3K-Dana**: it must execute genuine guest instructions, expose CPU and memory, diagnose MMIO/IRQ/peripherals, reproduce test cases, and qualify the future OS3K-Dana boot and application behavior. **EmuTOS-Dana is the present reference/bring-up guest; Palm OS is a fidelity/reference guest and bootstrap source, neither is the ultimate operating-system deliverable.** Firmware patching remains in the separate `SamDelorean/Dana-OS3K` repository.

The first guest reference is **EmuTOS-Dana loaded into RAM**.

**Guest-image acquisition priority (user directive, 2026-10-17):** Before setting up any MiNT/bare-metal toolchain or recompiling EmuTOS-Dana, search for an **existing, legally redistributable and source-identifiable prebuilt Dana-specific image** (`emutos-dana.rom`, often renamed `kernel.img`, and/or `emutos.img`), including matching linker map, symbols or independently recoverable entry/layout evidence. The official Atari/Amiga/FireBee EmuTOS binaries are not substitutes for the Dana port. Treat any found file as untrusted input: check its provenance, hash, size, embedded image and RAM/entry compatibility without claiming it matches the pinned source unless that is established. If a compatible image exists, adapt the F1 input/validation pipeline **without requiring a compiler or fabricating a linker map**. **Only compile EmuTOS if this targeted search fails or a candidate cannot be validated**, recording the exact blocker. Keep this binary-first preference in every future F1 handoff and do not create a new microincrement for it. It is an observable hardware workload and a source of peripheral expectations; **EmuTOS is not the ultimate product, a replacement for the hardware model, or a reason to implement Atari/Palm OS in the host**. After qualifying the required hardware model, the same emulator may be used to test independently developed OS3K-compatible firmware under a separately approved workstream.

**Successive functional outcomes, not the number of commits, test scripts, registration checks, or individual register edits, measure progress.** The first substantial milestone is real guest instruction execution; the first visual milestone is a framebuffer generated by the guest; the first interactive milestone is host keyboard input traversing virtual Dana hardware and affecting guest output.

Not required for the first functional emulator: complete Palm OS emulation, authentic physical Flash/cold boot, a full MAME distribution, upstream MAME acceptance, a polished daily-use UI, or every optional Dana peripheral.

### Explicit future objective: physical Dana-to-EmuTOS boot fidelity (user directive, 2026-10-23)

**Committed future product scope, DEFERRED / NOT IMPLEMENTED.** After the current native EmuTOS desktop keyboard-and-stylus interaction milestone, evolve the SAME Dana hardware model and the SAME `dana-diag` development executable to reproduce the original machine's complete boot and OS transition, as faithfully as available hardware evidence permits. This supersedes the historical "optional" status of D8.5; it does **not** move the current execution cursor, authorize Commander, or create a prerequisite to finish interactive EmuTOS.

Expected real-hardware sequence (separate **physical-boot** profile):
1. Hardware-equivalent VZ reset, initial vectors, RAM/Flash/chip-select decode, peripherals, timing and firmware entry; avoid host-only jumps into EmuTOS.
2. Run genuine, lawfully obtained **Dana-specific Palm OS firmware** from an appropriately modeled virtual Flash/storage environment, until its launcher and required services work through actual guest CPU/peripheral execution.
3. Provide **two distinct virtual SD-card slots**, each backed by its **own user-selected sector-image file**, representing the Dana's original left/right slots. The host GUI must be able to browse/open a disk image independently for each slot, show its selected image/path and inserted/ejected status, choose read-only or read/write use, and retain per-slot assignments across application restarts. Mount/eject/image replacement must respect guest media state and protect host images from corruption; implement safe write flush, clear failures for missing/corrupt images, and a reversible eject workflow. The guest must access its cards through **emulated VZ SPI/GPIO/card-select/detect hardware**, not an invented host-side file API.
4. Launch the authentic **DanaRun.prc** application under Palm OS using the virtual SD accessible from its original left-side slot; `/kernel.img` holds the EmuTOS-Dana bootloader package. The original port's separate right-side TOS-formatted SD must be represented as a **second independent inserted card**, not a second filename on the first image. Validate exact physical slot-to-controller pin mapping before freezing the driver: logical left/right labels are grounded by the original port's usage instructions, but register/CS assignments must not be guessed.
5. Verify actual DanaRun RAM block loading, Palm-to-supervisor transfer via trap #0, embedded `danaboot.S` relocation of `emutos.img` to `0x00002140`, and real CPU execution of the relocated guest.
6. Demonstrate the resulting EmuTOS LCD desktop, keyboard, stylus and **card access actually supported by the guest** and compare meaningful checkpoints against sourced original hardware behavior; preserve authentic cold reset to Palm OS. Both slots must exist as physical virtual devices even though the historical EmuTOS-Dana port documents usable support for only one slot.

**Dual-SD user-facing contract (2026-10-23):** support at minimum validated raw sector images with compatible guest-recognizable on-disk layouts (e.g., the FAT layouts required by Palm OS/VFS and EmuTOS's supported SD path); do not assert every SD image format or filesystem will be accepted. Prefer reuse of existing MAME removable-media/image-device facilities rather than inventing another emulator, nested media tree, or host-side FAT shim. Host browsing/image selection is a product feature to be implemented later, not a claim that a UI exists today. Keep virtual card contents strictly separate from the commercial Palm firmware/Flash image and from the direct EmuTOS `.dana` quickload package. Pair this future work with D7 storage and D8.3 second-slot hardware on the way to D8.5; do not defer one of the slots out of the **full physical boot** end-state, and do not make either slot a prerequisite for the currently pending GUI-input proof.

**Acceptance is end-to-end observed CPU/bus/firmware execution, not a scripted state change or direct-RAM shortcut relabeled as a physical boot.** Keep the already-qualified **direct post-bootstrap RAM mode** as a fast, independent DIAG profile for focused regressions. Reuse proven shared peripherals; do not create a second emulator or isolated MAME tree. Original commercial ROMs/Flash dumps and any private user data must remain outside public Git; firmware availability, permissions, dump provenance and licensing are separately checked when activating this future task. Formalize functional increments under D8.5 only after the current interactive GUI task; do not create speculative gates now.

### Final product scope: AS2K-analog diagnostic bootstrap and user interface (user directive, 2026-10-23)

**COMMITTED FINAL-PRODUCT REQUIREMENT / DEFERRED, NOT IMPLEMENTED.** The finished Dana emulator will expose ordinary guest operation and a genuine diagnostic ROM/payload execution workflow within the same qualified MAME/Dana hardware model. Use the AS2K emulator's *architecture and human-interface pattern*, not HC11-specific bootstrap instructions, binary formats or keyboard layout. First continue the already active `dana-diag` EmuTOS keyboard/stylus interaction task; do not open a parallel build or change the existing verified executable for this documentation decision.

**User-selectable internal firmware and operating-system profiles (required final capability; 2026-10-23):** The GUI shall expose `Archivo → Abrir imagen ROM/Flash interna…` (or equivalent AS2K-style firmware selector) and a clear `Máquina → Sistema de arranque` selector for **Palm OS, EmuTOS-Dana, OS3K-Dana (primary project target), and Diagnostic ROM**. A single *emulated internal firmware/Flash device* loads the selected **compatible** Palm or OS3K firmware image for a cold-reset profile; avoid inventing multiple physical ROM sockets. The selected image's source path, type/profile, full-size/hash, layout, reset vectors, chip-select/Flash mapping and read-only or safe copy-on-write semantics must be validated against the actual Dana hardware model. The existing Dana Palm updater `Flas` resource reconstruction is **not proven to be a complete bootable Flash dump**, so an arbitrary updater package must not be silently accepted as one. Never commit commercial firmware bytes or private images to public Git. Switching firmware/profile is applied only upon a deliberate machine reset, with a clear prompt about volatile RAM/state as appropriate; each OS/profile's persistent guest memory and optional snapshots remain isolated, while the independently chosen left/right SD-card images can be retained as configured.

**EmuTOS-Dana is an *OS choice* in that same UI, not necessarily an internal Flash ROM**: its source-authentic implementation runs from RAM using either the already qualified direct post-bootstrap `.dana` loader or the full Palm OS → DanaRun → SD `/kernel.img` chain. The UI must report the actual chosen EmuTOS boot method, not label a RAM shortcut as stock Flash boot. **OS3K-Dana is a prospective internal-firmware target**; until a real patched image and proven VZ/Flash/boot map exist, the selector can describe a future image slot but must not claim OS3K boots. Images accepted as firmware, diagnostic payloads, EmuTOS RAM packages and SD disk images are different artifact types with separate validation and error messages.

**Boot/guest profiles exposed by one application:**
- **Normal Dana / Palm OS:** select a validated original Dana internal Flash image and perform authentic VZ/Flash reset, stock Palm launcher and normal device state (future D8.5).
- **EmuTOS-Dana:** select an original EmuTOS RAM payload for direct post-bootstrap launch, or select the authentic Palm-to-EmuTOS route where Palm OS executes DanaRun from the original SD arrangement, bootstrap/TRAP #0 and RAM relocation are real (future D8.5).
- **OS3K-Dana / primary target:** choose a future patched OS3K firmware image, validate its own reset vectors, physical Flash/RAM map, bootstrap and VZ peripheral contract, and run its real 68k code, GUI/text editor and SmartApplet/OS3K compatibility tests. Its firmware image is defined and produced in the independent DANA-OS3K project; its hardware behavior is validated by DANA-emu, not faked by host OS calls.
- **Diagnostic ROM/bootstrap:** choose an authorized external Dana/68k diagnostic firmware image or payload, validate its size/layout/addressing/SHA, establish an explicit reproducible VZ CPU/RAM/vector/SP/PC entry contract, and execute *real guest instructions* with MMIO/IRQ/peripheral traces. Reuse AS2K's diagnostic trust-chain ideas (minimal entry, monitor, escalating tests, bounded logs), but **the HC11 Special Bootstrap mode cannot be assumed to exist on MC68VZ328**. Determine whether the Dana-specific implementation uses a supported hardware boot mechanism, an emulated ROM/Flash profile, or an explicitly marked host-assisted RAM diagnostic loader; never label the latter an authentic physical cold boot. Select/apply this profile at an explicit reset, not an unannounced hot swap of CPU PC or Palm firmware.
- **EmuTOS direct-RAM:** preserve the existing separately identified fast post-bootstrap `.dana` loader for deterministic regressions and development.

**AS2K-analog GTK user interface:** the **internal ROM/Flash image + system boot-profile selector** is a primary user-facing operation, not merely a debug command; it must show the current firmware identity and the next-reset pending image/profile, alongside both independently selected SD images. Inspect/reuse compatible patterns from `SamDelorean/AS2K-Emulator` `stable/frontend/as2k_ui.py`, `stable/frontend/as2k_session.py`, `stable/docs/UI_CONTRACT.md` and `stable/README.md`; **adapt rather than blindly transplant** AlphaSmart 2000 hardware semantics. The Dana product UI must provide a 560x160 guest-driven monochrome LCD at correct aspect ratio, host keyboard mapping and clickable *Dana-correct* special keys, genuine pen/mouse mapping, an always-visible menu bar (`Archivo`, `Máquina`, `Ver`, `Configuración`, `Ayuda`), 100%/200%/300% and full-screen presentation, coherent status, start/reset/pause where technically supported, separate selectors for Palm/Flash firmware, diagnostic ROM/payload, direct EmuTOS guest image and both independently inserted SD sector images, plus session/configuration management. Preserve AS2K's conceptual screenshot/recording support and native frontend integration when adapted to Dana. Do **not** reproduce AS2K-only F1–F8/Spell/Send controls or PC/IR/printer behavior without an actual equivalent Dana signal/path.

**Storage and recovery:** retain image selections and per-slot read-only/read-write + insertion state across launches; offer a default persisted guest RAM/state artifact in the working/user-data directory and an explicit selection of an alternate artifact. Distinguish a normal retained battery-backed guest memory image from an optional full machine snapshot (CPU/MMIO/peripheral state), and protect guest data during SD eject/write flush and forced application close. A diagnostic ROM is never to be treated as the same file as Palm firmware, an SD image or a `.dana` RAM guest.

**Acceptance and project sequence:** the principal end-to-end acceptance target is **real OS3K-Dana guest firmware execution** using the validated Dana virtual hardware and an independently supplied patched image, including boot, LCD, keyboard, pen and applicable SmartApplets; source-only hooks, pre-rendered OS screens and a fake PC jump do not count. The currently active immediate objective remains genuine EmuTOS GUI keyboard/pen interaction; implementing the selector or completing Palm OS full boot must not become an artificial prerequisite for that current milestone. Selection of Palm OS/OS3K internal firmware and EmuTOS guest boot options is a committed future D6.6/D8/O0 UI and firmware contract. Functional DIAG ROM mode requires a verified guest 68k entry, recorded PC/SP/SR, ROM or RAM mapping, observable real diagnostics and an isolated PASS/FAIL from guest-origin events. GUI acceptance requires real keyboard/pen state changes, correct image selections/scaling/persistence/restart and accurate hardware semantics, not a static host-drawn skin. The final delivery must retain direct RAM testing *and* support the full Palm-to-EmuTOS path, with the diagnostic bootstrap profile independently selectable. Implement GUI product packaging under D6.6, two SD slots under D7/D8.3, Palm-to-EmuTOS under D8.5, and diagnostic ROM/bootstrap under D8.6; the ordering of the latter two may be chosen later by proven dependencies, not new artificial gates. Until a separate user decision, only the **one existing `dana-diag` tree and executable** are active; `dana-stable` remains deferred. Commercial firmware, private user images and RAM contents stay out of public Git.

## 2. Governing source material — reuse is mandatory

Before writing a hardware implementation, compare the desired behavior against **the already completed D0.1–D0.6 research** and the exact pinned sources in [research/sources.lock.json](../research/sources.lock.json). Those documentary increments remain **SPEC_READY**; do not repeat their research absent concrete contradictory evidence.

| Authority or implementation | Assigned use |
| --- | --- |
| [Motorola MC68VZ328UM](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf) and [official addendum](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf) | Hardware authority for register addresses, access widths, reset values, bits, exceptions, and corrected specifications |
| [SamDelorean/mame-as3k](https://github.com/SamDelorean/mame-as3k) at pinned commit | **Emulation engine**: native M68000, bus/address spaces, scheduler, debugger, DragonBall MC68328/EZ peripherals, screen/LCD infrastructure, serialization and machine integration |
| [POSE / EmRegsVZ](https://github.com/cloudpilot-emu/pose-original) | Reference for MC68VZ328 device behavior, initialization, interrupts, PLL, timers, UART, SPI, GPIO and LCD |
| [Retro68 / POSE Dana](https://github.com/csnover/Retro68) | **Dana board model**: VZ-to-Dana GPIO, ST auxiliary keyboard microcontroller, SPI2 communication, ADC and display-related hardware |
| [davidgiven/emutos, dana branch](https://github.com/davidgiven/emutos) | Real guest initialization and transactions; reproducible RAM image build, bootstrap, IRQ/timer/UART, LCD, ST keyboard and optional SD paths |
| [davidgiven/dbztool](https://github.com/davidgiven/dbztool) | Observed DRAM/chip-select/bootstrap configuration, never a generic license to manipulate physical hardware |
| [ioma8/neo-re](https://github.com/ioma8/neo-re) and NEO/NEO2 research | Secondary VZ and engineering references only where hardware behavior actually overlaps; do not import NEO-specific LCD/keyboard assumptions into Dana |
| [DANA-OS3K research](https://github.com/SamDelorean/Dana-OS3K) | Existing theoretical hardware/firmware evidence; remain separate from emulator implementation |
| [D0.1 reuse audit](D0_1_MAME_VZ_REUSE_AUDIT.md), [D0.2 EZ/VZ contract](D0_2_EZ_VZ_REGISTER_CONTRACT.md), [D0.3 EmuTOS loader](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md), [D0.4 RAM contract](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md) | Already-established engineering decisions and test assumptions; consume rather than recreate |

**Reuse method:** identify the exact MAME primitive or device and its existing tests; compare it against the VZ manual/addendum, POSE/Retro68 behavior, and actual Dana guest accesses; reuse compatible MAME implementations, adapt only demonstrated VZ/Dana differences, and test the resulting guest-visible behavior. Keep MC68328/EZ and AS2K behavior unchanged.

**Licensing is a real constraint:** MAME components have file-specific licenses, POSE/Retro68/EmuTOS may be GPL, and other references may have unknown reuse permissions. A technical reference is not permission to paste code. Review licenses/SPDX and use properly licensed reuse or independently implemented behavior from hardware specifications. Never add proprietary firmware, credentials, private images or unapproved third-party source to the public Git repository.

## 3. Permanent system architecture

Build **one faithful, shared Dana hardware model** based on MAME; develop and qualify its DIAG target first.

1. **Native M68000 execution:** reuse the existing MAME processor, exceptions, registers, debugger and bus mechanisms. Do not write a replacement 68k interpreter.
2. **Memory and MC68VZ328 SoC:** preserve the already verified 4 MiB RAM/bus contract; implement correct 32-bit high-address VZ MMIO, byte lanes, widths and documented reset/side effects. Reference both canonical 0xFFFFFxxx and any documented aliases only under their correct hardware conditions.
3. **Clock and interrupt system:** PLL, source masking/pending, vector delivery, acknowledgments and Timer1 according to the VZ model and guest demand. Reuse MAME scheduler/timer/IRQ machinery.
4. **Communications and board peripherals:** UART1 as required for the guest; SPI2 plus the Dana ST controller and its GPIO lines for keyboard; SPI1/SD only when the selected real guest path actually requires it.
5. **Display:** VZ LCD controller state, LSSA addressing, framebuffer read from **guest RAM**, Dana 560 × 160 monochrome format, line/bit ordering, refresh and required LCD power GPIO. A host-painted placeholder is not a functional PASS.
6. **Guest loading and execution:** a documented RAM/post-bootstrap profile first; later, if explicitly selected and evidenced, an authentic power-on/Flash profile. Never claim the RAM profile is physical cold boot.
7. **Diagnostic control:** native CPU/memory/MMIO/IRQ/SPI traces, bounded instrumentation, snapshots and machine-readable tests. Probes must not alter the guest-visible behavior.
8. **Future everyday-use product:** dana-stable derives from the proven shared hardware model only after a separate user decision; no parallel stable build or parity gate during current DIAG development.

The final emulator remains a reduced, Dana-specific machine, **not a second general-purpose emulator and not a repackaging of entire third-party emulators**.

## 4. General development roadmap — functional deliveries

The detailed D1–D8 identifiers and per-capability test contracts in [DANA_EMU_INCREMENTAL_WORK_PLAN.md](DANA_EMU_INCREMENTAL_WORK_PLAN.md) remain traceable. The stages below group closely related work into **useful Codex deliveries**. Grouping eliminates unnecessary conversational/code-line rounds but does not allow skipping an independently required functional test or a real dependency.

### Stage A — Existing foundation and first real guest execution

- Preserve completed source research, historical D1.1 machine selection/build evidence, and independently qualified D1.2 RAM/bus behavior.
- Repair localized harness/toolchain defects inside the same implementation delivery; do not turn a stale assertion into a separate development program.
- Adapt MAME DragonBall components into the VZ register/bus foundation needed by the guest, using the pinned D0.2 hardware comparison.
- Build the historical EmuTOS-Dana target with its pinned toolchain recipe, obtain actual images, hashes and link map, and verify placement.
- Introduce a transparent, deterministic **post-bootstrap RAM loader** and run genuine guest instructions until a reproducible unsupported device or behavior is observed.
- **Acceptance:** verified DIAG executable, preserved impacted RAM/MMIO regressions, real guest entry/PC/SP/SR/instruction trace, and a precisely identified next functional blocker. No fake guest progress.

### Stage B — Run the initialization paths required by EmuTOS

- Reuse MAME/POSE-informed VZ PLL, interrupt control, Timer1, UART1, reset and essential GPIO behavior.
- Implement a group of related functions as one coherent integration task when their interactions are necessary for guest startup.
- Resume the actual guest after each relevant correction; let its trace identify which hardware dependency is next.
- **Acceptance:** the guest progresses through the previously blocked initialization, with actual CPU/MMIO/IRQ/timer/UART observations and no host-side interception of guest OS calls. Do not demand unused UART RX or unrelated controllers.

### Stage C — Real Dana display

- Implement guest-programmed LCD registers and the existing MAME screen/LCD connections needed for Dana.
- Read the 560 × 160 one-bit framebuffer from actual guest RAM and verify deterministic pixel order/stride against a known test pattern.
- Continue EmuTOS to its own display initialization and capture guest-generated video.
- **Acceptance:** visible, reproducible output demonstrably backed by guest writes/RAM and LCD state, not a host-rendered substitute.

### Stage D — Dana ST keyboard and SPI2

- Reuse Retro68's Dana ST/SPI behavioral knowledge, without copying incompatible GPL implementation code.
- Integrate correct GPIO reset/ready/chip-select, SPI2 transfer/completion, ST initialization, key press/release and host input injection.
- Exercise the actual guest keyboard path; use bounded representative keys and edge cases.
- **Acceptance:** a physical host key event traverses emulated GPIO/SPI2/ST and is consumed by the guest, producing a real guest-visible effect.

### Stage E — First integrated interactive engineering emulator

- Integrate CPU, RAM, VZ peripherals, guest loader, LCD, keyboard, clock and interrupts in the DIAG target.
- Demonstrate reproducible startup, guest-generated UI and end-to-end interaction; independently distinguish function failures from harness/infrastructure failures.
- Preserve necessary diagnostics and test reproducibility; do not require polished menus, unrelated storage support, or a separate stable build.
- **Acceptance:** independently repeatable EmuTOS-Dana interactive session running on the virtual Dana hardware.

### Stage F — Usable diagnostic tooling and hardening

- Develop the engineering functions needed to inspect CPU registers, RAM/MMIO, IRQ, SPI/UART, logs, snapshots and reproducible test sessions.
- Improve UI and execution controls only where they facilitate real development and diagnosis. Avoid duplicated menus, noisy defaults and permanent clutter.
- Check instrumentation-on/off equivalence for relevant guest behavior.
- **Acceptance:** a practical and reproducible hardware/firmware diagnostic tool, with traceability and safe restart/state handling.

### Later separately authorized work

- **SD0 / SPI1:** add when the selected real guest and use case require card access.
- **Touch/ADC, RTC, power, USB, IR, extra memory, Flash/cold boot:** demand-driven extensions rather than default blockers.
- **OS3K/NEO firmware testing:** begin after a suitably sourced guest is available and the required emulator contract is approved; firmware patching remains in its own workstream.
- **Stable/product packaging:** activate only by express decision; derive from the qualified shared core, simplify controls and independently qualify the finished everyday-use build.

**Dependency discipline:** these are intended capability outcomes, not arbitrary gates. Adjust implementation order only when a real guest trace or source-backed technical dependency demands it; record the reason without changing the mission.

## 5. Execution model: substantial Codex work, independently qualified

### Supervisor A — ChatGPT

- Retrieve the latest canonical checkpoint, prior result and approved scope **before** any new work.
- Select a meaningful functional deliverable and the existing D1–D8 capabilities it contains; define expected guest outcomes, applicable source references, allowed files, exclusions, test fixtures and failure classification.
- Produce a **self-contained, source-backed Codex assignment** rather than prompts for individual code lines.
- Review actual Codex diff, source provenance, regression design, build/test outputs and blockers; integrate only independently supported results.
- Preserve exactly one next action. Do not reopen closed work or invent prerequisite projects.

### Codex — implementation

- Study the pinned source and completed research relevant to the assignment; use native MAME primitives instead of reinventing the emulator.
- Implement the agreed functional scope **as a coherent change set** with tests, diagnostics and bounded documentation.
- Resolve its own local source, compiler, script and test-harness issues within the assignment wherever possible; do not open a new conversational development phase for each trivial correction.
- Return a reviewable branch/diff, source references, exact commands, targeted tests, result classifications and any genuine blockers.
- Do not merge PRs, publish binaries, alter other projects or expand scope autonomously.

### Local workers, when connected and explicitly used

- **A:** supervisor; controls progression and consumes the previous result before the next cycle.
- **B:** local executor; distinguishes **NEW/SENT/NO_TASK**, executes only the approved prepared job.
- **C:** independent verifier/integrator; reports **PASS/FAIL/BLOCKED** and prepares a bounded Codex prompt if necessary.
- **D:** injector; transports only the approved prompt, without choosing work or modifying it.
- A prepared prompt is not proof that Codex has run. No automated continuation or unauthorized task escalation.

**The implementation batch may be broad, but testing remains granular and causal.** Preserve evidence for each real hardware behavior. Fix demonstrated defects and rerun only affected regressions, not every historical benchmark or the whole project.

## 6. Test, evidence and acceptance policy

- Use **actual guest M68000 execution on the real DIAG binary** for CPU, memory, MMIO, interrupt, framebuffer and keyboard claims. A source review, Python verifier unit test, fake host transaction, completed compiler, accepted job PID or missing log is not a functional PASS.
- Give each relevant behavior a deterministic fixture or actual EmuTOS execution trace; require correct bus provenance, register semantics, native events and meaningful negative cases.
- Separate failure domains: **PRODUCT**, **HARNESS**, **BUILD/TOOLCHAIN**, **INFRA/QUEUE**, **SOURCE/INPUT**.
- A harness assertion failure does not negate a previously proven memory subsystem; a failed launcher does not prove a CPU bug.
- Preserve independent PASS evidence and immutable historical baselines; regression-test only what a source/behavior change can affect.
- Use status **PENDING / SPEC_READY / READY / PASS / FAIL / BLOCKED** with exact scope; never call untested optional work PASS.
- Every executed deliverable records source/guest/toolchain commits, MAME revision, hashes of actual binary and fixture, test command, bounded logs, CPU/MMIO/IRQ/framebuffer observations as relevant, results, rollback state and the next action.
- Maintain a practical number of negative tests for address lanes, unsupported accesses, trace integrity, corrupted input and deterministic restart. Do not make the test harness itself the dominant project.

## 7. T, Commander and Google Drive — non-negotiable

**Target machine:** spc-HP-t640-Thin-Client, user spc, mandatory explicit deviceId **dee0b4b6-578a-41a5-88de-73dbeb808983**.  
**Existing Dana checkout:** /home/spc/Projects/alphasmart/DANA-emu.  
**Isolated work:** /home/spc/DANA_EMU_ISOLATED.  
**Verified canonical launcher:** /home/spc/.local/bin/dcjob launch.  
**Shared Drive job root:** AS2K_TEMP/COMMANDER_PIPELINE, with inbox/outbox/archive/failed/hold.  
**Known DIAG build baseline:** Clang 21, OVERRIDE_CC=clang, OVERRIDE_CXX=clang++, OVERRIDE_LD=clang++, PRECOMPILE=0, DEBUG=1, SUBTARGET=danadiag, at most **make -j3**.

1. **STATIC_FIRST:** GitHub, manuals and Drive results before consuming remote calls. Never use Commander for exploration, polling, file listings, connection tests, privilege probes or evidence already accessible in Git/Drive.
2. Prepare **one complete, syntax-tested, source-pinned self-contained .job.sh**, including integrity checks, necessary build/test actions, outputs and honest error classification.
3. Verify job readback/SHA; inspect the existing shared Drive queue; ensure **exactly one intended .job.sh** in inbox. Do not move or alter foreign jobs or run superseded scripts.
4. **Explicit user authorization is required for every remote intervention.** Default maximum is **three Commander calls for the intervention**, not a standing preauthorization. Larger blocks require fresh explicit approval; all previous grants expire on completion/exhaustion. Minimize calls by using one approved bundled launch.
5. Run exclusively via the verified launcher on the explicit device. A successful dispatch, PID or process exit is not evidence of test acceptance.
6. Retrieve and independently audit results **through Drive**, not repeated Commander calls. Retain manifests, hashes, bounded traces, job/console logs and machine-readable case results.
7. Avoid unnecessary rebuilds: reuse a binary only after verifying exact source/model compatibility, identity and SHA. **Rebuild when product source actually changes**, not for a harness-only correction.
8. Keep disposable Dana builds independent of AS2K and read-only MAME donors. Do not reset/clean another working tree, overwrite jobs, modify real Dana hardware or alter system configuration without separate approval.

## 8. Repository boundaries and publication rules

- All new repository-controlled material — source, documentation, comments, commits, PRs, scripts, results and worker prompts — is **English**. User conversation remains Spanish.
- The development repository is **DANA-emu**. DANA-OS3K owns the independent firmware/research track. Do not conflate repositories or reuse their authorization.
- No proprietary Palm/Dana/AlphaSmart Flash or commercial ROM images, credentials, private data, user state dumps or unlicensed third-party code may enter Git.
- Git changes must be contained to a correctly selected branch and an inspectable diff. **No automatic PR merges**, uncontrolled task escalation, repository-visibility change, physical firmware programming, external binary distribution, or upstream contribution.
- Repositories, branch snapshots and existing successfully built binaries are assets. Do not discard or regenerate them without a reason established by evidence.

## 9. Anti-drift and continuity checks

Before each new task, confirm:

1. **What real emulator capability is the current deliverable meant to provide?**
2. **Which already available MAME/POSE/Retro68/EmuTOS/D0 result eliminates work?**
3. **What is the exact current proven baseline, including independently audited PASS results?**
4. **Does the requested change implement missing guest behavior or merely repair its tools?** Keep incidental repairs within the same delivery when safe.
5. **What concrete guest trace or interaction establishes success?**
6. **Which work is explicitly excluded or deferred?**
7. **Is any T, Codex or Git mutation actually authorized?**
8. **What is the single next action after reviewing the latest result?**

Enforce all [AG-01 through AG-12](DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md), including no artificial gates, no reopening closed work, proportional testing, failure localization, durable evidence and no auto-escalation.

**Do not substitute a fresh microincrement plan for the established work sequence simply because a verifer, compiler invocation or script exposed a correctable issue.** Conversely, do not declare a broad functional package PASS when one of its required real hardware dependencies remains unproved.

## 10. Document authority and progress bookkeeping

This file establishes **durable project direction**. It does not erase older accepted evidence or automatically authorize implementation or machine execution.

Read in this order when resuming:

1. **This GENERAL_WORK_PLAN.md:** purpose, architecture, source reuse and desired functional outcomes.
2. **DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md:** current execution cursor, detailed AG rules and latest verified evidence. Historical checkpoint text can be stale; cross-check with the newest actual Git/Drive result.
3. **DIAG_FIRST_DEVELOPMENT_POLICY.md:** the active DIAG-only decision, deferred stable and worker-method restrictions.
4. **CANONICAL_CONTINUITY_AND_RULES.md** and **WORKFLOW_AS2K.md:** universal Git, Commander, Drive, safety and authorization controls. Older status/cursor statements are historical when superseded by newer independently verified evidence.
5. **DANA_EMU_INCREMENTAL_WORK_PLAN.md**, D0 contracts and source lock: precise technical acceptance and immutable references.
6. **HANDOFF.md**, relevant branch/PR and Drive job results: current handoff and implementation evidence; reconcile outdated entries before acting.

**Progress lives in existing execution/handoff records, not in copies of this general plan.** Record each completed capability with evidence, outstanding blocker and one next authorized action. No speculative dates, percentages or claimed completion without actual execution.

---

**Permanent operating directive:** Build the Dana emulator by **integrating the hardware behavior already documented and implemented elsewhere**, giving Codex substantive, bounded functional assignments, testing actual guest behavior, and preserving the user's existing rules and work. No duplicated investigation, unnecessary rebuilds, arbitrary code-line rounds, false hardware successes, or deviations into unrelated projects.
