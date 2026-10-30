#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Original UK1.5 USB application run in the sole canonical MAME tree."""
import argparse,hashlib,json,os,shutil,socket,subprocess,time
from pathlib import Path
from PIL import Image
from isp1161_virtual_host import USBHost,ACK
def main():
 p=argparse.ArgumentParser();p.add_argument("--installed",action="store_true")
 p.add_argument("--case",required=True);p.add_argument("--mode",choices=["printer","device"],default="printer")
 p.add_argument("--require-original-device",action="store_true");p.add_argument("--interactive",action="store_true");args=p.parse_args();assert args.case.replace("-","").replace("_","").isalnum()
 root=Path(__file__).resolve().parents[1];binary=root/("runtime/diag/bin/dana-diag"if args.installed else"runtime/diag/source/danadiagd")
 folder=root/"local-evidence/runtime-compare/usb-20261030"/args.case;folder.mkdir(parents=True,exist_ok=False)
 cfg=folder/"cfg";cfg.mkdir()
 for name in ["asmdana.cfg","default.cfg"]:shutil.copy2(root/"config/palm-uk15"/name,cfg/name)
 env=os.environ.copy();env.update(SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy",DANA_REPO_ROOT=str(root),
  DANA_USB_INTERACTIVE="1"if args.interactive else"0",DANA_LCD_DUMP_DIR=str(folder),DANA_USB_MODE=args.mode,DANA_TRACE_FILE=str(folder/"trace.txt"))
 cmd=[str(binary),"asmdana","-rom",str(root/"runtime/diag/work/uk15_qualify_20261025/UK15_private.raw"),
  "-cfg_directory",str(cfg),"-video","none","-nothrottle","-skip_gameinfo","-nowriteconfig",
  "-autoboot_script",str(root/"tests/palm_uk15_usb_application.lua"),"-autoboot_delay","0","-oslog","-log",
  "-wavwrite",str(folder/"audio.wav"),"-lightgun","-lightgun_device","lightgun","-lightgunprovider","sdl","-nomouse"]
 listener=None
 if args.mode=="printer":
  (folder/"alphaword.prn").write_bytes(b"");cmd+=["-prin1",str(folder/"alphaword.prn")]
 else:
  listener=socket.socket();listener.bind(("127.0.0.1",0));listener.listen(1);listener.settimeout(15)
  (folder/"computer.usb").write_text("socket.127.0.0.1:%d\n"%listener.getsockname()[1])
  cmd+=["-usbcomputer",str(folder/"computer.usb")]
 report={"original_device_softconnect":False,"mode":args.mode,"binary_sha256":hashlib.sha256(binary.read_bytes()).hexdigest()}
 with(folder/"run.out").open("w")as log:
  process=subprocess.Popen(cmd,cwd=root/"runtime/diag",env=env,stdout=log,stderr=subprocess.STDOUT)
  try:
   if listener:
    connection,_=listener.accept()
    with connection:
     connection.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
     host=USBHost(connection);host.connect();enumerated=False
     while process.poll()is None:
      try:
       status,n,meta=host.packet(0x10)
       if len(meta)==8 and(meta[1]&1):report["original_device_softconnect"]=True
       (folder/"upstream-state.json").write_text(json.dumps({"status":status,"metadata":meta.hex()})+"\n")
       if not enumerated and len(meta)==8 and(meta[1]&1)and meta[3]:
        host.reset();time.sleep(.02)
        status,device=host.control(0x80,6,0x100,length=18);assert status==ACK and len(device)==18
        assert host.control(0,5,5)[0]==ACK
        status,header=host.control(0x80,6,0x200,length=9);assert status==ACK and len(header)==9
        total=int.from_bytes(header[2:4],"little")
        status,configuration=host.control(0x80,6,0x200,length=total);assert status==ACK and len(configuration)==total
        assert host.control(0,9,configuration[5])[0]==ACK
        report["original_device_descriptor"]=device.hex();report["original_configuration_descriptor"]=configuration.hex()
        report["enumeration"]="ORIGINAL_FIRMWARE_PASS";enumerated=True
        (folder/"enumeration.json").write_text(json.dumps(report,indent=2)+"\n")
      except(ConnectionError,TimeoutError,OSError):break
      time.sleep(.05)
     (folder/"host-packets.json").write_text(json.dumps(host.trace,indent=2)+"\n")
   process.wait(timeout=1200 if args.interactive else 120)
  finally:
   if listener:listener.close()
   if process.poll()is None:
    process.terminate()
    try:process.wait(timeout=3)
    except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
 report["returncode"]=process.returncode
 for fb in folder.glob("calib_*.bin"):Image.frombytes("1",(560,160),fb.read_bytes()).save(fb.with_suffix(".png"))
 text=(folder/"run.out").read_text()
 report["blocked"]=[line for line in text.splitlines()if"DANA_PHYSICAL_BLOCKED"in line]
 if args.mode=="printer":
  data=(folder/"alphaword.prn").read_bytes()
  report["print_bytes"]=len(data);report["print_sha256"]=hashlib.sha256(data).hexdigest()
  report["contains_test_phrase"]=b"DANA USB 123"in data
  report["postscript_complete"]=data.startswith(b"%!")and data.rstrip().endswith(b"%%EOF")
 report["status"]="ORIGINAL_ALPHAWORD_USB_PRINT_PASS"if args.mode=="printer"and report["contains_test_phrase"]and report["postscript_complete"]else"PROBE_ONLY"
 if args.mode=="device":
  report["status"]="ORIGINAL_DEVICE_ENUM_PASS"if report.get("enumeration")=="ORIGINAL_FIRMWARE_PASS"else"PENDING_ORIGINAL_DEVICE"
  report["hotsync_e2e"]="PENDING"
 (folder/"probe.json").write_text(json.dumps(report,indent=2)+"\n")
 print(json.dumps(report,indent=2))
 if report["returncode"]or report["blocked"]or"[LUA ERROR]"in text or(args.mode=="printer"and not args.interactive and report["status"]!="ORIGINAL_ALPHAWORD_USB_PRINT_PASS"):raise SystemExit(1)
 if args.require_original_device and report["status"]!="ORIGINAL_DEVICE_ENUM_PASS":raise SystemExit(2)
if __name__=="__main__":main()
