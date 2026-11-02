// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
// Implementations for the existing alphasdana_state. No second MCU or clock.

u32 alphasdana_state::h2_pll_hz() const
{ return 2U*(14U*(u32(m_pllfsr&255)+1)+u32((m_pllfsr>>8)&15)+1)*m_xtal->read(); }
u32 alphasdana_state::h2_dma_hz() const
{ return h2_pll_hz()/((m_pllcr&0x80)?2:1)/((m_pllcr&0x20)?2:1); }
u32 alphasdana_state::physical_system_clock_hz() const
{ unsigned const n=(m_pllcr>>8)&7;return h2_dma_hz()/(n>=4?1:(2U<<n)); }
u32 alphasdana_state::guest_system_clock_hz() const
{ return physical_system_clock_hz(); }
u32 alphasdana_state::h2_sysclk() const
{ return m_pll_stopped ? 0 : physical_system_clock_hz(); }
u32 alphasdana_state::h2_lcd_hz() const
{ unsigned const n=(m_pllcr>>11)&7;return m_pll_stopped?0:h2_dma_hz()/(n>=4?1:(2U<<n)); }

void alphasdana_state::h2_clock_capture()
{
    if((m_tctl1&1) && ((m_tctl1&14)==2 || (m_tctl1&14)==4))m_tcn1=timer1_tcn_r();
    if((m_tctl2&1) && ((m_tctl2&14)==2 || (m_tctl2&14)==4))m_tcn2=timer2_tcn_r();
}
void alphasdana_state::h2_retime(emu_timer *timer,u32 old_hz,u32 new_hz,double &remaining)
{
    if(old_hz && timer->enabled())remaining=timer->remaining().as_double()*old_hz;
    if(timer->enabled() || (!old_hz && remaining>=0))
        timer->adjust(new_hz?attotime::from_double(remaining/new_hz):attotime::never);
    if(new_hz)remaining=-1;
}
void alphasdana_state::h2_clock_apply(u32 old_hz)
{
    u32 const hz=h2_sysclk();
    if(hz)m_maincpu->set_unscaled_clock(hz);
    // PLL changes must not restart an independent CLK32 compare interval.
    if((m_tctl1&14)==2 || (m_tctl1&14)==4)timer1_schedule();
    if((m_tctl2&14)==2 || (m_tctl2&14)==4)timer2_schedule();
    h2_retime(m_spi1_timer,old_hz,hz,m_spi_clock_remaining);
    if(!(m_pwm1_control&0x8000))
    {
        h2_retime(m_pwm1_timer,old_hz,hz,m_pwm_clock_remaining);
        h2_retime(m_pwm1_fall_timer,old_hz,hz,m_pwm_fall_remaining);
    }
    serial_clock();h2_cpu_gate();
}
void alphasdana_state::h2_cpu_gate()
{
    bool const off=m_pll_stopped || ((m_pctlr&0x80) && (!(m_pctlr&31) || !m_pcm_on));
    if(off)m_maincpu->suspend(SUSPEND_REASON_HALT,true);
    else m_maincpu->resume(SUSPEND_REASON_HALT);
}
void alphasdana_state::pctlr_w(u8 data)
{
    m_pctlr=data&0x9f;m_pcm_on=true;
    m_pcm_timer->adjust(attotime::never);
    unsigned const width=m_pctlr&31;
    if((m_pctlr&0x80) && width && width<31)
        m_pcm_timer->adjust(attotime::from_ticks(width,m_xtal->read()));
    h2_cpu_gate();update_irq_lines();
    logerror("DANA_H2_PCM control=%02x sysclk=%u\n",m_pctlr,h2_sysclk());
}
TIMER_CALLBACK_MEMBER(alphasdana_state::h2_pcm_edge)
{
    if(!(m_pctlr&0x80) || !(m_pctlr&31) || (m_pctlr&31)==31)return;
    m_pcm_on=!m_pcm_on;h2_cpu_gate();
    unsigned const ticks=m_pcm_on?(m_pctlr&31):(31-(m_pctlr&31));
    m_pcm_timer->adjust(attotime::from_ticks(ticks,m_xtal->read()));
}
void alphasdana_state::pllcr_w(offs_t,u16 data,u16 mem_mask)
{
    u32 const old=h2_sysclk();h2_clock_capture();
    u16 const before=m_pllcr;
    m_pllcr=((before&~mem_mask)|(data&mem_mask))&0x3fbb;
    if((before^m_pllcr)&8)
    {
        if(m_pllcr&8)
            m_pll_off_timer->adjust(attotime::from_ticks(30,old));
        else
        {
            m_pll_off_timer->adjust(attotime::never);
            if(m_pll_stopped && !m_pll_wake_pending)
            {m_pll_wake_pending=true;m_pll_wake_timer->adjust(attotime::from_ticks(h2_wake_ticks(),m_xtal->read()));}
        }
    }
    h2_clock_apply(old);update_irq_lines();
    logerror("DANA_H2_PLLCR value=%04x pll=%u sysclk=%u lcdclk=%u\n",m_pllcr,h2_pll_hz(),h2_sysclk(),h2_lcd_hz());
}
TIMER_CALLBACK_MEMBER(alphasdana_state::h2_pll_off)
{
    if(!(m_pllcr&8))return;
    u32 const old=h2_sysclk();h2_clock_capture();m_pll_stopped=true;
    h2_clock_apply(old);update_irq_lines();
}
TIMER_CALLBACK_MEMBER(alphasdana_state::pll_wake_complete)
{
    if(!m_pll_wake_pending)return;
    h2_clock_capture();m_pll_wake_pending=false;m_pll_stopped=false;m_pllcr&=~u16(8);
    m_pll_off_timer->adjust(attotime::never);h2_clock_apply(0);update_irq_lines();
    logerror("DANA_H2_PLL_WAKE ticks=%u sysclk=%u\n",h2_wake_ticks(),h2_sysclk());
}
void alphasdana_state::pllfsr_w(offs_t,u16 data,u16 mem_mask)
{
    u32 const old=h2_sysclk();h2_clock_capture();
    if(!(m_pllfsr&0x4000))
    {u16 const mask=mem_mask&0x0fff;m_pllfsr=(m_pllfsr&~mask)|(data&mask);}
    if(data&mem_mask&0x4000)m_pllfsr|=0x4000;
    h2_clock_apply(old);
}

void alphasdana_state::rtc_sync_from_host()
{
    // Host time seeds power-on only. Thereafter all counting belongs to CLK32,
    // including wrong REFREQ settings, sleep, warm reset and save restoration.
    if(m_rtc_initialized)return;
    system_time host;machine().current_datetime(host);
    auto const &now=host.local_time;
    m_rtc_time=(u32(now.hour)<<24)|(u32(now.minute)<<16)|u32(now.second);
    m_rtc_initialized=true;
}
TIMER_CALLBACK_MEMBER(alphasdana_state::rtc_tick)
{
    if(m_watchdog&1)
    {
        unsigned const count=((m_watchdog>>8)&3)+1;
        if(count>=2)
        {
            m_watchdog&=~u16(0x300);
            if(m_watchdog&2)m_watchdog|=0x80;
            else m_watchdog_guard->adjust(attotime::zero);
        }
        else m_watchdog=(m_watchdog&~u16(0x300))|u16(count<<8);
    }
    if(m_rtc_control&0x80)
    {
        unsigned sec=(m_rtc_time&63)+1,min=(m_rtc_time>>16)&63,hour=(m_rtc_time>>24)&31;
        m_rtc_isr|=0x10;
        if(sec>=60)
        {
            sec=0;++min;m_rtc_isr|=2;
            if(m_stopwatch_active)
            {
                m_stopwatch=(m_stopwatch-1)&63;
                if(m_stopwatch==63){m_stopwatch_active=false;m_rtc_isr|=1;}
            }
            else if(m_stopwatch==63 && (m_rtc_ien&1))m_rtc_isr|=1;
            if(min>=60)
            {
                min=0;++hour;m_rtc_isr|=0x20;
                if(hour>=24){hour=0;m_rtc_day=(m_rtc_day+1)&511;m_rtc_isr|=8;}
            }
        }
        m_rtc_time=(hour<<24)|(min<<16)|sec;m_rtc_last_tick=m_rtc_time;
        if(m_rtc_time==m_rtc_alarm && m_rtc_day==m_rtc_day_alarm)m_rtc_isr|=4;
    }
    rtc_update_irq();
}
void alphasdana_state::h2_clk32_cycle()
{
    if(!(m_rtc_control&0x80) && !(m_watchdog&1))return;
    u16 const previous_status=m_rtc_isr;
    ++m_rtc_prescaler;
    // RTI taps are fixed crystal divisions, independent of REFREQ's TOD divider.
    ++m_rti_prescaler;
    for(unsigned n=0;n<8;++n)
        if(!(m_rti_prescaler&((8192U>>n)-1)))m_rtc_isr|=u16(0x100U<<n);
    if(m_rtc_prescaler>=((m_rtc_control&0x20)?38400U:32768U))
    {m_rtc_prescaler=0;rtc_tick(0);}
    if((m_rtc_isr^previous_status)&m_rtc_ien&0xff00)rtc_update_irq();
}
void alphasdana_state::rtc_update_irq()
{
    m_pending&=~u32(0x00400018);
    if(m_watchdog&0x80 && m_watchdog&2)m_pending|=8;
    if(m_rtc_isr&m_rtc_ien&0x003f)m_pending|=0x10;
    if(m_rtc_isr&m_rtc_ien&0xff00)m_pending|=0x00400000;
    update_irq_lines();
}
void alphasdana_state::rtc_time_w(offs_t offset,u16 data,u16 mem_mask)
{
    unsigned const shift=offset?0:16;u32 const mask=u32(mem_mask)<<shift;
    m_rtc_time=((m_rtc_time&~mask)|(u32(data&mem_mask)<<shift))&rtc_time_mask;
    m_rtc_last_tick=m_rtc_time;
}
void alphasdana_state::rtc_alarm_w(offs_t offset,u16 data,u16 mem_mask)
{
    unsigned const shift=offset?0:16;u32 const mask=u32(mem_mask)<<shift;
    m_rtc_alarm=((m_rtc_alarm&~mask)|(u32(data&mem_mask)<<shift))&rtc_time_mask;
}
void alphasdana_state::rtc_day_w(offs_t,u16 data,u16 mem_mask)
{m_rtc_day=((m_rtc_day&~mem_mask)|(data&mem_mask))&511;}
void alphasdana_state::rtc_day_alarm_w(offs_t,u16 data,u16 mem_mask)
{m_rtc_day_alarm=((m_rtc_day_alarm&~mem_mask)|(data&mem_mask))&511;}
void alphasdana_state::rtc_control_w(offs_t,u16 data,u16 mem_mask)
{m_rtc_control=((m_rtc_control&~mem_mask)|(data&mem_mask))&0xa0;rtc_update_irq();}
void alphasdana_state::rtc_ien_w(offs_t,u16 data,u16 mem_mask)
{m_rtc_ien=((m_rtc_ien&~mem_mask)|(data&mem_mask))&0xff3f;rtc_update_irq();}
void alphasdana_state::rtc_isr_w(offs_t,u16 data,u16 mem_mask)
{m_rtc_isr&=~(data&mem_mask&0xff3f);rtc_update_irq();}
void alphasdana_state::h2_stopwatch_w(offs_t,u16 data,u16 mem_mask)
{m_stopwatch=((m_stopwatch&~mem_mask)|(data&mem_mask))&63;m_stopwatch_active=m_stopwatch>0 && m_stopwatch<63;}
void alphasdana_state::watchdog_w(offs_t,u16 data,u16 mem_mask)
{
    u16 const controls=mem_mask&3;
    m_watchdog=(m_watchdog&~controls)|(data&controls);
    if(mem_mask&0x300)m_watchdog&=~u16(0x300);
    m_watchdog&=~(data&mem_mask&0x80);rtc_update_irq();
}
TIMER_CALLBACK_MEMBER(alphasdana_state::watchdog_guard)
{
    // Internal MCU reset, not a reset of an unmeasured external USB/IR net.
    ++m_watchdog_resets;m_watchdog_reset=true;
    machine_reset();for(auto &uart:m_uart)uart->reset();
    isp1161_irq_update(false);pd7_irq(false);st_irq_update(false);pen_irq5_update();rtc_update_irq();
    m_maincpu->reset();m_watchdog_reset=false;
}

u8 alphasdana_state::h2_gpio_input(unsigned n) const
{
    u8 const drive=m_gpio_drive[n]->read(),value=m_gpio_value[n]->read();
    // No external wire is inferred. Undriven GPIO uses its documented pull;
    // an unbiased pad retains the last digital sample, not an invented voltage.
    u8 const bias=m_gpio[n*4+2];
    u8 result=(m_gpio_sample[n]|bias);
    return (result&~drive)|(value&drive);
}
u8 alphasdana_state::h2_gpio_r(unsigned n,offs_t reg)
{
    if(reg!=1)return m_gpio[n*4+reg];
    // PDSEL[3:0] are reserved zero, not a peripheral selection.
    // PD0..3 remain GPIO outputs when DIR=1 (UM 10.4.5.5).
    u8 const sel=n==1?u8(m_gpio[7]|15):(n==3?m_pfsel:m_gpio[n*4+3]);
    u8 const driven=m_gpio[n*4] & sel;
    u8 value=(m_gpio[n*4+1]&driven)|(h2_gpio_input(n)&~driven);
    if(n==3 && !(sel&4) && pllcr_clko_enabled())
        value=(value&~u8(4))|((h2_sysclk() && (machine().time().as_ticks(u64(h2_sysclk())*2)&1))?4:0);
    m_gpio_sample[n]=value;return value;
}
u8 alphasdana_state::h2_lcd_pins() const
{
    u32 const hz=h2_lcd_hz();
    if(!hz || !(m_lckcon&0x80))return 0;
    u32 const div=(m_lpxcd&63)+1,width=std::max(u32(m_lxmax),1U),height=u32(m_lymax)+1;
    u64 const half=machine().time().as_ticks(u64(hz)*2)/div;
    u64 const pix=half/2,line=width+12+(m_lrra&1023);
    u32 const y=(pix/line)%height,x=pix%line;
    unsigned const bus=1U<<((m_lpicf>>2)&3),bpp=1U<<(m_lpicf&3),group=std::max(bus/bpp,1U);
    u8 value=((half/group)&1)?0x40:0;
    if(y==0)value|=0x10;
    if(x==line-1)value|=0x20;
    if((pix/line/((m_lacdrc&15)+1))&1)value|=0x80;
    if(x<width && m_lpicf==8)
    {
        u32 const col=(x/group)*group;
        for(unsigned bit=0;bit<4;++bit)
        {
            u32 const a=m_lssa+y*2*m_lvpw+(col+bit)/8;
            if(a<0x400000 && (m_ram[a/2]&(0x8000U>>((a&1)*8+((col+bit)&7)))))value|=1U<<(3-bit);
        }
    }
    if(m_lpolcf&1)value^=15;
    if(m_lpolcf&2)value^=0x20;
    if(m_lpolcf&4)value^=0x10;
    if(m_lpolcf&8)value^=0x40;
    return value;
}
u8 alphasdana_state::pcdata_r()
{
    u8 const drive=m_pc_drive->read(),external=m_pc_value->read();
    u8 const input=(m_pc_sample&~m_pcpden&~drive)|(external&drive);
    u8 const gpio=(m_pcdata&m_pcdir)|(input&~m_pcdir);
    m_pc_sample=(gpio&m_pcsel)|(h2_lcd_pins()&~m_pcsel);return m_pc_sample;
}
INPUT_CHANGED_MEMBER(alphasdana_state::h2_gpio_changed)
{sd_gpio_irq(true);}
INPUT_CHANGED_MEMBER(alphasdana_state::h2_xtal_changed)
{
    u32 const old=m_maincpu->clock();h2_clock_capture();
    m_clk32_timer->adjust(attotime::from_hz(u32(m_xtal->read())*2),0,attotime::from_hz(u32(m_xtal->read())*2));
    h2_clock_apply(old);
}
