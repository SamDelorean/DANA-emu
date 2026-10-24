// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors

#include "emu.h"
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
        , m_pen_contact(*this, "PEN")
        , m_pen_x(*this, "PENX")
        , m_pen_y(*this, "PENY")
        , m_firmware(*this, "firmware")
        , m_boot_memory(*this, "boot_memory")
        , m_sd(*this, "sd%u", 0U)
        , m_sd_irq(*this, "SDIRQ")
    {
    }

    void alphasdana(machine_config &config);
    DECLARE_INPUT_CHANGED_MEMBER(sd_irq_changed);

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
    void boot_postload();
    void physical_block(const char *reason, u32 address, u16 data=0);
    u16 physical_r(offs_t offset);
    u16 physical_mmio_r(offs_t offset, u16 mem_mask);
    void physical_mmio_w(offs_t offset, u16 data, u16 mem_mask);
    void physical_w(offs_t offset, u16 data, u16 mem_mask);
    u32 cs_base(unsigned group) const { return u32(m_cs_base[group] & 0xfffe) << 13; }
    u32 cs_size(unsigned group) const { return (group<2 ? 0x20000U : 0x8000U) << ((m_cs_select[group] >> 1) & 7); }
    bool cs_hit(unsigned group, u32 address) const
    { return (m_cs_select[group] & 1) && !(cs_base(group) & (cs_size(group)-1)) && address>=cs_base(group) && u64(address)<u64(cs_base(group))+cs_size(group); }
    bool physical_ram_ready() const
    { return !(m_cs_select[3] & 0x0200) || ((m_dram[1] | m_dram[2]) & 0x8000); }
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
    void dram_w(offs_t offset, u16 data, u16 mem_mask) { COMBINE_DATA(&m_dram[offset]); }
    static bool firmware_vectors_valid(const u8 *rom)
    {
        u32 const pc=(u32(rom[4])<<24) | (u32(rom[5])<<16) | (u32(rom[6])<<8) | rom[7];
        return pc && !(pc & 1) && pc<0xfffff000;
    }
    static bool firmware_size_valid(u32 size) { return size>=0x20000 && size<=0x1000000 && !(size & (size-1)); }
    void program_map(address_map &map) ATTR_COLD;
    void cpu_space_map(address_map &map) ATTR_COLD;
    void update_irq_lines();
    u8 irq_vector_r(offs_t offset);
    TIMER_CALLBACK_MEMBER(timer1_compare);
    u32 guest_system_clock_hz() const;
    u32 timer1_source_hz() const;
    void timer1_schedule();
    u16 timer1_tctl_r() { return m_tctl1; }
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
    // VZ PLLFSR, 0xFFFFF202: CLK32 is a virtual-time signal, not stored data.
    u16 pllfsr_r() { return (m_pllfsr & 0x4fff) | (m_clk32_high ? 0x8000 : 0); }
    void pllfsr_w(offs_t, u16 data, u16 mem_mask);
    TIMER_CALLBACK_MEMBER(clk32_tick);
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
    void portc_reset() { m_pcpden = 0; m_pcsel = 0; }
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
#undef DANA_LCD_BYTE
#define DANA_LCD_WORD(NAME) \
    u16 NAME##_r() { return m_##NAME; } \
    void NAME##_w(offs_t, u16 data, u16 mem_mask) { COMBINE_DATA(&m_##NAME); }
    DANA_LCD_WORD(lxmax)
    DANA_LCD_WORD(lymax)
    DANA_LCD_WORD(lrra)
    DANA_LCD_WORD(pwmr)
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
    required_ioport m_pen_contact;
    required_ioport m_pen_x;
    required_ioport m_pen_y;
    required_device<generic_socket_device> m_firmware;
    memory_view m_boot_memory;
    required_device_array<dana_sd_image_device,2> m_sd;
    required_ioport m_sd_irq;
    dana_sd::controller m_spi1;
    emu_timer *m_spi1_timer=nullptr;
    u16 m_spi1_word=0,m_spi1_control=0,m_spi1_received=0,m_ilcr=0x6533;
    u8 m_spi1_bits_left=0;
    u8 m_pd_extra[4]={},m_sd_last_pins=0x0c,m_sd_edges=0;
    bool m_spi1_busy=false;
    bool m_physical_boot=false, m_physical_blocked=false;
    u8 m_scr=0x1c, m_flash_sha1[20]={};
    u16 m_cs_base[4]={}, m_cs_select[4]={};
    u16 m_cs_upper=0, m_cs_control[3]={}, m_emucs=0;
    u16 m_dram[4]={};
    emu_timer *m_clk32_timer = nullptr;
    emu_timer *m_timer1_timer = nullptr;
    u16 m_tctl1=0, m_tprer1=0, m_tcmp1=0xffff;
    u16 m_tcr1=0, m_tcn1=0, m_tstat1=0, m_tstat_clear1=0;
    u32 m_timer1_compares=0, m_timer1_iacks=0;
    u16 m_ustcnt1=0, m_ubaud1=0x0002, m_urx1=0, m_utx1=0, m_umisc1=0;
    u16 m_uart_prescaler1=0;
    u16 m_pllfsr = 0x0347;
    bool m_clk32_high = false;
    u8 m_ivr = 0;
    bool m_guest_loaded = false;
    u16 m_icr = 0;
    u32 m_imr = 0x00ffffff;
    u32 m_pending = 0;
    u8 m_pcpden = 0;
    u8 m_pcsel = 0;
    u8 m_pfsel = 0xc5;
    u8 m_gpio[32] = {};
    u16 m_spi2_data = 0, m_spi2_ctrl = 0;
    // The pen ADC reply is staged within one PG2 selection.
    u8 m_pen_command = 0;
    u16 m_pen_sample = 0;
    bool m_st_ready = false, m_st_hello = false, m_st_reset_held = false;
    u8 m_st_old_keys = 0, m_st_pending_keys = 0, m_st_queue_left = 0;
    u32 m_lssa = 0;
    u8 m_lvpw = 0xff;
    u16 m_lxmax = 0x03f0;
    u16 m_lymax = 0x01ff;
    u8 m_lpicf = 0, m_lpolcf = 0, m_lacdrc = 0, m_lpxcd = 0;
    u8 m_lckcon = 0, m_lposr = 0, m_lgpmr = 0x84;
    u16 m_lrra = 0x00ff, m_pwmr = 0;
};

void alphasdana_state::machine_start()
{
    m_clk32_timer = timer_alloc(FUNC(alphasdana_state::clk32_tick), this);
    m_timer1_timer = timer_alloc(FUNC(alphasdana_state::timer1_compare), this);
    save_item(NAME(m_pllfsr));
    save_item(NAME(m_clk32_high));
    save_item(NAME(m_ivr));
    save_item(NAME(m_guest_loaded));
    save_item(NAME(m_icr));
    save_item(NAME(m_imr));
    save_item(NAME(m_pending));
    save_item(NAME(m_tctl1)); save_item(NAME(m_tprer1));
    save_item(NAME(m_tcmp1)); save_item(NAME(m_tcr1));
    save_item(NAME(m_tcn1)); save_item(NAME(m_tstat1));
    save_item(NAME(m_tstat_clear1));
    save_item(NAME(m_timer1_compares));
    save_item(NAME(m_timer1_iacks));
    save_item(NAME(m_ustcnt1)); save_item(NAME(m_ubaud1));
    save_item(NAME(m_urx1)); save_item(NAME(m_utx1));
    save_item(NAME(m_umisc1)); save_item(NAME(m_uart_prescaler1));
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
    save_item(NAME(m_lssa));
    save_item(NAME(m_lvpw));
    save_item(NAME(m_lxmax));
    save_item(NAME(m_lymax));
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
    save_item(NAME(m_scr)); save_item(NAME(m_flash_sha1));
    save_item(NAME(m_cs_base)); save_item(NAME(m_cs_select));
    save_item(NAME(m_cs_upper)); save_item(NAME(m_cs_control));
    save_item(NAME(m_emucs)); save_item(NAME(m_dram));
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
    // Existing peripheral implementation is shared by both boot profiles.
    // Motorola MC68VZ328UM 4.4.2: actual VZ reset, not MAME EZ/POSE 0x0123.
    m_pllfsr = 0x0347;
    m_clk32_high = false;
    // As in the pinned MAME DragonBall reference, advance CLK32 via
    // scheduler time rather than toggling it on register reads.
    m_clk32_timer->adjust(attotime::from_hz(32768), 0, attotime::from_hz(32768));
    m_ivr = 0x00;
    m_icr = 0;
    m_imr = 0x00ffffff;
    m_pending = 0;
    m_tctl1=0; m_tprer1=0; m_tcmp1=0xffff;
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
    m_physical_boot=m_firmware->exists();
    if (m_physical_boot && m_guest->exists())
        fatalerror("Select either raw firmware (-rom) or DANARAM1 (-quickload), never both");
    m_boot_memory.select(m_physical_boot ? 1 : 0);
    if (m_physical_boot)
    {
        physical_reset();
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
    if (m_guest->exists())
        return std::make_pair(image_error::INVALIDIMAGE,std::string("Firmware and DANARAM1 are mutually exclusive"));
    if (!image.loaded_through_softlist() && image.length()>0x1000000)
        return std::make_pair(image_error::INVALIDLENGTH,std::string("Firmware exceeds VZ CSA maximum decode"));
    u32 const size=m_firmware->common_get_size("rom");
    if (!firmware_size_valid(size))
        return std::make_pair(image_error::INVALIDLENGTH,std::string("Supply a complete power-of-two raw Flash array (128 KiB to 16 MiB), not an updater/PRC"));
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
    m_maincpu->set_unscaled_clock(guest_system_clock_hz());
    m_maincpu->resume(SUSPEND_REASON_DISABLE);
    logerror("DANA_PHYSICAL_RESET vectors=firmware CSA=%04x CSCTRL2=%04x CSCTRL3=%04x\n",
        m_cs_select[0],m_cs_control[1],m_cs_control[2]);
}

void alphasdana_state::boot_postload()
{
    if (m_physical_boot!=m_firmware->exists() || (m_physical_boot && m_guest->exists()))
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
        logerror("DANA_PHYSICAL_BLOCKED reason=%s address=%08x data=%04x pc=%08x\n",
            reason,address,data,u32(m_maincpu->pc()));
    m_physical_blocked=true;
    m_maincpu->suspend(SUSPEND_REASON_DISABLE,true);
}

u16 alphasdana_state::physical_r(offs_t offset)
{
    u32 const address=u32(offset)<<1;
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
        u32 const index=(boot ? address : address-cs_base(0)) & (size-1);
        u8 const *rom=m_firmware->get_rom_base();
        return (u16(rom[index])<<8) | rom[index+1];
    }
    if (ram && !flash && !(m_cs_select[3] & 0x6000))
    {
        if (!physical_ram_ready() || ((m_dram[2] & 0x8000) && (m_dram[2] & 0x0c00)))
        {
            physical_block("DRAM_DISABLED_OR_INIT_READ",address);
            return 0xffff;
        }
        u32 const index=address-cs_base(3);
        if (index<0x400000) return m_ram[index>>1];
    }
    physical_block(flash && ram ? "OVERLAPPING_CS" : "EXTERNAL_DECODE_OR_PROTECTION",address);
    return 0xffff; // Terminal unsupported access, never counted as a valid device response.
}

void alphasdana_state::physical_w(offs_t offset, u16 data, u16 mem_mask)
{
    u32 const address=u32(offset)<<1;
    bool const boot=!(m_cs_select[0] & 1);
    if (!boot && cs_hit(3,address) && !cs_hit(0,address) && !(m_cs_select[3] & 0xe000))
    {
        if (!physical_ram_ready()) { physical_block("DRAM_DISABLED",address,data); return; }
        // SDRAM precharge/mode-register writes are controller commands, not
        // guest data stores (M68VZ328Hwr.h INITPRECHG/INITMODE bits).
        if ((m_dram[2] & 0x8000) && (m_dram[2] & 0x0c00)) return;
        u32 const index=address-cs_base(3);
        if (index<0x400000)
        {
            COMBINE_DATA(&m_ram[index>>1]);
            return;
        }
    }
    // Exact NOR part/command set is not established. Do not fabricate an ID,
    // completed erase/program, or persistent write to the original dump.
    physical_block(boot || cs_hit(0,address) ? "FLASH_COMMAND_SET_UNVERIFIED" : "EXTERNAL_WRITE_OR_PROTECTION",address,data);
}

u16 alphasdana_state::physical_mmio_r(offs_t offset, u16 mem_mask)
{
    if (machine().side_effects_disabled()) return 0xffff;
    logerror("DANA_PHYSICAL_UNIMPLEMENTED_MMIO read address=%08x mask=%04x\n",0xfffff000+(u32(offset)<<1),mem_mask);
    physical_block("MMIO_READ_UNIMPLEMENTED",0xfffff000+(u32(offset)<<1));
    return 0xffff;
}

void alphasdana_state::physical_mmio_w(offs_t offset, u16 data, u16 mem_mask)
{
    if (machine().side_effects_disabled()) return;
    logerror("DANA_PHYSICAL_UNIMPLEMENTED_MMIO write address=%08x mask=%04x\n",0xfffff000+(u32(offset)<<1),mem_mask);
    physical_block("MMIO_WRITE_UNIMPLEMENTED",0xfffff000+(u32(offset)<<1),data);
}

void alphasdana_state::scr_w(u8 data)
{
    // DMAP=1 is the existing high internal-register decoder. Do not invent a
    // second low-register page when a firmware requests an unsupported mode.
    m_scr=(m_scr & 0xe0 & ~data) | (data & 0x1f);
    if (!(m_scr & 4)) physical_block("SCR_DMAP_MODE",0xfffff000,data);
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
        COMBINE_DATA(&m_cs_control[offset-5]);
        u16 const reset=offset==5 ? 0 : 0x1000;
        if (m_cs_control[offset-5]!=reset) physical_block("CS_CONTROL_MODE",0xfffff100+offset*2,data);
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
    m_st_old_keys=0; m_st_pending_keys=0; m_st_queue_left=0;
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
    // ST selection is active-low PE3; pen ADC and other SPI slaves are not
    // claimed as implemented. A deselected ST returns an idle data level.
    if (!m_st_ready || (m_gpio[2*4+1] & 0x08))
        return 0xff;
    if (m_st_hello)
    {
        m_st_hello=false;
        return 0xaa;
    }
    // Version/query commands are not fabricated. No queued host event while
    // not polling means zero data, exactly as the guest tests.
    if (command)
        return 0;
    if (m_st_queue_left)
    {
        u8 const bits=m_st_pending_keys;
        --m_st_queue_left;
        // Six real ST scan-code keys: A, B, Return, Space, Left Alt, C. In real Dana protocol
        // these are ST scan bytes, not Atari/Amiga key codes.
        static constexpr u8 st_scan[6]={0x2b,0x7a,0x2e,0x7e,0x46,0x6d};
        for(unsigned i=0;i<6;++i)
            if (bits & (1<<i)) { m_st_pending_keys &= ~(1<<i); return st_scan[i]; }
        return 0;
    }
    u8 const keys=m_keys->read() & 0x3f;
    if (keys!=m_st_old_keys)
    {
        m_st_old_keys=keys;
        m_st_pending_keys=keys;
        unsigned count=0;
        for(unsigned i=0;i<6;++i) count+=BIT(keys,i);
        m_st_queue_left=count;
        return u8(0x40 | count);
    }
    return 0;
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
    { u8 const inputs=~m_gpio[4] & 0x0c; result=(result & ~inputs)|(m_sd_irq->read() & inputs); }
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
    if (m_guest_loaded)
        m_maincpu->set_unscaled_clock(guest_system_clock_hz());
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
    m_maincpu->set_input_line(4,((active & 0x00000c04) || (spi_level==4 && (active & 0x00200000))) ? ASSERT_LINE : CLEAR_LINE);
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
    // The exact original EmuTOS-Dana clock formula applied to PLLFSR.
    return (u32(m_pllfsr & 0xff)*14
        + u32((m_pllfsr >> 8) & 0x3f)+15)*32768;
}
u32 alphasdana_state::timer1_source_hz() const
{
    // CPU and SYSCLK-sourced Timer1 must advance in the SAME guest time.
    u32 const guest_hz=guest_system_clock_hz();
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
    m_boot_memory[1](0xfffff000,0xffffffff).rw(FUNC(alphasdana_state::physical_mmio_r),FUNC(alphasdana_state::physical_mmio_w));
    // Additional system/chip-select/DRAM registers exist only in physical mode.
    m_boot_memory[1](0xfffff000,0xfffff000).rw(FUNC(alphasdana_state::scr_r),FUNC(alphasdana_state::scr_w));
    // Fixed VZ part ID from pinned M68VZ328Hwr/EmRegsVZ; mask revision is not guessed.
    m_boot_memory[1](0xfffff004,0xfffff004).lr8(NAME([]() { return u8(0x56); }));
    m_boot_memory[1](0xfffff100,0xfffff10d).rw(FUNC(alphasdana_state::cs_r),FUNC(alphasdana_state::cs_w));
    m_boot_memory[1](0xfffff110,0xfffff117).rw(FUNC(alphasdana_state::cs_select_r),FUNC(alphasdana_state::cs_select_w));
    m_boot_memory[1](0xfffff118,0xfffff119).rw(FUNC(alphasdana_state::emucs_r),FUNC(alphasdana_state::emucs_w));
    m_boot_memory[1](0xfffff150,0xfffff151).rw(FUNC(alphasdana_state::cs_control3_r),FUNC(alphasdana_state::cs_control3_w));
    m_boot_memory[1](0xfffffc00,0xfffffc07).rw(FUNC(alphasdana_state::dram_r),FUNC(alphasdana_state::dram_w));

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
    // including a word spanning both registers. No PCDIR/PCDATA, external
    // input values or LCD responses are synthesized by these latches.
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
    QUICKLOAD(config, m_guest, "dana", attotime::zero).set_load_callback(FUNC(alphasdana_state::guest_load));
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
    PORT_BIT(0x01,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("A") PORT_CODE(KEYCODE_A) PORT_CHAR('a')
    PORT_BIT(0x02,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("B") PORT_CODE(KEYCODE_B) PORT_CHAR('b')
    PORT_BIT(0x04,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Return") PORT_CODE(KEYCODE_ENTER) PORT_CHAR(13)
    PORT_BIT(0x08,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Space") PORT_CODE(KEYCODE_SPACE) PORT_CHAR(' ')
    PORT_BIT(0x10,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("Left Alt") PORT_CODE(KEYCODE_LALT)
    PORT_BIT(0x20,IP_ACTIVE_HIGH,IPT_KEYBOARD) PORT_NAME("C") PORT_CODE(KEYCODE_C) PORT_CHAR('c')
    PORT_BIT(0xc0,IP_ACTIVE_HIGH,IPT_UNUSED)
INPUT_PORTS_END

ROM_START(asmdana)
ROM_END

} // anonymous namespace

COMP(2002, asmdana, 0, 0, alphasdana, alphasdana, alphasdana_state, empty_init,
    "AlphaSmart, Inc.", "AlphaSmart Dana (D1.1 skeleton)", MACHINE_NOT_WORKING | MACHINE_NO_SOUND)
