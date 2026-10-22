#!/usr/bin/env bash
# One existing Dana DIAG only. No tree copies, clone, or alternative target.
set -eo pipefail
if [[ "$(printenv DANA_F2_INPLACE_AUTHORIZED 2>/dev/null || true)" != YES ]]; then
  echo "HOLD: new T/Commander authorization required"; exit 2
fi
exec python3 - <<'PY'
import fcntl, hashlib, io, json, os, re, shutil, subprocess, sys, traceback, types, unittest
from pathlib import Path
PIN="78be96c5615c4b929a96c9dc835b9fff3a2161aa"
F2="4841e227b7a12798517cc4220ae40c22450022c0f9a954d873581bd0fb4d5f0d"
OLD="e8211be78dfb2bf4cdc0ccabd444c97d715dc37d189d4f113f2f1cbf05b573e2"
OLD_BIN="caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37"
BASE=Path("/home/spc/DANA_EMU_ISOLATED")
WORK=BASE/"dana_timer_uart_irq_hmkem769/mame-stage/diag"
MAME=WORK/"source"
SRC=MAME/"src/mame/skeleton/alphasdana.cpp"
BIN=WORK/"bin/dana-diag"
INTERNAL=MAME/"danadiagd"
GIT=Path("/home/spc/Projects/alphasmart/DANA-emu")
EV=BASE/"DIAG_EVIDENCE_ARCHIVE"
REPORT=EV/"F2_ONE_ACTIVE_DIAG_RESULT.json"
def hashfile(p):
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()
def hashbytes(b):return hashlib.sha256(b).hexdigest()
if not EV.is_dir() or EV.is_symlink():raise SystemExit("Missing canonical evidence dir")
lock=(EV/".one_active_dana_diag.lock").open("a+")
fcntl.flock(lock.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
state={"scope":"F2_STYLUS_SINGLE_DIAG","source_commit":PIN,"status":"PREFLIGHT",
       "active_binary":str(BIN),"new_DIAG_trees":0,"ROM_builds":0,
       "full_MAME_rebuilds":0,"tests":[],"native_F2":"NOT_PROVEN"}
def save():REPORT.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
def cmd(label,args,**opts):
 log=EV/("F2_"+label+".log")
 with log.open("wb") as f:
  try:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=opts.pop("timeout",900),**opts).returncode
  except subprocess.TimeoutExpired:r=124
 state["tests"].append({"name":label,"exit":r,"log":str(log)})
 save()
 if r:raise RuntimeError("FAILED_"+label+":"+str(r))
original_head=None; oldsrc=None; oldobj=None; oldinternal=None
try:
 for p in (WORK,MAME,SRC,BIN,INTERNAL,GIT):
  if not p.exists() or p.is_symlink():raise RuntimeError("UNEXPECTED_CANONICAL_PATH:"+str(p))
 if hashfile(SRC)!=OLD or hashfile(BIN)!=OLD_BIN:
  raise RuntimeError("CURRENT_DIAG_NOT_AT_QUALIFIED_BASELINE")
 objects=list((MAME/"build/dana-diag").rglob("alphasdana.o"))
 if len(objects)!=1:raise RuntimeError("NOT_ONE_DANA_DRIVER_OBJECT")
 obj=objects[0]
 if obj.is_symlink():raise RuntimeError("OBJECT_IS_SYMLINK")
 if subprocess.check_output(["git","-C",str(GIT),"status","--porcelain"],text=True).strip():
  raise RuntimeError("GIT_HAS_UNCOMMITTED_WORK_DO_NOT_OVERWRITE")
 original_head=subprocess.check_output(["git","-C",str(GIT),"rev-parse","HEAD"],text=True).strip()
 if subprocess.run(["git","-C",str(GIT),"cat-file","-e",PIN+"^{commit}"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  cmd("fetch_existing_git",["git","-C",str(GIT),"fetch","--depth=1","origin",PIN],timeout=300)
 fresh=subprocess.check_output(["git","-C",str(GIT),"show",PIN+":src/mame/skeleton/alphasdana.cpp"])
 if hashbytes(fresh)!=F2 or b"UART1CTS" in fresh:raise RuntimeError("PINNED_F2_SOURCE_MISMATCH")
 if original_head!=PIN:cmd("switch_existing_checkout",["git","-C",str(GIT),"switch","--detach",PIN])
 oldsrc,oldobj,oldinternal=SRC.read_bytes(),obj.read_bytes(),INTERNAL.read_bytes()
 SRC.write_bytes(fresh)
 cc=shutil.which("clang-21") or shutil.which("clang")
 cxx=shutil.which("clang++-21") or shutil.which("clang++")
 if not cc or not cxx or "clang version 21." not in subprocess.check_output([cxx,"--version"],text=True):
  raise RuntimeError("EXPECTED_COMPILER_NOT_AVAILABLE")
 make=["make","-j3","TARGET=mame","SUBTARGET=danadiag","SOURCES=src/mame/skeleton/alphasdana.cpp",
       "BUILDDIR=build/dana-diag","TOOLS=0","DEBUG=1","PRECOMPILE=0","USE_QTDEBUG=0",
       "OVERRIDE_CC="+cc,"OVERRIDE_CXX="+cxx,"OVERRIDE_LD="+cxx]
 env=dict(os.environ,CC=cc,CXX=cxx,LD=cxx)
 env.pop("REGENIE",None)
 cmd("dryrun",["make","-n"]+make[1:],cwd=MAME,env=env,timeout=300)
 planned=[line for line in (EV/"F2_dryrun.log").read_text(errors="replace").splitlines()
          if re.search(r"(?:^|\s)-c(?:\s|$)",line)]
 if len(planned)!=1 or "alphasdana.cpp" not in planned[0]:
  raise RuntimeError("NOT_ONE_INCREMENTAL_OBJECT")
 state["status"]="BUILD_STARTED";save()
 cmd("compile_and_link",make,cwd=MAME,env=env,timeout=5400)
 if hashfile(obj)==hashbytes(oldobj) or hashfile(INTERNAL)==OLD_BIN:
  raise RuntimeError("NO_NEW_F2_OBJECT_OR_DIAG")
 state.update(status="COMPILE_PASS",candidate_object_sha=hashfile(obj),
              candidate_DIAG_sha=hashfile(INTERNAL))
 save()
 testcode=subprocess.check_output(["git","-C",str(GIT),"show",PIN+":tests/dana_hardware_test.py"])
 sys.path[:0]=[str(GIT/"tests"),str(GIT/"tools")]
 module=types.ModuleType("dana_f2_source_test")
 module.__file__=str(GIT/"tests/dana_hardware_test.py")
 exec(compile(testcode,module.__file__,"exec"),module.__dict__)
 module.DRIVER=SRC
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.Hardware)
 if suite.countTestCases()!=6:raise RuntimeError("EXPECTED_6_EXISTING_DIRECTED_CASES")
 output=io.StringIO()
 result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
 (EV/"F2_production_methods.log").write_text(output.getvalue())
 state["directed_tests"]={"cases":result.testsRun,"failures":len(result.failures),"errors":len(result.errors)}
 if not result.wasSuccessful():raise RuntimeError("F2_DIRECTED_TEST_FAIL")
 state["status"]="COMPILE_AND_SIX_SOURCE_TESTS_PASS_NATIVE_F2_PENDING"
except Exception as error:
 state["status"]="BLOCKED";state["error"]=str(error)
 (EV/"F2_error_trace.log").write_text(traceback.format_exc()[-24000:])
finally:
 # Back up only in RAM, restore the SAME canonical binary/object/source.
 # F2 is not promoted without native pen-contact and ADC observation.
 if oldsrc is not None:SRC.write_bytes(oldsrc)
 if oldobj is not None:obj.write_bytes(oldobj)
 if oldinternal is not None:INTERNAL.write_bytes(oldinternal)
 if original_head and original_head!=PIN:
  p=subprocess.run(["git","-C",str(GIT),"switch","--detach",original_head],
                   stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True)
  if p.returncode:state["git_restore_error"]=p.stderr[-2000:]
 state["original_DIAG_binary_preserved"]=hashfile(BIN)==OLD_BIN
 state["original_DIAG_source_restored"]=hashfile(SRC)==OLD
 save()
 lock.close()
print(json.dumps({"status":state["status"],"record":str(REPORT),"native_F2":"PENDING"}))
if state["status"]=="BLOCKED":sys.exit(2)
PY
