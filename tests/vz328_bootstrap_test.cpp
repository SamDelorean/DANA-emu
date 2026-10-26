// license:BSD-3-Clause
#include "../src/mame/skeleton/vz328_bootstrap.h"
#include <iostream>
#include <string>
using namespace vz328_bootstrap;
#define VERIFY(v) do{if(!(v)){std::cerr<<"BOOT_ASSERT line "<<__LINE__<<"\n";return 1;}}while(0)
int main()
{
    auto p=parse("00FFFFC0044E7160FE\r00FFFFC000\r");
    VERIFY(p.valid() && p.records.size()==2);
    VERIFY(p.records[0].address==0xffffc0 && p.records[0].count==4);
    VERIFY(p.records[0].data[0]==0x4e && p.records[0].data[3]==0xfe);
    VERIFY(p.records[1].execute() && p.records[1].address==0xffffc0);
    auto q=parse("FFFFF43B01CF\r"); // Motorola VZ UART2 TX enable example
    VERIFY(q.valid() && q.records.size()==1);
    VERIFY(q.records[0].address==0xfffff43b && q.records[0].data[0]==0xcf);
    for(const std::string &bad:{
        "00FFFFC0024E\r",              // truncation
        "00FFFFC0044e7160fe\r",      // lower-case not Motorola B-record
        "00FFFFC000\n",              // missing CR
        "00FFFFC0E04E7160FE\r",      // nonbyte B-record mode unsupported
        "00FFFFC000\r00FFFFC0020000\r", // bytes after execute
        "FFFFFFFE0401020304\r",      // wraps 32-bit
        "00FFFFC0044E7160FX\r",      // nonhex
    }) {
        VERIFY(!parse(bad).valid());
    }
    auto noexec=parse("00FFFFC0024E71\r");
    VERIFY(noexec.valid() && !noexec.records.back().execute());
    std::cout<<"PASS Motorola VZ B-record parse, execution, IBUFF, UART2 example and invalid forms\n";
}
