// license:BSD-3-Clause
// Integrated ISP1161A1 packet endpoints, board signals and explicit transports.
// Included in alphasdana.cpp after the existing HC/DC register/PIO implementation.

void alphasdana_state::isp1161_dc_event(u32 events)
{
    // Philips section 13.1.5: enables gate event capture, not just output.
    m_isp_dc_interrupt|=events & m_isp_dc_interrupt_enable & 0x00ffff7fU;
    isp1161_irq_update(true);
}

void alphasdana_state::isp1161_irq_update(bool transition)
{
    if((m_isp_interrupt_enable&0x80000000U) &&
       (m_isp_interrupt_enable&m_isp_interrupt_status&0x7f))
        m_isp_up_irq|=0x10;
    else m_isp_up_irq&=~u16(0x10);
    bool const condition[2]={
        bool(m_isp_up_irq&m_isp_hc_regs16[0x25]&0x77),
        bool((m_isp_dc_mode&8)&&(m_isp_dc_interrupt&m_isp_dc_interrupt_enable&0x00ffff7fU))};
    for(unsigned ch=0;ch<2;++ch)
    {
        bool const enabled=ch==0 ? bool(m_isp_hardware&1) : bool(m_isp_dc_mode&8);
        bool const pol=ch==0 ? bool(m_isp_hardware&4) : bool(m_isp_dc_hw&1);
        bool const pulse=ch==0 ? bool(m_isp_hardware&2) : bool(m_isp_dc_hw&2);
        if(enabled || ch==1)
        {
            if(pulse)
            {
                if(transition && condition[ch]&&!m_isp_irq_condition[ch])
                {
                    m_isp_irq_high[ch]=pol;
                    m_isp_irq_timer[ch]->adjust(attotime::from_nsec(166),ch);
                }
                else if(!condition[ch])m_isp_irq_high[ch]=!pol;
            }
            else m_isp_irq_high[ch]=condition[ch]?pol:!pol;
            m_isp_irq_condition[ch]=condition[ch];
        }
        // Original ROM: DC HwrIRQ2Handler reads C0. The HC installs its
        // service at HwrIRQ3Handler and unmasks IRQ3. These are distinct
        // chip pin names and VZ IRQ numbers; PCB copper is not claimed.
        unsigned const irq=ch==0?3:2;
        u16 const polarity=u16(1U<<(16-irq));
        u16 const edge=u16(1U<<(12-irq));
        bool const active=(m_icr&polarity)?m_isp_irq_high[ch]:!m_isp_irq_high[ch];
        if(transition && m_isp_irq_high[ch]!=m_isp_vz_last_high[ch] && active && (m_icr&edge))
            m_isp_vz_edge[ch]=true;
        m_isp_vz_last_high[ch]=m_isp_irq_high[ch];
        u8 const pin=u8(1U<<(irq+3));
        bool const gate=!(m_gpio[4]&pin)&&!(m_gpio[7]&pin);
        bool const pending=gate&&((m_icr&edge)?m_isp_vz_edge[ch]:active);
        u32 const bit=1U<<(15+irq);
        m_pending=(m_pending&~bit)|(pending?bit:0);
    }
    update_irq_lines();
}

TIMER_CALLBACK_MEMBER(alphasdana_state::isp1161_irq_pulse_end)
{
    unsigned const ch=unsigned(param);
    m_isp_irq_high[ch]=ch==0 ? !(m_isp_hardware&4) : !(m_isp_dc_hw&1);
    // Do not re-trigger a pulse from an unchanged pending condition.
    isp1161_irq_update(false);
}

void alphasdana_state::isp1161_dc_bus_reset()
{
    // USB bus reset preserves mode, hardware, enables and address readback.
    // Its effective address is zero until a new status-stage ACK.
    auto const command=m_isp_dc_fifo;
    m_isp_dc_fifo=isp1161a1::dc_endpoints{};
    m_isp_dc_fifo.port_mode=command.port_mode;m_isp_dc_fifo.port_ep=command.port_ep;
    m_isp_dc_fifo.port_cursor=command.port_cursor;
    m_isp_dc_fifo.enabled=1;
    std::fill(std::begin(m_isp_dc_ep_config),std::end(m_isp_dc_ep_config),0);
    std::fill(std::begin(m_isp_dc_ep_status),std::end(m_isp_dc_ep_status),0);
    m_isp_dc_dma_cfg&=~u16(8);
    m_isp_dc_mode&=~u16(0x20);
    m_isp_dc_interrupt=0; // USB reset does not reset the MCU command/data transaction
    m_isp_dc_suspended=false;
    isp1161_dc_event(1);
    logerror("DANA_USB_DC_BUS_RESET mode=%04x enable=%08x\n",m_isp_dc_mode,m_isp_dc_interrupt_enable);
}

void alphasdana_state::isp1161_dc_command(u16 data)
{
    if(data&0xff00){physical_block("ISP1161_DC_COMMAND_UPPER_BYTE",0x1f000006,data);return;}
    u8 const cmd=u8(data);
    if(m_isp_dc_pending||m_isp_dc_read_phase)
    {physical_block("ISP1161_DC_INCOMPLETE_TRANSFER",0x1f000006,data);return;}
    m_isp_dc_fifo.port_mode=0;
    if(cmd==0xf6){isp1161_dc_reset();isp1161_irq_update(true);return;}
    if(cmd==0xf4){m_isp_dc_fifo.setup_ack=1;return;}
    if(cmd>=1&&cmd<=0x0f)
    {
        unsigned const ep=cmd;
        if(!m_isp_dc_fifo.direction(ep,m_isp_dc_ep_config))
        {logerror("DANA_USB_DC illegal OUT FIFO write ep=%u\n",ep);return;}
        m_isp_dc_fifo.select(ep,true);return;
    }
    if(cmd==0x10||(cmd>=0x12&&cmd<=0x1f))
    {
        unsigned const ep=cmd&15;
        if(m_isp_dc_fifo.direction(ep,m_isp_dc_ep_config))
        {logerror("DANA_USB_DC illegal IN FIFO read ep=%u\n",ep);return;}
        m_isp_dc_fifo.select(ep,false);return;
    }
    if((cmd>=0x40&&cmd<=0x4f)||(cmd>=0x80&&cmd<=0x8f))
    {
        unsigned const ep=cmd&15;
        m_isp_dc_fifo.stalled[ep]=(cmd&0xf0)==0x40;
        if(!m_isp_dc_fifo.stalled[ep])m_isp_dc_fifo.flush(ep);
        return;
    }
    if(cmd>=0x61&&cmd<=0x6f){m_isp_dc_fifo.validate(cmd&15,m_isp_dc_ep_config);return;}
    if(cmd==0x70||(cmd>=0x72&&cmd<=0x7f)){m_isp_dc_fifo.clear(cmd&15,m_isp_dc_ep_config);return;}
    if(isp1161_dc_write_command(cmd))
    {m_isp_dc_cmd=cmd;m_isp_dc_pending=true;m_isp_dc_write_phase=0;return;}
    if(isp1161_dc_read_command(cmd))
    {
        m_isp_dc_cmd=cmd;m_isp_dc_read_phase=1;
        m_isp_dc_read_snapshot=cmd==0xc0?m_isp_dc_interrupt:m_isp_dc_interrupt_enable;
        return;
    }
    physical_block("ISP1161_DC_COMMAND_UNKNOWN",0x1f000006,data);
}

u16 alphasdana_state::isp1161_dc_data_r()
{
    if(m_isp_dc_fifo.port_mode==2)return m_isp_dc_fifo.read(m_isp_dc_ram);
    if(m_isp_dc_pending||m_isp_dc_fifo.port_mode==1)return 0xffff; // CLR.W pre-read
    if(!m_isp_dc_read_phase)
    {physical_block("ISP1161_DC_READ_WITHOUT_COMMAND",0x1f000004);return 0xffff;}
    u8 const cmd=m_isp_dc_cmd;
    if(cmd==0xc0||cmd==0xc3)
    {
        u16 const value=m_isp_dc_read_phase==1?u16(m_isp_dc_read_snapshot):u16(m_isp_dc_read_snapshot>>16);
        if(m_isp_dc_read_phase==1)m_isp_dc_read_phase=2;
        else
        {
            m_isp_dc_read_phase=0;
            if(cmd==0xc0)m_isp_dc_interrupt&=~(m_isp_dc_read_snapshot&0x005bU);
            isp1161_irq_update(true);
        }
        return value;
    }
    m_isp_dc_read_phase=0;
    if(cmd>=0x30&&cmd<=0x3f)return m_isp_dc_ep_config[cmd&15];
    if((cmd>=0x50&&cmd<=0x5f)||(cmd>=0xd0&&cmd<=0xdf))
    {
        unsigned const ep=cmd&15;
        u16 const value=m_isp_dc_fifo.status(ep);
        if(cmd<0x60)
        {
            m_isp_dc_interrupt&=~(1U<<(8+ep));
            if(ep<2)m_isp_dc_fifo.overwrite=0;
            isp1161_irq_update(true);
        }
        return value;
    }
    if(cmd>=0xa0&&cmd<=0xaf){unsigned const ep=cmd&15;u8 const e=m_isp_dc_fifo.error[ep];m_isp_dc_fifo.error[ep]&=0x7f;m_isp_dc_fifo.error_pending[ep]=0;return e;}
    switch(cmd)
    {
    case 0xb3:return m_isp_dc_scratch;
    case 0xb4:return m_isp_dc_fifo.frame&0x7ff;
    case 0xb5:return 0x6123;
    case 0xb7:return m_isp_dc_address;
    case 0xb9:return m_isp_dc_mode;
    case 0xbb:return m_isp_dc_hw;
    case 0xf1:return m_isp_dc_dma_cfg;
    case 0xf3:return m_isp_dc_dma_count;
    }
    physical_block("ISP1161_DC_READ_REGISTER_UNKNOWN",0x1f000004,cmd);return 0xffff;
}

void alphasdana_state::isp1161_dc_data_w(u16 data)
{
    if(m_isp_dc_fifo.port_mode==1){m_isp_dc_fifo.write(data,m_isp_dc_ram);return;}
    if(!m_isp_dc_pending)
    {physical_block("ISP1161_DC_WRITE_WITHOUT_COMMAND",0x1f000004,data);return;}
    u8 const code=m_isp_dc_cmd;
    if(code==0xc2)
    {
        if(!m_isp_dc_write_phase){m_isp_dc_write_low=data;m_isp_dc_write_phase=1;return;}
        m_isp_dc_interrupt_enable=(u32(m_isp_dc_write_low)|(u32(data)<<16))&0x00ffff7f;
        m_isp_dc_write_phase=0;m_isp_dc_pending=false;
        isp1161_irq_update(false);return;
    }
    if(code>=0x20&&code<=0x2f)
    {
        if(data&0xff00){physical_block("ISP1161_DC_ENDPOINT_CONFIG_RESERVED",0x1f000004,data);return;}
        m_isp_dc_ep_config[code&15]=data;
        if(code==0x2f&&!m_isp_dc_fifo.allocate(m_isp_dc_ep_config))
            logerror("DANA_USB_DC endpoint allocation rejected (2462-byte SRAM / 512 non-ISO)\n");
    }
    else switch(code)
    {
    case 0xb0:
        if(data!=0xaa37){physical_block("ISP1161_DC_UNLOCK_CODE",0x1f000004,data);return;}
        m_isp_dc_unlocked=true;break;
    case 0xb2:m_isp_dc_scratch=data&0x1fff;break;
    case 0xb6:
        m_isp_dc_address=data&0xff;
        m_isp_dc_fifo.enabled=bool(data&0x80);
        m_isp_dc_fifo.pending_address=data&0x7f;
        m_isp_dc_fifo.address_pending=1;
        break;
    case 0xb8:
        if((m_isp_dc_mode&0x20)&&!(data&0x20))m_isp_dc_suspend_requested=true;
        m_isp_dc_mode=data&0xad;break;
    case 0xba:m_isp_dc_hw=data&0x7fff;break;
    case 0xf0:
        if((data&8)&&!(m_isp_dc_dma_cfg&8))m_isp_dc_dma_count=m_isp_dc_dma_reload;
        m_isp_dc_dma_cfg=data&0xc0fb;
        m_isp_dc_dma_cursor=0;break;
    case 0xf2:m_isp_dc_dma_count=data;m_isp_dc_dma_reload=data;break;
    default:physical_block("ISP1161_DC_WRITE_UNSUPPORTED",0x1f000004,data);return;
    }
    m_isp_dc_pending=false;
    isp1161_irq_update(true);
    logerror("DANA_ISP1161_DC cmd=%02x value=%04x mode=%04x irq=%08x\n",code,data,m_isp_dc_mode,m_isp_dc_interrupt);
}

void alphasdana_state::isp1161_root_update()
{
    for(unsigned port=0;port<2;++port)
    {
        unsigned const kind=(m_usb_printer[port]->is_open()&&m_usb_printer[port]->is_ready())?1:
            ((ioport("USBTEST")->read()&(1U<<port))?2:0);
        u32 &status=m_isp_hc_regs32[0x15+port];
        if(kind!=m_isp_function[port].kind)
        {
            m_isp_function[port]=isp1161a1::usb_function{};
            m_isp_function[port].kind=u8(kind);
            if(kind)status|=1;else status&=~u32(0x317);
            status|=0x10000;m_isp_interrupt_status|=0x40;
            logerror("DANA_USB_ATTACH port=%u function=%u status=%08x\n",port+1,kind,status);
        }
        bool const overcurrent=bool(ioport("USBOC")->read()&(1U<<port));
        if((m_isp_hc_regs32[0x12]&0x200)&&!overcurrent)status|=0x100; // no power switching
        if(overcurrent!=bool(status&8))
        {
            status=(status&~u32(8))|(overcurrent?8:0)|0x80000;
            if(overcurrent)status&=~u32(0x102);
            m_isp_interrupt_status|=0x40;
        }
        if(m_isp_port_reset[port]&&m_isp_usb_msec>=m_isp_port_reset[port])
        {
            m_isp_port_reset[port]=0;status&=~u32(0x10);
            if((status&0x109)==0x101)status|=2;
            status|=0x100000;m_isp_interrupt_status|=0x40;
            m_isp_function[port].reset();
        }
    }
}

void alphasdana_state::isp1161_root_write(unsigned port,u32 value)
{
    u32 &status=m_isp_hc_regs32[0x15+port];
    status&=~(value&0x1f0000);
    if(value&1)status&=~u32(2);
    if(value&2){if(status&1)status|=2;else status|=0x10000;}
    if(value&4){if(status&1)status|=4;else status|=0x10000;}
    if((value&8)&&(status&4)){status&=~u32(4);status|=0x40000;}
    if((value&0x100)&&!(status&8))status|=0x100;
    if((value&0x200)&&!(m_isp_hc_regs32[0x12]&0x200))status&=~u32(0x107);
    if((value&0x10)&&(status&0x109)==0x101)
    {status=(status|0x10)&~u32(2);m_isp_port_reset[port]=m_isp_usb_msec+10;}
    if(status&0x1f0000)m_isp_interrupt_status|=0x40;
    isp1161_irq_update(true);
}

isp1161a1::reply alphasdana_state::isp1161_host_packet(
    isp1161a1::transaction const &tx,u8 const *out,u8 *in,u16 length)
{
    for(unsigned port=0;port<2;++port)
    {
        u32 const status=m_isp_hc_regs32[0x15+port];
        if((status&0x11f)!=0x103||tx.low_speed!=bool(status&0x200))continue;
        auto &function=m_isp_function[port];
        if(!function.kind||function.address!=tx.address)continue;
        auto print=[this,port](u8 value)->bool {
            if(!m_usb_printer[port]->is_ready())return false;
            m_usb_printer[port]->output(value);return true;
        };
        auto result=function.transfer(tx,out,in,length,print);
        logerror("DANA_USB_HC_PACKET port=%u address=%u ep=%u pid=%u bytes=%u result=%u actual=%u\n",
            port+1,tx.address,tx.endpoint,unsigned(tx.direction),length,unsigned(result.status),result.size);
        return result;
    }
    return {isp1161a1::handshake::timeout,0};
}

TIMER_CALLBACK_MEMBER(alphasdana_state::isp1161_usb_service)
{
    ++m_isp_usb_msec;
    isp1161_root_update();
    if(m_isp_usb_vbus&&!m_usb_link->online())
    {m_isp_usb_vbus=false;m_isp_dc_suspended=false;m_isp_dc_interrupt&=~u32(0x84);}
    m_usb_link->poll([this](u8 op,u8 address,u8 endpoint,u8 flags,u8 const *out,u8 *in,u16 length)
    {return isp1161_upstream(op,address,endpoint,flags,out,in,length);});
    if(m_isp_usb_vbus&&((m_isp_dc_mode&1)||(m_isp_dc_hw&0x4000)))
    {
        if(m_isp_usb_clock&&!m_isp_dc_suspended)
        {m_isp_dc_last_sof=m_isp_usb_msec;m_isp_dc_fifo.frame=(m_isp_dc_fifo.frame+1)&0x7ff;isp1161_dc_event(0x10);}
        else if(!m_isp_dc_suspended&&m_isp_usb_msec>m_isp_dc_last_sof)
        {
            isp1161_dc_event(0x20);
            if(m_isp_usb_msec-m_isp_dc_last_sof>=3)
            {m_isp_dc_suspended=true;m_isp_dc_interrupt|=0x80;isp1161_dc_event(4);}
        }
    }
    isp1161_irq_update(true);
}

isp1161a1::reply alphasdana_state::isp1161_upstream(
    u8 op,u8 address,u8 endpoint,u8 flags,u8 const *out,u8 *in,u16 length)
{
    using namespace isp1161a1;
    if(op==1){m_isp_usb_vbus=true;m_isp_usb_clock=bool(flags&1);m_isp_dc_last_sof=m_isp_usb_msec;return {handshake::ack,0};}
    if(op==2){m_isp_usb_vbus=false;m_isp_usb_clock=false;m_isp_dc_suspended=false;return {handshake::ack,0};}
    if(op==0x10)
    {
        in[0]=m_isp_usb_vbus;in[1]=u8(m_isp_dc_mode);in[2]=m_isp_dc_fifo.active_address;
        in[3]=m_isp_dc_fifo.allocation_valid;in[4]=u8(m_isp_dc_address);
        in[5]=m_isp_irq_high[0];in[6]=m_isp_irq_high[1];in[7]=m_isp_dc_suspended;
        return {handshake::ack,8};
    }
    if(op>=0x20&&op<=0x25)return isp1161_dma_packet(op,flags,out,in,length);
    bool const connected=m_isp_usb_vbus&&((m_isp_dc_mode&1)||(m_isp_dc_hw&0x4000));
    if(!connected)return {handshake::timeout,0};
    if(op==3){m_isp_dc_last_sof=m_isp_usb_msec;isp1161_dc_bus_reset();return {handshake::ack,0};}
    if(op==4){m_isp_dc_last_sof=m_isp_usb_msec;m_isp_dc_fifo.frame=u16((unsigned(address)|(unsigned(endpoint)<<8))&0x7ff);isp1161_dc_event(0x10);return {handshake::ack,0};}
    if(op==5){m_isp_usb_clock=false;m_isp_dc_suspended=true;m_isp_dc_interrupt|=0x80;isp1161_dc_event(4);return {handshake::ack,0};}
    if(op==6){m_isp_usb_clock=true;m_isp_dc_last_sof=m_isp_usb_msec;m_isp_dc_suspended=false;m_isp_dc_interrupt&=~u32(0x84);isp1161_dc_event(2);return {handshake::ack,0};}
    if(op==0x11){m_isp_usb_clock=bool(flags&1);m_isp_dc_last_sof=m_isp_usb_msec;return {handshake::ack,0};}
    if(op<7||op>9)return {handshake::pid_error,0};
    if(m_isp_dc_suspended)return {handshake::timeout,0};
    transaction tx{address,endpoint,op==7?pid::setup:op==8?pid::out:pid::in,
        bool(flags&4),bool(flags&2),bool(flags&1),length};
    reply result=m_isp_dc_fifo.transfer(tx,out,in,length,m_isp_dc_ep_config,m_isp_dc_ram,isp1161a1::handshake(flags>>4));
    if(m_isp_dc_fifo.event_good||(m_isp_dc_mode&4)||tx.isochronous)isp1161_dc_event(m_isp_dc_fifo.events);
    logerror("DANA_USB_DC_PACKET address=%u ep=%u pid=%u bytes=%u result=%u actual=%u irq=%08x\n",
        address,endpoint,unsigned(tx.direction),length,unsigned(result.status),result.size,m_isp_dc_interrupt);
    return result;
}

isp1161a1::reply alphasdana_state::isp1161_dma_packet(u8 op,u8 flags,u8 const *out,u8 *in,u16 length)
{
    using namespace isp1161a1;
    bool const hc_request=(m_isp_hc_regs16[0x21]&0x10)&&m_isp_hc_fifo_remaining;
    unsigned const ep=(m_isp_dc_dma_cfg>>4)&15;
    bool const dc_write=m_isp_dc_fifo.direction(ep,m_isp_dc_ep_config);
    bool const dc_request=(m_isp_dc_dma_cfg&8)&&(!(m_isp_dc_dma_cfg&0x8000)||m_isp_dc_dma_count)&&ep>1&&m_isp_dc_fifo.capacity[ep]&&
        (dc_write?!(m_isp_dc_fifo.full[ep]&(1U<<m_isp_dc_fifo.cpu_bank[ep])):
                   bool(m_isp_dc_fifo.full[ep]&(1U<<m_isp_dc_fifo.cpu_bank[ep])));
    if(op==0x20)
    {
        in[0]=hc_request;in[1]=dc_request;
        in[2]=hc_request?bool(m_isp_hardware&0x20):!bool(m_isp_hardware&0x20);
        in[3]=dc_request?bool(m_isp_dc_hw&0x40):!bool(m_isp_dc_hw&0x40);
        in[4]=u8(m_isp_hc_fifo_remaining);in[5]=u8(m_isp_hc_fifo_remaining>>8);
        in[6]=u8(m_isp_dc_dma_count);in[7]=u8(m_isp_dc_dma_count>>8);
        return {handshake::ack,8};
    }
    if(op==0x25)
    {
        if(flags&1){m_isp_hc_regs16[0x21]&=~u16(0x10);m_isp_up_irq|=4;}
        if(flags&2){
            if(dc_request&&m_isp_dc_dma_cursor){unsigned const bank=m_isp_dc_fifo.cpu_bank[ep];
                if(dc_write){m_isp_dc_fifo.length[ep][bank]=m_isp_dc_dma_cursor;m_isp_dc_fifo.validate(ep,m_isp_dc_ep_config);}
                else m_isp_dc_fifo.clear(ep,m_isp_dc_ep_config);
            }
            m_isp_dc_dma_cursor=0;m_isp_dc_dma_cfg&=~u16(8);isp1161_dc_event(8);
        }
        isp1161_irq_update(true);return {handshake::ack,0};
    }
    bool const host=op==0x21||op==0x22;
    bool const write=op==0x22||op==0x24;
    unsigned const width=host?2:((m_isp_dc_mode&0x80)?2:1);
    if(length!=width)return {handshake::pid_error,0};
    if(bool(flags&1)!=bool(host?(m_isp_hardware&0x40):(m_isp_dc_hw&0x20)))return {handshake::nak,0};
    word transferred=word(width);
    if(host)
    {
        bool const expected_write=m_isp_hc_regs16[0x21]&1;
        if(!hc_request||write!=expected_write)return {handshake::nak,0};
        u8 const previous=m_isp_cmd;
        m_isp_cmd=u8((m_isp_hc_regs16[0x21]&2)?0x41:0x40)|(write?0x80:0);
        if(write)isp1161_w(0,u16(out[0]|(u16(out[1])<<8)),0xffff);
        else {u16 const value=isp1161_r(0,0xffff);in[0]=u8(value);in[1]=u8(value>>8);}
        m_isp_cmd=previous;
        if(!m_isp_hc_fifo_remaining)m_isp_hc_regs16[0x21]&=~u16(0x10);
    }
    else
    {
        if(!dc_request||write!=dc_write)return {handshake::nak,0};
        unsigned const bank=m_isp_dc_fifo.cpu_bank[ep];
        unsigned const available=write?m_isp_dc_fifo.capacity[ep]:m_isp_dc_fifo.length[ep][bank];
        if(m_isp_dc_dma_cursor>=available)return {handshake::nak,0};
        unsigned const pos=m_isp_dc_fifo.location(ep,bank)+m_isp_dc_dma_cursor;
        unsigned n=std::min<unsigned>(width,available-m_isp_dc_dma_cursor);
        if((m_isp_dc_dma_cfg&0x8000)&&m_isp_dc_dma_count<n)n=m_isp_dc_dma_count;
        if(!n)return {handshake::nak,0};
        if(write){m_isp_dc_ram[pos]=out[0];if(n==2)m_isp_dc_ram[pos+1]=out[1];}
        else {in[0]=m_isp_dc_ram[pos];in[1]=n==2?m_isp_dc_ram[pos+1]:0;}
        transferred=word(n);
        m_isp_dc_dma_cursor+=u16(n);
        m_isp_dc_dma_cfg=(m_isp_dc_dma_cfg&~u16(0x100))|(n==2?0x100:0);
        if(m_isp_dc_dma_cfg&0x8000)m_isp_dc_dma_count-=u16(n);
        bool const eot=((m_isp_dc_dma_cfg&0x8000)&&!m_isp_dc_dma_count)||
            (!write&&m_isp_dc_dma_cursor>=available&&(m_isp_dc_fifo.iso(ep,m_isp_dc_ep_config)||((m_isp_dc_dma_cfg&0x4000)&&available<m_isp_dc_fifo.capacity[ep])));
        if(eot)
        {
            if(write){m_isp_dc_fifo.length[ep][bank]=m_isp_dc_dma_cursor;m_isp_dc_fifo.validate(ep,m_isp_dc_ep_config);}
            else m_isp_dc_fifo.clear(ep,m_isp_dc_ep_config);
            m_isp_dc_dma_cursor=0;m_isp_dc_dma_cfg&=~u16(8);isp1161_dc_event(8);
        }
        else if(m_isp_dc_dma_cursor>=available)
        {
            if(write){m_isp_dc_fifo.length[ep][bank]=m_isp_dc_dma_cursor;m_isp_dc_fifo.validate(ep,m_isp_dc_ep_config);}
            else m_isp_dc_fifo.clear(ep,m_isp_dc_ep_config);
            m_isp_dc_dma_cursor=0;
        }
    }
    isp1161_irq_update(true);return {handshake::ack,transferred};
}
