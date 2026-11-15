# H5 — PWM audio and identified power signals, 2026-11-15

## Result and continuity

**PASS for the demonstrated digital H5 scope.** The single installed `runtime/diag/bin/dana-diag` implements and natively verifies PWM1 REPEAT/FIFO/counter/IRQ/clock/recovery and the UK1.5-identified raw power signals. Physical analog and board-level properties remain explicitly **NO VERIFICADO**. No H6 work was started.

H4 was first verified closed and published: `main` and GitHub both pointed to `d49a5b1237916d1347ea15ba212e7fd33d25fdf7`, the tree was clean, and the installed H4 executable SHA-256 was `cf25eaafa08201862bd07f7cd3a7af64844f9a79ed6cecca39ddc676336c51a0`. The canonical T repository, existing compiler/cache, one runtime and one branch were reused. No additional emulator installation, clone, branch, worktree, tool installation or ROM modification was made.

Final installed executable SHA-256:

`6081b48e671cd677a09f3033eb2131a3cfaad8638e3d9ab742c56bf57da6e480`

Driver `alphasdana.cpp`: `760a45a012ee9361d182530155909fa19b2da84e12c54aba76e4037742302e07`.

PWM helper `alphasdana_pwm.h`: `74ef677d4efeaabdde76b30734b5d81573e85dde928001bb57ff1d7a3edfe02c`.

The native receipts, journals, build identity, regression results and Drive readback are in [H5_NATIVE_RESULTS_20261115.json](H5_NATIVE_RESULTS_20261115.json). Private ROM, Ghidra exports, recordings and original print output remain on T.

## PWM1 implementation

The existing controller state, two PWM timers, MAME mono speaker, H2 clock graph and interrupt controller are reused. `alphasdana_pwm.h` is an implementation include for the same driver, not a second audio device or controller. PWM1 MMIO is now shared by physical and R-direct boot profiles. H1/H3/H4 controllers are unchanged; H2 changes are limited to the PWM clock callback and PB7 pin multiplexing.

| Function | Implemented behavior and evidence |
| --- | --- |
| PWMC1 REPEAT | Write-only bits select 1/2/4/8 periods per FIFO sample. Readback clears the write-only fields. Remaining repeats are saved. All five sample widths and repetition counts are checked through CPU pad reads. |
| PWMS1 FIFO | Five bytes, packed word high then low; single byte uses the odd SAMPLE1 address. An even-only write is ignored. Full FIFO ignores writes; with one slot left only the packed high byte enters. FIFOAV is derived from capacity. |
| Underflow/refill | Empty FIFO continues the last real sample; refill is consumed at a period boundary. No host-generated replacement tone or synthetic Palm event. |
| Period and duty | PWMP1 plus two source ticks, with `FF` aliasing `FE` to 256 counter steps. Final strict measurement is 512 CLK32 ticks for both encodings, not the previous 514. Zero and full duty and intermediate widths are observed on PB7. |
| Counter and live writes | PWMCNT1 reflects elapsed source cycles; writes to its read-only byte have no effect. Running control/period changes preserve phase. A newly lowered comparator behind the count waits for wrap. IRQ/control writes do not restart every pulse. |
| IRQ | Real PWM source bit 7, existing mask/priority/vector/IACK path. Threshold, refill, read acknowledgement, software post/clear and disabled high-byte lane preservation are tested. Timer1 and PWM can share level 6 without clearing each other's producer. |
| Clock and suspension | Existing H2 source-cycle retiming covers SYSCLK and the independent CLK32 source. SYSCLK stop freezes the current digital level/counter; CLK32 playback continues. PLL frequency changes preserve phase. |
| Disable/reset/restore | Disable flushes FIFO and drives the existing output low; watchdog reset and active-audio save/load are checked. FIFO/repeat/sample/timer phase and pin state are restored, without fabricated recovery pulses. |

MC68VZ328UM chapter 15 and the manufacturer's addenda govern these behaviors. Existing MAME scheduling/speaker mechanics were reused; older/EZ-family counter assumptions were not substituted for the VZ manual.

## PWM2 and physical audio boundary

The VZ does contain PWM2: a separate 16-bit channel at `0xFFFFF510–0xFFFFF517`, without the PWM1 FIFO. PCR can select PWM1, PWM2 or logical combinations onto PWMO1. The PWM1 pad function is PB7/PWMO1; PWM2's independent pad function is PM5/PWMO2. None of those silicon facts establishes Dana board routing, an amplifier, stereo or a second physical speaker.

The existing atlas identifies `U_SOUND` without a qualified output-stage model or complete continuity. The original `HwrResetPWM` routine at `0x10079FCE` addresses PWM1. The already accredited Palm audio path and this campaign use PWM1 mono. No additional physical PWM2 audio path was found in that evidence. PWM2 routing/use outside that observed path and the PCR combined modes remain **NO VERIFICADO** and unqualified; no speculative second channel was enabled. A stereo/second physical speaker feature is **NO APLICA to the accredited mono path**. This is not a claim that PWM2 is absent from the silicon or conclusively disconnected on the board.

PB7 digital output is testable through the existing GPIO mux. PB7-to-speaker continuity, filtering, amplification, impedance, acoustic response and electrical tolerances remain **NO VERIFICADO**. The existing speaker representation is retained without claiming those analog properties.

## Power/battery protocol correction and firmware evidence

Targeted read-only/no-analysis queries reused the existing `DanaPalmUK15Touch` project and its original UK1.5 program. The project was not reimported or globally reanalysed; bounded leaf ADC listing corrections were discarded after extraction. Technical conclusions are recorded here; private disassemblies/decompiler exports stay on T.

| Original routine | Observed digital behavior |
| --- | --- |
| `HwrBatMasterRead`, `0x1007B54E` | Drives/releases PG1, polls PGDATA at `0x1007B618` for up to 1,100 iterations and writes classification 0 or 4. Calls the original ADC path and stores the resulting raw battery sample. |
| `PrvFilteredBurrBrownRead`, `0x1007B31E` | Reads three samples and selects a stable pair, using the firmware's own filtering. |
| ADC leaf, `0x1007B0BC` | PG2 selection and real SPI2 command/data exchange: 7 command clocks, one final command clock, 16 data clocks. At `0x1007B172`, CPU reads SPIDATA2, shifts right three and masks 12 bits. |
| `PrvBatteryCmdMainRead`, `0x1007C842` | Uses command A4 and the firmware's own calibration/arithmetic. |
| `PrvBatteryCmdAlkDetectRead`, `0x1007C8C2` | Uses E4; no host voltage conversion is invented. |
| `PrvHWChargeStatus/On/Off`, `0x1007BC22/BC4A/BC68` | Reads PJ6 direction; charge-on releases the pin and charge-off drives low via the existing direction/data registers. |
| `HwrDockStatus/HwrPluggedIn`, `0x1007CCEC/CD1E` | Uses firmware state; it is not mapped to a guessed external AC pin. |

This exposed two real driver errors: A4/E4 had been treated as pen coordinates, and input PG1 had mirrored pen contact. H5 separates those power inputs from PEN and leaves the established X/Y digitizer commands unchanged.

The three bench inputs are configurable in the existing driver:

* `POWER_PG1`: raw digital low/high level, only when GPIO-selected as an input. Output mode still follows the existing latch/direction rules.
* `POWER_ADC_A4`, `POWER_ADC_E4`: raw 12-bit sample codes consumed by the existing SPI2 framing. They work with pen up or down; pending sample state uses existing serialization/save-state.

Default PG1 high and ADC `FFF` preserve the former undriven reference behavior. `FFF` means raw saturation, **not a measured full battery**. No percentage, voltage, chemistry, discharge curve, charger circuit, AC net or RC delay is fabricated. External input settings remain external stimuli; saved internal in-flight ADC and GPIO state retains its normal behavior.

The original unchanged firmware was then run from cold physical reset four times: PG1 low/high on the candidate and on the installed binary. At runtime the raw A4 stimulus changed from 1536 to 2048 and E4 from 3072 to 4095. Real firmware SPI reads consumed both sets, its battery buffer received 1536 and 2048, it classified low PG1 as 4 and high PG1 as 0, and it wrote the PJ6 charge control. No guest memory/PC/register patch or Palm trap hook was used. A separate native case asserts the pen interrupt and proves that touching the pen does not alter the power inputs.

## Native tests, regression and installation

All functional assertions use actual 68000 instructions inside the existing `dana-diag`. Guest code writes MMIO/FIFO/RAM, reads PB7/PWMCNT1/SPI2/GPIO, uses CLK32 Timer1 for pulse timing and executes interrupt handlers through CPU-space IACK. Lua observes journals and real bus transactions; it only drives documented external inputs or requests MAME save/load. Read-only diagnostic outputs and WAV data supplement those CPU measurements; they are not the sole PASS criterion.

The **22 unique H5 scenarios all PASS on the final installed executable**, after passing on the identical candidate:

`repeat0 repeat1 repeat2 repeat3 period-ff counter duty0 duty100 irq irq-control mixed clock clock32 sleep sleep32 save reset adc7 adc8 adc-pen power-low power-high`.

The strict FF/FE alias proof was additionally rerun with a 511–513 CLK32-tick bound and measured 512 for both. Nonzero-duty cases produce real MAME PCM/WAV; silence for zero duty/disabled channels is expected. Active-audio save/load repeats the guest checks after restoration; watchdog reset verifies flush and reset state.

The candidate regression campaign completed **38 harness/check invocations**, including composite campaigns. These are not claimed as 38 independent native CPU scenarios. Installed repetition completed **37 invocations plus a fresh-state SDL session**. The reused affected-path coverage includes:

* Original UK1.5 cold boot, AlphaWord, keyboard 81/81 and five chords, stylus, RTC/calendar, volume/mute and real audio.
* Dual SD write/reopen, CRC and protection; EmuTOS execution and keyboard.
* H4: nine targeted LCD cases covering 1/2/4 bpp, dynamic depth, clock, sleep/save, restore, cursor and contrast output.
* H2: nine clock/PCM/sleep/doze/mixed-IRQ/watchdog/calendar/GPIO/save cases.
* H3: fourteen 4/8 MiB NOR programming/erase/protection/persistence/reopen/save/watchdog cases, exclusively on disposable seed images.
* UART1/UART2 dual transport, IrDA SIR, active SIR save and PLL change; USB host printer/device/fault/PTD bus; original AlphaWord USB print.
* Original Power suspension/wake, the existing cursor contract and SDL/XTest/F12 presentation. Installed SDL uses a state created by this same build, not a historical incompatible state.

Clang 21.1.8 incremental compile and link returned 0 using the existing build tree. Candidate regressions passed before installation. A private non-executable compressed rollback copy preserves the previous installed H4 bytes; the verified candidate was atomically installed into the sole runtime path. The source-cache files match canonical sources byte for byte. Installed native and affected-path regressions passed afterward.

Original UK1.5 remains 6,094,848 bytes, SHA-256 `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`. No physical equipment or host configuration was changed. Temporary compositor resources were cleaned up by the existing harness.

## Documentation and Drive

The existing `DANA_EMU_Control_Rector_Auditoria.xlsx`, ID `1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l`, is updated in place. Its **14 sheets and all 1,020 formulas** are preserved, together with prior cell values outside the explicit change plan, styles, validations, dimensions, variant matrix and historical rows. H5 appends `BITACORA!56`, `FUENTES!49` and `CAMPAÑAS!35`; current PWM/power audit rows and AUDIO-HW entries reference this verified scope. Upload was downloaded again and compared byte for byte; see [H5_DRIVE_READBACK_20261115.json](H5_DRIVE_READBACK_20261115.json) and [H5_MASTER_VERIFICATION_20261115.json](H5_MASTER_VERIFICATION_20261115.json).

The atlas was consulted, and its repository reference now distinguishes MCU pin-function evidence from measured board nets. No new physical continuity is claimed and no replacement atlas or master book is created. Historical H1–H4 reports remain intact.

## Final scope classification

| Status | Scope |
| --- | --- |
| **PASS** | PWM1 digital behavior, real mono output, source clocks/recovery/save-state; PG1 and SPI2 raw A4/E4 protocol; original UK1.5 response and charge-GPIO writes; affected H1–H4 regressions and installation. |
| **NO VERIFICADO** | Analog audio/power transfer, amplifier/filter, speaker net, PWM2 board routing/use, battery voltage reference/capacity/chemistry, charger/AC circuitry, RC characteristics and unmeasured PCB continuity. |
| **NO APLICA** | An asserted stereo/second physical audio channel for the accredited mono path; a host-invented battery percentage or discharge curve without evidence. |

H5 is closed within the demonstrable digital hardware scope. Development stops here. **Do not start H6.**
