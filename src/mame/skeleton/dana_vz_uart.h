// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
#ifndef MAME_SKELETON_DANA_VZ_UART_H
#define MAME_SKELETON_DANA_VZ_UART_H
#pragma once

#include "diserial.h"
#include "imagedev/bitbngr.h"

// Both endpoints use MAME's bit shifter, framing, parity and virtual clocks.
// The physical SIR codec is between those shifters, never between their FIFOs.
class dana_serial_phy : public device_t, public device_serial_interface
{
public:
    auto output() { return m_output.bind(); }
    void pin_w(int state)
    {
        state=!!state;
        if (m_sir)
        {
            bool const active=!(state ^ m_rxpol);
            if (active && !m_pulse_in)
            {
                m_pulse_start=machine().time();
                receive_bit(0);
                m_expand->adjust(m_period);
            }
            if (!active && m_pulse_in && machine().time()-m_pulse_start<attotime::from_double(3.0/1843200.0))
            { receive_register_reset(); receive_bit(1); m_expand->adjust(attotime::never); }
            m_pulse_in=active;
        }
        else receive_bit(state ^ m_rxpol);
        m_pin=state;
    }
    int pin_r() const { return m_pin; }
    int tx_r() const { return m_txpin; }
protected:
    dana_serial_phy(const machine_config &config,device_type type,const char *tag,device_t *owner,u32 clock)
        : device_t(config,type,tag,owner,clock),device_serial_interface(config,*this),m_output(*this) {}
    virtual void device_start() override
    {
        m_release=timer_alloc(FUNC(dana_serial_phy::release),this);
        m_expand=timer_alloc(FUNC(dana_serial_phy::expand),this);
        set_rate(attotime::never);
        m_txclock=timer_alloc(FUNC(dana_serial_phy::tx_tick),this);
        m_rxclock=timer_alloc(FUNC(dana_serial_phy::rx_tick),this);
        save_item(NAME(m_sir)); save_item(NAME(m_sirtx)); save_item(NAME(m_rxpol)); save_item(NAME(m_txpol));
        save_item(NAME(m_pin)); save_item(NAME(m_txpin)); save_item(NAME(m_pulse_in));
        save_item(NAME(m_sync)); save_item(NAME(m_normal)); save_item(NAME(m_txphase)); save_item(NAME(m_txactive));
        save_item(NAME(m_txleft)); save_item(NAME(m_rxleft));
        save_item(NAME(m_period)); save_item(NAME(m_width)); save_item(NAME(m_pulse_start));
    }
    void phy_reset()
    {
        m_release->adjust(attotime::never); m_expand->adjust(attotime::never);
        m_pulse_in=false; m_normal=1; m_txactive=false; m_txphase=false;
        m_txclock->adjust(attotime::never); m_rxclock->adjust(attotime::never);
        receive_register_reset(); transmit_register_reset(); rx_w(1); tx_clock_w(0);
        if(m_sync && !m_period.is_never()) m_rxclock->adjust(m_period,0,m_period);
        drive(m_sirtx ? m_txpol : !m_txpol);
    }
    // Keep the MAME framing/shift registers, but own the VZ clocks. Updating
    // a PLL or stopping SYSCLK must not reset those shift registers.
    void receive_bit(int bit)
    {
        m_normal=bit;
        if(m_sync) return;
        bool const was=is_receive_register_synchronized();
        rx_w(bit);
        if(!was && is_receive_register_synchronized() && !m_period.is_never())
            m_rxclock->adjust(m_period*3/2,0,m_period);
    }
    void start_frame(u8 data)
    {
        transmit_register_setup(data);
        if(!m_txactive)
        {
            m_txactive=true; m_txphase=false; tx_clock_w(0);
            if(!m_period.is_never()) m_txclock->adjust(m_period/2,0,m_period/2);
        }
    }
    void period_w(attotime period,bool sync=false)
    {
        attotime const old=m_period;
        if(!old.is_never())
        {
            if(m_txactive) m_txleft=m_txclock->remaining().as_double()/old.as_double();
            if(m_sync || is_receive_register_synchronized()) m_rxleft=m_rxclock->remaining().as_double()/old.as_double();
        }
        bool const new_sync=sync && !m_sync;
        m_period=period; m_sync=sync;
        m_txclock->adjust(attotime::never);m_rxclock->adjust(attotime::never);
        if(period.is_never()) return;
        if(m_txactive) m_txclock->adjust(attotime::from_double(period.as_double()*m_txleft),0,period/2);
        if(sync || is_receive_register_synchronized())
        {
            double const fraction=new_sync ? 1.0-std::fmod(machine().time().as_double()/period.as_double(),1.0) : m_rxleft;
            m_rxclock->adjust(attotime::from_double(period.as_double()*fraction),0,period);
        }
    }
    TIMER_CALLBACK_MEMBER(tx_tick)
    {
        m_txphase=!m_txphase; tx_clock_w(m_txphase);
        if(is_transmit_register_empty()) {m_txactive=false;m_txclock->adjust(attotime::never);}
    }
    TIMER_CALLBACK_MEMBER(rx_tick)
    {
        receive_register_update_bit(m_normal);
        if(is_receive_register_full())
        {if(!m_sync)m_rxclock->adjust(attotime::never); rcv_complete();}
    }
    virtual void physical_out(int state) {}
    void drive(int state) { m_txpin=!!state; m_output(m_txpin); physical_out(m_txpin); }
    void send_bit(int bit)
    {
        if (m_sirtx)
        {
            m_release->adjust(attotime::never);
            drive((!bit) ^ m_txpol);
            if (!bit) m_release->adjust(m_width);
        }
        else drive(bit ^ m_txpol);
    }
    TIMER_CALLBACK_MEMBER(release) { drive(m_txpol); }
    TIMER_CALLBACK_MEMBER(expand) { receive_bit(1); }
    bool m_sir=false,m_sirtx=false,m_rxpol=false,m_txpol=false,m_pulse_in=false;
    int m_pin=1,m_txpin=1;
    attotime m_period=attotime::never,m_width=attotime::never,m_pulse_start=attotime::zero;
    devcb_write_line m_output;
    emu_timer *m_release=nullptr,*m_expand=nullptr,*m_txclock=nullptr,*m_rxclock=nullptr;
    bool m_sync=false,m_txphase=false,m_txactive=false;
    int m_normal=1;
    double m_txleft=0.5,m_rxleft=1.0;
};

class dana_serial_peer_device;
DECLARE_DEVICE_TYPE(DANA_SERIAL_PEER,dana_serial_peer_device)

// An explicitly mounted MAME byte stream is an independent serial peer.
// Baud/framing/SIR are peer settings, not copied from the guest UART.
class dana_serial_peer_device : public dana_serial_phy
{
public:
    dana_serial_peer_device(const machine_config &config,const char *tag,device_t *owner,u32 clock=0)
        : dana_serial_phy(config,DANA_SERIAL_PEER,tag,owner,clock),m_stream(*this,"stream"),
          m_baud(*this,"BAUD"),m_format(*this,"FORMAT"),m_lines(*this,"LINES") {}
    void pin_w(int state) { if(m_stream->is_open()) dana_serial_phy::pin_w(state); }
    auto cts() { return m_cts.bind(); }
    void rts_w(int state) { m_rts=!!state; }
    void update(int state) { configure(); }
    void optical(bool value) { m_default_sir=value; }
    bool optical_mode() const { return m_sir; }
protected:
    virtual void device_add_mconfig(machine_config &config) override { BITBANGER(config,m_stream); }
    virtual ioport_constructor device_input_ports() const override;
    virtual void device_start() override
    {
        dana_serial_phy::device_start();
        m_poll=timer_alloc(FUNC(dana_serial_peer_device::poll),this);
        machine().save().register_postload(save_prepost_delegate(FUNC(dana_serial_peer_device::detach),this));
        save_item(NAME(m_break)); save_item(NAME(m_rts)); save_item(NAME(m_queue)); save_item(NAME(m_head)); save_item(NAME(m_count));
    }
    virtual void device_reset() override
    {
        m_head=m_count=0; m_rts=1; configure(); phy_reset();
        m_poll->adjust(attotime::from_msec(1),0,attotime::from_msec(1));
    }
    void detach()
    {
        m_stream->unload(); m_head=m_count=0; phy_reset(); m_cts(1);
    }
    void configure()
    {
        u32 const f=m_format->read();
        m_sir=(f&8) ? bool(f&16) : m_default_sir; m_sirtx=m_sir;
        period_w(attotime::from_hz(m_baud->read())); m_width=attotime::from_nsec(1630);
        set_data_frame(1,(f&1)?7:8,(f&2)?((f&4)?PARITY_ODD:PARITY_EVEN):PARITY_NONE,STOP_BITS_1);

    }
    TIMER_CALLBACK_MEMBER(poll)
    {
        u32 const lines=m_lines->read();
        m_cts((lines&1) || !m_stream->is_open());
        // The peer's break switch drives a real line, not a receiver flag.
        bool const was=m_break; m_break=bool(lines&4);
        if(m_break || was) drive(m_break?0:1);
        if (!m_stream->is_open() || ((lines&2) && m_rts)) return;
        if (!m_count) { m_head=0; m_count=m_stream->input(m_queue,sizeof(m_queue)); }
        if (m_count && is_transmit_register_empty())
        { start_frame(m_queue[m_head++] & ((m_format->read()&1)?0x7f:0xff)); --m_count; }
    }
    virtual void tra_callback() override
    { int const bit=transmit_register_get_data_bit(); send_bit(m_break?0:(m_stream->is_open()?bit:1)); }
    virtual void rcv_complete() override
    {
        receive_register_extract();
        if (m_stream->is_open()) m_stream->output(get_received_char());
    }
private:
    required_device<bitbanger_device> m_stream;
    required_ioport m_baud,m_format,m_lines;
    devcb_write_line m_cts{*this};
    bool m_default_sir=false,m_break=false;
    int m_rts=1;
    u8 m_queue[256]={};
    u16 m_head=0,m_count=0;
    emu_timer *m_poll=nullptr;
};

static INPUT_PORTS_START(dana_serial_peer)
    PORT_START("BAUD")
    PORT_CONFNAME(0x0003ffff,9600,"Serial peer baud") PORT_WRITE_LINE_DEVICE_MEMBER(DEVICE_SELF,FUNC(dana_serial_peer_device::update))
    PORT_CONFSETTING(1200,"1200") PORT_CONFSETTING(2400,"2400") PORT_CONFSETTING(4800,"4800")
    PORT_CONFSETTING(9600,"9600") PORT_CONFSETTING(19200,"19200") PORT_CONFSETTING(38400,"38400")
    PORT_CONFSETTING(57600,"57600") PORT_CONFSETTING(115200,"115200")
    PORT_START("FORMAT")
    PORT_CONFNAME(1,0,"Serial peer data bits") PORT_WRITE_LINE_DEVICE_MEMBER(DEVICE_SELF,FUNC(dana_serial_peer_device::update))
    PORT_CONFSETTING(0,"8") PORT_CONFSETTING(1,"7")
    PORT_CONFNAME(6,0,"Serial peer parity") PORT_WRITE_LINE_DEVICE_MEMBER(DEVICE_SELF,FUNC(dana_serial_peer_device::update))
    PORT_CONFSETTING(0,"None") PORT_CONFSETTING(2,"Even") PORT_CONFSETTING(6,"Odd")
    PORT_CONFNAME(24,0,"Serial peer physical link") PORT_WRITE_LINE_DEVICE_MEMBER(DEVICE_SELF,FUNC(dana_serial_peer_device::update))
    PORT_CONFSETTING(0,"Dana default (UART1 NRZ, UART2 optical SIR)")
    PORT_CONFSETTING(8,"NRZ") PORT_CONFSETTING(24,"Optical SIR")
    PORT_START("LINES")
    PORT_CONFNAME(1,0,"Serial peer CTS") PORT_CONFSETTING(0,"Ready when mounted") PORT_CONFSETTING(1,"Busy")
    PORT_CONFNAME(2,2,"Serial peer obey RTS") PORT_CONFSETTING(0,"No") PORT_CONFSETTING(2,"Yes")
    PORT_CONFNAME(4,0,"Serial peer break (NRZ)") PORT_CONFSETTING(0,"Released") PORT_CONFSETTING(4,"Asserted")
INPUT_PORTS_END
inline ioport_constructor dana_serial_peer_device::device_input_ports() const { return INPUT_PORTS_NAME(dana_serial_peer); }

class dana_vz_uart_device;
DECLARE_DEVICE_TYPE(DANA_VZ_UART,dana_vz_uart_device)

class dana_vz_uart_device : public dana_serial_phy
{
public:
    dana_vz_uart_device(const machine_config &config,const char *tag,device_t *owner,u32 clock=0)
        : dana_serial_phy(config,DANA_VZ_UART,tag,owner,clock) {}
    auto clock_changed() { return m_clock_changed.bind(); }
    bool uclk_output() const { return m_regs[1]&0x2000; }
    u32 uclk_hz() const { return m_period.is_never() ? 0 : u32(((m_regs[0]&0x1000)?1:16)/m_period.as_double()+0.5); }
    auto irq() { return m_irq.bind(); }
    auto rts() { return m_rts.bind(); }
    void channel(unsigned value) { m_channel=value; }
    void sysclk(u32 hz) { if (hz!=m_sysclk) { m_sysclk=hz; configure(); kick(); } }
    void external_clock(u32 hz) { if(hz!=m_external) {m_external=hz; configure(); kick();} }
    void cts_w(int state)
    {
        if (m_cts!=!!state) m_regs[3]|=0x100;
        m_cts=!!state; status(); kick();
    }
    void rxpin_w(int state)
    { if ((m_regs[0]&0xc000)==0xc000 && !(m_regs[4]&0x1010)) pin_w(state); }
    int rts_r() const
    {
        if (!(m_regs[4]&0x80)) return !(m_regs[4]&0x40);
        unsigned const threshold=m_channel==1 ? 8 : ((m_regs[4]&0x100)?63:4*(m_regs[6]&15));
        return threshold && m_rxcount>=threshold;
    }
    u16 read(offs_t offset,u16 mask=0xffff)
    {
        if(offset==2)
        {
            u16 value=rx_status() | (m_rxcount ? m_rx[m_rxhead] : m_last_rx);
            if ((mask&0xff) && !machine().side_effects_disabled() && m_rxcount)
            {
                m_last_rx=m_rx[m_rxhead]&0xff; m_rxhead=(m_rxhead+1)%rx_size(); --m_rxcount;
                m_old=false; old_schedule(); status();
            }
            return value;
        }
        if(offset==3) return tx_status();
        return offset<7 ? m_regs[offset] : 0;
    }
    void write(offs_t offset,u16 data,u16 mask=0xffff)
    {
        static constexpr u16 writable[7]={0xffff,0x2f3f,0,0x1900,0xfcfc,0x87ff,0x0f0f};
        if(offset>=7 || offset==2 || (offset==6 && m_channel==1)) return;
        u16 const old=m_regs[offset];
        u16 const bits=mask & (offset==4 && m_channel==2 ? 0xfdfc : writable[offset]);
        m_regs[offset]=(old&~bits)|(data&bits);
        if(offset==0)
        {
            if ((old&0xc000)!=(m_regs[0]&0xc000))
            {
                m_rxhead=m_rxcount=0; m_old=false; m_old_timer->adjust(attotime::never); receive_register_reset();
            }
            if (!(m_regs[0]&0x8000) || !(m_regs[0]&0x2000)) m_txhead=m_txcount=0;
        }
        if(offset==0 || offset==1 || offset==4 || offset==5) configure();
        if(offset==3 && (mask&0xff) && (m_regs[0]&0xa000)==0xa000 && m_txcount<tx_size())
        { m_tx[(m_txhead+m_txcount)%tx_size()]=data; ++m_txcount; }
        if(offset==3 && ((old^m_regs[3])&0x1000) && !m_sirtx)
        { if(m_regs[3]&0x1000) drive(m_txpol); else if(!m_busy) send_bit(1); }
        status(); kick();
        if(offset==0 || offset==1 || offset==4 || offset==5) m_clock_changed(1);
    }
    void refresh() { status(); }
protected:
    virtual void device_start() override
    {
        dana_serial_phy::device_start();
        m_old_timer=timer_alloc(FUNC(dana_vz_uart_device::old_timeout),this);
        m_done=timer_alloc(FUNC(dana_vz_uart_device::done),this);
        save_item(NAME(m_regs)); save_item(NAME(m_rx)); save_item(NAME(m_tx));
        save_item(NAME(m_rxhead)); save_item(NAME(m_rxcount)); save_item(NAME(m_txhead)); save_item(NAME(m_txcount));
        save_item(NAME(m_last_rx)); save_item(NAME(m_old)); save_item(NAME(m_busy)); save_item(NAME(m_cts));
        save_item(NAME(m_sysclk)); save_item(NAME(m_external)); save_item(NAME(m_frame)); save_item(NAME(m_bit));
        save_item(NAME(m_stop_left)); save_item(NAME(m_old_left));
        save_item(NAME(m_config)); save_item(NAME(m_deferred));
        machine().save().register_postload(save_prepost_delegate(FUNC(dana_vz_uart_device::refresh),this));
    }
    virtual void device_reset() override
    {
        std::fill(std::begin(m_regs),std::end(m_regs),0);
        m_regs[1]=2; m_regs[6]=0x0102;
        m_rxhead=m_rxcount=m_txhead=m_txcount=m_last_rx=0;
        m_old=m_busy=m_deferred=false; m_cts=1;
        m_old_timer->adjust(attotime::never); m_done->adjust(attotime::never);
        m_config=~u64(0); configure(); phy_reset(); status();
    }
    unsigned rx_size() const { return m_channel==1 ? 12 : 64; }
    unsigned tx_size() const { return m_channel==1 ? 8 : 64; }
    u16 rx_status() const
    {
        unsigned const threshold=m_channel==1 ? 8 : 4*(m_regs[6]&15);
        return (m_rxcount==rx_size()?0x8000:0) | (threshold && m_rxcount>=threshold?0x4000:0)
            | (m_rxcount?0x2000:0) | (m_old && m_rxcount?0x1000:0);
    }
    u16 tx_status() const
    {
        // UTX FIFO flags reset low until the UART module is enabled.
        // CTS remains the actual pin level, independently of the enable.
        if(!(m_regs[0]&0x8000)) return (m_regs[3]&0x1900) | (m_busy?0x400:0) | (m_cts?0x200:0);
        unsigned const free=tx_size()-m_txcount;
        bool const half=m_channel==1 ? m_txcount<4 : ((m_regs[6]>>8)&15) && free>=4*((m_regs[6]>>8)&15);
        return (m_txcount?0:0x8000) | (half?0x4000:0) | (free?0x2000:0)
            | (m_regs[3]&0x1900) | (m_busy || m_txcount?0x400:0) | (m_cts?0x200:0);
    }
    void status()
    {
        u16 const r=rx_status(),t=tx_status(),c=m_regs[0];
        bool const rx=(c&0xc000)==0xc000 && (((c&0x80)&&(r&0x1000))||((c&0x20)&&(r&0x8000))
            ||((c&0x10)&&(r&0x4000))||((c&8)&&(r&0x2000)));
        bool const tx=(c&0xa000)==0xa000 && (((c&4)&&(t&0x8000))||((c&2)&&(t&0x4000))||((c&1)&&(t&0x2000)));
        m_irq((c&0x8000) && (rx || tx || ((c&0x40)&&(t&0x100))));
        m_rts(rts_r());
    }
    void configure()
    {
        // Changes to masks and enables must never reset a shifting frame.
        u64 const config=u64(m_regs[0]&0x1f00) | (u64(m_regs[1])<<16) | (u64(m_regs[4]&0xfc3c)<<32) | (u64(m_regs[5])<<48);
        double const source=(m_regs[1]&0x800 || m_regs[4]&0x4000) ? ((m_regs[1]&0x2000)?0:m_external) : m_sysclk;
        unsigned const select=(m_regs[5]>>8)&7;
        double const noninteger=select==7 ? (m_channel==2?1.0:0.0)
            : double(1U<<(select+1))+double(m_regs[5]&255)/double(1U<<(7-select));
        double const divisor=(m_regs[5]&0x8000) ? noninteger : (65-(m_regs[1]&63));
        double const baud=(m_regs[4]&0x8800) ? 0 : (m_regs[4]&0x4000) ? source : divisor ? source/divisor/(1U<<((m_regs[1]>>8)&7))/((m_regs[0]&0x1000)?1:16) : 0;
        attotime const period=baud>0 ? attotime::from_double(1.0/baud) : attotime::never;
        if(config==m_config && period==m_period) {m_deferred=false;return;}
        if(m_busy && config!=m_config) {m_deferred=true;return;}
        if(!m_period.is_never())
        {
            // Preserve the fractional final stop bit and old-data timeout.
            double const ratio=period.is_never()?0:period.as_double()/m_period.as_double();
            if(m_done->enabled()) {m_stop_left=m_done->remaining().as_double()/m_period.as_double();m_done->adjust(ratio?attotime::from_double(m_done->remaining().as_double()*ratio):attotime::never);}
            if(m_old_timer->enabled()) {m_old_left=m_old_timer->remaining().as_double()/m_period.as_double();m_old_timer->adjust(ratio?attotime::from_double(m_old_timer->remaining().as_double()*ratio):attotime::never);}
        }
        else if(m_period.is_never() && !period.is_never())
        {
            if(m_busy && !m_txactive) m_done->adjust(attotime::from_double(period.as_double()*m_stop_left));
            if(m_rxcount && !m_old) m_old_timer->adjust(attotime::from_double(period.as_double()*m_old_left));
        }
        m_config=config; period_w(period,bool(m_regs[0]&0x1000));
        m_sir=bool(m_regs[4]&0x20); m_sirtx=bool(m_regs[4]&0x420); m_rxpol=bool(m_regs[4]&8); m_txpol=bool(m_regs[4]&4);
        m_frame=m_regs[0];
        // 1.63 us in the manual is the rounded 3/1.8432 MHz SIR pulse.
        m_width=m_sysclk && noninteger ? attotime::from_double(3.0*noninteger/m_sysclk) : period*3/16;
        set_data_frame(1,(m_frame&0x100)?8:7,(m_frame&0x800)?((m_frame&0x400)?PARITY_ODD:PARITY_EVEN):PARITY_NONE,(m_frame&0x200)?STOP_BITS_2:STOP_BITS_1);
        m_deferred=false;
        if(!m_busy) send_bit((m_regs[3]&0x1000)?0:1);
    }
    void kick()
    {
        if(m_busy || !m_txcount || (m_regs[0]&0xa000)!=0xa000 || (!(m_regs[3]&0x800) && m_cts) || m_period.is_never()) return;
        if(m_deferred) configure();
        u8 const data=m_tx[m_txhead]; m_txhead=(m_txhead+1)%tx_size(); --m_txcount;
        m_busy=true; m_bit=0; start_frame(data & ((m_frame&0x100)?0xff:0x7f)); status();
    }
    virtual void physical_out(int state) override
    {
        if ((m_regs[0]&0xc000)!=0xc000) return;
        if (m_sir && (m_regs[4]&0x10)) pin_w(!state);
        if (!m_sirtx && (m_regs[4]&0x1000)) receive_bit(state ^ m_txpol);
    }
    virtual void tra_callback() override
    {
        int bit=transmit_register_get_data_bit();
        if ((m_frame&0x800) && (m_regs[4]&0x2000) && m_bit==((m_frame&0x100)?9:8)) bit^=1;
        ++m_bit;
        if (m_regs[3]&0x1000) bit=0;
        send_bit(bit);
        if ((m_regs[0]&0xc000)==0xc000 && m_sirtx && (m_regs[4]&0x1000)) receive_bit(bit);
    }
    virtual void tra_complete() override
    {
        if(m_txcount && (m_regs[0]&0xa000)==0xa000 && ((m_regs[3]&0x800)||!m_cts) && !m_deferred)
        { m_busy=false; kick(); }
        else m_done->adjust(m_period);
    }
    TIMER_CALLBACK_MEMBER(done)
    { m_busy=false; if(m_deferred)configure(); status(); kick(); }
    virtual void rcv_complete() override
    {
        receive_register_extract();
        if ((m_regs[0]&0xc000)!=0xc000) return;
        u16 data=get_received_char();
        if(is_receive_parity_error()) data|=0x100;
        if(is_receive_framing_error()) data|=0x400;
        if(is_receive_framing_error() && !(data&255)) data|=0x200;
        if(m_rxcount==rx_size())
        { m_rxhead=(m_rxhead+1)%rx_size(); --m_rxcount; data|=0x800; }
        m_rx[(m_rxhead+m_rxcount)%rx_size()]=data; ++m_rxcount;
        m_old=false; old_schedule(); status();
    }
    void old_schedule()
    { m_old_timer->adjust(m_rxcount ? m_period*30 : attotime::never); }
    TIMER_CALLBACK_MEMBER(old_timeout) { m_old=bool(m_rxcount); status(); }
private:
    devcb_write_line m_irq{*this},m_rts{*this},m_clock_changed{*this};
    unsigned m_channel=1;
    u32 m_sysclk=33'161'216,m_external=0;
    u16 m_regs[7]={},m_rx[64]={};
    u8 m_tx[64]={};
    u16 m_rxhead=0,m_rxcount=0,m_txhead=0,m_txcount=0,m_last_rx=0,m_frame=0,m_bit=0;
    bool m_old=false,m_busy=false,m_deferred=false;
    int m_cts=1;
    u64 m_config=~u64(0);
    double m_stop_left=1,m_old_left=30;
    emu_timer *m_old_timer=nullptr,*m_done=nullptr;
};
#endif
