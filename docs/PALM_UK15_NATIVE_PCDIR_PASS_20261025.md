# Palm OS UK1.5 native — physical PCDIR PASS, PCDATA fail-closed (2026-10-25)

## Status

**PCDIR is genuinely implemented, built and NATIVE PASS** for the observed original firmware write. **Palm OS UI is NOT booted.** The next *chronological unimplemented guest hardware access* is **PCDATA** (Port C Data, odd/low byte), explicitly stopped at `0xFFFFF411`. Do not claim the later `0xFFFFF610` stop from an intermediate candidate as the first faithful hardware blocker: it occurred while the unimplemented PCDATA lane was silently ignored.

This is a single targeted intervention on the existing T DIAG and GitHub `main`, without Codex, Ghidra, branch, worktree, secondary emulator, ROM patch, forced PC, or replacement of the installed operative.

## Exact source and executable identity

- Production controller: `src/mame/skeleton/alphasdana.cpp`, final SHA256 `2b1d94b5246db4befb501d4f81902b19a43c6abc9b1602b50def9ac6f7d8a5fc`, checked byte-identical with the published GitHub source and T source.
- Coding commits: `ed04e0d` initial PCDIR; `976c53d` explicit lane masks + PCDATA fail-closed guard (authoritative final driver).
- Persistent production-handler regression: `tests/pcdir_register_test.py`, added `db56a6e`; run on T, **1/1 PASS** with Clang++21 C++20 `static_assert`. Checks real inline PCDIR reset/write/read, neighboring PCPDEN/PCSEL isolation, Port C physical view `FF00/00FF` lane selectors, guard bindings and save-state registration.
- Full incremental MAME Clang21 build/link: **PASS**, `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21`. Final candidate `source/danadiagd` SHA256 `537de93f8bd345a66015631561666b83d3ea3f61918961924533e124fcdb7380`.
- Installed `bin/dana-diag` SHA256 **unchanged** `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`; final checked after native run and directed test.
- Private original `UK15_private.raw` SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`, size 6,094,848 B, unchanged; updater-derived reset experiment with unqualified NOR geometry and image tail.
- Canonical T DIAG `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`; private records `work/uk15_qualify_20261025/pcdir_gpt_20261025/`: `pcdir_directed.cpp`, `directed_check.log`, `build.log`, `build_laneguard.log`, `build_pcdata_guard.log`, `native_pcdata_guard.err`, `trace_pcdata_guard.txt`, related intermediate logs. No original ROM bytes published.

## Authentic original firmware CPU evidence

Native command was existing `source/danadiagd asmdana -rom <private verified UK15 raw> -video none -sound none -nothrottle -skip_gameinfo -nowriteconfig -autoboot_script <existing observer.run.lua> -autoboot_delay 0 -log -oslog` with `DANA_PALM_TRACE=<private trace_pcdata_guard.txt>`. Observer is read-only with bounded frames. Exit code 0 means bounded observer exited, **not GUI boot**.

PCDIR high/even lane, guest instruction `CURPC=0x100051A0`:

```text
WRITE address=fffff410 data=00000000 mask=0000ff00 pc=100051a6 curpc=100051a0 sp=00000316 usp=00000000 sr=00002704 ir=0000117c a4=10000338
```

CPU accepted the genuine write and continued. Next guest instruction `CURPC=0x100051A6` wrote odd/low byte, represented by the 16-bit MAME write tap at word base `0xFFFFF410` with `mask=0x00FF`:

```text
WRITE address=fffff410 data=00000000 mask=000000ff pc=100051ac curpc=100051a6 sp=00000316 usp=00000000 sr=00002704 ir=0000117c a4=10000338
```

With PCDATA unsupported handling explicitly installed, the correct **first subsequent guard** fires:

```text
DANA_PHYSICAL_BLOCKED reason=PCDATA_WRITE_UNIMPLEMENTED address=fffff411 data=0000 pc=100051ac
DANA_PHYSICAL_CPU curpc=100051a6 ir=117c sp=00000316 usp=00000000 sr=2704 a4=10000338
```

Manufacturer: MC68VZ328UM §10.4.3, Port C. PCDIR `0xFFFFF410` is 8-bit reset `00`, bits 0=input/1=output; real map uses `umask16(0xff00)`. Its adjacent `PCDATA` at `0xFFFFF411` is **NOT implemented**: a `umask16(0x00ff)` physical handler stops unknown PCDATA reads/writes explicitly, rather than silently accepting/aliasing them. Existing `PCPDEN` and `PCSEL` unchanged. No invented LCD/GPIO external input behavior.

## Next work (not part of this closed increment)

Investigate genuine `PCDATA` byte register behavior against the Motorola manual and existing Dana LCD/GPIO mapping, then implement only the manufacturer-backed functionality needed for the **actually observed** low/odd 8-bit write `00`, with a focused test and one native retry. Do NOT skip PCDATA to work on `0xFFFFF610`; that address was reached only after an unqualified silently ignored PCDATA write in an intermediate candidate. Palm OS graphical boot is still unverified.

**Closed:** PCDIR native write accepted; proper missing PCDATA blocked; SHA, compilation, test, operative integrity verified.
