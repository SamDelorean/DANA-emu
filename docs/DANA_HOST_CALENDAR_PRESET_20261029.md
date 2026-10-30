# Dana original Palm UK1.5: host calendar preset

Date: 2026-10-30
Status: **CLOSED / NATIVE PASS** for this increment.

The single installed `runtime/diag/bin/dana-diag` now supplies the host-local
calendar during the original UK1.5 first-format sequence. The unchanged ROM
displays **30/10/26** in Setup 3 before any date-setting input. The host T local
date at installation was 2026-10-30 (UTC-06:00). Host time continues to use the
existing VZ RTC implementation.

Base commit: `c55b560bd124b3be57346d361eea143495c7e51d`.
The implementation, tests and this qualification record are committed together;
the exact revision is available in this file's Git history.

## Original firmware analysis

Ghidra 12.1.3 analyzed the existing private UK1.5 program read-only, with
`-noanalysis`, explicit instruction decoding and decompilation. Native M68000
bus observations independently confirmed the addresses and data flow below.
Analysis scripts: `tests/ghidra/DanaUK15TimeManager.java` and
`tests/ghidra/DanaUK15CalendarBacking.java`.

| Routine or structure | Original UK1.5 evidence |
| --- | --- |
| TimeInit | 0x1007FCEE; allocates 24-byte TimeGlobals and stores its pointer at low memory 0x178 |
| MemNVParams (A03F) | 0x10016668; copies the 30-byte SysNVParams block and verifies/updates the storage-header checksum |
| Calendar backing | SysNVParams.rtcHours at RAM storage header +0x4C; backup RTCTIME at +0x50 |
| RAM store identity | Signature FEEDFACE; version 1 and RAM flag 1 at +4/+6; checksum at +0xFC |
| New-store formatter | 0x10015B78; zeroes the 256-byte header at 0x10015C6C–7A, writes signature at 0x10015C84 and rtcHours at 0x10015CC2 |
| Header checksum | Formatter calls 0x1001A27A at 0x10015DA0, then writes its result at 0x10015DA4 |
| TimeInit consumption | MemNVParams call at 0x1007FD22; RTC test at 0x1007FD26; rtcHours loaded into TimeGlobals at 0x1007FD36 |
| TimGetSeconds (A0F5) | 0x1007FDC2; stable RTC sampling through 0x1007FFEC; conversion helper 0x1008004E |
| TimSetSeconds (A0F6) | 0x1007FE0A; updates TimeGlobals at 0x1007FE72 and RTCTIME at 0x1007FE84 |
| TimSecondsToDateTime (A0FC) | Native dispatch target 0x10042296 |
| TimDateTimeToSeconds (A0FD) | Native dispatch target 0x100421FA |
| Setup startup date check | Resource code at raw-ROM position 0x103275CE–0x10327608; original execution copies this code to RAM |

The original formula is:
`(rtcHours + RTCTIME.hours) * 3600 + RTCTIME.minutes * 60 + RTCTIME.seconds`,
with epoch 1904-01-01. The date conversion routines use the original Palm
calendar arithmetic; they have not been replaced.

Fresh UK1.5 originally initializes rtcHours to `0x000CD740` (2000-01-01).
The Setup resource obtains TimGetSeconds, converts it, and changes **exactly
2000-01-01** to 2005-01-01 through the genuine TimSetSeconds trap. This is why
the prior screen showed 1/1/05. The original RAM caller returned at 0x00091F48;
a private read-only comparison mapped that return to resource position
0x10327608. These resource offsets are not assumed to be execute-in-place
entry points.

DAYR is unrelated to this full calendar: its 9-bit range and the original
alarm initialization at 0x10080144–0x10080150 remain unchanged.

Factual structure/trap cross-checks used the Palm headers preserved in POSE
revision `97b10711fe4ca50c1bd47072378eaab26ba8e81d`
(SystemPrv.h, MemoryPrv.h, Globals.h and SysTraps.py).
No reference implementation or proprietary firmware bytes were copied into
the driver.

## Implementation and preservation

`calendar_format_word` supplies the two bus words of the original factory
rtcHours initializer **before the guest calculates its checksum**. Qualification
requires all of the following:

- Exact original UK1.5 SHA-1 identity, original formatter instruction positions
  and full-word bus writes.
- A completely zeroed 256-byte header before the original FEEDFACE signature
  write, followed by the original RAM/version fields.
- The original unconfigured rtcHours initializer 0x000CD740 in D4.

The header address is discovered from that real format transaction, rather
than fixed to the observed 0x00080000 location. The guest computes the checksum,
loads the NV parameters through MemNVParams, initializes TimeGlobals and
constructs its own Setup controls. No ROM patch, CPU state change, Palm event
injection, framebuffer alteration, post-checksum repair or host-rendered date
is involved. Test PEN input is used only for the existing calibration,
navigation and deliberate preference-change checks.

The preset derives year/month/day from `machine().current_datetime(system_time&)`,
the **same host-local, emulated-time-advancing source** already used by RTCTIME.
Gregorian day count from 1904 is converted to midnight-aligned hours. It does
not seed DAYR or change the RTC offset, RTCEN, alarm, interrupt or tick handlers.

A valid store, normal Palm writes and a restored calendar never qualify merely
because their date happens to match a factory value. The three in-flight preset
fields are included in MAME save-state and are not cleared by hardware reset.
Existing Palm NV storage and MAME state persistence remain the persistence
mechanisms; no separate calendar file or second clock was introduced.

Representable full days are checked against Palm's unsigned 32-bit epoch.
Invalid dates and partial final epoch days are rejected. Exactly 2000-01-01
is left to the original Setup factory-date policy; this increment does not
override that firmware policy.

## Native qualification

ROM: original 6,094,848-byte UK1.5 updater image, unchanged.
SHA-256: `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.

| Check | Observed result |
| --- | --- |
| Incremental Clang 21.1.8 compilation and link | PASS; only driver object/archive/link rebuilt |
| First-format date supplied | rtcHours 0x00106DE8 = 2026-10-30 |
| Original TimeInit on native CPU | MemNVParams output 0x00106DE8 at PC 0x1007FD26; TimeGlobals contains the same date |
| Installed Setup 1 | Frame 1800, original welcome screen |
| Three-point digitizer calibration | Existing qualified PEN sequence reaches Setup 3 |
| Installed Setup 3 | Frame 3510, original Set Date shows 30/10/26, host-derived time |
| Next / Setup 4 / Enter Data | Frames 3900 and 4400 PASS; CPU still running at frame 4800; no physical blocks |
| PWM1 / generated audio | 48,000 Hz, mono 16-bit WAV, peak 5980, 3289 nonzero samples |
| Leap-day transition | MAME -rtc 20240228235945; native Palm advances to 29/2/24 |
| Year transition | MAME -rtc 20261231235945; native Palm advances to 1/1/27 |
| Guest-selected date | Original date picker changes 30/10/26 to 29/10/26 through TimSetSeconds |
| Persistence after guest NV save | rtcHours and NV value 0x00106DD0 survive soft reset |
| State restoration | Same selected date survives restoring the saved emulator state |
| Local production-handler tests | Gregorian conversion, first-format/ROM/header/word guards, pending-state restoration and existing RTC regression PASS |

The deterministic cases use MAME's existing `-rtc` option; T's OS clock was
not changed. Both transitions are native guest midnight processing, including
the corresponding rtcHours/NV advance by 24. The installed final binary was
also used for those deterministic runs.

The preservation test starts with deterministic host 2026-10-30 12:30:00.
At frame 4400, original TimSetSeconds has changed TimeGlobals to 0x00106DD0,
while the NV backup is still the previous value. Palm later saves the NV
parameters itself. After waiting for that save, soft reset reloads 0x00106DD0
at frame 12300; restoring the state preserves it at frame 12900. The preset
is applied only once during the fresh format. An immediate hardware reset
before Palm saves its own NV backup is not evidence of persisted preferences.

The initial preservation harness incorrectly expected immediate NV persistence
and re-ran its autoboot setup on reset. Those harness errors were diagnosed
and corrected; they were not counted as emulator PASS. The final runner
rejects Lua callback errors as well as native physical blocks.

Real generated audio is accredited by the captured WAV. Physical speaker
listening and desktop mouse acceptance retain their prior manual status.

## Evidence and reproduction

Public framebuffer PNGs are direct 560x160 monochrome decodes, without
overlays, text replacement or resizing:

- [Installed host date, Setup 3](evidence/host-calendar-20261030/installed-host-setup3.png)
- [Installed Setup 1](evidence/host-calendar-20261030/installed-setup1.png)
- [Installed Setup 4](evidence/host-calendar-20261030/installed-setup4.png)
- [Installed Enter Data](evidence/host-calendar-20261030/installed-enter-data.png)
- [Leap day](evidence/host-calendar-20261030/leap-setup3.png)
- [Year rollover](evidence/host-calendar-20261030/year-setup3.png)
- [Guest date after reset](evidence/host-calendar-20261030/user-date-after-reset.png)
- [Guest date after state restoration](evidence/host-calendar-20261030/user-date-after-load.png)

Machine-readable qualification: [result.json](evidence/host-calendar-20261030/result.json).
Private ROM, framebuffer byte dumps, WAV, state files, Ghidra projects and
detailed traces remain ignored under
`local-evidence/runtime-compare/calendar-host/`.

Run from the canonical repository on T:

```sh
python3 tests/host_calendar_test.py
python3 tests/rtc_uk15_test.py
python3 tests/run_host_calendar_native.py --case installed-host
python3 tests/run_host_calendar_native.py --case installed-leap --rtc 20240228235945
python3 tests/run_host_calendar_native.py --case installed-year --rtc 20261231235945
python3 tests/run_host_calendar_native.py --case preservation --rtc 20261030123000 --script tests/palm_uk15_calendar_preservation.lua
```

The runner defaults to the official launcher and sole installed executable.
Its candidate option qualifies only the existing build artifact before
installation, in the same build tree. If the shared /tmp quota is exhausted,
use a scoped writable TMPDIR for local compiler fixtures; no global cleanup
is needed.

## Final integration

Installed executable SHA-256:
`1d2478b107c150321e5aca2051c09c80dad061e32079e1cb066c684d89b26d6e`.

Canonical driver and build-tree driver SHA-256:
`cf70b2c2bc2c24f1c321e2c1a0b1776b4a5a6a706fa6ad0a565da1e6d4f05dca`.

The previous operative c073e42e… was preserved until candidate qualification.
After PASS, the candidate was moved atomically into `bin/dana-diag` and tested
again through `tools/run-palm-uk15.sh`. The historical `source/danadiagd`
build artifact no longer exists. A pre-existing executable backup in bin was
converted to a verified, non-executable compressed archive under private local
evidence. The previous operative also has a verified compressed rollback
archive. Only `runtime/diag/bin/dana-diag` remains operational.
