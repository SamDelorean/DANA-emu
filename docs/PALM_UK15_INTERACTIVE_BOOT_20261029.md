# Dana Palm UK1.5: reproducible graphical boot profile (2026-10-29)

Authoritative single emulator repository: `DANA-emu`, branch `main`; no standalone clones or branches. No source-code modifications were required for the observed splash blockage.

## Cause and evidence

The 2026-10-29 manual run used the *default* virtual board settings: `NOR_PROFILE=0`, `NOR_FACTORY=0`, SDIRQ lines released. The original UK1.5 firmware updater provides 6,094,848 bytes, not a complete 8 MiB Flash image. Without the previously qualified opt-in NOR fixture, the original CPU stayed in startup polling at PC about `0x1007B09x`, LCD fingerprint `C29080CC` through frame 2400 (AlphaSmart logo). The nominal emulation speed was about 99.5%, so the result was not due to a slow host.

The known qualified configuration from the previous native Palm test explicitly selects `NOR_PROFILE=1` (M28W640HCB profile), `NOR_FACTORY=1` (missing top NOR addresses behave as erased `FF`), and both `SDIRQ` PD2/PD3 pin levels low. This is an **experimental factory-NOR assumption**, not a complete verified physical Flash dump or a claim about every real Dana. The original ROM remains unchanged.

`config/palm-uk15/asmdana.cfg` contains this configuration; the installed T runtime `runtime/dana_timer_uart_irq_hmkem769/mame-stage/diag/cfg/asmdana.cfg` has been updated to match. Other profiles and driver defaults must not be silently reclassified as authentic Dana hardware.

## Exact regression (native original ROM, same diag binary)

| Frame | Previously observed FNV | Corrected FNV | Interpretation |
|---|---|---|---|
| 600 | `C29080CC` | `84D040AF` | Original startup advances |
| 1400 | `C29080CC` | `0521063B` | Palm OS Setup screen |
| 1800 | `C29080CC` | `B395EBF3` | `Setup 1 of 4` |
| 2400 | `C29080CC` | `B395EBF3` | Waiting for genuine user input |

Runtime traces: `local-evidence/runtime-compare/current.log`, `current-with-config.log`, `fixture-factory.log`, `canonical-default-pass.log`. Original canonical proof: `docs/UK15_ROM_BOOT_SD_SPI_GHIDRA_PANORAMA_20261026.md`, section R. Host-only regression used the existing `lcd_framebuffer_native.lua`, verified the actual 68000 bus and byte-for-byte historical frame hashes. No new emulator was created.

## Interactive execution on T

From `/home/spc/Projects/alphasmart/DANA-emu/runtime/diag`:

```bash
./bin/dana-diag asmdana -rom ./work/uk15_qualify_20261025/UK15_private.raw -cfg_directory ./cfg -window -nomaximize -lightgun -lightgun_device lightgun -lightgunprovider sdl -nomouse
```

Await `Setup 1 of 4`. Attempt a real left-button tap inside the LCD. Palm touchscreen delivery and `Setup 2 of 4` are **not yet qualified**. The power key is host `Pause`, but `Setup 1 of 4` was observed by frame 1400 **before** the scripted power key at frame 1600, so it is **not required to get past the logo**.

## Single authorized executable (2026-10-29)

The **only active executable** is `runtime/diag/bin/dana-diag` (SHA-256 `50487355727baab96b93acaebc108cb40deb2d7fc00c0fec225f7e96a5dae9de`). The previously misleading executable name `source/danadiagd` is retired. The runtime tree no longer contains the old isolated increment directory name. Only `main` of `SamDelorean/DANA-emu` is operational. Original MAME source is under `runtime/diag/source`; historical files are archival evidence, not alternate build trees or runnable products. The original UK1.5 frame-1800 hash `B395EBF3` was requalified with this exact `dana-diag` executable.
