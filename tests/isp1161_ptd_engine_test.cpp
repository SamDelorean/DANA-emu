// SPDX-License-Identifier: BSD-3-Clause
// Compile: clang++-21 -std=c++20 -Wall -Wextra -Werror -I. tests/isp1161_ptd_engine_test.cpp -o /tmp/ptd-test
#include "../src/mame/skeleton/isp1161_ptd.h"
#include <array>
#include <cstdint>
#include <iostream>
#include <vector>
using namespace isp1161a1;
using u8=std::uint8_t;
static std::array<u8,24> descriptor(std::uint16_t length,pid direction,
        bool last=true, u8 endpoint=0)
{
    std::array<u8,24> p{};
    p[1]=0x08; // Active
    p[2]=8; // MaxPacketSize
    p[3]=u8((endpoint<<4) | (last?8:0));
    p[4]=u8(length);
    p[5]=u8(((length>>8)&3)|(unsigned(direction)<<2));
    p[6]=0; // address 0, control format
    return p;
}
#define CHECK(x) do {if(!(x)){std::cerr<<"Failed "<<__LINE__<<": "<<#x<<"\n";return 1;}}while(0)
int main()
{
    {
        // SETUP GET_DESCRIPTOR, followed in the next PTD by the USB IN
        // data packet. Real USB control setup/data/status are separate TDs.
        auto p=descriptor(8,pid::setup);
        for(int i=0;i<8;i++)p[8+i]=u8(i+1);
        auto out=execute(p.data(),16,[](transaction const &t,
            u8 const *source,u8 *,std::uint16_t len)->reply {
            if(t.direction!=pid::setup || t.address!=0 || t.endpoint!=0 ||
                len!=8 || !source || source[0]!=1 || source[7]!=8)
                return {handshake::stall,0};
            return {handshake::ack,len};
        });
        CHECK(!out.malformed && out.descriptors==1 && out.completed==1);
        CHECK(!(p[1]&0x08) && !(p[1]&0xf0) && p[0]==8);
        auto in=descriptor(8,pid::in);
        out=execute(in.data(),16,[](transaction const &t,
            u8 const *,u8 *target,std::uint16_t len)->reply {
            if(t.direction!=pid::in || !target || len!=8)
                return {handshake::stall,0};
            for(unsigned j=0;j<len;j++)target[j]=u8(j+0x20);
            return {handshake::ack,len};
        });
        CHECK(out.completed==1 && in[8]==0x20 && in[15]==0x27);
    }
    {
        auto p=descriptor(8,pid::in);
        auto out=execute(p.data(),16,[](transaction const &,u8 const *,u8 *,
          std::uint16_t)->reply{return {handshake::nak,0};});
        CHECK(out.pending==1 && out.completed==0 && (p[1]&0x08));
        CHECK(!(p[1]&0xf0));
        out=execute(p.data(),16,[](transaction const &,u8 const *,u8 *,
          std::uint16_t)->reply{return {handshake::stall,0};});
        CHECK(out.completed==1 && !(p[1]&0x08) && (p[1]&0xf0)==0x40);
    }
    {
        auto p=descriptor(8,pid::in);
        auto out=execute(p.data(),16,[](transaction const &,u8 const *,u8 *,
          std::uint16_t)->reply{return {handshake::timeout,0};});
        CHECK(out.completed==1 && (p[1]&0xf0)==0x50 && !(p[1]&0x08));
        p=descriptor(8,pid::out);
        out=execute(p.data(),16,[](transaction const &,u8 const *,u8 *,
          std::uint16_t)->reply{return {handshake::crc,0};});
        CHECK((p[1]&0xf0)==0x10);
    }
    {
        // Two PTDs, first packet (five bytes) DWORD-padded to position16.
        std::array<u8,32> p{};
        p[1]=0x08; p[2]=8;p[4]=5;p[5]=4;
        p[16+1]=0x08;p[16+2]=8;p[16+3]=8;p[16+4]=4;p[16+5]=4;
        unsigned count=0;
        const auto out=execute(p.data(),32,[&](transaction const &,u8 const *,
          u8 *,std::uint16_t size)->reply{++count;return {handshake::ack,size};});
        CHECK(!out.malformed && count==2 && out.descriptors==2 && out.completed==2);
        CHECK(p[0]==5 && p[16]==4);
    }
    {
        // A corrupt descriptor cannot read/write outside its upload RAM.
        auto p=descriptor(8,pid::in);
        auto out=execute(p.data(),10,[](transaction const &,u8 const *,u8 *,
          std::uint16_t)->reply{return {handshake::ack,0};});
        CHECK(out.malformed && out.completed==0);
    }
    std::cout<<"PASS original Philips PTD SETUP/IN, NAK, STALL, timeout,"
                " CRC, multi-PTD DWORD alignment, bounds\n";
}
