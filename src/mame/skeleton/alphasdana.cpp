// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors

#include "emu.h"
#include "cpu/m68000/m68000.h"
#include "imagedev/snapquik.h"
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
    {
    }

    void alphasdana(machine_config &config);

protected:
    virtual void machine_start() override ATTR_COLD;
    virtual void machine_reset() override ATTR_COLD;

private:
    void program_map(address_map &map) ATTR_COLD;
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

    DECLARE_QUICKLOAD_LOAD_MEMBER(guest_load);
    required_device<dana_vz_cpu_device> m_maincpu;
    required_device<quickload_image_device> m_guest;
    output_finder<> m_guest_ready;
    emu_timer *m_clk32_timer = nullptr;
    u16 m_pllfsr = 0x0347;
    bool m_clk32_high = false;
    u8 m_ivr = 0;
    bool m_guest_loaded = false;
    u16 m_icr = 0;
    u32 m_imr = 0x00ffffff;
    u32 m_pending = 0;
};

void alphasdana_state::machine_start()
{
    m_clk32_timer = timer_alloc(FUNC(alphasdana_state::clk32_tick), this);
    save_item(NAME(m_pllfsr));
    save_item(NAME(m_clk32_high));
    save_item(NAME(m_ivr));
    save_item(NAME(m_guest_loaded));
    save_item(NAME(m_icr));
    save_item(NAME(m_imr));
    save_item(NAME(m_pending));
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
    // Quickload is timer-driven. Suppress *all* CPU fetches until validation
    // and the complete RAM/bootstrap seed have succeeded. No-image tests keep
    // their independently qualified native reset path unchanged.
    if (m_guest->exists() && !m_guest_loaded)
        m_maincpu->suspend(SUSPEND_REASON_DISABLE, true);
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
    u16 const counter_mask = mem_mask & 0x0fff;
    if (!(m_pllfsr & 0x4000))
        m_pllfsr = (m_pllfsr & ~counter_mask) | (data & counter_mask);
    if (data & mem_mask & 0x4000)
        m_pllfsr |= 0x4000;
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


// VZ interrupt configuration/status prefix used by dana_init. Native MAME
// register/word-lane pattern (mc68328.cpp), VZ mask/layout from the UM interrupt-controller definitions and
// D0.2. No IRQ sources are implemented/asserted here: pending really is zero.
// PLLCR, PCTRL, Timer, GPIO and UART stay unmapped pending independent contracts.
 // PLLFSR alone is now implemented with VZ-specific reset/PROT/CLK32 semantics.
void alphasdana_state::imr_w(offs_t offset, u16 data, u16 mem_mask)
{
    unsigned const shift = offset ? 0 : 16;
    u32 const mask = u32(mem_mask) << shift;
    m_imr = ((m_imr & ~mask) | (u32(data & mem_mask) << shift)) & 0x00ffffff;
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
    m_guest_ready = 1;
    logerror("DANA_GUEST_LOAD entry=%08x stack=%08x bytes=%u sha1=%s profile=R-direct phystop=%08x\n",
        entry, stack, length, hash.as_string(), phystop);
    // Native reset sequencing fetches the seeded vectors; do not write PC.
    m_maincpu->reset();
    m_maincpu->resume(SUSPEND_REASON_DISABLE);
    return std::make_pair(std::error_condition(), std::string());
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
}

void alphasdana_state::alphasdana(machine_config &config)
{
    QUICKLOAD(config, m_guest, "dana", attotime::zero).set_load_callback(FUNC(alphasdana_state::guest_load));
    // Placeholder CPU frequency, not a calibrated VZ PLL.
    DANA_VZ_CPU(config, m_maincpu, 1'000'000);
    m_maincpu->set_addrmap(AS_PROGRAM, &alphasdana_state::program_map);
}

static INPUT_PORTS_START(alphasdana)
INPUT_PORTS_END

ROM_START(asmdana)
ROM_END

} // anonymous namespace

COMP(2002, asmdana, 0, 0, alphasdana, alphasdana, alphasdana_state, empty_init,
    "AlphaSmart, Inc.", "AlphaSmart Dana (D1.1 skeleton)", MACHINE_NOT_WORKING | MACHINE_NO_SOUND)
