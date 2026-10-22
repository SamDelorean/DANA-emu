# F2 — Host mouse as Dana stylus: native MAME input route

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
