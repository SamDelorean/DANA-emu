# GUI-026 — Dana / AS2K Writer shared blink cadence

**2026-10-24; BUILD PASS on the sole installed Dana DIAG; USER_MANUAL_VISUAL_PASS__CLOSED (AUD-045).**

## Authoritative origin (read U19 records first)
- AS2K Writer visual contract frozen 2026-10-03: TEXT = **380 ms** and MASK = **190 ms** per phase, total **570 ms**, explicitly app-independent.
- AS2K Git commits [547f65fe](https://github.com/SamDelorean/AS2K-V3.14.x/commit/547f65fe8a9d9350909c43c28867f0056ddf1ae5) and [780dfc81](https://github.com/SamDelorean/AS2K-V3.14.x/commit/780dfc812280ca4ac537154db83c9d245357868d) are the verified source. AS2K used MAME visual qualification at 50 Hz (TEXT typical 380ms, MASK ~190ms).
- The older Dana GUI-025 cadence was 600 ms shown / 400 ms hidden. User directed consistency across projects, so this **supersedes only that timing**, not the original GUI-025 functional PASS or other code.

## Actual minimal change in the same DIAG
- Patch [026 timing-only](../patches/026_dana_cursor_as2k_writer_380_190.patch), **one** source file `src/osd/sdl/window.cpp`:
  - old: `((idle - 500U) % 1000U) < 600U`
  - new: `((idle - 500U) % 570U) < 380U`
- The initial 500 ms visible grace after motion is intentionally unchanged. Cursor remains shown on movement, off while outside the focus as in existing 025; **lightgun input, EmuTOS, all PENX/PENY, driver and calibration unchanged**.
- Proof from actual authorized T job `026_dana_cursor_as2k_380_190.job.sh`: original DIAG SHA-256 `1715a4820ed32fafda5ba18f54d4491bc8ae6686f5817a85e99ccb7e871c33d3`, source `window.cpp` SHA-256 `1584c9a4fb86fb09a8f7e6ef15dcf7517484f7c7ae263f825c46e97c3e3e2a92`; both checked before editing.
- Clang 21.1.8, MAME incremental make -n and build both rc0. Plan identified 1 compile step. Reused `build/dana-diag`, compiled and relinked **only existing `dana-diag`**, no extra MAME trees or EmuTOS builds.
- New installed DIAG SHA-256 **`51dddb7de0728fd796364039ac56409f50e292c4baea1ffa39aaf96b7c2c5937`**. EmuTOS 024C SHA-256 `eaf3d25cd32a21a9bcfa5cb71756dba749d611c73ed88259444a8ca7aabf67cd` and Dana driver SHA-256 `8e88d36d9d5b1e7574b7d5d58683975aa78ae94f6baf8213a311236707975e21` were preserved.
- Evidence: [Drive GUI-026 receipts](https://drive.google.com/drive/folders/13KAj9uTC73DM24d8yuGpC9EN4plZ0w1t) including `result.json`, source delta, Clang incremental log, gzip rollback of previous executable.
- Canonical master [v4.8 AUD-045](https://docs.google.com/spreadsheets/d/1B7KFKL4BsQZUQ0kSaqdm2ygv835tPE9l/edit).

**Qualification — AUD-045 (2026-10-24):** BUILD_PASS was verified in AUD-044; the user then directly reported **“prueba ok”** after the manual visual check on the installed 026 DIAG. This closes GUI-026 as **USER_MANUAL_VISUAL_PASS__CLOSED**. Nominal 380/190 ms timings come from verified source and the AS2K contract, **not** an instrumented stopwatch measurement. No new build, guest run or remote action is needed. GUI-025S remains a valid historic baseline. Never infer GUI/mass-storage APP PASS from this cursor check.

**Cross-project UI policy:** Where a blinking high-contrast selection or visibility indicator is intentionally used, prefer the established AS2K 380/190 ms readability rhythm over inventing independent cadence values; assess different UX patterns on their merits, not an unconditional requirement that all timeouts be 380/190.
