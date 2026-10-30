// license:BSD-3-Clause
// Independent packet-level USB functions and ISP1161A1 device FIFO semantics.
// Manufacturer source: Philips ISP1161A1 Rev03, sections 11-13.
// No Linux or QEMU implementation code is incorporated.
#pragma once
#include "isp1161_ptd.h"
#include <array>
#include <algorithm>
#include <cstdint>
#include <cstring>

namespace isp1161a1 {
using byte=std::uint8_t;
using word=std::uint16_t;

// Explicitly attached downstream function. kind=1 printer, kind=2 diagnostic
// loopback (bulk, interrupt and ISO). This is never the Dana upstream identity.
struct usb_function {
    byte kind=0,address=0,configuration=0,pending_address=0;
    byte pending_configuration=0xff;
    byte control_direction=0,control_pending=0,control_stall=0,fault_status=0,fault_count=0;
    byte toggle_in[16]={},toggle_out[16]={},halt_in[16]={},halt_out[16]={};
    byte control[512]={},loopback[4][1024]={};
    word control_size=0,control_cursor=0,control_expected=0,loopback_size[4]={};
    std::uint32_t accepted_bytes=0,packets=0;

    void reset() {
        byte const attached=kind;
        *this=usb_function{};
        kind=attached;
    }
    static word le16(byte const *p) {return word(p[0]|(word(p[1])<<8));}
    void response(byte const *p,unsigned count,unsigned requested) {
        control_size=word(std::min({count,requested,unsigned(sizeof(control))}));
        std::copy_n(p,control_size,control);
    }
    void descriptor(word value,word requested) {
        byte const type=value>>8,index=byte(value);
        static constexpr byte device[]={18,1,0x10,1,0,0,0,64,0xff,0xff,0x61,0x11,0,1,1,2,0,1};
        static constexpr byte printer_config[]={
            9,2,32,0,1,1,0,0x80,25,9,4,0,0,2,7,1,2,0,
            7,5,1,2,64,0,0,7,5,0x82,2,64,0,0};
        static constexpr byte loop_config[]={
            9,2,60,0,1,1,0,0x80,25,9,4,0,0,6,0xff,0,0,0,
            7,5,1,2,64,0,0,7,5,0x81,2,64,0,0,
            7,5,2,3,8,0,1,7,5,0x82,3,8,0,1,
            7,5,3,1,0xff,3,1,7,5,0x83,1,0xff,3,1};
        if(type==1)response(device,sizeof(device),requested);
        else if(type==2) {
            if(kind==1)response(printer_config,sizeof(printer_config),requested);
            else response(loop_config,sizeof(loop_config),requested);
        } else if(type==3) {
            if(!index) {
                byte const languages[]={4,3,9,4};response(languages,4,requested);
            } else {
                char const *s=index==1?"DANA-emu":kind==1?"Virtual USB Printer":"USB packet loopback";
                unsigned const n=unsigned(std::strlen(s));
                control[0]=byte(2+2*n);control[1]=3;
                for(unsigned i=0;i<n;++i){control[2+2*i]=byte(s[i]);control[3+2*i]=0;}
                control_size=word(std::min(unsigned(control[0]),unsigned(requested)));
            }
        } else control_stall=1;
    }
    reply setup(byte const *data,word count) {
        if(count!=8)return {handshake::pid_error,0};
        control_direction=data[0]>>7;control_pending=1;control_stall=0;
        control_cursor=control_size=0;control_expected=le16(data+6);
        pending_address=address;pending_configuration=0xff;
        halt_in[0]=halt_out[0]=0;toggle_in[0]=toggle_out[0]=1;
        byte const request=data[1],recipient=data[0]&31,type=data[0]&0x60;
        word const value=le16(data+2),index=le16(data+4);
        if(type==0) {
            switch(request) {
            case 6:descriptor(value,control_expected);break;
            case 5:if(value>127)control_stall=1;else pending_address=byte(value);break;
            case 9:if(value>1)control_stall=1;else pending_configuration=byte(value);break;
            case 8:control[0]=configuration;control_size=word(std::min<unsigned>(1,control_expected));break;
            case 0:control[0]=recipient==2?((index&0x80)?halt_in[index&15]:halt_out[index&15]):0;
                control[1]=0;control_size=word(std::min<unsigned>(2,control_expected));break;
            case 1:case 3:
                if(recipient==2&&value==0) {
                    ((index&0x80)?halt_in[index&15]:halt_out[index&15])=request==3;
                    ((index&0x80)?toggle_in[index&15]:toggle_out[index&15])=0;
                } else control_stall=1;
                break;
            case 10:control[0]=0;control_size=word(std::min<unsigned>(1,control_expected));break;
            case 11:if(value)control_stall=1;break;
            default:control_stall=1;break;
            }
        } else if(type==0x20&&kind==1) {
            if(request==0) {
                static constexpr char id[]="MFG:DANA-emu;MDL:Virtual USB Printer;CMD:PCL,POSTSCRIPT;CLS:PRINTER;";
                unsigned const n=sizeof(id)-1;
                control[0]=byte((n+2)>>8);control[1]=byte(n+2);
                std::copy_n(reinterpret_cast<byte const *>(id),n,control+2);
                control_size=word(std::min<unsigned>(n+2,control_expected));
            } else if(request==1) {
                control[0]=0x18;control_size=word(std::min<unsigned>(1,control_expected));
            } else if(request==2) {
                std::fill_n(toggle_in,16,0);std::fill_n(toggle_out,16,0);
            } else control_stall=1;
        } else if(type==0x40&&kind==2&&request==0xf0) {fault_status=byte(value);fault_count=byte(index);}
        else control_stall=1;
        return {handshake::ack,8};
    }
    template<class Print>
    reply transfer(transaction const &tx,byte const *out,byte *in,word count,Print&& print) {
        ++packets;
        if(!kind||tx.address!=address)return {handshake::timeout,0};
        unsigned const ep=tx.endpoint;
        if(ep>15)return {handshake::stall,0};
        if(tx.direction==pid::setup) {
            if(ep||!out)return {handshake::stall,0};
            return setup(out,count);
        }
        if(ep==0) {
            if(control_stall)return {handshake::stall,0};
            if(!control_pending)return {handshake::nak,0};
            if(tx.direction==pid::in) {
                if(tx.toggle!=bool(toggle_in[0]))return {handshake::toggle_mismatch,0};
                word const n=word(std::min<unsigned>(count,control_size-control_cursor));
                if(n)std::copy_n(control+control_cursor,n,in);
                control_cursor+=n;toggle_in[0]^=1;
                if(!control_direction) {
                    address=pending_address;control_pending=0;
                    if(pending_configuration!=0xff){configuration=pending_configuration;
                        for(unsigned i=1;i<16;++i)toggle_in[i]=toggle_out[i]=halt_in[i]=halt_out[i]=0;}
                }
                return {handshake::ack,n};
            }
            if(tx.toggle!=bool(toggle_out[0]))return {handshake::ack,count};
            toggle_out[0]^=1;
            if(control_direction&&count==0)control_pending=0;
            return {handshake::ack,count};
        }
        if(!configuration)return {handshake::nak,0};
        if(fault_count){--fault_count;return {handshake(fault_status),0};}
        bool const input=tx.direction==pid::in;
        if((input?halt_in[ep]:halt_out[ep]))return {handshake::stall,0};
        if(kind==1&&(ep!=(input?2U:1U)||tx.isochronous))return {handshake::stall,0};
        if(kind==2&&(ep>3||tx.isochronous!=(ep==3)))return {handshake::stall,0};
        byte &toggle=input?toggle_in[ep]:toggle_out[ep];
        if(!tx.isochronous&&tx.toggle!=bool(toggle))
            return {input?handshake::toggle_mismatch:handshake::ack,input?word(0):count};
        byte *const channel=loopback[ep];
        word &available=loopback_size[ep];
        if(input) {
            if(!available)return {handshake::nak,0};
            word const n=std::min(count,available);
            std::copy_n(channel,n,in);
            std::move(channel+n,channel+available,channel);
            available-=n;
            if(!tx.isochronous)toggle^=1;
            return {handshake::ack,n};
        }
        if(kind==1) {
            for(unsigned i=0;i<count;++i)if(!print(out[i]))return {handshake::nak,0};
            accepted_bytes+=count;
        } else {
            if(available+count>1024)return {handshake::nak,0};
            std::copy_n(out,count,channel+available);available+=count;
        }
        if(!tx.isochronous)toggle^=1;
        return {handshake::ack,count};
    }
};

// Additional metadata for the pre-existing, independent 2462-byte DC SRAM.
// All payload is stored in the caller's SRAM, not in synthetic endpoint replies.
struct dc_endpoints {
    word base[16]={},capacity[16]={},length[16][2]={};
    byte full[16]={},cpu_bank[16]={},usb_bank[16]={},toggle[16]={},error[16]={};
    byte stalled[16]={},error_pending[16]={},setup_pending=0,setup_ack=0,overwrite=0,event_good=0;
    byte active_address=0,pending_address=0,address_pending=0,enabled=0;
    byte port_mode=0,port_ep=0,allocation_valid=0;
    word port_cursor=0,frame=0;
    std::uint32_t events=0;
    bool direction(unsigned ep,word const *config)const {return ep==1||(ep>1&&(config[ep]&0x40));}
    bool iso(unsigned ep,word const *config)const {return ep>1&&(config[ep]&0x10);}
    unsigned banks(unsigned ep,word const *config)const {return ep>1&&(config[ep]&0x20)?2:1;}
    void flush(unsigned ep) {
        full[ep]=cpu_bank[ep]=usb_bank[ep]=toggle[ep]=0;
        length[ep][0]=length[ep][1]=0;error[ep]=error_pending[ep]=0;
    }
    bool allocate(word const *config) {
        static constexpr word iso_size[]={16,32,48,64,96,128,160,192,256,320,384,512,640,768,896,1023};
        unsigned offset=0,noniso=0;
        byte const control_toggle[2]={toggle[0],toggle[1]};
        allocation_valid=0;
        for(unsigned ep=0;ep<16;++ep) {
            flush(ep);capacity[ep]=0;base[ep]=word(offset);
            if(!(config[ep]&0x80))continue;
            unsigned size=64;
            if(ep>1) {
                unsigned const code=config[ep]&15;
                if(iso(ep,config))size=iso_size[code];
                else {if(code>3)return false;size=8U<<code;}
            }
            unsigned const bytes=size*banks(ep,config);
            if(offset+bytes>2462)return false;
            if(!iso(ep,config)){noniso+=bytes;if(noniso>512)return false;}
            capacity[ep]=word(size);offset+=bytes;
        }
        if(setup_ack||setup_pending){toggle[0]=control_toggle[0];toggle[1]=control_toggle[1];}
        allocation_valid=1;return true;
    }
    word status(unsigned ep)const {
        return word((stalled[ep]?0x80:0)|((full[ep]&2)?0x40:0)|
            ((full[ep]&1)?0x20:0)|(toggle[ep]?0x10:0)|
            ((ep<2&&overwrite)?8:0)|((ep<2&&setup_pending)?4:0)|
            (cpu_bank[ep]?2:0));
    }
    unsigned location(unsigned ep,unsigned bank)const {return base[ep]+bank*capacity[ep];}
    void select(unsigned ep,bool write) {port_ep=byte(ep);port_mode=write?1:2;port_cursor=0;}
    word read(byte const *ram) {
        unsigned const ep=port_ep,bank=cpu_bank[ep];
        word const cursor=port_cursor;port_cursor+=2;
        if(!allocation_valid||!capacity[ep]||!(full[ep]&(1U<<bank)))return 0;
        if(!cursor)return length[ep][bank];
        if(cursor-2>=length[ep][bank])return 0;
        unsigned const pos=location(ep,bank)+cursor-2;
        return word(ram[pos]|((cursor-1<length[ep][bank])?word(ram[pos+1])<<8:0));
    }
    void write(word data,byte *ram) {
        unsigned const ep=port_ep,bank=cpu_bank[ep];
        word const cursor=port_cursor;port_cursor+=2;
        if(!allocation_valid||!capacity[ep]||(full[ep]&(1U<<bank)))return;
        if(!cursor){length[ep][bank]=data;return;}
        if(cursor-2>=capacity[ep]){error[ep]=0x12;return;}
        unsigned const pos=location(ep,bank)+cursor-2;
        ram[pos]=byte(data);
        if(cursor-1<capacity[ep])ram[pos+1]=byte(data>>8);
    }
    bool validate(unsigned ep,word const *config) {
        if(!direction(ep,config)||!capacity[ep]||!allocation_valid||(ep<2&&!setup_ack&&setup_pending))return false;
        unsigned const bank=cpu_bank[ep];
        if(full[ep]&(1U<<bank))return false;
        if(length[ep][bank]>capacity[ep]){error[ep]=0x12;return false;}
        full[ep]|=byte(1U<<bank);
        if(banks(ep,config)==2)cpu_bank[ep]^=1;
        return true;
    }
    bool clear(unsigned ep,word const *config) {
        if(direction(ep,config)||!capacity[ep]||(ep<2&&!setup_ack&&setup_pending))return false;
        full[ep]&=byte(~(1U<<cpu_bank[ep]));length[ep][cpu_bank[ep]]=0;
        if(banks(ep,config)==2)cpu_bank[ep]^=1;
        if(ep==0){setup_pending=0;overwrite=0;}
        return true;
    }
    void record(unsigned ep,byte code,bool good,bool data1=false) {
        error[ep]=byte((error_pending[ep]?0x80:0)|(good?(data1?0x40:0)|1:(error[ep]&0x40)|(code<<1)));
        error_pending[ep]=1;
    }
    reply reject(unsigned ep,handshake result,byte code,word n=0) {
        record(ep,code,false);events=1U<<(8+ep);return {result,n};
    }
    reply transfer(transaction const &tx,byte const *out,byte *in,word count,
                   word const *config,byte *ram,handshake wire=handshake::ack) {
        events=0;event_good=0;
        if(!enabled||tx.address!=active_address)return {handshake::timeout,0};
        unsigned const ep=tx.endpoint?unsigned(tx.endpoint)+1:(tx.direction==pid::in?1:0);
        if(ep>=16)return {handshake::stall,0};
        if(wire!=handshake::ack) {
            byte code=1;
            switch(wire){
            case handshake::nak:code=9;break;case handshake::stall:code=10;break;
            case handshake::timeout:code=6;break;case handshake::crc:code=5;break;
            case handshake::bitstuff:code=13;break;case handshake::toggle_mismatch:code=15;break;
            case handshake::unexpected_pid:code=2;break;case handshake::data_overrun:case handshake::buffer_overrun:code=11;break;
            case handshake::data_underrun:code=8;break;case handshake::buffer_underrun:code=12;break;
            default:break;}
            return reject(ep,wire,code);
        }
        if(tx.direction==pid::setup) {
            if(tx.endpoint||count!=8||!out)return {handshake::pid_error,0};
            if(!allocation_valid||capacity[0]<8)return {handshake::nak,0};
            byte const replaced=setup_pending&&!setup_ack;
            flush(0);flush(1);stalled[0]=stalled[1]=0;
            toggle[0]=toggle[1]=1;setup_pending=1;setup_ack=0;overwrite=replaced;
            std::copy_n(out,8,ram+base[0]);length[0][0]=8;full[0]=1;
            address_pending=0;events=1U<<8;event_good=1;record(0,0,true,false);
            return {handshake::ack,8};
        }
        if(!allocation_valid||!capacity[ep]||!(config[ep]&0x80))return reject(ep,handshake::nak,9);
        if(stalled[ep])return reject(ep,handshake::stall,10);
        bool const input=tx.direction==pid::in;
        if(input!=direction(ep,config))return {handshake::stall,0};
        unsigned const bank=usb_bank[ep];
        if(!iso(ep,config)&&tx.toggle!=bool(toggle[ep]))
            return reject(ep,input?handshake::toggle_mismatch:handshake::ack,15,input?word(0):count);
        if(input) {
            if(!(full[ep]&(1U<<bank)))return reject(ep,iso(ep,config)?handshake::ack:handshake::nak,iso(ep,config)?12:9);
            word const n=length[ep][bank];
            if(n>count)return {handshake::data_overrun,n};
            if(n)std::copy_n(ram+location(ep,bank),n,in);
            full[ep]&=byte(~(1U<<bank));
            if(banks(ep,config)==2)usb_bank[ep]^=1;
            if(!iso(ep,config))toggle[ep]^=1;
            events=1U<<(8+ep);event_good=1;record(ep,0,true,tx.toggle);
            if(ep==1&&n==0&&address_pending){active_address=pending_address;address_pending=0;}
            return {handshake::ack,n};
        }
        if(full[ep]&(1U<<bank))return reject(ep,handshake::nak,9);
        if(count>capacity[ep])return reject(ep,handshake::data_overrun,11,count);
        if(count)std::copy_n(out,count,ram+location(ep,bank));
        length[ep][bank]=count;full[ep]|=byte(1U<<bank);
        if(banks(ep,config)==2)usb_bank[ep]^=1;
        if(!iso(ep,config))toggle[ep]^=1;
        events=1U<<(8+ep);event_good=1;record(ep,0,true,tx.toggle);
        return {handshake::ack,count};
    }
};
} // namespace isp1161a1
