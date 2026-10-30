#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""One canonical-MAME ISP1161 native campaign. No install/build/ROM patch."""
import argparse,hashlib,json,os,shutil,socket,subprocess,time
from pathlib import Path
from isp1161_native_fixtures import host_fixture,dc_fixture,observer
from isp1161_virtual_host import USBHost,ACK,NAK,STALL,TIMEOUT

def main():
 p=argparse.ArgumentParser();p.add_argument("--installed",action="store_true")
 p.add_argument("--case",required=True);p.add_argument("--mode",choices=["bus","ptd-bus","host-printer","host-faults","device"],required=True)
 args=p.parse_args();assert args.case.replace("-","").replace("_","").isalnum()
 root=Path(__file__).resolve().parents[1]
 binary=root/("runtime/diag/bin/dana-diag"if args.installed else "runtime/diag/source/danadiagd")
 evidence=root/"local-evidence/runtime-compare/usb-20261030"/args.case;evidence.mkdir(parents=True,exist_ok=False)
 cfg=evidence/"cfg";cfg.mkdir()
 for name in ["asmdana.cfg","default.cfg"]:shutil.copy2(root/"config/palm-uk15"/name,cfg/name)
 env=os.environ.copy();env.update(SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy",TMPDIR=str(evidence))
 command=[str(binary),"asmdana","-video","none","-sound","none","-skip_gameinfo","-nowriteconfig",
  "-cfg_directory",str(cfg),"-nvram_directory",str(evidence/"nvram"),"-state_directory",str(evidence/"states"),"-oslog","-log","-autoboot_delay","0"]
 reports=[];jobs=[];listener=None
 if args.mode in ["bus","ptd-bus"]:
  command+=["-rom",str(root/"runtime/diag/work/uk15_qualify_20261025/UK15_private.raw"),"-nothrottle",
   "-autoboot_script",str(root/"tests"/("isp1161_hc_dc_bus.lua"if args.mode=="bus"else"isp1161_ptd_native_bus.lua"))]
  env["DANA_PALM_TRACE"]=str(evidence/"bus.txt")
 else:
  if args.mode.startswith("host"):
   package,reports,jobs=host_fixture(args.mode=="host-printer",args.mode=="host-faults")
   if jobs:
    for i in range(2):
     output=evidence/("printer%d.prn"%i);output.write_bytes(b"")
     command+=["-prin"+str(i+1),str(output)]
   else:
    text=(cfg/"asmdana.cfg").read_text().replace("</input>",'<port tag=":USBTEST" type="CONFIG" mask="1" defvalue="0" value="1"/></input>')
    (cfg/"asmdana.cfg").write_text(text)
   command+=["-nothrottle"]
  else:
   package=dc_fixture()
   text=(cfg/"asmdana.cfg").read_text().replace("</input>",'<port tag=":USBTEST" type="CONFIG" mask="2" defvalue="0" value="2"/></input>')
   (cfg/"asmdana.cfg").write_text(text)
   listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1);listener.settimeout(15)
   link=evidence/"computer.usb";link.write_text("socket.127.0.0.1:%d\n"%listener.getsockname()[1])
   command+=["-usbcomputer",str(link),"-throttle"]
  (evidence/"guest.dana").write_bytes(package)
  (evidence/"observer.lua").write_text(observer(evidence/"cpu.json",reports))
  command+=["-quickload",str(evidence/"guest.dana"),"-autoboot_script",str(evidence/"observer.lua")]
 result={"mode":args.mode,"binary_sha256":hashlib.sha256(binary.read_bytes()).hexdigest()}
 with(evidence/"run.out").open("w")as logfile:
  process=subprocess.Popen(command,cwd=root/"runtime/diag",env=env,stdout=logfile,stderr=subprocess.STDOUT)
  try:
   if listener:
    connection,_=listener.accept()
    with connection:
     host=USBHost(connection)
     def phase(want):
      end=time.monotonic()+10
      while time.monotonic()<end:
       progress=evidence/"progress.json"
       if progress.exists():
        try:
         value=json.loads(progress.read_text())
         if value["phase"]==want:return
         if value["marker"]==0xdead:raise AssertionError(value)
        except json.JSONDecodeError:pass
       if process.poll()is not None:raise RuntimeError("MAME exited: "+(evidence/"run.out").read_text()[-1200:])
       time.sleep(.003)
      raise TimeoutError("CPU phase %x"%want)
     phase(0xd0);host.connect()
     while host.packet(0x10)[2][1]!=0x89:time.sleep(.003)
     host.reset();phase(0xd1)
     setup=bytes([0x40,1,0x12,0x34,0x56,0x78,8,0])
     assert host.packet(7,data=setup)[0]==ACK
     status,count,data=host.retry(9,flags=1,length=64)
     assert status==ACK and count==8 and data==setup,(status,count,data)
     assert host.packet(8,flags=1,data=b"")[0]==ACK
     phase(0xd3)
     sent=[bytes(range(16)),bytes(range(16,32))]
     for i,data in enumerate(sent):assert host.packet(8,endpoint=1,flags=i,data=data)[0]==ACK
     phase(0xd4)
     assert host.packet(9,endpoint=15,length=8)[0]==STALL
     for i,data in enumerate(sent):
      status,count,payload=host.retry(9,endpoint=2,flags=i,length=64)
      assert status==ACK and payload==data,(status,count,payload)
      if i==0:phase(0xd40)
     phase(0xd5)
     signals=host.packet(0x20)[2];assert signals[1]==1 and signals[6]==5,signals
     for data in [b"AB",b"CD",b"E_"]:assert host.packet(0x24,data=data)[0]==ACK
     phase(0xd6)
     assert host.packet(5)[0]==ACK and host.packet(0x10)[2][7]==1
     assert host.packet(9,endpoint=2,length=64)[0]==TIMEOUT
     assert host.packet(6)[0]==ACK and host.packet(0x10)[2][7]==0
     assert host.retry(9,endpoint=2,flags=0,length=64)[2]==b"ABCDE"
     phase(0xd60)
     assert host.packet(0x24,flags=1,data=b"!")[0]==NAK # inactive physical DACK2 level
     for b in b"XYZ":assert host.packet(0x24,data=bytes([b]))[0]==ACK
     phase(0xd61);assert host.retry(9,endpoint=2,flags=1,length=64)[2]==b"XYZ"
     phase(0xd62);assert host.packet(0x24,data=b"GH")[0]==ACK
     assert host.packet(0x25,flags=2)[0]==ACK
     phase(0xd63);assert host.retry(9,endpoint=2,flags=0,length=64)[2]==b"GH"
     phase(0xd7)
     assert host.packet(0x20)[2][0]==1
     assert host.packet(0x22,data=bytes([0x11,0x22]))[0]==ACK
     assert host.packet(0x22,data=bytes([0x33,0x44]))[0]==ACK
     phase(0xd8)
     assert host.packet(2)[0]==ACK and host.packet(0x10)[2][0]==0
     assert host.packet(9,length=8)[0]==TIMEOUT
     host.connect();assert host.packet(0x10)[2][0]==1;host.reset()
     result["disconnect_reconnect"]=True
     phase(0xdf) # keep the explicit upstream bus alive through real IRQ2/IACK
     (evidence/"packets.json").write_text(json.dumps(host.trace,indent=2)+"\n")
     result["upstream_packets"]=len(host.trace);result["native_ep0_echo"]=setup.hex();result["dma_payload"]="ABCDE / XYZ / GH";result["hc_dc_concurrent"]=True;result["suspend_resume"]=True
   process.wait(timeout=90)
  finally:
   if listener:listener.close()
   if process.poll()is None:
    process.terminate()
    try:process.wait(timeout=3)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
 (evidence/"process.json").write_text(json.dumps({"returncode":process.returncode})+"\n")
 text=(evidence/"run.out").read_text()
 assert process.returncode==0 and "[LUA ERROR]"not in text and "DANA_PHYSICAL_BLOCKED"not in text,text[-3000:]
 if args.mode in ["bus","ptd-bus"]:
  trace=(evidence/"bus.txt").read_text()
  marker="USB_DIRECTED_TOTAL_PASS=33"if args.mode=="bus"else"ISP1161_HC_PTD_NATIVE_BUS_PASS"
  assert marker in trace and "FAIL"not in trace
  result["native_bus_assertions"]=33 if args.mode=="bus"else 7
 else:
  cpu=json.loads((evidence/"cpu.json").read_text());assert cpu["marker"]==0xa55a,cpu
  assert cpu["cpu_usb_writes"]>10,cpu
  if args.mode=="device":assert cpu["irq2_handler_entries"]>0,cpu
  result["cpu"]=cpu
  if jobs:
   for i,data in enumerate(jobs):assert(evidence/("printer%d.prn"%i)).read_bytes()==data
   result["printed_jobs"]=[data.decode()for data in jobs]
 result["status"]="NATIVE_PASS"
 (evidence/"result.json").write_text(json.dumps(result,indent=2)+"\n")
 print(json.dumps(result,indent=2))
if __name__=="__main__":main()
