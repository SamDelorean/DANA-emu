#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Independent IrLAP discovery-only peer for unmodified UK1.5 Beam.

This is a test endpoint, not a Palm service/ROM patch, OBEX implementation or
successful-file-transfer simulation. All bytes cross the actual SIR shifters.
"""
import argparse,json,os,socket,subprocess,time
from pathlib import Path

def fcs(data):
 crc=0xffff
 for byte in data:
  crc^=byte
  for _ in range(8):crc=(crc>>1)^(0x8408 if crc&1 else 0)
 return crc
def encode(body):
 data=body+(fcs(body)^0xffff).to_bytes(2,'little');out=bytearray(b'\xff'*10+b'\xc0')
 for byte in data:
  if byte in (0xc0,0xc1,0x7d):out.extend([0x7d,byte^0x20])
  else:out.append(byte)
 return bytes(out)+b'\xc1'
class Decoder:
 def __init__(self):self.data=None;self.escape=False
 def feed(self,data):
  frames=[]
  for byte in data:
   if byte==0xc0:self.data=bytearray();self.escape=False;continue
   if self.data is None:continue
   if self.escape:self.data.append(byte^0x20);self.escape=False
   elif byte==0x7d:self.escape=True
   elif byte==0xc1:frames.append(bytes(self.data));self.data=None
   else:self.data.append(byte)
  return frames
def main():
 p=argparse.ArgumentParser();p.add_argument('--installed',action='store_true');p.add_argument('--case',required=True);a=p.parse_args()
 root=Path(__file__).resolve().parents[1];folder=root/'local-evidence/runtime-compare/serial-20261101'/a.case;folder.mkdir(parents=True,exist_ok=False)
 listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen(1);listener.settimeout(75)
 env=os.environ.copy();env['DANA_SERIAL_FRAMES']='12100';env['DANA_IR_LINK']='socket.127.0.0.1:'+str(listener.getsockname()[1])
 command=['python3',str(root/'tests/run_host_calendar_native.py'),'--case',a.case,'--script','tests/palm_uk15_serial_application.lua']
 if not a.installed:command+=['--candidate']
 frames=[];responses=[];wire=bytearray();decoder=Decoder()
 with(folder/'runner.out').open('w')as out:
  process=subprocess.Popen(command,cwd=root,env=env,stdout=out,stderr=subprocess.STDOUT)
  try:
   peer,_=listener.accept();peer.settimeout(.5)
   with peer:
    end=time.monotonic()+65
    while time.monotonic()<end:
     try:data=peer.recv(4096)
     except ConnectionResetError:break
     except socket.timeout:
      if process.poll()is not None:break
      continue
     if not data:break
     wire.extend(data)
     for frame in decoder.feed(data):
      frames.append({'length':len(frame),'valid_fcs':fcs(frame)==0xf0b8,'address':frame[0]if frame else-1,'control':frame[1]if len(frame)>1 else-1,'slot':frame[12]if len(frame)>13 else-1})
      if len(frame)>=16 and fcs(frame)==0xf0b8 and frame[:3]==b'\xff\x3f\x01'and frame[12]==0 and not responses:
       # IrLAP XID response: independent device address, echoed destination,
       # discovery flags, PDA/OBEX hints, ASCII character set and peer name.
       body=b'\xfe\xbf\x01\x11\x22\x33\x44'+frame[3:7]+bytes([frame[11],frame[12],0,0x82,0x20,0])+b'Codex IR Peer'
       packet=encode(body);peer.sendall(packet);responses.append(packet.hex())
   process.wait(timeout=30)
  finally:
   listener.close()
   if process.poll()is None:process.kill();process.wait()
 (folder/'wire.bin').write_bytes(wire)
 palm=root/'local-evidence/runtime-compare/calendar-host'/a.case
 text=(palm/'serial-mmio.txt').read_text()if(palm/'serial-mmio.txt').exists()else''
 rx=[line for line in text.splitlines()if'READ=FFFFF914'in line and int(line.split('DATA=')[1].split()[0],16)&0x2000]
 words=[int(line.split('DATA=')[1].split()[0],16)for line in rx if'MASK=FFFF'in line]
 actual=bytes(w&255 for w in words);expected=bytes.fromhex(responses[0])if responses else b''
 result={'original_rx_exact':actual==expected,'original_rx_bytes':len(actual),'original_rx_error_characters':sum(bool(w&0xf00)for w in words),'application_acceptance':'not established by this transport test','returncode':process.returncode,'wire_bytes':len(wire),'frames':frames,'xid_responses':len(responses),'original_uart2_rx_reads':len(rx),'discovery_only':True,'file_transfer_pass':False}
 result['pass']=process.returncode==0 and len(frames)>0 and all(f['valid_fcs']for f in frames)and bool(responses)and bool(rx)and actual==expected and not result['original_rx_error_characters']
 (folder/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
 if not result['pass']:print((folder/'runner.out').read_text()[-2000:]);raise SystemExit(1)
if __name__=='__main__':main()
