# UK1.5 physical native — canonical main sync and test (2026-10-25 local / 2026-10-26 UTC)

## Single DIAG, pinned source, immutable operative

User authorized one `main` synchronization/build/native test. Sole T DIAG:
`/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`.

GitHub source was pinned to **`main@2943ba6ca50d22f212d539c473e2b9b51e912518`**. T source had one missing ISP1161 guard relative to that commit: discarded write-port read for Motorola `CLR.W`. A before/after diff was stored locally. Neither branches nor additional DIAG environments were created.

- Final source `source/src/mame/skeleton/alphasdana.cpp`: **SHA256 `195de28abdded94c45713348b7fa6cf44e1fd26a06f7e0c3ef7e8e08e7f6c21a`**, byte-identical to pinned GitHub commit.
- Targeted regression `source/tests/isp1161_uk15_init_test.py`: **SHA256 `1fc8cc25554c4d83b36345b1295ce680d59ba00f8cc8bac209251056572cf7a2`**, byte-identical to pinned GitHub commit.
- Python regression **1/1 PASS**.
- Native incremental MAME build with Clang 21.1.8 **PASS**, return code 0, 25.4 s.
- Staged `source/danadiagd` candidate SHA256 **`6536fd35aa88dfcf7d7b40582bc5ef2316f0afa3add96bc4276611f907e03e79`**; this is NOT the installed binary.
- Sole installed `bin/dana-diag` SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`** before and after, unchanged.
- Exact original private UK1.5 raw firmware SHA256 **`2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`**, unchanged.
- Same existing observer `work/uk15_qualify_20261025/observer.run.lua`, headless physical `-rom`, read-only bus taps, 240 frames bounded. MAME return code 0 is **NOT** proof of Palm OS boot.
- T evidence `work/uk15_qualify_20261025/main_sync_20261025/{focused_regression.log,build.log,native.err,native.out,trace.txt,source_delta_T_to_main.diff}`.

## What the original CPU actually did

Native firmware executed the Ghidra-identified boot sequence, passed GPIO/Port C/Timer2/chip select setup, and logged SDRAM phase progression:

```text
DANA_SDRAM_INIT phase=1 sdctrl=c83f dramc=8000
DANA_SDRAM_INIT phase=2 sdctrl=d03f dramc=8000
DANA_SDRAM_INIT phase=3 sdctrl=d43f dramc=8000
```

The Philips ISP1161 host controller initialization registered commands `85, 83, A4, AA, AB, 8D, A0, 83, 81`. 68000 `CLR.W` memory read-before-write behavior at a write-port was exercised without fabricated HC data:
```text
DANA_ISP1161 discarded_write_port_read cmd=aa phase=0
DANA_ISP1161 discarded_write_port_read cmd=81 phase=1
DANA_ISP1161 cmd=81 value=0000 control=000000c0 atl=1000 itl=0000
```

**First new actual native failure**, after all preceding bus operations:

```text
DANA_PHYSICAL_BLOCKED reason=EXTERNAL_WRITE_OR_PROTECTION address=1f000006 data=00b0 pc=1000306c
DANA_PHYSICAL_CPU curpc=10003064 ir=33fc sp=00003a92 usp=00000000 sr=2700 a4=10000338
DANA_PHYSICAL_DECODE csa=018d csd=0283 csgba=8000 ... csctrl=4150/d000/9c00 dram=0f00/8000/d43f/0000
```

Independent Motorola 68000 binutils disassembly from **the same private ROM image** (base `0x10000000`), excluding non-code bytes before the verified `CURPC`, shows:
```asm
10003064: MOVE.W #$00B0,$1F000006
1000306C: MOVE.W #$AA37,$1F000004
10003074: MOVE.W #$00BA,$1F000006
```

Actual CPU has attempted only the first instruction. **Do not call `$1F000004/$1F000006` ISP1161 registers without independent board/manufacturer evidence.** Existing ISP1161 map for `$1F000000..$1F000003` is already implemented and passed the above native transactions. Determine what external device / lane decode should own `$1F000004..7` by reverse engineering and schematic/hardware evidence **before writing a new peripheral**, not by inventing MMIO state. Neither Palm OS UI nor full USB controller functionality is proven.

## Next action

Investigate true external `0x1F000004..7` devices and address decoding against the original Dana hardware and Ghidra/control-flow. The only *code* change in this sync intervention was copying the exact authoritative committed controller/test, not adding external-register mocks. After a genuinely source-backed minimal change, run same canonical T DIAG native test. No change to installed operative unless full Palm UI later passes.
