#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""One complete original-Palm keyboard campaign on the canonical Dana emulator.
No build, installation, ROM change, branches or external media modifications.
"""
import argparse,hashlib,json,os,re,subprocess,sys
from pathlib import Path
from st81_full_keyboard_native import inventory

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--candidate",action="store_true",help="Existing source/danadiagd build artifact; default is installed dana-diag")
 p.add_argument("--prefix",required=True)
 args=p.parse_args()
 assert re.fullmatch("[A-Za-z0-9_-]+",args.prefix)
 root=Path(__file__).resolve().parents[1]
 evidence=root/"local-evidence/runtime-compare/keyboard-20261030"
 evidence.mkdir(exist_ok=True,parents=True)
 record=evidence/(args.prefix+"-campaign")
 record.mkdir(exist_ok=False)
 env=os.environ.copy();env["TMPDIR"]=str(record)
 binary=root/("runtime/diag/source/danadiagd"if args.candidate else "runtime/diag/bin/dana-diag")
 digest=hashlib.sha256(binary.read_bytes()).hexdigest()
 def run(name,command):
  print("RUN",name,flush=True)
  result=subprocess.run(command,cwd=root,env=env,capture_output=True,text=True,timeout=180)
  (record/(name+".out")).write_text(result.stdout+result.stderr)
  print(result.stdout[-1800:]+result.stderr[-1000:],flush=True)
  assert result.returncode==0,name+" failed; inspect private campaign output"
 def native(name,script):
  command=[sys.executable,"-u",str(root/"tests/run_host_calendar_native.py"),"--case",args.prefix+"-"+name,"--script",script]
  if args.candidate:command+=["--candidate"]
  run(name,command)
 for name in ["st_irq1_protocol_test.py","sdl_monitor_geometry_test.py","rtc_uk15_test.py","host_calendar_test.py"]:
  run(name,[sys.executable,str(root/"tests"/name)])
 native("application","tests/palm_uk15_keyboard_native.lua")
 app=root/"local-evidence/runtime-compare/calendar-host"/(args.prefix+"-application")
 env["DANA_KEYBOARD_STATE"]=str(app/"alphaword-clean.sta")
 assert Path(env["DANA_KEYBOARD_STATE"]).exists()
 keys=inventory((root/"src/mame/skeleton/alphasdana.cpp").read_text())
 encoded="return {"+",".join("{tag="+json.dumps(":"+tag)+",name="+json.dumps(name)+",scan="+str(scan)+",mask="+str(mask)+"}"for tag,name,scan,mask in keys)+"}\n"
 (record/"inventory.lua").write_text(encoded);env["DANA_KEYBOARD_INVENTORY"]=str(record/"inventory.lua")
 native("all81","tests/palm_uk15_keyboard_all81.lua")
 native("robust","tests/palm_uk15_keyboard_robust.lua")
 native("sound-controls","tests/palm_uk15_sound_controls_native.lua")
 compatibility=[sys.executable,"-u",str(root/"tests/keyboard_regression_native.py"),"--case",args.prefix+"-compatibility"]
 if not args.candidate:compatibility+=["--installed"]
 run("compatibility",compatibility)
 sdl=[sys.executable,"-u",str(root/"tests/palm_keyboard_x11_session.py")]
 if not args.candidate:sdl+=["--installed"]
 run("sdl",sdl)
 cases=root/"local-evidence/runtime-compare/calendar-host"
 all81=json.loads((cases/(args.prefix+"-all81")/"all81.json").read_text())
 robust=json.loads((cases/(args.prefix+"-robust")/"robust.json").read_text())
 compatibility=json.loads((evidence/(args.prefix+"-compatibility")/"result.json").read_text())
 sdl_result=json.loads((evidence/("sdl-candidate"if args.candidate else "sdl-installed")/"sdl-result.json").read_text())
 assert len(all81["seen"])==81 and not all81["missing"]and not all81["host_missing"]and not all81["release_missing"]
 assert len(all81["chords"])==5 and not robust["stale_modifier"]
 assert hashlib.sha256(binary.read_bytes()).hexdigest()==digest,"Binary changed during qualification"
 sound=(cases/(args.prefix+"-sound-controls")/"calendar.txt").read_text().strip()
 assert sound=="MAME_SOUND_UI_MUTE_AND_RESTORE_PASS"
 result={"status":"NATIVE_PASS","sound_ui_mute_restore":sound,"binary_sha256":digest,"all81":all81,"robustness":robust,
  "compatibility":compatibility,"host_sdl":sdl_result,
  "driver_sha256":hashlib.sha256((root/"src/mame/skeleton/alphasdana.cpp").read_bytes()).hexdigest()}
 (record/"result.json").write_text(json.dumps(result,indent=2)+"\n")
 print("ORIGINAL_PALM_ALPHAWORD_81_KEYBOARD_CAMPAIGN_PASS",flush=True)
 print(json.dumps(result,indent=2),flush=True)
if __name__=="__main__":main()
