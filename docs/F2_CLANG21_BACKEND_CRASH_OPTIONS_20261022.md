# F2 compilation: verified Clang21 backend crash and minimal remediation options

**Date:** 2026-10-22. **Type:** source/log audit only; no new Commander, MAME build, native test, ROM build, or workspace creation.

## Evidence from the actual single-tree F2 launch

The original 2026-10-22 T logs (already inspected and recorded by the project) are at:
- `/home/spc/DANA_EMU_ISOLATED/DIAG_EVIDENCE_ARCHIVE/F2_ONE_ACTIVE_DIAG_RESULT.json`
- `/home/spc/DANA_EMU_ISOLATED/DIAG_EVIDENCE_ARCHIVE/F2_dryrun.log`
- `/home/spc/DANA_EMU_ISOLATED/DIAG_EVIDENCE_ARCHIVE/F2_compile_and_link.log`

The **real Clang 21.1.8** frontend was started with `-O3 -std=c++20` for exactly one source unit, `src/mame/skeleton/alphasdana.cpp`. The translation completed parsing and entered **X86 DAG->DAG Instruction Selection**, then crashed with signal 11 / compiler exit **139** within `llvm::SelectionDAGISel::SelectCodeCommon`; `make` exited 2. The LLVM symbol rendered in the report is `device_finder<dana_vz_cpu_device, false>::device_finder`, **not** F2 `pen_exchange`. Parsing or C++ diagnostic failure is not shown; success of all F2 behavior is also not shown. Dry-run compiled one object only. No new DIAG link, six directed tests, EmuTOS test or native stylus PASS. Original DIAG source and binary restored; zero duplicate worktrees.

Compiler-provided repro outputs were reported under `/tmp/alphasdana-691d0b.cpp` and `/tmp/alphasdana-691d0b.sh`; **existence after the attempt has not been checked**. Do not create another copy of the MAME build just to inspect these.

## Critical correction to the previous baseline description

The qualified 012-C DIAG binary `caad0206386d6f3039b836d20198d850bc0911f546963df43f3f4be2f6e48f37` was built with production source at **`581601b49acb6603af2a100817d0f06fed17ed96`**, original driver SHA-256 `e8211be78dfb2bf4cdc0ccabd444c97d715dc37d189d4f113f2f1cbf05b573e2`, **826 lines**.

The later version `80cbfecab4df3c4412e370974295ac8a2f336fc1` (1131 lines) is a source-only base for the F2 Git cherry-pick, **not the known compiled-binary source**. Compared with 012-C it has **355 additions / 50 deletions** touching UART serial interface and FIFOs, SPI1 handling, expanded ST keyboard input, LCD rendering, IRQ/timer behavior and I/O definitions. Native compilation of this precise base is not established by the current evidence. F2 then changes **81 additions / 8 deletions**, yielding `78be96c5615c4b929a96c9dc835b9fff3a2161aa` (1204 lines). The real qualified-binary-source-to-F2 delta is **436 additions / 58 deletions**. Therefore calling the last attempt "only F2 changed relative to the last compiled binary" was inaccurate. This matters for diagnosis: the incident cannot be localized to the pen peripheral.

In both old and new production source the named MAME CPU finder/CPU construction is materially unchanged. `false` is an *optional* finder template parameter: it is not directly the `required_device<dana_vz_cpu_device>` declaration of `m_maincpu`. Do not edit the CPU or core `device_finder` template on the basis of its frame alone.

## Ranked, bounded options

1. **Minimal first choice:** Same pinned Clang 21.1.8, same generated includes/defines and 1129+ existing cached MAME objects, same one `dana-diag` worktree. Change ONLY the command-line optimization of the driver compilation from existing `-O3` to **`-O0`** (option appended after generated `-O3`, or replacement in that single command), not the entire project's `OPTIMIZE` setting. Derive the exact driver command from existing dry-run; no MAME project regeneration. Link via the generated MAME link-only step, only when `make -n` proves no additional C++ objects would compile. **One authorized attempt**. Rationale: bypass the optimizer-sensitive LLVM codegen path with least scope; this is a hypothesis, not a guaranteed LLVM bug fix. If an optimized DIAG is later needed, tune only this unit after genuine behavior tests, not up-front.
2. **If #1 still crashes:** Go back to the REAL 012-C compiled source pin, not to the uncompiled 80cb base. Reapply the already-written hardware changes in coherent dependency order (e.g. SPI2/ST baseline relevant to pen, then pen, independent UART1/SPI1/LCD corrections separately) in the same Git/DIAG workspace and with one object at a time. Use existing historical functional tests as evidence where source identity is unchanged. Do **not** reinterpret all the accumulated 355-line delta as a single peripheral. Avoid arbitrary changes to unrelated CPU template implementation.
3. **Last resort for this single object:** Use another already installed compatible Clang toolchain, or GCC15 with carefully reviewed Clang-only flag removal, compiling just this object and linking into the unchanged DIAG; review ABI, exceptions, runtime compatibility, and ensure the resulting binary passes true native tests. This is NOT justification for a second MAME tree, a full recompilation, or rebuilding EmuTOS.
4. **Do not choose now:** Regenerate/build all 1130+ MAME objects in a GCC-homogeneous project. No evidence requires it.

## One-tree job integrity correction needed BEFORE any next successful compile

The prior job `017_f2_one_active_diag_inplace.job.sh` saves/restores the source, `alphasdana.o` and `danadiagd` bytes in memory. However a successful MAME driver compile would also recreate `build/dana-diag/linux_clang/bin/x64/Debug/mame_danadiag/libmame_danadiag.a`, an archive shown in the real dry-run. This archive is **not** currently restored by the script after its candidate run. A future one-tree job must preserve and restore it as well, verify all files on exit, and not claim consistency from the source/object/binary check alone. Do not overwrite the installed qualified `bin/dana-diag` until native F2 behavior is accredited. Maintain a single active DIAG and only small bounded logs/receipts.

## Verdict

The incident is **COMPILER_BACKEND_CRASH_CONFIRMED / EXACT_TRIGGER_UNPROVEN / F2_NATIVE_PENDING**. This does not warrant a complete toolchain rebuild and does not prove an F2 C++ defect. Prefer a single controlled `-O0` object-only build *if the user authorizes a new attempt*; if still unsuccessful, genuinely isolate the previously uncompiled hardware delta starting from the real 012-C source. No repeat jobs, no isolated emulator variants and no Commander monitoring.
