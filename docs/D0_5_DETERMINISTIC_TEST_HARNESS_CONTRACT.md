# D0.5 — Deterministic MAME Dana test harness, trace and evidence contract

**State: SPEC_READY — documentary specification only.** Prepared 2026-10-13; strictly downstream of [D0.4](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md) and upstream of D0.6. No harness code, emulator binary, guest image, MAME build, Commander invocation, or T execution has occurred in D0.5.

**Single technical question:** How can one independently prove, using deterministic inputs and bounded evidence, that MAME Dana executed actual guest instructions, preserved CPU/MMIO behavior, and stopped for the stated reason, without confusing an infrastructure failure, a forged host marker, or a diagnostic side effect with an emulator result?

## 1. Trust boundaries and invariants

The planned **dana-stable** and **dana-diag** must share **one MAME hardware model**. Diagnostics are observation only. Distinguish four independently checkable layers:

1. **Input fixture and source provenance:** immutable MAME/EmuTOS SHA, real image/map hashes, synthetic RAM/CPU/MMIO bootstrap policy. No hashes or binaries exist yet.
2. **Hardware-side events:** MAME CPU instruction trace, exceptions, accesses to MAME address space and actual device/register callbacks.
3. **Guest-visible state and milestones:** guest PC/SP/SR, vector writes and reads, framebuffer bytes originating from guest RAM, UART/SPI transactions initiated by the guest.
4. **Independent verifier:** parses the bounded trace and final guest-state/checkpoint artifacts; does not trust the runner exit status or arbitrary text printed by the guest or host.

**Never declare guest PASS from:** compilation, process exit code 0, a boot banner, a host-drawn LCD, a missing/zero-length trace, a synthetic "success" line, source-code inspection alone, or the absence of a crash.

**Test authority:** an assertion passes only if its originating event and end-state are supported by machine-readable evidence captured at the specified boundary. The verifier runs *after* the guest attempt and reports its own status; it cannot rewrite guest observations.

## 2. Fixture manifest v1: mandatory contract, not an actual created fixture

The future test file **fixture.json** shall use a documented schema version. All timestamps, host IDs and elapsed wall-clock times are **provenance metadata**, **not** part of deterministic comparisons. Strings below are schema/value examples, not actual SHA values or measured machine states.

| Field | Type / rule | Meaning |
|---|---|---|
| schema_version | string, exact `dana-fixture-v1` | Reject unsupported versions |
| case_id / increment_id | stable strings | One technical assertion group; e.g. `D1.3-mmio-byte-lanes` |
| hardware_model | `mc68vz328-dana` | Physical target; no NEO GPIO or EZ-specific register substitutes |
| emulator_variant | `stable` or `diag` | Same guest hardware, variant-specific instrumentation |
| emulator_source / emutos_source | SHA-1 git commit, not branch-only | Reproducible source provenance; official revision may change only with explicit record |
| emulator_executable_sha256 | SHA-256 of actual binary **at run time** | Never invent or bypass; absent until build |
| guest.path / guest.sha256 / guest.length | file, SHA-256, integer | Explicit exact guest input; synthetic unit-test guest must be marked as synthetic |
| guest.kind / guest.profile | `synthetic-68k` or `emutos-dana`; `R-direct` or `R-booter` | Prevents confusing firmware and boot modes |
| guest.map_sha256 / guest.symbols | actual map file SHA and symbols if EmuTOS | `__text`, `_os_header`, `_stktop`, `__bss`, `__ebss`; never hardcode unknown values |
| ram.size_bytes / ram.base / initial_fill | 4194304, 0, e.g. all-zero bytes unless fixture overrides | Defined **virtual post-bootstrap** memory only, not physical reset |
| ram.patches[] | typed address, width, value, rationale | Every synthetic memory initialization e.g. `_phystop` at 0x42E explicitly recorded |
| cpu.start.pc / sr / ssp / d[] / a[] | aligned, typed, provenance-tagged | Exact deterministic injected CPU state, distinguish observed versus synthetic |
| vz.profile / initial_registers[] | `post-bootstrap` or other labelled, with width/reset/source | Never call dbztool values electrical defaults |
| input_events[] | virtual cycle and physical key/pin event + value | Immutable event ordering, never wall-clock keystroke timing |
| termination | guest cycle/instruction ceiling, trace limit, wall safety timeout | Predictable, bounded stop; wall timeout is only host safety stop |
| probes | named probe profile and capture bounds | Instrumentation choices are **not** guest inputs |
| assertions[] / regressions[] | unique assertion IDs, expected ordered conditions | Assertions must reference guest-side event/observable, no host marker shortcut |

**Required fixture validation BEFORE running:** all input artifacts exist; SHA and length match; map belongs to same compiled EmuTOS guest; addresses and widths legal; stack, image, BSS and low RAM ranges valid; guest input events time-sorted; no duplicate case IDs; end condition finite. **A fixture with absent guest image/hash is BLOCKED_FIXTURE for firmware tests**, not a fake PASS or permission to run an arbitrary PRC.

### Reserved initial RAM policy

- Default fixture: **all-zero 4 MiB RAM**, then explicit ordered patches by address and width; no hidden mutable global state between tests.
- Mandatory explicit alternate for EmuTOS: `_phystop = 0x00400000` at **0x42E** when chosen as a synthetic post-bootstrap premise; `_warm_magic` at **0x6FC** must be either zeroed or set to **0x5741524D**, each in a named separate case.
- The verifier must not assume the same branch executes in both choices. The branch is determined by the guest's instructions and must be observed.
- EmuTOS image placement, stack, `__text` and `__bss` depend on the exact **emutos.map** and image hash, which do not exist yet.
- Never seed vector 0x10 or guest IRQ vectors on the host merely to make an asserted guest vector-write pass.

## 3. Bounded machine-readable trace v1

**Proposed future format:** newline-delimited JSON (**events.ndjson**), with one header line and versioned event objects. A single monotonic `seq` orders events from one emulated machine timeline; `vcycle` records guest virtual cycles, not host elapsed milliseconds. Stable and diag need not write equal trace volume. Trace sources must indicate **CPU/DEVICE** versus **FIXTURE/HOST**.

Required universal fields (or explicit null for inapplicable event fields):

| Field | Contract |
|---|---|
| schema | `dana-trace-v1` |
| run_id / case_id / variant | Correlate log with manifest and evidence |
| seq | Zero-based, strictly increasing per run; detect duplicate/gaps unless bounded-drop is explicitly marked |
| vcycle / icount | Monotonic guest clock/instruction counters; scheduling semantics must be frozen per driver |
| origin | `cpu`, `device`, `fixture`, `host`, `verifier`; only CPU/device origins prove guest operation |
| event | Enumerated event type, see below |
| pc / sr / ssp | Guest CPU state at event, when meaningful; exact semantics defined by event |
| address / width_bits / value | Byte address, **8/16/32**, big-endian host-independent value, and read/write direction |
| lane_mask | Byte lanes actually accessed for partial-register operations; essential for SPI/VZ and LCD |
| device / register / instance | `vz`, `ram`, `st`, `lcd`, `spi1`, `spi2`, `uart1` etc; named MMIO register when resolved |
| aux | Small typed event-specific object; prohibit arbitrary huge dumps in a trace record |
| probe_id / sampling | Probe identity or `none`; probes must never inject guest CPU/peripheral changes |

Event types:

| Event | What it proves | Event-specific details |
|---|---|---|
| `run.begin` | Verified fixture was accepted, before guest enters CPU | Source/guest/binary hashes; profile ID; no guest PASS |
| `cpu.insn` | CPU fetched/executed guest instruction (with precise hook position defined) | PC before fetch, opcode bytes if available, icount |
| `cpu.state` | CPU checkpoint only | PC/SR/SSP, registers where required; distinguish state snapshots from single instruction events |
| `cpu.exception` | Actual CPU exception dispatch | Exception vector, original PC, frame address, handler target, cause (illegal, address error, bus error, trap, IRQ) |
| `mem.read` / `mem.write` | Bus access to actual guest RAM | Byte lanes, width, address, value and origin; bounded watch ranges |
| `mmio.read` / `mmio.write` | Bus access serviced by VZ device mapping | Full address, width, lane, PC, value; no host-injected faux register state |
| `irq.assert` / `irq.clear` / `irq.ack` | Interrupt-source change and CPU acceptance | Source, mask, pending, priority, vector, CPU result |
| `spi.exchange` | Completed serial transaction via SPI controller | Master, CS state, bytes/words, device, response; no sector-level syscall shortcuts |
| `uart.tx` / `uart.rx` | UART data direction from guest/peripheral | Register and byte, TX-ready/RX-ready state |
| `lcd.frame` | Guest RAM framebuffer sampled at real LSSA | LSSA, dimensions, bit order, RAM-source hash, frame hash; host-painted images cannot satisfy |
| `input.apply` | Scheduled external stimulus actually delivered | Virtual time, input ID and physical/host mapping; **not** proof that guest consumed it |
| `assert.observed` | Verifier-linked observation; never standalone proof | Assertion ID + event seq/range and state hash |
| `trace.dropped` | Explicit count/range of lost trace records | Drop reason, affected seq range, invalidated assertion classes |
| `run.end` | Machine stopped with reason; not automatic PASS | `expected_stop`, `guest_fault`, `budget_limit`, `host_abort`, `unimplemented_device`, `external_stop` |

**Safety/size proposal for first bounded tests:** default maximum **20,000 trace events OR 5 MiB uncompressed NDJSON** per case, whichever occurs first; additionally cap the CPU virtual-cycle/instruction budget in each fixture. These are **design defaults**, not measured performance limits, and can be tightened per case. Trace end must show truncation status. For a positive assertion that depends on discarded events, the verdict is **INCONCLUSIVE / BLOCKED_EVIDENCE**, never PASS. A planned sampling rule may be used only if the assertion does not depend on unsampled events.

**Time:** guest timing is defined in emulated cycles; host wall-time safety cutoff stops runaway jobs but does not define the guest's timer tick or deterministic expected output.

## 4. Test matrix: host assertions versus real guest assertions

Each test must define **setup → stimulus → observed event(s) → independent comparator → expected stop → regression dependencies**. Test IDs below are templates, NOT tests already run.

| Planned first use | Fixture / stimulus | Mandatory independent assertion | Negative/limitation |
|---|---|---|---|
| **D1.1** driver/build | MAME reduced target, no firmware needed for selectability | Build fingerprint, binary actually starts with declared device ID | PASS_BUILD only, never PASS_BOOT |
| **D1.2** RAM | Small synthetic 68k program with 8/16/32-bit loads/stores and address boundary probes | Guest CPU values and RAM readback in snapshot, with PC path | Misaligned 16/32 access generates CPU address error; no silent widening |
| **D1.3** MMIO | Synthetic guest writes test registers in controlled order | Real MMIO address+lane+value and guest readback for implemented regs | Unmapped access diagnosed, not converted to `0` or a fictional success |
| **D1.4** loader | Valid/invalid EmuTOS image+map hash cases | Loader places exact bytes, CPU starts at map-derived `__text` | Wrong hash/map/address/oversize rejects before guest |
| **D1.5** first EmuTOS | Source-locked guest, R-direct profile | Real `_os_header → _main → _realmain`; vector writes, memory.S branch; next unimplemented MMIO reported | Stop at unimplemented peripheral is **an expected D1.5 boundary only** if all earlier declared assertions passed; not a "boot successful" claim |
| **D2.1–D2.3** PLL/IRQ/timer | Controlled virtual-cycle stimulus with genuine guest register operations | PLLFSR transition, mask/priority/ack and handler entered by CPU | A scheduled `irq.assert` event alone cannot prove guest handler execution |
| **D2.4–D2.5** UART | Byte TX/RX via real registers | UART byte trace **and** guest read/write state | A host log string cannot prove UART implementation |
| **D3** LCD | Guest writes known 1-bpp RAM patterns and LSSA/stride | Frame hash from source RAM, image dimensions/polarity and guest PC context | Host-generated static 560x160 bitmap is inadmissible |
| **D4** SPI2/ST keyboard | GPIO reset/CS/ready and timed key presses | Guest SPI exchange with **0xAA** handshake and observed press/release consumption | `input.apply` alone is not a guest keyboard PASS |
| **D5** full integration | Actual EmuTOS RAM guest, screen and multiple keys | Ordered S0–S6+ milestones, guest-owned framebuffer and key response | Startup reaches IVR only ≠ functional emulator |
| **D6** parity/automation | Identical fixture under stable and diag; instrumentation toggled | Canonical guest-state/event hashes and screen output agree, excluding only probe artifacts | Host wall timing/log lengths need not match |

**Comparator rule:** where exact CPU trace equality is not portable across optional diagnostic probes, compare **guest-visible checkpoints** and a normalized **semantic event sequence** (CPU exception/vector accepted, register effects, timed input consumption, frame RAM bytes). Do **not** include diag logging counters, host timestamps, memory addresses of host allocations or file paths in semantic hashes. Compare at explicitly documented virtual-cycle barriers/checkpoints, not arbitrary GUI frame times.

**Milestone claims are scoped:** D1.1 passing a build/selectability test is **not** D1.5 guest instruction execution and definitely not D5 EmuTOS boot. Each increment's PASS evidence is limited to its stated assertions.

## 5. Assertion provenance and verifier safeguards

- Every assertion has `assertion_id`, `kind` (`guest_state`, `device_effect`, `input_response`, `build_only`), `required_event_types`, `event_seq_refs` and `actual_vs_expected`.
- For `guest_state` and `device_effect`, assertion must point to **CPU/device-origin** events and, where feasible, a corroborating **final RAM/register snapshot**. `fixture` and `host` event sources cannot satisfy it on their own.
- A message embedded in guest UART output that spells "PASS" is data, not the verifier's verdict.
- The verifier independently checks trace monotonicity, schema, SHA/size of all artifacts, event boundaries, stop reason, assertion completeness, and no unexpected event loss. On absent evidence, report **BLOCKED_EVIDENCE** even if process exit code is zero.
- The verifier's implementation and its tests are a **future D1/D6 engineering task**; this document only defines the interface. No script/test files are created by D0.5.
- An `expected_stop` is accepted only where an explicit, versioned assertion requires exactly that endpoint. Unexpected crash, illegal vector, unknown MMIO or budget exhaustion is not a pass.
- Each repeated test must reset the emulated machine and external device state from the fixture; no NVRAM or SD image carryover. Save-state hash and deterministic cycle schedule are the basis of reproduction once save-state support exists.

## 6. Classification: separate execution state from failure domain

**Overall outcome** is exactly `PASS`, `FAIL` or `BLOCKED` (or `PENDING` before a run). **Failure domains** provide diagnosis without conflating them:

| Domain / reason code | Overall state | Interpretation |
|---|---|---|
| `BUILD_COMPILE_ERROR` | FAIL | Product source does not compile in a prepared supported environment |
| `BUILD_TOOLCHAIN_MISSING` | BLOCKED | The required toolchain cannot be provided for the approved run |
| `LAUNCH_EXEC_ERROR` | BLOCKED | Runner could not start the target; **no guest result** |
| `CONNECTOR_UNAVAILABLE` / `COMMANDER_TOOL_ERROR` | BLOCKED | Remote connector failure, no inference that machine is offline |
| `QUEUE_CONFLICT` | BLOCKED | More than one/another `.job.sh` exists; never displace external jobs |
| `FIXTURE_NOT_FOUND` / `FIXTURE_HASH_MISMATCH` | BLOCKED | Required image/map/test fixture absent or inconsistent; guest not run |
| `HARNESS_CRASH` / `VERIFIER_EXCEPTION` | BLOCKED | Test infrastructure failed before trustworthy verdict |
| `EVIDENCE_TRUNCATED` / `MISSING_EVENTS` | BLOCKED | Necessary observations absent or invalid |
| `HOST_TIMEOUT` | BLOCKED | Host safety timeout elapsed; guest cause unknown unless prior trace proves otherwise |
| `GUEST_ADDRESS_ERROR` / `GUEST_CPU_MISMATCH` | FAIL when unexpected | Bad CPU/bus model or unintended guest exception |
| `MMIO_UNIMPLEMENTED` | FAIL unless explicitly expected endpoint | Real missing device/feature with PC/address captured |
| `ASSERTION_MISMATCH` | FAIL | Real guest-visible behavior disagreed with contract |
| `REGRESSION_MISMATCH` | FAIL | Previously proven guest behavior changed |
| `VERIFIED_EXPECTED_STOP` | PASS for **that limited test only** | All declared assertions pass and expected endpoint matched |
| `VERIFIED_GUEST_BEHAVIOR` | PASS for **that increment only** | Full declared fixture/assertion coverage and regressions pass |

**Important nuance:** For a first implementation attempt, an unmapped MMIO at the end of D1.5 may be the **expected test boundary**, but if the test's own objective is "execute Timer1 interrupt", that same absence is **FAIL**, not PASS. Pass/fail are relative to the pre-frozen increment contract, not conveniently reinterpreted after execution.

For each failure report, include `primary_domain`, `reason_code`, `first_bad_event_seq`, `guest_pc` if available, `blocked_dependency`, `recovery_action` and `repeat_safety`. An unrelated connector error must never cause deletion, reset, reinstall or blind rerun of the MAME source tree.

## 7. Drive-first evidence bundle contract

**Conceptual structure only; no Drive job or folder was created in D0.5:**

```text
DANA_EMU/<increment-id>/<run-id>/
  input/fixture.json             # immutable run input, SHA checked
  input/source_manifest.json     # pinned repos, toolchain and build flags
  evidence/emulator_build.json   # actual binary/toolchain/compile status
  evidence/events.ndjson         # bounded timestamp-free guest timeline
  evidence/console.log           # human-readable, not sole verdict source
  evidence/guest_state.json      # PC, SR, SSP, vectors, RAM/register digests
  evidence/framebuffer.sha256    # only when a real frame exists
  evidence/framebuffer.png       # optional, never host-generated substitute
  evidence/regression.json       # affected prior checkpoints
  result/verification.json       # independent verifier assertions
  result/result.json             # overall status and failure classification
  result/artifacts.sha256        # integrity hashes for actual files
```

Folders/files that do not apply to a given increment must be **explicitly declared not_applicable** in the result manifest instead of silently invented as empty placeholder evidence.

**Job execution transport (later only):** T runs an isolated, self-contained job using **/home/spc/.local/bin/dcjob launch** via the Drive-first queue, **exactly one `.job.sh`** in its shared inbox before dispatch. Verify remote identity `deviceId=dee0b4b6-578a-41a5-88de-73dbeb808983` in every approved Commander call, no inherited authorization, default maximum three calls per **separately authorised** intervention, use **-j3** for builds, fetch logs/results from Drive, never by polling Commander. Do not create or use a Dana queue path on T without confirmed setup. Never touch someone else's queue items.

**Minimal conceptual result.json fields:**

| Field | Rule |
|---|---|
| `schema_version` | `dana-result-v1` |
| `run_id`, `case_id`, `increment_id`, `variant` | Identity, cross-check every evidence file |
| `overall_status` | `PASS` / `FAIL` / `BLOCKED`; never infer from rc=0 |
| `stage_status` | Separate `source`, `build`, `launch`, `guest`, `verification`, `publish_evidence` status |
| `primary_domain` / `reason_code` | Precise failure attribution or `none` |
| `assertions`, `regressions`, `missing_artifacts` | Independent verifier references |
| `source_sha`, `guest_sha256`, `binary_sha256` | Actual existing hashes only |
| `first_bad_event_seq` / `guest_pc` | Null when no guest execution occurred |
| `artifact_inventory`, `artifact_manifest_sha256` | Only created files and their hashes |
| `resolution` / `next_action` | Concrete, limited remedy; no automatic destructive action |

Store secrets, private raw firmware and user media **outside Git**. Logs must not leak credentials or the contents of proprietary ROM. This test specification itself is safe to publish only under separate authorization; no Git visibility change was made.

## 8. Freeze conditions for D0.5 and handoff to D0.6

D0.5 **documentary closure** requires all items below, **without executing them**:

- [x] Deterministic fixture format: immutable image/map SHA, CPU, RAM, VZ register policy, virtual-clock inputs and finite stopping rules.
- [x] Trace format v1: event types, provenance, byte lanes/endian, CPU/IRQ/MMIO/SPI/UART/LCD evidence and bounded behavior.
- [x] Independent assertion/normalization rules: expected endpoint, negative tests, real guest versus host checks, stable/diag parity.
- [x] Failure taxonomy and overall PASS/FAIL/BLOCKED logic that separates product, runner, connector, verifier and fixture issues.
- [x] Drive evidence bundle and regression contract.
- [x] Missing inputs explicitly listed below; no false implementation claims.

**Unresolved and not silently promoted to PASS:**
1. **emutos.img**, **emutos-dana.rom**, **emutos.map**, source-derived build metadata and real SHA: not available/verified.
2. Actual **MAME checkout path/build** on T: unknown, to be verified in the first approved productive preflight.
3. Actual **virtual-cycle scheduler scale** and suitable finite limits: will be fixed when a real reduced driver/harness exists; defaults above are only design limits.
4. Ground-truth EmuTOS exit/guest outcomes: no real run; the S0–S6 chain remains a future acceptance target.
5. Independent verifier and fixture generator implementations: not written.

**Next increment: D0.6 (PENDING)** — freeze the **first D1.1 MAME implementation candidate**: exact source tree/commit and file allowlist, minimal MC68VZ328 driver skeleton, reduced build target/flags, fixture selection, build/selectability smoke, regression tests, rollback and job/evidence plan. The candidate must not be implemented/compiled/launched until **separately approved**.

No Commander call, build, guest run, Drive mutation or emulator-source edit is implied by D0.5 documentation.

### Referenced authoritative project documents

- [Canonical operating rules](CANONICAL_CONTINUITY_AND_RULES.md)
- [D0.4 CPU/RAM/bus contract](D0_4_RAM_CPU_BUS_ENTRY_CONTRACT.md)
- [D0.3 guest image/booter contract](D0_3_EMUTOS_DANA_GUEST_IMAGE_CONTRACT.md)
- [D0.2 VZ/EZ MMIO contract](D0_2_EZ_VZ_REGISTER_CONTRACT.md)
- [MAME baseline and reuse audit](D0_1_MAME_VZ_REUSE_AUDIT.md)
- [Authoritative incremental plan](DANA_EMU_INCREMENTAL_WORK_PLAN.md)
- [Source commit lock](../research/sources.lock.json)
