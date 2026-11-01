# Dana UART1, UART2 and IrDA integration — 2026-11-01

The canonical Dana VZ model now implements timed UART1/UART2 transmit and
receive, their different FIFOs, errors, flow control, interrupt sources and
SIR encoding/decoding. Data crosses an independently configured MAME serial
peer and a mounted host byte stream. UART2 now reaches the CPU at the level
selected by ILCR[10:8]. This replaces the UART1 log-only transmitter and the
UART2 register bank that blocked real transmission.

**Acceptance:** native operational NRZ/SIR transport is qualified. This is
not a claim of completed Palm Beam file transfer, measured PCB continuity,
optical/electrical accuracy or manufacturer factory-test qualification.

## Release measurements

- 24/24 release native cases passed; seven installed-binary checks passed.
- The installed full Palm/keyboard/SD/EmuTOS/RTC/sound/SDL campaign passed,
  including 81 physical keys and five modifier chords.
- Installed USB HC/DC regression passed. Original AlphaWord USB printing
  produced a complete 10,409-byte PostScript job, SHA-256
  `792013e870ceeba0de25c1476b0132286befcca35da05478b2acfcb4dfd8e6b8`.
- Original Palm emitted 112 XID frames with valid FCS in the bounded
  single-response run. All **44 returned wire bytes** were read exactly by
  its UART2 driver, with **zero character errors**. Its UI did not accept a
  receiving handheld; no file transfer is claimed.
- Installed executable SHA-256:
  `f1002968c67dd2f6ebaf9ae107f6f120321986b94fb495eb4b9826414d36cdcc`.
- Driver SHA-256:
  `6876e1181a07528168603dc7c4b5db7f972d8518d7c710642b6fa61ebcdab28c`.
- UART header SHA-256:
  `bf9eddcc21c359f1b7735b5739bc97de5dbfd6769a328755a4321d5cf2585803`.
- The previous operative was archived as private gzip with its original
  digest verified; the build artifact was atomically moved to the sole
  installed path and no parallel executable remains.

## Canonical environment and provenance

- T: `spc-HP-t640-Thin-Client`.
- Repository: `/home/spc/Projects/alphasmart/DANA-emu`, `main`.
- Starting commit: `d4ae5e6`.
- Sole installed emulator: `runtime/diag/bin/dana-diag`.
- Incremental build: existing `runtime/diag/source`, Clang 21.1.8; no new
  checkout, branch, environment, compiler or emulator installation.
- Original UK1.5 image: 6,094,848 bytes, SHA-256
  `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.
  The image was neither patched nor reconstructed. ROM, raw screen captures,
  save states and Ghidra output stay in private local evidence.

Exact release source/binary digests, native case results, installation and
regression results are in [the qualification record](UART_IRDA_NATIVE_20261101.json).

## Implementation contract

`dana_vz_uart.h` contains a common VZ UART device, a pin-level NRZ/SIR codec
and an independent virtual serial peer. The existing `alphasdana_state`
retains the VZ memory map, CPU, GPIO, clocks and interrupt controller.

| Property | UART1 | UART2 |
| --- | --- | --- |
| Registers | `FFFFF900–FFFFF90B` | `FFFFF910–FFFFF91D` |
| RX/TX FIFO capacity | 12 / 8 bytes | 64 / 64 bytes |
| RX half threshold | 8 occupied slots | 4 × HMARK RX nibble; zero disables |
| TX half threshold | fewer than 4 occupied slots | 4 × HMARK TX nibble free slots; zero disables |
| UART interrupt source | IPR bit 2, CPU level 4 | IPR bit 12, ILCR[10:8] |
| Peripheral pins | PE4 RX, PE5 TX, PE6 RTS, PE7 CTS | PJ4 RX, PJ5 TX, PJ6 RTS, PJ7 CTS |
| Virtual peer default | NRZ, 9600 8N1 | optical SIR, 9600 8N1 |

UTX FIFO status bits remain low at reset while UEN=0; CTS reports its actual pin level.

Word and byte accesses use the existing 68000 big-endian lanes. Reading the
URX high byte observes status without removing data; reading the low byte or
word removes one character. Character parity, framing, break and overrun
status accompany that character. A full receiver overwrites the oldest
queued character and marks the new valid character with OVRUN. Writes to a
full TX FIFO are ignored. RX disable flushes RX; TX disable flushes queued
data while the shifting character finishes.

The transmitter supports 7/8 data bits, even/odd/no parity, one/two stop
bits, forced parity errors and NRZ BREAK. CTS is active low and controls the
next character; NOCTS bypasses it. RTS supports software control and FIFO
control, including UART2's RTS2TRIG selection. OLD DATA uses 30 virtual bit
times, with its own interrupt enable. RX/TX status sources and CTS DELTA
remain level conditions until the peripheral condition clears. VZ ISR
writes do not acknowledge away UART FIFO conditions.

UBAUD integer division uses `65 - PRESCALER`, DIVIDE and the 16x/1x mode.
NIPR supplies the noninteger source, including UART2 SELECT=7 divide-by-one.
SIR zero bits become timed pulses; the receiver expands qualified pulses
before the MAME framing shifter. NIPR controls pulse width independently
of the integer baud divisor. TX/RX polarity, internal NRZ loopback, IRDA
loopback and IRTEST TX visibility are separate paths. The nominal 1.63 µs
minimum pulse is represented by `3 / 1,843,200` seconds, preserving the
valid UK1.5 NIPR=`0320` pulse at the actual VZ clock.

Virtual bit clocks preserve shift-register contents when SYSCLK/UCLK stops
or changes. Asynchronous RX samples at bit centers; CLKM=1 samples clock
edges. PE3 muxing disconnects UCLK in GPIO mode. A disconnected external
clock holds pending transmission until the input reconnects. PCR bit 4
selects the UART output clock at PE3; its unrelated PWM/timer combinations
remain explicitly unsupported. PCM preserves peripheral SYSCLK; physical
PLL sleep stops UART SYSCLK and wake restores it through the existing PLL
wake path.

FIFO contents, character errors, register state, fractional clock phases,
SIR pulse/expansion timers and in-flight shifts participate in save states.
Restoring a state detaches mounted host streams: external TCP/file history
cannot be rewound. The guest's UART state is retained and the cable can be
attached again explicitly. Existing pre-integration states have a different
MAME device graph and are not promised compatible.

## Reused components and licensing

Reuse is from the pinned BSD-3-Clause MAME implementation at
`c4e48388ca620472643110db2941ce70aa5f3c07`:

- `device_serial_interface`: bit framing, parity and shift registers.
- `bitbanger_device`: mounted file/socket byte transport.
- Existing MAME device, timer, save-state and CPU interrupt infrastructure.

The VZ-specific FIFOs, register/IRQ semantics, clock control and SIR adapter
are implemented here. MAME's `mc68328.cpp` UART methods and its null-modem
device were examined; the former are register stubs rather than a complete
VZ UART core. POSE/Retro68 GPL sources were reference material only; no GPL
UART implementation was copied into the BSD driver. Source pins are
recorded in `research/sources.lock.json`.

Primary specifications are Motorola MC68VZ328UM chapter 14, chapters 4,
5, 9 and 10, and **MC68VZ328UMAD Rev. 7, October 2001, §1.8**:

- [Manufacturer manual](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf).
- [Manufacturer addendum](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf).

The addendum governs UBAUD reset `0002`, read-only UTX BUSY/CTS status,
UMISC2 RTS2TRIG bit 8 and UART2 NIPR SELECT=7. Linux register definitions
and the uncorrected manual are not substituted for those corrections.

## Original firmware and board evidence

Original native execution entered UART2's driver at `102E00C8`, programmed
ILCR's UART2 field to level 4, configured baud at `102E0512`, enabled
IRDAEN at `102E0292` and wrote NIPR2=`0320` at `102E029C`. Ghidra was
used read-only on the existing UK1.5 project to corroborate the instructions
and calls; `tests/ghidra/DanaSerialAudit.java` records the method.

Thus **UART2 is the firmware-selected Dana infrared channel**. Tests of
UART1's silicon SIR capability do not assert a second physical IR port.
The atlas photographs identify the MC68VZ328PV CPU package but do not
establish transceiver part number, shutdown wiring, pin-to-pad continuity,
analog pulse response or optical performance. The virtual optical connector
models normal transmitter/receiver polarity; it is not a measured PCB net.

## Reproducible execution

The native package generator reuses `tests/d7_5_native.py::Code`; it emits
actual 68000 instructions for the existing diagnostic RAM loader. The Lua
observer reads results, controls physical peer/CTS inputs and requests MAME
save/reset operations. It does not write UART MMIO, guest RAM, CPU PC or
Palm traps. This diagnostic guest is distinct from the unchanged Palm ROM.

```sh
python3 tests/serial_native.py --installed --mode backend --uart 1 --case review-uart1
python3 tests/serial_native.py --installed --mode irda --uart 2 --case review-sir2
python3 tests/serial_native.py --installed --mode dual --uart 1 --case review-both-irqs
python3 tests/serial_native.py --installed --mode saveir --uart 2 --case review-sir-state
python3 tests/serial_palm_discovery.py --installed --case review-palm-sir
```

Additional native modes are `loop`, `deep`, `clock`, `flow`, `irq`,
`irtest`, `save`, `reset` and `rts`. Use a fresh case name for each run.
The release matrix includes both UARTs, both IRQs together, UART2 ILCR
levels 1–6, FIFO overflow/full writes, parity/framing/break errors, CTS
release, RTS thresholds, shared UCLK disconnect/reconnect during a frame,
reset and restoration of NRZ/SIR transmission in flight. Host round trips
include `00`, `55`, `AA`, `FF` and the channel-specific test text.

The standard MAME image names are `bitbanger1`/`bitb1` and
`bitbanger2`/`bitb2`; Lua device tags are `:serial0:stream` and
`:serial1:stream`. Mount an explicitly chosen file or
`socket.127.0.0.1:PORT`. A socket peer must already be listening. Peer
baud, framing, physical NRZ/SIR link and CTS/RTS controls are MAME input
configuration fields under `:serial0`/`:serial1`. They are independent
of guest settings, so a baud/parity mismatch remains observable. No host
port is opened by default. PTY termios, physical RS-232 electrical levels
and a physical optical adapter are not qualified by the socket tests.

## Qualification boundaries

The authentic AlphaWord workflow names a document and selects **Beam Doc**
using the physical ST keyboard and pen. Outgoing IrLAP XID frames traverse
UART2 and the SIR peer with valid FCS. An independent discovery-only peer
returns an XID response, and the original firmware reads the returned
bytes from URX2. The screen ultimately reports that no receiving handheld
was found. **Peer discovery acceptance, IrLAP session establishment and
OBEX document delivery are not PASS.** The test peer intentionally does
not implement a complete receiving Palm/OBEX stack; no successful result
is inserted into the guest. The JSON distinguishes transport evidence
from application acceptance.

Factory BAUDTEST's undocumented nibble-counter waveform is not reproduced;
that setting inhibits the normal clock path. BAUDRESET holds baud counters
reset. Manufacturing-test waveform fidelity requires additional silicon
evidence. Physical transceiver timing/continuity and a complete external
Palm Beam partner remain separate qualification boundaries. No new CPU
block or missing ordinary UART register was observed in the tested path.

Related regressions cover original Palm boot/AlphaWord, keyboard and SDL
input, stylus/LCD, RTC, timers, SD/SPI1, EmuTOS, sound controls, sleep/wake,
USB HC/DC and original USB printing. Two historical source-extraction
tests (`pwm1_uk15_test.py` and `pd7_irq6_external_input_test.py`) have stale
stubs/assertions against unchanged baseline methods; they are not counted
as passing tests. Native sound/power regressions provide the relevant
execution checks. Compiler temporary files use the existing project work
directory because the system temporary directory has a quota limit.

The existing control workbook is
`1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l`; its UART1, UART2 and IrDA rows and
append-only history record this delivery. The hardware atlas remains clear
that software routing evidence is not PCB continuity measurement. USB
Computer/HotSync, OS3K/NEO work and the LCD/audio queues are unaffected.
