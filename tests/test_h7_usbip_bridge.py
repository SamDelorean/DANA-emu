#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Host-only protocol tests. Synthetic descriptor fixture is NOT Dana evidence."""
import sys,struct,time,unittest,errno,socket,threading
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from h7_usbip_bridge import (
 USBIP_CMD_SUBMIT,USBIP_CMD_UNLINK,USBIP_RET_SUBMIT,USBIP_RET_UNLINK,
 Blocked,Hardware,URB,Bridge,usbip_device_info,first_interface,endpoint_caps,
 extract_packets,ret_submit,ret_unlink,listen_and_bridge,ACK,NAK,STALL
)

DEVICE=bytes.fromhex('12 01 00 02 00 00 00 08 34 12 78 56 00 01 01 02 03 01')
CONFIG=bytes.fromhex('09 02 20 00 01 01 00 80 32 '
 '09 04 00 00 02 ff 01 02 00 '
 '07 05 81 02 20 00 00 '
 '07 05 02 02 20 00 00')

class FakeUsb:
 def __init__(self):self.calls=[];self.events=[];self.response=[]
 def packet(self,operation,address=0,endpoint=0,flags=0,data=b'',length=0):
  self.calls.append((operation,address,endpoint,flags,data,length))
  if self.events:
   return self.events.pop(0)
  if operation in (7,8,1,3,2):return ACK,0,b''
  if operation==9:return ACK,0,b''
  if operation==0x10:return ACK,8,bytes([1,1,0,1,0,0,0,0])
  raise AssertionError(operation)

class UsbipStaticTests(unittest.TestCase):
 def test_no_guessed_vid_pid_metadata(self):
  meta=usbip_device_info(DEVICE,CONFIG)
  self.assertEqual(len(meta),312)
  self.assertEqual(meta[300:306],bytes.fromhex('12 34 56 78 01 00'))
  self.assertEqual(meta[309:312],bytes([1,1,1]))
  self.assertEqual(first_interface(CONFIG),bytes.fromhex('ff 01 02 00'))
  self.assertEqual(endpoint_caps(CONFIG),{0x81:32,0x02:32})
  with self.assertRaises(Blocked):usbip_device_info(b'\0'*18,CONFIG)

 def test_descriptor_discovery_comes_only_from_guest_packets(self):
  class Guest:
   def __init__(self):self.ops=[];self.request=None;self.offset=0
   def packet(self,op,address=0,endpoint=0,flags=0,data=b'',length=0):
    self.ops.append((op,flags,address,endpoint,data,length))
    if op==0x10:return ACK,8,bytes([1,1,0,1,0,0,0,0])
    if op==7:
     bm,req,value,index,size=struct.unpack('<BBHHH',data)
     self.request=DEVICE if (value>>8)==1 else CONFIG
     self.offset=0
     return ACK,0,b''
    if op==9:
     chunk=self.request[self.offset:self.offset+length]
     self.offset+=len(chunk)
     return ACK,len(chunk),chunk
    return ACK,0,b''
  guest=Guest();hardware=Hardware(guest)
  hardware.identify(time.monotonic()+3)
  self.assertEqual(hardware.device,DEVICE)
  self.assertEqual(hardware.config,CONFIG)
  self.assertEqual(hardware.max_packet,8)
  self.assertEqual(hardware.caps,{0x81:32,0x02:32})
  self.assertEqual({c[1] for c in guest.ops if c[0]==9},{1,0})
  self.assertFalse(any(c[1]&4 for c in guest.ops if c[0] in (8,9)))

 def test_usbip_loopback_list_import_and_real_guest_descriptor(self):
  class Guest:
   def __init__(self):self.calls=[];self.buffer=b'';self.pos=0
   def packet(self,op,address=0,endpoint=0,flags=0,data=b'',length=0):
    self.calls.append((op,flags))
    if op==7:
     kind=data[3]
     self.buffer=DEVICE if kind==1 else CONFIG
     self.pos=0
    if op==9:
     chunk=self.buffer[self.pos:self.pos+length]
     self.pos+=len(chunk)
     return ACK,len(chunk),chunk
    return ACK,0,b''
  guest=Guest();hw=Hardware(guest);hw.device=DEVICE;hw.config=CONFIG;hw.caps=endpoint_caps(CONFIG)
  with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as reserv:
   reserv.bind(('127.0.0.1',0));port=reserv.getsockname()[1]
  failures=[]
  def server():
   try:listen_and_bridge(hw,port,3)
   except Exception as exc:failures.append(exc)
  worker=threading.Thread(target=server,daemon=True);worker.start()
  def connect():
   for _ in range(80):
    try:return socket.create_connection(('127.0.0.1',port),timeout=.5)
    except OSError:time.sleep(.008)
   self.fail('Loopback USB/IP server not accepting connection')
  with connect() as c:
   c.settimeout(2);c.sendall(struct.pack('!HHI',0x111,0x8005,0))
   response=bytearray()
   while len(response)<328:response.extend(c.recv(328-len(response)))
   self.assertEqual(response[:12],struct.pack('!HHII',0x111,5,0,1))
   self.assertEqual(response[12+300:12+304],bytes.fromhex('12 34 56 78'))
  with connect() as c:
   c.settimeout(2)
   c.sendall(struct.pack('!HHI',0x111,0x8003,0)+b'1-1'.ljust(32,b'\0'))
   response=bytearray()
   while len(response)<320:response.extend(c.recv(320-len(response)))
   self.assertEqual(response[:8],struct.pack('!HHI',0x111,3,0))
   setup=struct.pack('<BBHHH',0x80,6,0x0100,0,8)
   urb=struct.pack('!IIIII',1,11,0x10001,1,0)+struct.pack('!IIIII',0,8,0,0xffffffff,0)+setup
   c.sendall(urb)
   response=bytearray()
   while len(response)<56:response.extend(c.recv(56-len(response)))
   self.assertEqual(struct.unpack('!II',response[:8]),(3,11))
   self.assertEqual(struct.unpack('!iI',response[20:28]),(0,8))
   self.assertEqual(response[48:],DEVICE[:8])
  worker.join(timeout=2)
  self.assertFalse(worker.is_alive())
  self.assertFalse(failures,failures)
  self.assertIn((9,1),guest.calls) # genuine DATA1; never ISO flag 4

 def test_partial_submit_and_unlink_parser(self):
  req=struct.pack('!IIIII',USBIP_CMD_SUBMIT,11,0x10001,0,2)
  req+=struct.pack('!IIIII',0,3,0,0xffffffff,0)+bytes(8)+b'XYZ'
  buf=bytearray(req[:31]);self.assertEqual(list(extract_packets(buf)),[])
  buf.extend(req[31:]);events=list(extract_packets(buf))
  self.assertEqual((len(buf),len(events),events[0][1].payload),(0,1,b'XYZ'))
  unl=struct.pack('!IIIII',USBIP_CMD_UNLINK,12,0,0,0)+struct.pack('!I',11)+bytes(24)
  buf=bytearray(unl);self.assertEqual(list(extract_packets(buf)),[('unlink',12,11)])

 def test_submit_result_and_unlink_endianness(self):
  urb=URB(55,1,1,8,b'',bytes(8));urb.data=bytearray(b'HELLO')
  p=ret_submit(urb,0,b'HELLO')
  self.assertEqual(len(p),53)
  self.assertEqual(struct.unpack('!I',p[:4])[0],USBIP_RET_SUBMIT)
  self.assertEqual(struct.unpack('!i',p[20:24])[0],0)
  self.assertEqual(struct.unpack('!I',p[24:28])[0],5)
  self.assertEqual(p[-5:],b'HELLO')
  u=ret_unlink(56,True)
  self.assertEqual((len(u),struct.unpack('!I',u[:4])[0],struct.unpack('!i',u[20:24])[0]),(48,USBIP_RET_UNLINK,-errno.ECONNRESET))

 def test_real_dusb_toggle_bit_zero_not_iso(self):
  fake=FakeUsb();hw=Hardware(fake);hw.max_packet=8;hw.device=DEVICE;hw.config=CONFIG;hw.caps=endpoint_caps(CONFIG)
  bridge=Bridge(hw)
  setup=struct.pack('<BBHHH',0x80,6,0x100,0,8)
  fake.events.extend([(ACK,0,b''),(ACK,8,b'12345678'),(ACK,0,b'')])
  bridge.accept(URB(9,0,1,8,b'',setup))
  for _ in range(3):result=bridge.tick()
  self.assertEqual(len(result),1)
  self.assertEqual(result[0][-8:],b'12345678')
  self.assertEqual([x[0] for x in fake.calls],[7,9,8])
  self.assertEqual(fake.calls[1][3],1) # DATA1, never 4 (ISO)
  self.assertEqual(fake.calls[2][3],1) # control status DATA1

 def test_set_address_commits_only_after_status(self):
  fake=FakeUsb();hw=Hardware(fake);hw.max_packet=8
  br=Bridge(hw);br.accept(URB(3,0,0,0,b'',struct.pack('<BBHHH',0,5,5,0,0)))
  br.tick();self.assertEqual(br.address,0)
  br.tick();self.assertEqual(br.address,5)
  self.assertEqual([x[0] for x in fake.calls],[7,9])

 def test_ep0_global_order_and_other_endpoint_forward_progress(self):
  fake=FakeUsb();hw=Hardware(fake);hw.caps=endpoint_caps(CONFIG)
  bridge=Bridge(hw)
  first=URB(1,0,1,8,b'',struct.pack('<BBHHH',0x80,6,0x100,0,8))
  second=URB(2,0,1,8,b'',first.setup)
  other=URB(3,2,0,3,b'ABC',bytes(8))
  bridge.accept(first);bridge.accept(second);bridge.accept(other)
  fake.events.extend([(NAK,0,b''),(ACK,0,b'')])
  bridge.tick()  # first turn establishes state; no DUSB packet yet for data EP
  bridge.tick()  # EP0 NAK does not starve independent OUT endpoint
  self.assertEqual([c[2] for c in fake.calls],[0,0,2])  # first EP0 may retry after NAK
  self.assertEqual(sum(1 for x in fake.calls if x[2]==0),2)
  self.assertEqual(fake.calls[-1][0],8)  # another physical endpoint progressed

 def test_cancel_urb_no_late_reply(self):
  fake=FakeUsb();hw=Hardware(fake)
  b=Bridge(hw);u=URB(11,1,1,4,b'',bytes(8));b.accept(u)
  self.assertTrue(b.cancel(11))
  self.assertEqual(b.tick(),[])
  self.assertEqual(len(b.pending),0)
  self.assertFalse(b.cancel(11))

 def test_no_softconnect_blocks_without_descriptor(self):
  fake=FakeUsb();fake.events.extend([(ACK,0,b''),(ACK,8,bytes([1,0,0,0,0,0,0,0]))])
  hw=Hardware(fake)
  with self.assertRaises(Blocked):hw.attach(time.monotonic()+.0001)
  self.assertNotIn(7,[x[0] for x in fake.calls])

if __name__=='__main__':unittest.main()
