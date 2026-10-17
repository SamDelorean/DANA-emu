# DANA-emu F1 — EmuTOS-Dana guest build subplan

**Date:** 2026-10-17  
**Parent:** [General Work Plan](GENERAL_WORK_PLAN.md), [F1 functional assignment #8](https://github.com/SamDelorean/DANA-emu/issues/8), active draft PR #7.  
**Work mode:** DIAG-FIRST, reuse and STATIC_FIRST. This subplan is **one bounded part of the existing F1 functional delivery**, not a new emulator project or a chain of microincrements.

## Intended result

Produce **real, provenance-checked** `emutos.img`, `emutos-dana.rom`, and `emutos.map` from the unmodified pinned source `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`, then feed the existing F1 RAM loader and run authentic M68000 guest instructions.

A targeted search found no independently usable prebuilt Dana guest; compilation is now the fallback explicitly selected by the user. Do not substitute standard Atari, Amiga or FireBee EmuTOS binaries.

## E1 — Install and qualify existing MiNT cross tools (CURRENT)

**Scope:** obtain two **official Linux x86_64** prebuilt archives from Thorsten Otto's CrossMiNT distribution, without building GCC/binutils or systemwide installation.

- `gcc-4.6.4-mint-bin-linux64.tar.xz` — upstream CrossMiNT GCC 4.6.4 with `-mshort` multilib.
- `binutils-2.30-mint-bin-linux64.tar.xz` — matching *classic m68k-a.out* binutils version. Prefer it to speculative upgrades for this historical guest; use the correct MiNT/a.out flavor, **not `mintelf`**.
- Source index: https://tho-otto.de/crossmint.php
- Candidate vendor links: https://tho-otto.m68k.eu/download/mint/gcc-4.6.4-mint-bin-linux64.tar.xz and https://tho-otto.m68k.eu/download/mint/binutils-2.30-mint-bin-linux64.tar.xz. Vendor index establishes filenames; **exact endpoints and downloaded SHA256 are not yet independently verified**.
- Isolate under the already documented Dana work area; never install into system locations, overwrite donor, alter AS2K, or require sudo.
- The source-controlled `tools/f1_crossmint_acquire.py` acquires or accepts already provided archives, computes SHA-256, checks bounded tar paths/links, and produces `toolchain_manifest.json` with resolved compiler directory. The existing `tools/f1_crossmint_preflight.py` must compile **and link** a real `-m68000 -mshort` 16-bit-int / 32-bit-long ABI probe using the candidate's own `libgcc`.

**E1 PASS:** actual installed compiler and binutils from acquired archives are usable; executable `m68k-atari-mint-gcc` with `-mshort` runtime and `-lgcc` linker test PASS, actual package SHA and compiler version recorded. **An archive listing or a synthetic fixture test is not PASS.**

**Current result:** helper syntax and synthetic offline installation-path test passed, missing-archive rejection passed; no genuine toolchain installed or executed in this chat. This container cannot resolve the vendor host (DNS/network unavailable). **E1=BLOCKED_ARCHIVE_NETWORK**, not a toolchain failure proven on T.

## E2 — Build exact EmuTOS-Dana artifacts in one run

Once E1 passes, use the already implemented `tools/f1_guest.py build` on the exact pinned source SHA in isolated staging. Run historical `make -j3 dana` **without source patching**. Preserve the compiler, version, arguments, source revision, `build.log`, `build_provenance.json`, and the actual three outputs.

Use `tools/f1_guest.py validate` to check the linked map (including `__text`, `_os_header`, `_main`, `_stktop`), image bounds, historical RAM profile, first-stage booter/embedded image identity, native entry and output SHA-256. Record verified SHA and actual sizes; do not assume historical sample image size is a current fixture.

**E2 PASS:** `emutos.img`, `emutos-dana.rom`, `emutos.map` exist from one valid build and the F1 packager produces a validated `emutos.dana` for the native MAME RAM loader. If source/model rejects real layout, classify precise INPUT/LAYOUT failure and repair the correct layer; do not falsify a map.

**Current result:** NOT BUILT. No EmuTOS guest-image SHA exists.

## E3 — Qualify F1 in the real DIAG emulator, still one campaign

The same source-controlled `tests/hold/000_dana_f1_emutos.job.sh` now prepares CrossMiNT when needed, runs the ABI probe, builds EmuTOS and validates it **before** compiling the changed production MAME DIAG driver using pinned MAME `c4e48388ca620472643110db2941ce70aa5f3c07`, Clang 21 and `make -j3`.

Then run the existing DIAG smoke, impacted RAM-01/RAM-08 and CPU-origin MMIO-01 regression, two fresh authentic guest runs, plus native rejected-corrupt-image test, preserving bounded logs, hashes and Drive results. The previously qualified D1.2 9/9 stays closed; R7 cannot be used as the F1 driver because C++ changed.

**E3 PASS (initial F1 scope):** genuine map-validated EmuTOS instructions execute through the MAME M68000 and a reproducible next hardware dependency is identified with PC/address/operation evidence. This does **not** declare the entire EmuTOS GUI functional; LCD and ST keyboard remain later stages of the General Work Plan.

## Authorization, evidence and state

- **Source preparation, document edits and local synthetic checks only** are performed without consuming Commander. No new Commander/T budget is inherited.
- The SH remains **GIT HOLD ONLY**. A verified file and one approved Drive queue job, then the canonical `/home/spc/.local/bin/dcjob launch` on explicit T device, require the user's separate fresh Commander approval. No automatic merge or next milestone.
- Run preflight and validation before the costly MAME build; do not repeat compiles merely to inspect a Python/script failure. Do not touch foreign Drive queue items.
- **Current cursor:** E1 toolchain preparation complete at source level; actual vendor package download, ABI check and EmuTOS build remain unexecuted. The next useful operation is a **single user-authorized F1 T job** once its full SH syntax, package endpoints and file SHA are independently validated. If no T access is authorized, continue only work that can genuinely complete off-machine.
- Historic status and new results must be appended to [HANDOFF.md](HANDOFF.md) and [DIAG-FIRST execution ledger](DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md) without reopening closed investigations or splitting F1 into artificial gates.

**Never claim PASS for E1/E2/E3 solely from Git commits, an online package listing, syntax checks, upload, accepted PID or synthetic verifier counts.**
