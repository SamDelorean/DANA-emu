# Dana original Palm UK1.5: host calendar prefill
Date: 2026-10-29
Status: OPEN / DESIGN AUDITED. Not implemented. Do not claim date sync PASS.

User requirement: at first boot, Setup 3 of 4 must display the same date as the host T (year, month, day), before manual configuration, just as the host already supplies RTC clock time. No guest firmware patch, arbitrary guest RAM writes, fake input, standalone emulator, or branch.

Actual original-ROM results:
- Host-derived HH:MM:SS exists in RTCTIME at FFFFFB00, driven by native MAME machine().current_datetime(system_time&).
- Actual Palm Setup 3 screenshot still shows Set Date: 1/1/05 and host time 23:23, on 2026-10-29.
- MC68VZ328UM chapter 11: RTC hardware has hours/minutes/seconds in RTCTIME and a 9-bit DAYR (FFFFFB1A), wrapping after 512 days. It cannot represent full year/month/day.
- Palm OS Time Manager has 32-bit TimGetSeconds/TimSetSeconds counting seconds from 1904-01-01, distinct from the hardware day counter.
- Ghidra authentic UK1.5 0x10080144..0x10080150 writes RTC alarm then clears DAYR and DAYALARM and enables alarm interrupts.
- Native original-ROM diagnostic observed one DAYR read from PC 1008014c, then guest DAYR writes 000; no evidence the guest consults DAYR to set the date before Setup 3.
- Therefore, host-seeding DAYR does not solve user requirement; an OS-compatible first-boot date initialization path must first be reverse-engineered.

Next bounded implementation:
1. Identify original Time Manager startup, TimGetSeconds/TimSetSeconds backing epoch and battery-backed date preference with Ghidra and guest CPU observability.
2. Initialize guest calendar to host local date BEFORE first-run Setup 3 using a valid OS-compatible initialization mechanism, not direct MMIO invalid year data and not an artificial mouse click.
3. Only set a genuinely unset or factory-default date; preserve user-selected date and existing RTCEN/time-offset, alarms, midnight rollover.
4. Regress authentic Setup 3 date against host date, through Setup 4/Enter Data with existing PWM1, audio and digitizer. Real mouse acceptance remains separate.

Proof:
Ghidra scripts tests/ghidra/DanaUK15RtcCalendarAudit.java, DanaUK15RtcCalendarCode.java.
Local evidence local-evidence/runtime-compare/ghidra-rtc-calendar-code.txt and rtc-calendar-day-trace.out.
Temporary probe was reverted. Original sole installed runtime/diag/bin/dana-diag remains SHA256 c073e42e7368dcd6d9bdf87767316dddab3636edad87f08901d5d26f81b874e0.
References: MC68VZ328UM chapter 11; https://palm.wiki/development/docs/601/PalmOSReference/DateAndTimeManager.html
