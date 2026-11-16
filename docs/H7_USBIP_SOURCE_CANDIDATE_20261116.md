# H7 — USB Computer: guest-driven USB/IP bridge (source candidate)

**Status:** `SOURCE_READY / HOST_PROTOCOL_TESTS_PASS / DANA_NATIVE_PENDING / PC_ENUMERATION_NOT_ACCREDITED`.

**Baseline pinned:** `SamDelorean/DANA-emu main@322e021924bc3c5d22e3911d51a153957e12d861`; the only installed `runtime/diag/bin/dana-diag` remains SHA-256 `73550d0fc28c3189038e39fad2b5a4321dab59da8cfc416317fad18b875f4e41`. This delivery changes *no* MAME production source, executable, private firmware, installed runtime, existing test result or T workspace. The previous H6 release remains closed and unmodified. The earlier H7 host probe corrected its data-toggle flag from 4 (ISO) to 1 (DATA1); no earlier native result is inferred.

## Existing evidence and code reuse

- `src/mame/skeleton/isp1161_dana.h`: the actual ISP1161 device controller, EP0, FIFO, USB host packet and interrupt paths. DUSB packet `flags` bit 0 is DATA toggle, bit 2 is isochronous. Guest-controlled `DcMode B8` SoftConnect and VBUS are required; host may not force them.
- `tests/isp1161_virtual_host.py`: **reused directly** by `tools/h7_usbip_bridge.py`, so the native-qualified DUSB framing, USB acknowledgments and packet API are not reimplemented.
- `docs/ISP1161_USB_INTEGRATION_20261030.md`: original Palm USB host printer and synthetic diagnostic USB device pass; original Palm USB Computer enumeration was not shown.
- `docs/USB_COMPUTER_OS3K_PC_VALIDATION_20261031.md`: DUSB is a localhost packet socket, not an OS-enumerated USB device.
- AS3K reference: `SamDelorean/mame-as3k`, branch `as3k-mame0289-dev`, `src/mame/skeleton/as3k_usbip.inc` Git blob `fec6d33154569807b837cb1d0565dce18d500d42`, previous AS3K USB/IP URB acceptance. Protocol adaptation only; neither the AS3K PDIUSBD11D core nor its descriptors are transplanted into Dana.
- Linux Kernel documentation: <https://docs.kernel.org/usb/usbip_protocol.html>, network-byte-order OP_REQ_DEVLIST/IMPORT and CMD/RET_SUBMIT/UNLINK. USB/IP metadata *must* be derived from guest-supplied descriptors, never an invented VID/PID.
- Existing read-only Ghidra evidence: `docs/ISP1161_USB_INTEGRATION_20261030.md`, genuine Palm UK1.5 DC routines `0x10081732`, `0x10081A7A`, `0x10081BE0`, `0x100824FA`, `0x102DE138`, `0x102DFD86` and related library entrypoints. `tests/ghidra/DanaH7UsbComputerAudit.java` is included for bounded, read-only reinspection.

## Source implementation

`tools/h7_usbip_bridge.py` is a **host transport program**, not another MAME emulator, another USB device or new Palm firmware. It binds only two local loopback endpoints:

1. DUSB listener: existing `-usbcomputer` MAME image connects to the existing DUSB host as before. The bridge asserts external host VBUS and offers SOF; it cannot write ISP1161 device registers or claim a physical cable net.
2. The bridge **waits for firmware SoftConnect**, then performs DUSB reset and genuine EP0 `GET_DESCRIPTOR(Device 8 / Device 18 / Configuration 9 / Configuration full)` with proper DATA0/DATA1 sequence and status stage. It rejects incomplete/malformed/absent firmware replies. The USB/IP listener **does not open unless this succeeds**.
3. USB/IP localhost server publishes a device whose VID/PID/bcdDevice, class, interface and endpoint max-packet sizes come directly from guest EP0. Its busnum, busid and virtual path are clearly transport-local labels, not measured Dana PCB identities.
4. For USB/IP IMPORT, each submitted control/bulk/interrupt URB is mapped to genuine existing DUSB SETUP, IN, OUT, STATUS and endpoint packet transactions. USB status/SET_ADDRESS are acknowledged only after the real device status stage. Endpoint direction, DATA toggle, guest SRAM/FIFO and unresponsive NAK are preserved. Round-robin pending-URB dispatch prevents pending IN from starving other endpoints and serializes EP0. UNLINK drops pending work and generates RET_UNLINK without a late fabricated RET_SUBMIT.
5. Bounded queues, byte counts and timeouts are enforced; unsupported isochronous URBs are not silently accepted. The USB/IP server creates neither descriptors nor endpoint replies; a programmatic USB/IP client/protocol test is not operating-system enumeration.

`tools/h7_usb_dc_host_probe.py` is retained as a smaller DUSB-only isolation test. Its DATA toggle is fixed to DUSB bit 0; bit 2 is ISO.

## Local source-only evidence

Run from repository root:

```sh
python3 -m unittest discover -s tests -p 'test_h7_*.py' -v
python3 -m py_compile tools/h7_usbip_bridge.py tools/h7_usb_dc_host_probe.py
```

**14 host/protocol tests passed** in the isolated source checkout: framing, sequence validation, oversized payload rejection, no invented SoftConnect/device identity, USB/IP metadata from guest descriptors, DUSB bit-0 DATA1 not bit-2 ISO, SET_ADDRESS after status ACK, concurrent endpoint progress, bounded cancellation, partial TCP records, USB/IP DEVLIST/IMPORT and full network-wire `GET_DESCRIPTOR` on a simulated guest. Unit fixtures' fake VID `1234`/PID `5678` exist only inside tests and are **not used in production code**.

The Ghidra Java script has **not** been executed on the original program; the bridge has **not** been executed against MAME. This is `STATIC/PROTOCOL_PASS`, not `NATIVE_USB_PASS` or `PC_USB_ENUMERATION_PASS`.

## Physical and functional qualification remaining

- **Guest:** the genuine UK1.5 connection path must select USB Computer, activate `DcMode.B8.SoftConnect`, configure EP0 and answer real host descriptor requests. If the guest never asserts SoftConnect, the bridge must stop `BLOCKED` and Ghidra/CPU traces must identify the actual blocker; do not inject a synthesized B8 write.
- **Hardware:** ISP1161 D_VBUS, upstream D+/D-, INT2/IRQ2, RESET/PG3, connector and source-of-pullup continuity on real Dana remain **NO VERIFICADO** until measured. No modified board-net mapping is justified by source documents alone.
- **Host:** a Linux USB/IP client with actual VHCI support or a verified USB gadget/physical Dana setup must import and enumerate the device using guest-derived VID/PID and complete bidirectional control/data packets. The current T environment was previously reported without a usable VHCI/gadget path; do not install modules, change host network or claim OS enumeration before checking actual client capability.
- **Regressions:** HC original PostScript printing, DC previous diagnostic packet/FIFO/IRQ/DMA, H1–H6 peripheral behavior. No broad rebuild/retest of completed unrelated gates.

## Controlled native execution — deferred

No new T/Commander authorization has been supplied; H6's 20/20 calls are consumed. The single `dana-diag` in `runtime/diag/bin/dana-diag` is the only emulator permitted. After explicit new authorization: compare canonical source/installed SHA with published baseline, run bounded original-guest connect observation and the bridge against genuine ISP1161; report first causal blocker, patch only when source+CPU trace warrant; qualify host enumeration on available PC transport; install only after native pass; preserve H6 binary as rollback. Update the existing three Drive masters in place, retaining formula count and history. No second MAME binary, branches, alternate driver, SDIO, Wi-Fi module, HotSync/DLP or NEO Manager.
