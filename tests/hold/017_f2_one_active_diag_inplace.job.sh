#!/usr/bin/env bash
# One existing Dana DIAG only; F2 from actual compiled 012-C; same object/cache.
set -eo pipefail
if [[ "$(printenv DANA_F2_INPLACE_AUTHORIZED 2>/dev/null || true)" != YES ]]; then
  echo "HOLD: new T/Commander authorization required"; exit 2
fi
exec python3 - <<'PY'
import fcntl, hashlib, io, json, os, re, shlex, shutil, subprocess, sys, traceback, types, unittest
from pathlib import Path
PIN="7514e96c9609b0427a2dae8920b544d80c66d397"
F2="f1f3c58efcc51f0f8b190c5d9672c502fbb7d6cddef33a8694d6c1ce7702c42f"
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
OBS_PIN="0db758db6c1be571b1d8f83ce0910c690712f068"
OBS_BLOB="5676f95fce0ee9db6b2ed8154c9fee0d392c7fc9"
OBS_PATH=EV/"F2_native_mmio.lua"
OBS_RESULT=EV/"F2_native_mmio_result.txt"
# Original F1 E1/E2 guest binaries and symbol map are immutable.
GUEST_DIR=BASE/"f1_e1e2_baldoi9k/emutos-built"
GUEST_PKG=GUEST_DIR/"emutos.dana"
GUEST_IMG=GUEST_DIR/"emutos.img"
GUEST_MAP=GUEST_DIR/"emutos.map"
GUEST_MANIFEST=GUEST_DIR/"guest_manifest.json"
GUEST_PIN="44da415eee09e2d41a4fe85a1b573e27999b98af"
GUEST_LUA_BLOB="3df9f26476800e68b8cedb2c6a00c30c8d4eeac7"
GUEST_VERIFY_BLOB="45277d4f28c25672f6cfcc0738e7b1a7e89bbbcf"
GUEST_TEST_BLOB="ff634b119e38c41e3560e1ebb7bb558d7c6a7eaf"
GUEST_LUA=EV/"F2_guest_cpu_observer.lua"
GUEST_VERIFY=EV/"dana_f2_guest_cpu_verify.py"
GUEST_TEST=EV/"test_dana_f2_guest_cpu_verify.py"
GUEST_RESULT=EV/"F2_guest_cpu_observation.json"
GUEST_VERDICT=EV/"F2_guest_cpu_verdict.json"
GUEST_PKG_SHA="c201c8527df87fa6a8788d8ac59f43298666196fefeee12dcac68295cb281b9d"
GUEST_IMG_SHA="ba590da2661bc582c19bb24d65db04667daf37a17d7aa51fb462b945933ba0a3"
GUEST_MAP_SHA="17cc980e675e2e1b50e713b9029f6fc3e51d3e55392deb99d53552d4b3af3e68"
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
 if obs_git_hash!=OBS_BLOB or b"PASS_HOST_NATIVE_MMIO_ONLY" not in obs_bytes or b"emu.add_machine_stop_notifier" not in obs_bytes or b"emu.register_stop" in obs_bytes:
  raise RuntimeError("F2_NATIVE_OBSERVER_IDENTITY_MISMATCH")
 OBS_PATH.write_bytes(obs_bytes)
 # One SDL lightgun input class supplies PEN, X and Y.
 # Existing SDL provider maps window pointer position and button events.
 if b"PORT_CODE(GUNCODE_BUTTON1)" not in fresh or b"PORT_CODE(MOUSECODE_BUTTON1)" in fresh:
  raise RuntimeError("F2_SINGLE_POINTER_TRIGGER_BINDING_NOT_PRESENT")
 if b"IPT_LIGHTGUN_X" not in fresh or b"IPT_LIGHTGUN_Y" not in fresh:
  raise RuntimeError("F2_ABSOLUTE_POINTER_AXES_MISSING")
 sdl=MAME/"src/osd/modules/input/input_sdl.cpp"
 if not sdl.is_file() or sdl.is_symlink():
  raise RuntimeError("PINNED_MAME_SDL_POINTER_PROVIDER_MISSING")
 sdl_text=sdl.read_text(errors="replace")
 for contract in ("class sdl_lightgun_device", "SDL_MOUSEMOTION",
                  "SDL_MOUSEBUTTONDOWN", "normalize_absolute_axis",
                  "DEVICE_CLASS_LIGHTGUN"):
  if contract not in sdl_text:raise RuntimeError("MAME_SDL_INPUT_CONTRACT_MISSING:"+contract)
 state["host_pointer_contract"]="ONE_SDL_LIGHTGUN_CLASS_TRIGGER_AND_ABSOLUTE_AXES_STATIC_PASS"
 # Guest evidence is the original F1 immutable EmuTOS-Dana, not a rebuilt ROM
 # or synthesized subroutine call. Reject changed guest/map before the run.
 for p in (GUEST_DIR,GUEST_PKG,GUEST_IMG,GUEST_MAP,GUEST_MANIFEST):
  if not p.exists() or p.is_symlink():
   raise RuntimeError("F2_GUEST_ARTIFACT_MISSING_OR_LINK:"+str(p))
 for p,expected in ((GUEST_PKG,GUEST_PKG_SHA),(GUEST_IMG,GUEST_IMG_SHA),(GUEST_MAP,GUEST_MAP_SHA)):
  if hashfile(p)!=expected:
   raise RuntimeError("ORIGINAL_EMUTOS_GUEST_HASH_MISMATCH:"+p.name)
 guest_manifest=json.loads(GUEST_MANIFEST.read_text())
 required_symbols={"_os_header":0x2140,"_dana_init":0x827e}
 if any(guest_manifest.get("symbols",{}).get(k)!=v for k,v in required_symbols.items()):
  raise RuntimeError("GUEST_INITIAL_ENTRY_NOT_PINNED")
 if guest_manifest.get("artifacts",{}).get("emutos.img",{}).get("sha256")!=GUEST_IMG_SHA or guest_manifest.get("package",{}).get("sha256")!=GUEST_PKG_SHA:
  raise RuntimeError("GUEST_MANIFEST_IDENTITY_UNBOUND")
 guest_map_text=GUEST_MAP.read_text(errors="replace")
 expected_map_symbols={"_dana_ts_rawread":0x852c,"_dana_poll_touchscreen":0x86a4}
 for name,address in expected_map_symbols.items():
  lines=[line for line in guest_map_text.splitlines()
        if re.search(r"\b"+re.escape(name)+r"$",line.strip())]
  if len(lines)!=1 or not re.search(r"0x0*"+format(address,"x")+r"\s+"+re.escape(name)+r"$",lines[0].strip()):
   raise RuntimeError("GUEST_SYMBOL_MAP_BINDING_MISMATCH:"+name)
 if subprocess.run(["git","-C",str(GIT),"cat-file","-e",GUEST_PIN+"^{commit}"],
                   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:
  cmd("fetch_guest_observer_pin",["git","-C",str(GIT),"fetch","--depth=1","origin",GUEST_PIN],timeout=300)
 for repo_path,blob,path in (
    ("tests/dana_f2_guest_cpu_observer.lua",GUEST_LUA_BLOB,GUEST_LUA),
    ("tests/dana_f2_guest_cpu_verify.py",GUEST_VERIFY_BLOB,GUEST_VERIFY),
    ("tests/dana_f2_guest_cpu_verify_test.py",GUEST_TEST_BLOB,GUEST_TEST)):
  payload=subprocess.check_output(["git","-C",str(GIT),"show",GUEST_PIN+":"+repo_path],timeout=30)
  actual=subprocess.check_output(["git","-C",str(GIT),"hash-object","--stdin"],
         input=payload).decode().strip()
  if actual!=blob:raise RuntimeError("GUEST_INSTRUMENT_IDENTITY_MISMATCH:"+repo_path)
  path.write_bytes(payload)
 if "dana-f2-natural-guest-bus-v1" not in GUEST_LUA.read_text() or "PASS_GUEST_CPU_PEN_X_Y" not in GUEST_VERIFY.read_text():
  raise RuntimeError("GUEST_OBSERVER_VERIFIER_SCOPE_MISMATCH")
 # Synthetic verification of the VERIFIER, not an EmuTOS run or F2 PASS.
 # Fail here without compiling any driver if the checker cannot distinguish
 # complete, incomplete and tampered CPU data.
 state["status"]="GUEST_MAP_AND_VERIFIER_STATIC_CHECK_RUNNING";save()
 cmd("guest_verifier_unit_preflight",["python3","-m","unittest","-v",
          "test_dana_f2_guest_cpu_verify"],cwd=EV,timeout=60)
 state["status"]="GUEST_MAP_AND_VERIFIER_STATIC_PREFLIGHT_PASS";save()
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
 # Use the unchanged MAME-generated Clang command for inputs and linker.
 # GCC15 replaces only the driver .o compiler, not the existing DIAG toolchain.
 gmake_dir=MAME/"build/dana-diag/projects/sdl/mamedanadiag/gmake-linux-clang"
 if not gmake_dir.is_dir() or gmake_dir.is_symlink():
  raise RuntimeError("GENERATED_GMAKE_DIRECTORY_NOT_FOUND")
 driver_cmd=shlex.split(planned[0])
 if not (25<=len(driver_cmd)<=180):
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
 if not all(flag in driver_cmd for flag in ("-MMD","-MP","-std=c++20","-m64","-fno-strict-aliasing")):
  raise RuntimeError("MAME_COMPILER_ABI_OR_DEPENDENCY_OPTIONS_MISSING")
 abi_switches=[x for x in driver_cmd if x.startswith((
       "-D_GLIBCXX_USE_CXX11_ABI","-stdlib=","-fabi-version=",
       "-fno-exceptions","-fno-rtti","-flto","-march=","-mcpu=",
       "-D_LIBCPP_VERSION"))]
 if abi_switches:
  raise RuntimeError("REVIEW_UNEXPECTED_ABI_FLAGS:"+repr(abi_switches))
 gcc=shutil.which("g++-15")
 if not gcc or not subprocess.check_output([gcc,"-dumpfullversion"],text=True,timeout=10).strip().startswith("15."):
  raise RuntimeError("INSTALLED_GCC15_MISSING_OR_CHANGED")
 for compiler in (gcc,cxx):
  if subprocess.check_output([compiler,"-dumpmachine"],text=True,timeout=10).strip().split("-")[0]!="x86_64":
   raise RuntimeError("COMPILER_TARGET_NOT_X86_64:"+compiler)
 # Read-only preprocessor macro check: no C++ source object is compiled.
 headers="#include <string>\n#include <list>\n"
 keys=("_GLIBCXX_USE_CXX11_ABI","_GLIBCXX_RELEASE","__GLIBCXX__",
       "__SIZEOF_POINTER__","__EXCEPTIONS","__GXX_RTTI","__BYTE_ORDER__")
 def abi_macros(compiler):
  out=subprocess.check_output([compiler,"-std=c++20","-dM","-E","-x","c++","-"],
       input=headers,text=True,timeout=45)
  m={}
  for line in out.splitlines():
   if line.startswith("#define "):
    parts=line[len("#define "):].split(maxsplit=1)
    if len(parts)==2:m[parts[0]]=parts[1]
  return {key:m.get(key) for key in keys}
 clang_abi=abi_macros(cxx)
 gcc_abi=abi_macros(gcc)
 if any(clang_abi[k] is None or gcc_abi[k] is None or clang_abi[k]!=gcc_abi[k] for k in keys):
  state.update(clang_abi_macros=clang_abi,gcc_abi_macros=gcc_abi)
  save()
  raise RuntimeError("CLANG_GCC15_CPP_ABI_MACRO_MISMATCH")
 def stdcpp_link(compiler):
  out=subprocess.check_output([compiler,"-print-file-name=libstdc++.so"],
         text=True,timeout=10).strip()
  p=Path(out)
  if not p.is_absolute() or not p.exists():
   raise RuntimeError("LIBSTDCXX_NOT_RESOLVED:"+compiler+":"+out)
  return str(p.resolve())
 clang_stdcpp=stdcpp_link(cxx)
 gcc_stdcpp=stdcpp_link(gcc)
 if clang_stdcpp!=gcc_stdcpp:
  raise RuntimeError("DIFFERENT_CXX_LINK_LIBRARY:"+clang_stdcpp+":"+gcc_stdcpp)
 old_header=oldobj[:20]
 if old_header[:6]!=bytes((127,69,76,70,2,1)) or int.from_bytes(old_header[18:20],"little")!=62:
  raise RuntimeError("BASELINE_OBJECT_NOT_ELF64_X86_64")
 # Remove only the Clang-only flags present in the observed original command.
 # Keep -O3, defines, includes, -Werror, ABI flags and one exact output.
 clang_only=("-fdiagnostics-show-note-include-stack",
      "-Wno-unknown-warning-option","-Wno-constant-logical-operand",
      "-Wno-extern-c-compat","-Wno-pragma-pack","-Wno-unknown-attributes",
      "-Wno-xor-used-as-pow","-Wno-bitwise-instead-of-logical")
 if driver_cmd.count("-fdiagnostics-show-note-include-stack")!=1:
  raise RuntimeError("EXPECTED_CLANG_DIAGNOSTIC_FLAG_ABSENT")
 gcc_cmd=[gcc]+[x for x in driver_cmd[1:] if x not in clang_only]
 removed=[x for x in driver_cmd[1:] if x in clang_only]
 if gcc_cmd.count("-O3")!=1 or gcc_cmd.count("-c")!=1 or gcc_cmd.count("-o")!=1:
  raise RuntimeError("GCC15_COMMAND_SCOPE_ALTERED")
 for sw in ("-c","-o"):
  if gcc_cmd[gcc_cmd.index(sw)+1]!=driver_cmd[driver_cmd.index(sw)+1]:
   raise RuntimeError("GCC15_INPUT_OR_OUTPUT_ALTERED")
 state["gcc15_preflight"]={"compiler":gcc,"compiler_version":subprocess.check_output(
    [gcc,"-dumpfullversion"],text=True,timeout=10).strip(),
    "clang_only_flags_removed":removed,"optimization_retained":"-O3",
    "same_libstdcxx":clang_stdcpp,"same_abi_macros":gcc_abi,
    "only_driver_object":str(obj),"new_worktrees":0}
 state["gcc15_driver_command"]=gcc_cmd
 state["status"]="GCC15_ABI_PREFLIGHT_PASS_SINGLE_OBJECT_STARTED";save()
 cmd("compile_driver_GCC15_only",gcc_cmd,cwd=gmake_dir,env=env,timeout=1800)
 if hashfile(obj)==hashbytes(oldobj):
  raise RuntimeError("GCC15_DRIVER_OBJECT_NOT_REPLACED")
 new_header=obj.read_bytes()[:20]
 if new_header[:6]!=old_header[:6] or new_header[18:20]!=old_header[18:20]:
  raise RuntimeError("GCC15_OBJECT_ELF_CLASS_ENDIAN_OR_ARCH_MISMATCH")
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
 state["status"]="GCC15_DRIVER_PASS_CLANG_LINK_EXISTING_DIAG_STARTED";save()
 cmd("archive_and_link_only",make,cwd=MAME,env=env,timeout=1800)
 link_log=(EV/"F2_archive_and_link_only.log").read_text(errors="replace")
 if "Compiling src/mame/skeleton/alphasdana.cpp" in link_log:
  raise RuntimeError("UNEXPECTED_DRIVER_RECOMPILATION_IN_LINK_STAGE")
 state["compiler_optimization_override"]="SINGLE_GCC15_DRIVER_O3_OTHER_OBJECTS_UNCHANGED"
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
 if suite.countTestCases()!=3:raise RuntimeError("EXPECTED_3_TRUE_F2_DIRECTED_CASES")
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
 state["status"]="F2_COMPILE_SOURCE_TESTS_NATIVE_HOST_MMIO_PASS_GUEST_CPU_TEST_PREPARATION";save()
 # F1 already established -quickload, debugger and real CPU bus taps. Never
 # change the guest PC, call a function, or inject synthetic MMIO responses.
 for p in (GUEST_RESULT,GUEST_VERDICT):
  if p.exists():p.unlink()
 native_guest=[
    str(BIN),"asmdana","-noreadconfig","-quickload",str(GUEST_PKG),
    "-debug","-debugger","none","-autoboot_script",str(GUEST_LUA),
    "-video","none","-sound","none","-skip_gameinfo",
    "-seconds_to_run","13"]
 state["guest_command"]=native_guest
 state["guest_emutos_package_sha256"]=GUEST_PKG_SHA
 state["guest_map_sha256"]=GUEST_MAP_SHA
 state["status"]="ORIGINAL_EMUTOS_NATURAL_GUEST_CPU_OBSERVATION_STARTED";save()
 cmd("native_guest_cpu",native_guest,cwd=EV,
     env=dict(os.environ,DANA_F2_GUEST_OBSERVATION=str(GUEST_RESULT)),timeout=200)
 if not GUEST_RESULT.is_file():
  raise RuntimeError("NO_F2_GUEST_CPU_OBSERVATION_RECEIPT")
 cmd("verify_native_guest_cpu",["python3",str(GUEST_VERIFY),
     str(GUEST_RESULT),str(GUEST_VERDICT)],cwd=EV,timeout=50)
 guest_truth=json.loads(GUEST_VERDICT.read_text())
 state["guest_cpu_result"]=guest_truth
 if guest_truth.get("status")!="PASS_GUEST_CPU_PEN_X_Y":
  raise RuntimeError("NATIVE_GUEST_CPU_F2_NOT_QUALIFIED")
 state["native_F2"]="PASS_GUEST_CPU_PEN_X_Y"
 state["status"]="F2_COMPILED_LINKED_METHODS_HOST_MMIO_AND_ORIGINAL_GUEST_CPU_PASS"

except Exception as error:
 state["status"]="BLOCKED";state["error"]=str(error)
 if GUEST_VERDICT.is_file():
  try:
   state["guest_cpu_result"]=json.loads(GUEST_VERDICT.read_text())
   state["status"]="F2_GUEST_"+str(state["guest_cpu_result"].get("status","BLOCKED"))
  except (OSError,ValueError,KeyError):pass
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
if state["status"]!="F2_COMPILED_LINKED_METHODS_HOST_MMIO_AND_ORIGINAL_GUEST_CPU_PASS":sys.exit(2)
PY
