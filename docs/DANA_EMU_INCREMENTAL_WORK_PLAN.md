# DANA-emu — incremental development and qualification master plan

> **2026-10-23 FINAL PRODUCT DIRECTIVE / COMMITTED SCOPE:** The primary and ultimate project objective is **running and validating future OS3K-Dana firmware**, adapted from NEO/OS3K to replace Palm OS on Dana. EmuTOS is the already proven bring-up guest and Palm OS is a reference/physical-boot target, **not the ultimate OS**. The finished emulator must let the user choose the emulated **internal ROM/Flash firmware image and boot profile** for Palm OS or OS3K-Dana, choose EmuTOS through its genuine RAM/DanaRun mechanisms, and run a separately selected diagnostic ROM/bootstrap profile. Menu selection, ROM validation and controlled reset must preserve the two independently selectable SD cards and per-profile persistent state. See [General Work Plan](GENERAL_WORK_PLAN.md), and [DANA-OS3K's documented purpose](https://github.com/SamDelorean/Dana-OS3K). **All of this is future scope, not implementation PASS.** The active product cursor remains genuine keyboard + stylus interaction in the one installed `dana-diag` after verified GUI-020. No T/Commander authorization follows from this plan.


> **2026-10-16 D1.3.1 static source audit:** documentation **PASS only**; [native VZ MMIO decode contract](D1_3_1_VZ_MMIO_ADDRESS_DECODE_CONTRACT.md) confirms the MAME standalone 24-bit vs canonical 32-bit VZ address issue, the manufacturer conditional DMAP alias and first guest IVR `0xFFFFF300` 8-bit fixture. **NEXT D1.3.1-B:** implement narrow 32-bit-aware IVR decoding and MMIO-01 guest real-bus proof, retaining D1.2 closed RAM and DIAG-only policy. Functional D1.3.1 remains PENDING; no Commander used by static audit. [Authoritative plan](DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md).


> **LATEST EXECUTION CURSOR — 2026-10-16:** D1.2 **CLOSED/PASS** (real DIAG R5 RAM-01..RAM-09 9/9, independent RAM/CPU/vector audit). Next **D1.3.1 — pinned MC68VZ328 native MMIO address decoding, STATIC_FIRST**. Ignore prior dual-build/parallel stable gates; `dana-stable` deferred. Current execution plan and evidence: [DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md](DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md). User authorizes Commander in explicit **10-call blocks**, not automatic permissions for unrelated tasks.


> **AUTHORITATIVE INCREMENTAL ROADMAP (2026-10-16):** [DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md](DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md) contains the active DIAG-only atomic sequence, anti-gate policies AG-01..AG-12, acceptance criteria, deferred stable phase and zero-ramp handoff. Older dual-build steps and gate ordering in this document are retained as history and are NOT active execution instructions. Exact next action **D1.2-R3.1 STATIC_FIRST**.


> **ACTIVE PLAN OVERRIDE — 2026-10-16:** [Diagnostic-first policy](DIAG_FIRST_DEVELOPMENT_POLICY.md) supersedes every requirement below to build/test stable and diag in parallel during development. Only `dana-diag` is an active development/qualification target. The D1.1 dual-build PASS is historical and remains closed. For D1.2, run the diagnostic-only real RAM/CPU matrix; RAM-10 stable/diag parity is deferred (not PASS), with instrumentation on/off equivalence separately specified if feasible. Later D5/D6 stable-parity, dual-launch and packaging clauses become **future stable activation** tasks, not development gates. Do not execute superseded R2. The D1.2 runner/verifier must be adjusted before diag-only R3; remote execution requires separate explicit authorization.


**Mandatory session guard:** read [CANONICAL_CONTINUITY_AND_RULES.md](CANONICAL_CONTINUITY_AND_RULES.md) before any action. It preserves the universal AS2K rules, execution authorization limits, source checkpoints, and exact next cursor. This plan alone does not authorize remote execution.

**Authoritative reduced-emulator plan.** Prepared on 2026-10-13; progress reconciled on 2026-10-14 after real T R5 qualification and authorized Git integration. It refines the previous D0–D8 outline without invalidating architecture, sources or AS2K rules. **D1.1: PASS (two separate MAME skeleton builds and selectability; no guest behavior). Exact next increment: D1.2 PENDING (4 MiB RAM, 8/16/32-bit bus accesses). D0.1–D0.6 remain documentary SPEC_READY only.** New source implementation and remote/Commander runs are not authorized by this plan.

## 1. Objective and products

**Ultimate target: an OS3K-Dana development and validation platform** based on one faithfully emulated MC68VZ328/Dana hardware model from MAME. EmuTOS-Dana is the first real bring-up/reference guest and Palm OS a stock-fidelity guest; the product must ultimately boot and validate adapted OS3K/NEO firmware supplied by the separate `SamDelorean/Dana-OS3K` workstream. Future everyday-use packaging and diagnostic capabilities share this hardware model. During present development **only one installed `dana-diag` executable/tree is active**; the historical dual-build evidence and stable product plans do not authorize separate emulator variants.

- **Stable:** simple UI and execution, 560×160 LCD, keyboard, image selector, pause/reset, save/restore, installation and error handling. Advertise only services actually verified.
- **Diag:** identical hardware model with CPU, MMIO, IRQ, timer, SPI, UART and framebuffer tracing; opt-in probes, headless runs, checkpoints and reproducible artifacts.
- **Isolation:** separate executables/configurations, logs, state, media and tests; no DIAG-only emulation fixes. Instrumentation must not alter guest behavior.
- **Foundation:** reuse existing MAME CPU, devices, debugger and scheduler; do not build another 68k engine. Examine MC68328/EZ, NEO/NEO2 work and the POSE/Retro68 Dana model first. Do not copy GPL implementation into MAME components without license and distribution review.

## 2. Mandatory operational and closure rules

1. **Strictly linear work.** One technical question and one small change per increment. Documentary-only **D0.x** can close as **SPEC_READY** when source inventory and verification are complete; that allows proceeding to the next D0.x **without claiming functional PASS**. From D1, do not begin N+1 until N is closed as **PASS** through real T evidence, or **BLOCKED** with a localized obstacle and documented minimal deviation. Never mark a hypothesis PASS.
2. **STATIC_FIRST:** consult already pinned revisions in `research/sources.lock.json` and DANA-OS3K; prefer reusable code. Do not restart satisfactorily completed research.
3. **Pre-change contract:** before implementing each increment, record its objective, prerequisites, allowed files, expected effects, exact image/fixture, test command, observable signals, PASS/FAIL/BLOCKED criteria and rollback. Do not expand scope while executing.
4. **Diagnostics before debugging:** introduce minimum engine observability from D1. Record PC, vector, MMIO operation and failure cause. Avoid host hacks that replace actual guest operations.
5. **Deterministic tests and regression:** retain source/commit, image and executable hashes, arguments, inputs, outputs, state transitions and a machine-readable report. Re-run at least the smoke tests for affected closed increments. Compile with **`-j3` on T** when appropriate.
6. **PASS requires the evidence defined by each increment on real T:** D1.1 explicitly qualifies *build/registration/selectability* by separately compiling and running CLI validations of both binaries; it cannot claim a guest behavior. D1.2 onward require actual guest-visible tests of RAM/peripherals where specified: compilation alone, host-drawn images or synthetic host success logs do not qualify those behaviors. Distinguish infrastructure, harness and product failures.
7. **Commander/Drive:** stage exactly one prevalidated self-contained SH job in Drive inbox, confirming the queue does not already contain another job. Execute through the canonical T launcher only after explicit authorization and a per-increment call budget. Retrieve results through Drive; do not spend Commander on polling, log reading, exploratory path searches or ad hoc repairs. Previous-conversation budgets are not inherited.
8. **Isolated work:** do not alter AS2K emulators/ROMs, unrelated repositories or physical Dana firmware. Never delete, clean or reset another workstream's trees. Record source, docs and PR/commit only for appropriately qualified increments in GitHub.
9. **Single status taxonomy:** PENDING, SPEC_READY (reviewed specification, not executed), READY (execution expressly approved), PASS, FAIL, BLOCKED. FAIL/BLOCKED must identify the cause and next technical question; do not inflate unrelated milestones.
10. **No speculative dates or percentages:** progress is measured by reproducible closures, not lines of code or CPU time.

### Minimum evidence package for an executed increment

- **manifest.json:** increment ID, revisions/commits, hashes and test-bench parameters.
- **result.json:** PASS/FAIL/BLOCKED status, assertions, expected/observed results and cause.
- **console.log + guest-trace.log**, the latter bounded and optional when inapplicable.
- **Target artifact:** unit test or reproducible fixture, actual framebuffer capture, SPI trace, IRQ vector evidence, etc., as appropriate.
- **Regression summary:** previous tests executed, those not applicable, and rationale.
- **Checkpoint/rollback:** identify the base commit and confirm pre-existing stable/diag remain operational.

A harness failure caused by a nonexistent path or file is not a functional hardware failure. Record **BLOCKED_INFRA** as the cause while retaining the overall BLOCKED status.

## 3. Initial technical baseline — no assumed Dana software implementation

The surveyed MAME tree contains a 68000 CPU and MC68328/MC68EZ328 devices; **no MC68VZ328 device or integrated NEO/NEO2 machine driver was confirmed** in the inspected revisions. [ioma8/neo-re/alpha-emu](https://github.com/ioma8/neo-re/tree/master/alpha-emu) examines NEO firmware and VZ outside MAME. The [EmuTOS-Dana](https://github.com/davidgiven/emutos/tree/dana) port uses 4 MiB operational RAM, a 560×160 LCD, Timer1, UART1, SPI1/SD and SPI2/ST keyboard. [Retro68 POSE Dana](https://github.com/csnover/Retro68/tree/palmos/PalmUtils/poser) already contains Dana-specific VZ and ST components; this GPL implementation is a **behavioral reference**, not directly importable without license analysis.

**Original D0 research dependencies and later verification:** the pinned MAME revision `c4e48388ca620472643110db2941ce70aa5f3c07` was verified on T as a read-only donor in R3; the Dana product Git checkout was likewise verified. The EmuTOS-Dana guest image, SHA and actual build map are **still unavailable/unverified** and belong to later stages. D0.4 specifies the intended RAM/CPU bootstrap state; VZ MMIO remains unimplemented. Do not create an indiscriminate extra MAME copy outside Dana-owned isolated staging.

## 4. Atomic increments

**Status:** D0.1–D0.6 have documentary SPEC_READY records. **D1.1 PASSED its exact build/selectability contract** in the T R5 run with two different binaries; no guest-functional increment has yet passed. **D1.2 is PENDING.** [Qualification record](https://github.com/SamDelorean/DANA-emu/pull/5#issuecomment-6179533751) and [R5 package](https://drive.google.com/file/d/1NLIydtsa6t2XTyeXG4SvleIZI-jfYeo7/view).

### D0 — References, initial model and reproducible bench (static only)

| ID | Single objective | Documentary closure |
|---|---|---|
| **D0.1** | Pin reference MAME revision and determine reusable NEO/VZ and EZ resources | **SPEC_READY:** [dated reuse audit](D0_1_MAME_VZ_REUSE_AUDIT.md); pinned GitHub SHA; T donor verified later in R3 |
| **D0.2** | Complete EZ-versus-VZ block comparison | **Documentary SPEC_READY:** [register contract and Motorola corrections](D0_2_EZ_VZ_REGISTER_CONTRACT.md); detailed bitfields remain subsystem-specific |
| **D0.3** | Define EmuTOS-Dana guest image reference | **SPEC_READY:** [source/build and RAM bootstrap contract](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md); source revision, make target, raw binary stages and 0x2140 relocation recorded. **No built image/hash yet** |
| **D0.4** | Specify virtual RAM bootstrap CPU/bus state | **Documentary SPEC_READY:** [contract](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md); 4 MiB RAM, vectors, SSP/PC/SR, memory initialization and first MMIO; no runtime verification |
| **D0.5** | Define deterministic fixtures, tracing and evidence schema | **Documentary SPEC_READY:** [contract](D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md); no harness implementation, fixture files or runtime PASS |
| **D0.6** | Freeze first dual-build MAME candidate | **Documentary SPEC_READY:** [independent Dana-stable and Dana-diag build contract](D0_6_FIRST_MAME_DRIVER_CANDIDATE.md); no functional qualification |

**D0 deliverable:** an executable specification for the first MAME increment, not a functional emulator. D0.1–D0.6 require no Commander when resolvable entirely from sources/Drive.

### D1 — CPU, memory, basic MMIO and minimum boot

| ID | Single product change | T closure test |
|---|---|---|
| **D1.1** | Introduce minimal Dana skeleton driver and independently compile Dana-stable **and** Dana-diag from one MAME hardware source | **Both** isolated builds compile; each enumerates `asmdana`; existing drivers remain untouched. No guest-runtime claim |
| **D1.2** | Map 4 MiB RAM/68k reads and writes; no new MMIO | Guest fixture reads/writes 8/16/32 bits, verifies big endian, alignment and boundaries without corruption |
| **D1.3** | Implement VZ register-window MMIO decoding with basic resets | Addressed trace proves offsets and 8/16/32-bit widths, byte-lane effects and identifiable invalid access |
| **D1.4** | Add EmuTOS-Dana **RAM-only** payload loader | Verify size/hash, placement, SSP/PC and control handoff without claiming physical cold boot |
| **D1.5** | Execute guest until first still-unimplemented VZ block | Capture PC/SR/SP, instructions, exact blocker and next MMIO access; no full-boot claim |

Do not implement LCD, keyboard or SD within D1.

### D2 — Clock, interrupts, timer and serial console

| ID | Single product change | T closure test |
|---|---|---|
| **D2.1** | Implement virtual clock/PLL and dynamic phase of EmuTOS-polled bit | Guest delay advances through virtual clock events, without host-forced constant values |
| **D2.2** | Implement VZ IRQ mask/pending/vectorization | Fixture asserts/masks a source, receives correct vector and verifies priority/ack |
| **D2.3** | Implement Timer1 prescaler/compare/status/ack | Guest receives ticks measured against virtual time and starts/stops them via masks |
| **D2.4** | Implement UART1 TX and ready conditions | Guest-transmitted bytes appear in console in the correct order with coherent ready status |
| **D2.5** | Complete UART1 RX/IRQ when required | Controlled RX injection, guest read and interrupt/ack without FIFO hang |
| **D2.6** | Repeat EmuTOS execution up to next unimplemented peripheral | Trace proves previously blocked states are passed without guest patches |

Cross-check register effects against POSE VZ and the manual; **do not implement synthetic timers based solely on read counts** when that distorts guest behavior.

### D3 — Real Dana LCD

| ID | Single product change | T closure test |
|---|---|---|
| **D3.1** | Integrated VZ LCD registers and state changes | Faithfully record guest writes to LSSA, dimensions, stride and enable |
| **D3.2** | Read framebuffer from physical guest RAM addressed by LSSA | Deterministic 560×160, 1 bpp pattern, at least **11,200 B** unpadded, without fabricated host picture |
| **D3.3** | Resolve bit order, line order, polarity and refresh | Capture checksum/image matches known pattern and changes after guest RAM writes |
| **D3.4** | Implement LCD power and basic contrast | Capture changes correctly from GPIO/register state without altering guest memory |
| **D3.5** | First display generated by EmuTOS | Capture actual framebuffer in guest execution with demonstrable preceding PC/commands |

No final UI or keyboard in D3.

### D4 — ST auxiliary controller, SPI2 and Dana keyboard

| ID | Single product change | T closure test |
|---|---|---|
| **D4.1** | ST GPIO reset/ready/CS/idle | Verify PB6, PK2 and PE3 transitions without false exchanges |
| **D4.2** | SPI2 transaction engine and completion flags | Guest fixture reads/writes SPIDATA2/SPICONT2 with correct CS and byte order |
| **D4.3** | ST initialization and handshake response | Guest receives **0xAA** through actual protocol, not a code skip |
| **D4.4** | Physical keycode packets for press/release | F1–F8 and letters, ordered events and coherent held-key state |
| **D4.5** | Wire host keyboard events to virtual ST | Press/release affects guest, not merely the host window |
| **D4.6** | ST edge cases: none/multiple keys/reset | Bounded queue, stability and traceable errors without invented ST behavior |

Do not reuse the NEO matrix as if it were ST. Primary reference is Retro68/EmSPISlaveSTMicro checked against EmuTOS-Dana.

### D5 — Qualification of the first functional emulator

| ID | Test question | T closure evidence |
|---|---|---|
| **D5.1** | Does EmuTOS boot without host-side emulation of TOS calls? | Deterministic guest execution to a real interface on LCD |
| **D5.2** | Does end-to-end keyboard interaction work? | Input sequence and visible guest-system response |
| **D5.3** | Do reset/restart reproduce a clean state? | Two runs from baseline snapshot/configuration with comparable outcomes |
| **D5.4** | Are RAM/IRQ correct under basic load? | Extended keypress, redraw and tick session without corruption/loops |
| **D5.5** | Does opt-in diagnostic instrumentation preserve guest execution? | Comparable capture/state with instrumentation on/off; daily-use hardening follows in D6.1 |

**D5 is the first milestone permitting a claim of a functional Dana emulator**, narrowly scoped to **RAM/EmuTOS mode + LCD + keyboard**. It does not imply Palm boot, USB, SD, suspend or OS3K functionality.

### D6 — Daily-use-quality stable and diagnostic products

Dana-stable and Dana-diag have **separate compiled products from D1.1**. D5 validates guest-visible parity. **D6.1 hardens** existing launchers, media, configuration and state isolation; it does **not** introduce dual builds for the first time.

| ID | Single increment | T closure test |
|---|---|---|
| **D6.1** | Harden existing stable/diag launchers, configuration, persistence and state isolation | Both builds preexist from D1.1; separately verify clean runtime state, media/caches and deployment |
| **D6.2** | Enable selective DIAG tracing and bounded logs | Reproducible CPU/MMIO/IRQ/SPI trace without exhausting storage; parity with stable |
| **D6.3** | Automate headless smoke/regressions | Script reproduces D1–D5 cases and reports structured results per case |
| **D6.4** | Save and restore complete state | CPU/RAM/peripheral checkpoint and deterministic continuation after restore |
| **D6.5** | Harden loader and error reporting | Missing/corrupt image, invalid RAM, truncation and restart fail in controlled ways |
| **D6.6** | AS2K-analog Dana GTK frontend with a **first-class internal ROM/Flash image chooser and OS boot-profile selector**, eventually packaged for everyday use | Choose Palm OS or OS3K-Dana firmware images for a valid internal-Flash cold-boot profile, or choose EmuTOS in direct-RAM / authentic Palm-DanaRun modes, plus separate diagnostic ROM; show active vs next-reset selection and image validation/error state. Preserve correct Dana 560x160 LCD, mapped keys/pen, `Archivo/Máquina/Ver/Configuración/Ayuda`, 100/200/300%/fullscreen, independent left/right SD selectors, optional capture, controlled reset, per-OS RAM/session persistence. Only host controls are copied from AS2K; no AS2K-only hardware assumptions or false firmware boot claims. |

**DIAG must not require another 68k engine or EmuTOS patches.** Headless mode can precede GUI; do not delay testing for presentation. This final user-facing GUI is a committed product requirement, but **not a gate for the current native EmuTOS keyboard/stylus task**. UI implementation must reuse compatible GTK/session patterns from `SamDelorean/AS2K-Emulator` (`stable/frontend/as2k_ui.py`, `stable/frontend/as2k_session.py`, `stable/docs/UI_CONTRACT.md`) and expose only Dana-real mappings; `dana-stable` is activated later only by separate authorization.

### D7 — SD0 storage (after base emulator)

| ID | Single change | Closure test |
|---|---|---|
| **D7.1** | SD0 power, insertion and CS GPIO | Guest-recognized transitions and detectable card absence |
| **D7.2** | SPI1 and low-speed SD negotiation | Guest command/response sequence without intercepting GEMDOS |
| **D7.3** | Read sectors from a host-selected raw SD image in first emulated slot | Guest SPI/SD sector read and checksum match the selected image; absent card and incorrect image fail visibly, without host filesystem emulation |
| **D7.4** | Guest filesystem integration | EmuTOS mounts and reads a known file from virtual SD |
| **D7.5** | Safe image writes, host open/eject and per-slot media configuration | Read-only/read-write policy, safe flush/replacement, image path and insertion state persist across launches; destructive tests use disposable copies |

**Dual-slot user-facing requirement (2026-10-23):** The final physical-boot emulator must offer **two independent host GUI image selectors**, one for each original Dana SD slot, with user-selected raw sector-image path, insert/eject status, read-only/read-write policy, safe write flush and remembered assignments. Emulated card behavior is exposed to guest firmware through actual SPI/card-select/GPIO/presence signals; validate physical left/right-to-controller mapping using source and hardware evidence. The original EmuTOS-Dana port documents access to only one slot; emulation of both physical slots does not claim both will be supported automatically by that EmuTOS build. D7 implements and verifies the first slot; D8.3 brings in the second for D8.5. Image-file selection must not be confused with the separate Flash/Palm firmware image or with the direct `.dana` RAM-loader. **Deferred, not a gate for current EmuTOS GUI interaction.**

### D8 — Separately scoped extensions; full boot and diagnostic ROM now committed deferred objectives

| ID | Scope | Activation condition |
|---|---|---|
| **D8.1** | SPI2 ADC/touchscreen | Guest UI requirement and controller contract |
| **D8.2** | Real VZ RTC + retained date/time for OS3K-Dana timestamped full-memory backup, plus power management and virtual suspend | Guest reads/writes real `RTCTIME 0xFFFFFB00` and 9-bit `DAYR 0xFFFFFB1A` hardware counters; true virtual-time advancement, rollover, alarms and sleep tested; OS3K holds calendar epoch/time zone persistently and labels unset dates, never fakes a full calendar in the hardware RTC |
| **D8.3** | Second independent SD slot with its own host-selected image, actual slot-specific CS/detect hardware and separate media state; USB/IR remain optional subfeatures | **Second SD required by future D8.5**, not by current GUI milestone; validate physical wiring and independently addressable guest sector I/O |
| **D8.4** | Expanded RAM and full chip-select configuration | Documented physical model; do not assume 8/16 MiB from rumor |
| **D8.5** | **Full Dana boot: VZ reset/Flash → Palm OS → DanaRun.prc loading `/kernel.img` from left-slot SD image → trap #0 → EmuTOS at `0x2140` with separate right-slot TOS SD image** | **COMMITTED FUTURE / DEFERRED**; select, insert/eject and persist **both** card images independently in the same `dana-diag`, and prove guest-visible I/O and authentic end-to-end transition after current keyboard + stylus milestone |
| **D8.6** | **AS2K-analog Dana diagnostic bootstrap and selectable diagnostic ROM/payload**; explicitly supported VZ/Flash boot or labeled synthetic RAM loader with immutable SHA/layout/entry/vector/stack manifest, bounded guest-origin diagnostics and normal reset restoration | **COMMITTED FUTURE / DEFERRED**; select a diagnostic image through the AS2K-style frontend; CPU executes real 68k diagnostic firmware; record guest PC/SP/SR, memory/IRQ/MMIO and PASS/FAIL. Never assume VZ provides HC11 Special Bootstrap; never pretend a host-assisted loader is physical boot or patch commercial Palm firmware |

D8.1, D8.2, D8.4 and the non-SD portions of D8.3 remain separately scoped extensions, not default prerequisites for interactive EmuTOS. The **second SD slot within D8.3 is required for committed D8.5** but is not an active development gate. **D8.5 (full Palm-to-EmuTOS boot) and D8.6 (diagnostic ROM/bootstrap) are committed final-product objectives, not optional and not active development gates.** The physical-boot profile must execute the actual guest firmware and complete chain, without silently using the direct-RAM handoff. Preserve the current post-bootstrap RAM mode as a separate fast diagnostic profile, keep the same DIAG tree/executable, reuse qualified devices, and compare against sourced physical Dana behavior. Commercial Palm/Flash images remain private and legally sourced, not committed to Git. Detailed source/hardware feasibility and testing contracts belong to the later D8.5 implementation phase, not the current interactive-GUI increment. See [General Work Plan](GENERAL_WORK_PLAN.md).

### O0 — OS3K-Dana is the ultimate guest/firmware acceptance target (COMMITTED, pending genuine patched image)

**Primary mission, not a merely optional extension.** The adapted NEO/OS3K firmware itself is produced, versioned and validated for provenance in `SamDelorean/Dana-OS3K`; the emulator must support and qualify it against the same real virtual Dana hardware that runs the reference guests. **OS3K-Dana is intended to replace Palm OS as its own guest operating environment**, not to run as an app inside Palm/EmuTOS, and should not be forced to traverse DanaRun. Do not create a false prerequisite requiring all Palm/EmuTOS startup features when a real OS3K execution trace only needs a smaller validated set of VZ devices.

| ID | Committed OS3K-Dana emulator capability | Evidence/acceptance |
|---|---|---|
| **O0.1** | Select `OS3K-Dana` as an internal-firmware profile, browse a user-supplied patched image, verify format/identity/size/entry, map Flash/ROM or documented RAM loader from the firmware's actual build contract | Source-identifiable image manifest and correct guest CPU reset/entry/vector/stack; never guess Flash offsets, nor treat an updater fragment as a complete dump |
| **O0.2** | Execute genuine OS3K-Dana guest startup on the virtual DragonBall VZ | Guest PC/exception/MMIO/IRQ/RAM evidence and progress to independently identified OS3K initialization code, not host-side hooks or prepainted screens |
| **O0.3** | Reach the OS3K-Dana native UI with real Dana LCD/keyboard/pen and applicable storage | Visible guest-created screen and causal user-input response with correct emulated hardware events |
| **O0.4** | **Native NEO/NEO2 `.OS3KApp` compatibility, with optional automatic per-app patching inside SD Manager**; shared OS3K-Dana HAL/ABI compatibility remains the primary solution | Install directly **unchanged** when compatible; when exact version/hash and failure are known, apply a prequalified bounded compatibility patch in a **staged copy** on device (source SD original untouched). Validate package header, code/data offsets and 68k relocation, input/output SHA-256, A-line ABI/A5, applet size/ID and safe persistence/rollback. Prove separate real guest 68k runs for unchanged **and patched** applets, including malformed/wrong-hash negative cases, and SD-off state after completion. Reject unknown versions without guessing; no assertion of universal compatibility or legal permission to redistribute proprietary app binaries |
| **O0.5** | Preserve system choice, selected firmware and independent per-OS nonvolatile guest state; provide **SD Manager → Backup All** full internal-memory/user-data generations stamped by the guest RTC date/time | Read all OS3K applet file namespaces and internal writable data, with range-verified raw RAM capture plus native document/app/config inventory, hashes, unique timestamped SD directory and no silent omissions; detect missing RTC date, interrupted transfer and incomplete image, do not overwrite earlier versions or auto-restore Flash; independently prove safe SD off/flush and recovery |

**Boot/media distinction:** `Archivo → Abrir imagen ROM/Flash interna…` is the explicit guest firmware image selector; `Máquina → Sistema de arranque` chooses Palm OS, OS3K-Dana, EmuTOS-Dana or Diagnostic ROM. Palm/OS3K use compatible internal-firmware mappings; EmuTOS normally uses RAM direct or Palm→DanaRun→SD and is **not** misreported as flash-resident. Applying a different image is an explicit reset with state-protection rules, not live replacement of guest PC. Commercial Palm ROM and any private/derived ROMs remain off public Git.

**Activation and precedence:** initial EmuTOS GUI input remains the immediate next result in DIAG; O0 functional tests become executable only after a real adapted binary exists with its own mapping/entry specification. O0 is nonetheless a *required final-product capability*. Develop only in the single existing DIAG until separately authorized transition to any stable package; no automatic Commander rights.

## 5. Regression and parity policy

- **Every D1–D4:** small synthetic fixture **plus EmuTOS guest where applicable**. Re-run affected previously closed tests and provide a coverage manifest.
- **Every D5–D6:** EmuTOS start, keyboard, LCD and timer; at least one test in **both stable and DIAG**, with capture hashes and state serialization when appropriate.
- **D7/D8:** the basic D5 suite remains mandatory; isolate additional media and peripheral tests.
- **Any CPU/IRQ/memory change:** execute the *entire* closed suite that depends on those services, not only the newest test.
- **No false positives:** successful compilation, GUI launch, output-file creation or exception-free termination qualify only those controls, not guest-visible peripheral behavior.

## 6. Progress ledger and scope-drift control

| Block | Recorded state | First permitted activity |
|---|---|---|
| **D0.1** | **SPEC_READY (documentary closure)** | [MAME/VZ reuse audit](D0_1_MAME_VZ_REUSE_AUDIT.md); GitHub baseline pinned, T checkout pending first preflight |
| **D0.2** | **SPEC_READY (documentary closure)** | [EZ/VZ table and addendum corrections](D0_2_EZ_VZ_REGISTER_CONTRACT.md); no emulation PASS |
| **D0.3** | **SPEC_READY (documentation only)** | [EmuTOS-Dana source/build and RAM handoff audit](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md); no binary SHA/test |
| **D0.4** | **SPEC_READY (documentation only)** | [Post-bootstrap RAM/CPU/bus entry contract](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md); no MAME functional PASS |
| **D0.5** | **SPEC_READY (documentation only)** | [Deterministic fixture/trace/evidence contract](D0_5_DETERMINISTIC_TEST_HARNESS_CONTRACT.md); no actual tests |
| **D0.6** | **SPEC_READY (documentation only)** | [First MAME driver, dual-build test and rollback contract](D0_6_FIRST_MAME_DRIVER_CANDIDATE.md); no compilation |
| **D1.1** | **PASS — build/selectability only** | Two separate Clang 21 / `PRECOMPILE=0` builds and `asmdana` CLI smoke on T, source/list preservation and binary SHA-256 verified in [R5](https://drive.google.com/file/d/1NLIydtsa6t2XTyeXG4SvleIZI-jfYeo7/view); integrated by [PR #5](https://github.com/SamDelorean/DANA-emu/pull/5) |
| **D1.2** | **PENDING — next increment, not yet authorized** | 4 MiB guest RAM, 8/16/32-bit big-endian read/write fixture, alignment and boundary checks; D1.1 regression |
| D1.3–D1.5 | **PENDING** | Only after D1.2 |
| D2.1–D2.6 | **PENDING** | Only after D1 |
| D3.1–D3.5 | **PENDING** | Only after D2 |
| D4.1–D4.6 | **PENDING** | Only after D3 |
| D5.1–D5.5 | **PENDING** | Only after D4 |
| D6.1–D6.6 | **PENDING** | Only after D5 |
| D7.1–D7.5 | **PENDING** | Only after D6 |
| D8.1–D8.6 and O0 | **PENDING** | D8.5 full physical Palm→EmuTOS and D8.6 diagnostic ROM required final scope; **O0.1–O0.5 OS3K-Dana is the definitive acceptance goal** once an adapted firmware image exists; all remain deferred behind the current DIAG keyboard/pen GUI task, with optional hardware extensions only when genuinely needed |

**Never bypass a blocker using a stub that reports artificial success.** If evidence is insufficient, record the exact missing register, event, file or signal, investigate the pinned source material, and resume the *same* increment. Any reordering requires an explicit, reasoned, traceable change to this plan.

**Exact continuation cursor: D1.2 PENDING — 4 MiB RAM and 68k 8/16/32-bit read/write semantics, with big-endian byte lanes, alignment, bounds and D1.1 regression.** D1.1 is closed **PASS only for two separate T-compiled MAME skeleton builds/selectability**. The tested product head is `92e39eff050fa7a62486569be6a34994682ce44c`; the stable and diag binary SHA-256 values are respectively `ec055d08b66d46181d26cd9371f7f961f52732ad36f468a8aae0a4e1b7bc83d1` and `dd877c9cb36c491e675b82ce2aba78548519cccf2bd16bf2a9c61cbd3000435c`. For R5 builds on T use Clang 21 with `OVERRIDE_CC=clang OVERRIDE_CXX=clang++ OVERRIDE_LD=clang++ PRECOMPILE=0`, sequential `make -j3`, separate stable/diag stages. **Do not claim a functional guest, VZ or LCD.** D0.1–D0.6 remain SPEC_READY documentary. Next action is static D1.2 contract and fixture review; no source implementation, Commander/T, launch, or publication without new explicit user authorization.

## 7. Control references

- [Pinned sources](../research/sources.lock.json).
- [NEO/NEO2 audit](NEO_NEO2_REUSE_AUDIT.md).
- [Stable/diag architecture](ARCHITECTURE.md).
- [AS2K rules](WORKFLOW_AS2K.md).
- [DANA-OS3K/MMIO](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/09-EMULADOR-MAPA-MMIO-Y-GPIO.md).
- [DANA-OS3K peripheral protocol](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/10-EMULADOR-PERIFERICOS-Y-HITOS.md).
