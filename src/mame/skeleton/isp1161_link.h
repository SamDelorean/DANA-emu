// license:BSD-3-Clause
// Explicit loopback-only USB packet link using MAME image/OSD stream APIs.
// The image is a text file containing socket.127.0.0.1:PORT. No real USB
// devices, kernel drivers, services or global host settings are captured.
#pragma once
#include "diimage.h"
#include "osdfile.h"
#include "isp1161_ptd.h"
#include <array>
#include <functional>
#include <string>

class dana_usb_link_device;
DECLARE_DEVICE_TYPE(DANA_USB_LINK, dana_usb_link_device)

class dana_usb_link_device : public device_t, public device_image_interface {
public:
    using handler=std::function<isp1161a1::reply(u8,u8,u8,u8,u8 const *,u8 *,u16)>;
    dana_usb_link_device(machine_config const &config,char const *tag,device_t *owner,u32 clock=0)
      : device_t(config,DANA_USB_LINK,tag,owner,clock),device_image_interface(config,*this) {}
    bool online() const {return bool(m_socket);}
    virtual bool is_readable()const noexcept override{return true;}
    virtual bool is_writeable()const noexcept override{return false;}
    virtual bool is_creatable()const noexcept override{return false;}
    virtual bool is_reset_on_load()const noexcept override{return false;}
    virtual char const *file_extensions()const noexcept override{return "usb";}
    virtual char const *image_type_name()const noexcept override{return "usbcomputer";}
    virtual char const *image_brief_type_name()const noexcept override{return "usbc";}
    virtual std::pair<std::error_condition,std::string> call_load()override {
        if(length()>80)return {image_error::INVALIDIMAGE,"USB link configuration is too long"};
        std::array<char,81> text{};
        fread(text.data(),u32(length()));
        std::string endpoint(text.data());
        while(!endpoint.empty()&&(endpoint.back()=='\n'||endpoint.back()=='\r'||endpoint.back()==' '))endpoint.pop_back();
        std::string const prefix="socket.127.0.0.1:";
        if(endpoint.compare(0,prefix.size(),prefix)!=0)
            return {image_error::INVALIDIMAGE,"Expected an explicit socket.127.0.0.1:PORT USB host link"};
        unsigned port=0;
        for(std::size_t i=prefix.size();i<endpoint.size();++i) {
            if(endpoint[i]<'0'||endpoint[i]>'9')return {image_error::INVALIDIMAGE,"Invalid USB host port"};
            port=port*10+unsigned(endpoint[i]-'0');
            if(port>65535)return {image_error::INVALIDIMAGE,"Invalid USB host port"};
        }
        if(!port)return {image_error::INVALIDIMAGE,"Invalid USB host port"};
        u64 size=0;
        auto error=osd_file::open(endpoint,OPEN_FLAG_READ|OPEN_FLAG_WRITE,m_socket,size);
        if(error)return {error,"Cannot connect to the explicitly selected local USB host"};
        m_rx_count=m_tx_count=m_tx_cursor=0;
        return {};
    }
    virtual void call_unload()override {
        m_socket.reset();m_rx_count=m_tx_count=m_tx_cursor=0;
    }
    void poll(handler const &transaction) {
        if(!m_socket)return;
        for(unsigned budget=0;budget<8&&m_socket;++budget) {
            if(m_tx_count) {
                u32 actual=0;
                auto error=m_socket->write(m_tx.data()+m_tx_cursor,0,m_tx_count-m_tx_cursor,actual);
                if(error==std::errc::operation_would_block)return;
                if(error){call_unload();return;}
                m_tx_cursor+=actual;
                if(m_tx_cursor<m_tx_count)return;
                m_tx_count=m_tx_cursor=0;
            }
            unsigned expected=16;
            if(m_rx_count>=16) {
                if(m_rx[0]!='D'||m_rx[1]!='U'||m_rx[2]!='S'||m_rx[3]!='B'||m_rx[4]!=1) {
                    logerror("DANA_USB_LINK invalid framing; link disconnected\n");
                    call_unload();return;
                }
                unsigned const n=m_rx[10]|(unsigned(m_rx[11])<<8);
                if(n>1023){call_unload();return;}
                if(has_out_payload(m_rx[5]))expected+=n;
            }
            if(m_rx_count<expected) {
                u32 actual=0;
                auto error=m_socket->read(m_rx.data()+m_rx_count,0,expected-m_rx_count,actual);
                if(error==std::errc::operation_would_block)return;
                if(error||!actual){call_unload();return;}
                m_rx_count+=actual;
                if(m_rx_count<16)continue;
                if(expected==16&&has_out_payload(m_rx[5])&&(m_rx[10]||m_rx[11]))continue;
                if(m_rx_count<expected)continue;
            }
            u16 const length=u16(m_rx[10]|(u16(m_rx[11])<<8));
            std::copy_n(m_rx.data(),16,m_tx.data());
            m_tx[5]|=0x80;
            isp1161a1::reply const answer=transaction(m_rx[5],m_rx[6],m_rx[7],m_rx[8],
                m_rx.data()+16,m_tx.data()+16,length);
            m_tx[9]=u8(answer.status);
            unsigned const n=std::min<unsigned>(answer.size,1023);
            m_tx[10]=u8(n);m_tx[11]=u8(n>>8);
            m_tx_count=16+((has_in_payload(m_rx[5])&&answer.status==isp1161a1::handshake::ack)?n:0);
            m_tx_cursor=0;m_rx_count=0;
        }
    }
protected:
    virtual void device_start()override {
        // External host state cannot be rewound by an emulator snapshot.
        // Require an explicit remount/reconnect after restoring a snapshot.
        machine().save().register_postload(save_prepost_delegate(FUNC(dana_usb_link_device::call_unload),this));
    }
private:
    static bool has_out_payload(u8 op){return op==7||op==8||op==0x22||op==0x24;}
    static bool has_in_payload(u8 op){return op==9||op==0x10||op==0x20||op==0x21||op==0x23;}
    osd_file::ptr m_socket;
    std::array<u8,1040> m_rx{},m_tx{};
    u32 m_rx_count=0,m_tx_count=0,m_tx_cursor=0;
};
