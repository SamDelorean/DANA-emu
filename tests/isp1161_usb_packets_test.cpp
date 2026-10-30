// license:BSD-3-Clause
// Real production packet functions / 2462-byte DC SRAM, independent USB peers.
#include "../src/mame/skeleton/isp1161_usb.h"
#include <array>
#include <vector>
#include <iostream>
#include <stdexcept>
using namespace isp1161a1;
static unsigned checks=0;
#define CHECK(x) do {++checks;if(!(x))throw std::runtime_error(std::string(__func__)+":"+std::to_string(__LINE__)+" " #x);}while(0)
static std::array<byte,8> setup(byte type,byte request,word value=0,word index=0,word count=0) {
 return {type,request,byte(value),byte(value>>8),byte(index),byte(index>>8),byte(count),byte(count>>8)};
}
void functions() {
 usb_function f;std::vector<byte> printed;
 auto printer=[&](byte b){printed.push_back(b);return true;};
 std::array<byte,1024> data{};
 auto packet=[&](pid p,byte address,byte ep,bool toggle,word n,byte const *out=nullptr,bool iso=false) {
  transaction tx{address,ep,p,false,iso,toggle,64};return f.transfer(tx,out,data.data(),n,printer);
 };
 CHECK(packet(pid::in,0,0,false,8).status==handshake::timeout);
 f.kind=1;f.reset();
 auto s=setup(0x80,6,0x100,0,18);
 CHECK(packet(pid::setup,0,0,false,8,s.data()).status==handshake::ack);
 CHECK(packet(pid::in,0,0,true,64).size==18&&data[0]==18&&data[1]==1);
 CHECK(packet(pid::out,0,0,true,0,s.data()).status==handshake::ack);
 s=setup(0,5,5);packet(pid::setup,0,0,false,8,s.data());
 CHECK(f.address==0);CHECK(packet(pid::in,0,0,true,0).status==handshake::ack);CHECK(f.address==5);
 CHECK(packet(pid::setup,0,0,false,8,s.data()).status==handshake::timeout);
 s=setup(0x80,6,0x200,0,255);packet(pid::setup,5,0,false,8,s.data());
 CHECK(packet(pid::in,5,0,true,64).size==32&&data[5]==1&&data[14]==7);
 packet(pid::out,5,0,true,0,s.data());
 s=setup(0,9,1);packet(pid::setup,5,0,false,8,s.data());packet(pid::in,5,0,true,0);
 std::array<byte,5> text={'D','A','N','A','\n'};
 CHECK(packet(pid::out,5,1,false,5,text.data()).size==5);
 CHECK(printed==std::vector<byte>(text.begin(),text.end()));
 CHECK(packet(pid::out,5,1,false,5,text.data()).size==5);CHECK(printed.size()==5); // duplicate OUT ACK without duplicate output
 CHECK(packet(pid::in,5,2,false,64).status==handshake::nak);
 s=setup(0x21,0,0,0,255);packet(pid::setup,5,0,false,8,s.data());
 CHECK(packet(pid::in,5,0,true,64).status==handshake::ack&&data[0]==0);
 packet(pid::out,5,0,true,0,s.data());
 s=setup(2,3,0,1);packet(pid::setup,5,0,false,8,s.data());packet(pid::in,5,0,true,0);
 CHECK(packet(pid::out,5,1,true,5,text.data()).status==handshake::stall);
 s=setup(2,1,0,1);packet(pid::setup,5,0,false,8,s.data());packet(pid::in,5,0,true,0);
 CHECK(packet(pid::out,5,1,false,5,text.data()).status==handshake::ack);
 f.kind=2;f.reset();f.configuration=1;
 for(unsigned ep=1;ep<=3;++ep) {
  bool const iso=ep==3;
  CHECK(packet(pid::out,0,byte(ep),false,5,text.data(),iso).size==5);
  CHECK(packet(pid::in,0,byte(ep),false,64,nullptr,iso).size==5);
  CHECK(std::equal(text.begin(),text.end(),data.begin()));
 }
 s=setup(0x40,0xf0,unsigned(handshake::nak),1);packet(pid::setup,0,0,false,8,s.data());packet(pid::in,0,0,true,0);
 CHECK(packet(pid::out,0,1,true,5,text.data()).status==handshake::nak);
 CHECK(packet(pid::out,0,1,true,5,text.data()).status==handshake::ack);
 f.kind=0;CHECK(packet(pid::in,0,1,false,8).status==handshake::timeout);
}
void endpoints() {
 dc_endpoints d;word config[16]={};byte ram[2462]={};
 config[0]=0x83;config[1]=0xc3;config[2]=0xa3;config[3]=0xe3;
 CHECK(d.allocate(config));CHECK(d.capacity[0]==64&&d.base[3]==256);
 d.enabled=1;
 auto s=setup(0x80,6,0x100,0,18);std::array<byte,1024> in{};
 transaction tx{0,0,pid::setup,false,false,false,64};
 CHECK(d.transfer(tx,s.data(),in.data(),8,config,ram).status==handshake::ack);
 CHECK(d.status(0)==0x34&&d.events==0x100);
 CHECK(d.error[0]==1&&d.error_pending[0]);
 CHECK(d.allocate(config)&&d.toggle[0]==1&&d.toggle[1]==1);
 // Reconfiguration during SETUP retains status-stage DATA1.
 CHECK(d.transfer(tx,s.data(),in.data(),8,config,ram).status==handshake::ack);
 d.select(0,false);CHECK(d.read(ram)==8);CHECK(d.read(ram)==0x0680);
 CHECK(!d.clear(0,config));d.setup_ack=1;CHECK(d.clear(0,config));
 d.select(1,true);d.write(3,ram);d.write(0x2211,ram);d.write(0x0033,ram);CHECK(d.validate(1,config));
 tx.direction=pid::in;tx.toggle=true;
 CHECK(d.transfer(tx,nullptr,in.data(),64,config,ram).size==3);
 CHECK(in[0]==0x11&&in[1]==0x22&&in[2]==0x33&&d.events==0x200);
 // Address takes effect only after firmware writes it and status-IN is ACKed.
 d.pending_address=7;d.address_pending=1;
 d.select(1,true);d.write(0,ram);CHECK(d.validate(1,config));
 tx.toggle=false;CHECK(d.transfer(tx,nullptr,in.data(),0,config,ram).status==handshake::ack);CHECK(d.active_address==7);
 tx={0,1,pid::out,false,false,false,64};CHECK(d.transfer(tx,s.data(),in.data(),8,config,ram).status==handshake::timeout);
 tx.address=7;
 CHECK(d.transfer(tx,s.data(),in.data(),8,config,ram).status==handshake::ack);
 CHECK(d.full[2]==1);tx.toggle=true;
 CHECK(d.transfer(tx,s.data(),in.data(),8,config,ram).status==handshake::ack);CHECK(d.full[2]==3);
 tx.toggle=false;CHECK(d.transfer(tx,s.data(),in.data(),8,config,ram).status==handshake::nak);
 d.select(2,false);CHECK(d.read(ram)==8);CHECK(d.clear(2,config));CHECK(d.cpu_bank[2]==1);
 CHECK(d.transfer(tx,s.data(),in.data(),8,config,ram).status==handshake::ack);
 // Double-buffered IN occupies both banks and preserves packet order.
 for(unsigned i=0;i<2;++i) {d.select(3,true);d.write(1,ram);d.write(word(0x41+i),ram);CHECK(d.validate(3,config));}
 CHECK(!d.validate(3,config));
 tx={7,2,pid::in,false,false,false,64};
 CHECK(d.transfer(tx,nullptr,in.data(),64,config,ram).size==1&&in[0]==0x41);
 tx.toggle=true;CHECK(d.transfer(tx,nullptr,in.data(),64,config,ram).size==1&&in[0]==0x42);
 tx.toggle=false;CHECK(d.transfer(tx,nullptr,in.data(),64,config,ram).status==handshake::nak);
 d.stalled[3]=1;CHECK(d.transfer(tx,nullptr,in.data(),64,config,ram).status==handshake::stall);
 d.stalled[3]=0;d.flush(3);
 // Invalid endpoint and over-capacity allocations cannot index past SRAM.
 tx.endpoint=15;CHECK(d.transfer(tx,nullptr,in.data(),64,config,ram).status==handshake::stall);
 config[2]=0xbf;config[3]=0xbf;CHECK(!d.allocate(config)&&!d.allocation_valid);
 config[2]=0;config[3]=0;
 config[4]=0xbf; // 2 * 1023 ISO + 128 control fits 2462
 CHECK(d.allocate(config)&&d.capacity[4]==1023);
 config[5]=0xbf;CHECK(!d.allocate(config));
 // SETUP overwrite, automatic unstall and F4 gating.
 config[4]=config[5]=0;CHECK(d.allocate(config));d.active_address=0;
 tx={0,0,pid::setup,false,false,false,64};d.stalled[0]=d.stalled[1]=1;
 CHECK(d.transfer(tx,s.data(),in.data(),8,config,ram).status==handshake::ack);CHECK(!d.stalled[0]&&!d.stalled[1]);
 CHECK(d.transfer(tx,s.data(),in.data(),8,config,ram).status==handshake::ack&&d.overwrite);
 dc_endpoints copy=d;byte restored[2462];std::copy_n(ram,2462,restored);
 copy.select(0,false);CHECK(copy.read(restored)==8&&copy.read(restored)==0x0680);
}
void ptd_cases() {
 std::array<byte,80> ram{};
 auto init=[&](word n,byte direction=2){ram.fill(0);ram[1]=8;ram[2]=8;ram[3]=8;ram[4]=byte(n);ram[5]=byte(direction<<2);};
 init(0);unsigned calls=0;
 auto zlp=execute(ram.data(),8,[&](transaction const &,byte const *,byte *,word n)->reply{++calls;CHECK(n==0);return {handshake::ack,0};});
 CHECK(zlp.completed==1&&calls==1&&(ram[1]&4)); // successful ZLP toggles
 init(16);ram[5]|=0x20;
 auto part=execute(ram.data(),24,[](transaction const &,byte const *,byte *p,word n)->reply{std::fill_n(p,n,0x55);return {handshake::ack,n};},true);
 CHECK(part.pending==1&&(ram[1]&8)&&ram[0]==8);
 part=execute(ram.data(),24,[](transaction const &tx,byte const *,byte *p,word n)->reply{CHECK(tx.toggle);std::fill_n(p,n,0xaa);return {handshake::ack,n};},true);
 CHECK(part.completed==1&&ram[0]==16&&ram[8]==0x55&&ram[16]==0xaa);
 init(16);execute(ram.data(),24,[](transaction const &,byte const *,byte *,word)->reply{return {handshake::ack,3};});
 CHECK((ram[1]>>4)==9&&ram[0]==3); // short data reports documented underrun
 init(8);execute(ram.data(),16,[](transaction const &,byte const *,byte *,word)->reply{return {handshake::ack,9};});
 CHECK((ram[1]>>4)==8); // overrun, not PID error
 for(auto error: {handshake::crc,handshake::bitstuff,handshake::toggle_mismatch,handshake::stall,handshake::timeout,handshake::pid_error,handshake::unexpected_pid}) {
  init(8);auto result=execute(ram.data(),16,[&](transaction const &,byte const *,byte *,word)->reply{return {error,0};});
  CHECK(result.completed==1&&!(ram[1]&8));
 }
 init(8);ram[5]=12;CHECK(execute(ram.data(),16,[](transaction const &,byte const *,byte *,word)->reply{return {};}).malformed);
 init(8);CHECK(execute(ram.data(),9,[](transaction const &,byte const *,byte *,word)->reply{return {};}).malformed);
}
int main(){try{functions();endpoints();ptd_cases();std::cout<<"ISP1161_PRODUCTION_PACKET_FIFO_PASS checks="<<checks<<"\n";return 0;}catch(std::exception const &e){std::cerr<<e.what()<<"\n";return 1;}}
