# F2 — Host mouse as Dana stylus: native MAME input route

## 2026-10-23 — Original EmuTOS calibration dependency for F2 GUI (source-only)

**Concrete source finding, not a new gate or peripheral.** The pinned original EmuTOS-Dana source `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b` defines `static LONG screen_calibration[7]` in `bios/dana.c:114`. At `dana_poll_touchscreen()` (lines 497–565), genuine pen contact invokes `dana_ts_rawread()`, but sets screen position `sx/sy` from the new X/Y **only if `c[0]` is nonzero**. The routine still emits `call_mousevec(packet)` while pressed/released. Until a calibration is installed, authentic PF1/SPI2 X/Y and button events therefore do **not** establish correct cursor motion; this is a potential future GUI symptom, not an observed hardware failure.

**Already implemented original guest route.** The source package explicitly contains `tools/danacal.c`; `doc/readme-dana.txt` describes compiling/running the optional `danacal.prg` from EmuCON or with keyboard mouse emulation. Its original guest code acquires three raw pen points via XBIOS `0x8e`, computes seven affine coefficients, and installs them via XBIOS `0x8f`. `bios/xbios.c:1551–1552` dispatches to `ts_rawread`/`ts_calibrate`, and `bios/mouse.c` forwards to `dana_ts_rawread`/`dana_ts_calibrate`. Prefer this real guest utility; do **not** synthesize host mouse packets, forge MMIO, patch the original EmuTOS image, or invent calibration coefficients. The donor tool is GPL-licensed: link to its source rather than merging it into the MAME driver.

**Availability is still unproven.** No `danacal.prg` appeared in a project Drive file search. This does not establish whether it exists on T. The guest program-loading route in the present F2-only DIAG is also unverified; do not silently assume an emulated SD slot, request unrelated SPI1 development, or mislabel missing guest media as a stylus failure.

**One subsequent bounded interactive GUI campaign, only after separate native authorization:**

1. Use the **same existing** `dana-diag` tree and the actual compiled F2 candidate. The existing accredited 012-C executable was restored by job017 and does not permanently include F2. No second emulator, stable version, ROM rebuild, or blind replay of job017.
2. Use an already-supported genuine EmuTOS loading route for `danacal.prg` if the tool is available; calibrate at three distinct host positions through XBIOS `0x8e/0x8f`. Require guest `c[0] != 0` before attributing a lack of movement to the mouse hardware. If the utility cannot be loaded, record `BLOCKED_INPUT_CALIBRATION`, not `F2_FAIL`.
3. Exercise three separated pointer positions, button down/up and held drag, with MAME SDL's **single** lightgun-class input. Require real guest `dana_poll_touchscreen`→`call_mousevec` effects and visible framebuffer/cursor changes at 560×160. Source mapping or MAME exit code alone is not a GUI PASS.
4. Report per-case PASS/FAIL/PARTIAL, preserve historical job017 X/Y evidence, and return source/object/library/linker/binary/dependency/mtime to the qualified DIAG state.
5. This source-only increment used **zero T/Commander calls, compilations, MAME guest executions, or new job scripts**. `PASS_GUEST_CPU_PEN_X_Y` remains reported by job017, with independent receipt audit and enclosing remote-exit discrepancy still unresolved.

Primary sources: [original Dana BIOS](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c), [XBIOS dispatcher](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/xbios.c), [mouse hooks](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/mouse.c), [original calibration tool](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/tools/danacal.c), and [README](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/doc/readme-dana.txt).

## 2026-10-23 — Post-job-017 static evidence audit; no new native execution

- Current authorized F2 campaign was job `017_f2_one_active_diag_inplace.job.sh` at pin `c651057fa3fb5641e01b2c9ffad79d20ee175801`, blob `c72e58b7992412b106f29aa77f5ab65f05253514`, executed once on canonical HP t640 in session PID 127497. Its nested stdout reported `F2_COMPILED_LINKED_METHODS_HOST_MMIO_AND_ORIGINAL_GUEST_CPU_PASS`, `PASS_GUEST_CPU_PEN_X_Y`, and `JOB017_FINAL_EXIT=0`; the enclosing remote session separately reported exit 1. Do not silently reconcile these statuses or treat the latter as evidence of a hardware defect.
- Source review of this **exact pinned job** establishes the success dependency chain: original EmuTOS package/image/map hashes; GCC15-only changed driver object and existing Clang21 link; three directed source tests; host-origin native MMIO; native guest quickload CPU observations; the independent Python verifier requiring original CPU PCs, PF1 active-low contact, PG2 writes, ordered real SPI2 0x90/0xD0 commands and both expected read words, matched event counts, and `overflow=0`; finally restoration of source, object, archive, linker output, binary, dependencies and timestamps. The job returns its successful status only after this chain and rollback checks pass.
- **Provenance limit:** `F2_ONE_ACTIVE_DIAG_RESULT.json`, `F2_guest_cpu_observation.json`, and `F2_guest_cpu_verdict.json` remain at `/home/spc/DANA_EMU_ISOLATED/DIAG_EVIDENCE_ARCHIVE/` on T. A Drive search for their names did not locate uploaded independent receipts. Therefore classify **NATIVE_VERIFIER_PASS_REPORTED / INDIVIDUAL_RECEIPTS_UNAUDITED**; do not claim an independent file-level audit or an entirely completed EmuTOS GUI boot.
- The production driver already maps `GUNCODE_BUTTON1` and the `IPT_LIGHTGUN_X/Y` absolute SDL inputs into PEN/PENX/PENY, and its LCD renderer reads the guest framebuffer directly when the controller registers select 560×160×1bpp. This is **SOURCE_READY**, not motion/click/drag tested.
- **Next useful bounded run, when independently authorized:** on the same sole DIAG, use the proven GCC15 driver-only candidate preparation and an actual SDL window; observe mouse movement, press/release, drag and cursor delta from natural guest framebuffer/UI. Preserve the 012-C accredited DIAG by rollback. Separately, consume existing receipts read-only when T access is authorized; **never replay job017 solely for documentary evidence**. No additional Commander calls or build/GUI tests are authorized by this static review.

**Date:** 2026-10-22. **Implementation:** STATIC SOURCE INTEGRATION READY. **Do not infer interactive GUI PASS or natural EmuTOS mouse-event PASS from this document.** One and only one `dana-diag` worktree, no parallel driver, duplicate emulator, guest patch, or new mouse stack.

## Purpose and chain of responsibility

`SDL host pointer → MAME's SINGLE lightgun-class input device (absolute X/Y, button 1) → DANA PEN/PENX/PENY → PF1 active-low, PG2 ADC CS, SPI2 command/data → original EmuTOS dana_ts_rawread/dana_poll_touchscreen → call_mousevec → guest cursor`.

The driver must emulate the **hardware**, not inject GEM/IKBD events at the application level. The guest already calls `call_mousevec(packet)` with relative movement and button-state packets in `bios/dana.c` (pinned original EmuTOS-Dana `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`).

## Source verification, not speculation

1. Pinned donor MAME `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`, `src/osd/modules/input/input_sdl.cpp`:
   - `sdl_lightgun_device::process_event` consumes **SDL_MOUSEMOTION** window-relative cursor X/Y, **SDL_MOUSEBUTTONDOWN** and **SDL_MOUSEBUTTONUP** from the same SDL pointer.
   - Its `poll` uses `normalize_absolute_axis(..., 0, window_width/height-1)`; its `configure` exports two axes plus buttons as `DEVICE_CLASS_LIGHTGUN`.
   - `sdl_mouse_device` uses **relative** motion; this is the wrong primary coordinate source for a direct touchscreen stylus.
2. MAME `src/emu/ioport.cpp`: `IPT_LIGHTGUN_X/Y` are **absolute, non-autocentering** analog fields; `-lightgun_device lightgun` enables the relevant input class. MAME `src/emu/emuopts.cpp`: `-mouse` and `-lightgun` default disabled unless enabled or auto-selected. The MAME manual cautions that enabling both for the same physical pointer may behave strangely; do not rely on a dual-stream binding.
3. The previous driver used `IPT_LIGHTGUN_X/Y` but `PORT_CODE(MOUSECODE_BUTTON1)`, i.e. coordinates and trigger from different classes. The **only functional source change** of this increment is to use `PORT_CODE(GUNCODE_BUTTON1) PORT_PLAYER(1)`, with PENX/PENY still `IPT_LIGHTGUN_X/Y` player 1. Original PF1/PG2/SPI2 behavior and provisional 12-bit ADC sample math remain unchanged.
4. Native SDL GUI is **not running in the authorized headless test runner**; the SDL class behavior above comes from the pinned donor source. It is a prerequisite to, not a replacement for, live mouse testing.

## Recommended interactive launch profile (future, single DIAG only)

The same single `dana-diag` candidate, **when specifically approved for an interactive session and natural guest testing**, should use MAME SDL's lightgun-class pointer interface, e.g.:

```bash
/path/to/the/existing/dana-diag asmdana \
    -noreadconfig -window \
    -lightgun -lightgun_device lightgun -lightgunprovider sdl -nomouse
```

This profile is an **interface contract**, not a claim that the current restored qualified 012-C binary contains F2. That earlier binary was restored after the previous successful GCC15 single-object host-MMIO test. Use existing authorized F2 candidate build on the **same** DIAG before trying live GUI. No new executable, global MAME configuration or installer. Control presence and visual screen location (padding/scaling) must be evaluated under an actual display, not assumed from a headless session.

Mouse left-button down = Dana pen contact low on PF1; hold and move = new X/Y ADC readings; release = PF1 high. In all three states the host never writes an EmuTOS mouse packet. EmuTOS generates its own mouse events, subject to the guest reaching `dana_poll_touchscreen`.

## Verification hierarchy

- **PREVIOUS PASS:** GCC15 sole `alphasdana.o` compile + original Clang link, two F2 method tests and HOST-origin real MAME MMIO on prior F2 source pin `09f171b...`. Candidate then restored; previous PASS cannot be directly inherited by this revised input binding for interactive use.
- **THIS INCREMENT:** New input binding source at `src/mame/skeleton/alphasdana.cpp` SHA256 `f1f3c58efcc51f0f8b190c5d9672c502fbb7d6cddef33a8694d6c1ce7702c42f`; three F2-directed cases, adding `test_sdl_pointer_reuses_single_absolute_lightgun_input`. Exact test suite updated in the SAME 017 job to require 3, with static SDL-provider evidence before modifying source on T. **A definitive 3/3 result was not returned by Commander during this intervention**, so do not report PASS.
- **ALREADY CONFIRMED:** The five synthetic tests of the guest CPU evidence checker passed on T (5/5). These qualify only the checker, NOT natural guest CPU or interactive mouse.
- **NEXT NATIVE:** Run the guarded 017 job only once in sole DIAG, and accept only an actual new GCC15 driver compile, Clang link, directed tests, host MMIO and original EmuTOS guest CPU trace receipts; identify NOT_REACHED versus F2_FAIL.
- **FINAL INTERACTIVE:** Verify host pointer mapping, PF1 press/release, PG2 select, 8+16 SPI2 command transactions, eight-sample guest raw read, mousevec events, cursor X/Y position, click and drag while visually displaying the original guest framebuffer. No one of these outcomes can be inferred solely from MAME input definition.

## Explicit guest dependencies not to fix by guessing

- Original `bios/dana.c` declares `static LONG screen_calibration[7]` and applies its affine mapping in `dana_poll_touchscreen` **only if `c[0]` is non-zero**; `dana_ts_calibrate` copies coefficients, and `bios/mouse.c` exposes `ts_calibrate`. Whether the guest initializes them before a particular UI session is **NOT PROVEN**. Do not arbitrarily hard-code screen scaling in MAME to conceal missing guest calibration.
- `dana_ts_rawread` samples X/Y eight times, increments count only while PF1 remains active and then divides by count. Release during the loop could produce count=0; verify with actual guest and avoid modifying guest or simulating false PF1 values.
- The ADC mapping currently clamps raw X to 290..3760 and Y to 200..3650 and is **provisional**, not factory-calibrated. The GUI display is 560×160 but host-window absolute axes need viewport/aspect validation. Do not claim pixel-accurate click until it is observed.
- Guest boot has been partially qualified historically, but normal touchscreen polling and UI mousevec have NOT been demonstrated on the original firmware.

## No gate inflation

This is part of the **existing F2 workstream**, not an extra independent project/gate. Mouse integration is a very small reuse of the existing MAME input stack. Continue with F3/F4 only after proper F2 scope closure; retain the user's no-blind-tests, no-duplicate-DIAG, five-Commander-calls-per-intervention maximum and no-recurring-polling rules.
