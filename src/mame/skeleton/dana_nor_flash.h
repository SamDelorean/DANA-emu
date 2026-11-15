// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
// UK1.5-supported M28W640HCB (2008 Rev.3) / M29W320DB (2010 Rev.12).
// virtual part profile; not an identification of the unmeasured U7 topmark.
#ifndef MAME_SKELETON_DANA_NOR_FLASH_H
#define MAME_SKELETON_DANA_NOR_FLASH_H
#pragma once
#include "machine/intelfsh.h"
#include "util/hashing.h"

class dana_m28w640hcb_device;
class dana_m29w320db_device;
class dana_nor_socket_device;
DECLARE_DEVICE_TYPE(DANA_M28W640HCB, dana_m28w640hcb_device)
DECLARE_DEVICE_TYPE(DANA_M29W320DB, dana_m29w320db_device)
DECLARE_DEVICE_TYPE(DANA_NOR_SOCKET, dana_nor_socket_device)

class dana_nor_flash_device : public intelfsh16_device
{
public:
    u32 array_bytes() const { return m_size; }
    u32 coverage_bytes() const { return m_size/16; }
    unsigned block_count() const { return m_small?67:135; }
    u32 part_id() const { return m_small?0x2022cb:0x208849; }
    static constexpr unsigned blocks=135;
    void mount_seed(u8 const *seed,u32 size,bool factory,u8 const *digest);
    char const *read_fault(u32 byte) const;
    u16 bus_read(u32 byte);
    char const *bus_write(u32 byte,u16 data,u16 mask);
    void pins_changed();

protected:
    dana_nor_flash_device(machine_config const &config,device_type type,char const *tag,device_t *owner,u32 clock,bool small)
        : intelfsh16_device(config,type,tag,owner,clock,small?0x400000:0x800000,0x20,small?0x22cb:0x8849),
          m_profile(*this,":NOR_PROFILE"),m_work(*this,":NOR_WORK"),m_vpp(*this,":NOR_VPP"),m_wp(*this,":NOR_WP"),m_rp(*this,":NOR_RP"),m_small(small) { }
    virtual void device_start() override;
    virtual void nvram_default() override;
    virtual bool nvram_read(util::read_stream &file) override;
    virtual bool nvram_write(util::write_stream &file) override;
    virtual bool nvram_can_write() const override { return m_work_session && m_seeded && m_integrity && m_dirty; }

private:
    enum : u8 { ARRAY=0, SIGNATURE=1, STATUS=2, CFI=3 };
    enum : u8 { IDLE=0, PROGRAM=1, ERASE=2, OTP=3 };
    enum : u8 { COMPLETE=0, SUSPEND=1, RECOVER=2, COLLECT=3, PROTECT=4, UNPROTECT=5, VERIFY=6 };
    enum : u8 { NO_SETUP=0, WORD_DATA=1, DOUBLE_DATA=2, QUAD_DATA=4, ERASE_CONFIRM=5, LOCK_CONFIRM=6, OTP_DATA=7 };
    required_ioport m_profile,m_work,m_vpp,m_wp,m_rp;
    bool const m_small;
    u8 m_amd_sequence=0,m_amd_toggle=0,m_cfi_return=ARRAY,m_protect_setup=0,m_protect_verify=0;
    bool m_amd_bypass=false,m_amd_error=false,m_amd_chip=false,m_amd_skip=false;
    u8 m_selected[blocks]={},m_cut_selected[17]={},m_protection_unknown[17]={},m_rp_level=1;
    u32 m_protect_address=0;
    unsigned m_last_vpp=1;
    attotime m_reset_low_since=attotime::zero;
    char const *amd_write(u32 byte,u16 data,u16 mask);
    u16 amd_status(u32 byte);
    void amd_select(u32 byte,bool chip);
    bool protection_unknown(unsigned n) const {return (m_protection_unknown[n/8]>>(n&7))&1;}
    void protection_known(unsigned n,bool known){if(known)m_protection_unknown[n/8]&=~u8(1U<<(n&7));else m_protection_unknown[n/8]|=1U<<(n&7);}
    unsigned st_pin() const {return m_wp->read()?m_vpp->read():0;}
    bool amd_protected(unsigned n) const { return (n==0&&st_pin()==0) || (m_locks[n]&&m_rp->read()!=2); }
    bool selected(u32 byte) const { return m_selected[block(byte)]; }

    emu_timer *m_operation_timer=nullptr;
    std::unique_ptr<u8[]> m_known;
    u8 m_locks[blocks]={},m_uid[8]={},m_otp[16]={},m_otp_lock=2,m_otp_known=255,m_otp_lock_known=1;
    u8 m_setup=0,m_loaded_count=0,m_expected_count=0,m_operation=IDLE,m_event=COMPLETE;
    u16 m_values[4]={};u32 m_addresses[4]={};
    u32 m_target=0,m_erase_target=0,m_seed_bytes=0,m_loaded_seed_bytes=0;
    u8 m_seed_hash[20]={},m_loaded_seed_hash[20]={},m_saved_recipe[20]={},m_live_recipe[20]={};
    u8 m_saved_disk[20]={},m_live_disk[20]={};
    u64 m_remaining=0,m_erase_remaining=0,m_disk_generation=0;
    bool m_suspended=false,m_erase_suspended=false,m_seeded=false,m_loaded=false,m_dirty=false;
    bool m_interrupted_lock=false;
    bool m_factory=false,m_loaded_factory=false,m_last_rp=true,m_recovering=false;
    bool m_work_session=false,m_integrity=true;
    u32 m_recovery_ns=30;
    u32 m_interrupted[4]={};u8 m_interrupted_otp=0;

    unsigned block(u32 byte) const { return m_small ? (byte<0x4000?0:byte<0x6000?1:byte<0x8000?2:byte<0x10000?3:4+(byte-0x10000)/0x10000) : (byte<0x10000?byte/0x2000:8+(byte-0x10000)/0x10000); }
    u32 block_base(unsigned n) const { static constexpr u32 boot[4]={0,0x4000,0x6000,0x8000};return m_small?(n<4?boot[n]:0x10000+(n-4)*0x10000):(n<8?n*0x2000:0x10000+(n-8)*0x10000); }
    u32 block_size(unsigned n) const { static constexpr u32 boot[4]={0x4000,0x2000,0x2000,0x8000};return m_small?(n<4?boot[n]:0x10000):(n<8?0x2000:0x10000); }
    bool known(u32 byte) const { u32 const n=byte/2;return (m_known[n/8]>>(n&7))&1; }
    void mark_block(u32 byte,bool value);
    u8 lock_status(unsigned n) const { return m_locks[n] | (((m_locks[n]&2)&&!m_wp->read())?1:0); }
    unsigned voltage() const { return m_work_session ? m_vpp->read() : 0; }
    u16 array_word(u32 byte) { return (u16(m_data[byte])<<8)|m_data[byte+1]; }
    void error(u8 bits) { m_status|=0x80|bits;m_flash_mode=STATUS;m_setup=NO_SETUP;m_loaded_count=0; }
    void launch(u8 operation,u32 byte,attotime delay);
    void suspend();
    void resume();
    void abort_operation();
    void postload();
    u16 cfi(u32 word) const;
    void metadata(u8 *out) const;
    util::sha1_t storage_hash(u8 const *header,u8 const *meta) const;
    static void put32(u8 *p,u32 n) { for(unsigned i=0;i<4;++i)p[i]=u8(n>>(24-i*8)); }
    static u32 get32(u8 const *p) { return (u32(p[0])<<24)|(u32(p[1])<<16)|(u32(p[2])<<8)|p[3]; }
    TIMER_CALLBACK_MEMBER(operation_tick);
};

void dana_nor_flash_device::device_start()
{
    // Reuse MAME's single x16 array allocation, array reader and state owner.
    // Its generic command decoder has different geometry/protection semantics.
    intelfsh16_device::device_start();
    m_byte_count=0;m_sdp=false;m_write_buffer_count=0;m_write_buffer_start_address=0;
    std::fill(std::begin(m_write_buffer),std::end(m_write_buffer),0);
    m_known=std::make_unique<u8[]>(coverage_bytes());
    std::fill_n(m_data.get(),m_size,255);std::fill_n(m_known.get(),coverage_bytes(),0);
    std::fill(std::begin(m_locks),std::end(m_locks),m_small?0:1);
    std::fill(std::begin(m_otp),std::end(m_otp),255);
    m_operation_timer=timer_alloc(FUNC(dana_nor_flash_device::operation_tick),this);
    save_pointer(NAME(m_known),coverage_bytes());
#define DANA_NOR_SAVE(x) save_item(NAME(x))
    DANA_NOR_SAVE(m_amd_sequence);DANA_NOR_SAVE(m_amd_toggle);DANA_NOR_SAVE(m_cfi_return);
    DANA_NOR_SAVE(m_protect_setup);DANA_NOR_SAVE(m_protect_verify);DANA_NOR_SAVE(m_protect_address);
    DANA_NOR_SAVE(m_amd_bypass);DANA_NOR_SAVE(m_amd_error);DANA_NOR_SAVE(m_amd_chip);DANA_NOR_SAVE(m_amd_skip);
    DANA_NOR_SAVE(m_protection_unknown);DANA_NOR_SAVE(m_rp_level);DANA_NOR_SAVE(m_selected);DANA_NOR_SAVE(m_last_vpp);DANA_NOR_SAVE(m_reset_low_since);
    DANA_NOR_SAVE(m_locks);DANA_NOR_SAVE(m_uid);DANA_NOR_SAVE(m_otp);DANA_NOR_SAVE(m_otp_lock);DANA_NOR_SAVE(m_otp_known);DANA_NOR_SAVE(m_otp_lock_known);
    DANA_NOR_SAVE(m_setup);DANA_NOR_SAVE(m_loaded_count);DANA_NOR_SAVE(m_expected_count);
    DANA_NOR_SAVE(m_operation);DANA_NOR_SAVE(m_event);DANA_NOR_SAVE(m_values);DANA_NOR_SAVE(m_addresses);
    DANA_NOR_SAVE(m_target);DANA_NOR_SAVE(m_erase_target);DANA_NOR_SAVE(m_remaining);DANA_NOR_SAVE(m_erase_remaining);
    DANA_NOR_SAVE(m_seed_bytes);DANA_NOR_SAVE(m_seed_hash);DANA_NOR_SAVE(m_saved_recipe);DANA_NOR_SAVE(m_saved_disk);
    DANA_NOR_SAVE(m_suspended);DANA_NOR_SAVE(m_erase_suspended);DANA_NOR_SAVE(m_seeded);DANA_NOR_SAVE(m_dirty);
    DANA_NOR_SAVE(m_factory);DANA_NOR_SAVE(m_last_rp);DANA_NOR_SAVE(m_recovering);DANA_NOR_SAVE(m_recovery_ns);
#undef DANA_NOR_SAVE
    machine().save().register_postload(save_prepost_delegate(FUNC(dana_nor_flash_device::postload),this));
}

void dana_nor_flash_device::nvram_default()
{
    // MAME loads configuration after device_start, before NVRAM.
    m_work_session=bool(m_work->read()) && m_profile->read()==1;
    std::fill_n(m_data.get(),m_size,255);std::fill_n(m_known.get(),coverage_bytes(),0);
    std::fill(std::begin(m_otp),std::end(m_otp),255);
    m_otp_lock=2;m_otp_known=255;m_otp_lock_known=1;m_seeded=false;m_loaded=false;m_dirty=false;
}

void dana_nor_flash_device::mount_seed(u8 const *seed,u32 size,bool factory,u8 const *digest)
{
    if(m_seeded)
    {
        if(size!=m_seed_bytes || factory!=m_factory || std::memcmp(digest,m_seed_hash,20))
        {m_integrity=false;fatalerror("Restart before changing the NOR seed or coverage profile; working storage preserved");}
        return;
    }
    if(size>m_size || (size&1))fatalerror("Seed exceeds the selected x16 NOR capacity");
    m_seed_bytes=size;m_factory=factory;std::copy_n(digest,20,m_seed_hash);
    u8 recipe[29]={};std::copy_n(digest,20,recipe);put32(recipe+20,size);put32(recipe+24,part_id());recipe[28]=factory;
    auto const hash=util::sha1_creator::simple(recipe,sizeof(recipe));
    // Storage policy is part of state compatibility, not the virtual chip UID.
    u8 state_recipe[30];std::copy_n(recipe,29,state_recipe);state_recipe[29]=m_work_session;
    auto const state_hash=util::sha1_creator::simple(state_recipe,sizeof(state_recipe));
    std::copy_n(state_hash.m_raw,20,m_live_recipe);std::copy_n(state_hash.m_raw,20,m_saved_recipe);
    if(m_loaded)
    {
        if(size!=m_loaded_seed_bytes || factory!=m_loaded_factory || std::memcmp(digest,m_loaded_seed_hash,20))
        {m_integrity=false;fatalerror("NOR working storage belongs to a different seed/profile; original and working files preserved");}
        for(unsigned n=0;n<2;++n)if(m_interrupted[n*2+1])mark_block(m_interrupted[n*2],false);
        if(m_small)for(unsigned n=0;n<block_count();++n)if(m_cut_selected[n/8]&(1U<<(n&7))){mark_block(block_base(n),false);m_dirty=true;}
        m_otp_known&=~m_interrupted_otp;
        if(m_interrupted[1]||m_interrupted[3]||m_interrupted_otp||m_interrupted_lock)m_dirty=true;
    }
    else
    {
        std::fill_n(m_data.get(),m_size,255);std::copy_n(seed,size,m_data.get());
        std::fill_n(m_known.get(),coverage_bytes(),factory?255:0);
        for(u32 n=0;n<size/2;++n)m_known[n/8]|=1U<<(n&7);
        // Immutable synthetic ID of this virtual seed, not an asserted U7 serial.
        std::copy_n(hash.m_raw,8,m_uid);
    }
    m_seeded=true;pins_changed();
    logerror("DANA_NOR_MOUNT profile=%s seed=%u factory=%u work=%u persistent=%u\n",m_small?"M29W320DB":"M28W640HCB",size,factory,m_work_session,m_loaded);
}

void dana_nor_flash_device::mark_block(u32 byte,bool value)
{
    unsigned const n=block(byte);u32 const first=block_base(n)/16,count=block_size(n)/16;
    std::fill_n(m_known.get()+first,count,value?255:0);
}

char const *dana_nor_flash_device::read_fault(u32 byte) const
{
    if(!m_last_rp || m_recovering)return "NOR_RESET_BUS_UNDRIVEN";
    if(!m_small&&m_rp->read()>1)return "NOR_RP_HIGH_VOLTAGE_UNQUALIFIED";
    if(m_small&&m_flash_mode==SIGNATURE&&((byte/2)&3)==2&&protection_unknown(block(byte)))return "NOR_ST_INTERRUPTED_PROTECTION_UNDEFINED";
    if(m_small&&m_protect_verify==2)return "NOR_ST_PROTECTION_VERIFY_NOT_READY";
    if(m_small && (m_amd_error || (m_flash_mode==ARRAY && (m_operation||m_erase_suspended)&&selected(byte))))return nullptr;
    if(m_operation && !m_suspended)return nullptr; // Busy reads always return SR.
    if(m_flash_mode==SIGNATURE)
    {
        u32 const a=(byte/2)&255;
        if(a==0x80&&!m_otp_lock_known)return "NOR_INTERRUPTED_OTP_UNDEFINED";
        if(a>=0x85 && a<=0x8c && !(m_otp_known&(1U<<(a-0x85))))return "NOR_INTERRUPTED_OTP_UNDEFINED";
    }
    if(m_flash_mode!=ARRAY)return nullptr;
    unsigned const b=block(byte);
    if(!m_small&&((m_erase_suspended && block(m_erase_target)==b)||(m_operation && m_suspended && block(m_target)==b)))return "NOR_SUSPENDED_ARRAY_UNDEFINED";
    return known(byte)?nullptr:"FLASH_BYTES_NOT_SUPPLIED";
}

u16 dana_nor_flash_device::bus_read(u32 byte)
{
    if(m_small)
    {
        if(m_protect_verify==1 && ((byte/2)&0x43)==((m_protect_address/2)&0x43))return m_locks[block(byte)]?1:0;
        if(m_amd_error||(m_operation&&!m_suspended)||((m_operation||m_erase_suspended)&&selected(byte)&&m_flash_mode==ARRAY))return amd_status(byte);
    }
    if((m_operation && !m_suspended)||m_flash_mode==STATUS)return m_status;
    u32 const word=byte/2,a=word&255;
    if(m_flash_mode==CFI)return cfi(a);
    if(m_flash_mode==SIGNATURE)
    {
        if(m_small)
        {u32 const low=word&3;if(low==0)return 0x20;if(low==1)return 0x22cb;if(low==2)return amd_protected(block(byte));return 0xffff;}
        if(a==0)return 0x20;if(a==1)return 0x8849;if(a==2)return lock_status(block(byte));
        if(a==0x80)return m_otp_lock;
        if(a>=0x81 && a<=0x84){unsigned const i=(a-0x81)*2;return (u16(m_uid[i])<<8)|m_uid[i+1];}
        if(a>=0x85 && a<=0x8c){unsigned const i=(a-0x85)*2;return (u16(m_otp[i])<<8)|m_otp[i+1];}
        return 0xffff; // Undefined signature locations, not invented IDs.
    }
    return intelfsh16_device::read(word);
}

u16 dana_nor_flash_device::cfi(u32 a) const
{
    if(m_small)
    {
        static constexpr u8 table[0x50]={
            0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
            'Q','R','Y',2,0,0x40,0,0,0,0,0,0x27,0x36,0xb5,0xc5,4,
            0,10,0,5,0,4,0,0x16,2,0,0,0,4,0,0,0x40,
            0,1,0,0x20,0,0,0,0x80,0,0x3e,0,0,1,0,0,0,
            'P','R','I','1','0',0,2,1,1,4,0,0,0,0xb5,0xc5,2};
        if(a>=0x61&&a<=0x64){unsigned const n=(a-0x61)*2;return (u16(m_uid[n])<<8)|m_uid[n+1];}
        return a<std::size(table)?table[a]:0;
    }
    // Manufacturer Tables 26-30, x16 query addresses (CPU byte offset = 2*a).
    static constexpr u8 table[0x48]={
        0x20,0x49,0,0,0,0,0,0,0,0,0,0,0,0,0,0,
        'Q','R','Y',3,0,0x35,0,0,0,0,0,0x27,0x36,0xb4,0xc6,4,
        4,10,0,5,5,3,0,0x17,1,0,3,0,2,7,0,0x20,
        0,0x7e,0,0,1,'P','R','I','1','0',0x66,0,0,0,1,3,
        0,0x30,0xc0,1,0x80,0,3,4};
    if(a==1)return 0x8849;
    return a<std::size(table)?table[a]:0;
}

void dana_nor_flash_device::launch(u8 op,u32 byte,attotime delay)
{
    m_operation=op;m_target=byte;m_suspended=false;m_event=COMPLETE;
    m_status&=~u8(0x84);m_flash_mode=STATUS;m_setup=NO_SETUP;m_dirty=true;
    m_operation_timer->adjust(delay);
    logerror("DANA_NOR_START op=%u address=%06x duration_ns=%lld\n",op,byte,(long long)(delay.as_attoseconds()/1000000000));
}
void dana_nor_flash_device::suspend()
{
    if(!m_operation||m_suspended||m_operation==OTP||m_event==SUSPEND)return;
    if(m_small && (m_operation!=ERASE||m_amd_chip))return;
    if(m_small&&m_event==COLLECT)
    {m_remaining=attotime::from_msec(800).as_attoseconds();m_suspended=true;m_flash_mode=ARRAY;m_operation_timer->adjust(attotime::never);return;}
    attotime const latency=attotime::from_usec(m_small?15:m_operation==ERASE?30:5);
    if(m_operation_timer->remaining()<=latency)return; // Operation may finish first.
    m_remaining=(m_operation_timer->remaining()-latency).as_attoseconds();m_event=SUSPEND;
    m_operation_timer->adjust(latency);
}
void dana_nor_flash_device::resume()
{
    if(!m_operation && m_erase_suspended)
    {m_operation=ERASE;m_target=m_erase_target;m_remaining=m_erase_remaining;m_erase_suspended=false;}
    if(!m_operation)return;
    m_suspended=false;m_event=COMPLETE;m_status&=~u8(0xc4);m_flash_mode=STATUS;
    m_operation_timer->adjust(attotime(0,m_remaining));
}

TIMER_CALLBACK_MEMBER(dana_nor_flash_device::operation_tick)
{
    if(m_event==RECOVER){m_recovering=false;return;}
    if(m_event==PROTECT||m_event==UNPROTECT)
    {
        if(m_event==PROTECT){m_locks[block(m_protect_address)]=1;protection_known(block(m_protect_address),true);}
        else {std::fill(std::begin(m_locks),std::end(m_locks),0);std::fill(std::begin(m_protection_unknown),std::end(m_protection_unknown),0);}
        m_dirty=true;m_protect_verify=0;return;
    }
    if(m_event==VERIFY){m_protect_verify=1;return;}
    if(m_event==COLLECT)
    {m_event=COMPLETE;bool any=false;for(unsigned n=0;n<block_count();++n)any|=m_selected[n]!=0;m_operation_timer->adjust(any?attotime::from_msec(800):attotime::from_usec(100));return;}
    if(m_event==SUSPEND)
    {m_suspended=true;m_status|=0x80|(m_operation==ERASE?0x40:4);if(m_small)m_flash_mode=ARRAY;logerror("DANA_NOR_SUSPENDED op=%u\n",m_operation);return;}
    if(m_operation==ERASE)
    {
        if(m_small)
        {for(unsigned n=0;n<block_count();++n)if(m_selected[n]){std::fill_n(m_data.get()+block_base(n),block_size(n),255);mark_block(block_base(n),true);}std::fill(std::begin(m_selected),std::end(m_selected),0);}
        else {unsigned const n=block(m_target);std::fill_n(m_data.get()+block_base(n),block_size(n),255);mark_block(m_target,true);}
    }
    else if(m_operation==PROGRAM)
    {
        for(unsigned n=0;n<m_expected_count&&!m_amd_skip;++n)
        {
            u32 const a=m_addresses[n];u16 const old=array_word(a),data=m_values[n];
            if(data&~old)m_status|=0x10;u16 const value=old&data;
            m_data[a]=u8(value>>8);m_data[a+1]=u8(value);
        }
    }
    else if(m_operation==OTP)
    {
        u32 const a=(m_addresses[0]/2)&255;
        if(a==0x80){if((m_values[0]&2)&~m_otp_lock)m_status|=0x10;m_otp_lock&=u8(m_values[0])&2;}
        else
        {
            unsigned const i=(a-0x85)*2;u16 const old=(u16(m_otp[i])<<8)|m_otp[i+1],data=m_values[0];
            if(data&~old)m_status|=0x10;u16 const v=old&data;m_otp[i]=u8(v>>8);m_otp[i+1]=u8(v);
        }
    }
    logerror("DANA_NOR_COMPLETE op=%u address=%06x status=%02x\n",m_operation,m_target,m_status|0x80);
    m_operation=IDLE;m_suspended=false;m_status=(m_status&~u8(4))|0x80;
    if(m_erase_suspended)m_status|=0x40;
    if(m_small){m_amd_error=bool(m_status&0x10);m_flash_mode=ARRAY;m_amd_skip=false;}
}

char const *dana_nor_flash_device::bus_write(u32 byte,u16 data,u16 mask)
{
    if(!m_last_rp||m_recovering)return nullptr;
    if(m_small)return amd_write(byte,data,mask);
    u8 const command=mask==0xff00?u8(data>>8):u8(data);
    if(m_operation&&!m_suspended)
    {if(command==0xb0)suspend();return nullptr;} // 70 polls; all other commands ignored.
    if(m_setup==WORD_DATA||m_setup==DOUBLE_DATA||m_setup==QUAD_DATA||m_setup==OTP_DATA)
    {
        // This evidenced profile programs x16 data. Command byte writes are
        // independently supported by the actual ROM. No invented byte-WE wiring.
        if(mask!=0xffff)return "NOR_X16_DATA_STROBES_UNQUALIFIED";
        bool const otp=m_setup==OTP_DATA;
        if(!voltage()){error(8);return nullptr;}
        if(!otp && (lock_status(block(byte))&1)){error(0x12);return nullptr;}
        if(!otp && m_erase_suspended && block(byte)==block(m_erase_target)){error(0x10);return nullptr;}
        if(!otp && !known(byte))return "NOR_PROGRAM_BASE_NOT_SUPPLIED";
        if(otp)
        {
            u32 const a=(byte/2)&255;
            if(a!=0x80 && !(a>=0x85&&a<=0x8c)){error(0x10);return nullptr;}
            if(a>=0x85 && !(m_otp_known&(1U<<(a-0x85))))return "NOR_INTERRUPTED_OTP_UNDEFINED";
            if(!m_otp_lock_known)return "NOR_INTERRUPTED_OTP_UNDEFINED";
            if(a!=0x80 && !(m_otp_lock&2)){error(0x12);return nullptr;}
        }
        if(m_loaded_count)
        {
            u32 const first=m_addresses[0];
            if((byte&~u32(m_expected_count*2-1))!=(first&~u32(m_expected_count*2-1)))
                return "NOR_MULTIWORD_ADDRESS_UNDEFINED";
            for(unsigned i=0;i<m_loaded_count;++i)if(byte==m_addresses[i])return "NOR_MULTIWORD_ADDRESS_UNDEFINED";
        }
        m_addresses[m_loaded_count]=byte;m_values[m_loaded_count++]=data;
        if(m_loaded_count==m_expected_count)launch(otp?OTP:PROGRAM,m_addresses[0],attotime::from_usec(10));
        return nullptr;
    }
    if(m_setup==ERASE_CONFIRM)
    {
        m_setup=NO_SETUP;
        if(command!=0xd0){error(0x30);return nullptr;}
        if(!voltage()){error(8);return nullptr;}
        if(lock_status(block(byte))&1){error(0x22);return nullptr;}
        launch(ERASE,byte,attotime::from_msec(block(byte)<8?400:1000));return nullptr;
    }
    if(m_setup==LOCK_CONFIRM)
    {
        m_setup=NO_SETUP;unsigned const n=block(byte);
        if(command==1)m_locks[n]|=1;
        else if(command==0x2f)m_locks[n]|=3;
        else if(command==0xd0){if(m_wp->read()||!(m_locks[n]&2))m_locks[n]&=~u8(1);}
        else {error(0x30);return nullptr;}
        m_flash_mode=STATUS;m_status|=0x80;return nullptr;
    }
    if(m_operation && m_suspended && m_operation!=ERASE)
    {
        if(command==0xd0){resume();return nullptr;}
        if(command!=0xff&&command!=0x90&&command!=0x98&&command!=0x70)return nullptr;
    }
    bool const erase_paused=(m_operation==ERASE&&m_suspended)||m_erase_suspended;
    switch(command)
    {
    case 0xff:m_flash_mode=ARRAY;break;
    case 0x90:m_flash_mode=SIGNATURE;break;
    case 0x98:m_flash_mode=CFI;break;
    case 0x70:m_flash_mode=STATUS;break;
    case 0x50:m_status&=~u8(0x3a);break;
    case 0xd0:if(m_suspended||m_erase_suspended)resume();break;
    case 0xb0:break;
    case 0x60:m_setup=LOCK_CONFIRM;break;
    case 0x20:if(!erase_paused)m_setup=ERASE_CONFIRM;break;
    case 0x10:case 0x40:case 0x30:case 0x56:case 0xc0:
        if((command==0x30||command==0x56)&&voltage()!=2){error(8);break;}
        if(m_operation==ERASE&&m_suspended)
        {m_erase_suspended=true;m_erase_target=m_target;m_erase_remaining=m_remaining;m_operation=IDLE;m_suspended=false;}
        m_loaded_count=0;m_expected_count=command==0x30?2:command==0x56?4:1;
        m_setup=command==0xc0?OTP_DATA:command==0x30?DOUBLE_DATA:command==0x56?QUAD_DATA:WORD_DATA;
        break;
    default:break; // Unsupported/undefined command: no write to array.
    }
    return nullptr;
}

void dana_nor_flash_device::abort_operation()
{
    if(m_operation==OTP)
    {u32 const a=(m_addresses[0]/2)&255;if(a>=0x85&&a<=0x8c)m_otp_known&=~u8(1U<<(a-0x85));else m_otp_lock_known=0;}
    else if(m_operation)
    {if(m_small&&m_operation==ERASE){for(unsigned n=0;n<block_count();++n)if(m_selected[n])mark_block(block_base(n),false);}else mark_block(m_target,false);}
    if(m_erase_suspended){if(m_small){for(unsigned n=0;n<block_count();++n)if(m_selected[n])mark_block(block_base(n),false);}else mark_block(m_erase_target,false);}
    if(m_operation||m_erase_suspended)m_dirty=true;
    m_operation=IDLE;m_suspended=false;m_erase_suspended=false;m_setup=NO_SETUP;
    std::fill(std::begin(m_selected),std::end(m_selected),0);
    m_operation_timer->adjust(attotime::never);
}
void dana_nor_flash_device::pins_changed()
{
    unsigned const vpp=m_small?st_pin():m_vpp->read();
    if(m_small&&vpp!=m_last_vpp)
    {
        if(vpp==2 && (m_operation||m_flash_mode!=ARRAY))fatalerror("ST VPP raised outside read mode: indeterminate operation");
        m_amd_bypass=vpp==2;m_amd_sequence=0;m_last_vpp=vpp;
    }
    u8 const level=m_rp->read();
    if(m_small&&m_rp_level==2&&level!=2&&m_operation_timer->enabled()&&(m_event==PROTECT||m_event==UNPROTECT))
        m_operation_timer->adjust(attotime::never); // Fuse outcome remains explicitly unknown.
    m_rp_level=level;
    bool const rp=bool(level);if(rp==m_last_rp)return;
    if(!rp)
    {
        m_reset_low_since=machine().time();m_recovery_ns=m_small?50:(m_operation||m_erase_suspended)?50000:30;abort_operation();
        m_amd_error=false;m_amd_sequence=0;m_amd_bypass=m_small&&vpp==2;m_protect_setup=0;m_protect_verify=0;
        m_status=0x80;m_flash_mode=ARRAY;m_recovering=false;
        if(!m_small)std::fill(std::begin(m_locks),std::end(m_locks),1);
    }
    else
    {
        m_recovering=true;m_event=RECOVER;
        attotime const busy_delay=m_small?std::max(attotime::zero,attotime::from_usec(25)-(machine().time()-m_reset_low_since)):attotime::zero;
        m_operation_timer->adjust(std::max(busy_delay,attotime::from_nsec(m_recovery_ns)));
    }
    m_last_rp=rp;
    logerror("DANA_NOR_RP value=%u recovery_ns=%u\n",rp,m_recovery_ns);
}
void dana_nor_flash_device::postload()
{
    if(std::memcmp(m_saved_recipe,m_live_recipe,20)||std::memcmp(m_saved_disk,m_live_disk,20))
    {m_integrity=false;fatalerror("NOR save-state conflicts with the mounted seed, storage mode or committed working-storage generation; persistent file preserved");}
    pins_changed();
}

void dana_nor_flash_device::metadata(u8 *out) const
{
    std::fill_n(out,184,0);std::copy_n(m_uid,8,out);std::copy_n(m_otp,16,out+8);out[24]=m_otp_lock;out[25]=m_otp_known;out[26]=m_otp_lock_known;if(m_small){std::copy_n(m_locks,blocks,out+32);std::copy_n(m_protection_unknown,17,out+167);}
}
util::sha1_t dana_nor_flash_device::storage_hash(u8 const *h,u8 const *meta) const
{
    util::sha1_creator hash;hash.append(h,56);hash.append(h+76,52);
    hash.append(m_data.get(),m_size);hash.append(m_known.get(),coverage_bytes());hash.append(meta,184);return hash.finish();
}
bool dana_nor_flash_device::nvram_read(util::read_stream &file)
{
    m_work_session=bool(m_work->read()) && m_profile->read()==1;
    if(!m_work_session)return true; // Reference mode never consumes the work image.
    m_integrity=false;u8 header[128],meta[184];
    auto exact=[&](void *p,size_t n){auto const [err,actual]=util::read(file,p,n);return !err&&actual==n;};
    if(!exact(header,sizeof(header))||std::memcmp(header,"DANANOR5",8)||get32(header+8)!=3||get32(header+12)!=part_id()||get32(header+16)!=m_size)
        fatalerror("NOR working storage has an incompatible header; file preserved");
    if(!exact(m_data.get(),m_size)||!exact(m_known.get(),coverage_bytes())||!exact(meta,sizeof(meta)))fatalerror("Truncated NOR working storage; file preserved");
    u8 extra;auto const [tail_error,tail_actual]=util::read(file,&extra,1);if(tail_actual)fatalerror("Trailing data in NOR working storage; file preserved");
    auto const hash=storage_hash(header,meta);if(std::memcmp(hash.m_raw,header+56,20))fatalerror("NOR working-storage checksum mismatch; file preserved");
    m_loaded_seed_bytes=get32(header+20);m_loaded_factory=bool(get32(header+24));std::copy_n(header+28,20,m_loaded_seed_hash);
    m_disk_generation=(u64(get32(header+48))<<32)|get32(header+52);
    std::copy_n(header+56,20,m_live_disk);std::copy_n(header+56,20,m_saved_disk);
    for(unsigned i=0;i<4;++i)m_interrupted[i]=get32(header+76+i*4);
    for(unsigned i=0;i<2;++i)if(m_interrupted[i*2+1] && (m_interrupted[i*2]>=m_size || m_interrupted[i*2+1]!=block_size(block(m_interrupted[i*2]))))fatalerror("Invalid NOR interrupted-operation range");
    m_interrupted_otp=header[92];std::copy_n(meta,8,m_uid);std::copy_n(meta+8,16,m_otp);m_otp_lock=meta[24]&2;m_otp_known=meta[25];m_interrupted_lock=bool(header[93]);m_otp_lock_known=meta[26]&&!m_interrupted_lock;
    if(m_small){std::copy_n(meta+32,blocks,m_locks);std::copy_n(meta+167,17,m_protection_unknown);std::copy_n(header+96,17,m_cut_selected);}
    m_loaded=true;m_integrity=true;return true;
}
bool dana_nor_flash_device::nvram_write(util::write_stream &file)
{
    u8 header[128]={},meta[184];std::memcpy(header,"DANANOR5",8);put32(header+8,3);put32(header+12,part_id());put32(header+16,m_size);
    put32(header+20,m_seed_bytes);put32(header+24,m_factory);std::copy_n(m_seed_hash,20,header+28);
    u64 const generation=m_disk_generation+1;put32(header+48,generation>>32);put32(header+52,generation);
    // A process exit is a power cut, not automatic completion of pending work.
    if(m_operation==PROGRAM||(!m_small&&m_operation==ERASE)){unsigned const b=block(m_target);put32(header+76,block_base(b));put32(header+80,block_size(b));}
    if(!m_small&&m_erase_suspended){unsigned const b=block(m_erase_target);put32(header+84,block_base(b));put32(header+88,block_size(b));}
    if(m_operation==OTP){u32 const a=(m_addresses[0]/2)&255;if(a>=0x85&&a<=0x8c)header[92]=1U<<(a-0x85);else header[93]=1;}
    if(m_small&&(m_operation==ERASE||m_erase_suspended))for(unsigned n=0;n<block_count();++n)if(m_selected[n])header[96+n/8]|=1U<<(n&7);
    metadata(meta);auto const hash=storage_hash(header,meta);std::copy_n(hash.m_raw,20,header+56);
    auto exact=[&](void const *p,size_t n){auto const [err,actual]=util::write(file,p,n);return !err&&actual==n;};
    return exact(header,sizeof(header))&&exact(m_data.get(),m_size)&&exact(m_known.get(),coverage_bytes())&&exact(meta,sizeof(meta));
}
// M29W320DB: Numonyx Rev.12, February 2010. This is the 0020/22CB,
// 67-block layout selected by the original UK1.5 driver, not a U7 BOM claim.
u16 dana_nor_flash_device::amd_status(u32 byte)
{
    bool const paused=(m_erase_suspended||(m_operation==ERASE&&m_suspended))&&selected(byte);
    m_amd_toggle^=paused?4:0x44;
    u16 value=paused?0x80:m_operation==PROGRAM||m_amd_error?u16(~m_values[0]&0x80):0;
    value|=m_amd_toggle&(paused?4:0x40);
    if((m_operation==ERASE||m_erase_suspended)&&selected(byte))value|=m_amd_toggle&4;
    if(m_amd_error)value|=0x20;
    if((m_operation==ERASE||m_erase_suspended)&&m_event!=COLLECT)value|=8;
    return value;
}
void dana_nor_flash_device::amd_select(u32 byte,bool chip)
{
    if(m_operation!=ERASE)
    {
        std::fill(std::begin(m_selected),std::end(m_selected),0);
        m_amd_chip=chip;m_amd_error=false;m_amd_toggle=0;m_status=0x80;
        launch(ERASE,byte,attotime::from_usec(50));
    }
    if(chip)
    {
        bool any=false;for(unsigned n=0;n<block_count();++n){m_selected[n]=!amd_protected(n);any|=m_selected[n]!=0;}
        m_event=COMPLETE;m_operation_timer->adjust(any?attotime::from_seconds(40):attotime::from_usec(100));
    }
    else
    {
        if(!amd_protected(block(byte)))m_selected[block(byte)]=1;
        m_event=COLLECT;m_operation_timer->adjust(attotime::from_usec(50));
    }
}
char const *dana_nor_flash_device::amd_write(u32 byte,u16 data,u16 mask)
{
    u8 const command=mask==0xff00?u8(data>>8):u8(data);
    u32 const a=(byte/2)&0x7ff;
    if(m_operation&&!m_suspended)
    {
        if(m_operation==ERASE&&!m_amd_chip)
        {
            if(m_event==COLLECT&&command==0x30)
            {if(protection_unknown(block(byte))&&m_rp->read()!=2)return "NOR_ST_INTERRUPTED_PROTECTION_UNDEFINED";amd_select(byte,false);}
            else if(command==0xb0)suspend();
        }
        return nullptr;
    }
    if(m_setup==WORD_DATA)
    {
        if(mask!=0xffff)return "NOR_X16_DATA_STROBES_UNQUALIFIED";
        if(!m_work_session)return "NOR_REFERENCE_SESSION_WRITE_DISABLED";
        if(protection_unknown(block(byte))&&m_rp->read()!=2)return "NOR_ST_INTERRUPTED_PROTECTION_UNDEFINED";
        m_amd_skip=amd_protected(block(byte)) || ((m_erase_suspended||(m_operation==ERASE&&m_suspended))&&selected(byte));
        if(!m_amd_skip&&!known(byte))return "NOR_PROGRAM_BASE_NOT_SUPPLIED";
        if(m_operation==ERASE&&m_suspended)
        {m_erase_suspended=true;m_erase_target=m_target;m_erase_remaining=m_remaining;m_operation=IDLE;m_suspended=false;}
        m_values[0]=data;m_addresses[0]=byte;m_expected_count=1;m_status=0x80;m_amd_error=false;m_amd_toggle=0;
        launch(PROGRAM,byte,attotime::from_usec(m_amd_skip?1:st_pin()==2?8:10));return nullptr;
    }
    // The documented in-system high-voltage protection flow is opt-in through
    // the virtual RP fixture. It is not attributed to Dana board wiring.
    if(m_rp->read()==2 && (command==0x60||command==0x40) && (a&3)==2)
    {
        if(!m_work_session)return "NOR_REFERENCE_SESSION_WRITE_DISABLED";
        if(m_operation||m_erase_suspended)return "NOR_ST_PROTECTION_DURING_ERASE_UNDEFINED";
        if(command==0x60)
        {
            if(m_protect_setup && ((byte^m_protect_address)&0x86)==0 && ((a&0x40)||block(byte)==block(m_protect_address)))
            {
                if(a&0x40)
                {
                    for(unsigned n=0;n<block_count();++n)if(!m_locks[n]||protection_unknown(n))return "NOR_ST_UNPROTECT_PREREQUISITE_UNDEFINED";
                    std::fill(std::begin(m_protection_unknown),std::end(m_protection_unknown),255);m_dirty=true;
                    m_event=UNPROTECT;m_operation_timer->adjust(attotime::from_msec(10));
                }
                else {protection_known(block(byte),false);m_dirty=true;m_event=PROTECT;m_operation_timer->adjust(attotime::from_usec(100));}
                m_protect_setup=0;
            }
            else {m_protect_setup=1;m_protect_address=byte;}
        }
        else
        {
            if((m_event==PROTECT||m_event==UNPROTECT)&&m_operation_timer->enabled())return "NOR_ST_PROTECTION_PULSE_TOO_SHORT";
            m_protect_address=byte;m_protect_verify=2;m_event=VERIFY;m_operation_timer->adjust(attotime::from_usec(4));
        }
        return nullptr;
    }
    if(command==0xf0)
    {
        m_amd_sequence=0;m_setup=NO_SETUP;m_amd_error=false;m_protect_setup=0;m_protect_verify=0;
        if(m_flash_mode==CFI)m_flash_mode=m_cfi_return;else m_flash_mode=ARRAY;
        return nullptr;
    }
    if(m_amd_error)return nullptr;
    if(m_amd_bypass)
    {
        if(m_amd_sequence==7){if(command==0)m_amd_bypass=false;m_amd_sequence=0;return nullptr;}
        if(command==0x90)m_amd_sequence=7;
        else if(command==0xa0)m_setup=WORD_DATA;
        return nullptr;
    }
    if(command==0x98&&a==0x55&&(m_flash_mode==ARRAY||m_flash_mode==SIGNATURE))
    {m_cfi_return=m_flash_mode;m_flash_mode=CFI;m_amd_sequence=0;return nullptr;}
    if(m_flash_mode==SIGNATURE||m_flash_mode==CFI)return nullptr;
    if(command==0x30 && ((m_operation==ERASE&&m_suspended)||m_erase_suspended))
    {resume();return nullptr;}
    switch(m_amd_sequence)
    {
    case 0:m_amd_sequence=(a==0x555&&command==0xaa)?1:0;break;
    case 1:m_amd_sequence=(a==0x2aa&&command==0x55)?2:0;break;
    case 2:
        m_amd_sequence=0;
        if(a!=0x555)break;
        if(command==0x90)m_flash_mode=SIGNATURE;
        else if(command==0xa0)m_setup=WORD_DATA;
        else if(command==0x20)m_amd_bypass=true;
        else if(command==0x80 && !m_operation&&!m_erase_suspended)m_amd_sequence=3;
        break;
    case 3:m_amd_sequence=(a==0x555&&command==0xaa)?4:0;break;
    case 4:m_amd_sequence=(a==0x2aa&&command==0x55)?5:0;break;
    case 5:
        m_amd_sequence=0;
        if(command==0x30||(a==0x555&&command==0x10))
        {if(!m_work_session)return "NOR_REFERENCE_SESSION_WRITE_DISABLED";
            if(m_rp->read()!=2){for(unsigned n=0;n<block_count();++n)if((command==0x10||n==block(byte))&&protection_unknown(n))return "NOR_ST_INTERRUPTED_PROTECTION_UNDEFINED";}
            amd_select(byte,command==0x10);}
        break;
    default:m_amd_sequence=0;break;
    }
    return nullptr;
}

class dana_m28w640hcb_device : public dana_nor_flash_device
{
public:
    dana_m28w640hcb_device(machine_config const &c,char const *tag,device_t *owner,u32 clock=0)
        : dana_nor_flash_device(c,DANA_M28W640HCB,tag,owner,clock,false) { }
};
class dana_m29w320db_device : public dana_nor_flash_device
{
public:
    dana_m29w320db_device(machine_config const &c,char const *tag,device_t *owner,u32 clock=0)
        : dana_nor_flash_device(c,DANA_M29W320DB,tag,owner,clock,true) { }
};

// One socket, one selected NOR card, one array. The option is resolved before
// allocation: the 4 MiB part never allocates/maps a second or 8 MiB flash array.
class dana_nor_socket_device : public device_t, public device_slot_interface
{
public:
    dana_nor_socket_device(machine_config const &c,char const *tag,device_t *owner,u32 clock=0)
        : device_t(c,DANA_NOR_SOCKET,tag,owner,clock),device_slot_interface(c,*this)
    {
        option_add("m28w640hcb",DANA_M28W640HCB);option_add("m29w320db",DANA_M29W320DB);
        set_default_option("m28w640hcb");set_fixed(false);
    }
    dana_nor_flash_device &chip() const {return downcast<dana_nor_flash_device &>(*get_card_device());}
    u32 array_bytes() const {return chip().array_bytes();}
    void mount_seed(u8 const *seed,u32 bytes,bool factory,u8 const *hash){chip().mount_seed(seed,bytes,factory,hash);}
    char const *read_fault(u32 a) const {return chip().read_fault(a);}
    u16 bus_read(u32 a){return chip().bus_read(a);}
    char const *bus_write(u32 a,u16 data,u16 mask){return chip().bus_write(a,data,mask);}
    void pins_changed(){if(get_card_device()&&get_card_device()->started())chip().pins_changed();}
protected:
    virtual void device_start() override {if(!get_card_device())fatalerror("Select exactly one evidenced NOR chip profile");}
};

#endif
