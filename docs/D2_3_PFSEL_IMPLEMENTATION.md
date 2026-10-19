## Consolidated Dana hardware integration (after D2.3 PFSEL)

**Source status:** multi-subsystem candidate implemented in PR #7; **not compiled on T, no native GUI/keyboard proof yet**. This is the replacement for one-register-per-job development. Preserve original D2.3 PFSEL specification below as historical context; never run old Git-HOLD job 010 against this altered driver.

**Actual integration:**
- MAME core, M68000, 4 MiB RAM, native screen, debugger, scheduler, quickload and save-state remain the host engine. No new CPU/emulator. Existing PLLFSR, interrupt-prefix, Port C and PFSEL code remains.
- Eight VZ GPIO families B/D/E/F/G/J/K/M as independently mapped 8-bit DIR/DATA/PUEN/SEL. All **32 initial register values** matched to `davidgiven/dbztool@d32702383c2ea3523ea58599c52345435c74e900:danainit.sh`. This is R-direct post-bootstrap, NOT physical silicon cold-reset. PFSEL remains separately mapped at 0xFFFFF42B, with PFPUEN separately accessible at 0xFFFFF42A.
- LCD controller: all **13 authentic guest-accessed** `LSSA/LVPW/LXMAX/LYMAX/LPICF/LPOLCF/LACDRC/LPXCD/LCKCON/LRRA/LPOSR/LGPMR/PWMR` mapped at true VZ offsets; LRRA 16-bit per Motorola addendum. MAME SCREEN 560x160 updates from precisely the guest RAM at LSSA, bit-plane 1 bpp, 35 words per row, 11,200 bytes. It only renders when guest registers actually specify 560x160 and enable LCD. Provisional 60 Hz refresh; no cycle-exact LCD DMA/contrast/electrical backlight simulation. No host-origin fake image.
- Dana ST/SPI2: actual 16-bit SPI2 DATA/CTRL pair at 0xFFFFF800/0xFFFFF802, enable/exchange/completion bits modelled. PB6 reset, PK2 handshake as GPIO input, PE3 active-low ST chip-select; first response `0xAA` after ST reset/wake; polling returns 0 unless a genuine MAME host key changes. Four **limited** ST-scancode keys A/B/Return/Space use the Dana byte protocol. Input travels through SPI2, not direct guest keyboard manipulation. The pen ADC transfer is not faked: unsupported 16-bit conversion reports the unsupported placeholder and requires later native qualification; no complete touchscreen claim.
- Source tests updated in `tests/d2_3_test.py` include C++-extracted SPI2/ST reset/ready/selection/key queue tests; existing PFSEL A/B fixtures retained, plus integrated GPIO/LCD map, save-state, framebuffer geometry and E4/E5 detector tests. A new source-pinned DIAG compilation is necessary because old binaries do NOT implement these subsystems.
- F1 guest observer and independent Python verifier recognize these mapped addresses only for a **new SHA-qualified DIAG build**, leaving historical E4 unchanged. The Lua guest observer now independently saves `lcd-frame.bin` from real 4 MiB RAM **only if guest LCD configuration is valid**, along with raw parameters/nonzero count. This capture is evidence, not native screen qualification.
- License hygiene: **MAME BSD-compatible source patterns adapted** and manufacturer/VZ register semantics used; GPL EmuTOS/POSE/Retro68 files read as behavior/protocol reference only. No GPL source copied into MAME. GPIO external pin inputs beyond the modeled ST handshake, LCD scan/DMA accuracy, full ST command set, SPI1/SD, ADC, UART and timer IRQs need genuine guest-driven follow-up, not automatic PASS.
- Caution: the existing source's `m_pfsel` is separate from the generic Port F entry; PFSEL single-byte handler is authoritative. SPI2 bit masks and ST response semantics are engineering candidates from reference sources and **must be checked on real native guest execution**, not marked qualified by text checks.

**Next operational milestone is ONE grouped build/qualification**, never per-register: compile exactly one `SUBTARGET=danadiag` from the frozen integrated source, run existing PFSEL regression A+B (not a rebuild of prior binary), and two authentic unmodified EmuTOS guest runs. Store CPU/MMIO/IRQ trace, guest LCD register snapshot, 11,200-byte frame if configured, SPI2/ST bus observations, SHA-identified executable, archive manifest and independently verified verdict. Old job `010` must not be launched for this newer source. Require fresh build/T authorization, preserve all other projects' inbox entries. **Do not promote `SOURCE_CANDIDATE` to native PASS until evidence is available.**

---
# D2.3 — PFSEL source implementation and DIAG qualification candidate

**D2_3_STATIC_PASS / NATIVE_PENDING. Source only, draft PR #7.** Clean branch
`codex/dana-d1-2-ram-bus` and remote HEAD were both
`56a0a0040edfc161e45c1131692a64c3649fe3af` before editing. Canonical main read:
`77c9758bdff932a4f94d1cc3052e5837c36ce66b`, including native F1-E4 checkpoint
`9d015868989b2813b772e42cf8b91094a313481d`.

## Preserved actual native evidence

Supervisor-audited F1-E4 archive `f1_e4_post_portc_q2foamyg.tar.gz`, 457,980 bytes,
SHA256 `55b60457439105b7fd01a7c927222a1654eccc36523be0dbda12ddb59775f5e0`,
has 36/36 verified manifest members and two real guest PIDs 318446/318469.
It qualifies PCSEL/PCPDEN crossing and the first unsupported **PFSEL byte read**
at PC `83A2`, raw aligned address `FFFFF42A`, mask `00FF`, effective `FFFFF42B`.
The old unsupported read's zero value is not a hardware contract. The later
write at `83A8` and 238 deferred events are not separately qualified progress.
F1-E4 remains scoped PASS/full_boot=false and is not rerun in this delivery.
R2.1, PLLFSR, RAM and original E1/E2 qualification remain preserved.

This report consumes the supplied complete specification and canonical audit;
it does not claim another private archive download/hash audit. The historical
Commander safety rejection remains unchanged. Subsequent native evidence did
not identify its launcher, and is not attributed to that rejected call. No
Commander, T, alternate launcher, Drive dispatch or inbox action occurred here.

## Source contract and reuse

| Source / exact revision | Claim used and evidence level |
| --- | --- |
| Motorola MC68VZ328UM/D Rev.0 §10.4.7.5, Table 10-35, PDF page 197 (index 196); Table 10-33 | Supplied and supervisor-verified primary excerpt: PFSEL at `FFFFF42B`, eight RW bits, silicon reset `87`; 0=dedicated, 1=GPIO; PF0 dedicated function LCONTRAST. The raw PDF was not independently retrieved again in Cloud. |
| Motorola MC68VZ328UMAD/D | Supplied primary review found no contradictory PFSEL reset; no guessed override imported. |
| `davidgiven/dbztool@d32702383c2ea3523ea58599c52345435c74e900`, `danainit.sh:16-19,32-35` | Actual pinned file read, cached SHA rechecked: PCSEL/PCPDEN zero and PFSEL `C5` are software-bootstrap assignments before RAM entry. Script never executed. |
| `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`, `bios/dana.c:63-80,270-276` | Actual pinned file read/hash rechecked: separate PFPUEN/PFSEL byte addresses; PCSEL=0, PCPDEN=0, PFSEL OR 1, later PK accesses. No guest edit. |
| `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`, `src/devices/machine/mc68328.cpp:154-155,420,601,1956-1965` | Pinned donor read only: separate `u8` handlers and save-item pattern are reusable. Donor startup `FF` is neither VZ silicon `87` nor the R-direct `C5` profile. |
| DANA-emu reviewed driver blob `b3b770bdbbcce3dff24470b1e697945fc2b5971d` | Existing individual Port C byte mapping, software reset, native save system and 32-bit-address M68000/RAM are retained. Only nine production lines are added. |

Official primary URLs: [manual](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf),
[addendum](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf).
Evidence limit: the manufacturer contract here relies on the supplied exact
table and independent canonical review, not a new local PDF fetch. No missing
primary value is replaced with a donor/POSE guess. Cached original source
identities are recorded in candidate status. No GPL implementation was copied.

### Three distinct values and the guest comment discrepancy

- Physical silicon reset: **87**, documented, no cold-boot path implemented.
- Existing machine's synthetic **R-direct reset/launch: C5**, from dbztool.
- Donor MC68328 startup **FF**, not imported.

The current architecture exposes the existing R-direct profile only.
`pfsel_reset()` therefore restores C5 on its machine reset, matching Port C's
software-profile policy. It does not claim physical power-on emulation.

Original EmuTOS says `PFSEL |= 0x01; /* enable LCONTRAST */`. C5 already has
bit 0 set, so its register result stays C5. Motorola says SEL0=1 selects GPIO,
while SEL0=0 selects the dedicated LCONTRAST function. **Both facts are retained**;
neither the guest nor physical contrast behavior is silently corrected or
claimed working. This implementation stores all eight bits and has no pin-level
effects, LCD, framebuffer, keyboard, power or readiness simulation.

## Production and diagnostic changes

`alphasdana.cpp` adds one `u8` latch/getter/setter/reset helper, one save-item
and exactly one address-map entry at **F42B..F42B**. It adds no F42A word/page
mapping, PFPUEN or low alias. Native MAME's existing big-endian 16-bit space
dispatches `00FF` at F42A to F42B; high-lane F42A remains unmapped. CPU, RAM,
loader, Port C and PLLFSR methods remain unchanged.

New test-owned MC68000 fixture: 294 bytes, SHA256
`7a73d9966b07eb8669a393735fc7640ea917f25a7428a53eb1afa1de4b7d3a1a`.
Python emission independently matches GNU `as -m68000`/`objcopy` bytes from
`tests/d2_3_pfsel_fixture.s`. The word read/write uses **even F42A**, not odd
F42B. Marker prefix is at 4000, branch displacement `010C`, first endpoint
4110, post-reset path 4114, CPU byte read 4116, result store 411C, STOP 4122.
Assembler checking builds only this test fixture, not an emulator or guest ROM.

Future native A exercises C5, 00/01/80/FF, repeated reads, high-lane negative
writes/reads, a genuine word transaction with only the low byte implemented,
24-bit alias rejection, CPU stores and full RAM comparisons; final latch 5A is
saved, host-mutated to 3C and restored by actual MAME buffer APIs. High/unmapped
read data is retained as observed and is not assigned a fabricated contract.
Fresh native B uses the same marker strategy as qualified R2.1 to branch around
the first body after one soft reset. Four new CPU vector reads, surviving RAM
marker, CPU low-lane PFSEL read C5, matching CPU result store and full RAM/STOP
trace must corroborate reset. No missing reset notifier or transient PC gate
is substituted for this evidence. A/B identities must differ.

Taps never replace data, exit or issue debugger operations; periodic capture
uses bounded raw events, epoch/request IDs and full snapshots. Independent
Python verification preserves missing/ambiguous evidence as BLOCKED. A wrong
reset value becomes FAIL only with a coherent CPU read/store/RAM/trace chain.
Save/restore is not inferred from source registration alone.

### F1-E5 build identity and real-guest acceptance

`--pfsel-build BINARY_QUALIFICATION_JSON` extends the existing F1 runner/Lua,
not a parallel emulator. Qualification requires the current driver/source SHA,
donor pin, successful DIAG-only build record/command, exact actual executable
path/hash, a matching hash-bound staged build manifest, and an observation-bound
qualification SHA. The old E4
binary SHA `d7bcdf513289a73b8a5c7ab1d258eeac45dc8dd6d89dd7d568cf7784900e6fe5`
is explicitly rejected for PFSEL. Old E4 mode keeps PFSEL unsupported and its
historical compiled driver hash, rather than relabelling that binary as new.

Only E5 enables PFSEL in observer/verifier classification. Two authentic guest
processes must reproduce the map-bound startup/old PCSEL crossing and then:
CPU read at **83A2**, aligned F42A/00FF = **C5**, CPU write at **83A8** = **C5**,
followed by the same newly observed first unsupported byte with trace/state/
lane provenance. No PKSEL/PKDATA address is preassigned as the outcome. Original
E4 raw archives are immutable; their old zero PFSEL read is not requalified.
No new native outcome, full boot or display result is claimed here.

## Executed local validation

```sh
PYTHONPATH=tests python3 -m unittest f1_test_guest f1_e4_test d2_3_test.SourceContracts d2_3_test.NativeEvidence d2_3_test.E5 d2_2_gpio_contract_test -v
```

Actual output: **`Ran 70 tests in 4.359s` / `OK`, exit 0**. These are static
logic, Lua callback mocks and synthetic evidence checks, never native MAME
qualification. Extracted real C++ methods pass all 256 values, representative
00/01/80/FF/readback/reset and latch snapshot checks. Native MAME serialization
and real lane dispatch remain pending despite save-item/map source checks.
Existing Port C/PLLFSR bodies compare unchanged; the old Port C map guard is
extended only to the approved F42B byte. No assertion is disabled.

Negatives include wrong high/low lanes, host-forged reads, duplicate vectors,
missing transition, stale result/marker, absent STOP, wrong build/source/hash
and old executable; coherent wrong physical-reset 87 versus R-direct C5 yields
FAIL, while missing/contradictory evidence stays BLOCKED. Actual Lua callback
mocks verify A save and B CPU reset capture without emulator execution or tap
exit/debugger calls. Python compilation, complete Lua parsing, Bash syntax,
embedded job Python AST and `git diff --check` pass. Fixture assembly is checked
independently; generated objects/binary/logs stay outside Git.

## One future qualification job, Git HOLD only

`tests/hold/010_dana_d23_pfsel_diag.job.sh` requires **both** fresh scoped flags:

```text
DANA_D2_3_AUTHORIZED=YES
DANA_D2_3_BUILD_AUTHORIZED=YES
```

These are runtime guards, not authorization granted by this source delivery.
New explicit T/build/Commander permission and its separate call cap are needed.
The historical safety rejection must not be bypassed; there is no Codex/model
decision or alternate launcher in the execution path. No job upload/dispatch
was performed. Missing flags and obsolete D2.2/F1-E4 flags return HOLD/exit 2
before Python/T work; the native-only flag without build authorization also
returns HOLD/exit 2.

The job validates unchanged private E1/E2 files and provenance first, fetches
its immutable DANA source, rejects unrelated production/build changes, runs
focused Python negatives before compilation, archives the pinned donor through
the existing DIAG prepare helper, and performs **one** isolated Clang 21
`make -j3 SUBTARGET=danadiag DEBUG=1 PRECOMPILE=0` build. Donor HEAD may differ;
only the pinned object is read. No donor checkout/reset/write, generic MAME,
stable variant, compiler installation, build fallback or ROM rebuild occurs.

The new executable SHA is recorded **after successful compilation**, along with
source/driver/donor/list provenance and build command. It is not predicted and
must differ from historical E4. That same new DIAG runs PFSEL A/B, followed
only after qualification by two authentic E5 guests. Original observations,
readbacks, traces, RAM, build logs, map, provenance, independent results and a
hash manifest go to the existing private outbox archive/receipt transport.
Upload problems prevent success. No binary is published.

Immutable job source: `11cb0d3f46c787f0a5061118b324f2bcedc4a712`.
Job SHA256: `eb2f94bcb6c6d881c178e162e799227121061768a87045fa13461acda8965b27`.
These identities are also in `tests/d2_3_candidate_status.json`.
**Remaining:** full new MAME compilation and all native D2.3/E5 outcomes are
NATIVE_PENDING. No emulator, MAME/EmuTOS build, T/Commander action, merge or
Drive dispatch occurred in Codex. Only isolated allowed C++ logic programs and
test-fixture assembly were compiled locally. PFPUEN, pins, LCD and the next
unknown peripheral remain outside this source increment.
