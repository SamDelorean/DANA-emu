// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
// Compile-time component checks only. No main, CPU, firmware or executable.
#include "../src/mame/skeleton/alphasdana_sd.h"
using namespace dana_sd;
struct medium
{
    bool inserted=true, failed=false;
    byte identity=0x12;
    unsigned reads=0;
    constexpr bool present() const { return inserted; }
    constexpr bool write_protected() const { return true; }
    constexpr bool write_sector(dword,const byte *) { return false; }
    constexpr bool read_sector(dword lba,byte *out)
    {
        ++reads;
        if (!inserted || failed) return false;
        for (unsigned i=0;i<512;++i) out[i]=byte(identity+lba+i);
        return true;
    }
};
constexpr byte wire(card &c,medium &m,byte value=0xff)
{
    byte result=0;
    for (int i=7;i>=0;--i) result=(result<<1)|c.bit((value>>i)&1,m);
    return result;
}
constexpr void clocks(card &c,medium &m)
{
    c.power(true); c.select(false);
    for (unsigned i=0;i<10;++i) wire(c,m);
    c.select(true);
}
constexpr byte command(card &c,medium &m,byte op,dword arg=0,bool valid_crc=true)
{
    byte packet[6]={byte(0x40|op),byte(arg>>24),byte(arg>>16),byte(arg>>8),byte(arg),0};
    packet[5]=crc7(packet,5);
    if (!valid_crc) packet[5]^=2;
    for (auto value:packet) wire(c,m,value);
    if (op==12) wire(c,m); // SPI CMD12 stuff byte
    for (unsigned i=0;i<8;++i)
    { byte const r=wire(c,m); if (!(r&0x80)) return r; }
    return 0xff;
}
constexpr bool initialize(card &c,medium &m)
{
    c.blocks=2048; clocks(c,m);
    if (command(c,m,0)!=1 || command(c,m,8,0x1aa)!=1) return false;
    if (wire(c,m)!=0 || wire(c,m)!=0 || wire(c,m)!=1 || wire(c,m)!=0xaa) return false;
    return command(c,m,55)==1 && command(c,m,41,0x40000000)==0;
}
constexpr bool token(card &c,medium &m,byte expected=0xfe)
{
    for (unsigned n=0;n<8;++n) { byte const v=wire(c,m); if (v!=0xff) return v==expected; }
    return false;
}
constexpr bool init_crc_and_power()
{
    byte cmd0[5]={0x40,0,0,0,0},cmd8[5]={0x48,0,0,1,0xaa};
    if (crc7(cmd0,5)!=0x95 || crc7(cmd8,5)!=0x87) return false;
    byte digits[9]={'1','2','3','4','5','6','7','8','9'};
    if (crc16(digits,9)!=0x31c3) return false;
    medium m; card c;c.blocks=2048;
    if (wire(c,m)!=0xff || command(c,m,0)!=0xff) return false;
    c.power(true);c.select(true);
    if (command(c,m,0)!=0xff) return false; // no 74-clock entry yet
    clocks(c,m);
    if (command(c,m,0,0,false)!=9 || command(c,m,0)!=1) return false;
    c.select(false);c.select(true);
    if (command(c,m,55)!=1 || command(c,m,41,0x40000000)!=0) return false;
    c.select(false);c.select(true);
    if (command(c,m,13)!=0 || wire(c,m)!=0) return false; // deselect preserves ready
    c.power(false);c.power(true);
    if (!c.idle || c.selected || c.blocks!=2048 || c.initial_clocks) return false;
    return true;
}
static_assert(init_crc_and_power(),"initial clocks, CRC7, deselect and power state");

constexpr bool identity_and_capacity()
{
    medium m; card c;if (!initialize(c,m)) return false;
    if (command(c,m,9)!=0 || !token(c,m)) return false;
    byte csd[16];for (auto &v:csd) v=wire(c,m);
    word crc=word(wire(c,m))<<8;crc|=wire(c,m);
    if (crc!=crc16(csd,16) || csd[15]!=crc7(csd,15) || !(csd[14]&0x10)) return false;
    unsigned size=((csd[6]&3)<<10)|(unsigned(csd[7])<<2)|(csd[8]>>6);
    unsigned mult=((csd[9]&3)<<1)|(csd[10]>>7);
    if (((size+1)<<(mult+2))!=c.blocks) return false;
    if (command(c,m,10)!=0 || !token(c,m)) return false;
    byte cid[16];for (auto &v:cid) v=wire(c,m);
    word cid_crc=word(wire(c,m))<<8;cid_crc|=wire(c,m);
    if (cid[0]!='M' || cid[15]!=crc7(cid,15) || cid_crc!=crc16(cid,16)) return false;
    bool hc;byte cm;word sz;
    if (card::geometry(0,hc,cm,sz) || card::geometry(17,hc,cm,sz)) return false;
    if (!card::geometry(0x4000000,hc,cm,sz) || !hc) return false;
    if (card::geometry(0x4000001,hc,cm,sz)) return false;
    card big;big.blocks=0x4000000;clocks(big,m);
    if (command(big,m,0)!=1 || command(big,m,55)!=1 || command(big,m,41,0)!=1) return false;
    if (command(big,m,55)!=1 || command(big,m,41,0x40000000)!=0 || !big.high_capacity) return false;
    if (command(big,m,58)!=0 || wire(big,m)!=0xc0 || wire(big,m)!=0xff || wire(big,m)!=0x80 || wire(big,m)!=0) return false;
    if (command(big,m,17,2)!=0 || !token(big,m) || wire(big,m)!=byte(m.identity+2)) return false;
    return true;
}
static_assert(identity_and_capacity(),"CSD/CID CRC and exact SDSC/SDHC/OCR capacity");

constexpr bool two_cards_and_reads()
{
    card a,b;medium x,y;y.identity=0xb7;
    if (!initialize(a,x) || !initialize(b,y)) return false;
    if (command(a,x,17,512)!=0 || command(b,y,17,1024)!=0 || !token(a,x) || !token(b,y)) return false;
    byte aa[512],bb[512];
    for (unsigned i=0;i<512;++i)
    { aa[i]=wire(a,x);bb[i]=wire(b,y);
      if (aa[i]!=byte(x.identity+1+i) || bb[i]!=byte(y.identity+2+i)) return false; }
    word ca=word(wire(a,x))<<8;ca|=wire(a,x);
    word cb=word(wire(b,y))<<8;cb|=wire(b,y);
    if (ca!=crc16(aa,512) || cb!=crc16(bb,512) || x.reads!=1 || y.reads!=1) return false;
    // A save/restore of in-progress wire state reproduces the remaining bytes.
    if (command(a,x,17,0)!=0 || !token(a,x)) return false;
    for (unsigned i=0;i<13;++i) wire(a,x);
    card restored=a;medium mirror=x;
    for (unsigned i=0;i<501;++i) if (wire(a,x)!=wire(restored,mirror)) return false;
    b.power(false);if (wire(b,y)!=0xff || a.idle || a.blocks!=2048) return false;
    return true;
}
static_assert(two_cards_and_reads(),"independent sector data/CRC and partial-frame restore");

constexpr bool multiblock_errors_and_absence()
{
    card c;medium m;if (!initialize(c,m)) return false;
    if (command(c,m,17,1)!=0x20 || command(c,m,17,c.blocks*512)!=0x20 || m.reads) return false;
    if (command(c,m,18,0)!=0 || !token(c,m)) return false;
    for (unsigned n=0;n<2;++n)
    {
        for (unsigned i=0;i<512;++i) if (wire(c,m)!=byte(m.identity+n+i)) return false;
        wire(c,m);wire(c,m);
        if (!n && !token(c,m)) return false;
    }
    if (command(c,m,12)!=0 || c.multi_read) return false;
    m.failed=true;
    if (command(c,m,17,0)!=0 || !token(c,m,0x09)) return false;
    m.inserted=false;
    if (command(c,m,0)!=0xff || wire(c,m)!=0xff) return false;
    m.inserted=true;c.select(false);c.select(true);m.failed=false;
    if (command(c,m,16,1024)!=0x40 || command(c,m,16,512)!=0) return false;
    if (command(c,m,60)!=4 || command(c,m,59,1)!=0) return false;
    if (command(c,m,13,0,false)!=8) return false;
    // Abort a partial command without altering the independent medium.
    wire(c,m,0x51);wire(c,m,0);c.select(false);c.select(true);
    if (command(c,m,13)!=0) return false;
    for (unsigned i=0;i<3;++i) c.bit(true,m);
    c.select(false); c.select(true);
    if (c.bit_count || command(c,m,13)!=0) return false;
    return true;
}
static_assert(multiblock_errors_and_absence(),"CMD18/CMD12, address, failed I/O, removal, CRC and partial CS");

constexpr bool readonly_writes()
{
    card c;medium m;if (!initialize(c,m)) return false;
    for (byte op:{byte(24),byte(25)})
    {
        if (command(c,m,op,0)!=0) return false;
        wire(c,m,op==24 ? 0xfe : 0xfc);
        for (unsigned i=0;i<514;++i) wire(c,m,0x5a);
        if (!token(c,m,0x0d)) return false;
        if (op==25)
        { wire(c,m,0xfd); for (unsigned i=0;i<8;++i) if (wire(c,m)==0xff && !c.write_reply) break; }
        if (command(c,m,13)!=0 || wire(c,m)!=0x20) return false;
    }
    return m.reads==0; // backend intentionally has NO write method
}
static_assert(readonly_writes(),"CMD24/CMD25 reject writes and report WP; no host write API");

constexpr bool fifo_masks_irq_and_clock()
{
    controller spi;
    if (spi.control || spi.mask || spi.spc || spi.flags()!=1) return false;
    if (!spi.push_tx(0xffff,0xffff) || spi.tx_count) return false;
    spi.control=0x060f;
    for (unsigned i=0;i<8;++i) if (!spi.push_tx(i,0xffff)) return false;
    if (spi.push_tx(9,0xffff) || (spi.flags()&7)!=6) return false;
    if (spi.cycles()!=64 || spi.bits()!=16) return false;
    for (unsigned i=0;i<8;++i) if (spi.pop_tx()!=i) return false;
    spi.control=0xa607; if (spi.cycles()!=1024) return false;
    spi.mask=0x0800;
    if (spi.irq() || !spi.push_rx(0x1234) || !spi.irq()) return false;
    if (spi.pop_rx(false)!=0x1234 || spi.rx_count!=1) return false;
    if (!(spi.status(false)&0x40) || !(spi.status(true)&0x40) || (spi.status(true)&0x40)) return false;
    if (spi.pop_rx(true)!=0x1234 || spi.rx_count || spi.irq()) return false;
    spi.push_tx(0xab00,0xff00);spi.push_tx(0x00cd,0x00ff);
    if (spi.pop_tx()!=0xab09 || spi.pop_tx()!=0xabcd) return false;
    for (unsigned i=0;i<8;++i) if (!spi.push_rx(i)) return false;
    return !spi.push_rx(9) && (spi.flags()&0x38)==0x38;
}
static_assert(fifo_masks_irq_and_clock(),"FIFO bounds/lanes/status, side effects, IRQ and divided clock");
