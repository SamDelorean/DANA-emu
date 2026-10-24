# D7.5 — Guest SPI writes and persistent dual SD images

2026-10-24. **IMPLEMENTED / STATIC_PASS / NATIVE_PENDING.** Base `main@5be8beb797fdf40475f564f54ca3ebd243dc20a5`, retaining the accredited D7/D8.3 implementation `cfa77f248711d75b6e0b75090a05f4b3d1bc0102`. Existing installed DIAG SHA256 reported in the canonical native receipt: `01ad4619bf82964c11d96049a3ff6c9ebfdcca84cbe0df470dcc3f88c0711417`. It has not been accessed or modified. No T/Commander operation, emulator execution, MAME/EmuTOS build, new branch/clone/tree/object/executable or repeated closed native campaign.

## Functional implementation

Only the three existing production files change. `alphasdana.cpp` assigns each existing device its slot index and adds two independent **SD0 image writes / SD1 image writes** machine-configuration fields, both **Protected** by default. Explicitly enable the intended field in MAME's existing configuration UI; normal system configuration retains the user's choice. The guest cannot enable it through MMIO. MAME may open an existing raw image read/write to provide that capability, falling back to a read-only handle if necessary; the device's effective protection also checks that handle and live fault quarantine. No create, resize, replacement, chmod or host filesystem emulation is added. File-open capability alone is not permission to write. A new configuration starts protected; a previously deliberate per-slot enabled configuration remains an explicit user choice.

`alphasdana_sd.h` extends the existing parser, not SPI1. CMD24 accepts FE +512 bytes +two CRC16 bytes. CMD25 accepts repeated FC packets and FD stop **between** complete packets; FD inside data is ordinary data. Invalid start tokens cannot trigger a write. CRC16 is always received and is validated when CMD59 has enabled CRC, as required by the existing SPI contract; default SPI CRC-off permits the original EmuTOS dummy CRC. Correctly framed packets yield:

| Outcome | Data response / later status |
| --- | --- |
| Full successful backend write/flush/readback/hash verification | `05`, two modeled zero busy bytes, then `FF` ready; next LBA advances only now |
| CRC failure with CRC enabled | `0B`; no backend write and no LBA advance |
| Protected/host-read-only media | `0D`; CMD13 WP violation20; no backend write |
| Backend error, short write, failed flush/readback or wrong resulting image | `0D`; CMD13 general error04; live session quarantine |
| Invalid initial address/alignment | R1 address error20; backend not called |
| Multiblock stream reaches capacity | `0D`; CMD13 out-of-range80; no file extension |
| Ejected/absent device | Electrical idle `FF`/no response; never a fake card acceptance |

CSD temporary write protection follows the slot's **effective** policy. Accepted and rejected packet responses suppress new parser input until the response tail is emitted. FD ends CMD25 and exposes a bounded completion/busy tail. Busy is a small deterministic serial completion phase **after** synchronous backend completion, not physical NAND timing or an invented asynchronous write cache. CMD17/CMD18 and their already qualified SPI1/GPIO paths are retained for reading the actual changed sectors.

`alphasdana_sd_image.h` writes through MAME's existing `image_core_file()` and `util::write_at`, preserving both error and actual byte count; the old convenience `fwrite` discards errors and is not used. Before any mutation, stream the existing medium and check its current SHA1 against the live identity, while calculating the exact expected new hash with only that512-byte replacement. Then write all512 bytes in bounds, check `flush()`, read and compare all512 bytes, hash the resulting medium and require equality with that predicted identity. Only then update the identity/counter, return success and allow the protocol to emit05. This is real in-place file I/O, not a RAM-only sector cache. Each full scan uses64KiB temporary memory; two full scans per committed sector prioritize integrity and can be slow on large images. The32GiB geometry bound is unchanged, not a performance promise.

## Persistence, interruption and snapshots

Completed blocks are already backend-written/flushed/verified before acknowledgement. Eject, CS release, power-off, reset and shutdown never commit a partly received block or missing CRC. They discard only the partial parser frame; earlier accepted blocks remain in the image. CMD25 is a sequence of per-block commits, not a whole-stream transaction. Ejection performs a checked final backend flush and reports an error if it fails. An operating-system write failure can have changed part of the target sector: **there is no atomic512-byte overwrite, rollback or repair guarantee**. Preserve the affected file and quarantine the session rather than acknowledge, hide the failure or bless a new hash. Quarantine blocks further read/write and save/restore until deliberate remount of independently verified media; snapshots cannot clear it.

The new receive buffer and response/busy phase are serialized alongside the existing parser/FIFO/partial-bit state. Full-file identities track **verified committed modifications**. Presave validates the current identity and records effective write permission; postload requires exact current image bytes/length/presence and matching permission. An earlier snapshot cannot undo file writes or replay its partial transfer against a subsequently modified image. Media bytes are not copied into public Git or rolled back from a snapshot. Existing pre-D7.5 states have a different schema and are not claimed compatible. Independent writable images must be separate files, with exclusive application ownership; concurrent external writers and file aliases are not supported or made atomic by these checks. MAME's cached file-length behavior is not a lock against external resizing.

**Exact durability limit:** pinned `src/lib/util/ioprocs.h` describes `flush` as application-cache flushing without a persistent-storage guarantee. `corefile.cpp::core_osd_file::flush` invalidates its read buffer and calls the OSD backend. The pinned POSIX regular-file `flush` implementation in `src/osd/modules/file/posixfile.cpp` returns success because its unistd writes are unbuffered; it does **not** issue `fsync`/`fdatasync`. Therefore this implementation supports verifiable normal-close/reopen persistence but makes **no power-loss, kernel-crash, device-cache or atomic overwrite durability claim**. Native close/reopen qualification is still pending.

## Preserved baseline and actual static results

No qualified SPI1/FIFO/scheduler/GPIO/IRQ function body changes; the controller struct is byte-identical. All existing Flash/RESET, RAM quickload, LCD, SPI2/ST, keyboard, pen, Timer1/UART functions and GUI-025/026 patches remain intact. EmuTOS024C is unchanged. PD2/PD3 board insertion semantics remain the already documented uncertainty, not a new gate or invented signal.

`DANA_MAME_REFERENCE=/path/to/pinned/mame python3 tests/d7_sd_test.py`: **19/19 static PASS**, no skips/errors/failures. Whole driver C++20 MAME-header syntax, six additional write-path constant assertion groups, exact qualified-function preservation, native fixture envelope/opcode controls, Bash HOLD guard and generated Lua5.4 syntax parsing are covered. No Lua script, native guest or emulator was executed. Source tests model backend short-write/flush failures at compile time; they are not real backend runtime evidence. The earlier read-only static fixture now waits for the correct CMD25 stop busy tail; its WP assertions remain. The GUI scope test now checks actual GUI filenames rather than matching `026` inside the year2026 of an unrelated native receipt. Neither harness adaptation changes a hardware assertion or historical native result.

Results/log/hashes: `tests/d7_5_status.json`, `tests/d7_5_static.log`, `docs/D7_5_SHA256SUMS.txt`. Historical D7/D8.3 and D8.5 native receipts remain unchanged. Python/Lua/Bash syntax and Git whitespace checks pass. Lua syntax is checked with the already installed shared library, loading text without executing it. Native execution, real file persistence, native error handling and the prepared fixture's actual CPU run remain **PENDING**.

## One integrated native campaign — LOCAL GIT HOLD ONLY

`tests/d7_5_native_HOLD.job.sh` and `tests/d7_5_native.py` are prepared, not dispatched. A fresh explicit authorization is mandatory; a subsequent intervention has a maximum of **five Commander calls**, not an inherited allowance. The job does not build, modify a source tree or contact T. After separately authorized incremental compilation of the same existing DIAG/cache, supply its measured **new** binary hash and the existing canonical skeleton directory. The guard rejects the accredited old read-only executable, a different executable name, source/hash drift, changed campaign bytes or an existing output directory. No original user image can be supplied: the runner creates exactly two owned16KiB disposable images in a new evidence directory and preserves them/results for review.

Authorization-time interface (instructions only):

```
DANA_D75_NATIVE_AUTHORIZED=YES bash tests/d7_5_native_HOLD.job.sh \
  --diag /existing/canonical/diag/bin/dana-diag \
  --diag-sha256 MEASURED_NEW_DIAG_SHA256 \
  --source /existing/canonical/mame-stage/diag/source/src/mame/skeleton \
  --output /new/absolute/disposable-D75-evidence
```

The script stages test-owned DANARAM1 diagnostics using fixed original68000 instruction encodings. CPU instructions drive the already qualified SPI1 registers; Lua only selects explicit per-slot test protection, observes CPU-owned RAM/MMIO activity, requests diagnostic reset/ejection or MAME state operations and exits. It never synthesizes SD data, tokens or writes to controller MMIO. No assembler/toolchain, alternate emulator or Flash campaign is needed. Initializing a card is a prerequisite within a write case, not a repetition of the closed reading/Flash/GUI campaigns.

Integrated cases: protected writes on both cards; bad CRC with CMD59 enabled; wrong/incomplete frames; partial CS release, power loss, close and ejection; soft reset before CRC; independent SD0-enabled/SD1-protected; CMD24 and CMD25/FD on both enabled slots with busy observations and CPU CMD17/CMD18 readback; whole-image comparison including untouched sectors; a separate process that reopens both images and rereads via guest CPU; new identity snapshot save/restore and explicit rejection of changed policy/stale media. A Linux `RLIMIT_FSIZE=4096` plus ignored SIGXFSZ makes a genuine in-bounds write to sector16 of an existing16KiB test image return a backend error; the file must remain unchanged and the actual error log must be present. No full disk, user path, physical card, driver fault injection or production failure-success stub is used.

Every native process is bounded to90 wall seconds,1800 display frames,2MiB combined log; the single job is bounded to1800 wall seconds. It records the measured binary hash, before/after image hashes, CPU PC/SR/SP, real SPI write count, response/busy RAM results, CPU-read sector buffers, raw logs and aggregate machine-readable PASS/FAIL/BLOCKED. A fixture assertion failure is FAIL; missing evidence/timeouts are BLOCKED. Expected state-rejection tests require the actual matching native error, not just any nonzero exit. These preparations are statically checked, not a native PASS. Genuine partial-host-write and flush-error responses are covered by component controls; the prepared real-file native failure case is EFBIG, not a claim to have injected every host storage failure.

**Single next action:** freshly authorize one same-DIAG incremental update and this integrated disposable-media D7.5 campaign. Do not repeat closed Flash/RESET, touch, read-only or GUI-026 qualification. Prepared continuity/rector records target the existing workbook only; no new workbook or T job submission was created.
