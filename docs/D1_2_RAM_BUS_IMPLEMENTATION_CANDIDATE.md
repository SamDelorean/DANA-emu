# D1.2 — RAM and M68000 bus source candidate

State: **SOURCE_CANDIDATE_PREPARED / AWAITING_INDEPENDENT_T_QUALIFICATION**.
Canonical D1.2 remains PENDING. No guest-memory PASS or observed bootstrap is
claimed. D1.1 remains closed PASS for its independent T build/selectability scope.

Base main: `3408d5849a132da5647d839c51cf174e94dff94b`.
MAME donor: `c4e48388ca620472643110db2941ce70aa5f3c07`.
The complete [issue #6 contract](https://github.com/SamDelorean/DANA-emu/issues/6)
was read directly through GitHub's public HTML embedded issue data. GraphQL/REST
API requests remain Forbidden. No external source checkout was modified.

## Minimal product change

`alphasdana.cpp` adds one native MAME address map and a single RAM share at
`0x00000000..0x003fffff` inclusive: exactly 4,194,304 bytes, including writable
vectors and low memory. No global mask, mirror or custom bus handler is added.
The existing M68000 implements endian transfers and address errors. The 1 MHz
placeholder, machine registration, description and nonworking/no-sound flags are
unchanged. No VZ, GUI, peripheral, firmware loader or guest boot is introduced.

The out-of-range experiment uses `0x00400000`, within the M68000's native 24-bit
address bus but outside RAM. Host addresses above the physical bus width are not
an extra 32-bit Dana decoding model. The VZ window remains unimplemented; its
24-bit physical address also lies outside the RAM map.

## Reproducible original fixtures

`tests/d1_2_fixtures.py` uses the already installed LLVM M68k MC library through
its C interface, CPU M68000. It assembles instruction-by-instruction, extracts
big-endian ELF .text, rejects relocations and independently disassembles the
bytes through LLVM's disassembler. It does not implement a CPU or hand-encode
MOVE instructions. The source manifest retains the exact Motorola source,
actual bytes, decoded instructions, instruction addresses, lengths and hashes.

LLVM 19 does not parse/decode STOP's immediate operand. For this one instruction
only, the generator assembles `.short 0x4e72, 0x2700`; its decode is explicitly
attributed to pinned `src/devices/cpu/m68000/m68000.lst` (`4e72 ffff stop i16u`).
It is not represented as an LLVM disassembly result. No guest firmware is used.
Generated binaries/disassemblies remain outside Git; the committed JSON contains
all assembled hex and actual SHA-256 values. Regenerate with:

```sh
python3 tests/d1_2_fixtures.py /tmp/dana-d1-2-fixtures-new
# Optional explicit installed LLVM shared library selector:
# ... --llvm-library /absolute/path/to/libLLVM.so.19.1
```

No package installation is needed in the audited Cloud instance. Other hosts can
use the committed byte manifest without installing LLVM; regeneration requires
an already available compatible LLVM M68k backend. The handler at `0x5000` is
`STOP #$2700`, SHA-256 recorded in the manifest.

| Fixture | Length | SHA-256 |
|---|---:|---|
| RAM-01 | 54 | `a8494fe2b0118329b7627ff9787c9811859dadbda5c8e1dbc5b61d27fd71ddae` |
| RAM-02 | 18 | `23273910c3147b058117c2b30c6bf90095264c26bb18d1903ee944668aa0bc9d` |
| RAM-03 | 16 | `61149b32bd89796519f938b5ba30402e1ed431735b21b66f8b611f03aeac797b` |
| RAM-04 | 18 | `681905ff1a33d0d6739b21d047b1b4c4e964ee2ffe6d57b7f10dd4fdd62b16e0` |
| RAM-05 | 16 | `5a1f82d7ce14305a5f5a8cc3750f0f26f0667229a9f5551aa61e6397cb2553e6` |
| RAM-06 | 14 | `97c8334825b13cc187b14526c2da421628b6e0329b8201581171cf8089295ee7` |
| RAM-07 | 14 | `dad488f66035d0d5a507a6054a7bdfe296447735739b5380d5c326aec6424716` |
| RAM-08 | 18 | `138fc2a58061bd2e8ce5ee6f1cf4428e17f97302975ed0683a7dce2d199638cc` |

RAM-01 is the exact issue program: longword access at A0+10 is even but not
four-byte aligned. Expected D0-D3 are 000000A5, 0000BEEF, 12345678, 89ABCDEF.
Expected scratch is `CC A5 BE EF 12 34 56 78 CC CC 89 AB CD EF CC CC`.
RAM-02 writes/reads vector 0x80; RAM-03/04/05 test the last valid word/long/byte.
All untouched RAM, including adjacent guards, must match the initial dump.

RAM-06/07 use actual `MOVE.W 1(A0),D0` / `MOVE.L 1(A0),D0` with A0=0x10000.
The runner does not manufacture exceptions, mutate exception frames or redirect
PC after execution. Acceptance requires CPU reads of vector 3 at 0xC/0xE,
handler entry 0x5000, SP=0x7FF2 and seven CPU frame writes. The pinned core's
14-byte frame is decoded as SSW, fault address, IR, saved SR, pipeline PC. The
verifier checks supervisor-data read status, fault=0x10001, actual fault opcode,
saved SR=0x2700 and a bounded even pipeline PC inside the fault instruction's
prefetch span. It also requires that no other RAM changed. This is a source-
derived candidate expectation, awaiting real CPU evidence on T.

RAM-08 records the actual native unmapped read value and requires unchanged RAM
and real CPU out-of-range read/write events; it never forces a bus-error outcome.
RAM-09 launches a new process with the RAM-01 fixture and compares normalized
CPU/RAM/bus state. RAM-10 compares all corresponding stable/diag outcomes,
excluding only identity/provenance/host instrumentation fields.

## Test-only bootstrap: source proof and runtime gate

The runner installs `d1_2_boot.lua` as the **test-only pluginspath/boot.lua**, not
as an autoboot script and not in a donor installation. The pinned startup code:

1. `src/frontend/mame/mame.cpp::start_luaengine` executes boot.lua before
   `execute` constructs/runs the target machine. Thus callbacks are registered
   before the first reset, rather than after an autoboot timer expires.
2. `luaengine.cpp::attach_notifiers` registers the Lua prestart notifier with
   `first=true`. `machine.cpp::start` has started devices and resolved the map
   before `machine.cpp::run` calls `soft_reset`. The prepended prestart callback
   runs before the device-reset notifier and before scheduler timeslices.
3. Prestart clears RAM, fills only scratch 0x10000..0x1000F with CC, seeds code at
   0x4000, STOP handler at 0x5000, and vectors SSP=0x8000, PC=0x4000, vector3=0x5000.
   It logs every vector/code seed and the bulk zero/scratch initialization.
   It zeros data/address registers and sets SR/SP. Remaining RAM is zero.
4. The native CPU reset state, not a host PC write, fetches reset SSP/PC. The
   reset notifier marks its callback and starts debugger execution. No callback
   after preparation writes guest RAM or CPU registers.
5. CPU breakpoints observe the first instruction at 0x4000 with SR=0x2700,
   SP=0x8000 and D0-D3 zero. The independent verifier requires the earlier
   preparation/reset records and CPU reads of reset vector words 0,2,4,6 before
   accepting this initial state. The complete initial RAM is checked bytewise.

The debugger is active for both products (`-debug -debugger none`), independent
of the product's DEBUG build configuration. Periodic callbacks run even while
stopped in the debugger (`debugcpu.cpp::wait_for_debugger` calls periodic_check).
Each declared instruction boundary is observed before resuming to the next.
The endpoint is **before STOP executes**, or before the exception handler's STOP.
All tested memory instructions must already have executed; the exact PC path,
register/RAM effects, vector reads and exception-frame writes prove their scope.
STOP or process exit is never used as proof of a successful test.

**Runtime ordering remains unobserved in this environment.** Any missing/wrong
bootstrap state yields BLOCKED_BOOTSTRAP; missing/truncated evidence or host
safety limits yield BLOCKED. The source-order argument is not a runtime PASS.
No permanent C++ test initializer or guest loader was added to obtain it.

## Evidence, budgets and independent verification

Per run: actual binary/fixture/source identities, invocation, fixture binary,
assembly/disassembly, initial/final 4 MiB dumps, bounded bus/instruction records,
CPU snapshots and an independent verification report. Host fixture writes and
observer snapshots cannot satisfy CPU-origin access assertions. Taps return no
replacement value. Trace events carry dana-trace-v1 identity/provenance, zero-
based sequence, virtual placeholder cycles, PC, actual 16-bit bus lane masks
and 8/16-bit width; a CPU longword is two native bus transfers.

The observation wrapper uses `dana-d1-2-observation-v1` JSON rather than NDJSON.
A case is limited to 20,000 events or 5 MiB serialized events, 32 instruction
boundaries, 20,000 virtual placeholder cycles (0.02 seconds), and 180 host seconds.
Raw RAM dumps are separate artifacts, not trace events. All paths/results are
isolated by variant, case and fresh run. Missing inputs do not become PASS.
Independent verdicts are PASS/FAIL/BLOCKED with exits 0/1/2. A fixture PASS is
only that executed assertion set; real T qualification remains separate.

## Subsequent independently authorized T execution

No T/Commander/Drive operation was performed by this task. Future operator steps:

1. Verify this source commit and read-only donor pin. Stage separate fresh
   stable/diag trees with the unchanged D1.1 `prepare` helper from this branch.
   The source manifests must describe the new RAM driver, not an R5 binary.
2. Sequential builds, each `make -j3`, with environment `CC=clang CXX=clang++
   LD=clang++` and options `OVERRIDE_CC=clang OVERRIDE_CXX=clang++
   OVERRIDE_LD=clang++ PRECOMPILE=0 TARGET=mame
   SOURCES=src/mame/skeleton/alphasdana.cpp REGENIE=1 TOOLS=0`.
   Stable: `SUBTARGET=danastable BUILDDIR=build/dana-stable`.
   Diag: `SUBTARGET=danadiag BUILDDIR=build/dana-diag DEBUG=1`.
3. Preserve source/list diffs, separate successful build logs and actual output
   hashes. Copy outputs to their distinct `VARIANT/bin` destinations beside
   `VARIANT/source` and `VARIANT/source-manifest.json`. Never reuse AS2K outputs.
4. From this repository, run the following with **verified** absolute paths:

   ```sh
   python3 tests/d1_2_run.py /absolute/stable/bin/dana-stable \
     /absolute/diag/bin/dana-diag /absolute/new-d1-2-evidence
   ```

   The runner first executes the unchanged D1.1 CLI/provenance regression, then
   CPU cases sequentially. It stops at the first FAIL/BLOCKED and reports the
   remaining assertions as unqualified. No build/install is performed by it.
5. Independently recompute and inspect assertions using:

   ```sh
   python3 tests/d1_2_verify.py /absolute/new-d1-2-evidence
   ```

6. Retrieve and verify evidence through the canonical authorized Drive workflow.
   Only a separate supervisor decision after both real T variants pass all ten
   cases may close D1.2. No continuation to D1.3 is implied.

## Local verification and limitations

Executed: actual fixture assembly and disassembly with installed LLVM 19,
fixture regeneration equality, Python and Lua 5.4 syntax parsing, native map /
unchanged D1.1 regression scope checks, 15 verifier unit tests using explicitly
synthetic evidence, and missing-binary runner rejection. The unit fixtures test
verifier acceptance/rejection; they do not claim any CPU executed locally.
No MAME binary, full build, real guest run, T access or dependency installation
was used. Bootstrap API behavior and real vector-3 frames remain qualification
risks; D1.1 CLI regression is prepared but unrun against new binaries.

Rollback: discard the unmerged feature candidate or revert its scoped commit.
Preserve later evidence before removing only owned staging. Never reset/clean
AS2K, donor/reference trees or the qualified D1.1 state. All new code is original
project test/mapping glue using MAME/LLVM interfaces; no GPL/NEO source copied.
