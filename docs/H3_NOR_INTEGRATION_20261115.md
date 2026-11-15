# H3: NOR Flash programming, erase and persistence

H3 implements and qualifies two explicit NOR profiles in the one canonical Dana
emulator. Both profiles execute real 68000 command transactions, program and
erase their actual working array, report timed operation states and retain changes
across processes. Original UK1.5 and the existing system regressions are preserved.

**The physical identity of U7 remains NO VERIFICADO.** The profiles below are
supported by firmware command/ID/sector-table evidence and manufacturer documents;
they do not identify a particular photographed Dana board. The existing three-board
configuration contract remains separate from proof of an individual board's wiring,
original 4 MiB firmware, grayscale LCD, SDIO or radio. H4 was not started.

## Release and continuity

| Artifact | SHA-256 |
|---|---|
| Sole installed `runtime/diag/bin/dana-diag` | `d2cc5e10c82919c69077521564a59665dff6c654326e263342dd59aeb1569ae0` |
| `src/mame/skeleton/alphasdana.cpp` | `7e1172858239afdcd7cc4942851164de52f4845a24daf5b49b10ce2161374b0e` |
| Companion `dana_nor_flash.h` | `01839189766e59e3acedc21204312227de03087016c3caefd1438d2dc242a3f0` |
| Unchanged H2 companion | `c2f02d76cc1ad4db22fb6decae847d4008e07eb398ebffa11b2ab0db35e85d6d` |
| Unchanged UART companion | `bf9eddcc21c359f1b7735b5739bc97de5dbfd6769a328755a4321d5cf2585803` |
| Pre-H3 operative, retained compressed privately | `81da0ba414382caecced5f85728fa74705729716a4c7243d28fd3f3969c68b5e` |

Work started on clean `main` at `a78a8399c1c3c1c1b55d16d47cada3d0420bb593`.
During qualification, the legitimate three-configuration documentation commits
through `b07d689361e9b26f8310ae447a1ac22483bdb426` arrived on remote `main`.
They were integrated by fast-forward and preserved, together with their concurrent
Drive workbook additions. No branch, clone, worktree, emulator installation or
replacement build environment was created. Clang 21.1.8 compiled and linked the
existing incremental MAME target. Source copies in that build tree match this release.

## Evidence and profile selection

| Explicit profile | Firmware evidence | Organization and algorithm |
|---|---|---|
| M28W640HCB, 8 MiB | UK1.5 function `1046B30C` recognizes `0020/8849`; table `1046A38E` matches 135 blocks | x16; eight 8 KiB bottom blocks and 127 64 KiB blocks; Intel-compatible command set |
| M29W320DB, 4 MiB | UK1.5 second-family probe at `1046B370` recognizes `0020/22CB`; table `10469F2E` matches all 67 manufacturer blocks | x16; 16 KiB, 8 KiB, 8 KiB, 32 KiB, then 63 64 KiB blocks; AMD-compatible command set |

The original program and erase routines confirm the command families: `1046AA9C`
uses FF/40 and a word payload; `1046AAF6` uses A0 in unlock-bypass mode;
`1046ABD4` uses the AA/55/80/AA/55/30 erase sequence. Existing Ghidra projects
were inspected read-only, without importing, patching or redistributing the ROM.
The 4 MiB ID alone was not treated as proof of a device: its complete original
sector table was also checked against the specific manufacturer's geometry.

Primary specifications:

- [M28W640HCT/HCB, Numonyx November 2008 Rev.3](https://www.ic-components.cz/files/33/M28W640HCB70N6E.pdf), SHA-256 `a908eb508768ce7ac65616a9aa395a01a2c705435618e32adad8ef530aa63eb1`.
- [M29W320DT/DB, Numonyx February 2010 Rev.12](https://www.ic-components.nl/files/75/M29W320DB70N6.pdf), SHA-256 `1a2771b857a163b825446b96ebbe6094a51ff8e4816f400a8a1cc7a5ab6c5e0a`.
- [Motorola MC68VZ328UM](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), chip-select selection, CSA.RO/BSW and SCR.WPV/BETEN.
- MAME's BSD-licensed [intelfsh.cpp](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/intelfsh.cpp) and [intelfsh.h](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/intelfsh.h).

## Architecture and bus integration

The `nor` socket selects exactly one MAME flash device before allocation. Its
default is `-nor m28w640hcb`; `-nor m29w320db` selects the 4 MiB device in the
same executable. The selected device allocates exactly its own 4 or 8 MiB array.
It inherits MAME's x16 storage, ordinary array reader, NVRAM interface and state
ownership. Part-specific command decoding, geometry, protection and operation
timers replace incompatible generic decoder behavior. No MAME core or existing
VZ peripheral was reimplemented, and no GPL emulator code was copied.

CSA selects the chip, BSW must select the qualified x16 bus, and the selected
part's address lines determine array aliases. An updater's length is never used
as a physical capacity mask. CSA.RO suppresses Flash writes and sets SCR.WPV;
with BETEN enabled it raises the genuine 68000 bus-error exception. An odd word
access raises the core's genuine address-error exception. SDRAM initialization
and the existing Flash/RAM mapping are retained.

`:NOR_PROFILE=1` remains the explicit qualification switch; default unknown-part
behavior remains guarded. This is independent of `PHYSRAM` and does not invent a
complete three-variant machine selector. An image larger than the selected part
is rejected, so the private `0x5D0000` UK1.5 image cannot be mounted as 4 MiB.

## Implemented commands and effects

| Function | M28W640HCB, 8 MiB | M29W320DB, 4 MiB |
|---|---|---|
| Array/reset | FF | F0, including three-cycle reset |
| Identification | 90; manufacturer, device, block lock and OTP registers | AA/55/90; manufacturer, device and block protection |
| CFI | 98; QRY, PRI, timings and mixed geometry | 98 at x16 word address 55; four erase regions, PRI and security code; CFI exit restores its previous mode |
| Program | 40/10 word, 30 double, 56 quadruple; double/quad require 12 V profile input | AA/55/A0 word; AA/55/20 unlock bypass, A0 payload, 90/00 exit; 12 V selects accelerated bypass |
| Erase | 20/D0 for one addressed block | AA/55/80/AA/55/30 for one or multiple blocks; 50 us selection window |
| Global erase | **Not supported by this part** | AA/55/80/AA/55/10; protected blocks are retained |
| Status/errors | SR7 READY, suspend bits and sticky program/erase/VPP/protection errors; 70 reads, 50 acknowledges | DQ7 data polling, DQ6/DQ2 toggling, DQ5 error and DQ3 erase timer; F0 clears error |
| Suspend/resume | B0/D0, including program during suspended erase and nested suspension | B0/30 for block erase, including programming another block; program and global erase do not suspend |
| Protection | 60/01 lock, 60/D0 unlock, 60/2F lock-down, WP behavior; volatile block locks reset locked | Boot WP protection, persistent block protection, explicit RP/VID temporary unprotection and documented in-system 60/60/40 protection/verification flows |
| Security | Immutable virtual UID; C0 user OTP and irreversible OTP lock | Immutable virtual UID in CFI security area |

Programming applies the NOR 1-to-0 restriction. A request to recover a zero bit
without erasing reports the appropriate part's program error. Ordinary CPU
writes never assign directly to the array. Erase changes only selected, permitted
blocks, including the real asymmetric boot regions and the final block.

All operation timing uses MAME virtual time. Nominal table timings are 10 us word
program, 400 ms parameter-block/1 s regular-block erase for M28W640HCB;
10 us normal/8 us accelerated program, 800 ms block erase and 40 s global erase
for M29W320DB. Suspend and reset recovery use their documented timing classes.
CFI retains the manufacturer's encoded timeout values. These are digital timing
profiles, without a claim of measured electrical tolerance or analog behavior.

MCU/watchdog reset is not connected to an invented external Flash RP wire. A
paused operation, modes, data and the applicable protection state survive the
processor reset. An actual virtual RP assertion aborts operations and marks
affected data uncertain; the guest must erase before relying on it. Interrupted
OTP or high-voltage protection retains explicit uncertainty instead of reporting
successful programming. Save-state includes command staging, operations, timers,
suspended work, status, protection, OTP and coverage.

## Working storage and image safety

The mounted firmware is an immutable seed. `:NOR_WORK` defaults to **0**. Reference
sessions ignore working NVRAM and cannot write it. Writable sessions require
`:NOR_WORK=1` at startup and use only the selected `-nvram_directory`; they never
write the original image through the firmware interface. M28 reference mode has
its virtual programming supply off; M29 reference writes stop at an explicit
policy guard because its normal VCC supply alone permits programming.

Use a separate working directory per seed/profile. Example input configuration:

```xml
<port tag=":NOR_PROFILE" type="CONFIG" mask="1" defvalue="0" value="1"/>
<port tag=":NOR_WORK" type="CONFIG" mask="1" defvalue="0" value="1"/>
<port tag=":NOR_VPP" type="CONFIG" mask="3" defvalue="1" value="1"/>
```

`NOR_VPP`, `NOR_WP` and `NOR_RP` are explicit virtual pin fixtures. Their PCB nets
are **not** inferred. For M29, VPP/WP LOW protects its boot block; 12 V enables
accelerated bypass. RP/VID is an explicit M29-only high-voltage fixture. M28
high-voltage RP and unqualified x16 partial-data strobes remain guarded.

`NOR_FACTORY=0` retains unknown coverage beyond supplied bytes. `NOR_FACTORY=1`
explicitly initializes missing cells as virgin erased cells; it does not describe
the contents of a used physical Dana. Erase establishes known contents even for
previously unsupplied blocks. Programming unknown prior contents remains guarded.

The `DANANOR5` version-3 NVRAM format binds capacity, device ID, seed length/hash,
coverage policy and generation to a checksummed payload. It stores the array,
coverage, UID, OTP and applicable persistent protection. Slot names separate the
profiles, and an incompatible file is also rejected if deliberately copied into
the other profile's filename. Truncation, checksum or seed mismatches terminate
without overwriting the existing file. A process exit with pending work records
the affected uncertain sectors rather than completing the operation on the host.

State compatibility also binds reference versus writable storage mode. An old save-state cannot silently replace a newly committed NVRAM generation.
Same-session in-flight restore and cross-process restore against an unchanged
committed generation pass; a stale generation is explicitly rejected. Old H2 and
intermediate development states are not promised compatible with this release.

UIDs are deterministic identifiers of the **virtual** seed/profile, not recovered
factory serials from U7. Original ROMs, private dumps, recovery files and historical
backups are not overwritten. Test images are disposable synthetic ROMs, marked
read-only at creation; only their explicit NVRAM copies are writable.

## Native qualification and regressions

`tests/nor_native.py`, `nor_st_native.py` and `run_nor_campaign.py` generate a
synthetic reset ROM. The real 68000 configures CSA/CSD and SDRAM, copies its own
test instructions to RAM, and performs every Flash command and verification read
through the real guest bus. Lua observes CPU journals, requests MAME state save/load
and drives explicit external pin fixtures. It never writes CPU state, RAM, MMIO
or Flash buffers. Tests do not patch or transplant vendor code.

- **8 MiB:** 41 cases, including program/erase, boundary isolation, OTP retention,
  nested suspension and state restore, clocks/status, true CPU exceptions and
  storage rejection tests.
- **4 MiB:** 34 cases, including all asymmetric sector types, real global erase,
  multisector selection, toggling/data polling, bypass/accelerated programming,
  persistent protection, watchdog/RP behavior and state/storage tests.
- **Cross-profile:** an additional incompatible working-file rejection preserves
  both disposable files. Expected bus/storage guards and the intentional pending
  power-cut checkpoint are separately classified; they are not semiconductor
  success claims.
- Both profiles program data, close, reopen and verify it using new CPU executions.
  M29 protection fuses and M28 OTP also survive reopening. Interrupted erase is
  rejected as unknown until a native erase recovers the affected sector.
- All 29 H2 native tests pass. UART1/2/SIR, USB HC/DC/fault/PTD, original AlphaWord
  USB printing, Palm power transitions and the original application campaign pass.
- Original UK1.5/AlphaWord, 81/81 keys, five chords, release/robustness tests,
  digitalizer/LCD/calendar, double SD writes/reopen, EmuTOS, PWM audio, sound UI,
  actual SDL/XTest menus and F12 capture are preserved.

One earlier save-program attempt completed its CPU checks but failed its seed
hash check after an unexplained 16-byte change in that disposable file. It was
discarded. Reproduction under existing `strace` showed MAME opening the seed only
with O_RDONLY and no seed writes. The read-only fixture and subsequent full
qualification retain exact seed hashes. The private original UK1.5 remains
6,094,848 bytes, SHA-256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.

The existing headless GUI harness also had a teardown race: the owned FUSE portal
could disappear between its mountinfo snapshot and fusermount. The harness now
accepts a failed unmount only after verifying that exact mount is gone. A remaining
mount still fails the campaign. No host display, packages or user services changed.

Reproduce on the existing tree, sequentially:

```sh
python3 tests/run_nor_campaign.py --prefix unique-8m --chip m28w640hcb
python3 tests/run_nor_campaign.py --prefix unique-4m --chip m29w320db
```

Add `--installed` to use the sole installed binary. Each prefix must be new.
Public machine-readable receipts, installed checks and exact artifact/workbook
identities are in [H3_NATIVE_RESULTS_20261115.json](H3_NATIVE_RESULTS_20261115.json).
Private states, NVRAM images, trace logs, original print jobs, ROMs and Ghidra
exports remain in the existing local evidence directories.

## Closure boundaries

H3's demonstrated digital NOR functions are operational for both documented 4/8
MiB profiles. Physical U7 identification, board connections and electrical
high-voltage/programmer waveforms remain **NO VERIFICADO**. A full original 4 MiB
Dana firmware image was not supplied: that profile's reset/commands use a synthetic
ROM; the original UK1.5 system regression uses its supported 8 MiB profile. No
claim is made that all three complete machine variants boot or that unknown
AMD/SST/other devices are implemented. Non-normal factory pin engineering and
semiconductor wear/analog fault prediction are not accredited board functions.

The original Drive master `1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l` is updated in place,
preserving its 14 sheets, 1,020 formulas, original history and concurrent variant
matrix. `main` and the GitHub head are synchronized. Development stops after H3.
