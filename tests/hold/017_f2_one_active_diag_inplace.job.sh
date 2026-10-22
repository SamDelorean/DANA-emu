#!/usr/bin/env bash
# One existing Dana DIAG only; F2 from actual compiled 012-C; same object/cache.
set -eo pipefail
if [[ "$(printenv DANA_F2_INPLACE_AUTHORIZED 2>/dev/null || true)" != YES ]]; then
  echo "HOLD: new T/Commander authorization required"; exit 2
fi
exec python3 - <<'PY'
import fcntl, hashlib, io, json, os, re, shlex, shutil, subprocess, sys, traceback, types, unittest
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
oldsrc=None; oldobj=None; oldinternal=None; oldarchive=None; oldbin=None; obj=None
dep=None; olddep=None; original_times={}
OBS_PIN="c92b256c21161a00d07c29f5fd08a3fb84bee9e6"
OBS_BLOB="a775debd5ac146e875a89d8c0f35024cfd6ee9ea"
OBS_PATH=EV/"F2_native_mmio.lua"
OBS_RESULT=EV/"F2_native_mmio_result.txt"
try:
 for p in (WORK,MAME,SRC,BIN,INTERNAL,ARCHIVE,GIT):
  if not p.exists() or p.is_symlink():raise RuntimeError("UNEXPECTED_CANONICAL_PATH:"+str(p))
 if hashfile(SRC)!=OLD or hashfile(BIN)!=OLD_BIN:
  raise RuntimeError("CURRENT_DIAG_NOT_AT_QUALIFIED_BASELINE")
 objects=list((MAME/"build/dana-diag").rglob("alphasdana.o"))
 if len(objects)!=1:raise RuntimeError("NOT_ONE_DANA_DRIVER_OBJECT")
 obj=objects[0]
 if obj.is_symlink():raise RuntimeError("OBJECT_IS_SYMLINK")
 dep=obj.with_suffix(".d")
 if dep.is_symlink():raise RuntimeError("OBJECT_DEPENDENCIES_ARE_SYMLINK")
 olddep=dep.read_bytes() if dep.exists() else None
 # The existing repository is accessed read-only except fetching the pinned
 # commit, with no checkout, no branch switch and no second worktree.
 if subprocess.run(["git","-C",str(GIT),"cat-file","-e",PIN+"^{commit}"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  cmd("fetch_existing_git",["git","-C",str(GIT),"fetch","--depth=1","origin",PIN],timeout=300)
 fresh=subprocess.check_output(["git","-C",str(GIT),"show",PIN+":src/mame/skeleton/alphasdana.cpp"])
 if hashbytes(fresh)!=F2 or b"UART1CTS" in fresh:raise RuntimeError("PINNED_F2_SOURCE_MISMATCH")
 original_times={str(p):(p.stat().st_atime_ns,p.stat().st_mtime_ns)
     for p in (SRC,obj,INTERNAL,ARCHIVE,BIN) }
 if dep.exists():
  original_times[str(dep)]=(dep.stat().st_atime_ns,dep.stat().st_mtime_ns)
 oldsrc,oldobj,oldinternal,oldarchive,oldbin=SRC.read_bytes(),obj.read_bytes(),INTERNAL.read_bytes(),ARCHIVE.read_bytes(),BIN.read_bytes()
 if not oldbin or hashbytes(oldbin)!=OLD_BIN:
  raise RuntimeError("INSTALL_DIAG_BACKUP_HASH_MISMATCH")
 # Pin the diagnostic Lua code to a known independent Git commit and verify
 # Git blob identity. This is an observer, NOT another emulator binary.
 if subprocess.run(["git","-C",str(GIT),"cat-file","-e",OBS_PIN+"^{commit}"],
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  cmd("fetch_observer_pin",["git","-C",str(GIT),"fetch","--depth=1","origin",OBS_PIN],timeout=300)
 obs_bytes=subprocess.check_output(["git","-C",str(GIT),"show",
     OBS_PIN+":tests/dana_f2_native_mmio.lua"])
 obs_git_hash=subprocess.check_output(["git","-C",str(GIT),"hash-object","--stdin"],
     input=obs_bytes,text=False).decode().strip()
 if obs_git_hash!=OBS_BLOB or b"PASS_HOST_NATIVE_MMIO_ONLY" not in obs_bytes:
  raise RuntimeError("F2_NATIVE_OBSERVER_IDENTITY_MISMATCH")
 OBS_PATH.write_bytes(obs_bytes)
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
 # Reuse the exact generated 012-C MAME compile command. Global OPTIMIZE=0
 # regenerates/changes more project settings, so NEVER pass it to make.
 # Substitute ONLY -O3 -> -O0 for this one driver translation unit.
 gmake_dir=MAME/"build/dana-diag/projects/sdl/mamedanadiag/gmake-linux-clang"
 if not gmake_dir.is_dir() or gmake_dir.is_symlink():
  raise RuntimeError("GENERATED_GMAKE_DIRECTORY_NOT_FOUND")
 driver_cmd=shlex.split(planned[0])
 if len(driver_cmd)>180 or len(driver_cmd)<25:
  raise RuntimeError("DRIVER_COMMAND_UNEXPECTED_SIZE")
 if Path(driver_cmd[0]).resolve()!=Path(cxx).resolve():
  raise RuntimeError("DRIVER_COMPILER_UNEXPECTED")
 if driver_cmd.count("-c")!=1 or driver_cmd.count("-o")!=1:
  raise RuntimeError("DRIVER_C_OR_O_ARGUMENT_MISSING")
 if driver_cmd.count("-O3")!=1 or any(flag in driver_cmd for flag in ("-O0","-O1","-O2","-Os","-Oz")):
  raise RuntimeError("EXPECTED_EXACTLY_ONE_O3_OPTIMIZATION_FLAG")
 if (gmake_dir/driver_cmd[driver_cmd.index("-c")+1]).resolve()!=SRC.resolve():
  raise RuntimeError("DRIVER_C_SOURCE_NOT_CANONICAL")
 if (gmake_dir/driver_cmd[driver_cmd.index("-o")+1]).resolve()!=obj.resolve():
  raise RuntimeError("DRIVER_OUTPUT_NOT_CANONICAL_OBJECT")
 if not all(flag in driver_cmd for flag in ("-MMD","-MP","-std=c++20")):
  raise RuntimeError("MAME_COMPILER_DEPENDENCY_OR_ABI_OPTIONS_MISSING")
 # Replace exactly one optimization token; every include path, generated flag,
 # C++ ABI option, object destination and input remains byte-for-byte equal.
 driver_o0=driver_cmd.copy()
 driver_o0[driver_o0.index("-O3")]="-O0"
 state["exact_driver_compile_changes"]=[{"before":"-O3","after":"-O0"}]
 state["driver_command_O0"]=driver_o0
 state["status"]="CLANG21_ONLY_ALPHASDANA_O0_STARTED";save()
 cmd("compile_driver_O0_only",driver_o0,cwd=gmake_dir,env=env,timeout=1800)
 if hashfile(obj)==hashbytes(oldobj):
  raise RuntimeError("NO_NEW_F2_OBJECT_AFTER_DRIVER_O0")
 # A second read-only Make plan must have ZERO C++ source compiles, i.e.,
 # only the existing archive and linker work may be required.
 cmd("post_driver_dryrun",["make","-n"]+make[1:],cwd=MAME,env=env,timeout=300)
 remaining=(EV/"F2_post_driver_dryrun.log").read_text(errors="replace")
 recompiles=[line for line in remaining.splitlines()
    if re.search(r"(?:^|\s)-c(?:\s|$)",line)]
 if recompiles:
  raise RuntimeError("POST_DRIVER_PLAN_WOULD_COMPILE_MORE_OBJECTS")
 if "Archiving libmame_danadiag.a" not in remaining:
  raise RuntimeError("EXPECTED_ONE_DRIVER_ARCHIVE_REBUILD_NOT_PLANNED")
 state["status"]="CLANG21_O0_DRIVER_PASS_LINK_EXISTING_DIAG_STARTED";save()
 cmd("archive_and_link_only",make,cwd=MAME,env=env,timeout=1800)
 link_log=(EV/"F2_archive_and_link_only.log").read_text(errors="replace")
 if "Compiling src/mame/skeleton/alphasdana.cpp" in link_log:
  raise RuntimeError("UNEXPECTED_DRIVER_RECOMPILATION_IN_LINK_STAGE")
 state["compiler_optimization_override"]="DRIVER_ONLY_O0_OTHER_OBJECTS_UNCHANGED"
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
 state["status"]="F2_COMPILED_SOURCE_TEST_PASS_NATIVE_MMIO_STARTING";save()
 # Use the ONE canonical installed DIAG path for a native hardware run.
 # All original binary bytes were retained in memory. No second version.
 BIN.write_bytes(INTERNAL.read_bytes())
 if hashfile(BIN)!=hashfile(INTERNAL):
  raise RuntimeError("CANDIDATE_NOT_INSTALLED_IN_CANONICAL_DIAG")
 if OBS_RESULT.exists():OBS_RESULT.unlink()
 run_env=dict(os.environ,DANA_F2_MMIO_RESULT=str(OBS_RESULT))
 native=[str(BIN),"asmdana","-noreadconfig","-autoboot_script",str(OBS_PATH),
         "-video","none","-sound","none","-skip_gameinfo","-seconds_to_run","2"]
 state["native_command"]=native
 state["native_binary_sha256"]=hashfile(BIN)
 save()
 cmd("native_mmio",native,cwd=EV,env=run_env,timeout=120)
 if not OBS_RESULT.is_file():
  raise RuntimeError("NO_REAL_MAME_LUA_MMIO_RESULT")
 reported=OBS_RESULT.read_text()
 state["native_mmio_receipt"]=reported[:3000]
 if "status=PASS_HOST_NATIVE_MMIO_ONLY" not in reported or "origin=HOST_LUA_NOT_GUEST_CPU" not in reported:
  raise RuntimeError("REAL_NATIVE_MMIO_NOT_QUALIFIED")
 state["native_F2"]="PASS_HOST_NATIVE_MMIO_ONLY_NOT_GUEST"
 state["status"]="F2_COMPILE_SOURCE_TESTS_NATIVE_HOST_MMIO_PASS_NOT_GUEST"

except Exception as error:
 state["status"]="BLOCKED";state["error"]=str(error)
 (EV/"F2_error_trace.log").write_text(traceback.format_exc()[-24000:])
finally:
 # Restore the SAME canonical DIAG source/object/archive/linker output/installed binary in RAM.
 # F2 is not promoted without native pen-contact and ADC observation.
 if oldsrc is not None:SRC.write_bytes(oldsrc)
 if oldobj is not None:obj.write_bytes(oldobj)
 if oldinternal is not None:INTERNAL.write_bytes(oldinternal)
 if oldarchive is not None:ARCHIVE.write_bytes(oldarchive)
 if oldbin is not None:BIN.write_bytes(oldbin)
 if dep is not None:
  if olddep is not None:dep.write_bytes(olddep)
  elif oldobj is not None and dep.exists():dep.unlink()
 # Metadata also matters: touching old source and old object leaves make
 # dependency timestamps inconsistent, prompting unintended recompilation.
 for path in (SRC,obj,INTERNAL,ARCHIVE,BIN,dep):
  if path is not None and str(path) in original_times and path.exists():
   os.utime(path,ns=original_times[str(path)])
 state["original_DIAG_binary_preserved"]=hashfile(BIN)==OLD_BIN
 state["original_DIAG_source_restored"]=hashfile(SRC)==OLD
 state["original_object_restored"]=(obj is None or oldobj is None or hashfile(obj)==hashbytes(oldobj))
 state["original_archive_restored"]=(oldarchive is None or hashfile(ARCHIVE)==hashbytes(oldarchive))
 state["original_linker_output_restored"]=(oldinternal is None or hashfile(INTERNAL)==hashbytes(oldinternal))
 state["original_dependency_file_restored"]=(dep is None or
     (olddep is None and not dep.exists()) or
     (olddep is not None and dep.exists() and hashfile(dep)==hashbytes(olddep)))
 state["original_build_timestamps_restored"]=all(
      Path(p).exists() and Path(p).stat().st_mtime_ns==stamp[1]
      for p,stamp in original_times.items())
 if oldbin is not None:state["binary_byte_for_byte_restored"]=(hashfile(BIN)==hashbytes(oldbin))
 else:state["binary_byte_for_byte_restored"]=True
 if not all(state[k] for k in ("binary_byte_for_byte_restored","original_DIAG_binary_preserved","original_DIAG_source_restored",
       "original_object_restored","original_archive_restored","original_linker_output_restored",
       "original_dependency_file_restored","original_build_timestamps_restored")):
  state["status"]="ROLLBACK_INTEGRITY_FAIL"
 save()
 lock.close()
print(json.dumps({"status":state["status"],"record":str(REPORT),"native_F2":state["native_F2"]}))
if state["status"] in ("BLOCKED","ROLLBACK_INTEGRITY_FAIL"):sys.exit(2)
PY
