// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
// MC68VZ328UM chapter 8 / UMAD. Implementations of the existing MCU state.
// Density is the manufacturer's digital duty, not a measured panel luminance.

namespace {
constexpr u8 lcd_numerator[16]={0,1,1,1,1,2,4,1,5,3,2,3,4,7,14,1};
constexpr u8 lcd_denominator[16]={1,8,5,4,3,5,9,2,9,5,3,4,5,8,15,1};
}

void alphasdana_state::lcd_start()
{
    m_lcd_timer=timer_alloc(FUNC(alphasdana_state::lcd_event),this);
    save_item(NAME(m_rmcr));save_item(NAME(m_dmacr));
    save_item(NAME(m_lcd_image));save_item(NAME(m_lcd_present));save_item(NAME(m_lcd_line));save_item(NAME(m_lcd_fifo));
    save_item(NAME(m_lcd_head));save_item(NAME(m_lcd_count));
    save_item(NAME(m_lcd_bpp));save_item(NAME(m_lcd_pan));
    save_item(NAME(m_lcd_y));save_item(NAME(m_lcd_width));save_item(NAME(m_lcd_height));
    save_item(NAME(m_lcd_fetched));save_item(NAME(m_lcd_consumed));save_item(NAME(m_lcd_needed));
    save_item(NAME(m_lcd_line_address));save_item(NAME(m_lcd_hz));
    save_item(NAME(m_lcd_frames));save_item(NAME(m_lcd_lines));
    save_item(NAME(m_lcd_dma_words));save_item(NAME(m_lcd_dma_bursts));save_item(NAME(m_lcd_dma_faults));
    save_item(NAME(m_lcd_running));save_item(NAME(m_lcd_self_refresh));
    save_item(NAME(m_lcd_pwm_phase));save_item(NAME(m_lcd_pwm_hz));save_item(NAME(m_lcd_pwm_origin));
    save_item(NAME(m_lcd_pwm_line_base));save_item(NAME(m_lcd_pwm_source));save_item(NAME(m_lcd_pwm_active));
    save_item(NAME(m_lcd_origin));save_item(NAME(m_lcd_offset));save_item(NAME(m_lcd_screen_period));
    machine().save().register_postload(save_prepost_delegate(FUNC(alphasdana_state::lcd_postload),this));
}

void alphasdana_state::lcd_bootstrap_reset()
{
    m_lssa=0; m_lvpw=0xff; m_lxmax=0x03f0; m_lymax=0x01ff;
    m_lcxp=0; m_lcyp=0; m_lcwch=0x0101; m_lblkc=0x7f;
    m_lpicf=0; m_lpolcf=0; m_lacdrc=0; m_lpxcd=0;
    m_lckcon=0; m_lposr=0; m_lgpmr=0x84; m_lrra=0x00ff; m_pwmr=0;
    m_rmcr=0;m_dmacr=0x62;
    m_lcd_timer->adjust(attotime::never);
    m_lcd_running=false;m_lcd_self_refresh=false;m_lcd_hz=0;
    m_lcd_y=0;m_lcd_frames=0;m_lcd_lines=0;
    m_lcd_dma_words=0;m_lcd_dma_bursts=0;m_lcd_dma_faults=0;
    m_lcd_head=0;m_lcd_count=0;m_lcd_fetched=0;m_lcd_consumed=0;m_lcd_needed=0;
    m_lcd_width=0;m_lcd_height=0;m_lcd_line_address=0;
    m_lcd_origin=machine().time();m_lcd_offset=0;
    m_lcd_pwm_phase=0;m_lcd_pwm_hz=0;m_lcd_pwm_origin=machine().time();
    m_lcd_pwm_line_base=0;m_lcd_pwm_source=0;m_lcd_pwm_active=false;
    std::fill(std::begin(m_lcd_image),std::end(m_lcd_image),0);
    std::fill(std::begin(m_lcd_present),std::end(m_lcd_present),0);
    std::fill(std::begin(m_lcd_line),std::end(m_lcd_line),0);
    std::fill(std::begin(m_lcd_fifo),std::end(m_lcd_fifo),0);
    lcd_publish();
}

void alphasdana_state::lcd_register_changed()
{
    // Masks follow the VZ register tables, including LCKCON's storage bits.
    m_lxmax&=0x03f0;m_lymax&=0x01ff;m_lpicf&=15;m_lpolcf&=15;
    m_lpxcd&=63;m_lposr&=15;m_lrra&=0x03ff;m_pwmr&=0x07ff;
    m_rmcr&=0x80;m_dmacr&=0xf7;
    lcd_clock_changed();
}

double alphasdana_state::lcd_position() const
{
    return m_lcd_offset+(m_lcd_running && m_lcd_hz
        ? (machine().time()-m_lcd_origin).as_double()*m_lcd_hz : 0);
}

void alphasdana_state::lcd_clock_changed()
{
    if(!m_lcd_timer)return;
    m_lcd_pwm_phase=std::fmod(lcd_pwm_ticks(),256.0);
    m_lcd_pwm_origin=machine().time();m_lcd_pwm_line_base=m_lcd_lines;
    // Capture elapsed pixel clocks at the previous rate before changing PLL
    // or LPXCD. A stopped PLL freezes the beam/FIFO; STOP alone does not.
    m_lcd_offset=lcd_position();m_lcd_origin=machine().time();
    u32 const clock=h2_lcd_hz();
    m_lcd_hz=double(clock)/((m_lpxcd&63)+1);
    if(!m_lcd_running && (m_lckcon&0x80) && m_lcd_hz)
    {
        m_lcd_running=true;m_lcd_offset=0;
        if(m_lcd_y>m_lymax)m_lcd_y=0;
        lcd_line_start();
    }
    if(m_lcd_hz && m_lxmax && (m_lckcon&0x80))
    {
        attotime const frame=attotime::from_ticks(u64(lcd_line_clocks())*(m_lymax+1)*((m_lpxcd&63)+1),clock);
        if(m_lcd_screen_period!=frame.as_attoseconds())
        {
            m_lcd_screen_period=frame.as_attoseconds();
            m_screen->configure(560,160,rectangle(0,559,0,159),attotime(0,m_lcd_screen_period));
        }
    }
    m_lcd_pwm_source=(m_pwmr>>9)&3;
    m_lcd_pwm_active=bool(m_pwmr&256) && clock && m_lcd_pwm_source!=3
        && (m_lcd_pwm_source==2 || m_lcd_running);
    m_lcd_pwm_hz=m_lcd_pwm_source==2?clock:m_lcd_hz;
    lcd_schedule();lcd_publish();
}

void alphasdana_state::lcd_line_start()
{
    // LSSA high address bits do not increment: an image must fit within a
    // 1 MiB boundary (UM table 8-2). This is an address counter, not RAM mirroring.
    m_lcd_line_address=(m_lssa&0xfff00000U) | ((m_lssa+u32(m_lcd_y)*2*m_lvpw)&0x000ffffeU);
    m_lcd_width=m_lxmax;m_lcd_height=m_lymax+1;
    m_lcd_bpp=(m_lpicf&3)==3?0:u8(1U<<(m_lpicf&3));m_lcd_pan=m_lposr;
    m_lcd_head=0;m_lcd_count=0;m_lcd_fetched=0;m_lcd_consumed=0;
    m_lcd_needed=m_lcd_bpp ? ((m_lcd_width+m_lcd_pan)*m_lcd_bpp+15)/16 : 0;
    std::fill(std::begin(m_lcd_line),std::end(m_lcd_line),0);
}

u16 alphasdana_state::lcd_dma_read(u32 address)
{
    // Bus-master fetches use the SAME physical storage and CS/SDRAM decode.
    // They are not instruction reads and must not inherit the interrupted
    // CPU's user/supervisor function code or appear as Lua CPU memory taps.
    if(!m_physical_boot)
    {
        if(address<0x400000)return m_ram[address>>1];
    }
    else if((m_cs_select[0]&1) && cs_hit(3,address) && !cs_hit(0,address)
        && physical_ram_ready() && (!(m_dram[2]&0x8000) || m_sdram_init_phase==3))
    {
        u32 const index=physical_sdram_index(address-cs_base(3));
        return index<0x400000 ? m_ram[index>>1] : m_physical_ram_extra[(index-0x400000)>>1];
    }
    else if(m_firmware->exists() && (!(m_cs_select[0]&1) || cs_hit(0,address)) && !cs_hit(3,address))
    {
        if(m_nor_profile->read()==1 && (m_cs_select[0]&0x80))
            return m_nor->bus_read(address&(m_nor->array_bytes()-1));
        u32 const size=m_firmware->get_rom_size();
        u32 const index=(size&(size-1)) ? address-cs_base(0) : (address-cs_base(0))&(size-1);
        if(index<size && size-index>=2)
        {
            u8 const *rom=m_firmware->get_rom_base();return u16(rom[index])<<8 | rom[index+1];
        }
    }
    // Unselected external bus is undriven. Do not fabricate a CPU exception,
    // LCD interrupt, RAM alias, or successful transfer from an absent bank.
    ++m_lcd_dma_faults;return 0xffff;
}

void alphasdana_state::lcd_schedule()
{
    m_lcd_timer->adjust(attotime::never);
    if(!m_lcd_running || !m_lcd_hz)return;
    double const position=lcd_position();
    double next=lcd_line_clocks();
    unsigned const burst=m_dmacr>>4,trigger=m_dmacr&7;
    bool const valid=burst>=1 && burst<=8 && trigger>=1 && trigger<=6 && burst+trigger<=8;
    if(!m_lcd_self_refresh && valid && m_lcd_needed && m_lcd_fetched<m_lcd_needed)
    {
        // Refill as soon as the eight-word FIFO reaches the low watermark.
        double const consume=std::max(0,int(m_lcd_fetched)-int(trigger))*16.0/m_lcd_bpp;
        next=std::min(next,12.0+std::max(0.0,consume-m_lcd_pan));
        if(m_lcd_fetched==0)next=0;
    }
    m_lcd_timer->adjust(attotime::from_double(std::max(1.0/m_lcd_hz,(next-position)/m_lcd_hz)));
}

u8 alphasdana_state::lcd_density(u8 pixel) const
{
    if(m_lcd_bpp==1)return pixel?15:0;
    if(m_lcd_bpp==2)return pixel==0?0:pixel==3?15:pixel==1?(m_lgpmr&15):(m_lgpmr>>4);
    return pixel&15;
}

u8 alphasdana_state::lcd_pixel_density(unsigned x) const
{
    unsigned const bit=(x+m_lcd_pan)*m_lcd_bpp,word=bit/16;
    u8 pixel=m_lcd_line[x+m_lcd_pan];
    if(word>=m_lcd_consumed && word-m_lcd_consumed<m_lcd_count)
        pixel=(m_lcd_fifo[(m_lcd_head+word-m_lcd_consumed)&7]>>(16-m_lcd_bpp-bit%16))&((1U<<m_lcd_bpp)-1);
    unsigned const cx=m_lcxp&1023,cy=m_lcyp&511,cw=(m_lcwch>>8)&31,ch=m_lcwch&31;
    bool const cursor_on=!(m_lblkc&128) || !((m_lcd_frames/((m_lblkc&127)+1))&1);
    if(cursor_on && x>=cx && x<cx+cw && m_lcd_y>=cy && m_lcd_y<cy+ch)
    {
        if((m_lcxp>>14)==1)return 15;
        if((m_lcxp>>14)==2)pixel^=(1U<<m_lcd_bpp)-1;
        if((m_lcxp>>14)==3)return 0;
    }
    return lcd_density(pixel);
}

void alphasdana_state::lcd_consume_words(unsigned target)
{
    // Advance the actual shift FIFO. Output is decoded from consumed FIFO
    // words, never by rereading a live framebuffer behind the DMA controller.
    while(m_lcd_count && m_lcd_consumed<target)
    {
        u16 const word=m_lcd_fifo[m_lcd_head];
        unsigned const pixels=16/m_lcd_bpp,base=m_lcd_consumed*pixels;
        for(unsigned p=0;p<pixels && base+p<std::size(m_lcd_line);++p)
        {
            m_lcd_line[base+p]=(word>>(16-m_lcd_bpp*(p+1)))&((1U<<m_lcd_bpp)-1);
            if(base+p>=m_lcd_pan && base+p-m_lcd_pan<m_lcd_width)
            {
                unsigned const x=base+p-m_lcd_pan;
                m_lcd_image[u32(m_lcd_y)*1024+x]=lcd_pixel_density(x);
            }
        }
        m_lcd_head=(m_lcd_head+1)&7;--m_lcd_count;++m_lcd_consumed;
    }
}

TIMER_CALLBACK_MEMBER(alphasdana_state::lcd_event)
{
    if(!m_lcd_running || !m_lcd_hz)return;
    // LCDOFF stops before another fill DMA. Existing FIFO contents persist.
    if(!(m_lckcon&0x80))
    {
        m_lcd_offset=lcd_position();m_lcd_origin=machine().time();m_lcd_running=false;
        lcd_clock_changed();return;
    }
    double const position=lcd_position();
    if(position+0.001>=lcd_line_clocks())
    {
        if(!m_lcd_self_refresh && m_lcd_bpp)
            lcd_consume_words(m_lcd_fetched);
        ++m_lcd_lines;
        if(++m_lcd_y>=m_lcd_height)
        {
            m_lcd_y=0;++m_lcd_frames;
            // Deliver completed digital frames to MAME/SDL. Its presentation
            // boundary need not coincide with a PLL-retimed guest frame edge.
            for(unsigned y=0;y<160;++y)
                std::copy_n(&m_lcd_image[y*1024],560,&m_lcd_present[y*560]);
            // RMCR changes take effect only on the positive frame edge.
            m_lcd_self_refresh=bool(m_rmcr&128);
        }
        m_lcd_offset=std::max(0.0,position-lcd_line_clocks());m_lcd_origin=machine().time();
        lcd_line_start();
    }
    if(!m_lcd_self_refresh && m_lcd_bpp && m_lcd_fetched<m_lcd_needed)
    {
        unsigned const burst=m_dmacr>>4,trigger=m_dmacr&7;
        if(burst>=1 && burst<=8 && trigger>=1 && trigger<=6 && burst+trigger<=8)
        {
            unsigned const consumed=std::min<unsigned>(m_lcd_fetched,
                unsigned(std::max(0.0,lcd_position()-12+m_lcd_pan)*m_lcd_bpp/16));
            lcd_consume_words(consumed);
            if(m_lcd_count<=trigger)
            {
                unsigned const count=std::min<unsigned>({burst,8U-m_lcd_count,unsigned(m_lcd_needed-m_lcd_fetched)});
                for(unsigned n=0;n<count;++n)
                {
                    u32 const address=(m_lcd_line_address&0xfff00000U)|((m_lcd_line_address+2*m_lcd_fetched)&0xffffeU);
                    u16 const word=lcd_dma_read(address);
                    m_lcd_fifo[(m_lcd_head+m_lcd_count++)&7]=word;
                    ++m_lcd_fetched;++m_lcd_dma_words;
                }
                ++m_lcd_dma_bursts;
            }
        }
    }
    lcd_schedule();lcd_publish();
}

u8 alphasdana_state::lcd_data_pins() const
{
    if(!m_lcd_running || !m_lcd_hz || m_lcd_self_refresh)return 0;
    double const pos=lcd_position();if(pos<12 || pos>=12+m_lcd_width)return 0;
    unsigned const bus=1U<<((m_lpicf>>2)&3),x=(unsigned(pos-12)/bus)*bus;
    u8 result=0;
    for(unsigned p=0;p<bus && x+p<m_lcd_width;++p)
    {
        u8 const density=lcd_pixel_density(x+p);
        // UM specifies densities, not the proprietary FRC spatial phase.
        // Deterministic pulse-density phase; measured silicon phase unqualified.
        if((m_lcd_frames%lcd_denominator[density])<lcd_numerator[density])result|=1U<<(bus-1-p);
    }
    return (m_lpolcf&1)?u8(result^((1U<<bus)-1)):result;
}

u8 alphasdana_state::lcd_control_pins() const
{
    if(!m_lcd_running || !m_lcd_hz)return 0;
    double const pos=lcd_position();unsigned const bus=1U<<((m_lpicf>>2)&3);
    u8 value=0;
    if(pos<4)value|=0x20;
    if((m_lcd_y==0 && pos>=4) || (m_lcd_y==1 && pos<4))value|=0x10;
    if(!m_lcd_self_refresh && pos>=12 && pos<12+m_lcd_width
        && (unsigned((pos-12)*2/bus)&1))value|=0x40;
    u64 const acd=(m_lacdrc&128)?m_lcd_lines:m_lcd_frames;
    if((acd/((m_lacdrc&127)+1))&1)value|=0x80;
    if(m_lpolcf&2)value^=0x20;if(m_lpolcf&4)value^=0x10;
    if(!m_lcd_self_refresh && (m_lpolcf&8))value^=0x40;
    return value;
}

double alphasdana_state::lcd_pwm_ticks() const
{
    return m_lcd_pwm_phase+(!m_lcd_pwm_active?0:m_lcd_pwm_source==0
        ? double(m_lcd_lines-m_lcd_pwm_line_base)
        : (machine().time()-m_lcd_pwm_origin).as_double()*m_lcd_pwm_hz);
}

bool alphasdana_state::lcd_contrast_pin() const
{
    return m_lcd_pwm_active && (u64(lcd_pwm_ticks())&255)<(m_pwmr&255);
}

void alphasdana_state::lcd_publish()
{
    m_lcd_outputs[0]=(m_lcd_frames);
    m_lcd_outputs[1]=(m_lcd_lines);
    m_lcd_outputs[2]=(m_lcd_dma_words);
    m_lcd_outputs[3]=(m_lcd_dma_bursts);
    m_lcd_outputs[4]=(m_lcd_dma_faults);
    m_lcd_outputs[5]=(m_lcd_line_address+2*m_lcd_fetched);
    m_lcd_outputs[6]=(m_lcd_count);
    m_lcd_outputs[7]=(m_lcd_y);
    m_lcd_outputs[8]=(m_lcd_hz);
    m_lcd_outputs[9]=(m_lcd_running && m_lcd_hz);
    m_lcd_outputs[10]=(m_lcd_self_refresh);
    m_lcd_outputs[11]=(m_lcd_bpp);
    m_lcd_outputs[12]=(ioport("LCD_PANEL")->read());
}

void alphasdana_state::lcd_postload()
{
    // Scheduler restores the exact event deadline; do not restart the FIFO or
    // frame on load. The output surface and partial line are save-state data.
    if(m_lcd_screen_period)m_screen->configure(560,160,rectangle(0,559,0,159),attotime(0,m_lcd_screen_period));
    lcd_publish();
}

u32 alphasdana_state::screen_update(screen_device &,bitmap_rgb32 &bitmap,const rectangle &cliprect)
{
    rgb_t const white(0xbd,0xbd,0xaa),black(0x40,0x40,0x40);
    if(!(m_lckcon&128)) {bitmap.fill(white,cliprect);return 0;}
    rgb_t colors[16];
    for(unsigned d=0;d<16;++d)
    {
        unsigned const n=lcd_numerator[d],q=lcd_denominator[d];
        colors[d]=rgb_t((white.r()*(q-n)+black.r()*n)/q,
            (white.g()*(q-n)+black.g()*n)/q,(white.b()*(q-n)+black.b()*n)/q);
    }
    for(int y=std::max(cliprect.top(),0);y<=std::min(cliprect.bottom(),159);++y)
        for(int x=std::max(cliprect.left(),0);x<=std::min(cliprect.right(),559);++x)
            bitmap.pix(y,x)=colors[m_lcd_present[y*560+x]];
    return 0;
}
