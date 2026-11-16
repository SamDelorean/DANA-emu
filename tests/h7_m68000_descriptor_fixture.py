#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Bounded H7 *diagnostic* M68000 guest using the established ISP1161 USBCode.

Only this guest generates test descriptors; the host bridge never does. It is
NOT original Dana firmware and its VID/PID are not original Dana identity.
"""
from isp1161_native_fixtures import USBCode, DC

DEVICE = bytes.fromhex('12 01 00 02 ff 00 00 08 34 12 78 56 00 01 01 02 03 01')
CONFIG = bytes.fromhex(
    '09 02 20 00 01 01 00 80 32 '
    '09 04 00 00 02 ff 01 02 00 '
    '07 05 81 02 20 00 00 '
    '07 05 02 02 20 00 00'
)


def send_chunk(c: USBCode, chunk: bytes):
    assert 0 <= len(chunk) <= 8
    c.dw(0x01, len(chunk))
    for i in range(0, len(chunk), 2):
        low = chunk[i]
        high = chunk[i + 1] if i + 1 < len(chunk) else 0
        c.move_w(low | (high << 8), DC)
    c.dw(0x61)
    c.wait(lambda: c.dr(0xc0, True), 0x200, 0x200)
    c.dr(0x51)   # Endpoint IN status read clears EPI interrupt


def control_in(c: USBCode, response: bytes, requested: int, phase: int):
    assert requested > 0
    c.stage(phase)
    c.wait(lambda: c.dr(0xc0, True), 0x100, 0x100)
    c.dr(0x50)   # EP0 OUT SETUP status, clear event
    c.move_w(0x10, DC + 2)
    c.read(DC)
    c.expect(8)  # Actual 8-byte SETUP from USB/IP/bridge host
    for i in range(4):
        c.read(DC)
    c.dw(0xf4)   # acknowledge SETUP command
    c.dw(0x70)   # clear/setup OUT buffer
    data = response[:requested]
    for i in range(0, len(data), 8):
        send_chunk(c, data[i:i + 8])
    # The host sends a real zero-length status OUT packet.
    c.wait(lambda: c.dr(0xc0, True), 0x100, 0x100)
    c.dr(0x50)
    c.dw(0x70)


def fixture():
    c = USBCode()
    c.stage(0x700)
    c.setup_vz()
    c.dw(0xf6)
    # Reuse the previously qualified DC+HC silicon initialization path.
    c.hw(0x29,0xf6)
    c.hw(0x12,0x202,True)
    c.hw(0x2a,0x100)
    c.hw(0x2b,0x800)
    c.hw(0x20,0x1009)
    c.hw(0x25,0x13)
    c.hw(4,0x80000040,True)
    c.hw(1,0x80,True)
    c.dw(0xba, 0x0f0c)
    c.dw(0xc2, 0xffff)
    c.move_w(0x00ff, DC)
    c.configure_dc()
    c.dw(0xb6, 0x80)
    c.dw(0xb8, 0x89)  # CPU programs DcMode SoftConnect, unlike an injected host bit
    c.wait(lambda: c.dr(0xc0, True), 1, 1)
    c.configure_dc()  # bus reset reinitializes the existing endpoint RAM map
    for idx, (desc, requested) in enumerate(
            [(DEVICE, 8), (DEVICE, 18), (CONFIG, 9), (CONFIG, len(CONFIG))]):
        control_in(c, desc, requested, 0x710 + idx)
    # USB/IP IMPORT triggers a second bus reset, not a new fake device.
    c.stage(0x720)
    c.wait(lambda: c.dr(0xc0, True), 1, 1)
    c.configure_dc()
    control_in(c, DEVICE, 8, 0x721)
    c.stage(0x72f)
    return c.finish()


if __name__ == '__main__':
    import sys
    from pathlib import Path
    path = Path(sys.argv[1])
    assert not path.exists(), 'Refuse overwrite'
    image = fixture()
    path.write_bytes(image)
    print('H7_M68000_DESCRIPTOR_GUEST_BYTES', len(image))
