#!/usr/bin/env bash
# One existing Dana DIAG only; F2 from actual compiled 012-C; same object/cache.
set -eo pipefail
if [[ "$(printenv DANA_F2_INPLACE_AUTHORIZED 2>/dev/null || true)" != YES ]]; then
  echo "HOLD: new T/Commander authorization required"; exit 2
fi
exec python3 - <<'PY'
import fcntl, hashlib, io, json, os, re, shutil, subprocess, sys, traceback, types, unittest
from pathlib import Path
PIN="09f171b426c7180eea2c244861005176a9c5ac82"
F2="105f882f77251ac3be4ee988f982ed88e64e6baadc775ca02fcd497a8f0df557"
OLD="e8211be78dfb2bf4cdc0ccabd444c97d715dc37d189d4f113f2f1cbf05b573e2"
OLD_BIN="caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37"
BASE=Path("/home/spc/DANA_EMU_ISOLATED")
WORK=BASE/"dana_timer_uart_irq_hmkem769/mame-stage/diag"
MAME=WORK/"source"
SRC=MAME/"src/mame/skeleton/alphasdana.cpp"
BIN=WORK/"bin/dana-diag"
INTERNAL=MAME/"danadiagd"
ARCHIVE=MAME/"build/dana-diag/linux_clang/bin/x64/Debug/mame_danadiag/libmame_danadiag.a"
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
oldsrc=None; oldobj=None; oldinternal=None; oldarchive=None; obj=None
try:
 for p in (WORK,MAME,SRC,BIN,INTERNAL,ARCHIVE,GIT):
  if not p.exists() or p.is_symlink():raise RuntimeError("UNEXPECTED_CANONICAL_PATH:"+str(p))
 if hashfile(SRC)!=OLD or hashfile(BIN)!=OLD_BIN:
  raise RuntimeError("CURRENT_DIAG_NOT_AT_QUALIFIED_BASELINE")
 objects=list((MAME/"build/dana-diag").rglob("alphasdana.o"))
 if len(objects)!=1:raise RuntimeError("NOT_ONE_DANA_DRIVER_OBJECT")
 obj=objects[0]
 if obj.is_symlink():raise RuntimeError("OBJECT_IS_SYMLINK")
 # The existing repository is accessed read-only except fetching the pinned
 # commit, with no checkout, no branch switch and no second worktree.
 if subprocess.run(["git","-C",str(GIT),"cat-file","-e",PIN+"^{commit}"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  cmd("fetch_existing_git",["git","-C",str(GIT),"fetch","--depth=1","origin",PIN],timeout=300)
 fresh=subprocess.check_output(["git","-C",str(GIT),"show",PIN+":src/mame/skeleton/alphasdana.cpp"])
 if hashbytes(fresh)!=F2 or b"UART1CTS" in fresh:raise RuntimeError("PINNED_F2_SOURCE_MISMATCH")
 oldsrc,oldobj,oldinternal,oldarchive=SRC.read_bytes(),obj.read_bytes(),INTERNAL.read_bytes(),ARCHIVE.read_bytes()
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
 if hashfile(obj)==hashbytes(oldobj) or hashfile(INTERNAL)==hashbytes(oldinternal):
  raise RuntimeError("NO_NEW_F2_OBJECT_OR_DIAG")
 if hashfile(ARCHIVE)==hashbytes(oldarchive):
  raise RuntimeError("NO_UPDATED_DIAG_LIBRARY_ARCHIVE")
 state.update(status="COMPILE_PASS",candidate_object_sha=hashfile(obj),
              candidate_DIAG_sha=hashfile(INTERNAL))
 save()
 testcode=subprocess.check_output(["git","-C",str(GIT),"show",
         PIN+":tests/dana_f2_012c_contract_test.py"])
 module=types.ModuleType("dana_f2_012c_contract_test")
 module.__file__=str(GIT/"tests/dana_f2_012c_contract_test.py")
 exec(compile(testcode,module.__file__,"exec"),module.__dict__)
 module.DRIVER=SRC
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(module.DanaF2FromQualified012C)
 if suite.countTestCases()!=2:raise RuntimeError("EXPECTED_2_TRUE_F2_DIRECTED_CASES")
 output=io.StringIO()
 result=unittest.TextTestRunner(stream=output,verbosity=2).run(suite)
 (EV/"F2_production_methods.log").write_text(output.getvalue())
 state["directed_tests"]={"cases":result.testsRun,"failures":len(result.failures),"errors":len(result.errors)}
 if not result.wasSuccessful():raise RuntimeError("F2_DIRECTED_TEST_FAIL")
 state["status"]="F2_012C_COMPILE_AND_TWO_SOURCE_TESTS_PASS_NATIVE_PENDING"
except Exception as error:
 state["status"]="BLOCKED";state["error"]=str(error)
 (EV/"F2_error_trace.log").write_text(traceback.format_exc()[-24000:])
finally:
 # Back up only in RAM, restore the SAME canonical binary/object/source.
 # F2 is not promoted without native pen-contact and ADC observation.
 if oldsrc is not None:SRC.write_bytes(oldsrc)
 if oldobj is not None:obj.write_bytes(oldobj)
 if oldinternal is not None:INTERNAL.write_bytes(oldinternal)
 if oldarchive is not None:ARCHIVE.write_bytes(oldarchive)
 state["original_DIAG_binary_preserved"]=hashfile(BIN)==OLD_BIN
 state["original_DIAG_source_restored"]=hashfile(SRC)==OLD
 state["original_object_restored"]=(obj is None or oldobj is None or hashfile(obj)==hashbytes(oldobj))
 state["original_archive_restored"]=(oldarchive is None or hashfile(ARCHIVE)==hashbytes(oldarchive))
 state["original_linker_output_restored"]=(oldinternal is None or hashfile(INTERNAL)==hashbytes(oldinternal))
 if not all(state[k] for k in ("original_DIAG_binary_preserved","original_DIAG_source_restored",
       "original_object_restored","original_archive_restored","original_linker_output_restored")):
  state["status"]="ROLLBACK_INTEGRITY_FAIL"
 save()
 lock.close()
print(json.dumps({"status":state["status"],"record":str(REPORT),"native_F2":"PENDING"}))
if state["status"] in ("BLOCKED","ROLLBACK_INTEGRITY_FAIL"):sys.exit(2)
PY
