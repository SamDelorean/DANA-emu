# DANA-emu UK1.5: real LCD live framebuffer reaches AlphaSmart second splash (2026-10-26)

## Verified new functional boot milestone, not an MMIO conjecture

**After the latest integrated ISP1161A1 register/PTD and native VZ bootstrap features**, the candidate `source/danadiagd` executes the **unchanged authentic private UK1.5 Palm ROM** to the **SECOND hardware LCD screen**: original `Palm Powered` splash first, then **AlphaSmart** logo after roughly five simulated seconds. At 90 simulated seconds the **AlphaSmart** image is still displayed. The emulator is **NOT at the Palm OS desktop**, and this test did not implement or install any new hardware change.

**Critical correction of the earlier reports**: all prior video observers read a *hard-coded* RAM address `0x00003B00`, which preserved the old Palm Powered splash. Consequently, the claim that the *active* display remained on Palm Powered was an **observer error**. The emulator's own screen renderer already uses the actual LCD `LSSA`; the ROM programmed another framebuffer. This report supersedes earlier video-state claims. Do not alter the emulator graphics code based on the stale fixed-address screenshot.

### Current exact candidate and integrity

Single existing T DIAG:
`/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`

- Exact source `src/mame/skeleton/alphasdana.cpp`, pinned GitHub `main@b19aec5208343dbf3244963b21b8c8acae1a2779`, SHA256 `42885f69ebbb70c4540e9e222a1754a7f3230b7ba747e87f5645225b75ef00d9`.
- Compiled test candidate `source/danadiagd` SHA256 **`6f2eb8a7789bfa6930c14363ca696a3272dad50c114000517c0d888873f53d49`**.
- Original operative **unchanged** `bin/dana-diag` SHA256 `0a72dffb23420da5d5830b7ee6725eb734cd59e17d87700a3d5c47a67dc6ea4a`.
- Private original ROM **unchanged** `UK15_private.raw` SHA256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. Do not upload ROM.

### Native register and screen evidence

Measured with a *new passive Lua observer* which reads `LSSA` from actual guest-visible VZ LCD registers `0xFFFFFA00..03`, `LVPW` at `0xFFFFFA05`, `LPICF` at `0xFFFFFA20`, `LCKCON` at `0xFFFFFA27`; uses real stride `LVPW×2`, not any host-generated bitmap.

| Frame / simulated time | LCD LSSA | Status and authentic bitmap |
|---|---|---|
| 60 / 1 s | `00003B00` | **Palm Powered**; 475 nonzero 16-bit words; hash `cb07507e` |
| 240 / 4 s | `00003B00` | Palm Powered |
| 300 / 5 s | `00072A10` | **AlphaSmart** logo; 316 nonzero 16-bit words; hash `2011d129` |
| 360 / 6 s | `00072A10` | AlphaSmart |
| 1800 / 30 s | `00072A10` | AlphaSmart |
| 3600 / 60 s | `00072A10` | AlphaSmart, unchanged |
| 5400 / 90 s | `00072A10` | AlphaSmart, unchanged |

All checks retain actual `LVPW=0x23` (35 words = 70 bytes/line), `LPICF=0x08`, `LCKCON=0x82`, `LXMAX=0x0230` (560), `LYMAX=0x009F` (159). The existing 1bpp `screen_update` display gates and active video base are satisfied. No artificial screen compositor is required.

Actual guest frame copies `live_lcd_0060.png`, `live_lcd_0300.png`, `live_lcd_1800.png`, corresponding PGM files, and `live_lcd_3600.pgm`/`live_lcd_5400.pgm` saved privately in the same DIAG work folder:
`work/uk15_qualify_20261025/boot_progress_20261026/`.

Previous 90-second hard-coded video observer had reported old framebuffer `3B00` unchanged: it **did not represent the current LCD output after frame 300**. Actual CPU progresses at least through the transition to AlphaSmart. Bounded observers exit code 0 because their Lua frame limit fires; not Palm desktop boot success.

## Ghidra original firmware location / current wait, not hardware guessing

Ghidra 12.1.3 on **the original UK1.5 private ROM** with `68000:BE:32:default`; original ROM segment at `10320000–1032FFFF` mapped in the existing project, not a separate emulator. Script `ghidra_scripts/DanaUK15BootCallerAudit.java`, transcript `boot_progress_20261026/ghidra_boot_caller.txt`.

Original program:
```asm
10325962 PEA   (-0xA,A6)
10325966 JSR   103256DE
1032596A MOVE.W (-0xA,A6),(0x3C,A3)

103256EA MOVE.B (0xFFFFF419).W,D0  ; Port D DATA
103256EE ANDI.W #0x0004,D0         ; PD2
103256F4 EORI.B #0x04,(0xFFFFF41C).W
103256FA MOVE.B (0xFFFFF419).W,D0
103256FE ANDI.W #0x0002,D0         ; PD1
10325704 EORI.B #0x02,(0xFFFFF41C).W
1032570A PEA #0x00FA
1032570E TRAP #$F                ; wait/time
10325712 MOVE.B (0xFFFFF419).W,D0
10325716 ANDI.W #0x0006,D0        ; PD1 or PD2 high?
1032571C BEQ 10325722
1032571E MOVEQ #0,D3
10325722 ADDQ.B #1,D3
10325724 CMPI.B #3,D3
10325728 BCS 103256EA
```
The 68000 CPU spends most of its post-AlphaSmart time in actual low-level delay routine `1007B060–1007B0AE` that waits for edges of VZ `PLLFSR.CLK32`; **this clock DOES toggle and routine's D2 counter actually decreases and reloads**. An earlier frame-snapshot of D2=8 repeated at 10-second intervals was **sampling aliasing**, not evidence of a halted oscillator. A more frequent 2-frame trace caught D2=15,11,7,2,14... and program executed other functions intermittently.

Repeated live 68000 stack chain after 5 s, **identical** at frames 304, 360, 1200, 1800, explains the real site where startup is still waiting:
```text
A6=0006EF4A RET=10325712 ARG=000000FA
A6=0006EF5C RET=1032596A ARG=0006EF7E
A6=0006EF88 RET=10317FF2
A6=0006EFB4 RET=101101E4
A6=0006EFC4 RET=10110148
A6=0006F016 RET=1010FD84
...
```

Native Port D from real address `0xFFFFF418–0xFFFFF41F` at frame 304–1800: PDDIR=`03`, PDDATA=`8C` (PD2 high), PDPUEN=`1C`, PDSEL=`0F`, Port-D extended control register `F41D=0C`, while `F41C` sometimes toggles `00/04`. Current external PD2/PD3 pin levels come from project SDIRQ input assumptions, **not a verified Dana schematic**.

A *controlled in-memory-only observer test* forced PD2 low in guest read responses after frame 303 using a MAME Lua `install_read_tap` (verified override guest-visible `PD_DATA=88`), **without any code/ROM changes**. A second test forced PD1 and PD2 low. In both cases the firmware was still found inside the same parent call chain and the AlphaSmart framebuffer remained unchanged through 30 s. **Therefore the cause of the stall is NOT established as simply PD2 input polarity. Do not commit a high→low PD2 default patch or fake return values.** The high-level waiting requirement and board linkage need actual further Ghidra/system event evidence.

The frame-level observer and the full 90-second long-run show **no `DANA_PHYSICAL_BLOCKED`** and no missing ISP1161 command. They do **not prove** perfect USB engine or GUI boot.

## Precise next work scope

The **verified progress is the real second AlphaSmart splash**. Current unresolved behavior is original firmware routine `103256DE`, its nested callers `10325966`, `10317FF2`, and device input/interrupt sequencing near Port D `FFFFF419`, not a specific new MMIO command or non-oscillating CLK32. Do not patch hardware inputs or CPU time from symptoms; continue static+native diagnosis of these original routines and qualified board conditions as a coherent startup subsystem.

No main-source edits, no new DIAG copies, no Codex, no operative installation were performed for this observation-only milestone.
