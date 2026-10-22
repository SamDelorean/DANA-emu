# F2–F4: replan after the one-attempt direct object strategy

## Actual last result

One explicitly authorized attempt used 2 Commander calls and stopped **before invoking the GCC compiler**. The preparatory flag translator rejected the *known* Clang-specific `-fdiagnostics-show-note-include-stack`. The correct description is **PREBUILD_TRANSLATOR_DEFECT**; this is **not** evidence that GCC15 failed compiling the driver or that MAME/EmuTOS failed to run.

- Source pin: `87e26793ff4743d5fef5539def994872e2291739`
- Attempt job: `836ebf28da619acaebb82346bb305acbe0dca62c`
- Archive SHA-256: `9a67ffabf3ac03f7251cd9b755b4b84fc40ea3df9c3a87228dca24e5101daefa`
- Full result: `tests/dana_f2_f4_direct_gcc15_attempt_result.json`

There must be **no silent retry**, no increment renaming, no more guessed compiler flags and no new declaration of a native functional PASS.

## Decision: stop mixing legacy Clang-generated make recipes with a single GCC object

The failure pattern is a tooling-path problem:
1. The qualified legacy MAME object cache belongs to a Clang21-generated project.
2. Clang21 has three internal backend crashes trying to compile the newer driver.
3. GCC15 is installed and uses the same host libstdc++, but a direct wrapper received Clang-only generated flags.
4. The follow-up translator, intended to remove those flags, rejected one without invoking GCC.

These attempts **do not prove a defect in the actual F2–F4 peripheral implementation**, but they do prove the current incremental build procedure is unproductive.

## Next product-oriented alternative: a coherent GCC build of only `dana-diag`

- Preserve the donor MAME pin `c4e48388ca620472643110db2941ce70aa5f3c07`, all source locks and the verified original EmuTOS guest binaries. Neither the ROM nor firmware will be rebuilt.
- Use an **isolated clean GCC15-generated MAME build configuration**, not Clang21 makefiles, and target only the existing `alphasdana.cpp` / `danadiag` product. Keep the previously qualified Clang cache read-only as a benchmark; do not present it as ABI-homogeneous GCC objects.
- Select installed `gcc-15` and `g++-15` only if both are verified available; use the native MAME build system to generate GCC flags (no manual conversion). Do not install toolchains or extract a new donor unless an actual dependency requires it.
- Allow **one coherent new object build of the required target dependencies**. The prior 1,130-object Clang cache cannot automatically be claimed reusable in a GCC-homogeneous build. Report actual compilation units and elapsed resource use. If the system can reuse independently qualified matching GCC objects, do so, with explicit provenance.
- If the binary links, run **only `dana-diag`** against the pinned, previously compiled EmuTOS. Capture actual boot progress, LCD, Timer1/IRQ6, UART TX and host input. No guest/ROM rebuild.
- Keep bounded evidence and hashes. Attribute the existing ten PASS items to the older verified driver, not to the new binary until observed.

**Before another native build:** derive one exact GCC project generation + build script statically from donor's locked Makefile and source layout, without another experiment on the T. Then seek **separate explicit authorization** for a single coherent build/test run. Do not label the new method a fresh objective to evade the previous failed attempt count.

## Product deliverable priority

The next meaningful output is a new executable `dana-diag` using real F2–F4 source. Following that, a measurable genuine EmuTOS boot and input test. The build system is a means to that end, not a new investigation workstream.
