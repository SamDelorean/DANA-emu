# Dana UK1.5 LCD splash and chip-select ROP — Ghidra, native long-run (2026-10-25)

## Executive technical outcome

**Authentic Palm OS UK1.5 GENERATED THE PALM POWERED SPLASH** using the real guest 560×160 monochrome SDRAM framebuffer. This was recovered from *the real guest memory*, not painted by host UI code, and confirmed via Ghidra instruction listing for the native LCD initialization routine. 240-frame testing was previously too short to catch a later memory-protection failure. The 30 simulated-second test on the old decoder revealed one erroneous gate on **CSD.ROP for reads**, and the minimal source correction has full native build + actual CPU progress PASS. An independent native write at a protected-stack address remains unresolved. **No Palm OS desktop/GUI boot PASS**; do not claim the device completely boots.

## Authoritative firmware, Ghidra and unique testing location

- Only existing T DIAG: `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`, no duplicate emulators, branches, worktrees, or operating installation.
- Private UK1.5 `work/uk15_qualify_20261025/UK15_private.raw` SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. Updater-derived reset experiment; NOR geometry and unknown image tail unqualified. No private firmware bytes in Git.
- Ghidra **12.1.3**, processor `68000:BE:32:default`, existing `DanaUK15RelocatedTemp` project, base `0x10000000`. Scripts `DanaUK15LCDInitAudit.java`, `DanaUK15SplashLoopAudit.java`, `DanaUK15CSDROPStackAudit.java`, `DanaUK15CSDExactEntry.java`. File/disk quota workaround: `TMPDIR=/dev/shm/dana_ghidra_tmp`, `JAVA_TOOL_OPTIONS="-Djava.io.tmpdir=/dev/shm/dana_ghidra_tmp -XX:-UsePerfData"`. Existing project was expanded privately from the same SHA-verified ROM; **not a new independent emulator or firmware patch**.
- Ghidra-derived source `work/uk15_qualify_20261025/lcd_display_ghidra_20261025/ghidra_lcd_init.txt`, `ghidra_splash_loop.txt`; `work/uk15_qualify_20261025/lcd_rop_read_fix_20261025/ghidra_csd_exact.txt`, `ghidra_cs_stack.txt`.
- Manufacturer primary source **Motorola MC68VZ328UM** §6.2.1, Table 6-10, Figure 6-1, https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf, and corroborating Linux `MC68VZ328.h` CSD bit definitions.

## Genuine LCD output recovered; screen_update existing configuration sufficient

Ghidra at original guest `CURPC=0x10005996..` shows `CLR.B $FFFFFA27`, `MOVE.L A2,$FFFFFA00` (framebuffer base), computes VPW, sets `LXMAX`, `LYMAX`, `LPICF=08`, `LRRA=0050`, then enables the display at `FA27` with `0x82`. Actual read-only MAME write taps to the entire `0xFFFFFA00–0xFFFFFA37` LCD window registered:

```text
LSSA=00003B00
LVPW=23 (35 words/row)
LXMAX=0230 (560)
LYMAX=009F (159; 160 lines)
LPICF=08 (1 bpp)
LCKCON=82 (on)
LRRA=0050
```

The existing physical RAM `m_ram` and existing `screen_update` already satisfy these exact video parameters; DO NOT redesign the renderer or synthesize a host splash.

Read-only original MAME 68000 program-space memory samples read all 5,600 16-bit words from `0x00003B00` (11,200 bytes) at frames 8, 30, 60, 120, 180, 240, with `0x1` bits interpreted as dark monochrome pixels (the existing LCD implementation uses high-to-low bit order). Screenshot `palm_uk15_frame_060.png` is a private 560×160 pixel reconstruction from the real SDRAM and visibly reads **palm POWERED**. It is not a host-rendered imitation. At 60..240 same SHA256 PGM `5909b9ffaad28fb2b149ed7efc8e859b22ce6d9e9a88e9fc6b94c907a7c57241`. Native results:
- Frame 8/30: 0 active pixels.
- Frame 60/120/180/240: **4,161 dark pixels**, **475 nonzero 16-bit words**, **93 rows with active data**, framebuffer CRC-style hash `cb07507e`.
- Original CPU still running code by frame240, so four simulated seconds did NOT prove successful Palm desktop boot.
- Private T artifacts: `work/uk15_qualify_20261025/lcd_display_ghidra_20261025/{lcd_bus_trace.txt,native_vram_metrics.txt,palm_uk15_frame_060.png,ghidra_lcd_init.txt,ghidra_splash_loop.txt}`.

Ghidra definitively disproved earlier hypothesis that PCs `10018054..1001807E` are an idle spin: they are an unrolled `MOVE.L`/memory-fill loop. `CURPC=0x1000CAD6` is `RTE`, a normal return from exception, not inherently a boot failure.

## First actual prolonged-run hardware failure: wrong handling of CSD.ROP on RAM **READ**

Without source change, a bounded 1800-frame native run (30 simulated seconds) reached the first genuine blocked read:
```text
DANA_PHYSICAL_BLOCKED reason=EXTERNAL_DECODE_OR_PROTECTION address=0007ec40 data=0000 pc=1007a108
DANA_PHYSICAL_CPU curpc=1007a106 ir=4e75 sp=0007ec40 sr=2000
DANA_PHYSICAL_DECODE ... csd=2283 ... dram=0f00/8000/d43f/0000
```
Motorola CSD `0xFFFFF116`, bits: `RO=8000`, `SOP=4000`, `ROP=2000`, `UPSIZ=1800`, `DRAM=0200`. **ROP protects a selected region against WRITES; its mere presence cannot disallow reads.** The original source erroneously required `!(m_cs_select[3]&0x6000)` for RAM reads, disallowing the read when ROP=1.

Small code commit `f9dc4c287b00e9171190ac4c4bc8649a779943ce` in single `src/mame/skeleton/alphasdana.cpp` adds `cs_ram_read_allowed(csd,supervisor)` and leaves RO/ROP out of the read gate while preserving a fail-closed SOP user-mode check. Focused production extracted C++20 test `tests/csd_rop_read_protection_test.py` commit `69f6298dcd8d063792c7e2705f41621d8efd709b`: **1/1 PASS**, including native `csd=2283`, RO, combined, SOP user/supervisor. Clang21 full MAME candidate build/link **PASS 19.08 s**. T source SHA256 `cfcdca886f8d38843a667d91baa719d66498abce6fe65b31ad2454e10e0c75ab`. Candidate `source/danadiagd` SHA256 **`a0f5081ea50e4c5f9e3f2d5fb63c41b082701b9f5a4242311ad7f4b32f6d1b7f`**. Operative `bin/dana-diag` SHA256 **`0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`** unchanged.

## Actual next, DIFFERENT protected WRITE now measured

A second 1800-frame native run with the new candidate **passed the previous read**, progressed to a new hardware blocker:
```text
DANA_PHYSICAL_BLOCKED reason=EXTERNAL_WRITE_OR_PROTECTION address=0007ec96 data=ecba pc=1008ecba
DANA_PHYSICAL_CPU curpc=1008ecb8 ir=4e4f sp=0007ec98 usp=00000000 sr=2000 a4=0007e524
DANA_PHYSICAL_DECODE ... csd=2283 ... csctrl=4150/d000/9c00 dram=0f00/8000/d43f/0000
```
This is a *write*, so ROP protection MAY genuinely apply. Do NOT simply remove `0x2000` from the write gate or mirror every RAM address as globally writable. The operation is CPU `TRAP #15` at `1008ECB8`; attempted stack write `0x0007EC96` below `SP=0x0007EC98`.

Read-only native register tap definitively traced CSD transition:
```text
CSD_WRITE data=00002283 mask=ffff CURPC=1007a100 SP=0007ec40 SR=2000
```
Exact original entry-point **disassembled under Ghidra** after correcting a false instruction boundary:
```asm
1007A100 [00782000F116] ORI.W #$2000,($FFFFF116).W
1007A106 [4E75] RTS
```
Thus **the authentic firmware intentionally SETS CSD.ROP**, after screen splash. Another genuine ROM code path at `0x1007A0E0` contains `ANDI.W #$DFFF,($FFFFF116).W` (clears ROP). This is a real software protection workflow, not an accidental emulator variable bit. The original stack write must be reconciled with manufacturer `UPSIZ` protected/unprotected address mapping, chip-select DRAM behavior and CPU function code; **this exact region has NOT been demonstrated writable on hardware**. The existing emulator write protection remains fail-closed. This is the **first and only verified next blocker**.

Native T evidence `work/uk15_qualify_20261025/lcd_rop_read_fix_20261025/{focused.log,build.log,native.err,native_extended_metrics.txt,csd_write_cpu_trace.txt,ghidra_csd_exact.txt,ghidra_cs_stack.txt}`.

### Closed/Not closed

**PASS:** Ghidra authentic LCD initialization reconstruction, authentic palm POWERED framebuffer, existing render configuration, read gate CSD.ROP bug corrected/compiled/native advanced, native ROP activation instruction verified with Ghidra.  
**BLOCKED:** CSD.ROP protected-area *WRITE* at `0x0007EC96` during supervisor TRAP. Need source-backed decoding of UPSIZ/protected range, not a broad bypass.  
**NOT PROVEN:** complete Palm OS startup or functional desktop, visual LCD compositing in installed operative, timing/clock fidelity of the whole system. Do not treat MAME observer exit code 0 as Palm OS boot success.
