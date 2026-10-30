#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Directed compatibility checks using existing D7.5 CPU fixtures and EmuTOS."""
import argparse,hashlib,importlib.util,json,os,subprocess
from pathlib import Path

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--installed",action="store_true")
 parser.add_argument("--case",default="compatibility")
 args=parser.parse_args()
 root=Path(__file__).resolve().parents[1]
 binary=root/("runtime/diag/bin/dana-diag"if args.installed else "runtime/diag/source/danadiagd")
 evidence=root/"local-evidence/runtime-compare/keyboard-20261030"/args.case
 evidence.mkdir(parents=True,exist_ok=False)
 spec=importlib.util.spec_from_file_location("qualified_sd",root/"tests/d7_5_native.py")
 sd=importlib.util.module_from_spec(spec);spec.loader.exec_module(sd)
 cards=[evidence/f"DISPOSABLE_SD{i}.img"for i in range(2)]
 original=[bytes([0x11+i])*16384 for i in range(2)]
 for p,data in zip(cards,original):p.write_bytes(data)
 results={}
 def execute(command,folder):
  env=os.environ.copy();env.update(SDL_VIDEODRIVER="dummy",SDL_AUDIODRIVER="dummy")
  run=subprocess.run(command,cwd=root/"runtime/diag",env=env,capture_output=True,text=True,timeout=90)
  text=run.stdout+run.stderr;(folder/"run.out").write_text(text)
  assert run.returncode==0 and "[LUA ERROR]"not in text and "DANA_PHYSICAL_BLOCKED"not in text,text[-2000:]
 for mode in ["protected","crc","both_write","reopen"]:
  folder=evidence/mode;folder.mkdir()
  package,ranges=sd.fixture(mode);(folder/"guest.dana").write_bytes(package)
  mask=0 if mode=="protected"else 3
  (folder/"observer.lua").write_text(sd.lua_script(folder/"cpu.json",ranges,mask))
  cfg=folder/"cfg";cfg.mkdir()
  ports="".join(f'<port tag=":SDWRITE" type="CONFIG" mask="{1<<slot}" defvalue="0" value="{mask&(1<<slot)}"/>'for slot in [0,1])
  (cfg/"asmdana.cfg").write_text('<mameconfig version="10"><system name="asmdana"><input>'+ports+'</input></system></mameconfig>')
  before=[p.read_bytes()for p in cards]
  execute([str(binary),"asmdana","-quickload",str(folder/"guest.dana"),"-sd1",str(cards[0]),"-sd2",str(cards[1]),
   "-autoboot_script",str(folder/"observer.lua"),"-autoboot_delay","0","-video","none","-sound","none","-nothrottle",
   "-nowriteconfig","-cfg_directory",str(cfg),"-nvram_directory",str(folder/"nvram"),"-state_directory",str(folder/"states"),"-oslog"],folder)
  result=json.loads((folder/"cpu.json").read_text());assert result["marker"]==0xa55a
  if mode in ["protected","crc"]:assert[p.read_bytes()for p in cards]==before
  else:
   for slot in [0,1]:
    expected=b"".join(bytes((0x31+slot*0x40+extra+i)&255 for i in range(512))for extra in range(3))
    assert bytes.fromhex(result["buffers"][slot])==expected
  results["sd_"+mode]={"status":"PASS","cpu_marker":result["marker"]}
 guest=root/"local-evidence/legacy-guest/emutos.dana"
 assert hashlib.sha256(guest.read_bytes()).hexdigest()=="c201c8527df87fa6a8788d8ac59f43298666196fefeee12dcac68295cb281b9d"
 folder=evidence/"emutos";folder.mkdir()
 lua=r"""
local m=manager.machine
local cpu=m.devices[":maincpu"];local b=cpu.spaces.program
local frame=0;local seen={};local pending=0;local releases=0;local reads=0;local pcs={}
local tap=b:install_read_tap(0xfffff800,0xfffff801,"emutos_original_st",function(a,d,k)
 local op=b:read_u16(cpu.state.CURPC.value)
 if (op&0xf1ff)~=0x3038 and(op&0xf1ff)~=0x3039 then return end
 reads=reads+1;local v=d&255
 if pending>0 then seen[v]=true;pending=pending-1
 elseif v>=0x40 and v<=0x48 then pending=v&15;if pending==0 then releases=releases+1 end end
end)
local a=m.ioport.ports[":KEYS"].fields["A"];local other=m.ioport.ports[":KEYS"].fields["B"];local enter=m.ioport.ports[":KEYS"].fields["Return"]
emu.register_frame_done(function()
 frame=frame+1
 if frame>300 and frame%10==0 then pcs[cpu.state.CURPC.value]=true end
 if frame==400 then a:set_value(1)end;if frame==430 then a:clear_value()end
 if frame==460 then other:set_value(1)end;if frame==480 then other:clear_value()end
 if frame==500 then enter:set_value(1)end;if frame==510 then enter:clear_value()end
 if frame==650 and tap then
  local codes={};for k in pairs(seen)do codes[#codes+1]=k end;table.sort(codes)
  local count=0;for _ in pairs(pcs)do count=count+1 end
  local f=assert(io.open(__RESULT__,"w"));f:write('{"codes":['..table.concat(codes,",")..'],"spi_reads":'..reads..',"releases":'..releases..',"pc_samples_changed":'..count..',"pdsel":'..b:read_u8(0xfffff41b)..',"irq1_pending":'..(b:read_u16(0xfffff310)&1)..'}');f:close();m:exit()
 end
end)
"""
 (folder/"observer.lua").write_text(lua.replace("__RESULT__",json.dumps(str(folder/"emutos.json"))))
 cfg=folder/"cfg";cfg.mkdir()
 execute([str(binary),"asmdana","-quickload",str(guest),"-autoboot_script",str(folder/"observer.lua"),"-autoboot_delay","0",
  "-video","none","-sound","none","-nothrottle","-skip_gameinfo","-nowriteconfig","-cfg_directory",str(cfg),"-oslog"],folder)
 result=json.loads((folder/"emutos.json").read_text())
 assert{43,122,46}.issubset(result["codes"]),result
 assert result["spi_reads"]>50 and result["releases"]>=3 and result["pc_samples_changed"]>1,result
 assert result["irq1_pending"]==0 and result["pdsel"]&0x10,result
 results["emutos"]=result
 results["binary_sha256"]=hashlib.sha256(binary.read_bytes()).hexdigest()
 (evidence/"result.json").write_text(json.dumps(results,indent=2)+"\n")
 print(json.dumps(results,indent=2))
if __name__=="__main__":main()
