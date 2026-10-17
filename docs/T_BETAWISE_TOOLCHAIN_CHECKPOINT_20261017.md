# T640 — BetaWise m68k-elf compiler reuse checkpoint (2026-10-17)

> **LATEST VERIFIED RESULT — 2026-10-17 11:59 America/Mexico_City — PASS_OS3K_COMPILER / BLOCKED_EMUTOS_MSHORT.** One explicitly authorized Commander call launched the exact previously staged single job on canonical T through `/home/spc/.local/bin/dcjob launch` (deviceId `dee0b4b6-578a-41a5-88de-73dbeb808983`); PID 252022 was the dispatch receipt. The job moved from inbox to archive. `dcjob` reported PASS/exit 0/9 seconds; independent job evidence confirms `PASS_OS3K`: existing `/home/spc/.local/bin/m68k-elf-gcc`, `m68k-elf` target, GCC **16.1.0**, actual object compile `-m68000 -ffreestanding -fshort-enums -c` exit 0, zero symlinks created, zero other changes. `m68k-elf-gcc -print-multi-lib` returned only `.;`, so **EmuTOS `-mshort` multilib is unavailable** (`BLOCKED_NO_MSHORT_MULTILIB`). This is not an EmuTOS guest build, or proof of full OS3K applet link; it qualifies the existing **compiler and M68000 compilation**. Never alter or rebuild this working OS3K compiler to satisfy EmuTOS; use an isolated compatible MiNT toolchain for the guest. Independent downloaded archive SHA-256: canonical dcjob `e928c6ae918cccc262b7cc282bf12cc94225dd0273cd9b94325fea79d0cddf38`; program evidence `cfc40be29fd85356c5e45796f01e07003fad613045c6ebbba14cdc4196a5b891` (both match Drive checksum files). [dcjob summary](https://drive.google.com/file/d/1TLDv0Rck7IICwaw8BYjPzw3k3soFb5xT/view), [dcjob package](https://drive.google.com/file/d/1GSQjmA0MwKfBDQQMYfRa810idZeDAEAL/view), [guest-independent compiler evidence](https://drive.google.com/file/d/1V1qOyvBOrWdZl_qI494bFazNq7dfdKDw/view). **Commander used 1/3 calls in this intervention, the other 2 are not standing authorization for another phase.**

**Cross-project objective:** Confirm that the already-used BetaWise/OS3K GCC toolchain is functional on canonical T and, if necessary, expose a verified existing user-owned installation from `/home/spc/.local/bin` for future OS3K work. This is separate from proving EmuTOS-Dana's stricter `-mshort` linker ABI.

## Source-based findings

- **Verified historical T filesystem inventory, 2026-09-28:** `/home/spc/Projects/alphasmart/betawise`, `betawise-abi`, `betawise-os3k`, and their `m68k-elf` source directories are present. The inventory did **not** audit installed `m68k-elf-gcc` executables, so compiler availability on T is still **UNKNOWN**.
- **[BetaWise m68k-elf/Makefile](https://github.com/SamDelorean/betawise/blob/ad557fcf4efbf07fcf0ff3f398a71a7987b7a41c/m68k-elf/Makefile):** compiler target `m68k-elf`, CPU M68000, default user-local installation prefix `$HOME/.local`, currently declared GCC 16.1.0, `--disable-multilib`.
- **[BetaWise Makefile.common](https://github.com/SamDelorean/betawise/blob/ad557fcf4efbf07fcf0ff3f398a71a7987b7a41c/Makefile.common):** application flags include `-mpcrel -ffixed-a5 -fshort-enums`. This is not proof of `-mshort`.
- **[Pinned EmuTOS Makefile](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/Makefile):** `ELF=1` selects `m68k-elf-gcc`, but EmuTOS always requires `-m68000 -mshort` and compatible `-lgcc`. A usable OS3K compiler does not prove EmuTOS compatibility.
- **Drive shared inbox (checked 2026-10-17):** holds `energy_r13a_mame_requalify_r6_isolated_rebuild_20261017.job.sh` belonging to another workstream; **it was not displaced, modified, or executed**. No Commander calls were used.

## Single-job verification and safe enablement — PREPARED, NOT EXECUTED

**Verified Google Drive HOLD file:**

[000_dana_betawise_toolchain_probe_enable_20261017.job.sh](https://drive.google.com/file/d/1JpVeiS6tpuxdZr7Kl5kPxurRpPVGswTc/view)

- Path: `AS2K_TEMP/COMMANDER_PIPELINE/hold/000_dana_betawise_toolchain_probe_enable_20261017.job.sh`
- **SHA-256:** `bb0ed845323b28158539f964bd96bb702a38bee63e929dc209e2c0a07ae8e663`
- **Verification:** Shell syntax and embedded Python syntax PASS; Drive upload/readback bytes exact-match PASS (both SHA-256).
- **Execution:** NOT EXECUTED. No T state has been observed or changed.

The job, when separately approved for actual canonical launch, will:

1. Check only known installed executable locations (current PATH, `$HOME/.local/bin`, `/usr/local/bin`, `/usr/bin` and known user-local toolchain prefixes) without `find`/sudo/system probes.
2. Verify native binary execution, ELF cross target `m68k-elf`, and a real M68000 OS3K-compatible C compilation (32-bit int/long, `-fshort-enums`).
3. If an installation is valid, create **only missing, non-clobbering, user-owned** symlinks in `/home/spc/.local/bin` where necessary; never overwrite existing programs, source checkout, system paths or other projects.
4. Independently record whether `-mshort` and linked `-lgcc` work for EmuTOS, without downgrading a working OS3K compiler if that separate test fails.
5. Save bounded logs, command exit codes, manifest, and SHA-256 package; send results to the canonical Drive outbox.

If no executable exists in the inspected known paths, it reports `BLOCKED_NOT_INSTALLED`. It does **not** silently build/install a new GNU GCC 16 toolchain or modify BetaWise checkouts. Provisioning a genuinely absent compiler requires a separately scoped, source-pinned installation decision based on that result. The user's instruction to keep the compiler reusable for later OS3K work is preserved.

## Authorization and next action

The shared inbox is **occupied**. Under the canonical Remote Desktop Commander rules, do **not** displace that foreign job or use direct probing as a workaround. When the inbox is legitimately available, stage exactly the verified HOLD file as the single intended job and launch via `/home/spc/.local/bin/dcjob launch` on device ID `dee0b4b6-578a-41a5-88de-73dbeb808983` **only under the applicable explicit Commander call authorization**. Verify its actual result through Drive before claiming installation/ready status.

**Historical pre-dispatch status (superseded):** `PREPARED_HOLD / BLOCKED_SHARED_INBOX`. The verified result at the top of this file is now authoritative. DANA-emu F1 source and OS3K project implementation remain untouched.
