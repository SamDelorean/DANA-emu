// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
// Compile-time write-path regressions. No CPU or executable.
#include "../src/mame/skeleton/alphasdana_sd.h"
using namespace dana_sd;
struct disk
{
    std::array<byte,4096> bytes{};
    bool inserted=true,protected_media=true,fail=false,short_write=false,flush_error=false;
    unsigned writes=0;
    constexpr bool present() const { return inserted; }
    constexpr bool write_protected() const { return protected_media; }
    constexpr bool read_sector(dword lba,byte *out)
    {
        if (!inserted || lba>=8) return false;
        for (unsigned i=0;i<512;++i) out[i]=bytes[lba*512+i];
        return true;
    }
    constexpr bool write_sector(dword lba,const byte *in)
    {
        ++writes;
        if (!inserted || protected_media || lba>=8 || fail) return false;
        for (unsigned i=0;i<(short_write ? 19U : 512U);++i) bytes[lba*512+i]=in[i];
        return !short_write && !flush_error;
    }
};
constexpr byte wire(card &c,disk &m,byte value=0xff)
{ byte r=0;for (int b=7;b>=0;--b) r=(r<<1)|c.bit((value>>b)&1,m);return r; }
constexpr byte command(card &c,disk &m,byte op,dword arg=0)
{
    byte p[6]={byte(0x40|op),byte(arg>>24),byte(arg>>16),byte(arg>>8),byte(arg),0};p[5]=crc7(p,5);
    for (byte v:p) wire(c,m,v);
    if (op==12) wire(c,m);
    for (unsigned n=0;n<8;++n) {byte r=wire(c,m);if (!(r&0x80))return r;}
    return 0xff;
}
constexpr bool ready(card &c,disk &m)
{
    c.blocks=8;c.power(true);
    for (unsigned i=0;i<10;++i) wire(c,m);
    c.select(true);
    return command(c,m,0)==1 && command(c,m,55)==1 && command(c,m,41)==0 && command(c,m,59,1)==0;
}
constexpr byte send_block(card &c,disk &m,byte token,byte seed,bool crc_ok=true)
{
    std::array<byte,512> b{};for (unsigned i=0;i<512;++i)b[i]=seed+i;
    word const crc=crc16(b.data(),512) ^ (crc_ok ? 0 : 1);
    wire(c,m,token);for (byte v:b)wire(c,m,v);wire(c,m,crc>>8);wire(c,m,crc);
    for (unsigned i=0;i<8;++i) {byte r=wire(c,m);if (r!=0xff)return r;}
    return 0xff;
}
constexpr unsigned finish(card &c,disk &m)
{
    unsigned busy=0;
    for (unsigned i=0;i<16;++i) {byte r=wire(c,m);if(r==0xff)return busy;if(r!=0)return 99;++busy;}
    return 99;
}
constexpr bool verify(card &c,disk &m,unsigned sector,byte seed)
{
    if(command(c,m,17,sector*512)!=0)return false;
    bool found=false;for(unsigned i=0;i<8;++i)if(wire(c,m)==0xfe){found=true;break;}
    if(!found)return false;
    for(unsigned i=0;i<512;++i)if(wire(c,m)!=byte(seed+i))return false;
    wire(c,m);wire(c,m);return true;
}
constexpr bool single_and_reopen()
{
    disk d;card c;if(!ready(c,d))return false;d.protected_media=false;
    if(command(c,d,24,512)!=0 || send_block(c,d,0xfe,0x37)!=5 || finish(c,d)==0 || d.writes!=1)return false;
    if(!verify(c,d,1,0x37))return false;
    card fresh;if(!ready(fresh,d) || !verify(fresh,d,1,0x37))return false;
    return command(fresh,d,13)==0 && wire(fresh,d)==0;
}
static_assert(single_and_reopen(),"CMD24 complete block, accepted/busy/readback and independent card reopen");
constexpr bool multiple_and_stop()
{
    disk d;d.protected_media=false;card c;if(!ready(c,d))return false;
    if(command(c,d,25,2*512)!=0)return false;
    if(send_block(c,d,0xfc,0x42)!=5 || finish(c,d)==0)return false;
    if(send_block(c,d,0xfc,0x53)!=5 || finish(c,d)==0)return false;
    wire(c,d,0xfd);finish(c,d);
    if(c.multi_write || c.write_left || d.writes!=2)return false;
    return verify(c,d,2,0x42)&&verify(c,d,3,0x53);
}
static_assert(multiple_and_stop(),"CMD25 FC blocks, FD stop, consecutive sectors, busy and CMD17 readback");
constexpr bool crc_and_wp()
{
    disk d;card c;if(!ready(c,d))return false;
    if(command(c,d,24,0)!=0 || send_block(c,d,0xfe,1)!=0x0d || d.writes)return false;
    finish(c,d);if(command(c,d,13)!=0 || wire(c,d)!=0x20)return false;
    d.protected_media=false;
    if(command(c,d,24,0)!=0 || send_block(c,d,0xfe,2,false)!=0x0b || d.writes)return false;
    finish(c,d);
    if(command(c,d,25,0)!=0 || send_block(c,d,0xfc,3,false)!=0x0b || d.writes)return false;
    finish(c,d);
    if(send_block(c,d,0xfc,4)!=5)return false;
    finish(c,d);wire(c,d,0xfd);finish(c,d);
    if(!verify(c,d,0,4))return false; // failed CRC did not advance the LBA
    if(command(c,d,59,0)!=0 || command(c,d,24,512)!=0)return false;
    return send_block(c,d,0xfe,5,false)==5; // CRC ignored only when explicitly disabled
}
static_assert(crc_and_wp(),"default WP, independent explicit enable, CRC rejection/retry and CRC-off contract");
constexpr bool partial_power_eject()
{
    disk d;d.protected_media=false;card c;if(!ready(c,d))return false;
    if(command(c,d,24,0)!=0)return false;
    wire(c,d,0xfd);wire(c,d,0xfc); // wrong tokens must not start CMD24 data
    if(c.write_left!=0xffff)return false;
    wire(c,d,0xfe);for(unsigned i=0;i<511;++i)wire(c,d,0x81);
    if(d.writes)return false;
    card saved=c;disk copied=d; // restore within partial block, no host commit yet
    wire(saved,copied,0x81);wire(saved,copied,0);wire(saved,copied,0); // invalid CRC
    if(copied.writes)return false;
    c.select(false);c.select(true);if(c.write_left || d.writes)return false;
    if(command(c,d,24,0)!=0)return false;
    wire(c,d,0xfe);for(unsigned i=0;i<512;++i)wire(c,d,0x42);
    c.power(false);if(d.writes)return false; // no CRC => no write
    c=card{};if(!ready(c,d)||command(c,d,24,0)!=0)return false;
    wire(c,d,0xfe);for(unsigned i=0;i<12;++i)wire(c,d,0x33);
    d.inserted=false;
    if(wire(c,d)!=0xff || d.writes)return false;
    return true;
}
static_assert(partial_power_eject(),"wrong tokens, missing data/CRC, CS/power/ejection and partial snapshot cannot commit");
constexpr bool failures_and_bounds()
{
    disk d;d.protected_media=false;card c;if(!ready(c,d))return false;
    if(command(c,d,24,8*512)!=0x20 || command(c,d,25,1)!=0x20 || d.writes)return false;
    for(unsigned fault=0;fault<3;++fault)
    {
        d.fail=fault==0;d.short_write=fault==1;d.flush_error=fault==2;
        if(command(c,d,24,0)!=0 || send_block(c,d,0xfe,0x54)!=0x0d)return false;
        finish(c,d);if(command(c,d,13)!=0 || wire(c,d)!=4)return false;
    }
    if(d.writes!=3)return false;
    d.fail=d.short_write=d.flush_error=false;
    if(command(c,d,25,7*512)!=0 || send_block(c,d,0xfc,0x65)!=5)return false;
    finish(c,d);
    if(send_block(c,d,0xfc,0x76)!=0x0d || d.writes!=4)return false;
    finish(c,d);wire(c,d,0xfd);finish(c,d);
    return command(c,d,13)==0 && wire(c,d)==0x80;
}
static_assert(failures_and_bounds(),"backend failure, short write, failed flush never accept; bounds before backend");
constexpr bool isolation_and_protection_change()
{
    disk a,b;card ca,cb;if(!ready(ca,a)||!ready(cb,b))return false;
    a.protected_media=false;
    if(command(ca,a,24,0)!=0 || send_block(ca,a,0xfe,0xa1)!=5)return false;
    finish(ca,a);
    if(command(cb,b,24,0)!=0 || send_block(cb,b,0xfe,0xb2)!=0x0d || b.writes)return false;
    finish(cb,b);b.protected_media=false;
    if(command(cb,b,24,0)!=0 || send_block(cb,b,0xfe,0xb2)!=5)return false;
    finish(cb,b);
    if(!verify(ca,a,0,0xa1)||!verify(cb,b,0,0xb2))return false;
    if(command(ca,a,24,512)!=0)return false;
    wire(ca,a,0xfe);for(unsigned i=0;i<512;++i)wire(ca,a,0x55);
    a.protected_media=true;
    std::array<byte,512> pending{};for(auto &v:pending)v=0x55;
    word const crc=crc16(pending.data(),512);wire(ca,a,crc>>8);wire(ca,a,crc);
    byte response=0xff;for(unsigned i=0;i<8 && response==0xff;++i)response=wire(ca,a);
    if(response!=0x0d)return false;
    finish(ca,a);
    return a.writes==1 && b.writes==1;
}
static_assert(isolation_and_protection_change(),"two backing media, default independent WP and protection during a frame");
