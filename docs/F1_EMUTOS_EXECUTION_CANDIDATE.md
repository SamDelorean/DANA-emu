# F1 — Native EmuTOS-Dana RAM execution candidate

Work order: issue #8. Active product: dana-diag only. Parent implementation:
9de5dfe6b1a06a417ae4384fa48a99c5113dfafe, including the CPU-name correction.
D1.2 remains independently qualified 9/9 PASS; this delivery does not reopen it.
The General Work Plan and DIAG-FIRST policies on main govern this assignment.
No T access, Commander call, Drive dispatch, stable build or PR merge occurred.

## Implemented behavior

The existing native 32-bit-address MAME M68000 and single 4 MiB RAM map are
preserved. A standard MAME QUICKLOAD image device mounts `emutos.dana`. When an
image is mounted, machine reset suspends the CPU before its first timeslice.
The quickload callback validates the complete envelope and image digest before
writing any RAM. On failure the CPU stays disabled. On success it clears RAM,
copies the original linked image, installs reset SSP/PC, sets the documented
synthetic `_phystop=0x400000`, `_warm_magic=0`, clears D/A registers, sets SR=2700,
and resets/resumes the native CPU. PC is fetched through native reset vectors;
there is no host-side execution substitute or CPU interpreter.

No-image operation uses the previous qualified reset/fixture path. Fresh process
boots are required for independent repetition; hot media replacement and save
state with external guest media are not qualified in this delivery.

The 64-byte big-endian DANARAM1 envelope contains entry, base, length, stack,
phystop, low-RAM end, BSS extent, image SHA-1 and profile flags. SHA-256 binds the
original image, booter ROM, linker map and complete envelope in the external
manifest; native MAME's existing SHA-1 helper also detects changed image bytes
inside the quickload callback. The loader is not a signed software distribution
format. All inputs must pass `f1_guest.py validate` before execution.

The loader requires the map-confirmed pinned R-direct entry/base 0x2140, stack
below low RAM/image, bounded BSS and at most 4 MiB RAM. It does not emulate Palm,
physical Flash reset or the historical DanaRun unsafe 256 KiB block table.
The original booter is preserved/hashed as an input artifact, not executed in
R-direct mode. Its embedded image must exactly match the linked `emutos.img`.

The native IVR remains intact. The initial interrupt configuration prefix adds
16-bit ICR and word-lane-correct 32-bit IMR/ISR/IPR. Masks/reset state follow the
D0.2 VZ contract, Motorola register definitions and existing MAME interrupt-word
handler pattern. ICR includes edge/polarity bits, IMR combines selected lanes,
and ISR acknowledges only edge-enabled external sources. No interrupt source
is invented: pending is zero because timer/UART/GPIO IRQ producers are not yet
implemented. This is not a complete VZ interrupt controller.

PLL, timer, UART, GPIO, LCD, ST and SD remain genuinely unmapped. Based on the
pinned guest's `dana_init`, the next expected unsupported transaction after the
implemented interrupt prefix is PLLFSR at 0xFFFFF202. **That is a source prediction,
not an observed functional dependency.** The runner records whichever actual
unsupported transaction the CPU makes first, with PC/SR/SP, direction, lanes
and data. It never fabricates PLL alternation, UART readiness or OS calls.

## Source reuse and implementation references

- Pinned MAME c4e48388ca620472643110db2941ce70aa5f3c07:
  `imagedev/snapquik.h/.cpp` for standard quickload lifecycle, timer and callback;
  `m68000.cpp` reset/state machinery; `mc68328.cpp/.h` for native word register
  handling; `util/hashing.h` for SHA-1; `output.h/.ipp` for native loader-ready
  output; `debugcmd.cpp` native trace; existing qualified DIAG Lua harness.
- Pinned EmuTOS 9c42ef0f2c2fa9d1e217fced9da68901b2326e8b:
  real Makefile dana target, startup.S, memory.S, dana.c, emutos.ld, tosvars.ld
  and util/danaboot.S/.ld. Original guest sources are built only in isolated
  output; no GPL implementation was copied into MAME code.
- Completed D0.1–D0.5 contracts and Motorola VZ UM/addendum links therein.
  POSE pinned M68VZ328Hwr.h was consulted for ICR edge/polarity definitions;
  the recorded Retro68 Dana references remain the authority for later board
  peripherals. No NEO/POSE/GPL peripheral implementation is pasted here.

## Actual guest build contract

```sh
python3 tools/f1_guest.py build /absolute/pinned-emutos-checkout /absolute/new-guest-output
# An already-installed matching bare-metal ELF toolchain is also supported:
# ... --prefix m68k-elf-
```

The helper checks the exact source SHA, archives it into a new private build
area, checks the actual compiler/mshort multilib, runs `make -j3 dana`, records
compiler/options/status and retains actual emutos.img, emutos-dana.rom, emutos.map.
No reference checkout is cleaned or built in place. Native MiNT is preferred;
ELF=1 is used only with the actual m68k-elf toolchain. Linux m68k GCC with no
mshort runtime is rejected, not relabeled as a qualified guest compiler.

`f1_guest.py package DIRECTORY` requires a successful recorded original build
provenance (it does not infer a source SHA from filenames), validates build outputs and creates the
manifest/container; `validate DIRECTORY` rechecks sizes, SHA-256, linker symbols,
startup branches, native envelope and image bytes. `_realmain` is a local label
that need not appear in GNU maps: its exact target is decoded from the built
`_main` BRA.w, and checked against a map symbol if present. The first header
BRA.s must reach the actual exported `_main`. Missing/ambiguous maps, wrong
entry, bounds, stack overlap, booter mismatch and corruption are rejected.

## First real guest execution test

```sh
python3 tests/f1_emutos_run.py /absolute/diag/bin/dana-diag \
    /absolute/guest-output /absolute/new-evidence
```

The native loader, not Lua, initializes the guest. The test-only plugin installs
breakpoints/taps before the machine starts. The loader-ready native output marks
fixture writes as distinct from CPU operations. Native reset word fetches at
0,2,4,6 must match actual linked stack/entry. The first instruction must have
PC=_os_header, SP=_stktop and SR=2700. The initial RAM image is read independently
and must exactly match the original guest SHA-256.

Native debugger instruction trace and actual `_main`/`_realmain` breakpoint
snapshots corroborate instruction execution. Optional meminit/BIOS/dana_init map
symbols become further one-shot breakpoints. Vector-table reads/writes and MMIO
transactions retain CPU state/lane data; the final stack is retained for exception
inspection. No instruction/register/guest memory modifications are performed by
the observation harness. The native exception engine remains untouched.

The instruction trace uses native loop compaction and an explicitly bounded
prefix (sampling ends at 512 KiB); milestones/MMIO continue afterward. Event
limits are 20,000 / 4 MiB, virtual execution at most 5 seconds at the placeholder
clock, host timeout 180 seconds, and native per-file safety limit 5 MiB. An
oversized/incomplete trace cannot qualify execution. The verifier requires real
trace PCs at the three startup labels, not a host PASS string or exit 0.

Two fresh processes must reach the same normalized CPU/MMIO boundary. A third
negative run corrupts the mounted envelope payload: the native callback must
reject its digest and produce no guest instruction trace. Missing bootstrap or
unavailable inputs are BLOCKED, contradictory executed assertions FAIL. Actual
startup can be PASS for its narrow observed scope while overall delivery remains
BLOCKED_HARDWARE at an actual missing VZ device. No full EmuTOS boot is claimed.

## Qualification job and R7 reuse

One complete job is retained in `tests/hold/000_dana_f1_emutos.job.sh`, HOLD only.
It pins the implementation commit, checks out an isolated source copy, builds
and validates the exact guest, runs existing Python checks, and compares the
production driver with R7 before choosing reuse or a DIAG-only rebuild.
Because this delivery changes production code, R7's known binary SHA
5df95ba18e34580de8f33872c8fb343e67953108cd8c19133c966dbe5c4b5a70 cannot contain
this loader/register prefix; rebuilding is necessary. There is no speculative
rebuild for the old CPU-name harness correction.

Only Clang 21, PRECOMPILE=0, DEBUG=1, make -j3, separate Dana-owned DIAG staging
are allowed by the job. Existing DIAG CLI, real MMIO-01 and targeted RAM-01/RAM-08
regressions are retained. Both authentic guest repeats and native corrupt-load
rejection follow, with logs/hashes/result JSON and a final archive uploaded via
the documented rclone outbox route. The job never dispatches itself. Uploading
or executing this local HOLD script remains a separate authorized action.

## Executed local validation and exact blockers

- Native driver C++20 `-fsyntax-only -Werror` against the pinned MAME headers
  passed, including actual image callback, address-map delegate and output APIs.
- Pinned makedep sourcesproject successfully discovered the reduced driver and
  image-device dependencies in an isolated read-only source view.
- 14 new input/verifier tests passed; 25 qualified RAM verifier tests and 11
  MMIO verifier tests passed unchanged. These use synthetic evidence and prove
  test behavior, not real guest execution. Python/Lua/shell checks are recorded
  in the local report; no source donor was modified.
- The exact EmuTOS source was retrieved. The installed host had no MiNT or
  bare-metal cross compiler. A private, signature-verified Debian cross-GCC14
  extraction was investigated: its `-print-multi-lib` reports only the default
  ABI, not mshort. ELF-mode compilation additionally encountered GCC internal
  compiler errors with -mshort; an -fno-ivopts diagnosis proceeded to an ABI-
  sensitive format error. This unsupported Linux cross compiler is **not** used
  to manufacture accepted guest artifacts. The final build helper honestly
  reports BLOCKED_TOOLCHAIN (m68k-atari-mint-gcc unavailable).
- No emutos.img, emutos-dana.rom or emutos.map was successfully built or validated.
  No image sizes/hashes or observed guest dependency are invented.
- No compatible DIAG executable exists in Cloud; R7 is on T and was not accessed.
  Thus first guest execution, native rejection and runtime regressions are UNRUN.

Precise next step: provide a compatible installed MiNT (or bare-metal m68k-elf)
compiler with mshort runtime, then independently authorize the single HOLD job
on T. It will build the genuine image and changed DIAG executable and collect
actual startup/dependency evidence. Qualification is BLOCKED_TOOLCHAIN and
BLOCKED_EXECUTABLE_MISSING, not a guest hardware PASS/FAIL.

Rollback: revert this bounded F1 source change on the existing branch. Preserve
independent D1.2 evidence and 9de5dfe6. Never reset/clean AS2K or donor checkouts.
Generated guest binaries, package and large logs stay outside Git; no release or
binary publication is authorized by this candidate.
