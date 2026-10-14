# DANA-emu — incremental development and qualification master plan

**Mandatory session guard:** read [CANONICAL_CONTINUITY_AND_RULES.md](CANONICAL_CONTINUITY_AND_RULES.md) before any action. It preserves the universal AS2K rules, execution authorization limits, source checkpoints, and exact next cursor. This plan alone does not authorize remote execution.

**Authoritative reduced-emulator plan.** Prepared on 2026-10-13. It refines the previous D0–D8 outline without invalidating the architecture, sources or AS2K rules. **Development status: no functional increments have passed. The next technical increment is D1.1 PENDING; D0.1–D0.6 are documentary SPEC_READY only. Dana-stable and Dana-diag require independent builds from D1.1, not D6.** No remote execution is authorized by this plan. Subsequent source preparation in a candidate branch does not itself qualify D1.1.

## 1. Objective and products

Build **DANA-stable** (daily use) and **DANA-diag** (instrumentation, automated execution, replay and evidence) **from one shared reduced MAME engine**, with a faithful MC68VZ328/Dana hardware model. Run the EmuTOS-Dana port as the first reference guest, **then** test patched OS3K firmware from DANA-OS3K. The primary purpose is an independent engineering test bench; contributing to upstream MAME is entirely optional.

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
6. **PASS requires real T evidence:** compilation alone does not demonstrate functionality. A host-drawn image does not prove the LCD works. A log message does not prove the guest received an interrupt. The verifier must distinguish infrastructure, harness and product failures.
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

**Original D0 research dependencies:** confirm the particular MAME revision/checkout for Dana on T; find or produce the EmuTOS-Dana guest image and its SHA and format (never invent Drive availability); specify exact RAM bootstrap/CPU state and MMIO/bus map for the chosen VZ revision. Do not create an indiscriminate extra copy of MAME.

## 4. Atomic increments

**Status:** D0.1–D0.6 have documentary SPEC_READY records. D1.1 remains PENDING until authorized real builds pass. None of the documentary closures is a functional PASS.

### D0 — References, initial model and reproducible bench (static only)

| ID | Single objective | Documentary closure |
|---|---|---|
| **D0.1** | Pin reference MAME revision and determine reusable NEO/VZ and EZ resources | **SPEC_READY:** [dated reuse audit](D0_1_MAME_VZ_REUSE_AUDIT.md); pinned GitHub SHA, T checkout not verified until later preflight |
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
| **D6.6** | Stable lightweight interface and installation | Selector, reset, save/delete, scale and user-environment launch; clean-install smoke test |

**DIAG must not require another 68k engine or EmuTOS patches.** Headless mode can precede GUI; do not delay testing for presentation.

### D7 — SD0 storage (after base emulator)

| ID | Single change | Closure test |
|---|---|---|
| **D7.1** | SD0 power, insertion and CS GPIO | Guest-recognized transitions and detectable card absence |
| **D7.2** | SPI1 and low-speed SD negotiation | Guest command/response sequence without intercepting GEMDOS |
| **D7.3** | Read sectors from SD image | Reproducible sector read and checksum from isolated test image |
| **D7.4** | Guest filesystem integration | EmuTOS mounts and reads a known file from virtual SD |
| **D7.5** | Optional protected writes and recovery | Disposable image/copy tests without real-media damage, failure handling |

### D8 — Separately scoped optional extensions

| ID | Scope | Activation condition |
|---|---|---|
| **D8.1** | SPI2 ADC/touchscreen | Guest UI requirement and controller contract |
| **D8.2** | RTC, power management and virtual suspend | Validated mapping and RAM/clock consistency criteria |
| **D8.3** | Second SD, USB, IR and other peripherals | Hardware evidence and firmware requirement |
| **D8.4** | Expanded RAM and full chip-select configuration | Documented physical model; do not assume 8/16 MiB from rumor |
| **D8.5** | Actual Palm/Flash boot and updater diagnostics | Verified physical regions, reset, bootloader and ROM coverage |

D8.x items are **independent and optional**, not prerequisites for usable DANA-stable.

### O0 — DANA-OS3K firmware support

Only when an adapted OS3K binary with defined provenance and mapping exists: create a **hardware compatibility suite** on the previously qualified emulator. OS3K firmware architecture and implementation belong to DANA-OS3K, **not this repository**. If a test fails, isolate the violated hardware contract before modifying the engine.

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
| **D1.1** | **PENDING — actual dual-build qualification required** | Two independent reduced Dana-stable and Dana-diag builds with shared source and isolated evidence |
| D1.2–D1.5 | **PENDING** | Only after D1.1 |
| D2.1–D2.6 | **PENDING** | Only after D1 |
| D3.1–D3.5 | **PENDING** | Only after D2 |
| D4.1–D4.6 | **PENDING** | Only after D3 |
| D5.1–D5.5 | **PENDING** | Only after D4 |
| D6.1–D6.6 | **PENDING** | Only after D5 |
| D7.1–D7.5 | **PENDING** | Only after D6 |
| D8.1–D8.5 and O0 | **PENDING / conditional** | Only when explicitly needed |

**Never bypass a blocker using a stub that reports artificial success.** If evidence is insufficient, record the exact missing register, event, file or signal, investigate the pinned source material, and resume the *same* increment. Any reordering requires an explicit, reasoned, traceable change to this plan.

**Exact continuation cursor: D1.1 PENDING — first isolated dual build of Dana-stable and Dana-diag, subject to independent implementation and remote authorization.** D0.1–D0.6 are **SPEC_READY documentation only**, not functional PASS. Do not build, invoke Commander or run a guest without fresh explicit authorization.

## 7. Control references

- [Pinned sources](../research/sources.lock.json).
- [NEO/NEO2 audit](NEO_NEO2_REUSE_AUDIT.md).
- [Stable/diag architecture](ARCHITECTURE.md).
- [AS2K rules](WORKFLOW_AS2K.md).
- [DANA-OS3K/MMIO](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/09-EMULADOR-MAPA-MMIO-Y-GPIO.md).
- [DANA-OS3K peripheral protocol](https://github.com/SamDelorean/Dana-OS3K/blob/main/docs/10-EMULADOR-PERIFERICOS-Y-HITOS.md).
