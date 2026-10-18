# D3 pre-research — AlphaSmart Dana LCD hardware compatibility and implementation contract

**Research checkpoint:** 2026-10-17. **Status:** STATIC RESEARCH VERIFIED / LCD DRIVER AND NATIVE VIDEO UNRUN. This is an advance-preparation document only; does not replace the current D2.2 GPIO qualification. No T, Commander, emulator, original ROM build or source driver change was made.

## 1. Authority and exact source pins

1. **Motorola/NXP MC68VZ328UM/D** (official): [manual](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf), Ch. 8 §§8.2–8.3, especially pp. 8-3–8-20, 8.2.2.3 pixel mapping, 8.2.4 DMA, Tables 8-2–8-16. [Official addendum MC68VZ328UMAD/D](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf), Rev.7, corrects LCD FRM naming and the **LRRA register's address, width and reset**. For controller register layout and electrical interface, prefer these over EZ MAME and POSE.
2. **Real Dana EmuTOS port** `davidgiven/emutos@9c42ef0f2c2fa9d1e217fced9da68901b2326e8b`: [`bios/dana.c`](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c), [`bios/dana.h`](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.h), [`bios/dana2.S`](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana2.S), [`bios/screen.c`](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/screen.c).
3. **Actual Dana hardware model**, read-only reference: `csnover/Retro68@d917b67b16bef7bcf5c75a74f617710c32addcbc`, [`PalmUtils/poser/SrcShared/Hardware/EmRegsVZAlphaSmart.cpp`](https://github.com/csnover/Retro68/blob/d917b67b16bef7bcf5c75a74f617710c32addcbc/PalmUtils/poser/SrcShared/Hardware/EmRegsVZAlphaSmart.cpp) and .h. MAME may not copy GPL code without license review.
4. **Existing MAME parts, donor SOURCE ONLY, not an executable authorized for testing:** `SamDelorean/mame-as3k@c4e48388ca620472643110db2941ce70aa5f3c07`, [`src/devices/video/mc68328lcd.cpp`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/video/mc68328lcd.cpp), [header](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/video/mc68328lcd.h), [`src/devices/machine/mc68328.cpp`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.cpp), [`src/mame/palm/palm.cpp`](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/palm/palm.cpp). The donor already has an LCD *panel* device, screen, palette, MAME timers and frame update examples; the Dana VZ LCD *controller* is not yet present in `alphasdana.cpp`.
5. **Historical display variant caution:** 2002–03 AlphaSmart-era secondary reviews advertise the original Dana's 560x160 backlit LCD with 4 grayscale shades, and later Wireless/machine revisions with differing grayscale capabilities. This source study **only certifies the pinned EmuTOS-Dana guest's B/W 1bpp path**. Do not infer one physical panel part number/pinout or that all Dana variants use identical grayscale hardware.

## 2. Physical interface versus framebuffer — do not conflate them

- The DragonBall VZ has a **memory-reading LCD controller**, continuously scanning from an **LCD DMA framebuffer address** in guest RAM. It serializes the pixels onto `LD[3:0]` using `LCLK`, `LLP` (line pulse), `LFRM` (frame marker, renamed from LFLM/FLM by the addendum), and `LACD` (alternate crystal drive). 4 physical data wires **do not mean 4 bits per pixel**. The pinned guest sets **`LPICF=0x08` = PBSIZ `10b` = 4 data lines and GS `00b` = monochrome 1bpp**.
- The screen is **560 x 160** per `DANA_SCREEN_WIDTH`/`DANA_SCREEN_HEIGHT`; the framebuffer is **70 bytes per line x 160 = 11,200 bytes** (5,600 16-bit words). The hardware streams **140 4-pixel groups per line**, not 560 physical shift-clock groups, for this 4-bit interface. Source pixel order for 1bpp is **MSB-first within each guest byte** per Motorola Figure 8-4.
- The monochrome controller supports single-panel STN LCDs up to **640 x 512** (Motorola §8.2.2); Dana's 560x160 fits. Frame rate matters to a physical panel (~50–70 Hz per §8.2.4) but do not invent its measured crystal, actual LCDCLK or full analog panel refresh characteristics. For a DIAG logical renderer, schedule a defensible configurable refresh and document approximation until virtual clock tree is qualified.
- **Not needed for the first software-rendered framebuffer:** exact manufacturer model of the glass/controller bonded to the panel, LCD cable pinout, physical bias voltage, external contrast DAC, touch digitizer or keyboard/ST controller. Those are distinct concerns and must be measured/identified before any real hardware replacement claim.

## 3. Verified EmuTOS software register sequence (source-predicted; not all CPU-observed)

`bios/screen.c` calls `dana_screen_init()` and later `screen_init_address()` eventually calls `dana_setphys(screen_start)`; this final call writes `LSSA=(ULONG)addr`. Do not assume LSSA is nonzero when the very first LCD enable occurs. `dana_initial_vram_size()` returns 11200.

`bios/dana.c::dana_screen_init()` executes:
```text
PCSEL=00; PCPDEN=00;
PFSEL |= 01; PKSEL |= 90; PKDATA |= 90;
LCKCON=00; LPICF=08; LVPW=23; LXMAX=0230; LYMAX=009F;
LPOLCF=00; LACDRC=00; LPXCD=03; LCKCON=80; LRRA=0050; LPOSR=00;
dana_set_lcd_contrast(100);
```
EmuTOS *also* writes a guest-managed framebuffer pointer to `LSSA` later; this is required for a meaningful screenshot and must not be fabricated by the host.

**MMIO map / guest writes for the D3 logical display contract:**

| Register | VZ address | Width | Source-predicted value / behavior | Why required |
| --- | --- | --- | --- | --- |
| `LSSA` | `0xFFFFFA00`–`03` | 32b | Real guest framebuffer pointer (not fixed) | DMA screen base; `LSSA[0]` reserved; 1-MiB boundary rule |
| `LVPW` | `0xFFFFFA05` | 8b | `0x23` (35 words/row) | **70-byte stride** |
| `LXMAX` | `0xFFFFFA08`–`09` | 16b | `0x0230` (560 pixels) | Width, multiple of 16 per UM |
| `LYMAX` | `0xFFFFFA0A`–`0B` | 16b | `0x009F` (159; height 160) | Last-row index |
| `LPICF` | `0xFFFFFA20` | 8b | `0x08` | 4 physical data wires; 1bpp |
| `LPOLCF` | `0xFFFFFA21` | 8b | `0x00` | Pixel and clock/line/frame polarities |
| `LACDRC` | `0xFFFFFA23` | 8b | `0x00` | Alternating-crystal direction (panel timing) |
| `LPXCD` | `0xFFFFFA25` | 8b | `0x03` | Pixel clock divider = 4 |
| `LCKCON` | `0xFFFFFA27` | 8b | `0x00` then `0x80` | Actual LCDON bit7 on/off |
| `LRRA` | **`0xFFFFFA28`–`29`** | **16b** | `0x0050` | **UMAD corrected** word-sized refresh control; reset `0x00FF` |
| `LPOSR` | `0xFFFFFA2D` | 8b | `0x00` | No horizontal pan; mask bits3:0 |

**Critical VZ/EZ pitfall:** the authoritative addendum explicitly corrects `LRRA` to **A28, 16 bits, reset 00FF**. Never import an EZ model using A29 byte. `LSSA` requires alignment and must not cross a **1 MiB memory boundary** while containing the complete framebuffer (Motorola §8.3.1). Enforce legitimate RAM bounds; do not create a 24-bit alias or blanket FAxx MMIO page.

When physical display power is relevant: `PKSEL` (`0xFFFFF443`) selects GPIO for **PK7/PK4**; `PKDATA` (`0xFFFFF441`) uses **bit7 LCD power** and **bit4 backlight**. This exact mapping is corroborated by pinned `EmRegsVZAlphaSmart.cpp::GetLCDScreenOn/GetLCDBacklightOn`, each checking Port K data `0x80/0x10`. Model distinct display-on/backlight states; do not treat backlight as required for framebuffer scan or fabricate missing GPIO input/direction effects.

**Less obvious, confirmed contrast dependency:** `bios/dana2.S::_dana_set_lcd_contrast` sends an **8-bit command bit-serially** using `PFDATA` (VZ `0xFFFFF429`, **PF6 / 0x40 = data**) and `PKDATA` (`0xFFFFF441`, **PK6 / 0x40 = clock, PK3 / 0x08 = command/strobe**). This is *not the same thing* as merely writing `PWMR=0xFFFFFA36`. There may be many read/modify/write GPIO accesses from that routine; implement the pin-state behavior from documented sources if the authentic CPU encounters them. A first logical renderer need not generate an analog bias voltage.

## 4. MAME reuse and an essential pre-integration audit

Pinned `src/devices/video/mc68328lcd.cpp/.h` supplies an MAME panel sink with `flm_w`, `llp_w`, `lsclk_w`, `ld_w`, `lcd_info_changed`, `video_update`, palette, screen and save-state plumbing. Pinned `src/mame/palm/palm.cpp` demonstrates `SCREEN(config,...).set_lcd()` plus `MC68328_LCD`. These can be reused **inside the same Dana DIAG**, never by executing another emulator.

**Source-level reuse compatibility CONFIRMED for 4-bit pixel packing (native Dana qualification still pending):** the generic donor's `mc68328.cpp::lcd_get_panel_bit_size()` derives **4** from `LPICF=0x08` (`PBSIZ=10b`), so `lcd_scan_tick` takes **`case 4`**, packing *four consecutive monochrome pixel bits into each LD[3:0] nibble*. Its `case 1` that forwards one pixel per tick is reached only for a 1-wire panel and **must not be mistaken for the Dana mode**. The panel sink `mc68328lcd.cpp::lsclk_w` expects `bus_width=4,bpp=1` and consumes all four pixel bits, so the source paths are compatible in packing. The 4-bit mode path is suitable for focused reuse inside **Dana DIAG**. Verify by a bounded `0xA5/0x3C` / walking-one / horizontal-stripe native round-trip test; that test is still UNRUN. One guest VRAM 16-bit word must produce **four** successive `LD[3:0]` groups, MSB-first. Remaining integration work is the *VZ register/timing model and wiring of this generator/sink*, not a speculative bit-packing bug. Neither component may be executed as a standalone alternative emulator.

**Pragmatic two-layer design:**
- **VZ display controller / MMIO:** authentic byte/word/long reads/writes, Motorola reset and writable masks, software values, status and clock-enable state, source-backed scan base/stride, hard memory bounds, device save-state. No software emulation of guest VDI or intercepted OS drawing commands.
- **Presentation endpoint:** monochrome 560x160 bitmap driven by guest RAM at LSSA (or by documented virtual-time 4-lane DMA signal generator feeding the reusable MAME panel sink). This is still native MAME hardware modeling, not host-painted fake output. If taking a direct bitmap route for the first milestone, explicitly document that cycle-accurate LCD DMA bus arbitration and LCLK/LLP/LFRM/LACD waveforms are deferred.

## 5. Specific fast-forward verification plan (no execution authorized by this research)

1. **STATIC_FIRST**: pin manual UM/UMAD, guest source and donor; qualify register addresses/bit widths, source predicted accesses and exact 4-lane pixel order. Preserve all F1/E3/D2.1/D2.2 PASS/UNRUN statuses as actually recorded.
2. **Isolated logic:** test MMIO masks/lanes/byte writes and LSSA pointer/stride, 560x160 geometry and 11200B payload. Use a **test-owned 1bpp framebuffer**, not private OS bytes, with all-zero/all-one, 0xA5/0x3C alternation, single-pixel walk, per-row boundaries, alternating rows, full 160th row, inversion polarity, two LSSA buffers and 1-MiB boundary rejection. Explicitly detect lost LCD lanes.
3. **Native Dana DIAG visual hardware fixture:** verified staged `.../diag/bin/dana-diag` ONLY; guest CPU writes LCD register sequence to real MMIO; 16-bit DMA or equivalent native RAM read pulls test bitmap from the MAME RAM mapping; test actual output pixel buffer/screenshot hash, save/reload and OFF/ON timing. Distinguish CPU-origin register operations from host fixture preparation. Test blank screen with LCDON=0, and clear progression after LCDON=1 plus valid LSSA; reject out-of-RAM/cross-boundary conditions with actual native evidence.
4. **Real immutable EmuTOS** once D2.2 and source-backed GPIO path permit: observe actual PC/order for screen init, exact real LSSA value, pixel memory writes and first real 560x160 frame; compare image pixels against VRAM dump. Do not require keyboard/ST or touch input for a first graphic; do not invent success or bypass a genuinely missing device.
5. **Full electrical/refresh precision later**: PLL-derived clock, 50–70 Hz timing validation, pin waveforms, LACD, analog contrast, PWM and hardware cursor/grayscale if guest later uses them. Touchscreen is a **separate input subsystem**. Physical panel part number/pinout and replacement compatibility remain **unknown**, not relevant to the first DIAG bitmap.

**No Codex agent was invoked and no runtime emulator test was run during this research.** When handing a subsequent LCD increment to Codex, give the user the **full exact copyable prompt** and require Codex to read these pinned sources first. Never use generic MAME, stable, or POSE as a test emulator: **dana-diag is exclusive**.

## 6. Supplemental pin-multiplex and donor-geometry audit — 2026-10-17

**Status: STATIC SOURCE AUDIT ONLY.** This supplements, rather than restarts, Sections 1–5. No emulator, T, Commander, Codex, ROM rebuild, product driver edit or D2.2 job was involved. **No D3 runtime PASS is claimed.** Immutable source pins remain those listed in Section 1.

### 6.1 Physical VZ pin function vs. Dana board control

The manufacturer MC68VZ328UM/D §§2.3/8.2.1 pin descriptions and current original-guest initialization together establish the following multiplexing. These are **VZ CPU pin functions**, not a proven pinout of the physical glass module or Dana LCD ribbon:

| VZ pins | Dedicated LCD signal in 4-bit mode | Dana-relevant constraint |
| --- | --- | --- |
| PC[3:0] | LD[3:0], four pixel-data wires | `PCSEL=0` selects dedicated functions; D2.2 currently models only the PCSEL configuration latch, not physical signal propagation. |
| PC4 | LFRM frame marker (older donor/manual spells FLM/LFLM) | Motorola UMAD requires the LFRM naming correction. |
| PC5 | LLP line pulse | This is frame/line timing, not a separate memory address/data bus. |
| PC6 | LCLK pixel shift clock | Separate from the CPU clock and LCD frame rate. |
| PC7 | LACD alternate crystal direction | Needed for electrically faithful STN waveforms, not for decoding an initial logical framebuffer. |
| PK[7:4] | LD[7:4] only for wider bus modes | In the currently evidenced 4-bit guest mode, Dana uses PK7 and PK4 as **board GPIO**, respectively panel enable and backlight. Do not indiscriminately switch to an 8-wire data bus. |
| PF0 | LCONTRAST dedicated function | Original EmuTOS writes PFSEL bit0, but the separate Dana-specific serial contrast transaction below must not be replaced with a fabricated PWM register write. |

Pinned `bios/dana.c` performs `PCSEL=0; PCPDEN=0; PFSEL|=1; PKSEL|=0x90; PKDATA|=0x90`. This gives the port-C D2.2 work a direct functional dependency in D3: **the PCSEL latch precedes actual LCD signaling, but its existence alone does not implement the LCD controller**.

The original `bios/dana2.S::_dana_set_lcd_contrast` bit-bangs **PF6 on PFDATA=0xFFFFF429 as serial data** and **PK6 clock / PK3 command-strobe on PKDATA=0xFFFFF441**. The pinned Dana-specific Retro68 POSE class separately corroborates **PK7=0x80 panel power** and **PK4=0x10 backlight**. Guest GPIO read/modify/write behavior must remain coherent; do not fake a ready/power state or assign LCD data pins to those GPIOs.

### 6.2 Critical MAME reuse boundary: 560 means 560, not 561

Pinned MAME `mc68328.cpp` contains both classic `mc68328_device` and `mc68ez328_device` LCD implementations. **They are not interchangeable with VZ register semantics**:

- The **classic** `mc68328_device::lcd_get_width()` returns `(LXMAX & mask)+1`, which would be **561** for Dana's `LXMAX=0x0230`: an off-by-one if copied unchanged.
- The **EZ** implementation returns `LXMAX & 0x03F0`, giving **560**, in agreement with manufacturer Table 8-4: VZ `LXMAX` is the actual pixel width, a multiple of sixteen. Its height remains **`LYMAX+1 = 0x009F+1 = 160`**.
- The **VZ** `LVPW=0x23` means **35 16-bit memory words per line**, hence 70 bytes, with 140 four-pixel shift groups per line. Do not use the classic `LLBAR`-dependent word-count calculation for Dana.
- The EZ-specific donor `lrra_w(u8)` on `0xFFFFFA29` is **not valid for VZ**; official UMAD fixes VZ LRRA at `0xFFFFFA28`, **16 bits**, reset `0x00FF`.

**Reuse split:** use the BSD-3-Clause `mc68328_lcd_device` panel sink (`flm_w`, `llp_w`, `lsclk_w`, `ld_w`, `lcd_info_changed`, `video_update`), MAME screen/palette/scheduler facilities, native CPU address space and DMA-style RAM reading. Implement a **VZ-accurate register/geometry/clock/pin generator** in Dana's own hardware path. Pinned `src/mame/palm/palm.cpp` provides working `SCREEN(config,...).set_lcd()`, `MC68328_LCD`, callback-binding and video-update integration examples, **source only**.

Test-owned 16-bit sample `0xA53C` must yield exactly four consecutive LD[3:0] values **A, 5, 3, C** (the first active pixel on LD3) and render 16 ordered 1-bpp pixels; prevent channel/polarity reversal or a 561st column. The donor `mc68328_lcd_device` saves panel timing/counters but its `m_lcd_bitmap` is not directly registered as a save-state item in the examined source. Therefore after a save/load, require a deterministic complete new scan/frame before asserting restored screenshot equivalence, rather than assuming the display bitmap itself was serialized.

### 6.3 Performance/refresh and distinct Dana models

At the manual's **general LCD refresh target 50–70 Hz**, the 1-bpp Dana frame entails:
- **11,200 guest-RAM bytes / 5,600 words per frame**, approximately **560–784 kB/s** of ideal raw frame-data reads.
- **22,400 four-pixel LD groups per frame**, approximately **1.12–1.568 million groups/s** averaged over a full frame. Actual shift-clock frequency requires blanking, PLL, LRRA and DMA scheduling; these are **not measured Dana clock rates**.
- An illustrative 60 Hz frame produces 672,000 bytes/s and 1.344 million groups/s, before hardware timing overhead.

The original Dana was reported with **560x160 and 4 grayscale shades** in specifications attributed directly to AlphaSmart (2003 review: https://the-gadgeteer.com/2003/06/19/alphasmart_dana_palm_powered_laptop_review/); contemporary Dana Wireless announcement advertises **16 grayscale shades** (https://www.palminfocenter.com/news/5583/alphasmart-announces-the-dana-wireless/). These are product-level reports, not validated exact glass controller part numbers or ribbon pinouts. The **actual immutable EmuTOS-Dana port configures `LPICF=0x08` (1bpp monochrome)**; neither historical product claim changes that first guest-functional contract. Support for 4/16 gray modes is a **separate, version-dependent future scope**, not a reason to defer D3 first pixels. The Motorola UMAD explicitly corrects the earlier mistaken product feature description of **color STN** to **single monochrome STN**.

### 6.4 Concrete pre-integration verdict

1. **Compatible now by source audit:** MAME's 4-line/1bpp serialization and panel sink; 560x160 screen infrastructure; standard MAME timer and memory APIs.
2. **Must be adapted to VZ before functional PASS:** LCD MMIO with accurate 8/16/32-bit widths and byte lanes, actual 560-pixel width, 35-word line stride, dynamically guest-written LSSA, 1 MiB image-boundary and 4 MiB RAM limits, LCDON-controlled scanning and selective GPIO mux/power semantics.
3. **Not required for first virtual screen:** glass vendor and flat-flex connector pinout, LCD bias voltages, electrical drive waveforms, real measured MHz, touchscreen/stylus, full grayscale palette, full Dana Flash cold boot.
4. **Acceptance:** test-owned CPU-origin MMIO + real 4 MiB guest RAM bitmap → exactly 560x160/1bpp at `dana-diag`, repeatability, off/on, multi-buffer LSSA and save/restore; then **unmodified EmuTOS-generated** frame only after real D2.2/GPIO blockers are resolved. Never substitute a host-painted image or another emulator.

**New source cross-checks:** [VZ manual](https://www.nxp.com/docs/en/user-guide/MC68VZ328UM.pdf) §§2.3, 8.2–8.3 and [UMAD](https://www.nxp.com/docs/en/user-guide/MC68VZ328UMAD.pdf); [pinned MAME CPU LCD scan](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/machine/mc68328.cpp) (`lcd_get_width`, `lcd_get_line_word_count`, `lcd_scan_tick`); [pinned MAME panel](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/devices/video/mc68328lcd.cpp) and [Palm wiring](https://github.com/SamDelorean/mame-as3k/blob/c4e48388ca620472643110db2941ce70aa5f3c07/src/mame/palm/palm.cpp); [original EmuTOS Dana](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana.c) and [contrast bit-bang](https://github.com/davidgiven/emutos/blob/9c42ef0f2c2fa9d1e217fced9da68901b2326e8b/bios/dana2.S); [pinned Dana-specific POSE](https://github.com/csnover/Retro68/blob/d917b67b16bef7bcf5c75a74f617710c32addcbc/PalmUtils/poser/SrcShared/Hardware/EmRegsVZAlphaSmart.cpp), consulted for behavior only (GPL). No third-party implementation code is copied.
