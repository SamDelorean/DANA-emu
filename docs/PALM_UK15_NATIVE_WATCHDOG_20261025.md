# Dana Palm OS UK1.5 — native regression after SCR.DMAP fix; WATCHDOG is first real remaining blocker

**Research and native qualification run in this ChatGPT conversation on authorized T, 2026-10-25.** Firmware is private owner-controlled; no vendor binary bytes are committed. **Palm OS UI has NOT booted.** This is a real physical-reset instruction/decoder observation, not a synthetic boot or a static-only PASS.

## Source state and T environment

- GitHub canonical `SamDelorean/DANA-emu` `main` contains Codex-published DMAP fix at commit `a6badebfac675f53c832aaf5c640d8aedbc44ab0`; driver blob `10f61a6b3c0558e21e43278e64c33a98c397de56`, **source SHA256 `ac32db33a52abe8c81479fef2605ecc52ee9e62ec1477a2131a63cc55e3b72ec`**. Diff was proved to affect **only `scr_w`** compared with prior exact qualified source `9b0e03909c21717758f9f75a31540b28f5943b377b2a0f000f7788b18885783e`.
- Same only MAME DIAG: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`; source `source/src/mame/skeleton/alphasdana.cpp`. Existing qualified installed **`bin/dana-diag` remains UNCHANGED** SHA256 `0a72dffb23420da5d5830b7b78c6ba992d2c582ed6eda6`? **NOT THIS** — actual verified canonical value `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
- Exact firmware `ROMUpdater_enUK150R1.prc` concatenated private original `Flas` payload, **`0x5D0000`** bytes, SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. Original ZIP on T SHA256 `1a0256e35c11c7455a58738f05218e1e290b8d381a5742467f1a512ac25c14fc`. SmallROM 0x0, BigROM 0x8000, no padding or guest state injection.
- Existing Clang21 MAME cache reused: `make -j3 TARGET=mame SUBTARGET=danadiag SOURCES=src/mame/skeleton/alphasdana.cpp BUILDDIR=build/dana-diag DEBUG=1 PRECOMPILE=0 TOOLS=0 USE_QTDEBUG=0 OVERRIDE_CC=clang-21 OVERRIDE_CXX=clang++-21 OVERRIDE_LD=clang++-21`, **BUILD PASS, linked executable**.
- Built native candidate `source/danadiagd` **SHA256 `cdd98381dba484396ba709468cffa137b97bd8a0e955e9006ed9931b2b1ed499`**, NOT INSTALLED. Native command: `source/danadiagd asmdana -rom <private_verified_UK15.raw> -video none -sound none -nothrottle -skip_gameinfo -nowriteconfig -autoboot_script <private_observer.run.lua> -autoboot_delay 0 -log -oslog` with `DANA_PALM_TRACE` pointing to private output. Native MAME process **rc=0** due to controlled observer termination; this does NOT mean Palm OS boot success.
- Private native build/run evidence: `diag/work/uk15_qualify_20261025/dmapfix_20261025_122124/{build.log,native.err,trace.txt}`, scripts/firmware outside GitHub. Last remote readback reconfirmed installed and candidate hashes. No alternative emulator, clone, branch, binary replacement, physical ROM modification or unapproved Ghidra actions.

## Native CPU evidence: SCR bug fixed, WATCHDOG first blocker

```text
DANA_PHYSICAL_IMAGE bytes=6094848 ... read_only=1 topology=linear_array_unqualified
DANA_PHYSICAL_COVERAGE classification=UPDATER_DERIVED_RESET_EXPERIMENT supplied=00000000-005cffff unknown_tail=BLOCKED reset_decode_window=01000000 geometry=UNQUALIFIED
DANA_PHYSICAL_RESET vectors=firmware CSA=00b0 CSCTRL2=1000 CSCTRL3=9c00
DANA_PHYSICAL_VECTOR_READ address=00000000 data=0000 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000002 data=0316 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000004 data=1000 mask=ffff
DANA_PHYSICAL_VECTOR_READ address=00000006 data=02a2 mask=ffff
DANA_PHYSICAL_UNIMPLEMENTED_MMIO write address=fffffb0a mask=ffff
DANA_PHYSICAL_BLOCKED reason=MMIO_WRITE_UNIMPLEMENTED address=fffffb0a data=0000 pc=10005158
DANA_PHYSICAL_CPU curpc=10005152 ir=0268 sp=00000316 usp=00000000 sr=2704 a4=10000338
DANA_PHYSICAL_DECODE csa=00b0 csd=0200 csgba=0000 csgbd=0000 csugba=0000 csctrl=0000/1000/9c00 dram=0000/0000/003c/0000
```

Independent **Lua M68000 CPU bus observer** captured accepted preceding SCR high-byte WRITE at `0xFFFFF000` (bus mask `0xFF00`; `CURPC=0x1000514C`), then blocked full-word WATCHDOG write at `0xFFFFFB0A` (mask `0xFFFF`, value `0x0000`, `CURPC=0x10005152`). **`pc=0x10005158` is the MAME-prefetched next instruction and `ir=0x0268` is NOT the failing opcode.** First blocker is `MOVE.W #0,($0B0A,A0)` with A0=`0xFFFFF000`. Firmware moved forward past the SCR.DMAP fault; no guest UI output.

## Research: exact WATCHDOG hardware semantics (PRIMARY MOTOROLA MANUAL)

**MC68VZ328 Integrated Processor User's Manual** `https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf`, §11.2.5, Table 11-6 (PDF page 218), and §11.1.4:

- `WATCHDOG`: **16-bit** register at **`0xFFFFFB0A`**.
- **Hardware reset value `0x0001`**, watchdog enabled on reset.
- Bits **9..8 CNTR** are 1-Hz tick counter readback; **writing any value resets counter to 0**.
- Bit **7 INTF** is an interrupt indicator, **write-1-to-clear**.
- Bit **1 ISEL** selects reset versus watchdog interrupt on expiry; **reset value 0**.
- Bit **0 EN** enables/disables counter; **reset value 1**, **write `0x0000` disables**. Reserved 15..10 and 6..2 should stay zero.
- The original firmware **legally disables the watchdog** before continuing peripheral initialization. The MAME driver currently routes this internal register to default `physical_mmio_w` => `MMIO_WRITE_UNIMPLEMENTED`. This is a proven missing decoder/handler, not Flash geometry problem, invalid firmware, or a reason to turn every unknown MMIO write into a generic success.
- Full timer overflow/reset/interrupt emulation can be deferred **only as long as enabled-mode behavior remains faithfully modeled/guarded**. The boot's first instruction intentionally disables it; implement documented read/write/reset/interrupt flag semantics rather than a write-and-forget black hole.

### Actual next original 68k instructions, disassembled on T (read-only, NOT YET executed after watchdog)

`m68k-elf-objdump -D -b binary -m m68k:68000 --adjust-vma 0x10000000 --start-address 0x10005142 --stop-address 0x10005178 <private UK15.raw>`. Excerpt provided as mnemonics/target addresses only:

| Original instruction PC | Instruction intent | Hardware address | Qualification |
|---|---|---|---|
| `0x1000514C` | `MOVE.B #$F0,(A0)` | SCR `0xFFFFF000` | NATIVE PASS |
| **`0x10005152`** | **`MOVE.W #0,($0B0A,A0)`** | **WATCHDOG `0xFFFFFB0A`** | **NATIVE FIRST BLOCKER** |
| `0x10005158` | `ANDI.W #$FFEF,($0200,A0)` | PLLCR `0xFFFFF200` | STATIC NEXT, NOT NATIVE |
| `0x1000515E` | `MOVE.W #8,($0D0C,A0)` | ICEMCR `0xFFFFFD0C` | STATIC NEXT, NOT NATIVE |
| `0x10005164` | `MOVE.W #7,($0D0E,A0)` | ICEMSR `0xFFFFFD0E` | STATIC NEXT, NOT NATIVE |
| `0x1000516A` | `MOVE.B #$40,($0300,A0)` | IVR `0xFFFFF300` | STATIC NEXT, NOT NATIVE |
| `0x10005170` | `MOVE.W #$007F,($0304,A0)` | IMR `0xFFFFF304` | STATIC NEXT, NOT NATIVE |

Source for PLLCR and ICE register addresses: pinned Motorola MC68VZ328UM and `cloudpilot-emu/pose-original` `M68VZ328Hwr.h`, available through `research/sources.lock.json`; IVR/IMR already have explicit handlers in current DIAG, while WATCHDOG, PLLCR and ICEMCR/SR currently do not. The table is **not** a sequence of native-observed failures: the emulator was stopped at WATCHDOG.

## CLOSED next coding contract (Codex develops; research stays here)

**Apply only sourced hardware semantics in the current DIAG; no new gate or duplicate build.** Add an explicitly decoded `WATCHDOG @ 0xFFFFFB0A` 16-bit register, reset `0x0001`, proper EN/ISEL/INTF/CNTR handling and write lane behavior; wire through physical map high MMIO while preserving CPU reset and `SCR.DMAP=0`. Native UK1.5 `-rom` test must advance past `CURPC=0x10005152` and report the next actual CPU MMIO transaction. Do not invent a watchdog timeout if no RTC clock source is present; do not silently hide unsupported enabled-mode functionality. Keep the **single** working DIAG and installed SHA unchanged until validated. Do not modify BigROM/SmallROM, RAM/Flash coverage, SD/LCD/ST, code architecture, or unobserved PLLCR/ICE behavior as a surrogate for results. Batch focused static plus native validation together, not dozens of gates.

**Status: SCR.DMAP FIX NATIVE PASS; WATCHDOG 16-bit MMIO is proven next missing hardware; genuine PALM OS screen NOT reached.**
