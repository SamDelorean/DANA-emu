// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors

#include "emu.h"
#include "cpu/m68000/m68000.h"
#include "imagedev/snapquik.h"
#include "screen.h"
#include "util/hashing.h"

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
    {
    }

    void alphasdana(machine_config &config);

protected:
    virtual void machine_start() override ATTR_COLD;
    virtual void machine_reset() override ATTR_COLD;

private:
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
    void pfsel_w(u8 data) { m_pfsel = data; }


    // Post-bootstrap GPIO output/configuration latches. The initial values
    // come from pinned dbztool/danainit.sh, NOT MC68VZ328 silicon reset.
    // External pen contact is modeled on PF1. Card detect is unconnected.
    // Port order B, D, E, F, G, J, K, M; DIR/DATA/PUEN/SEL columns.
    void gpio_bootstrap_reset();
#define DANA_GPIO_PORT(NAME, INDEX) \
    u8 NAME##_r(offs_t reg) { return m_gpio[(INDEX)*4 + reg]; } \
    void NAME##_w(offs_t reg, u8 value) { m_gpio[(INDEX)*4 + reg] = value; }
    // Port B and K observe the ST controller reset/ready handshake.
    u8 pb_r(offs_t reg) { return m_gpio[reg]; }
    void pb_w(offs_t reg, u8 value);
    DANA_GPIO_PORT(pd, 1)
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
    void pf_w(offs_t reg, u8 value) { m_gpio[3*4+reg]=value; }
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
    DANA_GPIO_PORT(pj, 5)
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
    m_guest_ready = 0;
}

void alphasdana_state::machine_reset()
{
    // Defined register reset only; full VZ cold-reset decoding is not modeled.
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
    // Quickload is timer-driven. Suppress *all* CPU fetches until validation
    // and the complete RAM/bootstrap seed have succeeded. No-image tests keep
    // their independently qualified native reset path unchanged.
    if (m_guest->exists() && !m_guest_loaded)
        m_maincpu->suspend(SUSPEND_REASON_DISABLE, true);
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
        // Four bounded host keys: A, B, Return, Space. In real Dana protocol
        // these are ST scan bytes, not Atari/Amiga key codes.
        static constexpr u8 st_scan[4]={0x2b,0x7a,0x2e,0x7e};
        for(unsigned i=0;i<4;++i)
            if (bits & (1<<i)) { m_st_pending_keys &= ~(1<<i); return st_scan[i]; }
        return 0;
    }
    u8 const keys=m_keys->read() & 0x0f;
    if (keys!=m_st_old_keys)
    {
        m_st_old_keys=keys;
        m_st_pending_keys=keys;
        unsigned count=0;
        for(unsigned i=0;i<4;++i) count+=BIT(keys,i);
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


// VZ interrupt group. Timer1 source bit1 -> IRQ6, UART1 bit2 -> IRQ4.
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
    // bit2 UART1 -> level4. UART1 RX is unconnected, so never assert it.
    u32 const active=m_pending & ~m_imr;
    m_maincpu->set_input_line(6,(active & 0x00000002) ? ASSERT_LINE : CLEAR_LINE);
    m_maincpu->set_input_line(4,(active & 0x00000004) ? ASSERT_LINE : CLEAR_LINE);
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
    map(0x00000000, 0x003fffff).ram().share("ram");

    // Individually decoded VZ registers only, never a blanket MMIO RAM page.
    // SCR.DMAP conditional low-address aliases remain intentionally unmapped.
    map(0xfffff202, 0xfffff203).rw(FUNC(alphasdana_state::pllfsr_r), FUNC(alphasdana_state::pllfsr_w));
    map(0xfffff300, 0xfffff300).rw(FUNC(alphasdana_state::ivr_r), FUNC(alphasdana_state::ivr_w));
    map(0xfffff302, 0xfffff303).rw(FUNC(alphasdana_state::icr_r), FUNC(alphasdana_state::icr_w));
    map(0xfffff304, 0xfffff307).rw(FUNC(alphasdana_state::imr_r), FUNC(alphasdana_state::imr_w));
    map(0xfffff30c, 0xfffff30f).rw(FUNC(alphasdana_state::isr_r), FUNC(alphasdana_state::isr_w));
    map(0xfffff310, 0xfffff313).r(FUNC(alphasdana_state::ipr_r));
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
    // latches; no external ST/SD/pen input or IRQ is fabricated. Preserve the
    // separately qualified Port C and PFSEL byte handlers.
    map(0xfffff408,0xfffff40b).rw(FUNC(alphasdana_state::pb_r),FUNC(alphasdana_state::pb_w));
    map(0xfffff418,0xfffff41b).rw(FUNC(alphasdana_state::pd_r),FUNC(alphasdana_state::pd_w));
    map(0xfffff420,0xfffff423).rw(FUNC(alphasdana_state::pe_r),FUNC(alphasdana_state::pe_w));
    map(0xfffff428,0xfffff42a).rw(FUNC(alphasdana_state::pf_r),FUNC(alphasdana_state::pf_w));
    map(0xfffff430,0xfffff433).rw(FUNC(alphasdana_state::pg_r),FUNC(alphasdana_state::pg_w));
    map(0xfffff438,0xfffff43b).rw(FUNC(alphasdana_state::pj_r),FUNC(alphasdana_state::pj_w));
    map(0xfffff440,0xfffff443).rw(FUNC(alphasdana_state::pk_r),FUNC(alphasdana_state::pk_w));
    map(0xfffff448,0xfffff44b).rw(FUNC(alphasdana_state::pm_r),FUNC(alphasdana_state::pm_w));

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
    PORT_BIT(0xf0,IP_ACTIVE_HIGH,IPT_UNUSED)
INPUT_PORTS_END

ROM_START(asmdana)
ROM_END

} // anonymous namespace

COMP(2002, asmdana, 0, 0, alphasdana, alphasdana, alphasdana_state, empty_init,
    "AlphaSmart, Inc.", "AlphaSmart Dana (D1.1 skeleton)", MACHINE_NOT_WORKING | MACHINE_NO_SOUND)
