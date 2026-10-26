// license:BSD-3-Clause
// Original ISP1161A1 packet-level PTD executor. Philips Rev03 Table 4/5.
// No code imported from Linux (GPL) or QEMU (GPL).
#pragma once

#include <algorithm>
#include <cstddef>
#include <cstdint>

namespace isp1161a1 {

enum class handshake : std::uint8_t {
    ack, nak, stall, timeout, crc, bitstuff, toggle_mismatch, pid_error
};
enum class pid : std::uint8_t { setup=0, out=1, in=2 };

struct transaction {
    std::uint8_t address=0, endpoint=0;
    pid direction=pid::setup;
    bool low_speed=false, isochronous=false, toggle=false;
    std::uint16_t maximum_packet=0;
};
struct reply {
    handshake status=handshake::timeout;
    std::uint16_t size=0;
};
struct outcome {
    std::size_t descriptors=0, completed=0, pending=0;
    bool malformed=false;
};

// A packet transport is a physical port+attached USB function, not a register.
// The caller is responsible for connection state and packet routing.
// Transport(request, OUT/source, IN/destination, packet length) -> reply.
template<typename Transport>
outcome execute(std::uint8_t *ram, std::size_t length, Transport&& transport,
                bool interrupt_one_packet=false)
{
    outcome result{};
    std::size_t offset=0;
    while(offset<length) {
        if(length-offset<8) {result.malformed=true;break;}
        std::uint8_t *const d=ram+offset;
        bool const last=bool(d[3]&0x08);
        std::uint16_t const total=std::uint16_t(d[4] | ((d[5]&3)<<8));
        std::uint16_t const maximum=std::uint16_t(d[2] | ((d[3]&3)<<8));
        std::size_t const next=(offset+8+total+3)&~std::size_t(3);
        if(total>1023 || maximum>1023 || !maximum || next>length) {
            result.malformed=true;break;
        }
        ++result.descriptors;
        if (d[1]&0x08) {
            std::uint8_t const direction=(d[5]>>2)&3;
            if(direction==3) {result.malformed=true;break;}
            transaction tx{std::uint8_t(d[6]&0x7f),
                std::uint8_t(d[3]>>4),pid(direction),
                bool(d[3]&4),bool(d[6]&0x80),
                bool(d[1]&4),maximum};
            std::uint16_t done=std::uint16_t(d[0] | ((d[1]&3)<<8));
            if(done>total) {result.malformed=true;break;}
            handshake error=handshake::ack;
            bool wait=false;
            unsigned packets=0;
            while(done<total || (total==0 && !packets)) {
                std::uint16_t const requested=std::uint16_t(
                    std::min<std::size_t>(maximum,total-done));
                std::uint8_t *const payload=d+8+done;
                // SETUP uses DATA0, while successful DATA packets toggle.
                if(tx.direction==pid::setup)tx.toggle=false;
                reply const rx=transport(tx,
                    tx.direction==pid::in ? nullptr : payload,
                    tx.direction==pid::in ? payload : nullptr,requested);
                ++packets;
                if(rx.status==handshake::nak) {wait=true;break;}
                if(rx.status!=handshake::ack) {error=rx.status;break;}
                if(rx.size>requested) {error=handshake::pid_error;break;}
                done+=rx.size;
                if(rx.size)tx.toggle=!tx.toggle;
                // A short IN packet terminates a successful transfer.
                if(tx.direction==pid::in && rx.size<requested)break;
                if(rx.size<requested && requested) {wait=true;break;}
                if(tx.isochronous ||
                    (interrupt_one_packet && (d[5]&0x20)))break;
                if(done==total)break;
            }
            d[0]=std::uint8_t(done);
            d[1]=std::uint8_t((d[1]&~std::uint8_t(0x07)) |
                ((done>>8)&3) | (tx.toggle ? 4 : 0));
            if(!wait) {
                std::uint8_t cc=0;
                switch(error) {
                case handshake::ack:cc=0;break;
                case handshake::stall:cc=4;break;
                case handshake::timeout:cc=5;break;
                case handshake::crc:cc=1;break;
                case handshake::bitstuff:cc=2;break;
                case handshake::toggle_mismatch:cc=3;break;
                case handshake::pid_error:cc=6;break;
                case handshake::nak:break;
                }
                d[1]=std::uint8_t((d[1]&0x07)|(cc<<4)); // Active=0
                ++result.completed;
            } else {
                d[1]=std::uint8_t((d[1]&0x0f)); // stays Active=1
                ++result.pending;
            }
        }
        if(last)break;
        offset=next;
    }
    return result;
}
} // namespace isp1161a1
