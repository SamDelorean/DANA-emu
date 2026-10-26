// license:BSD-3-Clause
// Motorola MC68VZ328UM section 17.1.2: UART bootstrap B-records.
// The parser does NOT bypass the VZ memory bus or manufacture a ROM image.
#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

namespace vz328_bootstrap {
struct record {
    std::uint32_t address=0;
    std::uint8_t count=0;
    std::array<std::uint8_t,31> data{};
    bool execute() const {return count==0;}
};
struct program {
    std::vector<record> records;
    std::string error;
    bool valid() const {return error.empty();}
};
inline int hex_digit(char c) {
    if(c>='0' && c<='9') return c-'0';
    if(c>='A' && c<='F') return c-'A'+10;
    return -1;  // Manufacturer requires uppercase hexadecimal.
}
inline program parse(std::string_view input)
{
    program out;
    if(input.empty() || input.size()>4*1024*1024) {
        out.error="B-record stream empty or exceeds 4MiB";return out;
    }
    std::size_t start=0;
    bool execute_seen=false;
    while(start<input.size()) {
        std::size_t const end=input.find('\r',start);
        if(end==std::string_view::npos) {
            out.error="B-record must end with CR";return out;
        }
        std::string_view const line=input.substr(start,end-start);
        start=end+1;
        if(start<input.size() && input[start]=='\n')++start;
        if(line.empty())continue;
        if(execute_seen) {
            out.error="Data after execution B-record";return out;
        }
        if(line.size()<10 || line.size()>72 || (line.size()%2)) {
            out.error="Malformed B-record length";return out;
        }
        std::array<std::uint8_t,36> decoded{};
        for(std::size_t i=0;i<line.size()/2;i++) {
            int const hi=hex_digit(line[i*2]),lo=hex_digit(line[i*2+1]);
            if(hi<0 || lo<0) {
                out.error="Non-uppercase or nonhex B-record";return out;
            }
            decoded[i]=std::uint8_t((hi<<4)|lo);
        }
        record r;
        r.address=(std::uint32_t(decoded[0])<<24)|
            (std::uint32_t(decoded[1])<<16)|
            (std::uint32_t(decoded[2])<<8)|decoded[3];
        std::uint8_t const mode_count=decoded[4];
        // Motorola B-record supports byte data records and zero-length
        // execution records. Word/long/read modes need separate hardware
        // semantics and are rejected instead of silently misinterpreted.
        if(mode_count & 0xe0) {
            out.error="Unsupported B-record mode (use byte writes)";return out;
        }
        r.count=mode_count;
        if(line.size()!=std::size_t(5+r.count)*2) {
            out.error="B-record byte count mismatch";return out;
        }
        if(r.count && std::uint64_t(r.address)+r.count>0x100000000ULL) {
            out.error="B-record address wraps 32-bit bus";return out;
        }
        for(unsigned i=0;i<r.count;i++)r.data[i]=decoded[5+i];
        execute_seen=r.execute();
        out.records.push_back(r);
    }
    if(out.records.empty())out.error="No B-records";
    return out;
}
} // namespace vz328_bootstrap
