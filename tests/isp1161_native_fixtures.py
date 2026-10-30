#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Diagnostic M68000 MMIO fixtures, reusing the qualified D7.5 byte encoder.
These are explicit test guests, never patches or injected code in Palm OS.
"""
from d7_5_native import Code,ENTRY,MARKER,BUFFER
HC,DC=0x1f000000,0x1f000004

class USBCode(Code):
 def __init__(self):
  super().__init__();self.phase=0;self.reports=[];self.move_w(0,MARKER+6)
 def stage(self,value=None):
  self.phase=self.phase+1 if value is None else value
  self.move_w(self.phase,MARKER+2)
 def read(self,address):self.w(0x3039);self.l(address)
 def hw(self,code,value,wide=False):
  self.move_w(code|0x80,HC+2);self.move_w(value&65535,HC)
  if wide:self.move_w(value>>16,HC)
 def hr(self,code,wide=False):
  self.move_w(code,HC+2);self.read(HC)
  if wide:self.w(0x3239);self.l(HC) # high word into d1, retaining low in d0
 def dw(self,code,value=None):
  self.move_w(code,DC+2)
  if value is not None:self.move_w(value,DC)
 def dr(self,code,wide=False):
  self.move_w(code,DC+2);self.read(DC)
  if wide:self.w(0x3239);self.l(DC)
 def wait(self,reader,mask,want):
  start=self.unique();done=self.unique()
  self.w(0x3e3c,60000);self.label(start);reader()
  self.w(0x0240,mask)
  if want is None:self.w(0x6706)
  else:self.w(0x0c40,want,0x6606)
  self.jump(done)
  self.w(0x51cf,(self.labels[start]-(ENTRY+len(self.data)+2))&65535)
  self.jump('fail');self.label(done)
 def setup_vz(self):
  self.move_b(0,0xfffff418);self.move_b(0,0xfffff41b)
  self.move_w(0,0xfffff302);self.move_w(0xfff9,0xfffff304);self.move_w(0xffff,0xfffff306)
 def configure_dc(self):
  for ep in range(16):
   value=(0x83 if ep==0 else 0xc3 if ep==1 else 0xa3 if ep==2 else 0xe3 if ep==3 else 0)
   self.dw(0x20+ep,value)
 def ptd(self,direction,address,endpoint,payload=b'',length=None,toggle=False,cc=0,active=False,iso=False,itl=False,expected=None):
  self.stage()
  total=len(payload)if length is None else length
  head=bytes([0,8|(4 if toggle else 0),64,(endpoint<<4)|8,total&255,((total>>8)&3)|(direction<<2),address|(0x80 if iso else 0),0])
  content=head+payload+bytes(max(0,total-len(payload)))
  content+=bytes((-len(content))%4)
  self.hw(0x22,len(content));self.move_w(0xc0 if itl else 0xc1,HC+2)
  for i in range(0,len(content),2):self.move_w(content[i]|(content[i+1]<<8),HC)
  self.wait(lambda:self.hr(0x2c),0x18 if itl else 0x20,None if itl else 0x20)
  dest=BUFFER+len(self.reports)*256
  self.reports.append((dest,len(content)))
  self.hw(0x22,len(content));self.move_w(0x40 if itl else 0x41,HC+2)
  for i in range(0,len(content),2):
   self.read(HC);self.record(dest+i)
   if i==0:self.w(0x0240,0xf800);self.expect((cc<<12)|(0x800 if active else 0))
   if expected is not None and i>=8 and i-8<len(expected):
    pair=(expected+b"\0")[i-8:i-6];self.expect(int.from_bytes(pair,"little"))
  self.read(0xfffff310);self.w(0x0240,4);self.expect(4)
  self.hw(0x24,0x77)
 def control(self,address,request,data=b'',read=0):
  self.ptd(0,address,0,request)
  if read:self.ptd(2,address,0,length=read,toggle=True)
  if data:self.ptd(1,address,0,data,toggle=True)
  self.ptd(1 if read else 2,address,0,toggle=True)
 def enumerate(self,port,address):
  self.wait(lambda:self.hr(0x15+port,True),0x101,0x101)
  self.hw(0x15+port,0x10,True)
  self.wait(lambda:self.hr(0x15+port,True),0x13,3)
  self.hw(0x15+port,0x1f0000,True)
  self.control(0,bytes([0x80,6,0,1,0,0,18,0]),read=18)
  self.control(0,bytes([0,5,address,0,0,0,0,0]))
  self.control(address,bytes([0x80,6,0,2,0,0,32,0]),read=32)
  self.control(address,bytes([0,9,1,0,0,0,0,0]))

def host_fixture(two_ports=True,faults=False):
 c=USBCode();c.stage();c.setup_vz();c.hw(0x29,0xf6)
 c.hw(0x12,0x202,True);c.hw(0x2a,0x100);c.hw(0x2b,0x800)
 c.hw(0x20,0x1009);c.hw(0x25,0x13);c.hw(4,0x80000040,True);c.hw(1,0x80,True)
 jobs=[]
 for port in range(2 if two_ports else 1):
  address=5+port;c.enumerate(port,address)
  if faults:
   for status,cc in [(1,0),(2,4),(3,5),(4,1),(5,2),(6,3),(7,6)]:
    request=bytes([0x40,0xf0,status,0,1,0,0,0])
    c.control(address,request)
    c.ptd(1,address,1,b'fault',cc=cc,active=status==1)
    if status==1:c.ptd(1,address,1,b'fault')
   # Configured diagnostic loopback: genuine interrupt and ITL ISO packets.
   c.ptd(1,address,2,b'INT')
   c.ptd(2,address,2,length=3)
   c.ptd(3,address,2,length=4,active=True)
   c.hr(3,True);c.w(0x0240,0x10);c.expect(0x10) # malformed PID: UE, no CPU freeze
   c.ptd(1,address,2,b'REC',toggle=True)
   c.ptd(2,address,2,length=3,toggle=True,expected=b'REC')
   for payload in [b'ISO0',b'ISO1',b'ISO2']:
    c.ptd(1,address,3,payload,iso=True,itl=True)
    c.ptd(2,address,3,length=len(payload),iso=True,itl=True,expected=payload)
  else:
   data=('DANA USB CPU PRINT PORT %d\r\n'%(port+1)).encode()
   c.ptd(1,address,1,data);jobs.append(data)
 oc_port=1 if two_ports else 0
 c.stage(0x73);c.wait(lambda:c.hr(0x15+oc_port,True),8,8)
 c.w(0x3e3c,20000);delay=c.unique();c.label(delay);c.w(0x4e71)
 c.w(0x51cf,(c.labels[delay]-(ENTRY+len(c.data)+2))&65535)
 c.hr(0x15+oc_port,True);c.w(0x0240,0x10a);c.expect(8)
 c.stage(0x74);c.wait(lambda:c.hr(0x15+oc_port,True),8,0);c.enumerate(oc_port,5+oc_port)
 c.stage(0x71);c.wait(lambda:c.hr(0x15,True),1,0)
 c.ptd(1,5,1,b'gone',cc=5)
 c.stage(0x70);c.hw(0x28,0xbeef)
 c.w(0x3c3c,7);outer=c.unique();inner=c.unique();c.label(outer);c.w(0x3e3c,65535)
 c.label(inner);c.w(0x4e71);c.w(0x51cf,(c.labels[inner]-(ENTRY+len(c.data)+2))&65535)
 c.w(0x51ce,(c.labels[outer]-(ENTRY+len(c.data)+2))&65535)
 c.hr(0x28);c.expect(0xbeef);c.hr(3,True);c.hw(3,0x7f,True);c.hw(0x24,0x77)
 return c.finish(),c.reports,jobs

def dc_fixture():
 c=USBCode();c.stage(0xd0);c.setup_vz();c.dw(0xf6)
 c.hw(0x29,0xf6);c.hw(0x12,0x202,True);c.hw(0x2a,0x100);c.hw(0x2b,0x800)
 c.hw(0x20,0x1009);c.hw(0x25,0x13);c.hw(4,0x80000040,True);c.hw(1,0x80,True)
 c.dw(0xba,0x0f0c);c.dw(0xc2,0xffff);c.move_w(0x00ff,DC)
 c.configure_dc();c.dw(0xb6,0x80);c.dw(0xb8,0x89)
 c.wait(lambda:c.dr(0xc0,True),1,1) # external bus reset
 c.configure_dc();c.stage(0xd1)
 c.wait(lambda:c.dr(0xc0,True),0x100,0x100)
 c.read(0xfffff310);c.w(0x0240,2);c.expect(2)
 c.dr(0x50);c.move_w(0x10,DC+2);c.read(DC);c.expect(8)
 for i in range(4):c.read(DC);c.record(BUFFER+i*2)
 c.dw(0xf4);c.dw(0x70);c.dw(0x01,8)
 for i in range(4):c.read(BUFFER+i*2);c.w(0x33c0);c.l(DC)
 c.dw(0x61);c.stage(0xd2)
 c.wait(lambda:c.dr(0xc0,True),0x200,0x200);c.dr(0x51)
 c.wait(lambda:c.dr(0xc0,True),0x100,0x100);c.dr(0x50)
 c.move_w(0x10,DC+2);c.read(DC);c.expect(0);c.dw(0x70)
 c.stage(0xd3)
 # Host traffic runs while external bulk OUT occupies the independent DC SRAM.
 c.wait(lambda:c.dr(0xd2),0x20,0x20);c.phase=0x1000
 c.enumerate(1,6);c.ptd(1,6,1,b'DUAL');c.ptd(2,6,1,length=4,expected=b'DUAL')
 c.stage(0xd30)
 for packet in range(2):
  c.wait(lambda:c.dr(0xd2),0x20 if packet==0 else 0x40,0x20 if packet==0 else 0x40);c.dr(0x52)
  c.move_w(0x12,DC+2);c.read(DC);c.expect(16)
  for i in range(8):c.read(DC);c.record(BUFFER+0x100+packet*32+i*2)
  c.dw(0x72);c.dw(0x03,16)
  for i in range(8):c.read(BUFFER+0x100+packet*32+i*2);c.w(0x33c0);c.l(DC)
  c.dw(0x63)
 # HC reset while DC has real validated IN payloads.
 c.dw(0xb2,0x1234);c.hw(0x28,0x4321);c.hw(0x29,0xf6);c.dr(0xb3);c.expect(0x1234)
 c.hw(0x28,0x9876);c.stage(0xd4)
 # Wait for both host IN packets before testing DC DMA.
 for i in range(2):c.wait(lambda:c.dr(0xc0,True),0x800,0x800);c.dr(0x53);c.stage(0xd40+i)
 c.dw(0xf2,5);c.dw(0xf0,0x8038);c.stage(0xd5)
 c.wait(lambda:c.dr(0xc0,True),8,8)
 c.stage(0xd6);c.wait(lambda:c.dr(0xc0,True),0x800,0x800);c.dr(0x53)
 c.dw(0xb8,9);c.dw(0xf2,3);c.dw(0xf0,0x8038);c.stage(0xd60)
 c.wait(lambda:c.dr(0xc0,True),8,8);c.stage(0xd61)
 c.wait(lambda:c.dr(0xc0,True),0x800,0x800);c.dr(0x53)
 c.dw(0xb8,0x89);c.dw(0xf0,0x0038);c.stage(0xd62)
 c.wait(lambda:c.dr(0xc0,True),8,8);c.stage(0xd63)
 c.wait(lambda:c.dr(0xc0,True),0x800,0x800);c.dr(0x53)
 c.dw(0xf6);c.hr(0x28);c.expect(0x9876)
 # Abstract DREQ1/DACK1/EOT on the SAME real HC SRAM and bus.
 c.hw(0x2a,0);c.hw(0x2b,0x100);c.hw(0x22,4);c.hw(0x21,0x17);c.stage(0xd7)
 c.wait(lambda:c.hr(0x21),0x10,0)
 c.hw(0x22,4);c.move_w(0x41,HC+2);c.read(HC);c.expect(0x2211);c.read(HC);c.expect(0x4433)
 # Execute a real level-2 interrupt handler through VZ IACK and vector $1A.
 c.stage(0xd8);c.dw(0xc2,0x11);c.move_w(0,DC);c.dw(0xb8,9)
 c.wait(lambda:c.dr(0xc0,True),1,1) # fresh external reset after disconnect/reconnect
 c.hw(0x20,0x1008);c.move_b(0x18,0xfffff300)
 skip=c.unique();isr=c.unique();c.jump(skip);c.label(isr)
 c.w(0x2f00,0x2f01);c.dr(0xc0,True)
 c.w(0x5279);c.l(MARKER+6);c.w(0x221f,0x201f,0x4e73)
 c.label(skip);c.w(0x23fc);c.l(c.labels[isr]);c.l(0x68)
 c.w(0x46fc,0x2000);c.wait(lambda:c.read(MARKER+6),0xffff,None);c.w(0x46fc,0x2700)
 c.stage(0xdf)
 return c.finish()

def observer(result,reports=()):
 import json
 return """
local m=manager.machine
local cpu=m.devices[":maincpu"];local b=cpu.spaces.program
local frame=0;local writes=0;local prior=-1;local saved=-1;local restored=false;local unplugged=false;local oc_state=0
local tap=b:install_write_tap(0x1f000000,0x1f000007,"isp_actual_cpu",function(a,d,k)
 local pc=cpu.state.CURPC.value
 if pc>=0x2140 and pc<0x20000 then writes=writes+1 end
end)
emu.register_frame_done(function()
 if not tap then return end -- keep native callback lifetime tied to observer
 frame=frame+1
 local marker=b:read_u16(0x20000)
 local phase=b:read_u16(0x20002)
 if phase==0x73 and oc_state==0 then
  local mask=(m.ioport.ports[":USBTEST"]:read()&1)~=0 and 1 or 2
  m.ioport.ports[":USBOC"]:field(mask).user_value=mask;oc_state=1
 end
 if phase==0x74 and oc_state==1 then
  local mask=(m.ioport.ports[":USBTEST"]:read()&1)~=0 and 1 or 2
  m.ioport.ports[":USBOC"]:field(mask).user_value=0;oc_state=2
 end
 if phase==0x71 and not unplugged then
  local image=m.images[":usbprinter0"]
  if image and image.filename and image.filename~=""then image:unload()else m.ioport.ports[":USBTEST"]:field(1).user_value=0 end
  unplugged=true
 end
 if phase==0x70 and saved<0 then saved=frame;m:save(__STATE__)end
 if saved>=0 and frame==saved+2 then m:load(__STATE__);restored=true end
 if phase~=prior then local p=assert(io.open(__PROGRESS__,"w"));p:write(string.format('{"marker":%d,"phase":%d}',marker,phase));p:close();prior=phase end
 if marker==0xa55a or marker==0xdead or frame>6000 then
  local f=assert(io.open(__RESULT__,"w"))
  f:write(string.format('{"marker":%d,"phase":%d,"pc":%d,"cpu_usb_writes":%d,"frames":%d,"save_restore":%s,"irq2_handler_entries":%d,"explicit_unplug":%s,"overcurrent_recovered":%s,"reports":[',marker,b:read_u16(0x20002),cpu.state.CURPC.value,writes,frame,tostring(restored),b:read_u16(0x20006),tostring(unplugged),tostring(oc_state==2)))
  local ranges=__RANGES__
  for j,r in ipairs(ranges)do
   if j>1 then f:write(',')end;f:write('"')
   for i=0,r[2]-1,2 do local v=b:read_u16(r[1]+i);f:write(string.format('%02x%02x',v&255,v>>8))end
   f:write('"')
  end
  f:write('],"usbtest":'..m.ioport.ports[":USBTEST"]:read()..',"overcurrent_input":'..m.ioport.ports[":USBOC"]:read())
  if marker==0xdead then
   for port=0,1 do b:write_u16(0x1f000002,0x15+port);local lo=b:read_u16(0x1f000000);local hi=b:read_u16(0x1f000000);f:write(string.format(',"root%d":%d',port,lo+hi*65536))end
  end
  f:write('}');f:close();m:exit()
 end
end)
""".replace("__RESULT__",json.dumps(str(result))).replace("__PROGRESS__",json.dumps(str(result.with_name("progress.json")))).replace("__STATE__",json.dumps(str(result.with_name("usb-active.sta")))).replace("__RANGES__","{"+",".join("{%d,%d}"%r for r in reports)+"}")
