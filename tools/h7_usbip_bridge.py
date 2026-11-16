#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""H7 USB/IP front end for the *existing* Dana ISP1161 DUSB device controller.

No USB device, VID/PID, endpoint payload, module, or MAME driver is emulated
here. The guest must assert SoftConnect and answer real EP0 descriptors over
DUSB before this server even advertises a USB/IP device. Listens on loopback
only. Requires a separately supported USB/IP client (e.g. Linux vhci_hcd).

Source-only candidate until an authorized one-dana-diag native campaign.
"""
from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass, field
import errno
import json
from pathlib import Path
import select
import socket
import struct
import sys
import time
from typing import Protocol

ACK, NAK, STALL, TIMEOUT = 0, 1, 2, 3
USBIP_VERSION = 0x0111
USBIP_OP_DEVLIST, USBIP_OP_IMPORT = 0x8005, 0x8003
USBIP_CMD_SUBMIT, USBIP_CMD_UNLINK = 1, 2
USBIP_RET_SUBMIT, USBIP_RET_UNLINK = 3, 4
MAX_URB = 65536
MAX_ISO = 32
MAX_PENDING = 64
MAX_CONFIG = 4096
SUPPORTED_EP0 = (8, 16, 32, 64)
BUSID = b'1-1'
# Paths and bus numbers below are USB/IP virtual transport labels, not PCB facts.
VIRTUAL_PATH = b'/sys/devices/platform/dana-diag/usb1/1-1'

class Blocked(RuntimeError):
    """A requested hardware/guest behavior is not established."""

class DUSB(Protocol):
    def packet(self, operation: int, address: int = 0, endpoint: int = 0,
               flags: int = 0, data: bytes = b'', length: int = 0): ...


def exact(sock: socket.socket, size: int) -> bytes:
    result = bytearray()
    while len(result) < size:
        chunk = sock.recv(size - len(result))
        if not chunk:
            raise EOFError('USB peer closed')
        result.extend(chunk)
    return bytes(result)


def header(status: int, command: int, version: int = USBIP_VERSION) -> bytes:
    return struct.pack('!HHI', version, command, status)


def usbip_device_info(device: bytes, config: bytes) -> bytes:
    """312-byte USB/IP export metadata; VID/PID/class only from guest bytes."""
    if len(device) != 18 or device[:2] != b'\x12\x01' or len(config) < 9 or config[1] != 2:
        raise Blocked('Guest descriptor identity not qualified')
    info = bytearray(312)
    info[0:len(VIRTUAL_PATH)] = VIRTUAL_PATH
    info[256:256+len(BUSID)] = BUSID
    struct.pack_into('!III', info, 288, 1, 1, 2)  # virtual bus/dev, full-speed
    info[300:302] = device[8:10][::-1]
    info[302:304] = device[10:12][::-1]
    info[304:306] = device[12:14][::-1]
    info[306:309] = device[4:7]  # bDeviceClass/SubClass/Protocol
    info[309] = config[5]        # bConfigurationValue, guest-supplied
    info[310] = device[17]      # bNumConfigurations
    info[311] = config[4]       # bNumInterfaces
    return bytes(info)


def first_interface(config: bytes) -> bytes:
    offset = 0
    while offset + 2 <= len(config):
        size, kind = config[offset], config[offset+1]
        if size < 2 or offset + size > len(config):
            raise Blocked('Malformed guest configuration descriptor')
        if kind == 4 and size >= 9:
            return bytes([config[offset+5], config[offset+6], config[offset+7], 0])
        offset += size
    raise Blocked('No guest USB interface descriptor')


def endpoint_caps(config: bytes) -> dict[int, int]:
    """Determine max USB packet sizes from firmware-supplied descriptors."""
    caps: dict[int, int] = {}
    offset = 0
    while offset + 2 <= len(config):
        size, kind = config[offset], config[offset+1]
        if size < 2 or offset + size > len(config):
            raise Blocked('Malformed guest endpoint descriptor')
        if kind == 5 and size >= 7:
            ep = config[offset+2]
            if ep & 0x70 or (ep & 0x0f) == 0:
                raise Blocked('Invalid guest endpoint address')
            size_bytes = int.from_bytes(config[offset+4:offset+6], 'little') & 0x7ff
            if not 1 <= size_bytes <= 1023:
                raise Blocked('Unsupported guest max packet size')
            caps[ep] = size_bytes
        offset += size
    return caps


class Hardware:
    def __init__(self, usb: DUSB, *, packet_timeout: float = 5.0):
        self.usb = usb
        self.address = 0
        self.max_packet = 8
        self.device = b''
        self.config = b''
        self.caps: dict[int, int] = {}
        self.config_value = 0
        self.packet_timeout = packet_timeout

    def try_packet(self, op: int, *, deadline: float, address: int = 0,
                   endpoint: int = 0, flags: int = 0, data: bytes = b'', length: int = 0):
        while time.monotonic() < deadline:
            status, count, reply = self.usb.packet(op, address=address, endpoint=endpoint,
                                                   flags=flags, data=data, length=length)
            if status == ACK:
                return reply
            if status == STALL:
                raise Blocked(f'Guest endpoint {endpoint} returned STALL on {op:#x}')
            if status != NAK:
                raise Blocked(f'Guest USB transaction {op:#x} returned status {status}')
            time.sleep(0.003)
        raise Blocked('Guest USB packet deadline expired')

    def status(self):
        status, count, payload = self.usb.packet(0x10, length=8)
        if status != ACK or count != 8 or len(payload) != 8:
            raise Blocked('DUSB device status unavailable')
        return payload

    def attach(self, deadline: float):
        self.try_packet(1, deadline=deadline, flags=1)  # VBUS + real SOF source
        # Cannot advertise a USB device if guest never enables SoftConnect.
        while time.monotonic() < deadline:
            state = self.status()
            if state[0] and (state[1] & 1):
                return
            time.sleep(0.025)
        raise Blocked('Original guest has not asserted DcMode.SoftConnect')

    def reset(self, deadline: float):
        self.try_packet(3, deadline=deadline)  # real DC bus-reset signal
        self.address = 0
        self.config_value = 0

    def control_in(self, setup: bytes, requested: int, deadline: float) -> bytes:
        if len(setup) != 8 or not setup[0] & 0x80:
            raise ValueError('Expected an 8-byte host-to-device USB SETUP for IN transfer')
        self.try_packet(7, deadline=deadline, address=self.address, data=setup)
        result = bytearray()
        toggle = 1  # DUSB bit 0 = USB DATA1; never bit 2 (ISO)
        while len(result) < requested:
            size = min(self.max_packet, requested-len(result))
            part = self.try_packet(9, deadline=deadline, address=self.address,
                                   flags=toggle, length=size)
            if len(part) > size:
                raise Blocked('Guest returned more data than host requested')
            result.extend(part)
            toggle ^= 1
            if len(part) < size:
                break
        self.try_packet(8, deadline=deadline, address=self.address, flags=1, data=b'')
        return bytes(result)

    def identify(self, deadline: float):
        self.attach(deadline)
        self.reset(deadline)
        first = self.control_in(struct.pack('<BBHHH',0x80,6,0x0100,0,8),8,deadline)
        if len(first) != 8 or first[:2] != b'\x12\x01' or first[7] not in SUPPORTED_EP0:
            raise Blocked('Original guest EP0 did not supply valid initial descriptor')
        self.max_packet = first[7]
        dev = self.control_in(struct.pack('<BBHHH',0x80,6,0x0100,0,18),18,deadline)
        if len(dev) != 18 or dev[:2] != b'\x12\x01' or dev[7] != self.max_packet:
            raise Blocked('Original guest full device descriptor incomplete or inconsistent')
        conf9 = self.control_in(struct.pack('<BBHHH',0x80,6,0x0200,0,9),9,deadline)
        if len(conf9) < 9 or conf9[:2] != b'\x09\x02':
            raise Blocked('Original guest configuration header unavailable')
        total = int.from_bytes(conf9[2:4], 'little')
        if not 9 <= total <= MAX_CONFIG:
            raise Blocked('Guest configuration size invalid or out of bound')
        conf = self.control_in(struct.pack('<BBHHH',0x80,6,0x0200,0,total),total,deadline)
        if len(conf) != total or conf[:9] != conf9:
            raise Blocked('Original guest configuration descriptor incomplete')
        first_interface(conf)  # reject non-enumerable guest configuration
        self.caps = endpoint_caps(conf)
        self.device = dev
        self.config = conf
        return dev, conf


@dataclass
class URB:
    seq: int
    ep: int
    direction: int
    length: int
    payload: bytes
    setup: bytes
    flags: int = 0
    phase: str = 'new'
    offset: int = 0
    toggle: int = 1
    data: bytearray = field(default_factory=bytearray)
    started: float = field(default_factory=time.monotonic)


class Bridge:
    def __init__(self, device: Hardware, *, transfer_timeout: float = 20.0):
        self.device = device
        self.pending: deque[URB] = deque()
        self.toggles: dict[tuple[int,int], int] = {}
        self.timeout = transfer_timeout
        self.address = 0

    def accept(self, urb: URB):
        if len(self.pending) >= MAX_PENDING:
            raise Blocked('Too many outstanding USB/IP URBs')
        if urb.ep > 15 or urb.direction not in (0,1) or urb.length > MAX_URB:
            raise Blocked('Unsupported USB/IP endpoint or URB')
        self.pending.append(urb)

    def cancel(self, seq: int) -> bool:
        for item in self.pending:
            if item.seq == seq:
                self.pending.remove(item)
                return True
        return False

    def _packet(self, op: int, urb: URB, *, length=0, data=b'', toggle=0):
        status, count, received = self.device.usb.packet(
            op, address=self.address, endpoint=urb.ep, flags=toggle,
            data=data, length=length)
        if status == NAK:
            return None
        if status != ACK:
            raise OSError({STALL:errno.EPIPE,TIMEOUT:errno.ETIMEDOUT}.get(status,errno.EPROTO),
                          f'USB packet handshake={status}')
        if op == 9 and (count != len(received) or count > length):
            raise OSError(errno.EPROTO, 'Bad USB guest IN packet length')
        return received

    def step(self, urb: URB):
        """At most one real DUSB packet per turn. NAK leaves URB pending."""
        if time.monotonic()-urb.started > self.timeout:
            raise OSError(errno.ETIMEDOUT, 'USB/IP URB timed out')
        ep = urb.ep
        if urb.phase == 'new':
            if ep == 0:
                if len(urb.setup) != 8:
                    raise OSError(errno.EINVAL, 'Missing control SETUP')
                # URB direction and setup direction must agree for data stages.
                want = int(bool(urb.setup[0]&0x80))
                if urb.length and want != urb.direction:
                    raise OSError(errno.EINVAL, 'Control direction disagrees with SETUP')
                if urb.length > int.from_bytes(urb.setup[6:8],'little'):
                    raise OSError(errno.EINVAL, 'URB exceeds USB wLength')
                part = self._packet(7, urb, data=urb.setup)
                if part is None:return False
                urb.phase = 'data_in' if want and urb.length else 'data_out' if urb.length else ('status_out' if want else 'status_in')
                # For IN data starts DATA1, for OUT data starts DATA1.
                urb.toggle = 1
            else:
                urb.phase = 'bulk_in' if urb.direction else 'bulk_out'
                urb.toggle = self.toggles.get((ep,urb.direction),0)
            return False

        if urb.phase in ('data_in','bulk_in'):
            mps = self.device.max_packet if ep == 0 else self.device.caps.get(ep|0x80)
            if not mps:raise OSError(errno.EOPNOTSUPP,'Guest endpoint IN not advertised')
            size = min(mps,urb.length-len(urb.data))
            if size <= 0:
                urb.phase = 'status_out' if ep==0 else 'complete'
                return urb.phase == 'complete'
            result = self._packet(9, urb,length=size,toggle=urb.toggle)
            if result is None:return False
            urb.data.extend(result)
            urb.toggle ^= 1
            if ep:self.toggles[(ep,urb.direction)] = urb.toggle
            if len(result) < size or len(urb.data) >= urb.length:
                urb.phase = 'status_out' if ep==0 else 'complete'
                return urb.phase == 'complete'
            return False

        if urb.phase in ('data_out','bulk_out'):
            mps = self.device.max_packet if ep == 0 else self.device.caps.get(ep)
            if not mps:raise OSError(errno.EOPNOTSUPP,'Guest endpoint OUT not advertised')
            size = min(mps,urb.length-urb.offset)
            # Non-control zero-length OUT is one real ZLP; no phantom ACK.
            chunk = urb.payload[urb.offset:urb.offset+size]
            if urb.length and not chunk:
                raise OSError(errno.EPROTO,'Short USB/IP outbound payload')
            result = self._packet(8, urb,data=chunk,toggle=urb.toggle)
            if result is None:return False
            urb.offset += len(chunk)
            urb.toggle ^= 1
            if ep:self.toggles[(ep,urb.direction)] = urb.toggle
            if urb.offset >= urb.length:
                urb.phase = 'status_in' if ep==0 else 'complete'
                return urb.phase == 'complete'
            return False

        if urb.phase == 'status_in':
            result = self._packet(9,urb,length=0,toggle=1)
            if result is None:return False
            if result:
                raise OSError(errno.EPROTO,'Control status IN must be ZLP')
            urb.phase='complete'
            self._control_commit(urb)
            return True

        if urb.phase == 'status_out':
            result = self._packet(8,urb,data=b'',toggle=1)
            if result is None:return False
            urb.phase='complete'
            return True

        return urb.phase == 'complete'

    def _control_commit(self, urb: URB):
        # USB device's SET_ADDRESS itself commits after status ACK within ISP1161.
        if urb.setup[:2] == b'\x00\x05' and urb.length == 0:
            self.address = int.from_bytes(urb.setup[2:4],'little') & 0x7f
        if urb.setup[:2] == b'\x00\x09' and urb.length == 0:
            self.device.config_value = int.from_bytes(urb.setup[2:4],'little') & 0xff
            self.toggles.clear()

    def tick(self):
        """Round-robin one packet/URB, so a waiting IN cannot block EP0/OUT."""
        replies=[]
        size=len(self.pending)
        serviced=set()
        for _ in range(size):
            urb=self.pending.popleft()
            # EP0 is globally serialized; each direction of other endpoints
            # preserves submission order even when earlier URBs are NAKed.
            key=(0,0) if urb.ep == 0 else (urb.ep,urb.direction)
            if key in serviced:
                self.pending.append(urb)
                continue
            serviced.add(key)
            try:
                complete=self.step(urb)
            except OSError as error:
                replies.append(ret_submit(urb,-error.errno,b''))
                continue
            if complete:
                replies.append(ret_submit(urb,0,bytes(urb.data)))
            else:
                self.pending.append(urb)
        return replies


def ret_submit(urb: URB, status: int, data: bytes) -> bytes:
    # USB/IP RET_SUBMIT: 48 bytes; zero reserved + no ISO descriptors.
    head = bytearray(48)
    struct.pack_into('!IIIIIiIIII',head,0,USBIP_RET_SUBMIT,urb.seq,0,0,0,status,
                     len(data) if urb.direction else urb.offset,0,0xffffffff,0)
    return bytes(head)+(data if status==0 and urb.direction else b'')


def ret_unlink(seq: int, canceled: bool) -> bytes:
    # No RET_SUBMIT is emitted for a successfully canceled pending URB.
    head=bytearray(48)
    struct.pack_into('!IIIIIi',head,0,USBIP_RET_UNLINK,seq,0,0,0,-errno.ECONNRESET if canceled else 0)
    return bytes(head)


def extract_packets(buffer: bytearray):
    """Parse complete USB/IP URBs, including client TCP fragmentation."""
    while len(buffer) >= 48:
        command,seq,dev,direction,ep=struct.unpack_from('!IIIII',buffer)
        if command == USBIP_CMD_UNLINK:
            target=struct.unpack_from('!I',buffer,20)[0]
            del buffer[:48]
            yield ('unlink',seq,target)
            continue
        if command != USBIP_CMD_SUBMIT:
            raise Blocked(f'Unsupported USB/IP command {command}')
        flags,rawlength,start,num,interval=struct.unpack_from('!IIIII',buffer,20)
        if direction not in (0,1) or ep>15 or rawlength>MAX_URB or num not in (0xffffffff,0):
            raise Blocked('Unqualified USB/IP direction/endpoint/size/iso')
        payload_len = rawlength if direction==0 else 0
        if len(buffer) < 48+payload_len:
            return
        setup=bytes(buffer[40:48]);data=bytes(buffer[48:48+payload_len])
        del buffer[:48+payload_len]
        yield ('submit',URB(seq,ep,direction,rawlength,data,setup,flags))


def serve_import(sock: socket.socket, usb: Hardware, stop_after: float):
    usb.reset(time.monotonic()+5)
    bridge=Bridge(usb,transfer_timeout=stop_after)
    sock.setblocking(False)
    buffer=bytearray()
    output=bytearray()
    last_activity=time.monotonic()
    while True:
        readable,writable,_=select.select([sock],[sock] if output else [],[],0.005)
        if readable:
            try:piece=sock.recv(65536)
            except BlockingIOError:piece=None
            if piece == b'':return
            if piece:
                buffer.extend(piece)
                if len(buffer) > MAX_URB+MAX_PENDING*48:
                    raise Blocked('USB/IP buffered input exceeds bound')
                last_activity=time.monotonic()
        for event in extract_packets(buffer):
            if event[0]=='submit':
                bridge.accept(event[1])
            else:
                output.extend(ret_unlink(event[1],bridge.cancel(event[2])))
        for response in bridge.tick():
            output.extend(response)
        if output and writable:
            try:n=sock.send(output)
            except BlockingIOError:n=0
            if n:del output[:n]
        if len(output)>2*MAX_URB:
            raise Blocked('USB/IP output exceeds bounded queue')
        if time.monotonic()-last_activity>max(60,stop_after+10) and not bridge.pending:
            return


def listen_and_bridge(usb: Hardware, port: int, timeout: float):
    # Listen only after guest descriptors have been obtained from real EP0.
    device_info=usbip_device_info(usb.device,usb.config)
    interface_info=first_interface(usb.config)
    with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
        listener.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
        listener.bind(('127.0.0.1',port))
        listener.listen(2)
        listener.settimeout(timeout)
        print(json.dumps({'status':'GUEST_DESCRIPTOR_OBSERVED',
                          'usbip':'127.0.0.1:'+str(port),
                          'vid':usb.device[8:10][::-1].hex(),
                          'pid':usb.device[10:12][::-1].hex(),
                          'host_os_enumeration':'NOT_ACCREDITED'}),flush=True)
        while True:
            with listener.accept()[0] as client:
                client.settimeout(5)
                v,op,status=struct.unpack('!HHI',exact(client,8))
                if v not in (0x0111,0x0106) or status != 0:
                    continue
                if op==USBIP_OP_DEVLIST:
                    client.sendall(header(0,5,v)+struct.pack('!I',1)+device_info+interface_info)
                elif op==USBIP_OP_IMPORT:
                    name=exact(client,32).split(b'\x00',1)[0]
                    if name!=BUSID:
                        client.sendall(header(1,3,v));continue
                    client.sendall(header(0,3,v)+device_info)
                    try:serve_import(client,usb,timeout)
                    finally:
                        try:usb.usb.packet(2)  # DUSB disconnect, genuine bus state
                        except Exception:pass
                    return


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dusb-port',type=int,default=39161)
    p.add_argument('--usbip-port',type=int,default=3240)
    p.add_argument('--timeout',type=float,default=25)
    args=p.parse_args()
    if not (1024<=args.dusb_port<=65535 and 1024<=args.usbip_port<=65535
            and args.dusb_port!=args.usbip_port and 5<=args.timeout<=120):
        p.error('Ports must be distinct 1024-65535, timeout 5-120')
    # Import only the already native-qualified DUSB host implementation.
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tests'))
    from isp1161_virtual_host import USBHost
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as listener:
            listener.bind(('127.0.0.1',args.dusb_port))
            listener.listen(1)
            listener.settimeout(args.timeout)
            print(f'DUSB_IMAGE_TEXT=socket.127.0.0.1:{args.dusb_port}',flush=True)
            with listener.accept()[0] as client:
                client.settimeout(5)
                hardware=Hardware(USBHost(client))
                hardware.identify(time.monotonic()+args.timeout)
                listen_and_bridge(hardware,args.usbip_port,args.timeout)
        return 0
    except (Blocked,OSError,EOFError,TimeoutError,AssertionError) as e:
        print(json.dumps({'status':'BLOCKED_H7_USB','reason':str(e),
                          'host_os_enumeration':'NOT_ACCREDITED'}),flush=True)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
