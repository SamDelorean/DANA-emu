// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
// MC68VZ328UM 15.5: independent 16-bit PWM2 (no FIFO); PCR 5.2.2
// This is a digital VZ pin model, not an assertion about Dana analog wiring.

bool alphasdana_state::pwm2_pin_level() const
{
    return bool((m_pwm2_control & 0x0010) && m_pwm2_high) ^ bool(m_pwm2_control & 0x0020);
}

void alphasdana_state::pwm_output_update()
{
    bool const a=m_pwm1_high;
    bool const b=pwm2_pin_level();
    bool pin=false;
    switch ((m_pcr >> 2) & 3)
    {
    case 0: pin=a; break; // PWM1 only, original UK1.5 path
    case 1: pin=b; break; // PWM2 only
    case 2: pin=a || b; break;
    case 3: pin=a && b; break;
    }
    m_pwm1_speaker->level_w(pin ? 1 : 0);
    m_pwm2_pin=bool(b);
}

void alphasdana_state::pwm2_irq()
{
    m_pending=(m_pending & ~u32(0x00002000)) |
        ((m_pwm2_control & 0xc000)==0xc000 ? 0x00002000 : 0);
    update_irq_lines();
}

u16 alphasdana_state::pwm2_count_r()
{
    if ((m_pwm2_control & 0x0010) && m_pwm2_timer->enabled() && m_pwm2_source_hz)
    {
        // Period timer was last armed with m_pwm2_count as the base.
        u64 const steps=m_pwm2_timer->elapsed().as_ticks(m_pwm2_source_hz) /
            (4U << (m_pwm2_control & 7));
        return u16(std::min<u64>(u64(m_pwm2_count)+steps,0xffff));
    }
    return m_pwm2_count;
}

void alphasdana_state::pwm2_schedule()
{
    m_pwm2_timer->adjust(attotime::never);
    m_pwm2_fall_timer->adjust(attotime::never);
    m_pwm2_source_hz=h2_sysclk();
    if (!(m_pwm2_control & 0x0010) || !m_pwm2_period || !m_pwm2_source_hz)
    {
        m_pwm2_high=false;
        pwm_output_update();
        return;
    }
    const u32 step=4U << (m_pwm2_control & 7);
    const u32 remaining=m_pwm2_count<m_pwm2_period ? m_pwm2_period-m_pwm2_count : 1;
    m_pwm2_timer->adjust(attotime::from_ticks(u64(remaining)*step,m_pwm2_source_hz));
    m_pwm2_high=m_pwm2_width && (m_pwm2_width>m_pwm2_count);
    if(m_pwm2_high && m_pwm2_width < m_pwm2_period)
        m_pwm2_fall_timer->adjust(attotime::from_ticks(
            u64(m_pwm2_width-m_pwm2_count)*step,m_pwm2_source_hz));
    pwm_output_update();
}

void alphasdana_state::pwm2_clock_changed()
{
    if (!m_pwm2_timer) return;
    if (m_pwm2_timer->enabled())
    {
        // Use the OLD source frequency for progress before retiming to SYSCLK.
        m_pwm2_count=pwm2_count_r();
    }
    pwm2_schedule();
}

TIMER_CALLBACK_MEMBER(alphasdana_state::pwm2_period_event)
{
    if(!(m_pwm2_control & 0x0010))return;
    ++m_pwm2_rollovers;
    m_pwm2_control|=0x8000; // IRQ status, read-to-clear, independently maskable
    m_pwm2_count=0;
    pwm2_schedule();
    pwm2_irq();
}

TIMER_CALLBACK_MEMBER(alphasdana_state::pwm2_width_event)
{
    m_pwm2_high=false;
    pwm_output_update();
}

u16 alphasdana_state::pwm2_control_r()
{
    // Disabled PWMC2 has reset 0000; PIN sampling is active only when PWMEN.
    u16 const value=(m_pwm2_control & ~u16(0x0180)) |
        (((m_pwm2_control & 0x0010) && !pwm2_pin_level()) ? 0x0080 : 0);
    if (!machine().side_effects_disabled())
    {
        m_pwm2_control &= ~u16(0x8000);
        pwm2_irq();
    }
    return value;
}

void alphasdana_state::pwm2_control_w(offs_t,u16 data,u16 mem_mask)
{
    u16 const old=m_pwm2_control;
    u16 const merged=(old & ~mem_mask)|(data & mem_mask);
    u16 const current=pwm2_count_r();
    // Control bits: PWMIRQ IRQEN LOAD PIN POL PWMEN CLKSEL; PIN is read-only.
    m_pwm2_control=(merged & u16(0xc037)) | (old & u16(0x8000));
    if (data & mem_mask & 0x8000) m_pwm2_control |= 0x8000;
    if (!(old & 0x0010) && (m_pwm2_control & 0x0010))m_pwm2_count=0;
    else if (!(m_pwm2_control & 0x0010))m_pwm2_count=0;
    else m_pwm2_count=current;
    // LOAD is self-clearing and re-latches period/width on the same timer.
    pwm2_schedule();
    pwm2_irq();
}

void alphasdana_state::pwm2_period_w(offs_t,u16 data,u16 mem_mask)
{
    m_pwm2_count=pwm2_count_r();
    m_pwm2_period=(m_pwm2_period & ~mem_mask)|(data & mem_mask);
    pwm2_schedule();
}
void alphasdana_state::pwm2_width_w(offs_t,u16 data,u16 mem_mask)
{
    m_pwm2_count=pwm2_count_r();
    m_pwm2_width=(m_pwm2_width & ~mem_mask)|(data & mem_mask);
    pwm2_schedule();
}
void alphasdana_state::pwm2_count_w(offs_t,u16 data,u16 mem_mask)
{
    u16 const c=pwm2_count_r();
    m_pwm2_count=(c & ~mem_mask)|(data & mem_mask);
    pwm2_schedule();
}
