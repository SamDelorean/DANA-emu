#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Explicit USB packet host for the Dana MAME USB computer image.
No Dana descriptors or endpoint answers are supplied by this peer.
"""
import socket,struct,time,threading
ACK,NAK,STALL,TIMEOUT=0,1,2,3
class USBHost:
 def __init__(self,connection):
  self.connection=connection;self.sequence=0;self.lock=threading.Lock();self.address=0
  connection.settimeout(5);self.trace=[]
 def exact(self,n):
  result=b""
  while len(result)<n:
   part=self.connection.recv(n-len(result))
   if not part:raise ConnectionError("MAME USB link closed")
   result+=part
  return result
 def packet(self,operation,address=0,endpoint=0,flags=0,data=b"",length=0):
  with self.lock:
   self.sequence+=1
   n=len(data)if operation in [7,8,0x22,0x24]else length
   assert 0<=n<=1023
   header=struct.pack("<4s6BHI",b"DUSB",1,operation,address,endpoint,flags,0,n,self.sequence)
   self.connection.sendall(header+data)
   response=self.exact(16)
   magic,version,op,adr,ep,fl,status,count,sequence=struct.unpack("<4s6BHI",response)
   assert magic==b"DUSB"and version==1 and op==(operation|0x80)and sequence==self.sequence
   payload=self.exact(count)if operation in [9,0x10,0x20,0x21,0x23]and status==ACK else b""
   self.trace.append({"operation":operation,"address":address,"endpoint":endpoint,"toggle":flags&1,"requested":n,"status":status,"actual":count,"data_hex":payload.hex()})
   return status,count,payload
 def retry(self,*args,**kwargs):
  deadline=time.monotonic()+4
  while True:
   answer=self.packet(*args,**kwargs)
   if answer[0]!=NAK:return answer
   if time.monotonic()>deadline:raise TimeoutError("Original DC firmware did not validate the requested packet")
   time.sleep(.002)
 def connect(self):
  assert self.packet(1,flags=1)[0]==ACK
 def reset(self):
  assert self.packet(3)[0]==ACK;self.address=0
 def control(self,request_type,request,value=0,index=0,payload=b"",length=0):
  n=length if request_type&0x80 else len(payload)
  setup=struct.pack("<BBHHH",request_type,request,value,index,n)
  answer=self.retry(7,self.address,data=setup);assert answer[0]==ACK,answer
  data=b"";toggle=1
  if request_type&0x80:
   while len(data)<length:
    status,count,part=self.retry(9,self.address,flags=toggle,length=min(64,length-len(data)))
    if status==STALL:return status,data
    assert status==ACK,(status,count)
    data+=part;toggle^=1
    if count<64:break
   assert self.retry(8,self.address,flags=1,data=b"")[0]==ACK
  else:
   for offset in range(0,len(payload),64):
    assert self.retry(8,self.address,flags=toggle,data=payload[offset:offset+64])[0]==ACK;toggle^=1
   status,count,part=self.retry(9,self.address,flags=1,length=0)
   if status==STALL:return status,b""
   assert status==ACK and count==0,(status,count,part)
   if request==5:self.address=value
  return ACK,data
