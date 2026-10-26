# UK1.5 original Palm OS startup — Ghidra reverse engineering and first native verification (2026-10-25)

## Evidence source and method

- Analyzed the **authentic privately held UK 1.5 raw image**, SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3` (6,094,848 bytes), using Ghidra **12.1.3**, language `68000:BE:32:default`. Boot vectors: SSP `00000316`, PC `100002A2`.
- Ghidra import initially returned `EDQUOT` on `/tmp/spc-ghidra/*.cache` and JVM perfdata, confirmed with `strace`. Resolved by `TMPDIR=/dev/shm/dana_ghidra_tmp` and `JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=/dev/shm/dana_ghidra_tmp -XX:-UsePerfData"`, without deleting existing user data.
- Imported only a **private 65,536-byte prefix** of the same checked raw image at ROM mapping base **`0x10000000`** to avoid unnecessary full-firmware analysis. This prefix contains the actual startup routine `0x10005146..0x10005444`. Private excerpt SHA256 `f25cc3afd3aea08feafc6fa41b2c801400410202b11f3ec6cbf16aa0daa03992`. No ROM content committed.
- Ghidra automation `work/uk15_qualify_20261025/ghidra_scripts/DanaUK15BootAudit.java`, artifacts `ghidra_uk15_boot_extended.txt` and `ghidra_uk15_extended.log` on sole T DIAG. The automated listing covered `0x10005140..0x10005800` and initial reset window. This is actual Ghidra-produced Motorola instruction listing, corroborated with previously captured native CPU bus events, **not speculative MMIO inference**.

## Ghidra-proven sequence

A0 is initialized to `0xFFFFF000` by `MOVEA.L #$FFFFF000,A0` at `0x10005146`. Therefore A0-displacement writes below use genuine VZ system addresses:

| Guest PC | M68000 instruction decoded by Ghidra | Actual register operation |
|---|---|---|
| `1000514C` | `MOVE.B #$F0,($0000,A0)` | SCR at FFFFF000 |
| `10005152` | `MOVE.W #$0000,($0B0A,A0)` | WATCHDOG off |
| `10005158` | `ANDI.W #$FFEF,($0200,A0)` | PLLCR RMW |
| `1000515E` | `MOVE.W #$0008,($0D0C,A0)` | ICEMCR |
| `10005164` | `MOVE.W #$0007,($0D0E,A0)` | ICEMSR |
| `1000517C` | `MOVE.W #$0000,($0008,A0)` | IODCR |
| `1000519A` | `MOVE.B #$00,($0413,A0)` | PCSEL |
| `100051A0` | `MOVE.B #$00,($0410,A0)` | PCDIR |
| `100051A6` | `MOVE.B #$00,($0411,A0)` | PCDATA |
| `100051AC` | `MOVE.B #$00,($0412,A0)` | PCPDEN |
| `10005272` | `MOVE.B #$00,($0A27,A0)` | Nearby timer/IO setup |
| `10005278` | `MOVE.W #$0000,($0600,A0)` | TCTL1 off |
| `1000527E` | `MOVE.W #$0000,($0610,A0)` | TCTL2 off |
| `10005284` | `MOVE.W #$D000,($010C,A0)` | CSCTRL2 configuration |
| `1000528A` | `MOVE.W #$0100,($010A,A0)` | CSCTRL1 configuration |
| `1000529C` | `MOVE.W D1,($0100,A0)` | CSA base after D1 calculation |
| `100052A0` | `MOVE.W #$018D,($0110,A0)` | CS selector |
| `100052AC` | `CMPI.L #$FEEDBEEF,($0008,A1)` | Read-only Flash capacity/identification probe |
| `100052EC` | `MOVE.W #$F800,($0102,A0)` | CS base group register |
| `100052F2` | `MOVE.W #$0081,($0112,A0)` | CS selection |
| `10005328..` | DRAM controller writes FFFFFCxx | SDRAM initialization path (code decoded, native completion not tested here) |

The original initializer also performs a long contiguous configuration of GPIO ports B, D, E, F, G, J, K, M between these steps; see private Ghidra listing for precise order and byte values. Some data/text regions outside verified entry points are not labeled functions and should not be treated as authoritative automatically.

## This intervention: actual code and native evidence

- GitHub `85258bc` added `PCDATA` latch and a guarded Timer2 disabled-control subset to the already existing single `alphasdana.cpp` with save/reset/physical map.
- GitHub `042b5d8` updated focused `tests/pcdir_register_test.py`; **actual extracted C++20 production handlers test PASS, 1/1** on T. This does not prove LCD external pin levels or running Timer2.
- Exact tested source SHA256 `915670eb9ad4ce38ad211ce19830bdc6523273fb7e15835d30114c4d7016eb36`.
- T Clang21 incremental build/link **PASS** (22.8 s). Staged candidate `source/danadiagd` SHA256 **`222e8609bba752b32743a948204fb5cf2d9e0688f5d95d9d36194a2566045cff`**.
- Sole installed operative `bin/dana-diag` SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a` unchanged**. Original ROM unchanged, same read-only 240-frame bounded observer.
- Native UK1.5 **accepted** PCDIR at `FFFFF410` (`CURPC=100051A0`), PCDATA at `FFFFF411` (`CURPC=100051A6`, low-byte bus lane), and TCTL2 word `0000` at `FFFFF610` (`CURPC=1000527E`). This confirms sequential CPU continuation; **not** a full GPIO electrical simulation or Timer2 functional timer PASS.
- First subsequent native blocker in THIS EXACT CANDIDATE, not necessarily in later independently published commits:

```text
DANA_PHYSICAL_BLOCKED reason=CS_CONTROL_MODE address=fffff10c data=d000 pc=1000528a
DANA_PHYSICAL_CPU curpc=10005284 ir=317c sp=00000316 usp=00000000 sr=2708 a4=10000338
DANA_PHYSICAL_DECODE ... csctrl=0000/d000/9c00 ...
```

- T logs `work/uk15_qualify_20261025/ghidra_portc_timer2_20261025/{test.txt,build.log,native.err,trace.txt,native.out}`.

**Non-claims:** Palm OS graphical UI remains unbooted; no complete firmware import/decompiler call graph was produced; the 64KiB Ghidra listing documents the authentic executed startup routine; this candidate's CSCTRL2 stop is historical if a newer main commit implements and tests that behavior. Avoid rewriting newest source using an older branch or T SHA without checking current `main`.
