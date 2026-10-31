# ISP1161A1 USB integration and native qualification — 2026-10-30

This delivery connects the existing single Dana ISP1161 model to explicit USB packet peers. **Original Palm UK1.5 AlphaWord printing is qualified. Device FIFO/packet/IRQ/DMA operation is qualified with a diagnostic 68000 guest. Original-Palm upstream enumeration and HotSync are pending. Integral chip acceptance remains OPEN.**

The canonical checkout is `/home/spc/Projects/alphasmart/DANA-emu`, branch `main`. The sole installed executable is `runtime/diag/bin/dana-diag`. No branch, clone, second installation, replacement ROM, or subordinate agent was used. The initial head was `0ff1551`; documentation-only commits `022fab7` and `eb118ca` arrived during development and are preserved, including the deferred LCD and audio queues.

## Installed artifact and evidence

- Clang 21.1.8 incremental compilation and link: PASS, using the existing `runtime/diag/source` build cache.
- Executable SHA-256: `34c0ddd062c15427b5485d7d99b1a9ab8b17da8873af51ed2d32cca000d7142b`.
- Driver SHA-256: `af5a5182a67a28b7b20e1b1aa295e7730ddfbbc09526828bccf2a7df5e9043b9`.
- Original private UK1.5 SHA-256, unchanged: `2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3`.
- Previous executable `db7404acb1b0ea44431d05e442dac231c1add2508bd1bcd217c35c2d628f5f3e` is preserved as a verified compressed rollback archive, not a second executable.
- [Machine-readable qualification manifest](evidence/usb-20261030/qualification.json) records candidate and installed results and source hashes. The implementation commit is the commit introducing this report; Git history supplies its exact ID.
- Private raw traces, firmware, RAM/framebuffer dumps, save-states, Ghidra outputs/projects, and rollback binary remain on T. Public evidence contains only bounded test summaries and test-document screenshots.

## Implementation

`alphasdana.cpp` retains the existing register banks, HC 4096-byte SRAM, DC 2462-byte SRAM, physical command/data ports and Philips PTD executor. The additional chip methods in `isp1161_dana.h`, packet/FIFO state in `isp1161_usb.h`, and MAME image transport in `isp1161_link.h` belong to that same driver instance. These headers are not another emulator or controller.

HC SETUP/IN/OUT now reaches explicitly attached peripherals. Control address/configuration changes commit on status ACK; DATA toggles, duplicates, short packets, ZLPs, NAK retry, STALL and documented completion errors update real PTDs. ATL and alternating ITL banks use the existing chip SRAM. LAST IN uploads may omit the incoming payload allocation, as the original Dana driver actually does; receive bounds remain the allocated bank capacity. Malformed PTDs signal UE and permit subsequent traffic instead of freezing the emulator.

Two logical root ports model connection/change, power, enable, reset, suspend/resume, overcurrent and full-speed attachment. Reset completion uses virtual time. Sustained overcurrent keeps power and enable cleared even when NPS is configured. Devices are absent by default.

The printer uses MAME's existing printer image device. Its virtual identity is explicitly a test peripheral, VID FFFF/PID 1161, with USB Printer class requests, descriptors, bulk OUT and status. Its bytes are accepted from guest USB packets and written to the selected printer image. It advertises PCL/PostScript capability but does not render or certify PDF output. A separately selected diagnostic function provides bulk, interrupt and isochronous loopback with bounded queues and deliberate packet faults.

The DC moves actual bytes through its original SRAM. Metadata tracks all 16 endpoint entries (EP0 OUT/IN plus 14 configurable entries), simple/double buffers, CPU/SIE bank ownership, length, toggle, halt, SETUP/F4, status/error records and endpoint events. SRAM allocation validates both total capacity and the non-ISO limit. Control toggles survive endpoint reallocation during a control request. Address activation follows the acknowledged status IN packet. USB bus reset preserves the MCU command/data phase, preventing a reset between C0 LOW and HIGH from corrupting the CPU transaction.

INT1 routes logically to VZ IRQ3/PD6 and INT2 to IRQ2/PD5, according to original ROM service installation and handlers. Polarity, level/pulse, pin mux/direction, masks, edge latch and acknowledgement are represented. This is ROM-supported logical routing, not measured PCB continuity. DREQ/DACK/EOT are exposed through the abstract packet link; no unverified VZ DMA connection is invented. DC DMA supports byte/word width, request/ack polarity, counters, short/ISO termination, buffer advancement and partial IN validation on explicit EOT.

Timer2 is a demonstrated USB dependency: original code at `10301D42` enables TCTL2, clears TPRER2, writes TCMP2=8189 and polls TCN2 during ATL upload. The first original-printer run blocked at `FFFFF612`. An independent Timer2 channel now reuses the existing Timer1 timing/IRQ design, with SYSCLK/prescaler, counter/compare/status and save-state. This is not a claim that all VZ capture/TIN electrical behavior is qualified. GPIO, SD, Flash, keyboard and LCD behavior was not changed for convenience.

## Complete command/register inventory and qualification boundary

Codes below are hexadecimal MCU commands; physical bus accesses remain 16-bit big-endian CPU words. Multiword registers transfer LOW before HIGH. USB FIFO bytes are packed low-byte first within the MCU word as documented by Philips.

| HC read / write | Width | Implemented meaning / boundary |
|---|---:|---|
| 00 / — | 32 | HcRevision 10 |
| 01 / 81 | 32 | HcControl; HC operational/suspend state starts/stops the 1-ms SOF scheduler |
| 02 / 82 | 32 | CommandStatus; HC reset independent of DC |
| 03 / 83 | 32 | InterruptStatus; W1C |
| 04 / 84, 05 / 85 | 32 | InterruptEnable / Disable; set/clear, MIE and OPR propagation |
| 06–0C | 32 bank | Reserved/unassigned compatibility storage; no OHCI HCCA/ED/TD engine is substituted |
| 0D / 8D | 32 | FrameInterval |
| 0E / — | 32 | FrameRemaining from the virtual SOF timer, including FIT |
| 0F / — | 32 | FrameNumber advances at SOF |
| 10 / 90, 11 / 91 | 32 | PeriodicStart and LSThreshold register storage; exact bandwidth arbitration/LS peripheral qualification is not claimed |
| 12 / 92, 13 / 93 | 32 | Root descriptors A/B; two ports and power policy |
| 14 / 94 | 32 | Root status and global port power operations |
| 15 / 95, 16 / 96 | 32 | Port status, W1C change flags, enable, reset, power, suspend/resume, overcurrent |
| 20 / A0 | 16 | Hardware configuration, INT1 and DMA pin configuration |
| 21 / A1 | 16 | HC DMA configuration / DREQ1 / FIFO selection |
| 22 / A2 | 16 | MCU transfer counter and FIFO cursor |
| 23 / A3 | 16 | Interrupt threshold register storage; threshold timing is not separately qualified |
| 24 / A4, 25 / A5 | 16 | MCU interrupt status W1C and enable mask 0077 |
| 27 / —, 28 / A8 | 16 | Chip ID 6123 and scratch |
| — / A9 | 16 | F6 software reset, independent of DC |
| 2A / AA, 2B / AB | 16 | ITL/ATL allocation, rejecting total above 4096 |
| 2C / AC | 16 | Buffer Full/Done state |
| 2D, 2E / — | 16 | ITL0 and ITL1 readback lengths |
| 40 / C0, 41 / C1 | FIFO | ITL and ATL PIO with latched bank selection |

| DC command | Width | Implemented meaning / side effect |
|---|---:|---|
| 20–2F / 30–3F | 16 | Write/read endpoint configuration; commit allocation at 2F |
| 01–0F | FIFO | IN packet length followed by payload |
| 10,12–1F | FIFO | OUT packet length followed by payload |
| 40–4F / 80–8F | command | Stall / unstall, FIFO/toggle reset on unstall |
| 50–5F | 16 | Endpoint status; clears that endpoint's interrupt |
| D0–DF | 16 | Status image without interrupt acknowledgement |
| 61–6F | command | Validate IN buffer and advance CPU bank when doubled |
| 70,72–7F | command | Clear OUT buffer and advance CPU bank when doubled |
| A0–AF | 16 | Last transaction error, RTOK, DATA01, UNREAD; read clears pending/unread metadata |
| B0 | 16 | AA37 unlock command accepted; suspend register write-protection is not modeled |
| B2 / B3 | 16 | Scratch, mask 1FFF |
| B4 / B5 | 16 | USB frame number / chip ID 6123 |
| B6 / B7 | 16 | Device enable/address readback; effective address deferred to status ACK |
| B8 / B9 | 16 | Mode mask 00AD: SoftConnect, INTENA, debug and DMA width; GOSUSP request tracked |
| BA / BB | 16 | Hardware configuration mask 7FFF; reset 2340; IRQ and DMA configuration |
| C0 | 32 | Interrupt snapshot LOW/HIGH; read-clear event subset, endpoint acknowledgement separate |
| C2 / C3 | 32 | Interrupt enables mask 00FFFF7F; enables gate event capture |
| F0 / F1 | 16 | DMA configuration mask C0FB |
| F2 / F3 | 16 | DMA counter/reload |
| F4 | command | Acknowledge SETUP before EP0 FIFO manipulation |
| F6 | command | Independent DC software reset |

Unsupported/unqualified command sequences retain deliberate diagnostic errors; this delivery does not replace the chip window with an unconditional write sink. Exact oscillator/LazyClock settling, suspend register protection, remote-wakeup electrical signalling, full USB bandwidth arbitration and physical low-speed peripheral coverage remain fidelity work. These limits are why this report does not close the entire manufacturer contract.

## Explicit transports and reproduction

Downstream printer: precreate an output file and add `-prin1 /absolute/job.prn` (or `-prin2`) to the existing Dana invocation. MAME exposes normal image mounting/unmounting. Diagnostic loopback and overcurrent inputs are explicit machine configuration choices, not automatic devices.

Upstream: mount `-usbcomputer /absolute/computer.usb`. That text image contains `socket.127.0.0.1:PORT`, pointing to an explicitly started local packet host. No public TCP listener, system service, physical USB capture, or kernel driver is installed. This transactional alternative reuses MAME OSD sockets. USB/IP/gadget concepts were investigated; T has no usable vhci_hcd/dummy_hcd/libcomposite route or installed Palm desktop/pilot-xfer stack. The link is not presented as a native USB/IP URB implementation.

DUSB v1 has a 16-byte little-endian header `<4s6BHI`: magic DUSB, version, opcode, address, endpoint, flags, handshake, length, sequence. Maximum payload is 1023. Replies echo sequence and set opcode bit 7. Packet flags select DATA toggle, ISO, speed and optional wire error outcome. DMA flags select the explicit physical DACK level; EOT selection is logical.

| Opcode | Operation |
|---|---|
| 01 / 02 / 03 | Explicit VBUS connect / disconnect / bus reset |
| 04 / 05 / 06 | SOF / suspend / resume |
| 07 / 08 / 09 | SETUP / OUT / IN, routed to the real DC SRAM/FIFO state |
| 10 / 11 | Read link metadata / start or stop the explicitly selected host SOF clock |
| 20 | Read logical and electrical DREQ1/2 and counters |
| 21 / 22 | DACK1 read / write word |
| 23 / 24 | DACK2 read / write configured byte or word |
| 25 | Explicit EOT for selected DMA channel(s) |

Connect flag 1 selects an automatic host SOF clock. With an attached, awake DC it advances in virtual 1-ms intervals; stopping it produces PSOF and suspension after three missing SOFs. Save-state preserves chip state but closes the external socket and clears VBUS: external host history cannot be rewound. Reconnection/remount is explicit.

Run from the canonical checkout, sequentially:

```sh
python3 tests/run_isp1161_native.py --installed --case NAME-bus --mode bus
python3 tests/run_isp1161_native.py --installed --case NAME-hc --mode host-printer
python3 tests/run_isp1161_native.py --installed --case NAME-itl --mode host-faults
python3 tests/run_isp1161_native.py --installed --case NAME-dc --mode device
python3 tests/run_isp1161_palm.py --installed --case NAME-print --mode printer
python3 tests/run_isp1161_palm.py --installed --case NAME-hotsync --mode device --require-original-device
python3 tests/run_keyboard_campaign.py --prefix NAME-regression
```

Use unique case names. The strict original-device command currently returns a pending/failure result, not an enumeration PASS. Diagnostic fixtures execute 68000 MMIO and PTD instructions in the authorized RAM-direct profile; they never patch or inject code into Palm. Original-Palm application runs use calibrated pen and ST keyboard input only.

## Native acceptance results

The evidence manifest is authoritative for final candidate and installed repetitions.

- Historical HC/DC physical bus interface: 33/33 PASS.
- Production packet/FIFO helpers: 88 checks PASS with Clang 21 and GCC ASan/UBSan; original PTD engine regression PASS. Clang's ASan runtime was unavailable, so GCC supplied the sanitizer run.
- HC: two explicit printers enumerated/configured by actual 68000 instructions, distinct output jobs, completion/IRQ state; sustained overcurrent, recovery, re-enumeration, explicit unplug and timeout.
- Interrupt/ITL: NAK retry, STALL, timeout, CRC, bitstuff, toggle and PID completion errors; malformed PID produces UE and subsequent transfers recover; six ISO packets exercise both ITL banks. HC save/restore and scratch preservation PASS.
- DC: actual CPU SETUP echo, EP0 DATA/STATUS, two independently consumed double buffers, concurrent HC transfers, independent resets, 8/16-bit DMA, wrong DACK polarity rejection, counter/partial-EOT payloads, suspend/resume, explicit disconnect/reconnect/bus reset, and a real IRQ2 handler reached through VZ IACK.
- General regression: original Palm boot/calibration/AlphaWord editing, ST 81/81 and 5/5 chords, modifier restore/repeat/reset, RTC/calendar, audio output and mute/restore, four SD persistence/protection/CRC cases, EmuTOS input, SDL keyboard/mouse and F12.
- Original AlphaWord: a fresh setup selects PostScript and USB in Print Setup, types `DANA USB 123`, invokes the original print action and receives **10409 bytes**, one page, with the phrase and `%%EOF`. SHA-256: `792013e870ceeba0de25c1476b0132286befcca35da05478b2acfcb4dfd8e6b8`. This is a complete received PostScript job, not a claimed rendered PDF.
- Original HotSync: the app opens and attempts connection, but the tested Cable path reports a connection problem before a DC SoftConnect/endpoint-configuration sequence is observed. Native original-device descriptors, SET_ADDRESS/SET_CONFIGURATION, endpoint traffic and a desktop synchronization session therefore remain **PENDING**. The diagnostic guest's echo/descriptors do not substitute for these requirements.

## Original firmware investigation

Ghidra 12.1.3 used the existing private full-ROM project, `68000:BE:32:default`, base 10000000, read-only/no-analysis import. The audit script creates temporary volatile MMIO blocks and follows actual instructions/calls. Palm A-line trap selectors are skipped correctly in fall-through; decompiler failures are retained instead of silently interpreted as evidence.

| Original address | Observed function/path |
|---|---|
| 103008B8 → 103020C6 | HC initialization installs the service at HwrIRQ3Handler |
| 10301D06, 1007CF1E/24/2A | HC INT1/MIE setup and VZ IRQ3 initialization |
| 10302258 | Root-hub change handling from the original HC ISR |
| 10301D42 | ATL upload and Timer2-based EOF timing |
| 1007CEF6 → 10081732 | HwrIRQ2Handler reads DC interrupt C0 LOW/HIGH |
| 100819E6 / 102DE0A4 | Resident/library endpoint allocation |
| 10081A7A / 102DE138 | Resident/library DC ConnectSetup |
| 100824FA / 102DEFFA | Original SETUP dispatch |
| 10082964 / 102DF2A2 | Original control transmit |
| 10082AA0 / 102DF362 | Original control receive |
| 102DFD86 | Library USB ISR dispatches EP0 and bulk endpoint completion |
| 102DD74E → 102DFAB8 | Original USB virtual-driver open and connect |
| 10081BE0 | Original PG3 reset pulse, identified in code; PCB net not measured |

Private decompiles are not redistributed. Linux ISP116x driver and QEMU USB core were used as conceptual references, not copied into BSD source. Their inspected blob IDs are recorded in the manifest. Linux's lack of ISO support is not treated as implementation evidence.

## Remaining acceptance and control status

The HC packet path and AlphaWord printer capability are functional. DC diagnostic packet/FIFO/IRQ/DMA capability is functional. **Neither result proves original-Palm USB Computer or HotSync.** The original firmware's USB port-selection/connection notification must be followed from the actual HotSync path; the tested UI path has not yet opened that driver. The precise board attach/VBUS notification and DMA continuity are not established by this work, and no fictitious GPIO event was added. A genuine desktop HotSync peer and original firmware data exchange must then be demonstrated.

The current contract and hardware audit retain an OPEN/PARTIAL integral state. Deferred LCD/audio work is preserved without implementation. The existing Drive workbook is updated in place, retaining its file ID, sheets and historical records; no second master workbook is created.

## HotSync simplificado: investigación posterior 2026-10-31

El [contrato HotSync MAME](DANA_HOTSYNC_SIMPLE_HOST_DESIGN_20261031.md) identifica el host original HotSync Manager y la alternativa abierta pilot-link, menú de instalación PRC/PDB y respaldo a carpeta, y prioriza la ruta original USB DC antes de construir la sesión DLP. **Investigación documentada, sin cambios de código ni nueva prueba HotSync.**
