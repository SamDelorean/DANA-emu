// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
#ifndef MAME_SKELETON_ALPHASDANA_SD_H
#define MAME_SKELETON_ALPHASDANA_SD_H

#include <array>
#include <cstdint>

// Driver-local SD SPI wire protocol. No CPU, filesystem or host file API.
// SD Physical Layer Simplified Specification, SPI command/response tables;
// pinned MAME spi_sdcard.cpp is the BSD interface/CRC/data-token reference.
// Unlike that donor's CHS image path, capacity here is exact raw sector count;
// failed reads cannot send stale data and deselection does not reset idle state.
namespace dana_sd {
using byte = std::uint8_t;
using word = std::uint16_t;
using dword = std::uint32_t;
using qword = std::uint64_t;
constexpr byte crc7(const byte *p, unsigned size)
{
    byte crc=0;
    for (unsigned n=0;n<size;++n)
        for (unsigned bit=0;bit<8;++bit)
        {
            bool const feedback=((p[n]>>(7-bit)) ^ (crc>>6)) & 1;
            crc=(crc<<1) & 0x7f;
            if (feedback) crc^=0x09;
        }
    return (crc<<1) | 1;
}
constexpr word crc16(const byte *p, unsigned size)
{
    word crc=0;
    for (unsigned n=0;n<size;++n)
    {
        crc^=word(p[n])<<8;
        for (unsigned bit=0;bit<8;++bit) crc=(crc<<1) ^ ((crc & 0x8000) ? 0x1021 : 0);
    }
    return crc;
}

struct card
{
    std::array<byte,6> cmd{};
    std::array<byte,520> reply{};
    word reply_pos=0, reply_size=0, write_left=0;
    byte command_size=0, bit_count=0, input=0, output=0xff;
    byte initial_clocks=0, status=0;
    dword blocks=0, next_block=0;
    bool powered=false, selected=false, idle=true, app=false;
    bool crc_enabled=false, high_capacity=false, multi_read=false, multi_write=false;

    // SDSC CSD v1 (512-byte blocks) or SDHC CSD v2, with exact capacity.
    static constexpr bool geometry(dword count, bool &hc, byte &mult, word &size)
    {
        for (unsigned m=0;m<8;++m)
        {
            unsigned const unit=1U<<(m+2);
            if (count && count%unit==0 && count/unit<=4096)
            { hc=false; mult=m; size=count/unit-1; return true; }
        }
        if (count>=1024 && count%1024==0 && count<=0x4000000)
        { hc=true; mult=0; size=0; return true; }
        return false;
    }
    constexpr void power(bool on)
    {
        if (powered!=on)
        {
            dword const capacity=blocks;
            *this=card{}; blocks=capacity; powered=on;
        }
    }
    constexpr void select(bool on)
    {
        if (selected!=on)
        {
            selected=on; command_size=bit_count=input=0; output=0xff;
            reply_size=reply_pos=write_left=0; multi_read=multi_write=false;
        }
    }
    constexpr void response(byte r1)
    { reply_pos=0; reply_size=2; reply[0]=0xff; reply[1]=r1; }
    constexpr void append(byte value) { reply[reply_size++]=value; }
    constexpr void data_crc(unsigned start, unsigned size)
    { word const crc=crc16(reply.data()+start,size); append(crc>>8); append(crc); }
    constexpr void identification(bool csd)
    {
        response(0); append(0xff); append(0xfe);
        unsigned const start=reply_size;
        for (unsigned i=0;i<16;++i) append(0);
        byte *const p=reply.data()+start;
        if (csd)
        {
            byte mult=0; word size=0; bool hc=false;
            geometry(blocks,hc,mult,size);
            p[0]=hc ? 0x40 : 0; p[1]=0x0e; p[3]=0x32;
            p[4]=0x5b; p[5]=0x59; // command classes, READ_BL_LEN=9
            if (hc)
            { dword const c=blocks/1024-1; p[7]=(c>>16)&0x3f; p[8]=c>>8; p[9]=c; }
            else
            { p[6]=(size>>10)&3; p[7]=size>>2; p[8]=(size&3)<<6;
              p[9]=(mult>>1)&3; p[10]=(mult&1)<<7; }
            p[10]|=0x40; p[11]=0x80; p[12]=0x02; p[13]=0x40;
            p[14]=0x10; // TMP_WRITE_PROTECT: all images are opened read-only.
        }
        else
        {
            p[0]='M'; p[1]='M'; p[2]='D'; // virtual card identity, not vendor spoofing
            p[3]='D'; p[4]='A'; p[5]='N'; p[6]='A'; p[7]='R'; p[8]=0x10;
            p[12]=1; p[13]=1; p[14]=0x10;
        }
        p[15]=crc7(p,15); data_crc(start,16);
    }
    constexpr bool address(dword arg, dword &lba) const
    {
        if (!high_capacity && (arg & 511)) return false;
        lba=high_capacity ? arg : arg/512;
        return lba<blocks;
    }
    template<class Media> constexpr void read_block(Media &media, bool r1)
    {
        reply_size=reply_pos=0;
        if (r1) { append(0xff); append(0); }
        append(0xff);
        if (next_block>=blocks || !media.read_sector(next_block,reply.data()+reply_size+1))
        { append(0x09); multi_read=false; return; } // data error + out of range
        append(0xfe); unsigned const start=reply_size; reply_size+=512;
        data_crc(start,512); ++next_block;
    }
    template<class Media> constexpr void execute(Media &media)
    {
        byte const op=cmd[0]&63, r1=idle ? 1 : 0;
        dword const arg=(dword(cmd[1])<<24)|(dword(cmd[2])<<16)|(dword(cmd[3])<<8)|cmd[4];
        bool const was_app=app; app=false;
        if (!(cmd[5]&1) || ((crc_enabled || op==0 || op==8) && crc7(cmd.data(),5)!=cmd[5]))
        { response(r1|8); return; }
        if (op==0)
        { idle=true; high_capacity=false; crc_enabled=false; multi_read=multi_write=false; write_left=0; status=0; response(1); return; }
        if (op==8)
        { response((arg & 0xf00)==0x100 ? r1 : byte(r1|0x40));
          append(0); append(0); append(arg>>8); append(arg); return; }
        if (op==55) { app=true; response(r1); return; }
        if (was_app && op==41)
        {
            byte mult=0; word size=0; bool hc=false; geometry(blocks,hc,mult,size);
            if (hc && !(arg & 0x40000000)) { response(1); return; }
            high_capacity=hc; idle=false; response(0); return;
        }
        if (op==58)
        { response(r1); append((idle ? 0 : 0x80)|(high_capacity ? 0x40 : 0));
          append(0xff); append(0x80); append(0); return; } // OCR 2.7--3.6 V
        if (op==59) { crc_enabled=arg&1; response(r1); return; }
        if (idle) { response(1); return; }
        switch (op)
        {
        case 9: case 10: identification(op==9); break;
        case 12: multi_read=false; reply_size=reply_pos=0;
                 append(0xff); append(0xff); append(0); append(0xff); break; // stuff + R1b
        case 13: response(0); append(status); status=0; break;
        case 16: response(arg==512 ? 0 : 0x40); break;
        case 17: case 18:
            if (!address(arg,next_block)) { response(0x20); break; }
            multi_read=op==18; read_block(media,true); break;
        case 24: case 25:
            if (!address(arg,next_block)) { response(0x20); break; }
            response(0); multi_write=op==25; write_left=0xffff; break;
        default: response(4); break; // explicit SPI illegal-command R1
        }
    }
    template<class Media> constexpr void receive(byte value, Media &media)
    {
        if (write_left)
        {
            if (write_left==0xffff)
            {
                if (multi_write && value==0xfd) { write_left=0; multi_write=false; }
                else if (value==(multi_write ? 0xfc : 0xfe)) write_left=514;
            }
            else if (!--write_left)
            {
                // Consume data + CRC, report write-error and WP violation.
                // There is deliberately no Media::write_sector call.
                status|=0x20; reply_size=reply_pos=0; append(0x0d); append(0xff);
                if (multi_write) write_left=0xffff;
            }
            return;
        }
        if (!command_size && (value & 0xc0)!=0x40) return;
        cmd[command_size++]=value;
        if (command_size==6) { command_size=0; execute(media); }
    }
    template<class Media> constexpr byte exchange(byte value, Media &media)
    {
        if (!powered) return 0xff;
        if (!selected)
        {
            if (value==0xff && initial_clocks<80) initial_clocks+=8;
            return 0xff;
        }
        if (!media.present() || initial_clocks<74) return 0xff;
        if (reply_pos==reply_size && multi_read && !command_size && (value&0xc0)!=0x40)
            read_block(media,false);
        byte const result=reply_pos<reply_size ? reply[reply_pos++] : 0xff;
        receive(value,media);
        return result;
    }
    // MSB first; works with 1..16-bit controller words and partial-byte CS abort.
    template<class Media> constexpr bool bit(bool mosi, Media &media)
    {
        bool const result=powered && selected && media.present() ? bool(output&0x80) : true;
        input=(input<<1)|mosi; output=(output<<1)|1;
        if (++bit_count==8)
        { bit_count=0; output=exchange(input,media); input=0; }
        return result;
    }
};

struct controller
{
    std::array<word,8> tx{},rx{};
    word control=0,mask=0,spc=0,last_tx=0,last_rx=0;
    byte tx_head=0,rx_head=0,tx_count=0,rx_count=0;
    bool rx_edge=false;
    constexpr byte flags() const
    { return (rx_edge ? 0x40 : 0) | (rx_count==8 ? 0x20 : 0) | (rx_count>=4 ? 0x10 : 0)
        | (rx_count ? 8 : 0) | (tx_count==8 ? 4 : 0) | (tx_count>=4 ? 2 : 0) | (!tx_count ? 1 : 0); }
    constexpr bool irq() const { return flags() & (mask>>8); }
    constexpr word status(bool side_effects)
    { word const result=mask|flags(); if (side_effects) rx_edge=false; return result; }
    constexpr word pop_rx(bool side_effects)
    {
        word const result=rx_count ? rx[rx_head] : last_rx;
        if (side_effects && rx_count) { rx_head=(rx_head+1)&7; --rx_count; last_rx=result; }
        return result;
    }
    constexpr bool push_tx(word data,word lanes)
    {
        last_tx=(last_tx & ~lanes)|(data & lanes);
        if (!(control&0x200)) return true;
        if (tx_count==8) return false;
        tx[(tx_head+tx_count)&7]=last_tx; ++tx_count; return true;
    }
    constexpr word pop_tx()
    { word const value=tx[tx_head]; tx_head=(tx_head+1)&7; --tx_count; return value; }
    constexpr bool push_rx(word data)
    {
        if (rx_count==8) return false;
        if (!rx_count) rx_edge=true;
        rx[(rx_head+rx_count)&7]=data; ++rx_count; return true;
    }
    constexpr unsigned bits() const { return (control&15)+1; }
    constexpr unsigned cycles() const { return (4U<<((control>>13)&7))*bits(); }
};
} // namespace dana_sd
#endif
