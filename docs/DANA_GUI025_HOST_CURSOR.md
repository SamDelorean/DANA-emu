# GUI-025 — Dana host cursor visibility/blink (SDL2, offline handoff)

**State: STATIC_PATCH_READY / BUILD_AND_NATIVE_PENDING — 2026-10-23.** All user machines are unavailable due to a power outage. No T, Commander, emulator run, or compilation was attempted. This file is an implementation specification, **not** proof that the host cursor works on the installed binary.

## Read first / qualified baseline
- Re-read the latest [Drive continuity](https://drive.google.com/file/d/1pmpnsCcsJOrRlst9kNbcD1Z-56eJ2mD-/view), original [master rector](https://docs.google.com/spreadsheets/d/1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l/edit), `docs/HANDOFF.md`, and native 024C evidence before further action (directive **U19**).
- The only authorized program to build/run is the **existing `dana-diag`** under `/home/spc/DANA_EMU_ISOLATED/dana_timer_uart_irq_hmkem769/mame-stage/diag`. Verified previous binary SHA-256: `cd4d7e3ae81f933dddb457152bdafb43e4bbcf605ea06726222f6abbb29269b4`.
- Keep EmuTOS 024C RAM guest **unchanged**: `/home/spc/DANA_EMU_ISOLATED/DIAG_EVIDENCE_ARCHIVE/DANA_GUI024C_20261023/emutos_calibrated_gem.dana`, SHA-256 `eaf3d25cd32a21a9bcfa5cb71756dba749d611c73ed88259444a8ca7aabf67cd`. Keep all seven default calibration coefficients. 024C GEM + menu click PASS manual; a brief rubber-band selection is only a tentative observation.
- Donor reference for this patch (read only): `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`. Pinned donor SDL blobs: `src/osd/sdl/window.cpp` `0e395fd1d62574c0edeb816c964492968585715a`, `src/osd/sdl/window.h` `5f55419a1543b935ebafc5d29f38728f22acb4be`. **Before applying patch on T compare installed stage source and SHA against these pins; do not overwrite changed local sources.**

## Implemented offline, not installed
- Patch: [`patches/025_dana_host_cursor_blink_sdl2.patch`](../patches/025_dana_host_cursor_blink_sdl2.patch), targeting **only two SDL2 window-management source files**, no Dana driver, PEN, EmuTOS, mousevec, GEM or CPU.
- Code path executes only for the MAME system name **`asmdana`**, SDL windowed mode and no MAME debugger. Other emulated systems and fullscreen retain standard MAME handling.
- It releases SDL relative/grab mode but continues using **existing genuine SDL mouse/lightgun events**, preserves host absolute axes and mouse buttons, and never injects guest mouse messages.
- Cursor visible upon movement and for the first 500 ms of inactivity; afterward cycles **600 ms shown / 400 ms hidden**. If the physical pointer leaves the window, normal visibility returns. While actively moving/dragging, the host cursor remains visible.
- Selection via environment variable, evaluated by the SDL window code: `DANA_HOST_CURSOR=blink` (or unset, default); `DANA_HOST_CURSOR=show` (always show while in window); `DANA_HOST_CURSOR=legacy` (original MAME hide/grab). This avoids changing MAME-wide configuration/options.
- Static check performed using both **exact Git donor files** and the patch fetched from `SamDelorean/DANA-emu`: four unified-diff hunks applied with **zero context mismatches or invalid line counts**, with unchanged files outside `window.cpp` / `window.h`. Timing expression checked at 0/500/1100/1500/2100 ms. **Static-only, no compilation.**

## One-scoped acceptance when T is available, requiring new execution approval
1. Recheck U19 and exact active source hashes, apply **only** this patch to the **single existing DIAG build tree** after clean dry run (`patch -p1 --dry-run`), without creating a second emulator or rebuilding EmuTOS. If the active source differs from donor, STOP and reconcile; do not force apply.
2. Compile/relink **only the necessary affected MAME SDL objects and the same DIAG executable** using the previously verified MAME build environment, object cache and bounded `-j3`; avoid a cold full MAME build. Record object delta, source SHA and resulting binary SHA.
3. Launch exactly the **024C** calibrated guest once in windowed mode, with SDL lightgun input as before. Confirm: physical pointer visible during movement; 600/400 blinking at rest; no SDL grab/relative trapping; cursor visible outside window; genuine EmuTOS pointer follows pen motion; clicking a known working GEM menu still succeeds.
4. Optionally exercise `DANA_HOST_CURSOR=show` and `legacy` only if the focused run warrants it; changes in cursor mode must **never** modify guest input. Note: clicking menus already passed on original 024C and need only a **single regression smoke** after SDL patch, not a repeated validation campaign.
5. Preserve original DIAG/guest and evidence. **Do not mark 025 NATIVE_PASS until the host window was actually tested.** Do not use Commander while machines are offline or without new explicit authorization.

**Exit condition for offline work:** patch and this handoff versioned; master records `025 STATIC_PATCH_READY / NATIVE_PENDING_POWER_OUTAGE` accurately. No new guest/run tests, no Drive inbox job submitted.
