# DANA-emu F1 — EmuTOS-Dana guest build subplan

**Date:** 2026-10-17  
**Parent:** [General Work Plan](GENERAL_WORK_PLAN.md), [F1 functional assignment #8](https://github.com/SamDelorean/DANA-emu/issues/8), active draft PR #7.  
**Work mode:** DIAG-FIRST, reuse and STATIC_FIRST. This subplan is **one bounded part of the existing F1 functional delivery**, not a new emulator project or a chain of microincrements.

## Intended result

Produce **real, provenance-checked** `emutos.img`, `emutos-dana.rom`, and `emutos.map` from the unmodified pinned source `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`, then feed the existing F1 RAM loader and run authentic M68000 guest instructions.

A targeted search found no independently usable prebuilt Dana guest; compilation is now the fallback explicitly selected by the user. Do not substitute standard Atari, Amiga or FireBee EmuTOS binaries.

## E1 — Reuse BetaWise assessment, qualify isolated CrossMiNT (CLOSED / REAL PASS)

**Priority 1: reuse the existing BetaWise compiler.** The user reports an already used m68k cross compiler. [BetaWise `m68k-elf/Makefile`](https://github.com/SamDelorean/betawise/blob/master/m68k-elf/Makefile) declares GCC 16.1.0 targeting `m68k-elf`, `--with-cpu=68000`, `--disable-multilib`, installation to `$HOME/.local`; [Makefile.common](https://github.com/SamDelorean/betawise/blob/master/Makefile.common) uses `-mpcrel -ffixed-a5 -fshort-enums`, **not `-mshort`**. [Pinned EmuTOS Makefile](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/Makefile) explicitly supports `m68k-elf-gcc` through `ELF=1`, but requires `-m68000 -mshort` and `-lgcc`. Because the BetaWise toolchain recipe disables multilib, it may lack a matching `-mshort` runtime; **actual installed compiler version, location and runtime support remain unverified on T**.

The existing F1 HOLD job now checks for `m68k-elf-gcc` in PATH or `$HOME/.local/bin` *first*, verifies exact target/ABI/multilib and compiles plus links against that compiler's actual libgcc. It selects `m68k-elf-` (and the already supported EmuTOS `ELF=1` mode) **only on an actual PASS**. An incompatible installed compiler yields a clearly recorded reason and continues to CrossMiNT **within the same job**, without a new iteration or system change.

**Priority 2 fallback:** obtain two **official Linux x86_64** prebuilt archives from Thorsten Otto's CrossMiNT distribution, without building GCC/binutils or systemwide installation.

- `gcc-4.6.4-mint-bin-linux64.tar.xz` — upstream CrossMiNT GCC 4.6.4 with `-mshort` multilib.
- `binutils-2.30-mint-bin-linux64.tar.xz` — matching *classic m68k-a.out* binutils version. Prefer it to speculative upgrades for this historical guest; use the correct MiNT/a.out flavor, **not `mintelf`**.
- Source index: https://tho-otto.de/crossmint.php
- **Verified official vendor URLs and exact archive hashes:** GCC `https://tho-otto.m68k.eu/download/mint/gcc-4.6.4-mint-20230719-bin-linux64.tar.xz` (SHA-256 `00f8eac034e1b17f5fb5314bf645a910c578c2ecb9db3854fb0025d0af90e6a9`); binutils `https://tho-otto.m68k.eu/download/mint/binutils-2.30-mint-20180323-bin-linux64.tar.xz` (SHA-256 `402a3143cefae2121270cb9d211e3a609a4daf04d236dbe9ba55a2105b8ca57e`). The non-date filenames originally recorded were **invalid URLs (HTTP 404)**, not unavailable software.
- Isolate under the already documented Dana work area; never install into system locations, overwrite donor, alter AS2K, or require sudo.
- The source-controlled `tools/f1_crossmint_acquire.py` acquires or accepts already provided archives, computes SHA-256, checks bounded tar paths/links, and produces `toolchain_manifest.json` with resolved compiler directory. The existing `tools/f1_crossmint_preflight.py` must compile **and link** a real `-m68000 -mshort` 16-bit-int / 32-bit-long ABI probe using the candidate's own `libgcc`.

**E1 PASS for EmuTOS:** a truly compatible compiler (currently expected to be isolated CrossMiNT) passes actual `-m68000 -mshort` ABI and matching `-lgcc` linker test, recording installed GCC identity, real archive SHA-256 and version. The separate BetaWise M68000 OS3K compiler probe is already PASS but does not meet EmuTOS's `-mshort` requirement. **An archive listing or a synthetic fixture test is not PASS.**

**Historical BetaWise compiler result (2026-10-17, canonical T, superseded for EmuTOS E1):** The installed BetaWise cross compiler is `/home/spc/.local/bin/m68k-elf-gcc` **GCC 16.1.0**, `m68k-elf`, proven by one real M68000 freestanding C object compilation using `-m68000 -fshort-enums` (**PASS_OS3K_COMPILER**; no symlink/install/system changes). `-print-multi-lib` outputs only `.;`, hence BetaWise lacks the required **`-mshort` multilib**; EmuTOS compatibility is **BLOCKED_NO_MSHORT_MULTILIB**. This does not invalidate BetaWise or its future OS3K use. **E1 for EmuTOS remains BLOCKED_MSHORT until separately installed/qualified isolated CrossMiNT**; don't rerun the already closed BetaWise probe. [Read-only T evidence](T_BETAWISE_TOOLCHAIN_CHECKPOINT_20261017.md). Source-level CrossMiNT acquisition helpers are prepared, but no genuine CrossMiNT toolchain/archive was verified. No guest binary or updated DIAG qualification yet.

**E1 actual PASS (2026-10-17, T):** Isolated CrossMiNT GCC 4.6.4 and binutils 2.30 obtained from verified official URLs; genuine 16-bit `int` / 32-bit `long` `-m68000 -mshort` C compile and `-lgcc` link **PASS**, GCC reports `mshort` multilib and file-backed libgcc. Location `/home/spc/DANA_EMU_ISOLATED/f1_e1e2_baldoi9k/crossmint/unpacked/usr/bin`. A verified reuse pointer is saved in `/home/spc/DANA_EMU_ISOLATED/F1_CROSSMINT_VERIFIED.json`. BetaWise remains unchanged and remains the priority toolchain for OS3K.

## E2 — Build exact EmuTOS-Dana artifacts in one run (CLOSED / REAL PASS)

Once E1 passes, use the already implemented `tools/f1_guest.py build` on the exact pinned source SHA in isolated staging. Run historical `make -j3 dana` **without source patching**. Preserve the compiler, version, arguments, source revision, `build.log`, `build_provenance.json`, and the actual three outputs.

Use `tools/f1_guest.py validate` to check the linked map (including `__text`, `_os_header`, `_main`, `_stktop`), image bounds, historical RAM profile, first-stage booter/embedded image identity, native entry and output SHA-256. Record verified SHA and actual sizes; do not assume historical sample image size is a current fixture.

**E2 PASS:** `emutos.img`, `emutos-dana.rom`, `emutos.map` exist from one valid build and the F1 packager produces a validated `emutos.dana` for the native MAME RAM loader. If source/model rejects real layout, classify precise INPUT/LAYOUT failure and repair the correct layer; do not falsify a map.

**E2 actual PASS (2026-10-17, T):** Unmodified `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b` compiled via `make -j3 dana TOOLCHAIN_PREFIX=m68k-atari-mint-` and separately validated (real linker map, physical entry `0x2140`, 4 MiB RAM profile, genuine `DANARAM1` envelope). Result SHA-256 identities:

| Real artifact | Bytes | SHA-256 |
|---|---:|---|
| `emutos.img` | 223,748 | `ba590da2661bc582c19bb24d65db04667daf37a17d7aa51fb462b945933ba0a3` |
| `emutos-dana.rom` | 223,792 | `efb055e5ac02526db069aec23c4b71b092fc48317aa4305e93a4a2f4e369243c` |
| `emutos.map` | 124,540 | `17cc980e675e2e1b50e713b9029f6fc3e51d3e55392deb99d53552d4b3af3e68` |
| `emutos.dana` | 223,812 | `c201c8527df87fa6a8788d8ac59f43298666196fefeee12dcac68295cb281b9d` |

All four hashes were independently recomputed from the [Drive evidence package](https://drive.google.com/file/d/1METSVshkjiuAJgpH5ilXRW5B2giTUkCf/view), archive SHA-256 `b53600abcbafa7345d1d3bceffc1dc6f13bbd8b0788e7e59e2b2aa2746b6e4c6`. MAME **not built or executed** in E1/E2. E2 outputs remain on canonical T at `/home/spc/DANA_EMU_ISOLATED/f1_e1e2_baldoi9k/emutos-built`, plus Drive and a downloadable artifact bundle.

## Private ROM mirrors — 2026-10-17 VERIFIED

The four E2 outputs and `SHA256SUMS.txt` were installed at **both** user-private canonical locations:

- **Google Drive:** [`ALPHASMART/private/roms/dana`](https://drive.google.com/drive/folders/1NoJL_HjtezdeayKlWYEYXQ9uYd12zvEH) — four actual bytes streams re-downloaded and independently checked against the exact E2 SHA-256 hashes listed above.
- **Canonical T:** `/home/spc/Projects/alphasmart/private/roms/dana` — one verified, bounded `dcjob` copy job archived PASS/exit 0; own job output confirms all four newly copied files, SHA256 **postcopy PASS**, no previous ROM overwritten. [Evidence package](https://drive.google.com/file/d/1e_yrgk5HZLiwh36jzmxez5Jv28gaD_fT/view), SHA256 `2db6055b77fb7c44a54c64e627973d2fa3c378fc8d4dd27ef72b1747a318719a`.

Use these mirrors for E3 and validate their hashes; no new guest build is needed. Do not publish ROM copies to GitHub.

## E3 — Qualify F1 in the real DIAG emulator, still one campaign

**Canonical E3 job (2026-10-17):** [`tests/hold/001_dana_f1_e3_diag_guest_only_20261017.job.sh`](https://github.com/SamDelorean/DANA-emu/blob/codex/dana-d1-2-ram-bus/tests/hold/001_dana_f1_e3_diag_guest_only_20261017.job.sh) replaces the prior `000_dana_f1_emutos.job.sh` **for E3 execution only**; do not dispatch the latter because it still contains optional E1/E2 rebuild paths. Immutable SHA-256 of canonical E3 job `dc3208a95fdd929f1b09618fb161f92ed242258e47123f5fae939ff843f8ed86`, registered in Drive [HOLD](https://drive.google.com/file/d/1439IQg75z0YLXNfAe-AqABVqQw202NIn/view). It requires exact SHA-256 for the four original E2 files in both `/home/spc/Projects/alphasmart/private/roms/dana` and preserved E2 staging, copies them into a fresh isolated run directory and validates the unchanged guest with existing `tools/f1_guest.py validate`. **It does not call `make dana`, download CrossMiNT, rebuild GCC, or write to private ROM folders.** It then prepares/builds the changed DIAG driver from pinned MAME `c4e48388ca620472643110db2941ce70aa5f3c07` with LLVM/Clang 21 and `make -j3`. Exact DANA-emu driver snapshot pinned at `144365bf0028cde47e8c419132af82652b550042`.

Then run the existing DIAG smoke, impacted RAM-01/RAM-08 and CPU-origin MMIO-01 regression, two fresh authentic guest runs, plus native rejected-corrupt-image test, preserving bounded logs, hashes and Drive results. The previously qualified D1.2 9/9 stays closed; R7 cannot be used as the F1 driver because C++ changed.

**E3 PASS (initial F1 scope):** genuine map-validated EmuTOS instructions execute through the MAME M68000 and a reproducible next hardware dependency is identified with PC/address/operation evidence. This does **not** declare the entire EmuTOS GUI functional; LCD and ST keyboard remain later stages of the General Work Plan.

## Authorization, evidence and state

- **Source preparation, document edits and local synthetic checks only** are performed without consuming Commander. No new Commander/T budget is inherited.
- The SH remains **GIT HOLD ONLY**. A verified file and one approved Drive queue job, then the canonical `/home/spc/.local/bin/dcjob launch` on explicit T device, require the user's separate fresh Commander approval. No automatic merge or next milestone.
- Run preflight and validation before the costly MAME build; do not repeat compiles merely to inspect a Python/script failure. Do not touch foreign Drive queue items.
- **Current cursor:** **E1 CLOSED/PASS; E2 CLOSED/PASS; E3 SOURCE-READY / DRIVE HOLD / NOT EXECUTED.** The dedicated E3-only SH passed local `bash -n`, embedded Python AST, strict no-recompile source-guard review, complete Drive upload/readback byte and SHA256 match, and exact GitHub source readback. This is **source/harness preflight only**, not a new production DIAG compile or real EmuTOS boot. Next action is the single real T qualification campaign after a **fresh explicit Commander/E3 authorization** and verification that the shared inbox is available. E3 must classify genuine instruction execution separately from EmuTOS being blocked on unimplemented VZ MMIO; do not mark F1 hardware complete from a guest trace.
- Historic status and new results must be appended to [HANDOFF.md](HANDOFF.md) and [DIAG-FIRST execution ledger](DIAG_FIRST_ANTI_GATE_INCREMENTAL_PLAN.md) without reopening closed investigations or splitting F1 into artificial gates.

**Never claim PASS for E1/E2/E3 solely from Git commits, an online package listing, syntax checks, upload, accepted PID or synthetic verifier counts.**
