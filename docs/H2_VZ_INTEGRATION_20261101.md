# H2: MC68VZ328 clock, power, RTC, watchdog and GPIO integration

This user-authorized H2 intervention extends the existing MCU implementation in `alphasdana_state`. It does not introduce another emulator, MCU, checkout, build environment or installation. The canonical repository is `/home/spc/Projects/alphasmart/DANA-emu`, branch `main`; the sole installed executable is `runtime/diag/bin/dana-diag`.

**Result: the H2 digital functions below pass actual 68000 execution and the executed system regressions.** GPIO board continuity and electrical/analog fidelity remain unverified. This is not certification of every VZ silicon mode or the entire Dana hardware. H3 NOR programming/erase, Palm Beam file transfer, and USB Computer/HotSync are not closed by this work.

## Release identity

| Artifact | SHA-256 |
|---|---|
| Installed `runtime/diag/bin/dana-diag` | `81da0ba414382caecced5f85728fa74705729716a4c7243d28fd3f3969c68b5e` |
| `src/mame/skeleton/alphasdana.cpp` | `031360bf2f690a3c0615891ce5093ffc7c9361d30055184d0cc9a210b4c01dd3` |
| Companion implementation `alphasdana_h2.h` | `c2f02d76cc1ad4db22fb6decae847d4008e07eb398ebffa11b2ab0db35e85d6d` |
| Unchanged UART implementation `dana_vz_uart.h` | `bf9eddcc21c359f1b7735b5739bc97de5dbfd6769a328755a4321d5cf2585803` |
| Pre-H2 operative, retained compressed privately | `f1002968c67dd2f6ebaf9ae107f6f120321986b94fb495eb4b9826414d36cdcc` |

The initial clean HEAD was `beb9516348ae13d33bea388eb4a582b8ae9b5b74`. Clang 21.1.8 compiled and linked the existing incremental MAME target. Source copies in the canonical build tree match the tracked source. Original UK1.5 remains unchanged: 6,094,848 bytes, SHA-256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. ROMs, states, framebuffer dumps, printer jobs and Ghidra exports remain private under `local-evidence`/the existing runtime.

## Implemented behavior

### Clock tree and power

`PLLCLK = 2 * (14 * (PC + 1) + QC + 1) * XTAL`, with PC=PLLFSR[7:0], QC=[11:8]. PRESC1, PRESC2, SYSCLKSEL and LCDCLKSEL determine the downstream clocks. PLLFSR protection is sticky until reset; CLK32 reads its real scheduled phase. UART1/2 use their existing clock API; Timer1/2, SPI1, PWM1 and LCD clock consumers use the shared graph.

Physical reset retains PLLCR=`24B3`, PLLFSR=`0347`: SYSCLK=16.580608 MHz. Original firmware selects `2483` and reaches 33.161216 MHz. The synthetic R-direct profile explicitly selects `2493` to preserve its previously qualified 33.161216 MHz; it no longer advertises `/2` while secretly running a different frequency. This is a compatibility-profile setting, not a claimed physical-reset value or a PLL write found in dbztool. Its watchdog disable is consistent with the pinned dbztool initializer.

DISPLL stops PLL-fed clocks after 30 SYSCLK cycles. CLK32 and its selected consumers continue. SYSCLK timer counts and in-flight SPI/PWM timing are retained and resumed. Changing PLL must not restart an independent CLK32 timer's compare interval. WKSEL selects 32/48/64/96 CLK32 recovery cycles. CLKEN/PFSEL affect CLKO output, not PLL operation.

PCTLR modulates **CPUCLK only**, over 31 CLK32 periods. WIDTH=0 gives doze; WIDTH=31 full duty. Native timers continue on SYSCLK during doze. A source enabled by IMR clears PCEN even if the CPU SR masks its ISR. Edge INT[3:0] can wake PCM doze but cannot restart an absent PLL (UM 10.4.5.9). Genuine M68000 STOP remains a separate CPU instruction; no guest PC is forced. Serialized timers, PLL/PCM phase, prescalers and retained RAM survive same-build save/restore.

Resolved paths: `PLL_CLOCK_MODE_UNIMPLEMENTED`, `PLL_SLEEP_MODE_UNIMPLEMENTED_R_DIRECT`, `PLL_WAKE_DELAY_UNIMPLEMENTED`, `PCTLR_CPU_BURST_UNIMPLEMENTED`.

### Watchdog and RTC

A single existing CLK32 source feeds the shared RTC/watchdog divider. RTCEN or watchdog EN keeps that divider running; REFREQ selects 32768 or 38400 cycles. Watchdog CNTR counts genuine divided ticks, expires at count binary `10`, supports high-byte/word service, EN/ISEL, W1C INTF, IRQ4 through IPR bit 3, and actual internal MCU/UART/CPU reset through the guest's reset vectors. RAM and time/day are retained. The independent USB device/peer is not assigned an invented MCU-reset wire. External electrical reset propagation is not accredited; NOR behavior beyond the existing boot path belongs to H3.

RTCIEN/RTCISR use defined mask `FF3F`; flags are W1C with correct byte lanes. The eight RTI taps produce 4, 8, 16, 32, 64, 128, 256 and 512 Hz at 32768 Hz XTAL. RTI uses IPR bit 22, separate from ordinary RTC bit 4 and watchdog bit 3. Alarm compares TOD/day; minute/hour/day rollover and stopwatch countdown are covered. The addendum's 16-bit STPWCH at `FFFFFB12` is respected. Reserved time bits are masked; out-of-range field values are accepted as the manual specifies, rather than rejected by host policy.

The host seeds power-on time once. Thereafter CLK32 owns counting: reading a register cannot advance time or generate events. Warm reset and save/restore retain the running time. Existing Palm calendar conversion/first-format behavior is preserved.

Resolved paths: `WATCHDOG_ENABLED_CLOCK_UNIMPLEMENTED`, `RTC_INTERRUPT_RATE_UNIMPLEMENTED`.

### Interrupts and GPIO

Existing IPR/IMR/ISR/ICR/ILCR and CPU-space IACK paths remain the implementation. Watchdog, RTC, RTI and KBD producers drive their documented source bits. Timer IRQEN now propagates a previously latched compare status. Level requests remain asserted while their producers are active; edge acknowledgment clears only the selected latch. A native simultaneous test observes Timer1 IRQ6, UART2 IRQ5 and RTI IRQ4 in that order with actual guest vectors.

GPIO input levels, output latches, directions and pulls are distinct. DATA writes while input-configured retain the latch; DATA reads observe pins. Reserved PDSEL[3:0] do not disable PD0–PD3 GPIO outputs. The existing ST/pen/SD/USB/UART wiring models are reused. Explicit external-drive/value fixtures are disconnected by default. An unbiased, undriven digital pad retains its last sample; this is a digital convention, **not a measured voltage or modeled analog capacitance**.

PCSEL selects GPIO versus the existing LCD controller. PCDATA observes configured external inputs, GPIO outputs or derived LCD signal/data states instead of blocking every access. PF2 CLKO derives from the shared clock graph. The existing 560×160 renderer and its 60 Hz host presentation are retained; this does not certify panel scan phase, analog bias or every alternate LCD bus mode.

Resolved path: `PCDATA_PIN_LEVEL_UNQUALIFIED` for the explicitly tested digital modes. Unknown board nets and untested alternate-pad waveforms remain **NO VERIFICADO**.

## Original-firmware boundary exposed by integration

The historical GPIO model returned zero input DATA latches. Correct pull/input reads exposed an implicit test-profile assumption: original UK1.5 repeatedly samples PD1/PD2 in `PrvSpiSetPol0` and PD0/PD3 in `PrvSpiSetPol1`. A high PD1 or PD0 keeps those loops running. Native traces showed PDDIR=`00`; an older atlas inference that PD0/PD1 were outputs cannot establish their board connections.

The canonical qualified UK1.5 diagnostic configuration now declares **PD0/PD1 LOW as explicit external stimuli**, alongside the existing explicit SDIRQ PD2/PD3 LOW and NOR diagnostic profiles. The CPU still reads the actual GPIO model and runs the unchanged firmware. This documents a bench condition previously hidden by latch reads; it does **not** identify sensors, pull resistors or PCB nets. Removing/changing that fixture can legitimately leave the ROM waiting. Establishing real board continuity remains a physical task.

Ghidra reused the existing `DanaPalmUK15Touch` project, `UK15_private.raw`, in `-readOnly -noanalysis` mode. Native call sites led to HwrDelay's PLLFSR polling, PrvSpiSetPol0/1, and the PCTLR idle routine. Exports remain private. No fresh ROM import, global reanalysis or copied GPL implementation was used.

## Native qualification and regressions

[Machine-readable release results](H2_NATIVE_RESULTS_20261101.json) contain artifact identities and measured outcomes.

- **29 H2 68000 cases PASS:** SYSCLK selectors and protected PLLFSR retune; independent CLK32 phase under repeated PLL changes; PCM widths 1/3/15/30/31; doze; all four PLL wake delays; all eight RTI rates; REFREQ; watchdog IRQ, service and true reset; calendar/alarm/stopwatch; GPIO direction/latches/LCD mux; pending timer IRQEN for both timers; simultaneous priorities; edge INT exclusion from PLL wake versus KBD level wake; edge INT wake from doze while SR still masks the ISR; two save/restore scenarios.
- The edge-doze regression demonstrably times out on the preceding H2 candidate and passes after the fix. The corrected test checks PCEN cleared and IPR pending **before** lowering SR, then observes the real ISR.
- **Nine UART/SIR regression cases PASS:** bidirectional backends for both UARTs, UART2 SIR, simultaneous UARTs, in-flight SIR restore, dynamic clocks and both IRQ paths. UART implementation remains byte-for-byte unchanged.
- **USB PASS:** HC printer, DC endpoint/IRQ/DMA, host faults, PTD/bus assertions, and unchanged original AlphaWord printing: 10409-byte complete PostScript, SHA-256 `792013e870ceeba0de25c1476b0132286befcca35da05478b2acfcb4dfd8e6b8`.
- **Original UK1.5/AlphaWord, 81/81 keys, five chords, pen calibration, modifier reconciliation, prolonged typing/reset, RTC/calendar, dual-SD write/CRC/protection/reopen, EmuTOS and sound controls PASS.** Original guest audio contains 6833 nonzero samples (peak 5978) in the 48 kHz capture. Existing PWM/audio and LCD implementations are retained.
- **Original Power PASS:** firmware enters real PCTLR=`80` doze at `1007976C`, before the old test's expected STOP PC. Physical Power changes the hardware input, clears PCEN and resumes firmware. The historical assertion now accepts and distinguishes genuine PCM doze from genuine STOP; it does not force either state.
- Real SDL/XTest keyboard delivery, reserved keys, MAME menu chord and F12 screenshot PASS. T's ordinary Wayland socket was disconnected; an existing GNOME software compositor ran with private D-Bus, runtime/config/data/cache and was terminated afterward. No host package installation or global display configuration change occurred. Tests require a save-state generated by the binary under test.
- The sole installed artifact is checked again after atomic replacement; detailed installed results are in the release JSON. The pre-H2 operative is retained compressed as private rollback evidence, not another installation.

Lua observes guest journals/registers and operates external physical-input fixtures. It does not patch CPU registers, RAM, MMIO, Palm traps or the ROM. Synthetic diagnostic programs themselves issue actual 68000 MMIO and vector operations.

## Reproduction in the canonical environment

Keep one MAME instance active at a time. Build with the existing `make` target and Clang21 configuration used by previous deliveries. Native diagnostics use `tests/h2_native.py --mode MODE --rate N --case UNIQUE`; add `--installed` for the sole operative. Modes/rates and receipts are listed in the release JSON.

For the complete original-ROM keyboard/system regression, including an isolated real SDL window when T has no active desktop:

```sh
python3 tests/run_keyboard_headless_campaign.py --prefix UNIQUE
```

Add `--installed` for the installed binary. For SDL-only qualification after an already completed campaign, use `--sdl-only --state /absolute/path/to/that-build/alphaword-clean.sta`. This reuses the existing GNOME/Xwayland/XTest programs; it installs nothing. The wrapper honors its scoped Wayland environment and cleans up its private process group.

Reuse `tests/serial_native.py`, `tests/run_isp1161_native.py`, `tests/run_isp1161_palm.py` and `tests/h2_palm_power.lua` as recorded in the release JSON. Source-extraction RTC/ST tests were adjusted for the shared CLK32 owner and companion implementation; they are supplemental, not substitutes for native execution.

## Sources and remaining boundaries

Primary authority: [Motorola MC68VZ328UM](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), clock/PCM chapter 4, interrupt chapter 9, GPIO chapter 10, RTC/watchdog chapter 11 and LCD/PWM register descriptions; manufacturer addendum Rev.7, October 2001. Reused references include MAME `mc68328.cpp` at `c4e48388ca620472643110db2941ce70aa5f3c07`, POSE VZ descriptions as reference only, and [dbztool initializer](https://github.com/davidgiven/dbztool/tree/d32702383c2ea3523ea58599c52345435c74e900).

Crystal tolerances, analog acquisition/jitter, power consumption, unbiased pad voltage, unmeasured board continuity, and full alternate-function electrical waveforms are not accredited. The 38.4 kHz fixture is not qualification of hot crystal replacement; Dana qualification uses 32768 Hz. Factory ICE/BAUDTEST modes retain their existing qualification boundaries. Same-build save/restore is qualified; old MAME save-state binary compatibility is not promised. LCD grayscale/physical audio queues and external NOR programming are not expanded here.

The same Drive master `DANA_EMU_Control_Rector_Auditoria.xlsx`, ID `1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l`, is updated in place with 14 sheets and prior history retained. H3 NOR Flash is the next priority and was **not started** in this intervention.
