#!/usr/bin/env python3
"""H7 bounded DUSB host probe for the existing Dana ISP1161 DC.

No emulated descriptors, VID/PID, USB/IP server, network listener beyond
127.0.0.1, ROM patch or guest register writes. Guest firmware must activate
SoftConnect. Use only with the one authorized dana-diag instance.
"""
from __future__ import annotations
import argparse
import json
import socket
import struct
import sys
import time

HEADER = struct.Struct('<4s6BHI')
MAGIC = b'DUSB'
VERSION = 1
ACK, NAK, STALL, TIMEOUT = 0, 1, 2, 3
IN_OPS = {9, 0x10, 0x20, 0x21, 0x23}
OUT_OPS = {7, 8, 0x22, 0x24}
MAX_PAYLOAD = 1023

class UsbProbeError(Exception):
    pass

class UsbTransport:
    def __init__(self, sock: socket.socket):
        self.sock = sock
        self.serial = 0

    def exact(self, n: int) -> bytes:
        result = bytearray()
        while len(result) < n:
            chunk = self.sock.recv(n - len(result))
            if not chunk:
                raise UsbProbeError('DUSB host peer disconnected')
            result.extend(chunk)
        return bytes(result)

    def exchange(self, op: int, address: int = 0, endpoint: int = 0,
                 flags: int = 0, payload: bytes = b'', length: int = 0):
        if not 0 <= length <= MAX_PAYLOAD or len(payload) > MAX_PAYLOAD:
            raise ValueError('DUSB length exceeds 1023')
        if op in OUT_OPS:
            length = len(payload)
        elif payload:
            raise ValueError('Only OUT/SETUP transactions may carry payload')
        self.serial += 1
        sequence = self.serial
        self.sock.sendall(HEADER.pack(MAGIC, VERSION, op, address, endpoint,
                                      flags, 0, length, sequence) + payload)
        magic, version, reply_op, addr, ep, _flags, status, n, seq = HEADER.unpack(self.exact(HEADER.size))
        if (magic, version, reply_op, addr, ep, seq) != (MAGIC, VERSION, op | 0x80, address, endpoint, sequence):
            raise UsbProbeError('DUSB response header mismatch')
        if n > MAX_PAYLOAD:
            raise UsbProbeError('Invalid DUSB reply length')
        data = self.exact(n) if op in IN_OPS and status == ACK else b''
        return status, data

    def retry(self, op: int, deadline: float, **kwargs):
        while time.monotonic() < deadline:
            status, data = self.exchange(op, **kwargs)
            if status == ACK:
                return data
            if status != NAK:
                raise UsbProbeError(f'USB transaction {op:#04x} failed: handshake={status}')
            time.sleep(0.01)
        raise UsbProbeError(f'USB transaction {op:#04x} timed out waiting for guest')


def probe(usb: UsbTransport, seconds: float):
    deadline = time.monotonic() + seconds
    status, _ = usb.exchange(1, flags=1)  # VBUS + host SOF clock, not SoftConnect
    if status != ACK:
        raise UsbProbeError('DUSB VBUS connect rejected')
    softconnect = False
    last_state = None
    while time.monotonic() < deadline:
        status, state = usb.exchange(0x10, length=8)  # passive status, no guest state write
        if status != ACK or len(state) < 8:
            raise UsbProbeError('DUSB status unavailable')
        last_state = list(state[:8])
        # Requires actual guest programmed SOFTCT (DcMode B8 bit 0).
        # EXTPUL hardware strap is NOT inferred from this eight-byte summary.
        if state[0] and (state[1] & 1):
            softconnect = True
            break
        time.sleep(0.02)
    if not softconnect:
        return {'status':'BLOCKED_NO_GUEST_SOFTCONNECT', 'last_link_state': last_state,
                'guest_descriptors':'NOT_OBSERVED', 'host_enumeration':'NOT_ACCREDITED'}

    usb.retry(3, deadline)  # genuine USB bus reset over the existing DUSB peer
    # USB standard GET_DESCRIPTOR(Device, 18) is a host request, never a host reply.
    setup = struct.pack('<BBHHH', 0x80, 6, 0x0100, 0, 18)
    usb.retry(7, deadline, address=0, endpoint=0, payload=setup)
    received = bytearray()
    toggle = 1
    while len(received) < 18:
        part = usb.retry(9, deadline, address=0, endpoint=0,
                         flags=toggle, length=18-len(received))
        if not part:
            break
        received.extend(part)
        toggle ^= 1
        if len(part) < 8:  # short packet, legal EP0 completion
            break
    if len(received) < 18 or received[:2] != b'\x12\x01':
        return {'status':'BLOCKED_GUEST_DEVICE_DESCRIPTOR',
                'bytes_observed':received.hex(), 'host_enumeration':'NOT_ACCREDITED'}
    usb.retry(8, deadline, address=0, endpoint=0, flags=1, payload=b'')
    return {'status':'GUEST_EP0_DEVICE_DESCRIPTOR_PASS', 'descriptor_hex':received[:18].hex(),
            'vendor_id':f'{int.from_bytes(received[8:10],"little"):04x}',
            'product_id':f'{int.from_bytes(received[10:12],"little"):04x}',
            'host_enumeration':'NOT_ACCREDITED',
            'note':'DUSB/guest EP0 proof only. OS-level enumeration requires separately qualified USB/IP/gadget.'}


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',type=int,required=True)
    parser.add_argument('--timeout',type=float,default=25.0)
    parser.add_argument('--accept-timeout',type=float,default=30.0)
    args=parser.parse_args()
    if not 1<=args.port<=65535 or not 1<=args.timeout<=180 or not 1<=args.accept_timeout<=180:
        parser.error('Invalid bounded port/timeout')
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            listener.bind(('127.0.0.1',args.port))
            listener.listen(1)
            listener.settimeout(args.accept_timeout)
            print('DUSB_IMAGE_TEXT=socket.127.0.0.1:'+str(args.port),flush=True)
            with listener.accept()[0] as client:
                client.settimeout(4)
                result=probe(UsbTransport(client),args.timeout)
                print(json.dumps(result,sort_keys=True))
                return 0 if result['status']=='GUEST_EP0_DEVICE_DESCRIPTOR_PASS' else 2
    except (UsbProbeError,OSError,TimeoutError) as exc:
        print(json.dumps({'status':'BLOCKED_TRANSPORT','reason':str(exc),
                          'host_enumeration':'NOT_ACCREDITED'}))
        return 2

if __name__=='__main__':
    sys.exit(main())
