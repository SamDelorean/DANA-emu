// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
// Existing VZ PWM1, MC68VZ328UM 15.4.1–15.4.4. No second audio controller.

void alphasdana_state::pwm1_save()
{
    save_item(NAME(m_pwm1_repeat_left));save_item(NAME(m_pwm1_high));
    save_item(NAME(m_pwm1_cycle_steps));save_item(NAME(m_pwm1_step_clocks));save_item(NAME(m_pwm1_source_hz));
    save_item(NAME(m_pwm1_cycles));save_item(NAME(m_pwm1_samples));
}

void alphasdana_state::pwm1_level(bool high)
{
    m_pwm1_high=high;m_pwm1_outputs[0]=high;
    // Retain the qualified mono MAME speaker path. Electrical filtering,
    // amplification and the physical PB7-to-speaker PCB net are unmeasured.
    pwm_output_update();
}

void alphasdana_state::pwm1_irq()
{
    m_pending=(m_pending&~u32(0x80))|((m_pwm1_control&0xc0)==0xc0?0x80:0);
    m_pwm1_outputs[3]=m_pwm1_count;update_irq_lines();
}

double alphasdana_state::pwm1_phase() const
{
    if(!(m_pwm1_control&0x10))return 0;
    double const clocks=m_pwm1_timer->enabled()
        ?m_pwm1_timer->remaining().as_double()*m_pwm1_source_hz:m_pwm_clock_remaining;
    if(clocks<0)return m_pwm1_counter;
    return std::clamp(double(m_pwm1_cycle_steps)-clocks/m_pwm1_step_clocks,0.0,255.999999);
}

void alphasdana_state::pwm1_clock_changed()
{
    if(!m_pwm1_timer)return;
    // Reuse H2's source-cycle preservation, including the independent crystal
    // source. Freeze the active level when SYSCLK stops; do not invent an edge.
    u32 const hz=(m_pwm1_control&0x8000)?m_xtal->read():h2_sysclk();
    h2_retime(m_pwm1_timer,m_pwm1_source_hz,hz,m_pwm_clock_remaining);
    h2_retime(m_pwm1_fall_timer,m_pwm1_source_hz,hz,m_pwm_fall_remaining);
    m_pwm1_source_hz=hz;
}

void alphasdana_state::pwm1_schedule(double phase)
{
    m_pwm1_timer->adjust(attotime::never);m_pwm1_fall_timer->adjust(attotime::never);
    if(!(m_pwm1_control&0x10))return;
    m_pwm1_source_hz=(m_pwm1_control&0x8000)?m_xtal->read():h2_sysclk();
    m_pwm1_step_clocks=(((m_pwm1_control>>8)&127)+1)*(2U<<(m_pwm1_control&3));
    unsigned const total=std::min(unsigned(m_pwm1_period),254U)+2;
    // A newly lowered compare already behind COUNT is encountered after the
    // eight-bit wrap, not by resetting the running counter on a CPU write.
    m_pwm1_cycle_steps=phase>=total?256:total;m_pwm1_counter=u8(phase);
    m_pwm_clock_remaining=(m_pwm1_cycle_steps-phase)*m_pwm1_step_clocks;
    m_pwm_fall_remaining=-1;
    if(m_pwm1_source_hz)
        m_pwm1_timer->adjust(attotime::from_double(m_pwm_clock_remaining/m_pwm1_source_hz));
    if(m_pwm1_high && m_pwm1_last_sample<m_pwm1_cycle_steps)
    {
        double const remaining=(m_pwm1_last_sample-phase)*m_pwm1_step_clocks;
        if(remaining<=0)pwm1_level(false);
        else
        {
            m_pwm_fall_remaining=remaining;
            if(m_pwm1_source_hz)m_pwm1_fall_timer->adjust(attotime::from_double(remaining/m_pwm1_source_hz));
        }
    }
}

void alphasdana_state::pwm1_begin_period()
{
    ++m_pwm1_cycles;m_pwm1_counter=0;
    if(m_pwm1_repeat_left)--m_pwm1_repeat_left;
    else
    {
        if(m_pwm1_count)
        {
            m_pwm1_last_sample=m_pwm1_fifo[m_pwm1_head];
            m_pwm1_head=(m_pwm1_head+1)%5;--m_pwm1_count;++m_pwm1_samples;
            m_pwm1_repeat_left=(1U<<((m_pwm1_control>>2)&3))-1;
        }
        // Empty FIFO free-runs at the last real sample. A later refill is
        // consumed at a period boundary, not immediately by the CPU write.
        if(m_pwm1_count<=1)m_pwm1_control|=0x80;
    }
    pwm1_level(m_pwm1_last_sample!=0);
    pwm1_schedule();pwm1_irq();
    m_pwm1_outputs[1]=m_pwm1_cycles;m_pwm1_outputs[2]=m_pwm1_samples;
    m_pwm1_outputs[4]=m_pwm1_last_sample;
}

TIMER_CALLBACK_MEMBER(alphasdana_state::pwm1_tick)
{
    if((m_pwm1_control&0x10) && m_pwm1_source_hz)pwm1_begin_period();
}

TIMER_CALLBACK_MEMBER(alphasdana_state::pwm1_fall)
{
    m_pwm_fall_remaining=-1;pwm1_level(false);
}

u16 alphasdana_state::pwm1_control_r()
{
    u16 const value=(m_pwm1_control&~u16(0x2c))|(m_pwm1_count<5?0x20:0);
    if(!machine().side_effects_disabled()) {m_pwm1_control&=~u16(0x80);pwm1_irq();}
    return value;
}

void alphasdana_state::pwm1_control_w(offs_t,u16 data,u16 mem_mask)
{
    double const phase=pwm1_phase();u16 const old=m_pwm1_control;
    u16 const next=(old&~mem_mask)|(data&mem_mask);
    m_pwm1_control=next&0xffdf; // IRQ is R/W; FIFOAV alone is hardware read-only.
    if(!(next&0x10))
    {
        m_pwm1_timer->adjust(attotime::never);m_pwm1_fall_timer->adjust(attotime::never);
        m_pwm_clock_remaining=m_pwm_fall_remaining=-1;
        m_pwm1_head=0;m_pwm1_count=0;m_pwm1_counter=0;m_pwm1_repeat_left=0;
        m_pwm1_last_sample=0;if(old&0x10)m_pwm1_control&=~u16(0x80);pwm1_level(false);
    }
    else if(!(old&0x10))
    {
        m_pwm1_head=0;m_pwm1_count=0;m_pwm1_repeat_left=0;m_pwm1_last_sample=0;
        m_pwm1_control|=0x80;pwm1_begin_period();
    }
    else if((old^next)&0xff03)pwm1_schedule(phase);
    // IRQEN/REPEAT/debug-status writes do not restart a period or truncate it.
    if(data&mem_mask&0x80)m_pwm1_control|=0x80;
    pwm1_irq();
}

void alphasdana_state::pwm1_sample_w(offs_t,u16 data,u16 mem_mask)
{
    if(!(m_pwm1_control&0x10) || m_pwm1_count==5 || !(mem_mask&0xff))return;
    auto push=[this](u8 value) {
        if(m_pwm1_count<5)m_pwm1_fifo[(m_pwm1_head+m_pwm1_count++)%5]=value;
    };
    // Packed word: high then low. A single byte must use SAMPLE1 (odd).
    if((mem_mask&0xffff)==0xffff)push(u8(data>>8));
    push(u8(data));m_pwm1_sample=(m_pwm1_sample&~mem_mask)|(data&mem_mask);
    if(m_pwm1_count>1)m_pwm1_control&=~u16(0x80);
    pwm1_irq();
}

u16 alphasdana_state::pwm1_period_count_r()
{
    return u16(m_pwm1_period)<<8|u8(pwm1_phase());
}

void alphasdana_state::pwm1_period_count_w(offs_t,u16 data,u16 mem_mask)
{
    if(!(m_pwm1_control&0x10) || !(mem_mask&0xff00))return;
    double const phase=pwm1_phase();m_pwm1_period=u8(data>>8);pwm1_schedule(phase);
}
