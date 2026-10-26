// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors

#include "emu.h"
#include "isp1161_ptd.h"
#include "vz328_bootstrap.h"
#include "cpu/m68000/m68000.h"
#include "imagedev/snapquik.h"
#include "bus/generic/slot.h"
#include "bus/generic/carts.h"
#include "screen.h"
#include "util/hashing.h"
#include "alphasdana_sd_image.h"

// Minimal VZ-aware M68000 address-width carrier. The stock M68000 exposes
// only 24 address bits; the pinned MAME MC68EZ328 shows the exact native
// configuration technique for the VZ's high 0xFFFFFxxx MMIO addresses.
// This is NOT an MC68EZ328 peripheral or a physical Dana reset model.
class dana_vz_cpu_device;
DECLARE_DEVICE_TYPE(DANA_VZ_CPU, dana_vz_cpu_device)

class dana_vz_cpu_device : public m68000_device
{
public:
    dana_vz_cpu_device(const machine_config &mconfig, const char *tag, device_t *owner, u32 clock)
        : m68000_device(mconfig, DANA_VZ_CPU, tag, owner, clock)
    {
        m_program_config.m_addr_width = 32;
        m_opcodes_config.m_addr_width = 32;
        m_uprogram_config.m_addr_width = 32;
        m_uopcodes_config.m_addr_width = 32;
        m_cpu_space_config.m_addr_width = 32;
    }
};

DEFINE_DEVICE_TYPE(DANA_VZ_CPU, dana_vz_cpu_device, "dana_vz_cpu", "Dana VZ 32-bit-address M68000 (DIAG)")

namespace {

class alphasdana_state : public driver_device
{
public:
    alphasdana_state(const machine_config &mconfig, device_type type, const char *tag)
        : driver_device(mconfig, type, tag)
        , m_maincpu(*this, "maincpu")
        , m_guest(*this, "guest")
        , m_guest_ready(*this, "dana_guest_loaded")
        , m_screen(*this, "screen")
        , m_ram(*this, "ram")
        , m_keys(*this, "KEYS")
        , m_st_extended_keys(*this, "EXKEY%u", 0U)
        , m_pen_contact(*this, "PEN")
        , m_pen_x(*this, "PENX")
        , m_pen_y(*this, "PENY")
        , m_firmware(*this, "firmware")
        , m_boot_memory(*this, "boot_memory")
        , m_sd(*this, "sd%u", 0U)
        , m_sd_irq(*this, "SDIRQ")
        , m_pd7_pin(*this, "PDPIN7")
        , m_sdram_profile(*this, "PHYSRAM")
        , m_emubrk_pin(*this, "EMUBRK")
    {
    }

    void alphasdana(machine_config &config);
    DECLARE_INPUT_CHANGED_MEMBER(sd_irq_changed);
    DECLARE_INPUT_CHANGED_MEMBER(st_key_changed);

protected:
    virtual void machine_start() override ATTR_COLD;
    virtual void machine_reset() override ATTR_COLD;

private:
    // D7/D8.3: shared VZ SPI1 controller, two independent raw SD image devices.
    void spi1_reset();
    u16 spi1_r(offs_t reg);
    void spi1_w(offs_t reg,u16 data,u16 mem_mask);
    void spi1_irq();
    void spi1_schedule();
    TIMER_CALLBACK_MEMBER(spi1_complete);
    void sd_lines();
    void sd_gpio_irq();
    u8 pd_r(offs_t reg);
    void pd_w(offs_t reg,u8 value);
    u8 pd_extra_r(offs_t reg) { return m_pd_extra[reg]; }
    void pd_extra_w(offs_t reg,u8 value) { m_pd_extra[reg]=value; sd_gpio_irq(); }
    u16 ilcr_r() { return m_ilcr; }
    void ilcr_w(offs_t,u16 data,u16 mem_mask)
    { COMBINE_DATA(&m_ilcr); m_ilcr&=0x7777; spi1_irq(); }
    // D8.5: one CPU, two exclusive memory profiles. The firmware socket owns
    // unchanged raw bus-order bytes, never a fabricated reset stack or PC.
    DECLARE_DEVICE_IMAGE_LOAD_MEMBER(firmware_load);
    void firmware_unload(device_image_interface &image);
    void physical_reset();
    std::pair<std::error_condition,std::string> bootstrap_load(std::vector<u8> const &data);
    u16 bootstrap_ibuff_r(offs_t offset,u16 mem_mask);
    void bootstrap_ibuff_w(offs_t offset,u16 data,u16 mem_mask);
    u16 bootstrap_wait_r() { return m_bootstrap_mode ? 0x60fe : 0xffff; }
    void boot_postload();
    void physical_block(const char *reason, u32 address, u16 data=0);
    u16 physical_r(offs_t offset, u16 mem_mask=0xffff);
    u16 physical_mmio_r(offs_t offset, u16 mem_mask);
    void physical_mmio_w(offs_t offset, u16 data, u16 mem_mask);
    // Philips ISP1161(A) HC external 16-bit command/data bus: real Dana
    // UK1.5 initialization, not a fabricated USB packet engine.
    u16 isp1161_r(offs_t offset, u16 mem_mask);
    void isp1161_w(offs_t offset, u16 data, u16 mem_mask);
    void physical_w(offs_t offset, u16 data, u16 mem_mask);
    u32 cs_base(unsigned group) const { return u32(m_cs_base[group] & 0xfffe) << 13; }
    u32 physical_sdram_bytes() const { return (m_sdram_profile->read() & 1) ? 0x1000000U : 0x800000U; }
    u32 physical_sdram_index(u32 index) const { return index & (physical_sdram_bytes()-1); }
    // VZ UM 6.3.5 and Example 6-1: CSCTRL1.EUPEN extends CSD.UPSIZ
    // with DUPS2. The unprotected region begins at the CSD bank base.
    static constexpr u32 cs_ram_unprotected_bytes(u32 bank_size, u16 csd, u16 csctrl1)
    {
        unsigned const upsiz=(csd >> 11) & 3;
        // EUPEN=0: legacy VZ size is 32/64/128/256 KiB, independent
        // of bank size. EUPEN=1: DUPS2 forms UPSIZ[2] and the manual's
        // extended 2^(7-UPSIZ) bank divisor applies (Cloudpilot/POSE).
        if (!(csctrl1 & 0x4000))
            return 0x8000U << upsiz;
        unsigned const extended=upsiz | ((csctrl1 & 0x0010) ? 4 : 0);
        return bank_size >> (7-extended);
    }
    static constexpr bool cs_ram_read_allowed(u16 csd, bool supervisor,
        u32 offset, u32 unprotected_size)
    {
        return offset<unprotected_size || !(csd & 0x4000) || supervisor;
    }
    static constexpr bool cs_ram_write_allowed(u16 csd, bool supervisor,
        u32 offset, u32 unprotected_size)
    {
        return !(csd & 0x8000) && (offset<unprotected_size
            || (!(csd & 0x2000) && (!(csd & 0x4000) || supervisor)));
    }
    u32 cs_size(unsigned group) const
    {
        unsigned const siz=(m_cs_select[group] >> 1) & 7;
        // Motorola AN2148 Table 5 / VZ UM CSCTRL1.DSIZ3: CSD SIZ=000/001
        // with DSIZ3=1 selects 8/16 MiB, not the generic 32/64 KiB window.
        if (group==3 && (m_cs_select[3] & 0x0200)
            && (m_cs_control[0] & 0x0040) && siz<=1)
        {
            u32 const bank=(0x800000U << siz);
            return (m_cs_select[3] & 0x0400) ? bank*2 : bank;
        }
        return (group<2 ? 0x20000U : 0x8000U) << siz;
    }
    bool cs_hit(unsigned group, u32 address) const
    { return (m_cs_select[group] & 1) && !(cs_base(group) & (cs_size(group)-1)) && address>=cs_base(group) && u64(address)<u64(cs_base(group))+cs_size(group); }
    bool physical_ram_ready() const
    { return !(m_cs_select[3] & 0x0200) || ((m_dram[1] | m_dram[2]) & 0x8000); }
    u16 watchdog_r() { return m_watchdog; }
    void watchdog_w(offs_t, u16 data, u16 mem_mask);
    TIMER_CALLBACK_MEMBER(watchdog_guard);
    u8 scr_r() { return m_scr; }
    void scr_w(u8 data);
    u16 cs_r(offs_t offset);
    void cs_w(offs_t offset, u16 data, u16 mem_mask);
    u16 cs_select_r(offs_t offset) { return m_cs_select[offset]; }
    void cs_select_w(offs_t offset, u16 data, u16 mem_mask) { COMBINE_DATA(&m_cs_select[offset]); }
    u16 emucs_r() { return m_emucs; }
    void emucs_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_emucs); }
    u16 cs_control3_r() { return m_cs_control[2]; }
    void cs_control3_w(offs_t, u16 data, u16 mem_mask);
    u16 dram_r(offs_t offset) { return m_dram[offset]; }
    // Motorola AN2148: SDRAM initialization is the ordered IP, RE, MR
    // command sequence C83F -> D03F -> D43F. MR remains a register bit,
    // not a permanently active prohibition on subsequent SDRAM accesses.
    void dram_w(offs_t offset, u16 data, u16 mem_mask)
    {
        COMBINE_DATA(&m_dram[offset]);
        if (offset==1 && !(m_dram[1] & 0x8000))
            m_sdram_init_phase=0;
        if (offset!=2) return;
        u16 const commands=m_dram[2] & 0x1c00;
        if (!(m_dram[2] & 0x8000))
            m_sdram_init_phase=0;
        else if (commands==0x0800 && (m_dram[1] & 0x8000))
            m_sdram_init_phase=1;
        else if (commands==0x1000 && m_sdram_init_phase==1)
            m_sdram_init_phase=2;
        else if (commands==0x1400 && m_sdram_init_phase==2)
            m_sdram_init_phase=3;
        else if (m_sdram_init_phase!=3)
            m_sdram_init_phase=0;
        if (m_physical_boot && m_sdram_init_phase)
            logerror("DANA_SDRAM_INIT phase=%u sdctrl=%04x dramc=%04x\n",
                unsigned(m_sdram_init_phase),m_dram[2],m_dram[1]);
    }
    static bool firmware_vectors_valid(const u8 *rom)
    {
        u32 const pc=(u32(rom[4])<<24) | (u32(rom[5])<<16) | (u32(rom[6])<<8) | rom[7];
        return pc && !(pc & 1) && pc<0xfffff000;
    }
    static bool firmware_size_valid(u32 size) { return size>=0x20000 && size<=0x1000000 && !(size & 1); }
    void program_map(address_map &map) ATTR_COLD;
    void cpu_space_map(address_map &map) ATTR_COLD;
    void update_irq_lines();
    u8 irq_vector_r(offs_t offset);
    TIMER_CALLBACK_MEMBER(timer1_compare);
    u32 guest_system_clock_hz() const;
    u32 physical_system_clock_hz() const;
    u32 timer1_source_hz() const;
    void timer1_schedule();
    u16 timer1_tctl_r() { return m_tctl1; }
    // VZ Timer 2 shares the documented TCTL format; disabled configuration
    // is retained, but unsupported running-counter behavior is never faked.
    u16 timer2_tctl_r() { return m_tctl2; }
    void timer2_tctl_w(offs_t, u16 data, u16 mem_mask)
    {
        u16 const next=((m_tctl2 & ~mem_mask) | (data & mem_mask)) & 0x01ff;
        if (next & 1)
        {
            physical_block("TIMER2_RUNNING_UNIMPLEMENTED",0xfffff610,data);
            return;
        }
        m_tctl2=next;
    }
    void timer1_tctl_w(offs_t, u16 data, u16 mem_mask);
    u16 timer1_tprer_r() { return m_tprer1; }
    void timer1_tprer_w(offs_t, u16 data, u16 mem_mask);
    u16 timer1_tcmp_r() { return m_tcmp1; }
    void timer1_tcmp_w(offs_t, u16 data, u16 mem_mask);
    u16 timer1_tcr_r() { return m_tcr1; }
    u16 timer1_tcn_r();
    u16 timer1_tstat_r();
    void timer1_tstat_w(offs_t, u16 data, u16 mem_mask);
    u16 uart1_ustcnt_r() { return m_ustcnt1; }
    void uart1_ustcnt_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_ustcnt1); }
    u16 uart1_ubaud_r() { return m_ubaud1; }
    void uart1_ubaud_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_ubaud1); }
    u16 uart1_urx_r() { return m_urx1; }
    u16 uart1_utx_r() { return (m_utx1 & 0x1fff) | 0xe000; }
    void uart1_utx_w(offs_t, u16 data, u16 mem_mask);
    u16 uart1_umisc_r() { return m_umisc1; }
    void uart1_umisc_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_umisc1); }
    u16 uart1_prescaler_r() { return m_uart_prescaler1; }
    void uart1_prescaler_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_uart_prescaler1); }
    // VZ UM 5.2.4: pad drive strength only (0=2 mA, 1=4 mA).
    // Stored configuration has no effect on logical GPIO, bus or clocks.
    u16 iodcr_r() { return m_iodcr & 0x1fff; }
    void iodcr_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_iodcr); m_iodcr &= 0x1fff; }
    u16 icemcr_r() { return m_icemcr; }
    void icemcr_w(offs_t, u16 data, u16 mem_mask);
    u16 icemsr_r() { return m_icemsr; }
    void icemsr_w(offs_t, u16 data, u16 mem_mask);
    u16 pllcr_r() { return m_pllcr; }
    void pllcr_w(offs_t, u16 data, u16 mem_mask);
    bool pllcr_clko_enabled() const { return !(m_pllcr & 0x0010) && !(m_pfsel & 0x04); }
    // VZ UM 4.5.4: PCEN[7], reserved[6:5], WIDTH[4:0].
    // The UK1.5 write of 0x9f is a full-duty CPUCLK, not a sleep transition.
    u8 pctlr_r() { return m_pctlr; }
    void pctlr_w(u8 data);
    // Motorola MC68VZ328UM §15.4.1: PWM1 is the 8-bit audio PWM,
    // independent of LCD contrast PWMR at FFFFFA36.
    u16 pwm1_control_r();
    void pwm1_control_w(offs_t, u16 data, u16 mem_mask);
    // VZ PLLFSR, 0xFFFFF202: CLK32 is a virtual-time signal, not stored data.
    u16 pllfsr_r() { return (m_pllfsr & 0x4fff) | (m_clk32_high ? 0x8000 : 0); }
    void pllfsr_w(offs_t, u16 data, u16 mem_mask);
    TIMER_CALLBACK_MEMBER(clk32_tick);
    // VZ 11.2: RTC time-of-day uses MAME's host-seeded system_time,
    // exactly like other MAME RTC devices; no second independent counter.
    static constexpr u32 rtc_time_mask=0x1f3f003fU;
    static constexpr bool rtc_time_valid(u32 t)
    {
        return !(t & ~rtc_time_mask) && ((t>>24)&0x1f)<24
            && ((t>>16)&0x3f)<60 && (t & 0x3f)<60;
    }
    // Read the host-seeded clock on either 68000 word lane. A firmware
    // read of only the seconds half must not return an old timestamp.
    u16 rtc_time_r(offs_t offset)
    {
        rtc_sync_from_host();
        return u16(m_rtc_time >> (offset ? 0 : 16));
    }
    u32 rtc_host_seconds();
    void rtc_sync_from_host();
    void rtc_time_w(offs_t offset, u16 data, u16 mem_mask);
    u16 rtc_control_r() { return m_rtc_control; }
    void rtc_control_w(offs_t, u16 data, u16 mem_mask);
    u16 rtc_ien_r() { return m_rtc_ien; }
    void rtc_ien_w(offs_t, u16 data, u16 mem_mask);
    u16 rtc_isr_r() { return m_rtc_isr; }
    void rtc_isr_w(offs_t, u16 data, u16 mem_mask);
    void rtc_update_irq();
    TIMER_CALLBACK_MEMBER(rtc_tick);
    u16 icr_r() { return m_icr; }
    void icr_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_icr); m_icr &= 0xff80; }
    u16 imr_r(offs_t offset) { return m_imr >> (offset ? 0 : 16); }
    void imr_w(offs_t offset, u16 data, u16 mem_mask);
    u16 isr_r(offs_t offset) { return (m_pending & ~m_imr) >> (offset ? 0 : 16); }
    u16 ipr_r(offs_t offset) { return m_pending >> (offset ? 0 : 16); }
    void isr_w(offs_t offset, u16 data, u16 mem_mask);
    u8 ivr_r();
    void ivr_w(u8 data);
    // R-direct GPIO configuration, not a claim about electrical cold reset.
    void portc_reset() { m_pcdir = 0; m_pcdata = 0; m_pcpden = 0; m_pcsel = 0; }
    // VZ Port C direction: each bit 0=input, 1=output; PCSEL may override the pin.
    u8 pcdir_r() { return m_pcdir; }
    void pcdir_w(u8 data) { m_pcdir = data; }
    // VZ UM 10.4.3.2: writes always update the GPIO latch, even for input
    // or LCD-selected pins. A read reports actual pin levels, not the latch.
    u8 pcdata_r()
    {
        if ((m_pcsel & m_pcdir) != 0xff)
        {
            physical_block("PCDATA_PIN_LEVEL_UNQUALIFIED",0xfffff411);
            return 0xff;
        }
        return m_pcdata;
    }
    void pcdata_w(u8 data) { m_pcdata = data; }
    u8 pcpden_r() { return m_pcpden; }
    void pcpden_w(u8 data) { m_pcpden = data; }
    u8 pcsel_r() { return m_pcsel; }
    void pcsel_w(u8 data) { m_pcsel = data; }
    // VZ silicon reset is 0x87; this machine uses dbztool's R-direct 0xc5.
    void pfsel_reset() { m_pfsel = 0xc5; }
    u8 pfsel_r() { return m_pfsel; }
    void pfsel_w(u8 data) { m_pfsel = data; sd_lines(); }


    // Post-bootstrap GPIO output/configuration latches. The initial values
    // come from pinned dbztool/danainit.sh, NOT MC68VZ328 silicon reset.
    // External pen contact is modeled on PF1; SD IRQ pins are separate inputs.
    // Port order B, D, E, F, G, J, K, M; DIR/DATA/PUEN/SEL columns.
    void gpio_bootstrap_reset();
#define DANA_GPIO_PORT(NAME, INDEX) \
    u8 NAME##_r(offs_t reg) { return m_gpio[(INDEX)*4 + reg]; } \
    void NAME##_w(offs_t reg, u8 value) { m_gpio[(INDEX)*4 + reg] = value; }
    // Port B and K observe the ST controller reset/ready handshake.
    u8 pb_r(offs_t reg) { return m_gpio[reg]; }
    void pb_w(offs_t reg, u8 value);
    DANA_GPIO_PORT(pe, 2)
    // PF1 is the active-low pen IRQ input. Only override its DATA bit while
    // configured as GPIO input; software-driven PF1 retains its own latch.
    u8 pf_r(offs_t reg)
    {
        u8 value=m_gpio[3*4+reg];
        if (reg==1 && !(m_gpio[3*4] & 0x02) && !(m_pfsel & 0x02))
            value=(value & ~u8(0x02)) | ((m_pen_contact->read() & 1) ? 0 : 0x02);
        return value;
    }
    void pf_w(offs_t reg, u8 value) { m_gpio[3*4+reg]=value; sd_lines(); }
    // PG2 selects the external pen ADC, distinct from PE3 selecting the ST.
    u8 pg_r(offs_t reg) { return m_gpio[4*4+reg]; }
    void pg_w(offs_t reg, u8 value)
    {
        m_gpio[4*4+reg]=value;
        if (reg==1 && (value & 0x04))
        {
            m_pen_command=0;
            m_pen_sample=0;
        }
    }
    u8 pj_r(offs_t reg) { return m_gpio[5*4+reg]; }
    void pj_w(offs_t reg,u8 value) { m_gpio[5*4+reg]=value; sd_lines(); }
    u8 pk_r(offs_t reg);
    void pk_w(offs_t reg, u8 value);
    DANA_GPIO_PORT(pm, 7)
#undef DANA_GPIO_PORT

    // Genuine guest-visible SPI2 (VZ 0xF800 DATA / 0xF802 CTRL).
    // The controller models byte exchange with Dana's ST keyboard, not
    // a high-level key injection into the guest OS.
    u16 spi2_data_r() { return m_spi2_data; }
    void spi2_data_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_spi2_data); }
    u16 spi2_ctrl_r() { return m_spi2_ctrl; }
    void spi2_ctrl_w(offs_t, u16 data, u16 mem_mask);
    u8 st_exchange(u8 command);
    u16 pen_exchange(unsigned width, u16 outgoing);
    void st_input_reset();

    // Guest-owned VZ LCD configuration registers; the DMA-backed screen
    // reads real emulated RAM. No LCD IRQ, contrast voltage or clock emulation.
    u16 lssa_r(offs_t offset) { return offset ? u16(m_lssa) : u16(m_lssa >> 16); }
    void lssa_w(offs_t offset, u16 data, u16 mem_mask)
    {
        unsigned const shift = offset ? 0 : 16;
        u32 const lane = u32(mem_mask) << shift;
        m_lssa = (m_lssa & ~lane) | (u32(data & mem_mask) << shift);
    }
#define DANA_LCD_BYTE(NAME) \
    u8 NAME##_r() { return m_##NAME; } \
    void NAME##_w(u8 value) { m_##NAME = value; }
    DANA_LCD_BYTE(lvpw)
    DANA_LCD_BYTE(lpicf)
    DANA_LCD_BYTE(lpolcf)
    DANA_LCD_BYTE(lacdrc)
    DANA_LCD_BYTE(lpxcd)
    DANA_LCD_BYTE(lckcon)
    DANA_LCD_BYTE(lposr)
    DANA_LCD_BYTE(lgpmr)
    DANA_LCD_BYTE(lblkc)
#undef DANA_LCD_BYTE
#define DANA_LCD_WORD(NAME) \
    u16 NAME##_r() { return m_##NAME; } \
    void NAME##_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_##NAME); }
    DANA_LCD_WORD(lxmax)
    DANA_LCD_WORD(lymax)
    DANA_LCD_WORD(lrra)
    DANA_LCD_WORD(pwmr)
    // MC68VZ328 UM 8.3.5-8.3.8: true LCD cursor registers, with
    // reserved bits masked and the 68000 word's byte lanes preserved.
    u16 lcxp_r() { return m_lcxp; }
    void lcxp_w(offs_t, u16 data, u16 mem_mask)
    { m_lcxp=((m_lcxp & ~mem_mask) | (data & mem_mask)) & 0xc3ff; }
    u16 lcyp_r() { return m_lcyp; }
    void lcyp_w(offs_t, u16 data, u16 mem_mask)
    { m_lcyp=((m_lcyp & ~mem_mask) | (data & mem_mask)) & 0x01ff; }
    u16 lcwch_r() { return m_lcwch; }
    void lcwch_w(offs_t, u16 data, u16 mem_mask)
    { m_lcwch=((m_lcwch & ~mem_mask) | (data & mem_mask)) & 0x1f1f; }
#undef DANA_LCD_WORD
    u32 screen_update(screen_device &screen, bitmap_rgb32 &bitmap, const rectangle &cliprect);
    void lcd_bootstrap_reset();

    DECLARE_QUICKLOAD_LOAD_MEMBER(guest_load);
    required_device<dana_vz_cpu_device> m_maincpu;
    required_device<quickload_image_device> m_guest;
    output_finder<> m_guest_ready;
    required_device<screen_device> m_screen;
    required_shared_ptr<u16> m_ram;
    required_ioport m_keys;
    required_ioport_array<4> m_st_extended_keys;
    required_ioport m_pen_contact;
    required_ioport m_pen_x;
    required_ioport m_pen_y;
    required_device<generic_socket_device> m_firmware;
    memory_view m_boot_memory;
    required_device_array<dana_sd_image_device,2> m_sd;
    required_ioport m_sd_irq;
    required_ioport m_pd7_pin;
    required_ioport m_sdram_profile;
    required_ioport m_emubrk_pin;
    dana_sd::controller m_spi1;
    emu_timer *m_spi1_timer=nullptr;
    u16 m_spi1_word=0,m_spi1_control=0,m_spi1_received=0,m_ilcr=0x6533;
    u8 m_spi1_bits_left=0;
    u8 m_pd_extra[4]={},m_sd_last_pins=0x0c,m_sd_edges=0;
    bool m_spi1_busy=false;
    bool m_physical_boot=false, m_physical_blocked=false;
    bool m_bootstrap_mode=false; // VZ silicon EMUBRK asserted during reset
    u8 m_bootstrap_ibuff[32]={}; // 0x00FFFFC0 on-chip 32-byte buffer
    u8 m_scr=0x1c, m_flash_sha1[20]={};
    u16 m_cs_base[4]={}, m_cs_select[4]={};
    u16 m_cs_upper=0, m_cs_control[3]={}, m_emucs=0;
    u16 m_dram[4]={};
    // Philips ISP1161A1 Rev03 Tables 7 and 75. HC and DC each have an
    // independent 16-bit command/data bus and independently reset registers.
    u8 m_isp_cmd=0, m_isp_phase=0, m_isp_hc_read_phase=0;
    u32 m_isp_hc_regs32[0x17]={};
    u16 m_isp_hc_regs16[0x42]={};
    // A real 4-KiB host packet buffer, independent from Device FIFO.
    u8 m_isp_hc_ram[0x1000]={};
    u16 m_isp_hc_fifo_index=0, m_isp_hc_fifo_remaining=0;
    u16 m_isp_hc_fifo_cursor=0;
    u8 m_isp_hc_fifo_bank=0;
    u16 m_isp_hc_valid_bytes[3]={}; // ITL0, ITL1, ATL
    u8 m_isp_hc_itl_cpu_bank=0;
    void isp1161_hc_execute_buffers();
    emu_timer *m_isp_hc_sof_timer=nullptr;
    TIMER_CALLBACK_MEMBER(isp1161_hc_sof);
    static constexpr bool isp1161_hc_32bit(u8 code)
    {
        return code<=5 || code==0x0d || code==0x0e || code==0x0f
            || code==0x11 || (code>=0x12 && code<=0x16);
    }
    static constexpr bool isp1161_hc_16bit(u8 code)
    {
        return (code>=0x20 && code<=0x22) || code==0x24 || code==0x25
            || code==0x27 || code==0x28 || code==0x2a || code==0x2b
            || code==0x2c || code==0x2d || code==0x2e
            || code==0x40 || code==0x41;
    }
    static constexpr bool isp1161_hc_can_write(u8 code)
    {
        return code==1 || code==2 || code==3 || code==4 || code==5
            || code==0x0d || code==0x11 || (code>=0x12 && code<=0x16)
            || (code>=0x20 && code<=0x22)
            || code==0x24 || code==0x25 || code==0x28
            || code==0x29 || code==0x2a || code==0x2b
            || code==0x40 || code==0x41;
    }
    u32 isp1161_hc_read32(u8 code);
    u16 isp1161_hc_read16(u8 code);
    void isp1161_hc_write32(u8 code,u32 value);
    void isp1161_hc_write16(u8 code,u16 value);
    void isp1161_hc_reset();

    // Philips ISP1161 A1=1 device-controller command/data channel (separate from HC).
    u8 m_isp_dc_cmd=0;
    bool m_isp_dc_pending=false, m_isp_dc_unlocked=false, m_isp_dc_suspend_requested=false;
    u16 m_isp_dc_hw=0, m_isp_dc_mode=0;
    // Philips ISP1161A1 Rev03 §13.3.6: 32-bit DcInterrupt,
    // two successive low-then-high 16-bit reads after command C0.
    u32 m_isp_dc_interrupt=0, m_isp_dc_read_snapshot=0;
    u8 m_isp_dc_read_phase=0; // 0 idle, 1 low next, 2 high next
    u8 m_isp_dc_write_phase=0;
    u16 m_isp_dc_write_low=0;
    u16 m_isp_dc_address=0, m_isp_dc_scratch=0;
    u16 m_isp_dc_dma_cfg=0,m_isp_dc_dma_count=0;
    u32 m_isp_dc_interrupt_enable=0;
    u16 m_isp_dc_ep_config[16]={},m_isp_dc_ep_status[16]={};
    u8 m_isp_dc_ram[2462]={};
    void isp1161_dc_reset();
    static constexpr bool isp1161_dc_read_command(u8 cmd)
    {
        return (cmd>=0x30 && cmd<=0x3f) || (cmd>=0x50 && cmd<=0x5f)
            || (cmd>=0xa0 && cmd<=0xaf) || (cmd>=0xd0 && cmd<=0xdf)
            || cmd==0xb3 || cmd==0xb4 || cmd==0xb5 || cmd==0xb7
            || cmd==0xb9 || cmd==0xbb || cmd==0xc0 || cmd==0xc3
            || cmd==0xf1 || cmd==0xf3;
    }
    static constexpr bool isp1161_dc_write_command(u8 cmd)
    {
        return (cmd>=0x20 && cmd<=0x2f) || cmd==0xb0
            || cmd==0xb2 || cmd==0xb6 || cmd==0xb8 || cmd==0xba
            || cmd==0xc2 || cmd==0xf0 || cmd==0xf2;
    }
    u16 m_isp_low=0, m_isp_up_irq=0, m_isp_itl_len=0,
        m_isp_atl_len=0, m_isp_hardware=0x0028;
    u32 m_isp_control=0, m_isp_interrupt_status=0,
        m_isp_interrupt_enable=0, m_isp_frame_interval=0x27782edf;
    u8 m_sdram_init_phase=0;
    // Upper physical SDRAM is separate from the qualified 4 MiB R-direct RAM.
    std::unique_ptr<u16[]> m_physical_ram_extra;
    u16 m_watchdog=0x0001;
    emu_timer *m_watchdog_guard=nullptr;
    emu_timer *m_clk32_timer = nullptr;
    emu_timer *m_rtc_timer = nullptr;
    // MAME's current_datetime is seeded from the host RTC at machine start,
    // then advances with guest time. Guest RTCTIME writes use local offset.
    u32 m_rtc_time=0, m_rtc_last_tick=0;
    s32 m_rtc_offset_seconds=0;
    u16 m_rtc_day=0, m_rtc_control=0x0080, m_rtc_ien=0, m_rtc_isr=0;
    u16 m_pwm1_control=0x0020; // PWMC1 reset: FIFOAV=1, EN=0
    emu_timer *m_timer1_timer = nullptr;
    u16 m_tctl1=0, m_tprer1=0, m_tcmp1=0xffff;
    u16 m_tctl2=0;
    u16 m_tcr1=0, m_tcn1=0, m_tstat1=0, m_tstat_clear1=0;
    u32 m_timer1_compares=0, m_timer1_iacks=0;
    u16 m_ustcnt1=0, m_ubaud1=0x0002, m_urx1=0, m_utx1=0, m_umisc1=0;
    u16 m_uart_prescaler1=0;
    u16 m_iodcr=0x1fff;
    u16 m_icemcr=0, m_icemsr=0;
    u16 m_pllcr = 0x24b3;
    u16 m_pllfsr = 0x0347;
    u8 m_pctlr = 0x1f;
    bool m_clk32_high = false;
    u8 m_ivr = 0;
    bool m_guest_loaded = false;
    u16 m_icr = 0;
    u32 m_imr = 0x00ffffff;
    u32 m_pending = 0;
    u8 m_pcdir = 0;
    u8 m_pcdata = 0;
    u8 m_pcpden = 0;
    u8 m_pcsel = 0;
    u8 m_pfsel = 0xc5;
    u8 m_gpio[32] = {};
    u16 m_spi2_data = 0, m_spi2_ctrl = 0;
    // The pen ADC reply is staged within one PG2 selection.
    u8 m_pen_command = 0;
    u16 m_pen_sample = 0;
    bool m_st_ready = false, m_st_hello = false, m_st_reset_held = false;
    u32 m_st_old_keys[4]={}, m_st_pending_keys[4]={};
    u8 m_st_queue_left=0;
    static constexpr unsigned ST_EVENT_CAPACITY=64;
    u32 m_st_host_held[4]={},m_st_events[ST_EVENT_CAPACITY*4]={};
    u8 m_st_event_head=0,m_st_event_count=0;
    u32 m_lssa = 0;
    u8 m_lvpw = 0xff;
    u16 m_lxmax = 0x03f0;
    u16 m_lymax = 0x01ff;
    u16 m_lcxp = 0, m_lcyp = 0, m_lcwch = 0x0101;
    u8 m_lblkc = 0x7f;
    u8 m_lpicf = 0, m_lpolcf = 0, m_lacdrc = 0, m_lpxcd = 0;
    u8 m_lckcon = 0, m_lposr = 0, m_lgpmr = 0x84;
    u16 m_lrra = 0x00ff, m_pwmr = 0;
};

void alphasdana_state::machine_start()
{
    // Allocate only physical-mode upper RAM; R-direct map remains 4 MiB.
    m_physical_ram_extra=std::make_unique<u16[]>(0x600000);
    save_pointer(NAME(m_physical_ram_extra),0x600000);
    m_watchdog_guard = timer_alloc(FUNC(alphasdana_state::watchdog_guard), this);
    save_item(NAME(m_watchdog));
    m_clk32_timer = timer_alloc(FUNC(alphasdana_state::clk32_tick), this);
    m_isp_hc_sof_timer=timer_alloc(FUNC(alphasdana_state::isp1161_hc_sof),this);
    m_rtc_timer = timer_alloc(FUNC(alphasdana_state::rtc_tick), this);
    save_item(NAME(m_rtc_time));
    save_item(NAME(m_rtc_offset_seconds));
    save_item(NAME(m_rtc_last_tick));
    save_item(NAME(m_rtc_day));
    save_item(NAME(m_rtc_control));
    save_item(NAME(m_rtc_ien));
    save_item(NAME(m_rtc_isr));
    m_timer1_timer = timer_alloc(FUNC(alphasdana_state::timer1_compare), this);
    save_item(NAME(m_iodcr));
    save_item(NAME(m_icemcr)); save_item(NAME(m_icemsr));
    save_item(NAME(m_pllcr));
    save_item(NAME(m_pllfsr));
    save_item(NAME(m_pctlr));
    save_item(NAME(m_pwm1_control));
    save_item(NAME(m_clk32_high));
    save_item(NAME(m_ivr));
    save_item(NAME(m_guest_loaded));
    save_item(NAME(m_icr));
    save_item(NAME(m_imr));
    save_item(NAME(m_pending));
    save_item(NAME(m_tctl1)); save_item(NAME(m_tctl2)); save_item(NAME(m_tprer1));
    save_item(NAME(m_tcmp1)); save_item(NAME(m_tcr1));
    save_item(NAME(m_tcn1)); save_item(NAME(m_tstat1));
    save_item(NAME(m_tstat_clear1));
    save_item(NAME(m_timer1_compares));
    save_item(NAME(m_timer1_iacks));
    save_item(NAME(m_ustcnt1)); save_item(NAME(m_ubaud1));
    save_item(NAME(m_urx1)); save_item(NAME(m_utx1));
    save_item(NAME(m_umisc1)); save_item(NAME(m_uart_prescaler1));
    save_item(NAME(m_pcdir));
    save_item(NAME(m_pcdata));
    save_item(NAME(m_pcpden));
    save_item(NAME(m_pcsel));
    save_item(NAME(m_pfsel));
    save_item(NAME(m_gpio));
    save_item(NAME(m_spi2_data));
    save_item(NAME(m_spi2_ctrl));
    save_item(NAME(m_pen_command));
    save_item(NAME(m_pen_sample));
    save_item(NAME(m_st_ready));
    save_item(NAME(m_st_hello));
    save_item(NAME(m_st_reset_held));
    save_item(NAME(m_st_old_keys));
    save_item(NAME(m_st_pending_keys));
    save_item(NAME(m_st_queue_left));
    save_item(NAME(m_st_host_held));
    save_item(NAME(m_st_events));
    save_item(NAME(m_st_event_head));
    save_item(NAME(m_st_event_count));
    save_item(NAME(m_lssa));
    save_item(NAME(m_lvpw));
    save_item(NAME(m_lxmax));
    save_item(NAME(m_lymax));
    save_item(NAME(m_lcxp)); save_item(NAME(m_lcyp));
    save_item(NAME(m_lcwch)); save_item(NAME(m_lblkc));
    save_item(NAME(m_lpicf));
    save_item(NAME(m_lpolcf));
    save_item(NAME(m_lacdrc));
    save_item(NAME(m_lpxcd));
    save_item(NAME(m_lckcon));
    save_item(NAME(m_lposr));
    save_item(NAME(m_lgpmr));
    save_item(NAME(m_lrra));
    save_item(NAME(m_pwmr));
    save_item(NAME(m_physical_boot)); save_item(NAME(m_physical_blocked));
    save_item(NAME(m_bootstrap_mode)); save_item(NAME(m_bootstrap_ibuff));
    save_item(NAME(m_scr)); save_item(NAME(m_flash_sha1));
    save_item(NAME(m_cs_base)); save_item(NAME(m_cs_select));
    save_item(NAME(m_cs_upper)); save_item(NAME(m_cs_control));
    save_item(NAME(m_emucs)); save_item(NAME(m_dram));
    save_item(NAME(m_sdram_init_phase));
    save_item(NAME(m_isp_cmd)); save_item(NAME(m_isp_phase));
    save_item(NAME(m_isp_hc_read_phase));
    save_item(NAME(m_isp_hc_regs32)); save_item(NAME(m_isp_hc_regs16));
    save_item(NAME(m_isp_hc_ram));
    save_item(NAME(m_isp_hc_fifo_index)); save_item(NAME(m_isp_hc_fifo_remaining));
    save_item(NAME(m_isp_hc_fifo_cursor)); save_item(NAME(m_isp_hc_fifo_bank));
    save_item(NAME(m_isp_hc_valid_bytes));
    save_item(NAME(m_isp_hc_itl_cpu_bank));
    save_item(NAME(m_isp_dc_cmd)); save_item(NAME(m_isp_dc_pending));
    save_item(NAME(m_isp_dc_unlocked)); save_item(NAME(m_isp_dc_suspend_requested));
    save_item(NAME(m_isp_dc_hw)); save_item(NAME(m_isp_dc_mode));
    save_item(NAME(m_isp_dc_interrupt));
    save_item(NAME(m_isp_dc_read_snapshot));
    save_item(NAME(m_isp_dc_read_phase));
    save_item(NAME(m_isp_dc_write_phase));save_item(NAME(m_isp_dc_write_low));
    save_item(NAME(m_isp_dc_address));save_item(NAME(m_isp_dc_scratch));
    save_item(NAME(m_isp_dc_dma_cfg));save_item(NAME(m_isp_dc_dma_count));
    save_item(NAME(m_isp_dc_interrupt_enable));
    save_item(NAME(m_isp_dc_ep_config));save_item(NAME(m_isp_dc_ep_status));
    save_item(NAME(m_isp_dc_ram));
    save_item(NAME(m_isp_low)); save_item(NAME(m_isp_up_irq));
    save_item(NAME(m_isp_itl_len)); save_item(NAME(m_isp_atl_len));
    save_item(NAME(m_isp_hardware)); save_item(NAME(m_isp_control));
    save_item(NAME(m_isp_interrupt_status)); save_item(NAME(m_isp_interrupt_enable));
    save_item(NAME(m_isp_frame_interval));
    machine().save().register_postload(save_prepost_delegate(FUNC(alphasdana_state::boot_postload),this));
    m_spi1_timer=timer_alloc(FUNC(alphasdana_state::spi1_complete),this);
#define DANA_SPI1_SAVE(member) save_item(NAME(m_spi1.member))
    DANA_SPI1_SAVE(tx); DANA_SPI1_SAVE(rx); DANA_SPI1_SAVE(control); DANA_SPI1_SAVE(mask);
    DANA_SPI1_SAVE(spc); DANA_SPI1_SAVE(last_tx); DANA_SPI1_SAVE(last_rx);
    DANA_SPI1_SAVE(tx_head); DANA_SPI1_SAVE(rx_head); DANA_SPI1_SAVE(tx_count);
    DANA_SPI1_SAVE(rx_count); DANA_SPI1_SAVE(rx_edge);
#undef DANA_SPI1_SAVE
    save_item(NAME(m_spi1_word)); save_item(NAME(m_spi1_control)); save_item(NAME(m_spi1_busy));
    save_item(NAME(m_spi1_received)); save_item(NAME(m_spi1_bits_left));
    save_item(NAME(m_ilcr)); save_item(NAME(m_pd_extra)); save_item(NAME(m_sd_last_pins)); save_item(NAME(m_sd_edges));
    m_guest_ready = 0;
}

void alphasdana_state::machine_reset()
{
    m_watchdog=0x0001;
    m_watchdog_guard->adjust(attotime::never);
    // Existing peripheral implementation is shared by both boot profiles.
    // Motorola MC68VZ328UM 4.4.2: actual VZ reset, not MAME EZ/POSE 0x0123.
    m_iodcr=0x1fff;
    m_icemcr=0; m_icemsr=0;
    m_pllcr = 0x24b3;
    m_pllfsr = 0x0347;
    m_pctlr = 0x1f;
    m_pwm1_control=0x0020;
    m_clk32_high = false;
    // As in the pinned MAME DragonBall reference, advance CLK32 via
    // scheduler time rather than toggling it on register reads.
    m_clk32_timer->adjust(attotime::from_hz(32768), 0, attotime::from_hz(32768));
    // The host-seeded RTC persists across a soft hardware reset.
    m_rtc_control=0x0080; m_rtc_ien=0; m_rtc_isr=0;
    rtc_sync_from_host();
    m_rtc_last_tick=m_rtc_time;
    m_rtc_timer->adjust(attotime::from_seconds(1), 0, attotime::from_seconds(1));
    m_ivr = 0x00;
    m_icr = 0;
    m_imr = 0x00ffffff;
    m_pending = 0;
    m_tctl1=0; m_tctl2=0; m_tprer1=0; m_tcmp1=0xffff;
    m_tcr1=0; m_tcn1=0; m_tstat1=0; m_tstat_clear1=0;
    m_timer1_compares=0; m_timer1_iacks=0;
    m_timer1_timer->adjust(attotime::never);
    m_ustcnt1=0; m_ubaud1=0x0002; m_urx1=0;
    m_utx1=0; m_umisc1=0; m_uart_prescaler1=0;
    update_irq_lines();
    // dbztool@d327023 danainit.sh configures PCPDEN=PCSEL=0 before RAM
    // entry. This machine implements that synthetic post-bootstrap profile.
    // POSE's 0xff initial values are NOT manufacturer reset evidence.
    portc_reset();
    pfsel_reset();
    gpio_bootstrap_reset();
    st_input_reset();
    m_pen_command=0; m_pen_sample=0;
    lcd_bootstrap_reset();
    spi1_reset();
    m_bootstrap_mode=!(m_emubrk_pin->read()&1);
    m_physical_boot=m_firmware->exists() || m_bootstrap_mode;
    if (m_firmware->exists() && m_guest->exists() && !m_bootstrap_mode)
        fatalerror("Flash + guest incompatible except EMUBRK bootstrap");
    m_boot_memory.select(m_physical_boot ? 1 : 0);
    if (m_physical_boot)
    {
        physical_reset();
        if(m_bootstrap_mode) {
            for(unsigned i=0;i<sizeof(m_bootstrap_ibuff);i+=2) {
                m_bootstrap_ibuff[i]=0x4e; m_bootstrap_ibuff[i+1]=0x71;
            }
            m_maincpu->suspend(SUSPEND_REASON_DISABLE,true);
            logerror("DANA_VZ_BOOTSTRAP_ENTER emubrk=0 reset=1 uart=19200-8N1 ibuff=00ffffc0\n");
        }
        // Register-only guarded subset: stop before returning an unmodelled
        // enabled counter after a one-second observation interval. This is a
        // diagnostic deadline, NOT an emulated watchdog expiry or RTC phase.
        m_watchdog_guard->adjust(attotime::from_seconds(1));
        sd_lines();
        return; // CPU device reset fetches the firmware vectors through AS_PROGRAM.
    }
    // Quickload is timer-driven. Suppress *all* CPU fetches until validation
    // and the complete RAM/bootstrap seed have succeeded. No-image tests keep
    // their independently qualified native reset path unchanged.
    if (m_guest->exists() && !m_guest_loaded)
        m_maincpu->suspend(SUSPEND_REASON_DISABLE, true);
}



DEVICE_IMAGE_LOAD_MEMBER(alphasdana_state::firmware_load)
{
    if (m_guest->exists() && (m_emubrk_pin->read()&1))
        return std::make_pair(image_error::INVALIDIMAGE,std::string("Firmware and DANARAM1 are mutually exclusive; EMUBRK low permits B-records"));
    if (!image.loaded_through_softlist() && image.length()>0x1000000)
        return std::make_pair(image_error::INVALIDLENGTH,std::string("Firmware exceeds VZ CSA maximum decode"));
    u32 const size=m_firmware->common_get_size("rom");
    if (!firmware_size_valid(size))
        return std::make_pair(image_error::INVALIDLENGTH,std::string("Supply even-length raw bus-order bytes (128 KiB to 16 MiB), not a PRC"));
    // Byte storage prevents implicit host-endian swapping. No padding, header
    // removal, updater reconstruction, relocation or vector substitution.
    m_firmware->rom_alloc(size,GENERIC_ROM8_WIDTH,ENDIANNESS_LITTLE);
    u8 *const rom=m_firmware->get_rom_base();
    if (!rom || m_firmware->get_rom_size()!=size)
        return std::make_pair(image_error::INVALIDIMAGE,std::string("Restart with the selected Flash geometry"));
    if (image.loaded_through_softlist())
        m_firmware->common_load_rom(rom,size,"rom");
    else if (image.fread(rom,size)!=size)
        return std::make_pair(image_error::INVALIDIMAGE,std::string("Short physical Flash read"));
    if (!std::memcmp(rom,"DANARAM1",8) || !firmware_vectors_valid(rom))
        return std::make_pair(image_error::INVALIDIMAGE,std::string("Expected raw Flash bytes with original aligned vectors at offset zero"));
    auto const hash=util::sha1_creator::simple(rom,size);
    std::copy(std::begin(hash.m_raw),std::end(hash.m_raw),std::begin(m_flash_sha1));
    logerror("DANA_PHYSICAL_IMAGE bytes=%u sha1=%s read_only=1 topology=linear_array_unqualified\n",size,hash.as_string());
    if (size & (size-1))
        logerror("DANA_PHYSICAL_COVERAGE classification=UPDATER_DERIVED_RESET_EXPERIMENT supplied=00000000-%08x unknown_tail=BLOCKED reset_decode_window=01000000 geometry=UNQUALIFIED\n",size-1);
    return std::make_pair(std::error_condition(),std::string());
}

void alphasdana_state::firmware_unload(device_image_interface &)
{
    // No hot fallback into old RAM or stale ROM bytes. Restart with one image.
    m_maincpu->suspend(SUSPEND_REASON_DISABLE,true);
    m_guest_ready=0;
}

void alphasdana_state::physical_reset()
{
    m_physical_blocked=false;
    m_guest_loaded=false;
    m_guest_ready=0;
    m_scr=0x1c;
    std::fill(std::begin(m_cs_base),std::end(m_cs_base),0);
    m_cs_upper=0;
    m_cs_select[0]=0x00b0; m_cs_select[1]=0;
    m_cs_select[2]=0; m_cs_select[3]=0x0200;
    // VZ UM + addendum, D0.2: do not inherit POSE's zero CTRL2/CTRL3.
    m_cs_control[0]=0; m_cs_control[1]=0x1000; m_cs_control[2]=0x9c00;
    m_emucs=0x0060;
    m_dram[0]=0; m_dram[1]=0; m_dram[2]=0x003c; m_dram[3]=0;
    m_sdram_init_phase=0;
    isp1161_hc_reset();
    std::fill(std::begin(m_isp_hc_ram),std::end(m_isp_hc_ram),0);
    m_isp_hc_sof_timer->adjust(attotime::never);
    m_isp_cmd=0; m_isp_phase=0; m_isp_low=0;
    isp1161_dc_reset();
    m_isp_up_irq=0; m_isp_itl_len=0; m_isp_atl_len=0;
    m_isp_hardware=0x0028; m_isp_control=0;
    m_isp_interrupt_status=0; m_isp_interrupt_enable=0;
    m_isp_frame_interval=0x27782edf;
    m_pcpden=0xff; m_pcsel=0xff; m_pfsel=0x87;
    // Open VZ reference pin-latch reset, not a measured Dana electrical state.
    static constexpr u8 reset_gpio[32]={
        0,0,0xff,0xff, 0,0,0xff,0xff, 0,0,0xff,0xff, 0,0,0xff,0x87,
        0,0,0x3d,0x08, 0,0,0xff,0xef, 0,0,0xff,0xff, 0,0,0x3f,0x3f
    };
    std::copy(std::begin(reset_gpio),std::end(reset_gpio),std::begin(m_gpio));
    // No RAM clear, vector writes, CPU state injection or reset() call here.
    // Reuse the existing PLL/SYSCLK model, also used by Timer1. Electrical
    // reset/lock timing and PLLCR divisors remain unqualified.
    m_maincpu->set_unscaled_clock(physical_system_clock_hz());
    m_maincpu->resume(SUSPEND_REASON_DISABLE);
    logerror("DANA_PHYSICAL_RESET vectors=firmware CSA=%04x CSCTRL2=%04x CSCTRL3=%04x\n",
        m_cs_select[0],m_cs_control[1],m_cs_control[2]);
}

void alphasdana_state::boot_postload()
{
    if (m_physical_boot!=(m_firmware->exists()||m_bootstrap_mode) || (m_firmware->exists() && m_guest->exists() && !m_bootstrap_mode))
        fatalerror("Boot profile differs from saved state; restart with the original image selection");
    if (m_physical_boot)
    {
        auto const hash=util::sha1_creator::simple(m_firmware->get_rom_base(),m_firmware->get_rom_size());
        if (std::memcmp(hash.m_raw,m_flash_sha1,sizeof(m_flash_sha1)))
            fatalerror("Flash image differs from saved state");
    }
    m_boot_memory.select(m_physical_boot ? 1 : 0);
}

void alphasdana_state::physical_block(const char *reason, u32 address, u16 data)
{
    if (machine().side_effects_disabled()) return;
    if (!m_physical_blocked)
    {
        logerror("DANA_PHYSICAL_BLOCKED reason=%s address=%08x data=%04x pc=%08x\n",
            reason,address,data,u32(m_maincpu->pc()));
        // PC is the core's prefetch/bus position, not necessarily the start
        // of the offending instruction. Capture native state without reads
        // through the guest bus (which could cause another blocked access).
        logerror("DANA_PHYSICAL_CPU curpc=%08x ir=%04x sp=%08x usp=%08x sr=%04x a4=%08x\n",
            u32(m_maincpu->state_int(STATE_GENPCBASE)),u16(m_maincpu->state_int(M68K_IR)),
            u32(m_maincpu->state_int(M68K_SP)),u32(m_maincpu->state_int(M68K_USP)),
            u16(m_maincpu->state_int(M68K_SR)),u32(m_maincpu->state_int(M68K_A4)));
        logerror("DANA_PHYSICAL_DECODE csa=%04x csd=%04x csgba=%04x csgbd=%04x csugba=%04x csctrl=%04x/%04x/%04x dram=%04x/%04x/%04x/%04x\n",
            m_cs_select[0],m_cs_select[3],m_cs_base[0],m_cs_base[3],m_cs_upper,
            m_cs_control[0],m_cs_control[1],m_cs_control[2],
            m_dram[0],m_dram[1],m_dram[2],m_dram[3]);
    }
    m_physical_blocked=true;
    m_maincpu->suspend(SUSPEND_REASON_DISABLE,true);
}

u16 alphasdana_state::physical_r(offs_t offset, u16 mem_mask)
{
    u32 const address=u32(offset)<<1;
    if(m_bootstrap_mode && address<8) {
        // Motorola VZ UM Figure 17-1: silicon-generated reset vectors.
        static constexpr u16 vector[4]={0xfffc,0xfffc,0xffff,0xff00};
        return vector[address>>1];
    }
    // CSA's reset boot selection precedes programmed group decoding. A full
    // linear Flash array uses its own address lines; no fixed Palm ROM base.
    bool const boot=!(m_cs_select[0] & 1);
    bool const flash=boot || cs_hit(0,address);
    bool const ram=!boot && cs_hit(3,address);
    if (flash && !ram)
    {
        u32 const size=m_firmware->get_rom_size();
        if (!firmware_size_valid(size)) { physical_block("NO_COMPLETE_FLASH",address); return 0xffff; }
        if (!boot && cs_size(0)<size)
        {
            physical_block("FLASH_BANK_WINDOW_UNVERIFIED",address);
            return 0xffff;
        }
        // Non-power-of-two streams describe coverage, not chip capacity.
        // Retain the existing full-array aliases; partial streams instead use
        // the VZ maximum 16 MiB reset window and never wrap at supplied length.
        bool const partial=bool(size & (size-1));
        u32 const index=partial ? (boot ? address & 0x00ffffff : address-cs_base(0))
                               : (boot ? address : address-cs_base(0)) & (size-1);
        if (index>=size || size-index<2)
        {
            if (!machine().side_effects_disabled())
                logerror("DANA_PHYSICAL_MISSING_BYTES address=%08x array_offset=%08x mask=%04x supplied_bytes=%u\n",address,index,mem_mask,size);
            physical_block("FLASH_BYTES_NOT_SUPPLIED",address);
            return 0xffff;
        }
        u8 const *rom=m_firmware->get_rom_base();
        u16 const value=(u16(rom[index])<<8) | rom[index+1];
        if (address<8 && !machine().side_effects_disabled())
            logerror("DANA_PHYSICAL_VECTOR_READ address=%08x data=%04x mask=%04x\n",address,value,mem_mask);
        return value;
    }
    if (ram && !flash && cs_ram_read_allowed(m_cs_select[3],
        bool(m_maincpu->state_int(M68K_SR) & 0x2000),
        address-cs_base(3), cs_ram_unprotected_bytes(cs_size(3),
            m_cs_select[3],m_cs_control[0])))
    {
        if (!physical_ram_ready() || ((m_dram[2] & 0x8000) && m_sdram_init_phase!=3))
        {
            physical_block("DRAM_DISABLED_OR_INIT_READ",address);
            return 0xffff;
        }
        u32 const index=physical_sdram_index(address-cs_base(3));
        if (index<0x400000) return m_ram[index>>1];
        if (index<0x1000000) return m_physical_ram_extra[(index-0x400000)>>1];
    }
    physical_block(flash && ram ? "OVERLAPPING_CS" : "EXTERNAL_DECODE_OR_PROTECTION",address);
    return 0xffff; // Terminal unsupported access, never counted as a valid device response.
}

void alphasdana_state::physical_w(offs_t offset, u16 data, u16 mem_mask)
{
    u32 const address=u32(offset)<<1;
    bool const boot=!(m_cs_select[0] & 1);
    if (!boot && cs_hit(3,address) && !cs_hit(0,address)
        && cs_ram_write_allowed(m_cs_select[3],
            bool(m_maincpu->state_int(M68K_SR) & 0x2000),
            address-cs_base(3), cs_ram_unprotected_bytes(cs_size(3),
                m_cs_select[3],m_cs_control[0])))
    {
        if (!physical_ram_ready()) { physical_block("DRAM_DISABLED",address,data); return; }
        // Precharge/mode commands are triggered by SDCTRL writes. RAM data
        // stores become legal only after IP -> RE -> MR has completed.
        if ((m_dram[2] & 0x8000) && m_sdram_init_phase!=3)
        { physical_block("SDRAM_NOT_INITIALIZED_WRITE",address,data); return; }
        u32 const index=physical_sdram_index(address-cs_base(3));
        if (index<0x400000)
        {
            COMBINE_DATA(&m_ram[index>>1]);
            return;
        }
        if (index<0x1000000)
        {
            COMBINE_DATA(&m_physical_ram_extra[(index-0x400000)>>1]);
            return;
        }
    }
    // Exact NOR part/command set is not established. Do not fabricate an ID,
    // completed erase/program, or persistent write to the original dump.
    if (!m_physical_blocked && !machine().side_effects_disabled())
        logerror("DANA_PHYSICAL_WRITE address=%08x data=%04x mask=%04x\n",address,data,mem_mask);
    physical_block(boot || cs_hit(0,address) ? "FLASH_COMMAND_SET_UNVERIFIED" : "EXTERNAL_WRITE_OR_PROTECTION",address,data);
}

u16 alphasdana_state::physical_mmio_r(offs_t offset, u16 mem_mask)
{
    if (machine().side_effects_disabled()) return 0xffff;
    logerror("DANA_PHYSICAL_UNIMPLEMENTED_MMIO read address=%08x mask=%04x\n",0xfffff000+(u32(offset)<<1),mem_mask);
    physical_block("MMIO_READ_UNIMPLEMENTED",0xfffff000+(u32(offset)<<1));
    return 0xffff;
}


void alphasdana_state::isp1161_hc_reset()
{
    // HC internal reset does not reset the DC or erase HC packet RAM.
    std::fill(std::begin(m_isp_hc_regs32),std::end(m_isp_hc_regs32),0);
    std::fill(std::begin(m_isp_hc_regs16),std::end(m_isp_hc_regs16),0);
    m_isp_cmd=0; m_isp_phase=0; m_isp_hc_read_phase=0; m_isp_low=0;
    m_isp_control=0; m_isp_interrupt_status=0; m_isp_interrupt_enable=0;
    m_isp_frame_interval=0x27782edf;
    m_isp_hardware=0x0028; m_isp_up_irq=0; m_isp_itl_len=0; m_isp_atl_len=0;
    m_isp_hc_regs32[0]=0x10; // OHCI specification release 1.0
    // Two actual downstream HC ports (NDP[1:0]=2); neither is connected.
    m_isp_hc_regs32[0x12]=2;
    m_isp_hc_regs32[0x0d]=m_isp_frame_interval;
    m_isp_hc_regs16[0x20]=m_isp_hardware;
    m_isp_hc_regs16[0x27]=0x6123; // ISP1161A1 Rev03 Table 46
    m_isp_hc_fifo_bank=0; m_isp_hc_fifo_cursor=0;
    m_isp_hc_fifo_index=0; m_isp_hc_fifo_remaining=0;
    std::fill(std::begin(m_isp_hc_valid_bytes),std::end(m_isp_hc_valid_bytes),0);
    m_isp_hc_itl_cpu_bank=0;
}

void alphasdana_state::isp1161_dc_reset()
{
    // Reset DEVICE only: do not alter the HC command, IRQ or FIFO state.
    m_isp_dc_cmd=0; m_isp_dc_pending=false; m_isp_dc_read_phase=0;
    m_isp_dc_write_phase=0; m_isp_dc_write_low=0;
    m_isp_dc_unlocked=false; m_isp_dc_suspend_requested=false;
    m_isp_dc_interrupt=0;m_isp_dc_read_snapshot=0;
    m_isp_dc_interrupt_enable=0;
    m_isp_dc_address=0;m_isp_dc_scratch=0;m_isp_dc_mode=0;m_isp_dc_hw=0;
    m_isp_dc_dma_cfg=0;m_isp_dc_dma_count=0;
    std::fill(std::begin(m_isp_dc_ep_config),std::end(m_isp_dc_ep_config),0);
    std::fill(std::begin(m_isp_dc_ep_status),std::end(m_isp_dc_ep_status),0);
    std::fill(std::begin(m_isp_dc_ram),std::end(m_isp_dc_ram),0);
}

void alphasdana_state::isp1161_hc_execute_buffers()
{
    // Execute at SOF on chip SRAM, never from CPU main memory.
    // The Philips 8-byte PTD layout is entirely different from OHCI TD/ED.
    for(unsigned bank=0;bank<3;++bank)
    {
        u16 const full=u16(1U<<bank);
        if(!(m_isp_hc_regs16[0x2c]&full))
            continue;
        u16 const base=bank==2 ? u16(2U*m_isp_itl_len)
            : u16(bank*m_isp_itl_len);
        u16 const limit=bank==2 ? m_isp_atl_len : m_isp_itl_len;
        u16 const count=m_isp_hc_valid_bytes[bank];
        if(count>limit || unsigned(base)+count>sizeof(m_isp_hc_ram))
        {
            physical_block("ISP1161_HC_PTD_FIFO_LAYOUT",0x1f000000,count);
            return;
        }
        auto disconnected=[](isp1161a1::transaction const &,
            u8 const *,u8 *,u16)->isp1161a1::reply
        {
            // No USB peripheral is configured/connected. A token receives
            // no handshake; never fabricate an enumeration ACK or data.
            return {isp1161a1::handshake::timeout,0};
        };
        isp1161a1::outcome const result=isp1161a1::execute(
            m_isp_hc_ram+base,count,disconnected,true);
        if(result.malformed)
        {
            physical_block("ISP1161_HC_PTD_MALFORMED",0x1f000000,count);
            return;
        }
        // The HC consumed the uploaded PTDs and made their updated status
        // readable to the MCU through the same 16-bit FIFO port.
        m_isp_hc_regs16[0x2c]=u16(
            (m_isp_hc_regs16[0x2c]&~full)|(1U<<(bank+3)));
        if(bank==2) m_isp_up_irq|=0x02; // ATL interrupt status
        else m_isp_up_irq|=0x01; // SOF/ITL interrupt
        logerror("DANA_ISP1161_PTD bank=%u count=%u parsed=%u complete=%u pending=%u\n",
            bank,count,unsigned(result.descriptors),
            unsigned(result.completed),unsigned(result.pending));
    }
    if((m_isp_hc_regs16[0x2c]&0x03)!=0x03)
        m_isp_hc_itl_cpu_bank^=1; // ITL ping-pong per millisecond
}

TIMER_CALLBACK_MEMBER(alphasdana_state::isp1161_hc_sof)
{
    if ((m_isp_control & 0xc0)!=0x80)
        return;
    m_isp_hc_regs32[0x0f]=(m_isp_hc_regs32[0x0f]+1)&0xffff;
    m_isp_interrupt_status|=0x00000004; // OHCI StartOfFrame
    isp1161_hc_execute_buffers();
    // Device attachment is explicit: no downstream USB device is present
    // until a configured emulated peripheral is connected to a root port.
    if (m_isp_hc_regs16[0x25]&1)
        m_isp_up_irq |=1;
}

u32 alphasdana_state::isp1161_hc_read32(u8 code)
{
    switch(code)
    {
    case 0: return 0x00000010;
    case 1: return m_isp_control;
    case 3: return m_isp_interrupt_status;
    case 4: case 5: return m_isp_interrupt_enable;
    case 0x0d: return m_isp_frame_interval;
    case 0x0e:
    {
        // OHCI HcFmRemaining: frame interval in full-speed bit times.
        // With HC operational the 1-ms period advances on virtual time,
        // independently of any attached USB downstream devices.
        if ((m_isp_control & 0xc0)!=0x80) return 0;
        u32 const fi=m_isp_frame_interval & 0x3fff;
        if(!fi) return 0;
        attoseconds_t const frame=ATTOSECONDS_PER_SECOND/1000;
        attoseconds_t const pos=machine().time().attoseconds()%frame;
        u32 const elapsed=u32(pos/(frame/fi));
        return elapsed<fi ? fi-elapsed : 0;
    }
    default: return m_isp_hc_regs32[code];
    }
}

u16 alphasdana_state::isp1161_hc_read16(u8 code)
{
    switch(code)
    {
    case 0x20: return m_isp_hardware;
    case 0x24: return m_isp_up_irq;
    case 0x27: return 0x6123; // documented silicon ID; no synthetic ID
    case 0x2a: return m_isp_itl_len;
    case 0x2b: return m_isp_atl_len;
    case 0x2c: return m_isp_hc_regs16[0x2c];
    case 0x2d: case 0x2e: return 0; // no PTD USB response without a target
    default: return m_isp_hc_regs16[code];
    }
}

void alphasdana_state::isp1161_hc_write32(u8 code,u32 value)
{
    switch(code)
    {
    case 1:
        m_isp_control=value;
        // HCFS 10 = operational, clock emits SOFs independently of DC.
        if ((value&0xc0)==0x80)
            m_isp_hc_sof_timer->adjust(attotime::from_msec(1),0,attotime::from_msec(1));
        else
            m_isp_hc_sof_timer->adjust(attotime::never);
        break;
    case 2:
        // OHCI HostControllerReset; no memory, DC or SRAM reset.
        if (value&1) { isp1161_hc_reset(); return; }
        m_isp_hc_regs32[2]=value;
        break;
    case 3: m_isp_interrupt_status &= ~value; break; // W1C
    case 4: m_isp_interrupt_enable |=value; break;
    case 5: m_isp_interrupt_enable &= ~value; break;
    case 0x0d: m_isp_frame_interval=value; break;
    case 0x14:
        // No upstream host or attached devices. RH change W1C and
        // local-power operations are handled without claiming a connection.
        m_isp_hc_regs32[code] &= ~(value & 0x00030000);
        break;
    case 0x15: case 0x16:
        // A disconnected downstream port can be powered; it cannot become
        // connected or enabled without an actual USB backend.
        if(value&0x00000100) m_isp_hc_regs32[code]|=0x00000100;
        if(value&0x00000200) m_isp_hc_regs32[code]&=~u32(0x00000100);
        m_isp_hc_regs32[code]&=~(value & 0x001f0000);
        break;
    default:
        m_isp_hc_regs32[code]=value;
        break;
    }
    if (code==1 || code==2 || code==3 || code==4 || code==5 || code==0x0d)
        m_isp_hc_regs32[code]=isp1161_hc_read32(code);
}

void alphasdana_state::isp1161_hc_write16(u8 code,u16 value)
{
    switch(code)
    {
    case 0x20: m_isp_hardware=value; break;
    case 0x24: m_isp_up_irq &=~(value & 0x0077); break; // W1C
    case 0x25: m_isp_hc_regs16[code]=value & 0x0077; return;
    case 0x2a: case 0x2b:
    {
        u32 const itl=code==0x2a ? value : m_isp_itl_len;
        u32 const atl=code==0x2b ? value : m_isp_atl_len;
        if(atl+2*itl>4096)
        {
            physical_block("ISP1161_HC_FIFO_ALLOCATION",0x1f000000,value);
            return;
        }
        if(code==0x2a) m_isp_itl_len=value;
        else m_isp_atl_len=value;
        break;
    }
    case 0x22:
        m_isp_hc_fifo_remaining=value;
        m_isp_hc_fifo_cursor=0;
        break;
    case 0x29:
        // Reset byte F6 keeps internal HC packet RAM.
        if (value!=0xf6)
        {
            physical_block("ISP1161_HC_INVALID_RESET",0x1f000000,value);
            return;
        }
        isp1161_hc_reset();
        return;
    default: break;
    }
    if(code<0x42) m_isp_hc_regs16[code]=value;
}

u16 alphasdana_state::isp1161_r(offs_t offset, u16 mem_mask)
{
    u32 const address=0x1f000000U+u32(offset)*2;
    if(mem_mask!=0xffff)
    { physical_block("ISP1161_BUS_REQUIRES_WORD",address); return 0xffff; }
    if(offset==2)
    {
        if(m_isp_dc_read_phase)
        {
            u8 const cmd=m_isp_dc_cmd;
            if(cmd==0xc0 || cmd==0xc3)
            {
                u16 const v=m_isp_dc_read_phase==1 ?
                    u16(m_isp_dc_read_snapshot) : u16(m_isp_dc_read_snapshot>>16);
                if(m_isp_dc_read_phase==1)
                    m_isp_dc_read_phase=2;
                else
                {
                    m_isp_dc_read_phase=0;
                    if(cmd==0xc0) m_isp_dc_interrupt &= ~u32(0x005b);
                }
                logerror("DANA_ISP1161_DC_INTERRUPT cmd=%02x value=%04x phase=%u\n",
                    cmd,v,unsigned(m_isp_dc_read_phase));
                return v;
            }
            m_isp_dc_read_phase=0;
            if(cmd>=0x30 && cmd<=0x3f)
                return m_isp_dc_ep_config[cmd-0x30];
            if(cmd>=0x50 && cmd<=0x5f)
            {
                u16 const state=m_isp_dc_ep_status[cmd-0x50];
                m_isp_dc_interrupt &=~(u32(1)<<(8+(cmd-0x50)));
                return state;
            }
            if(cmd>=0xd0 && cmd<=0xdf)
                return m_isp_dc_ep_status[cmd-0xd0]; // no side effects
            if(cmd>=0xa0 && cmd<=0xaf) return 0; // no transfer errors
            switch(cmd)
            {
            case 0xb3: return m_isp_dc_scratch;
            case 0xb4: return 0; // no upstream SOF until a host is attached
            case 0xb5: return 0x6123; // Rev03 Table 106
            case 0xb7: return m_isp_dc_address;
            case 0xb9: return m_isp_dc_mode;
            case 0xbb: return m_isp_dc_hw;
            case 0xf1: return m_isp_dc_dma_cfg;
            case 0xf3: return m_isp_dc_dma_count;
            }
            physical_block("ISP1161_DC_READ_REGISTER_UNKNOWN",address,cmd);
            return 0xffff;
        }
        if(m_isp_dc_pending)
        {
            // Real 68000 CLR.W read-before-write; a write command does not
            // have a readable data result at this stage.
            return 0xffff;
        }
        physical_block("ISP1161_DC_READ_WITHOUT_COMMAND",address);
        return 0xffff;
    }
    if(offset!=0)
    { physical_block("ISP1161_BAD_READ_ADDRESS",address); return 0xffff; }
    if(m_isp_cmd&0x80)
    {
        // The 68000 reads before writing CLR.W; this inactive read does not
        // move any command or FIFO cursor.
        return 0xffff;
    }
    u8 const code=m_isp_cmd;
    if(code==0x40 || code==0x41)
    {
        // Buffer RAM is inaccessible unless a transfer count was programmed.
        if(!m_isp_hc_fifo_remaining) return 0;
        u16 const base=code==0x40 ? u16(m_isp_hc_itl_cpu_bank*m_isp_itl_len) : u16(2U*m_isp_itl_len);
        u16 const cursor=base+m_isp_hc_fifo_cursor;
        if(cursor+1>=4096)
        { physical_block("ISP1161_HC_FIFO_OOB",address); return 0xffff; }
        u16 const value=u16(m_isp_hc_ram[cursor])|(u16(m_isp_hc_ram[cursor+1])<<8);
        m_isp_hc_fifo_cursor+=2;
        m_isp_hc_fifo_remaining=m_isp_hc_fifo_remaining>2 ?
            m_isp_hc_fifo_remaining-2 : 0;
        if (!m_isp_hc_fifo_remaining) m_isp_up_irq|=0x04; // EOT
        return value;
    }
    if (isp1161_hc_32bit(code))
    {
        u32 const value=isp1161_hc_read32(code);
        if(!m_isp_hc_read_phase)
        {
            m_isp_hc_read_phase=1;
            return u16(value);
        }
        m_isp_hc_read_phase=0;
        return u16(value>>16);
    }
    if(isp1161_hc_16bit(code))
        return isp1161_hc_read16(code);
    physical_block("ISP1161_HC_BAD_READ_COMMAND",address,code);
    return 0xffff;
}

void alphasdana_state::isp1161_w(offs_t offset,u16 data,u16 mem_mask)
{
    u32 const address=0x1f000000U+u32(offset)*2;
    if(mem_mask!=0xffff)
    { physical_block("ISP1161_BUS_REQUIRES_WORD",address,data); return; }
    // ISP1161A1 Device Controller: Table 75 indexed command bank.
    if(offset==3)
    {
        if(data&0xff00)
        { physical_block("ISP1161_DC_COMMAND_UPPER_BYTE",address,data);return; }
        if(m_isp_dc_pending || m_isp_dc_read_phase)
        { physical_block("ISP1161_DC_INCOMPLETE_TRANSFER",address,data);return; }
        u8 const command=u8(data);
        if(command==0xf6)
        {
            isp1161_dc_reset(); // DC software reset, HC is unchanged
            return;
        }
        if(command==0xf4)
        {
            // ACK SETUP command: clear only pending EP0 setup status.
            m_isp_dc_ep_status[0]&=~u16(0x0040);
            return;
        }
        if(isp1161_dc_write_command(command))
        {
            m_isp_dc_cmd=command;m_isp_dc_pending=true;
            m_isp_dc_write_phase=0;
            return;
        }
        if(isp1161_dc_read_command(command))
        {
            m_isp_dc_cmd=command; m_isp_dc_read_phase=1;
            m_isp_dc_read_snapshot=command==0xc0 ?
                m_isp_dc_interrupt : m_isp_dc_interrupt_enable;
            return;
        }
        physical_block("ISP1161_DC_COMMAND_UNKNOWN",address,data);
        return;
    }
    if(offset==2)
    {
        if(!m_isp_dc_pending)
        { physical_block("ISP1161_DC_WRITE_WITHOUT_COMMAND",address,data);return; }
        u8 const code=m_isp_dc_cmd;
        if(code==0xc2)
        {
            if(!m_isp_dc_write_phase)
            { m_isp_dc_write_low=data;m_isp_dc_write_phase=1;return; }
            m_isp_dc_interrupt_enable=u32(m_isp_dc_write_low)|(u32(data)<<16);
            m_isp_dc_write_phase=0;m_isp_dc_pending=false;
            return;
        }
        if(code>=0x20 && code<=0x2f)
        {
            if(data&0xff00)
            { physical_block("ISP1161_DC_ENDPOINT_CONFIG_RESERVED",address,data);return; }
            m_isp_dc_ep_config[code-0x20]=data;
        }
        else switch(code)
        {
        case 0xb0:
            if(data!=0xaa37)
            { physical_block("ISP1161_DC_UNLOCK_CODE",address,data);return; }
            m_isp_dc_unlocked=true;
            break;
        case 0xb2: m_isp_dc_scratch=data&0x1fff;break;
        case 0xb6: m_isp_dc_address=data&0x00ff;break;
        case 0xb8:
            // GOSUSP set/clear sequence is a physical power request;
            // do not fabricate USB bus suspend or SOF packets.
            if((m_isp_dc_mode&0x20) && !(data&0x20))
                m_isp_dc_suspend_requested=true;
            m_isp_dc_mode=data;
            break;
        case 0xba: m_isp_dc_hw=data;break;
        case 0xf0: m_isp_dc_dma_cfg=data;break;
        case 0xf2: m_isp_dc_dma_count=data;break;
        default:
            physical_block("ISP1161_DC_WRITE_UNSUPPORTED",address,data);return;
        }
        m_isp_dc_pending=false;
        logerror("DANA_ISP1161_DC cmd=%02x value=%04x hw=%04x mode=%04x suspend_requested=%u\n",
            code,data,m_isp_dc_hw,m_isp_dc_mode,unsigned(m_isp_dc_suspend_requested));
        return;
    }
    if(offset==1)
    {
        if(data & 0xff00)
        { physical_block("ISP1161_HC_COMMAND_UPPER_BYTE",address,data); return; }
        u8 const code=u8(data)&0x7f;
        bool const write=bool(data&0x80);
        if(m_isp_phase || m_isp_hc_read_phase)
        { physical_block("ISP1161_HC_INCOMPLETE_REGISTER",address,data); return; }
        if(write)
        {
            if(!isp1161_hc_can_write(code))
            { physical_block("ISP1161_HC_READ_ONLY",address,data); return; }
        }
        else if(!isp1161_hc_32bit(code) && !isp1161_hc_16bit(code))
        { physical_block("ISP1161_HC_BAD_COMMAND",address,data); return; }
        m_isp_cmd=u8(data);
        m_isp_phase=0; m_isp_hc_read_phase=0;
        if(code==0x40 || code==0x41)
        {
            m_isp_hc_fifo_cursor=0;
            m_isp_hc_fifo_bank=code;
        }
        return;
    }
    if(offset)
    { physical_block("ISP1161_HC_BAD_ADDRESS",address,data); return; }
    if(!(m_isp_cmd&0x80))
    { physical_block("ISP1161_HC_WRITE_WITH_READ_CMD",address,data); return; }
    u8 const code=m_isp_cmd & 0x7f;
    if(code==0x40 || code==0x41)
    {
        if(m_isp_hc_fifo_remaining==0)
        { physical_block("ISP1161_HC_FIFO_COUNT_REQUIRED",address,data); return; }
        u16 const base=code==0x40 ? u16(m_isp_hc_itl_cpu_bank*m_isp_itl_len) : u16(2U*m_isp_itl_len);
        u16 const cursor=base+m_isp_hc_fifo_cursor;
        if(cursor+1>=4096)
        { physical_block("ISP1161_HC_FIFO_OOB",address,data); return; }
        m_isp_hc_ram[cursor]=u8(data);m_isp_hc_ram[cursor+1]=u8(data>>8);
        m_isp_hc_fifo_cursor+=2;
        m_isp_hc_fifo_remaining=m_isp_hc_fifo_remaining>2 ?
            m_isp_hc_fifo_remaining-2 : 0;
        if(!m_isp_hc_fifo_remaining)
        {
            m_isp_up_irq|=0x04; // End of host-buffer PIO transfer
            unsigned const bank=code==0x40 ? m_isp_hc_itl_cpu_bank : 2;
            m_isp_hc_valid_bytes[bank]=m_isp_hc_fifo_cursor;
            m_isp_hc_regs16[0x2c] |= u16(1U<<bank);
        }
        return;
    }
    if(isp1161_hc_32bit(code))
    {
        if(!m_isp_phase)
        { m_isp_low=data; m_isp_phase=1; return; }
        m_isp_phase=0;
        isp1161_hc_write32(code,u32(m_isp_low)|(u32(data)<<16));
    }
    else if(isp1161_hc_can_write(code))
        isp1161_hc_write16(code,data);
    else
        physical_block("ISP1161_HC_BAD_WRITE_COMMAND",address,data);
}

void alphasdana_state::physical_mmio_w(offs_t offset, u16 data, u16 mem_mask)
{
    if (machine().side_effects_disabled()) return;
    logerror("DANA_PHYSICAL_UNIMPLEMENTED_MMIO write address=%08x mask=%04x\n",0xfffff000+(u32(offset)<<1),mem_mask);
    physical_block("MMIO_WRITE_UNIMPLEMENTED",0xfffff000+(u32(offset)<<1),data);
}

// VZ UM 11.2.5: any actual lane write clears CNTR[9:8]; INTF[7]
// is W1C, ISEL[1]/EN[0] are writable and all other bits read zero.
// Enabled counting/IRQ/reset timing is deliberately guarded, not fabricated.
void alphasdana_state::watchdog_w(offs_t, u16 data, u16 mem_mask)
{
    if (!mem_mask) return;
    u16 const controls=((m_watchdog & ~mem_mask) | (data & mem_mask)) & 0x0003;
    m_watchdog=(m_watchdog & 0x0080 & ~(data & mem_mask)) | controls;
    m_watchdog_guard->adjust(attotime::never);
    if (m_watchdog & 1)
        physical_block("WATCHDOG_ENABLED_CLOCK_UNIMPLEMENTED",0xfffffb0a,m_watchdog);
}

TIMER_CALLBACK_MEMBER(alphasdana_state::watchdog_guard)
{
    if (m_physical_boot && (m_watchdog & 1))
        physical_block("WATCHDOG_ENABLED_CLOCK_UNIMPLEMENTED",0xfffffb0a,m_watchdog);
}

void alphasdana_state::scr_w(u8 data)
{
    // DMAP=0 retains the high internal-register page (VZ UM 5.2.1).
    // DMAP=1 also permits 24-bit aliases; neither value disables this page.
    // Preserve write-one-to-clear status bits and writable control bits.
    m_scr=(m_scr & 0xe0 & ~data) | (data & 0x1f);
}

u16 alphasdana_state::cs_r(offs_t offset)
{
    if (offset<4) return m_cs_base[offset];
    if (offset==4) return m_cs_upper;
    return m_cs_control[offset-5];
}

void alphasdana_state::cs_w(offs_t offset, u16 data, u16 mem_mask)
{
    if (offset<4)
    {
        COMBINE_DATA(&m_cs_base[offset]);
        m_cs_base[offset] &= 0xfffe;
    }
    else if (offset==4)
    {
        COMBINE_DATA(&m_cs_upper);
        if (m_cs_upper) physical_block("CS_UPPER_ADDRESS_MODE",0xfffff108,data);
    }
    else
    {
        // VZ UM 6.3.5/6.3.6: CSCTRL1/2 define memory sizing and bus timing.
        // Native UK1.5 first writes CSCTRL2=D000, then CSCTRL1=0100.
        // Store valid fields; electrical wait-state cycles are not synthesized.
        u16 const defined=offset==5 ? 0x7f55 : 0xf300;
        u16 const merged=(m_cs_control[offset-5] & ~mem_mask) | (data & mem_mask);
        if (merged & ~defined)
        {
            physical_block("CS_CONTROL_RESERVED_BITS",0xfffff100+offset*2,data);
            return;
        }
        m_cs_control[offset-5]=merged;
    }
}

void alphasdana_state::cs_control3_w(offs_t, u16 data, u16 mem_mask)
{
    COMBINE_DATA(&m_cs_control[2]);
    if (m_cs_control[2]!=0x9c00) physical_block("CS_CONTROL3_MODE",0xfffff150,data);
}


void alphasdana_state::gpio_bootstrap_reset()
{
    // R-direct preconfiguration from dbztool@d327023/danainit.sh.
    // B,D,E,F,G,J,K,M: DIR, DATA latch, PUEN, SEL.
    static constexpr u8 profile[32] = {
        0x60,0x00,0x00,0x60, 0x00,0x00,0x1f,0x10,
        0xc8,0x08,0x10,0xc8, 0x44,0x00,0x00,0xc5,
        0x1f,0x1d,0x00,0x3f, 0xbf,0x40,0x00,0xcf,
        0xf9,0x00,0x00,0xfd, 0x20,0x20,0x00,0x20
    };
    for (unsigned i=0; i<32; ++i)
        m_gpio[i] = profile[i];
}


void alphasdana_state::st_input_reset()
{
    // The reference Dana has a separate ST controller; initialize the
    // interface to unready, not a permanently asserted input pin.
    m_st_ready=false; m_st_hello=false; m_st_reset_held=false;
    for (unsigned i=0;i<4;++i) { m_st_old_keys[i]=0; m_st_pending_keys[i]=0; }
    m_st_queue_left=0;
    for (unsigned i=0;i<4;++i) m_st_host_held[i]=0;
    for (unsigned i=0;i<ST_EVENT_CAPACITY*4;++i) m_st_events[i]=0;
    m_st_event_head=0; m_st_event_count=0;
    m_spi2_data=0; m_spi2_ctrl=0;
}

void alphasdana_state::pb_w(offs_t reg, u8 value)
{
    u8 const old=m_gpio[reg];
    m_gpio[reg]=value;
    if (reg==1)
    {
        // PB6 drives the auxiliary controller reset line.
        if ((value & 0x40) && !(old & 0x40))
        {
            st_input_reset();
            m_st_reset_held=true;
        }
        else if (!(value & 0x40) && (old & 0x40) && m_st_reset_held)
        {
            m_st_reset_held=false;
            m_st_ready=true;
            m_st_hello=true;
        }
    }
    sd_lines();
}

u8 alphasdana_state::pk_r(offs_t reg)
{
    u8 result=m_gpio[6*4+reg];
    if (reg==1 && !(m_gpio[6*4] & 0x04))
    {
        // PK2 reads the ST ready INPUT while configured as GPIO input.
        // Never replace the output latch when the CPU drives this pin.
        result=(result & ~0x04) | (m_st_ready ? 0x04 : 0);
    }
    return result;
}

void alphasdana_state::pk_w(offs_t reg, u8 value)
{
    u8 const old=m_gpio[6*4+reg];
    m_gpio[6*4+reg]=value;
    if (reg==0 && (value & 0x04) && !(old & 0x04)
        && !(m_gpio[6*4+1] & 0x04))
    {
        // The software's PK2 output pulse wakes the separate ST controller.
        // Once released as input, PKDATA reports the ready line.
        m_st_ready=true;
        m_st_hello=true;
    }
    sd_lines();
}

u8 alphasdana_state::st_exchange(u8 command)
{
    // Guest OS translates physical Dana scan codes; ST owns only SPI2 packets.
    if (!m_st_ready || (m_gpio[2*4+1] & 0x08))
        return 0xff;
    if (m_st_hello)
    {
        m_st_hello=false;
        return 0xaa;
    }
    if (command)
        return 0;
    // Never interleave one key-state packet with another.
    if (m_st_queue_left)
    {
        for (unsigned scan=0;scan<128;++scan)
        {
            u32 const bit=u32(1)<<(scan&31);
            u32 &pending=m_st_pending_keys[scan>>5];
            if (pending & bit)
            {
                pending &= ~bit;
                --m_st_queue_left;
                return u8(scan);
            }
        }
        m_st_queue_left=0;
        return 0;
    }

    // Sample all 81 physical inputs, including six original KEY bindings.
    // Sampling also restores held state if ST was reset while a key was down.
    u32 live[4]={};
    static constexpr u8 original_scan[6]={0x2b,0x7a,0x2e,0x7e,0x46,0x6d};
    u8 const original=m_keys->read()&0x3f;
    for (unsigned i=0;i<6;++i)
        if (BIT(original,i))
            live[original_scan[i]>>5]|=u32(1)<<(original_scan[i]&31);
    for (unsigned i=0;i<4;++i)
        live[i]|=m_st_extended_keys[i]->read();

    u32 next[4]={};
    bool changed=false;
    while (m_st_event_count)
    {
        unsigned const slot=m_st_event_head;
        for (unsigned i=0;i<4;++i)
        {
            next[i]=m_st_events[slot*4+i];
            changed |= next[i]!=m_st_old_keys[i];
        }
        m_st_event_head=u8((unsigned(m_st_event_head)+1)%ST_EVENT_CAPACITY);
        --m_st_event_count;
        if (changed) break;
    }
    if (!changed)
    {
        for (unsigned i=0;i<4;++i)
        {
            next[i]=live[i];
            changed |= next[i]!=m_st_old_keys[i];
        }
    }
    if (!changed) return 0;
    for (unsigned i=0;i<4;++i)
    {
        m_st_old_keys[i]=next[i];
        m_st_pending_keys[i]=0;
    }

    // Pinned EmuTOS-Dana new_keys[8] is eight bytes: never advertise >8.
    unsigned count=0;
    for (unsigned scan=0;scan<128 && count<8;++scan)
    {
        u32 const bit=u32(1)<<(scan&31);
        if (next[scan>>5] & bit)
        {
            m_st_pending_keys[scan>>5]|=bit;
            ++count;
        }
    }
    m_st_queue_left=u8(count);
    return u8(0x40|count);
}

u16 alphasdana_state::pen_exchange(unsigned width, u16 outgoing)
{
    // EmuTOS dana.c::pen_send_recv sends 0x90/0xD0 (8 clocks), followed
    // by a 16-clock read on the same active-low PG2 chip-select window.
    // The guest consumes (received >> 4) as an unsigned 12-bit sample.
    // No claimed factory calibration: these bounded endpoints are a
    // provisional emulator digitizer mapping, separate from the LCD pixels.
    if (!(m_pen_contact->read() & 1))
        return 0xffff;
    if (width==8)
    {
        m_pen_command=(outgoing==0x90 || outgoing==0xd0) ? u8(outgoing) : 0;
        if (!m_pen_command)
        {
            m_pen_sample=0;
            return 0xff;
        }
        unsigned const coord=(m_pen_command==0x90) ? (m_pen_x->read() & 0xffff) : (m_pen_y->read() & 0xffff);
        unsigned const minimum=(m_pen_command==0x90) ? 290 : 200;
        unsigned const span=(m_pen_command==0x90) ? 3470 : 3450;
        m_pen_sample=u16(minimum+(coord*span)/65535U);
        return 0xff; // command phase clocks out idle data
    }
    if (width==16 && m_pen_command)
    {
        u16 const sample=u16(m_pen_sample<<4);
        m_pen_command=0;
        m_pen_sample=0;
        return sample;
    }
    return 0xffff; // wrong phase, unknown command or unimplemented mode
}

// SPI1 uses the existing scheduler/interrupt controller and SYSCLK domain.
// FIFO/status masks follow the VZ register contract; they are not SPI2 bits.
void alphasdana_state::spi1_reset()
{
    m_spi1=dana_sd::controller{}; m_spi1_word=m_spi1_control=m_spi1_received=0;
    m_spi1_bits_left=0; m_spi1_busy=false; m_spi1_timer->adjust(attotime::never);
    m_ilcr=0x6533; std::fill(std::begin(m_pd_extra),std::end(m_pd_extra),0);
    m_sd_edges=0; m_sd_last_pins=m_sd_irq->read() & 0x0c;
    // A machine reset reinitializes the cards without unmounting either file.
    for (auto &slot:m_sd) slot->lines(false,false);
    sd_lines(); spi1_irq(); sd_gpio_irq();
}

void alphasdana_state::sd_lines()
{
    auto driven=[this](unsigned port,u8 mask,u8 select) {
        return (m_gpio[port*4] & mask) && (select & mask);
    };
    bool const power0=driven(0,0x20,m_gpio[3]) && (m_gpio[1]&0x20);
    bool const power1=driven(6,0x20,m_gpio[27]) && (m_gpio[25]&0x20);
    bool const cs0=driven(5,0x08,m_gpio[23]) && !(m_gpio[21]&0x08);
    bool const cs1=driven(3,0x04,m_pfsel) && !(m_gpio[13]&0x04);
    m_sd[0]->lines(power0,cs0); m_sd[1]->lines(power1,cs1);
}

void alphasdana_state::spi1_irq()
{
    m_pending=(m_pending & ~0x00200000U) | (m_spi1.irq() ? 0x00200000U : 0);
    unsigned const level=(m_ilcr>>12)&7;
    if (m_spi1.irq() && (!level || level==7))
    {
        logerror("DANA_SPI1_BLOCKED INVALID_SPI1_INTERRUPT_LEVEL ILCR=%04x\n",m_ilcr);
        m_spi1_busy=false; m_spi1_timer->adjust(attotime::never);
        m_maincpu->suspend(SUSPEND_REASON_DISABLE,true);
    }
    update_irq_lines();
}

u16 alphasdana_state::spi1_r(offs_t reg)
{
    bool const effects=!machine().side_effects_disabled();
    switch (reg)
    {
    case 0: { u16 const value=m_spi1.pop_rx(effects); if (effects) spi1_irq(); return value; }
    case 1: return m_spi1.last_tx;
    case 2: return m_spi1.control;
    case 3: { u16 const value=m_spi1.status(effects); if (effects) spi1_irq(); return value; }
    case 4: return m_spi1.tx_count | (u16(m_spi1.rx_count)<<4);
    default: return m_spi1.spc;
    }
}

void alphasdana_state::spi1_w(offs_t reg,u16 data,u16 mem_mask)
{
    switch (reg)
    {
    case 0: return; // RX data is read-only.
    case 1:
        if (!m_spi1.push_tx(data,mem_mask))
        { logerror("DANA_SPI1_BLOCKED TX_FIFO_OVERFLOW\n"); m_spi1_busy=false; m_spi1_timer->adjust(attotime::never); m_maincpu->suspend(SUSPEND_REASON_DISABLE,true); }
        break;
    case 2:
    {
        u16 const previous=m_spi1.control;
        COMBINE_DATA(&m_spi1.control);
        if (!(m_spi1.control&0x0200))
        {
            m_spi1.tx_head=m_spi1.rx_head=m_spi1.tx_count=m_spi1.rx_count=0;
            m_spi1.rx_edge=false;
        }
        if ((m_spi1.control&0x0600)!=0x0600 || !(m_spi1.control&0x0100))
        {
            m_spi1_busy=false; m_spi1.control&=~0x0100;
            m_spi1_timer->adjust(attotime::never);
        }
        else if (!(previous&0x0100)) spi1_schedule();
        break;
    }
    case 3: m_spi1.mask=((m_spi1.mask & ~mem_mask)|(data & mem_mask)) & 0x7f00; break;
    case 4:
        if (data & mem_mask)
        { logerror("DANA_SPI1_BLOCKED TEST_MODE_UNQUALIFIED\n"); m_spi1_busy=false; m_spi1_timer->adjust(attotime::never); m_maincpu->suspend(SUSPEND_REASON_DISABLE,true); }
        break;
    case 5:
        COMBINE_DATA(&m_spi1.spc);
        if (m_spi1.spc)
        { logerror("DANA_SPI1_BLOCKED SAMPLE_MODE_UNQUALIFIED\n"); m_spi1_busy=false; m_spi1_timer->adjust(attotime::never); m_maincpu->suspend(SUSPEND_REASON_DISABLE,true); }
        break;
    }
    spi1_irq();
}

void alphasdana_state::spi1_schedule()
{
    if (!m_spi1.tx_count)
    { m_spi1.control&=~0x0100; m_spi1_busy=false; return; }
    // SD SPI permits modes 0 and 3. Never treat an unsupported master/slave,
    // sample/test or phase configuration as successful SD wire traffic.
    bool const polarity=m_spi1.control&0x10, phase=m_spi1.control&0x20;
    if (polarity!=phase || (m_gpio[23]&7) || m_spi1.spc)
    {
        logerror("DANA_SPI1_BLOCKED unsupported_bus_mode control=%04x PJSEL=%02x SPC=%04x\n",m_spi1.control,m_gpio[23],m_spi1.spc);
        m_spi1_busy=false; m_spi1_timer->adjust(attotime::never); m_maincpu->suspend(SUSPEND_REASON_DISABLE,true); return;
    }
    m_spi1_word=m_spi1.pop_tx(); m_spi1_control=m_spi1.control;
    m_spi1_bits_left=m_spi1.bits(); m_spi1_received=0; m_spi1_busy=true;
    m_spi1_timer->adjust(attotime::from_ticks(4U<<((m_spi1_control>>13)&7),guest_system_clock_hz()));
    spi1_irq();
}

TIMER_CALLBACK_MEMBER(alphasdana_state::spi1_complete)
{
    if (!m_spi1_busy) return;
    // Refresh actual output pins at each serial bit, including power/CS
    // transitions during an exchange; no whole-command host shortcut.
    sd_lines();
    if (m_sd[0]->selected() && m_sd[1]->selected())
    {
        logerror("DANA_SPI1_BLOCKED TWO_SELECTED_CARDS_BUS_CONTENTION\n");
        m_spi1_busy=false; m_spi1_timer->adjust(attotime::never); m_maincpu->suspend(SUSPEND_REASON_DISABLE,true); return;
    }
    bool const outgoing=(m_spi1_word>>(m_spi1_bits_left-1))&1;
    bool const a=m_sd[0]->bit(outgoing), b=m_sd[1]->bit(outgoing);
    m_spi1_received=(m_spi1_received<<1)|(a && b);
    if (--m_spi1_bits_left)
    { m_spi1_timer->adjust(attotime::from_ticks(4U<<((m_spi1_control>>13)&7),guest_system_clock_hz())); return; }
    if (!m_spi1.push_rx(m_spi1_received))
    { logerror("DANA_SPI1_BLOCKED RX_FIFO_OVERFLOW\n"); m_spi1_busy=false; m_spi1_timer->adjust(attotime::never); m_maincpu->suspend(SUSPEND_REASON_DISABLE,true); return; }
    spi1_irq();
    if (m_spi1_busy) spi1_schedule(); // A terminal IRQ error must not restart the timer.
}

// PD2/PD3 are independent electrical input levels, NOT invented socket-
// insertion events or SD command-completion interrupts. The pinned sources
// identify the pins but do not establish their external board circuitry.
u8 alphasdana_state::pd_r(offs_t reg)
{
    u8 result=m_gpio[4+reg];
    if (reg==1)
    {
        u8 const inputs=~m_gpio[4] & 0x0c;
        result=(result & ~inputs)|(m_sd_irq->read() & inputs);
        // Motorola VZ PD7/IRQ6: input DATA reads the actual external pin.
        // UK1.5 boot samples PD7 after disabling its internal pull-up; do
        // not conflate the DATA output latch with board input voltage.
        u8 const pd7_input=~m_gpio[4] & 0x80;
        result=(result & ~pd7_input)|(m_pd7_pin->read() & pd7_input);
    }
    return result;
}
void alphasdana_state::pd_w(offs_t reg,u8 value)
{
    m_gpio[4+reg]=value;
    if (reg==1) m_sd_edges&=~(value & m_pd_extra[3]);
    sd_gpio_irq();
}
void alphasdana_state::sd_gpio_irq()
{
    u8 const pins=m_sd_irq->read() & 0x0c;
    u8 const changed=pins ^ m_sd_last_pins;
    m_sd_edges|=changed & ~(pins ^ m_pd_extra[0]);
    m_sd_last_pins=pins;
    u8 const levels=~(pins ^ m_pd_extra[0]) & ~m_pd_extra[3];
    u8 const edges=m_sd_edges & m_pd_extra[3];
    u8 const active=(levels|edges) & m_pd_extra[1] & ~m_gpio[4] & 0x0c;
    m_pending=(m_pending & ~0x00000c00U)|(u32(active)<<8);
    update_irq_lines();
}
INPUT_CHANGED_MEMBER(alphasdana_state::sd_irq_changed) { sd_gpio_irq(); }

INPUT_CHANGED_MEMBER(alphasdana_state::st_key_changed)
{
    // param is the physical Dana scan code. Preserve press/release edges
    // even when both occur between successive guest SPI2 keyboard polls.
    unsigned const scan=unsigned(param);
    if (scan>=128) return;
    u32 const mask=u32(1)<<(scan&31);
    u32 &held=m_st_host_held[scan>>5];
    if (newval) held|=mask;
    else held&=~mask;
    if (m_st_event_count==ST_EVENT_CAPACITY)
    {
        m_st_event_head=u8((unsigned(m_st_event_head)+1)%ST_EVENT_CAPACITY);
        --m_st_event_count;
        logerror("DANA_ST_EVENT_OVERFLOW oldest_snapshot_discarded=1\n");
    }
    unsigned const tail=(unsigned(m_st_event_head)+m_st_event_count)%ST_EVENT_CAPACITY;
    for (unsigned i=0;i<4;++i)
        m_st_events[tail*4+i]=m_st_host_held[i];
    ++m_st_event_count;
}

void alphasdana_state::spi2_ctrl_w(offs_t, u16 data, u16 mem_mask)
{
    COMBINE_DATA(&m_spi2_ctrl);
    // MC68VZ328UM: SPI2 ENABLE=0x0200 and XCH=0x0100.
    // Qualified 012-C also required SPI rate bit 0x2000 in error.
    if ((m_spi2_ctrl & 0x0300)!=0x0300)
        return;
    unsigned const width=(m_spi2_ctrl & 0x000f)+1;
    // PE3 selects original ST; PG2 selects pen ADC. No invented overlap.
    bool const st_selected=!(m_gpio[2*4+1] & 0x08);
    bool const pen_selected=!(m_gpio[4*4+1] & 0x04);
    u16 in=0xffff;
    if (st_selected && !pen_selected && width==8)
        in=st_exchange(u8(m_spi2_data));
    else if (pen_selected && !st_selected)
        in=pen_exchange(width,m_spi2_data);
    m_spi2_data = width==8 ? (m_spi2_data & 0xff00) | (in & 0xff) : in;
    m_spi2_ctrl=(m_spi2_ctrl & ~0x0100) | 0x0080;
    // IRQ4 remains as in original 012-C; EmuTOS polls bit 7.
}

void alphasdana_state::lcd_bootstrap_reset()
{
    // D0.2 register contract; LCD is off until explicitly programmed by guest.
    // These are controller-register initial values, not a physical LCD reset test.
    m_lssa=0; m_lvpw=0xff; m_lxmax=0x03f0; m_lymax=0x01ff;
    m_lcxp=0; m_lcyp=0; m_lcwch=0x0101; m_lblkc=0x7f;
    m_lpicf=0; m_lpolcf=0; m_lacdrc=0; m_lpxcd=0;
    m_lckcon=0; m_lposr=0; m_lgpmr=0x84; m_lrra=0x00ff; m_pwmr=0;
}

u32 alphasdana_state::screen_update(screen_device &, bitmap_rgb32 &bitmap, const rectangle &cliprect)
{
    // Read the actual guest-allocated 560x160 1-bpp framebuffer, never draw a
    // host-generated imitation of an EmuTOS screen. The direct RAM share avoids
    // debugger memory taps falsely classifying video reads as 68000 traffic.
    rgb_t const off(0xbd, 0xbd, 0xaa), on(0x40, 0x40, 0x40);
    bitmap.fill(off, cliprect);
    if (!(m_lckcon & 0x80) || m_lpicf != 8 || m_lvpw != 35
        || m_lxmax != 560 || m_lymax != 159 || (m_lssa & 1)
        || m_lssa > 0x400000 - 11200)
        return 0;
    for (int y=std::max(cliprect.top(),0); y<=std::min(cliprect.bottom(),159); ++y)
    {
        u32 const line = m_lssa + u32(y)*70;
        for (int x=std::max(cliprect.left(),0); x<=std::min(cliprect.right(),559); ++x)
        {
            u16 const word = m_ram[(line >> 1) + u32(x >> 4)];
            bitmap.pix(y,x) = BIT(word,15-(x & 15)) ? on : off;
        }
    }
    return 0;
}

TIMER_CALLBACK_MEMBER(alphasdana_state::clk32_tick)
{
    m_clk32_high = !m_clk32_high;
}

void alphasdana_state::rtc_update_irq()
{
    // MC68VZ328 RTC is bit 4 in interrupt pending LOW, level 4.
    if ((m_rtc_control & 0x0080) && (m_rtc_isr & m_rtc_ien))
        m_pending |= 0x00000010;
    else
        m_pending &= ~u32(0x00000010);
    update_irq_lines();
}

u32 alphasdana_state::rtc_host_seconds()
{
    system_time host;
    machine().current_datetime(host);
    auto const &now=host.local_time;
    return u32(now.hour)*3600U+u32(now.minute)*60U+now.second;
}

void alphasdana_state::rtc_sync_from_host()
{
    if (!(m_rtc_control & 0x0080))
        return; // RTCEN=0: hold programmed time
    s32 const raw=s32(rtc_host_seconds())+m_rtc_offset_seconds;
    s32 const seconds=(raw%86400+86400)%86400;
    m_rtc_time=(u32(seconds/3600)<<24)
        | (u32((seconds/60)%60)<<16) | u32(seconds%60);
}

TIMER_CALLBACK_MEMBER(alphasdana_state::rtc_tick)
{
    if (!(m_rtc_control & 0x0080)) return;
    u32 const previous=m_rtc_last_tick;
    rtc_sync_from_host();
    u32 const current=m_rtc_time;
    if (current!=previous)
    {
        m_rtc_isr |= 0x0010;  // 1Hz event, not generated on plain read
        if (((current>>16)&0x3f)!=((previous>>16)&0x3f))
            m_rtc_isr |= 0x0002; // minute
        if (((current>>24)&0x1f)!=((previous>>24)&0x1f))
            m_rtc_isr |= 0x0020; // hour
        if (((previous>>24)&0x1f)==23 && ((current>>24)&0x1f)==0)
        {
            m_rtc_day=(m_rtc_day+1)&0x01ff;
            m_rtc_isr |= 0x0008; // midnight
        }
        m_rtc_last_tick=current;
    }
    rtc_update_irq();
}

void alphasdana_state::rtc_time_w(offs_t offset, u16 data, u16 mem_mask)
{
    rtc_sync_from_host();
    u32 const shift=offset ? 0 : 16;
    u32 const mask=u32(mem_mask)<<shift;
    u32 const value=(m_rtc_time & ~mask)|(u32(data & mem_mask)<<shift);
    if (!rtc_time_valid(value))
    { physical_block("RTC_TIME_INVALID",0xfffffb00+(offset*2),data); return; }
    m_rtc_time=value;
    m_rtc_last_tick=value;
    s32 const wanted=s32(((value>>24)&0x1f)*3600
        +((value>>16)&0x3f)*60+(value&0x3f));
    m_rtc_offset_seconds=wanted-s32(rtc_host_seconds());
    logerror("DANA_RTC_TIME_WRITE time=%08x offset=%u mask=%04x host_offset_s=%d\n",
        m_rtc_time,unsigned(offset),mem_mask,m_rtc_offset_seconds);
}

void alphasdana_state::rtc_control_w(offs_t, u16 data, u16 mem_mask)
{
    u16 const next=(m_rtc_control & ~mem_mask)|(data & mem_mask);
    // VZ UM 11.2.6: RTCEN bit7, REFREQ bit5; other bits reserved.
    if (next & ~0x00a0)
    { physical_block("RTC_CONTROL_RESERVED_BITS",0xfffffb0c,next); return; }
    // Freeze clock on disable; on re-enable keep the stopped time as
    // origin by recalculating only this device's host offset.
    bool const was_enabled=bool(m_rtc_control & 0x0080);
    if (was_enabled && !(next & 0x0080))
        rtc_sync_from_host();
    m_rtc_control=next;
    if (!was_enabled && (next & 0x0080))
    {
        u32 const t=m_rtc_time;
        s32 const seconds=s32(((t>>24)&0x1f)*3600
            + ((t>>16)&0x3f)*60+(t&0x3f));
        m_rtc_offset_seconds=seconds-s32(rtc_host_seconds());
        m_rtc_last_tick=t;
    }
    rtc_update_irq();
    logerror("DANA_RTC_CONTROL value=%04x rtcen=%u refreq=%u\n",
        m_rtc_control,unsigned(bool(m_rtc_control&0x80)),
        unsigned(bool(m_rtc_control&0x20)));
}

void alphasdana_state::rtc_ien_w(offs_t, u16 data, u16 mem_mask)
{
    u16 const next=(m_rtc_ien & ~mem_mask)|(data & mem_mask);
    // 1Hz, minute, hour and 24h are generated by the 1Hz timer.
    // Subsecond rates, alarm and stopwatch need dedicated mechanics.
    if (next & ~0x003a)
    { physical_block("RTC_INTERRUPT_RATE_UNIMPLEMENTED",0xfffffb10,next); return; }
    m_rtc_ien=next; rtc_update_irq();
    logerror("DANA_RTC_IEN value=%04x\n",m_rtc_ien);
}

void alphasdana_state::rtc_isr_w(offs_t, u16 data, u16 mem_mask)
{
    // Manufacturer VZ RTCISR is write-one-to-clear.
    m_rtc_isr &= ~(data & mem_mask);
    rtc_update_irq();
}

// VZ UM 16.2.3/16.2.4: normal-mode ICE setup only. HMDIS does not
// remap ordinary memory. Other ICE controls require unimplemented machinery.
void alphasdana_state::icemcr_w(offs_t, u16 data, u16 mem_mask)
{
    if (!mem_mask) return;
    u16 const next=((m_icemcr & ~mem_mask) | (data & mem_mask)) & 0x005f;
    if (next & 0x0057)
    { physical_block("ICE_CONTROL_MODE_UNIMPLEMENTED",0xfffffd0c,next); return; }
    m_icemcr=next;
    logerror("DANA_ICE ICEMCR data=%04x mask=%04x value=%04x normal_mode=1\n",data,mem_mask,m_icemcr);
}

void alphasdana_state::icemsr_w(offs_t, u16 data, u16 mem_mask)
{
    if (!mem_mask) return;
    // VZ-specific bit order: EMUEN=3, BBIRQ/BRKIRQ/EMIRQ=2/1/0.
    // Flags are W1C; writing 0007 cannot set EMUEN or manufacture events.
    u16 const next=((m_icemsr & 0x0008 & ~mem_mask) | (data & mem_mask & 0x0008))
        | (m_icemsr & 0x0007 & ~(data & mem_mask));
    if (next & 0x0008)
    { physical_block("ICE_EMULATION_MODE_UNIMPLEMENTED",0xfffffd0e,next); return; }
    m_icemsr=next;
    logerror("DANA_ICE ICEMSR data=%04x mask=%04x value=%04x normal_mode=1\n",data,mem_mask,m_icemsr);
}

// VZ UM 4.4.1: CLKEN gates the CLKO output, not the PLL itself.
// Keep the qualified PLLFSR-derived CPU/peripheral clocks unchanged. Reject
// unsupported divider, sleep and wake-delay changes before committing them.
u16 alphasdana_state::pwm1_control_r()
{
    // Motorola §15.4.1: FIFOAV is a read-only status bit. With the
    // real 5-byte FIFO empty and PWM1 disabled it stays set. Repeat
    // count bits are write-only and therefore read back as zero.
    u16 const value=(m_pwm1_control & ~u16(0x000c)) | 0x0020;
    m_pwm1_control &= ~u16(0x0080); // IRQ status clears on control read
    return value;
}

void alphasdana_state::pwm1_control_w(offs_t, u16 data, u16 mem_mask)
{
    u16 const next=(m_pwm1_control & ~mem_mask) | (data & mem_mask);
    // Original UK1.5 ANDI.W #FFEF disables PWM1. Enabling audio,
    // FIFO interrupts or a software IRQ cannot be claimed without the
    // actual PWM sample FIFO, clock and sound-output machinery.
    if ((next & 0x0050) || (data & mem_mask & 0x0080))
    {
        physical_block("PWM1_AUDIO_OR_IRQ_UNIMPLEMENTED",0xfffff500,data);
        return;
    }
    // Bit5 FIFOAV is hardware-owned, bit7 IRQ is status; neither is
    // writable. Other documented fields remain programmable while off.
    m_pwm1_control=(next & 0xff1f) | 0x0020;
    logerror("DANA_PWM1_CONTROL value=%04x enabled=0 fifo_available=1\n",
        m_pwm1_control);
}

void alphasdana_state::pctlr_w(u8 data)
{
    // Only valid hardware bits; the two reserved bits read back zero.
    u8 const next=data & 0x9f;
    // PCM burst gating affects the CPU instruction clock, not SYSCLK. Do not
    // accept a partial-duty or completely disabled CPU clock as fully running.
    if ((next & 0x80) && (next & 0x1f)!=0x1f)
    {
        physical_block("PCTLR_CPU_BURST_UNIMPLEMENTED",0xfffff207,data);
        return;
    }
    m_pctlr=next;
    logerror("DANA_PCTLR value=%02x pcen=%u width=%u cpuclk_full_duty=1\n",
        m_pctlr,unsigned(bool(m_pctlr & 0x80)),unsigned(m_pctlr & 0x1f));
}

void alphasdana_state::pllcr_w(offs_t, u16 data, u16 mem_mask)
{
    u16 const next=((m_pllcr & ~mem_mask) | (data & mem_mask)) & 0x3fbb;
    u16 const changed=next ^ m_pllcr;
    if (changed & 0x0008)
    { physical_block("PLL_SLEEP_MODE_UNIMPLEMENTED",0xfffff200,next); return; }
    // Physical VZ SYSCLK and prescaler changes are documented in UM 4.4.1.
    // R-direct retains its previously qualified clock contract; LCD timing
    // selection is separately unmodelled and must not silently succeed.
    if ((changed & 0x3fa0) && (!m_physical_boot || (changed & 0x3800)))
    { physical_block("PLL_CLOCK_MODE_UNIMPLEMENTED",0xfffff200,next); return; }
    if (changed & 0x0003)
    { physical_block("PLL_WAKE_DELAY_UNIMPLEMENTED",0xfffff200,next); return; }
    if (m_physical_boot && (changed & 0x07a0) && (m_tctl1 & 1))
        m_tcn1=timer1_tcn_r(); // Snapshot before changing virtual SYSCLK.
    m_pllcr=next;
    if (m_physical_boot && (changed & 0x07a0))
    {
        m_maincpu->set_unscaled_clock(physical_system_clock_hz());
        if (m_tctl1 & 1) timer1_schedule();
    }
    if (changed)
        logerror("DANA_PLLCR value=%04x clko_enabled=%u pfsel=%02x sysclk_hz=%u physical_clock_change=%u\n",
            m_pllcr,unsigned(pllcr_clko_enabled()),m_pfsel,
            m_physical_boot ? physical_system_clock_hz() : guest_system_clock_hz(),
            unsigned(m_physical_boot && bool(changed & 0x07a0)));
}

void alphasdana_state::pllfsr_w(offs_t, u16 data, u16 mem_mask)
{
    // Motorola MC68VZ328UM 4.4.2: CLK32 read-only; reserved bits stay 0.
    // PC[7:0] and QC[11:8] permit 16-bit or lane-selected accesses before
    // sticky PROT[14] is set; PROT can only be cleared by machine reset.
    // One write may set the counters and PROT together. Subsequent writes
    // cannot alter the counters, even when they attempt to clear PROT.
    // Snapshot elapsed ticks against the OLD source frequency before any
    // permitted PLL retune. Otherwise the new schedule loses partial ticks.
    if (m_tctl1 & 1) m_tcn1=timer1_tcn_r();
    u16 const counter_mask = mem_mask & 0x0fff;
    if (!(m_pllfsr & 0x4000))
        m_pllfsr = (m_pllfsr & ~counter_mask) | (data & counter_mask);
    if (data & mem_mask & 0x4000)
        m_pllfsr |= 0x4000;
    // Preserve the 1 MHz no-guest diagnostic clock, which the R2.1 and
    // register-only fixtures already qualified. Authentic RAM guest runs
    // instead use the VZ PLL-derived M68000 clock, matching their Timer1.
    if (m_guest_loaded || m_physical_boot)
        m_maincpu->set_unscaled_clock(m_physical_boot ? physical_system_clock_hz() : guest_system_clock_hz());
    if (m_tctl1 & 1)
        timer1_schedule();
}

u8 alphasdana_state::ivr_r()
{
    // Actual handler dispatch, independently countable in MAME -log output.
    logerror("DANA_VZ_IVR_READ state=%02x\n", m_ivr);
    return m_ivr;
}

void alphasdana_state::ivr_w(u8 data)
{
    // VZ interrupt vector group occupies IVR[7:3]. Lower bits are ignored.
    // The exact mask agrees with pinned MAME mc68328_base_device::ivr_w.
    m_ivr = data & 0xf8;
    logerror("DANA_VZ_IVR_WRITE data=%02x state=%02x\n", data, m_ivr);
}


// VZ interrupt group. Preserve Timer1/UART1; SPI1 uses ILCR and PD2/3 use IRQ4.
// Guest IVR=0x40 and CPU space IACK allow authentic interrupt vectors.
// PLLCR/PCTRL and unrelated sources stay unimplemented; no broad MMIO stub.
void alphasdana_state::imr_w(offs_t offset, u16 data, u16 mem_mask)
{
    unsigned const shift = offset ? 0 : 16;
    u32 const mask = u32(mem_mask) << shift;
    m_imr = ((m_imr & ~mask) | (u32(data & mem_mask) << shift)) & 0x00ffffff;
    update_irq_lines();
}

void alphasdana_state::isr_w(offs_t offset, u16 data, u16 mem_mask)
{
    // Edge-selected external IRQ1/2/3/6 acknowledge (the only writable ISR
    // bits). With no asserted external source, writes cannot invent an IRQ.
    if (!offset)
    {
        u16 const edges = ((m_icr >> 11) & 1) | ((m_icr >> 9) & 2)
            | ((m_icr >> 7) & 4) | ((m_icr >> 5) & 8);
        m_pending &= ~(u32(data & mem_mask & edges) << 16);
    }
    update_irq_lines();
}


void alphasdana_state::update_irq_lines()
{
    // VZ IPR/IMR masks proven by pinned EmuTOS: bit1 Timer1 -> level6,
    // bit2 UART1 and INT2/3 -> level4; SPI1 bit21 uses ILCR[14:12].
    u32 const active=m_pending & ~m_imr;
    unsigned const spi_level=(m_ilcr>>12)&7;
    for (unsigned level=1;level<=6;++level)
    {
        bool const spi=(spi_level==level) && (active & 0x00200000);
        if (level!=4 && level!=6) m_maincpu->set_input_line(level,spi ? ASSERT_LINE : CLEAR_LINE);
    }
    m_maincpu->set_input_line(6,((active & 0x00000002) || (spi_level==6 && (active & 0x00200000))) ? ASSERT_LINE : CLEAR_LINE);
    m_maincpu->set_input_line(4,((active & 0x00000c14) || (spi_level==4 && (active & 0x00200000))) ? ASSERT_LINE : CLEAR_LINE);
}

u8 alphasdana_state::irq_vector_r(offs_t offset)
{
    // DragonBall CPU-space IACK convention. IVR=0x40 gives the authentic
    // EmuTOS VEC_USER(6)=0x46 and VEC_USER(4)=0x44.
    u8 const vector=m_ivr | (offset & 7);
    if ((offset & 7)==6 && (m_pending & ~m_imr & 2))
        ++m_timer1_iacks;
    // Bound diagnostics to the early authentic boot. Counters remain live and
    // save-state backed, avoiding thousands of repetitive log lines.
    if ((offset & 7)!=6 || m_timer1_iacks<=16)
        logerror("DANA_VZ_IACK level=%u vector=%02x pending=%08x imr=%08x ack6=%u\n",
            unsigned(offset & 7), vector, m_pending, m_imr,
            unsigned(m_timer1_iacks));
    return vector;
}

u32 alphasdana_state::guest_system_clock_hz() const
{
    // Preserve the qualified EmuTOS-Dana/R-direct base clock formula.
    // This is HALF the manufacturer PLLCLK formula, before physical dividers.
    return (u32(m_pllfsr & 0xff)*14
        + u32((m_pllfsr >> 8) & 0x3f)+15)*32768;
}
u32 alphasdana_state::physical_system_clock_hz() const
{
    // Motorola MC68VZ328UM 4.3.2.2: PLLCLK =
    // 2 * (14*(PC+1) + QC+1) * CLK32. Then PRESC1, PRESC2,
    // and SYSCLKSEL: 000=/2, 001=/4, 010=/8, 011=/16, 1xx=/1.
    u32 const pll_hz=guest_system_clock_hz()*2;
    u32 const presc1=(m_pllcr & 0x0080) ? 2 : 1;
    u32 const presc2=(m_pllcr & 0x0020) ? 2 : 1;
    u32 const select=(m_pllcr >> 8) & 7;
    u32 const sys_div=select>=4 ? 1 : (2U << select);
    return pll_hz/(presc1*presc2*sys_div);
}
u32 alphasdana_state::timer1_source_hz() const
{
    // CPU and SYSCLK-sourced Timer1 must advance in the SAME guest time.
    u32 const guest_hz=m_physical_boot ? physical_system_clock_hz() : guest_system_clock_hz();
    switch(m_tctl1 & 0x000e)
    {
    case 0x0002: return guest_hz;
    case 0x0004: return guest_hz/16;
    case 0x0008: case 0x000a: case 0x000c: case 0x000e:
        return 32768;
    default: return 0; // STOP or external TIN; no invented clock.
    }
}
void alphasdana_state::timer1_schedule()
{
    u32 const hz=timer1_source_hz();
    if (!(m_tctl1 & 1) || !hz || !m_tcmp1)
    {
        m_timer1_timer->adjust(attotime::never);
        return;
    }
    // MAME's MC68328 timer has restart (FRR=0) and free-run (FRR=1)
    // modes. Schedule the NEXT compare from the current counter position,
    // never restart an entire period on a mid-cycle register write.
    // Both free-run and restart reach the comparator through a wrapping
    // 16-bit counter. They differ only in the post-match counter value:
    // restart resets it to zero; free-run retains the comparator position.
    u32 remaining=(u32(m_tcmp1)-u32(m_tcn1)) & 0xffff;
    if (!remaining) remaining=65536;
    m_timer1_timer->adjust(attotime::from_ticks(
        u64(m_tprer1+1)*remaining,hz));
}
TIMER_CALLBACK_MEMBER(alphasdana_state::timer1_compare)
{
    // One virtual-time callback per actual comparator match. FRR=0 resets
    // counter; FRR=1 retains comparator position and wraps at 16 bits.
    m_tstat1 |= 1;
    m_tcn1=(m_tctl1 & 0x0100) ? m_tcmp1 : 0;
    ++m_timer1_compares;
    if (m_tctl1 & 0x0010) m_pending |= 0x00000002;
    if (m_timer1_compares<=16)
        logerror("DANA_VZ_TIMER1_COMPARE count=%u tctl=%04x tprer=%04x tcmp=%04x pending=%08x\n",
            unsigned(m_timer1_compares),m_tctl1,m_tprer1,m_tcmp1,m_pending);
    update_irq_lines();
    timer1_schedule();
}
void alphasdana_state::timer1_tctl_w(offs_t, u16 data, u16 mem_mask)
{
    bool const enabled=bool(m_tctl1 & 1);
    if (enabled) m_tcn1=timer1_tcn_r();
    COMBINE_DATA(&m_tctl1);
    if (!enabled && (m_tctl1 & 1)) m_tcn1=0;
    timer1_schedule();
}
void alphasdana_state::timer1_tprer_w(offs_t, u16 data, u16 mem_mask)
{
    if (m_tctl1 & 1) m_tcn1=timer1_tcn_r();
    COMBINE_DATA(&m_tprer1);
    timer1_schedule();
}
void alphasdana_state::timer1_tcmp_w(offs_t, u16 data, u16 mem_mask)
{
    if (m_tctl1 & 1) m_tcn1=timer1_tcn_r();
    COMBINE_DATA(&m_tcmp1);
    timer1_schedule();
}
u16 alphasdana_state::timer1_tcn_r()
{
    u32 const hz=timer1_source_hz();
    if (!(m_tctl1 & 1) || !hz || !m_tcmp1) return m_tcn1;
    u64 const delta=m_timer1_timer->elapsed().as_ticks(hz)/u64(m_tprer1+1);
    return u16((u64(m_tcn1)+delta)&0xffff);
}
u16 alphasdana_state::timer1_tstat_r()
{
    // Reuse MAME mc68328::tstat_r read-then-write clearing semantics.
    m_tstat_clear1 |= m_tstat1;
    return m_tstat1;
}
void alphasdana_state::timer1_tstat_w(offs_t, u16, u16 mem_mask)
{
    m_tstat1 &= ~(m_tstat_clear1 & mem_mask);
    m_tstat_clear1 &= ~mem_mask;
    if (!(m_tstat1 & 1)) m_pending &= ~u32(0x00000002);
    update_irq_lines();
}
void alphasdana_state::uart1_utx_w(offs_t, u16 data, u16 mem_mask)
{
    // Source-backed ready/empty UART transmitter. No unsolicited RX IRQ.
    m_utx1=(m_utx1 & ~mem_mask) | (data & mem_mask & 0x1fff);
    if (mem_mask & 0x00ff)
        logerror("DANA_VZ_UART1_TX data=%02x char=%c\n",
            unsigned(data & 0xff),
            (data & 0xff)>=32 && (data & 0xff)<=126
                ? char(data & 0xff) : '.');
}

QUICKLOAD_LOAD_MEMBER(alphasdana_state::guest_load)
{
    // B-record transport can select silicon bootstrap without a Flash ROM.
    if(image.length()>=10 && image.length()<=4*1024*1024) {
        std::vector<u8> raw(image.length());
        if(image.fread(raw.data(),raw.size())!=raw.size())
            return std::make_pair(image_error::INVALIDIMAGE,std::string("Short bootstrap/guest image read"));
        if(std::memcmp(raw.data(),"DANARAM1",8))
            return bootstrap_load(raw);
        image.fseek(0,SEEK_SET);
    }
    if (m_firmware->exists() || m_physical_boot)
        return std::make_pair(image_error::INVALIDIMAGE,std::string("DANARAM1 cannot replace a physical Flash boot"));
    // DANARAM1: 64-byte big-endian map-verified envelope, followed by the
    // unmodified EmuTOS image. tools/f1_guest.py binds the original image,
    // first-stage ROM and linker map with SHA-256 before this native load.
    auto bad = [] (const char *why) {
        return std::make_pair(image_error::INVALIDIMAGE, std::string(why));
    };
    if (image.length() < 66 || image.length() > 0x400040)
        return bad("Invalid Dana RAM package length");
    std::vector<u8> data(image.length());
    if (image.fread(data.data(), data.size()) != data.size())
        return bad("Short Dana RAM package read");
    if (std::memcmp(data.data(), "DANARAM1", 8))
        return bad("Not a DANARAM1 package");
    auto be32 = [&data] (unsigned off) -> u32 {
        return (u32(data[off]) << 24) | (u32(data[off+1]) << 16)
            | (u32(data[off+2]) << 8) | data[off+3];
    };
    u32 const entry = be32(8), base = be32(12), length = be32(16);
    u32 const stack = be32(20), phystop = be32(24), lowtop = be32(28);
    u32 const bss = be32(32), ebss = be32(36), flags = be32(60);
    if (flags != 1 || base != 0x2140 || entry != base || length != data.size()-64
        || length > 0x400000-base || (length & 1) || length < 2
        || stack < 0x800 || (stack & 1) || stack > lowtop || lowtop > base
        || bss < base+length || ebss < bss || ebss > 0x400000 || phystop != 0x400000)
        return bad("Invalid map, stack, entry or 4 MiB RAM bounds");
    auto const hash = util::sha1_creator::simple(data.data()+64, length);
    if (std::memcmp(hash.m_raw, data.data()+40, 20))
        return bad("Guest image digest mismatch");
    auto &space = m_maincpu->space(AS_PROGRAM);
    for (u32 addr=0; addr<0x400000; addr+=4)
        space.write_dword(addr, 0);
    for (u32 i=0; i<length; ++i)
        space.write_byte(base+i, data[64+i]);
    // Explicit synthetic R-direct bootstrap, not Dana Flash/Palm reset.
    space.write_dword(0, stack);
    space.write_dword(4, entry);
    space.write_dword(0x42e, phystop);
    space.write_dword(0x6fc, 0); // Cold RAM fixture; let the guest initialize it.
    for (int r=0; r<8; ++r)
        m_maincpu->set_state_int(M68K_D0+r, 0);
    for (int r=0; r<7; ++r)
        m_maincpu->set_state_int(M68K_A0+r, 0);
    m_maincpu->set_state_int(M68K_SR, 0x2700);
    m_guest_loaded = true;
    // Use actual post-bootstrap VZ SYSCLK for the authentic guest, not the
    // 1 MHz diagnostic fixture clock. The absence-of-guest DIAG is unchanged.
    m_maincpu->set_unscaled_clock(guest_system_clock_hz());
    m_guest_ready = 1;
    logerror("DANA_GUEST_LOAD entry=%08x stack=%08x bytes=%u sha1=%s profile=R-direct phystop=%08x\n",
        entry, stack, length, hash.as_string(), phystop);
    // Native reset sequencing fetches the seeded vectors; do not write PC.
    m_maincpu->reset();
    m_maincpu->resume(SUSPEND_REASON_DISABLE);
    return std::make_pair(std::error_condition(), std::string());
}

u16 alphasdana_state::bootstrap_ibuff_r(offs_t offset,u16 mem_mask)
{
    u32 const byte=u32(offset)*2;
    if(!m_bootstrap_mode)
        return physical_r((0x00ffffc0U+byte)>>1,mem_mask);
    return u16(u16(m_bootstrap_ibuff[byte])<<8)|m_bootstrap_ibuff[byte+1];
}

void alphasdana_state::bootstrap_ibuff_w(offs_t offset,u16 data,u16 mem_mask)
{
    u32 const byte=u32(offset)*2;
    if(!m_bootstrap_mode)
    {
        physical_w((0x00ffffc0U+byte)>>1,data,mem_mask);
        return;
    }
    if(mem_mask&0xff00)m_bootstrap_ibuff[byte]=u8(data>>8);
    if(mem_mask&0x00ff)m_bootstrap_ibuff[byte+1]=u8(data);
}

std::pair<std::error_condition,std::string>
alphasdana_state::bootstrap_load(std::vector<u8> const &data)
{
    auto fail=[](std::string why)->std::pair<std::error_condition,std::string> {
        return {image_error::INVALIDIMAGE,std::move(why)};
    };
    vz328_bootstrap::program const p=vz328_bootstrap::parse(
        std::string_view(reinterpret_cast<char const *>(data.data()),data.size()));
    if(!p.valid())
        return fail(p.error);
    // A B-record image asserts EMUBRK before issuing a simulated reset.
    // The silicon loader executes via a high-level UART record service;
    // no external chip or substitute guest ROM is introduced.
    m_bootstrap_mode=true;
    m_physical_boot=true;
    m_boot_memory.select(1);
    physical_reset();
    for(unsigned i=0;i<sizeof(m_bootstrap_ibuff);i+=2)
    {
        m_bootstrap_ibuff[i]=0x4e;
        m_bootstrap_ibuff[i+1]=0x71; // Unwritten internal buffer = NOP
    }
    m_maincpu->reset();
    m_maincpu->suspend(SUSPEND_REASON_DISABLE,true);
    auto &bus=m_maincpu->space(AS_PROGRAM);
    unsigned writes=0;
    for(auto const &rec:p.records)
    {
        if(rec.execute())
        {
            if(rec.address&1)
                return fail("VZ execution address must be even");
            // A real VZ jumps into RAM, or executes internal IBUFF and
            // returns to bootstrap. This bridge supports the jump-to-code
            // use case; IBUFF return-to-loader needs silicon ROM tracing.
            logerror("DANA_VZ_BOOTSTRAP_EXEC address=%08x writes=%u uart=19200\n",
                rec.address,writes);
            m_maincpu->set_state_int(M68K_PC,rec.address);
            m_guest_ready=1;
            m_maincpu->resume(SUSPEND_REASON_DISABLE);
            return {std::error_condition(),std::string()};
        }
        for(unsigned i=0;i<rec.count;++i)
        {
            bus.write_byte(rec.address+i,rec.data[i]);
            if(m_physical_blocked)
                return fail(util::string_format(
                    "VZ bootstrap bus rejected write to %08x",rec.address+i));
            ++writes;
        }
    }
    logerror("DANA_VZ_BOOTSTRAP_READY records=%u writes=%u awaiting_exec=1\n",
        unsigned(p.records.size()),writes);
    return {std::error_condition(),std::string()};
}

void alphasdana_state::cpu_space_map(address_map &map)
{
    // The M68000 IRQ acknowledge vector lives in CPU space, not MMIO RAM.
    map(0xfffffff0,0xffffffff).r(FUNC(alphasdana_state::irq_vector_r)).umask16(0x00ff);
}
void alphasdana_state::program_map(address_map &map)
{
    // Preserve the independently qualified D1.2 synthetic post-bootstrap RAM.
    map(0x00000000,0xffffffff).view(m_boot_memory);
    m_boot_memory[0](0x00000000,0x003fffff).ram().share("ram");
    m_boot_memory[1](0x00000000,0xffffefff).rw(FUNC(alphasdana_state::physical_r),FUNC(alphasdana_state::physical_w));
    // Dedicated VZ 32-byte instruction buffer; normal firmware does not
    // receive a separate emulated ROM or any guest memory injection.
    m_boot_memory[1](0x00ffffc0,0x00ffffdf).rw(FUNC(alphasdana_state::bootstrap_ibuff_r),FUNC(alphasdana_state::bootstrap_ibuff_w));
    m_boot_memory[1](0xffffff00,0xffffff01).r(FUNC(alphasdana_state::bootstrap_wait_r));
    // Dana's external Philips ISP1161: HC (A1=0) and DC (A1=1),
    // each a 16-bit data/command pair, with distinct command state.
    m_boot_memory[1](0x1f000000,0x1f000007).rw(FUNC(alphasdana_state::isp1161_r),FUNC(alphasdana_state::isp1161_w));
    m_boot_memory[1](0xfffff000,0xffffffff).rw(FUNC(alphasdana_state::physical_mmio_r),FUNC(alphasdana_state::physical_mmio_w));
    // The genuine UK1.5 ROM accesses the LCD cursor from physical mode.
    // Scope MMIO to the four manufacturer-defined cursor registers only.
    m_boot_memory[1](0xfffffa18,0xfffffa19).rw(FUNC(alphasdana_state::lcxp_r),FUNC(alphasdana_state::lcxp_w));
    m_boot_memory[1](0xfffffa1a,0xfffffa1b).rw(FUNC(alphasdana_state::lcyp_r),FUNC(alphasdana_state::lcyp_w));
    m_boot_memory[1](0xfffffa1c,0xfffffa1d).rw(FUNC(alphasdana_state::lcwch_r),FUNC(alphasdana_state::lcwch_w));
    m_boot_memory[1](0xfffffa1f,0xfffffa1f).rw(FUNC(alphasdana_state::lblkc_r),FUNC(alphasdana_state::lblkc_w)).umask16(0x00ff);
    // Additional system/chip-select/DRAM registers exist only in physical mode.
    m_boot_memory[1](0xfffff000,0xfffff000).rw(FUNC(alphasdana_state::scr_r),FUNC(alphasdana_state::scr_w));
    // Fixed VZ part ID from pinned M68VZ328Hwr/EmRegsVZ; mask revision is not guessed.
    m_boot_memory[1](0xfffff004,0xfffff004).lr8(NAME([]() { return u8(0x56); }));
    m_boot_memory[1](0xfffff008,0xfffff009).rw(FUNC(alphasdana_state::iodcr_r),FUNC(alphasdana_state::iodcr_w));
    m_boot_memory[1](0xfffff100,0xfffff10d).rw(FUNC(alphasdana_state::cs_r),FUNC(alphasdana_state::cs_w));
    m_boot_memory[1](0xfffff110,0xfffff117).rw(FUNC(alphasdana_state::cs_select_r),FUNC(alphasdana_state::cs_select_w));
    m_boot_memory[1](0xfffff118,0xfffff119).rw(FUNC(alphasdana_state::emucs_r),FUNC(alphasdana_state::emucs_w));
    m_boot_memory[1](0xfffff150,0xfffff151).rw(FUNC(alphasdana_state::cs_control3_r),FUNC(alphasdana_state::cs_control3_w));
    m_boot_memory[1](0xfffff200,0xfffff201).rw(FUNC(alphasdana_state::pllcr_r),FUNC(alphasdana_state::pllcr_w));
    m_boot_memory[1](0xfffff207,0xfffff207).rw(FUNC(alphasdana_state::pctlr_r),FUNC(alphasdana_state::pctlr_w)).umask16(0x00ff);
    m_boot_memory[1](0xfffff500,0xfffff501).rw(FUNC(alphasdana_state::pwm1_control_r),FUNC(alphasdana_state::pwm1_control_w));
    m_boot_memory[1](0xfffff410,0xfffff410).rw(FUNC(alphasdana_state::pcdir_r),FUNC(alphasdana_state::pcdir_w)).umask16(0xff00);
    // Native UK1.5 cold-start also writes TCTL2=0000 after TCTL1=0000.
    m_boot_memory[1](0xfffff610,0xfffff611).rw(FUNC(alphasdana_state::timer2_tctl_r),FUNC(alphasdana_state::timer2_tctl_w));
    m_boot_memory[1](0xfffff411,0xfffff411).rw(FUNC(alphasdana_state::pcdata_r),FUNC(alphasdana_state::pcdata_w)).umask16(0x00ff);
    m_boot_memory[1](0xfffffb00,0xfffffb03).rw(FUNC(alphasdana_state::rtc_time_r),FUNC(alphasdana_state::rtc_time_w));
    m_boot_memory[1](0xfffffb0c,0xfffffb0d).rw(FUNC(alphasdana_state::rtc_control_r),FUNC(alphasdana_state::rtc_control_w));
    m_boot_memory[1](0xfffffb0e,0xfffffb0f).rw(FUNC(alphasdana_state::rtc_isr_r),FUNC(alphasdana_state::rtc_isr_w));
    m_boot_memory[1](0xfffffb10,0xfffffb11).rw(FUNC(alphasdana_state::rtc_ien_r),FUNC(alphasdana_state::rtc_ien_w));
    m_boot_memory[1](0xfffffb0a,0xfffffb0b).rw(FUNC(alphasdana_state::watchdog_r),FUNC(alphasdana_state::watchdog_w));
    m_boot_memory[1](0xfffffc00,0xfffffc07).rw(FUNC(alphasdana_state::dram_r),FUNC(alphasdana_state::dram_w));
    m_boot_memory[1](0xfffffd0c,0xfffffd0d).rw(FUNC(alphasdana_state::icemcr_r),FUNC(alphasdana_state::icemcr_w));
    m_boot_memory[1](0xfffffd0e,0xfffffd0f).rw(FUNC(alphasdana_state::icemsr_r),FUNC(alphasdana_state::icemsr_w));

    // Individually decoded VZ registers only, never a blanket MMIO RAM page.
    // SCR.DMAP conditional low-address aliases remain intentionally unmapped.
    map(0xfffff202, 0xfffff203).rw(FUNC(alphasdana_state::pllfsr_r), FUNC(alphasdana_state::pllfsr_w));
    map(0xfffff300, 0xfffff300).rw(FUNC(alphasdana_state::ivr_r), FUNC(alphasdana_state::ivr_w));
    map(0xfffff302, 0xfffff303).rw(FUNC(alphasdana_state::icr_r), FUNC(alphasdana_state::icr_w));
    map(0xfffff304, 0xfffff307).rw(FUNC(alphasdana_state::imr_r), FUNC(alphasdana_state::imr_w));
    map(0xfffff30c, 0xfffff30f).rw(FUNC(alphasdana_state::isr_r), FUNC(alphasdana_state::isr_w));
    map(0xfffff310, 0xfffff313).r(FUNC(alphasdana_state::ipr_r));
    map(0xfffff314,0xfffff315).rw(FUNC(alphasdana_state::ilcr_r),FUNC(alphasdana_state::ilcr_w));
    // Timer1 / UART1 complete register groups (individual, true VZ lanes).
    map(0xfffff600,0xfffff601).rw(FUNC(alphasdana_state::timer1_tctl_r),FUNC(alphasdana_state::timer1_tctl_w));
    map(0xfffff602,0xfffff603).rw(FUNC(alphasdana_state::timer1_tprer_r),FUNC(alphasdana_state::timer1_tprer_w));
    map(0xfffff604,0xfffff605).rw(FUNC(alphasdana_state::timer1_tcmp_r),FUNC(alphasdana_state::timer1_tcmp_w));
    map(0xfffff606,0xfffff607).r(FUNC(alphasdana_state::timer1_tcr_r));
    map(0xfffff608,0xfffff609).r(FUNC(alphasdana_state::timer1_tcn_r));
    map(0xfffff60a,0xfffff60b).rw(FUNC(alphasdana_state::timer1_tstat_r),FUNC(alphasdana_state::timer1_tstat_w));
    map(0xfffff900,0xfffff901).rw(FUNC(alphasdana_state::uart1_ustcnt_r),FUNC(alphasdana_state::uart1_ustcnt_w));
    map(0xfffff902,0xfffff903).rw(FUNC(alphasdana_state::uart1_ubaud_r),FUNC(alphasdana_state::uart1_ubaud_w));
    map(0xfffff904,0xfffff905).r(FUNC(alphasdana_state::uart1_urx_r));
    map(0xfffff906,0xfffff907).rw(FUNC(alphasdana_state::uart1_utx_r),FUNC(alphasdana_state::uart1_utx_w));
    map(0xfffff908,0xfffff909).rw(FUNC(alphasdana_state::uart1_umisc_r),FUNC(alphasdana_state::uart1_umisc_w));
    map(0xfffff90a,0xfffff90b).rw(FUNC(alphasdana_state::uart1_prescaler_r),FUNC(alphasdana_state::uart1_prescaler_w));

    // VZ Port C: eight pulldown enables and eight GPIO/function selects.
    // Native u8 handlers preserve the M68000 high/even and low/odd lanes,
    // including a word spanning both registers. PCDIR and PCDATA are
    // separately decoded in the physical view; external pins/LCD are not faked.
    // See docs/D2_2_PORTC_IMPLEMENTATION.md for the primary-source limitation.
    map(0xfffff412, 0xfffff412).rw(FUNC(alphasdana_state::pcpden_r), FUNC(alphasdana_state::pcpden_w));
    map(0xfffff413, 0xfffff413).rw(FUNC(alphasdana_state::pcsel_r), FUNC(alphasdana_state::pcsel_w));
    // Preserve the individually qualified PFSEL low byte; the grouped Port F
    // mapping below now provides its separate F42A PFPUEN high byte.
    map(0xfffff42b, 0xfffff42b).rw(FUNC(alphasdana_state::pfsel_r), FUNC(alphasdana_state::pfsel_w));

    // One coherent Dana VZ R-direct GPIO family. DATA registers are output
    // latches; external inputs are explicitly scoped per pin. Preserve the
    // separately qualified Port C and PFSEL byte handlers.
    map(0xfffff408,0xfffff40b).rw(FUNC(alphasdana_state::pb_r),FUNC(alphasdana_state::pb_w));
    map(0xfffff418,0xfffff41b).rw(FUNC(alphasdana_state::pd_r),FUNC(alphasdana_state::pd_w));
    map(0xfffff41c,0xfffff41f).rw(FUNC(alphasdana_state::pd_extra_r),FUNC(alphasdana_state::pd_extra_w));
    map(0xfffff420,0xfffff423).rw(FUNC(alphasdana_state::pe_r),FUNC(alphasdana_state::pe_w));
    map(0xfffff428,0xfffff42a).rw(FUNC(alphasdana_state::pf_r),FUNC(alphasdana_state::pf_w));
    map(0xfffff430,0xfffff433).rw(FUNC(alphasdana_state::pg_r),FUNC(alphasdana_state::pg_w));
    map(0xfffff438,0xfffff43b).rw(FUNC(alphasdana_state::pj_r),FUNC(alphasdana_state::pj_w));
    map(0xfffff440,0xfffff443).rw(FUNC(alphasdana_state::pk_r),FUNC(alphasdana_state::pk_w));
    map(0xfffff448,0xfffff44b).rw(FUNC(alphasdana_state::pm_r),FUNC(alphasdana_state::pm_w));

    map(0xfffff700,0xfffff70b).rw(FUNC(alphasdana_state::spi1_r),FUNC(alphasdana_state::spi1_w));

    // Dana SPI2 register pair (ST keyboard and pen bus).
    map(0xfffff800,0xfffff801).rw(FUNC(alphasdana_state::spi2_data_r),FUNC(alphasdana_state::spi2_data_w));
    map(0xfffff802,0xfffff803).rw(FUNC(alphasdana_state::spi2_ctrl_r),FUNC(alphasdana_state::spi2_ctrl_w));

    // Dana LCD controller programmed by authentic EmuTOS. Native big-endian
    // word splitting for LSSA and LRRA, especially AD-corrected 16-bit LRRA.
    map(0xfffffa00,0xfffffa03).rw(FUNC(alphasdana_state::lssa_r),FUNC(alphasdana_state::lssa_w));
    map(0xfffffa05,0xfffffa05).rw(FUNC(alphasdana_state::lvpw_r),FUNC(alphasdana_state::lvpw_w));
    map(0xfffffa08,0xfffffa09).rw(FUNC(alphasdana_state::lxmax_r),FUNC(alphasdana_state::lxmax_w));
    map(0xfffffa0a,0xfffffa0b).rw(FUNC(alphasdana_state::lymax_r),FUNC(alphasdana_state::lymax_w));
    map(0xfffffa18,0xfffffa19).rw(FUNC(alphasdana_state::lcxp_r),FUNC(alphasdana_state::lcxp_w));
    map(0xfffffa1a,0xfffffa1b).rw(FUNC(alphasdana_state::lcyp_r),FUNC(alphasdana_state::lcyp_w));
    map(0xfffffa1c,0xfffffa1d).rw(FUNC(alphasdana_state::lcwch_r),FUNC(alphasdana_state::lcwch_w));
    map(0xfffffa1f,0xfffffa1f).rw(FUNC(alphasdana_state::lblkc_r),FUNC(alphasdana_state::lblkc_w)).umask16(0x00ff);
    map(0xfffffa20,0xfffffa20).rw(FUNC(alphasdana_state::lpicf_r),FUNC(alphasdana_state::lpicf_w));
    map(0xfffffa21,0xfffffa21).rw(FUNC(alphasdana_state::lpolcf_r),FUNC(alphasdana_state::lpolcf_w));
    map(0xfffffa23,0xfffffa23).rw(FUNC(alphasdana_state::lacdrc_r),FUNC(alphasdana_state::lacdrc_w));
    map(0xfffffa25,0xfffffa25).rw(FUNC(alphasdana_state::lpxcd_r),FUNC(alphasdana_state::lpxcd_w));
    map(0xfffffa27,0xfffffa27).rw(FUNC(alphasdana_state::lckcon_r),FUNC(alphasdana_state::lckcon_w));
    map(0xfffffa28,0xfffffa29).rw(FUNC(alphasdana_state::lrra_r),FUNC(alphasdana_state::lrra_w));
    map(0xfffffa2d,0xfffffa2d).rw(FUNC(alphasdana_state::lposr_r),FUNC(alphasdana_state::lposr_w));
    map(0xfffffa33,0xfffffa33).rw(FUNC(alphasdana_state::lgpmr_r),FUNC(alphasdana_state::lgpmr_w));
    map(0xfffffa36,0xfffffa37).rw(FUNC(alphasdana_state::pwmr_r),FUNC(alphasdana_state::pwmr_w));

}

void alphasdana_state::alphasdana(machine_config &config)
{
    DANA_SD_IMAGE(config,m_sd[0]).set_slot(0);
    DANA_SD_IMAGE(config,m_sd[1]).set_slot(1);
    GENERIC_SOCKET(config,m_firmware,generic_plain_slot,"dana_flash","bin,rom");
    m_firmware->set_device_load(FUNC(alphasdana_state::firmware_load));
    m_firmware->set_device_unload(FUNC(alphasdana_state::firmware_unload));
    QUICKLOAD(config, m_guest, "dana,b", attotime::zero).set_load_callback(FUNC(alphasdana_state::guest_load));
    // Placeholder CPU frequency, not a calibrated VZ PLL.
    DANA_VZ_CPU(config, m_maincpu, 1'000'000);
    m_maincpu->set_addrmap(AS_PROGRAM, &alphasdana_state::program_map);
    m_maincpu->set_addrmap(m68000_base_device::AS_CPU_SPACE, &alphasdana_state::cpu_space_map);
    // Reuse MAME's LCD screen infrastructure; the only pixel source is guest RAM.
    SCREEN(config, m_screen).set_lcd();
    m_screen->set_refresh_hz(60); // Display cadence provisional; VZ PLL timing pending.
    m_screen->set_size(560,160);
    m_screen->set_visarea(0,559,0,159);
    m_screen->set_screen_update(FUNC(alphasdana_state::screen_update));
}

static INPUT_PORTS_START(alphasdana)
    PORT_START("EMUBRK")
    PORT_CONFNAME(0x01,0x01,"MC68VZ328 EMUBRK at RESET")
    PORT_CONFSETTING(0x01,"High - Normal Dana boot")
    PORT_CONFSETTING(0x00,"Low - Silicon UART bootstrap")
    PORT_START("SDWRITE")
    PORT_CONFNAME(0x01,0x00,"SD0 image writes")
    PORT_CONFSETTING(0x00,"Protected (default)")
    PORT_CONFSETTING(0x01,"Enabled explicitly")
    PORT_CONFNAME(0x02,0x00,"SD1 image writes")
    PORT_CONFSETTING(0x00,"Protected (default)")
    PORT_CONFSETTING(0x02,"Enabled explicitly")
    // The pinned port labels PD2/3 as SD IRQ, but does not prove that they
    // are insertion switches or give board polarity. Expose actual pin levels
    // for independent qualification; never fabricate an insertion interrupt.
    // User-selectable external PD7/IRQ6 level. The Dana board voltage is
    // not established from CPU documentation; default high models a released
    // active-low interrupt line, while low tests the original sleep path.
    // Original Dana 8 MiB; later Dana 2 and Wireless 16 MiB. The authentic
    // 68k memory probe decides what exists. Unpopulated addresses mirror RAM.
    PORT_START("PHYSRAM")
    PORT_CONFNAME(0x01,0x01,"Dana physical SDRAM (boot profile)")
    PORT_CONFSETTING(0x00,"8 MiB (original Dana)")
    PORT_CONFSETTING(0x01,"16 MiB (Dana 2 / Wireless)")
    PORT_START("PDPIN7")
    PORT_CONFNAME(0x80,0x80,"PD7/IRQ6 external level (startup board assumption)")
    PORT_CONFSETTING(0x80,"High / released (boot path)")
    PORT_CONFSETTING(0x00,"Low / asserted (sleep path)")
    PORT_START("SDIRQ")
    PORT_CONFNAME(0x04,0x04,"SD0 PD2 external pin level (board function unqualified)") PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::sd_irq_changed),0)
    PORT_CONFSETTING(0x04,"High / released")
    PORT_CONFSETTING(0x00,"Low")
    PORT_CONFNAME(0x08,0x08,"SD1 PD3 external pin level (board function unqualified)") PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::sd_irq_changed),0)
    PORT_CONFSETTING(0x08,"High / released")
    PORT_CONFSETTING(0x00,"Low")
    // Use one SDL lightgun-class pointing device for absolute X/Y AND its
    // trigger. The SDL lightgun provider already tracks the host mouse
    // position and left button in the MAME window. Never inject GEM mouse
    // events: EmuTOS reads PF1/PG2/SPI2 and calls mousevec itself.
    // Interactive Linux profile: -lightgun -lightgun_device lightgun
    // -lightgunprovider sdl -nomouse (avoid two competing input streams).
    PORT_START("PEN")
    PORT_BIT(0x01, IP_ACTIVE_HIGH, IPT_BUTTON1) PORT_NAME("Dana Stylus Contact") PORT_CODE(GUNCODE_BUTTON1) PORT_PLAYER(1)
    PORT_BIT(0xfe, IP_ACTIVE_HIGH, IPT_UNUSED)
    PORT_START("PENX")
    PORT_BIT(0xffff, 0x8000, IPT_LIGHTGUN_X) PORT_MINMAX(0,0xffff) PORT_SENSITIVITY(50) PORT_KEYDELTA(256) PORT_PLAYER(1)
    PORT_START("PENY")
    PORT_BIT(0xffff, 0x8000, IPT_LIGHTGUN_Y) PORT_MINMAX(0,0xffff) PORT_SENSITIVITY(50) PORT_KEYDELTA(256) PORT_PLAYER(1)

    // Small, independently visible ST scan-code subset; no key matrix spoof.
    PORT_START("KEYS")
    PORT_BIT(0x01,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("A") PORT_CODE(KEYCODE_A) PORT_CHAR('a') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),43)
    PORT_BIT(0x02,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("B") PORT_CODE(KEYCODE_B) PORT_CHAR('b') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),122)
    PORT_BIT(0x04,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Return") PORT_CODE(KEYCODE_ENTER) PORT_CHAR(13) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),46)
    PORT_BIT(0x08,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Space") PORT_CODE(KEYCODE_SPACE) PORT_CHAR(' ') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),126)
    PORT_BIT(0x10,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Left Alt") PORT_CODE(KEYCODE_LALT) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),70)
    PORT_BIT(0x20,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("C") PORT_CODE(KEYCODE_C) PORT_CHAR('c') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),109)
    PORT_BIT(0xc0,IP_ACTIVE_HIGH,IPT_UNUSED)

    // Extended physical Dana scan code inputs (no guest OS translation).
    PORT_START("EXKEY0")
    PORT_BIT(0x00000010,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("[") PORT_CODE(KEYCODE_OPENBRACE) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),4)
    PORT_BIT(0x00000020,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("F7") PORT_CODE(KEYCODE_F7) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),5)
    PORT_BIT(0x00000080,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("]") PORT_CODE(KEYCODE_CLOSEBRACE) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),7)
    PORT_BIT(0x00000100,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Y") PORT_CODE(KEYCODE_Y) PORT_CHAR('y') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),8)
    PORT_BIT(0x00000200,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Left shift") PORT_CODE(KEYCODE_LSHIFT) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),9)
    PORT_BIT(0x00000400,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("T") PORT_CODE(KEYCODE_T) PORT_CHAR('t') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),10)
    PORT_BIT(0x00000800,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Tab") PORT_CODE(KEYCODE_TAB) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),11)
    PORT_BIT(0x00001000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Caps lock (control)") PORT_CODE(KEYCODE_CAPSLOCK) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),12)
    PORT_BIT(0x00002000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("F3") PORT_CODE(KEYCODE_F3) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),13)
    PORT_BIT(0x00004000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Backspace") PORT_CODE(KEYCODE_BACKSPACE) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),14)
    PORT_BIT(0x00008000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("On/off (escape)") PORT_CODE(KEYCODE_PAUSE) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),15)
    PORT_BIT(0x00040000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Down") PORT_CODE(KEYCODE_DOWN) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),18)
    PORT_BIT(0x00080000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Command") PORT_CODE(KEYCODE_LWIN) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),19)
    PORT_BIT(0x00100000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("'") PORT_CODE(KEYCODE_QUOTE) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),20)
    PORT_BIT(0x00800000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("F6") PORT_CODE(KEYCODE_F6) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),23)
    PORT_BIT(0x01000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("H") PORT_CODE(KEYCODE_H) PORT_CHAR('h') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),24)
    PORT_BIT(0x04000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("G") PORT_CODE(KEYCODE_G) PORT_CHAR('g') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),26)
    PORT_BIT(0x20000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("F4") PORT_CODE(KEYCODE_F4) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),29)
    PORT_BIT(0x40000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("F5") PORT_CODE(KEYCODE_F5) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),30)
    PORT_BIT(0x9a63004f,IP_ACTIVE_HIGH,IPT_UNUSED)

    PORT_START("EXKEY1")
    PORT_BIT(0x00000010,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME(";") PORT_CODE(KEYCODE_COLON) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),36)
    PORT_BIT(0x00000020,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("L") PORT_CODE(KEYCODE_L) PORT_CHAR('l') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),37)
    PORT_BIT(0x00000080,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("K") PORT_CODE(KEYCODE_K) PORT_CHAR('k') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),39)
    PORT_BIT(0x00000100,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("J") PORT_CODE(KEYCODE_J) PORT_CHAR('j') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),40)
    PORT_BIT(0x00000200,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("\\") PORT_CODE(KEYCODE_BACKSLASH) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),41)
    PORT_BIT(0x00000400,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("F") PORT_CODE(KEYCODE_F) PORT_CHAR('f') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),42)
    PORT_BIT(0x00001000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("S") PORT_CODE(KEYCODE_S) PORT_CHAR('s') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),44)
    PORT_BIT(0x00002000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("D") PORT_CODE(KEYCODE_D) PORT_CHAR('d') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),45)
    PORT_BIT(0x00080000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Search") PORT_CODE(KEYCODE_F11) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),51)
    PORT_BIT(0x00100000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("P") PORT_CODE(KEYCODE_P) PORT_CHAR('p') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),52)
    PORT_BIT(0x00200000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("O") PORT_CODE(KEYCODE_O) PORT_CHAR('o') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),53)
    PORT_BIT(0x00800000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("I") PORT_CODE(KEYCODE_I) PORT_CHAR('i') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),55)
    PORT_BIT(0x01000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("U") PORT_CODE(KEYCODE_U) PORT_CHAR('u') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),56)
    PORT_BIT(0x04000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("R") PORT_CODE(KEYCODE_R) PORT_CHAR('r') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),58)
    PORT_BIT(0x08000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Q") PORT_CODE(KEYCODE_Q) PORT_CHAR('q') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),59)
    PORT_BIT(0x10000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("W") PORT_CODE(KEYCODE_W) PORT_CHAR('w') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),60)
    PORT_BIT(0x20000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("E") PORT_CODE(KEYCODE_E) PORT_CHAR('e') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),61)
    PORT_BIT(0xc247c84f,IP_ACTIVE_HIGH,IPT_UNUSED)

    PORT_START("EXKEY2")
    PORT_BIT(0x00000001,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Beam (Help)") PORT_CODE(KEYCODE_PGDN) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),64)
    PORT_BIT(0x00000002,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Home") PORT_CODE(KEYCODE_HOME) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),65)
    PORT_BIT(0x00000010,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("-") PORT_CODE(KEYCODE_MINUS) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),68)
    PORT_BIT(0x00000020,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("F8") PORT_CODE(KEYCODE_F8) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),69)
    PORT_BIT(0x00000080,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("=") PORT_CODE(KEYCODE_EQUALS) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),71)
    PORT_BIT(0x00000100,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("6") PORT_CODE(KEYCODE_6) PORT_CHAR('6') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),72)
    PORT_BIT(0x00000400,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("5") PORT_CODE(KEYCODE_5) PORT_CHAR('5') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),74)
    PORT_BIT(0x00000800,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("`") PORT_CODE(KEYCODE_TILDE) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),75)
    PORT_BIT(0x00001000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("F1") PORT_CODE(KEYCODE_F1) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),76)
    PORT_BIT(0x00002000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("F2") PORT_CODE(KEYCODE_F2) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),77)
    PORT_BIT(0x00004000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Calendar (F9)") PORT_CODE(KEYCODE_F9) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),78)
    PORT_BIT(0x00080000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Memo pad (F12)") PORT_CODE(KEYCODE_F12) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),83)
    PORT_BIT(0x00100000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("0") PORT_CODE(KEYCODE_0) PORT_CHAR('0') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),84)
    PORT_BIT(0x00200000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("9") PORT_CODE(KEYCODE_9) PORT_CHAR('9') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),85)
    PORT_BIT(0x00800000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("8") PORT_CODE(KEYCODE_8) PORT_CHAR('8') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),87)
    PORT_BIT(0x01000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("7") PORT_CODE(KEYCODE_7) PORT_CHAR('7') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),88)
    PORT_BIT(0x04000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("4") PORT_CODE(KEYCODE_4) PORT_CHAR('4') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),90)
    PORT_BIT(0x08000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("1") PORT_CODE(KEYCODE_1) PORT_CHAR('1') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),91)
    PORT_BIT(0x10000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("2") PORT_CODE(KEYCODE_2) PORT_CHAR('2') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),92)
    PORT_BIT(0x20000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("3") PORT_CODE(KEYCODE_3) PORT_CHAR('3') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),93)
    PORT_BIT(0x40000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Addressbook (F10)") PORT_CODE(KEYCODE_F10) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),94)
    PORT_BIT(0x8247824c,IP_ACTIVE_HIGH,IPT_UNUSED)

    PORT_START("EXKEY3")
    PORT_BIT(0x00000001,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("To-do list (Insert)") PORT_CODE(KEYCODE_INSERT) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),96)
    PORT_BIT(0x00000004,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Menu (Undo)") PORT_CODE(KEYCODE_MENU) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),98)
    PORT_BIT(0x00000020,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME(".") PORT_CODE(KEYCODE_STOP) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),101)
    PORT_BIT(0x00000040,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Delete") PORT_CODE(KEYCODE_DEL) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),102)
    PORT_BIT(0x00000080,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME(",") PORT_CODE(KEYCODE_COMMA) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),103)
    PORT_BIT(0x00000100,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("M") PORT_CODE(KEYCODE_M) PORT_CHAR('m') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),104)
    PORT_BIT(0x00000200,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Right shift") PORT_CODE(KEYCODE_RSHIFT) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),105)
    PORT_BIT(0x00000400,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("V") PORT_CODE(KEYCODE_V) PORT_CHAR('v') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),106)
    PORT_BIT(0x00000800,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Z") PORT_CODE(KEYCODE_Z) PORT_CHAR('z') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),107)
    PORT_BIT(0x00001000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("X") PORT_CODE(KEYCODE_X) PORT_CHAR('x') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),108)
    PORT_BIT(0x00004000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("#") PORT_CODE(KEYCODE_BACKSLASH2) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),110)
    PORT_BIT(0x00010000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Up") PORT_CODE(KEYCODE_UP) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),112)
    PORT_BIT(0x00020000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Right") PORT_CODE(KEYCODE_RIGHT) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),113)
    PORT_BIT(0x00040000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Left") PORT_CODE(KEYCODE_LEFT) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),114)
    PORT_BIT(0x00080000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Esc") PORT_CODE(KEYCODE_ESC) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),115)
    PORT_BIT(0x00100000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("/") PORT_CODE(KEYCODE_SLASH) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),116)
    PORT_BIT(0x01000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("N") PORT_CODE(KEYCODE_N) PORT_CHAR('n') PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),120)
    PORT_BIT(0x08000000,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Left ctrl (caps lock)") PORT_CODE(KEYCODE_LCONTROL) PORT_CHANGED_MEMBER(DEVICE_SELF,FUNC(alphasdana_state::st_key_changed),123)
    PORT_BIT(0xf6e0a01a,IP_ACTIVE_HIGH,IPT_UNUSED)
INPUT_PORTS_END

ROM_START(asmdana)
ROM_END

} // anonymous namespace

COMP(2002, asmdana, 0, 0, alphasdana, alphasdana, alphasdana_state, empty_init,
    "AlphaSmart, Inc.", "AlphaSmart Dana (D1.1 skeleton)", MACHINE_NOT_WORKING | MACHINE_NO_SOUND)
