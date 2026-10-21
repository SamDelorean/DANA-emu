#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Execute extracted hardware functions, never an emulator or guest workload."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from d2_1_pllfsr_contract_test import method_body
import f1_emutos_run as f1
from lua_contract import check_lua

ROOT=Path(__file__).resolve().parents[1]
DRIVER=ROOT/'src/mame/skeleton/alphasdana.cpp'

def compile_logic(code):
    with tempfile.TemporaryDirectory(prefix='dana-hardware-static-') as tmp:
        p=Path(tmp);(p/'test.cpp').write_text('#include <initializer_list>\n'+code)
        subprocess.run(['c++','-std=c++20','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',
                        str(p/'test.cpp'),'-o',str(p/'logic')],check=True,timeout=60)
        subprocess.run([str(p/'logic')],check=True,timeout=10)

class Hardware(unittest.TestCase):
    def test_spi1_empty_bus_all_widths_and_disabled_master(self):
        src=DRIVER.read_text()
        method=method_body(src,r'void alphasdana_state::spi1_ctrl_w\(offs_t, u16 data, u16 mem_mask\)\s*')
        compile_logic('''#include <cstdint>
#include <cassert>
using u16=std::uint16_t;using u32=std::uint32_t;using offs_t=unsigned;
#define COMBINE_DATA(p) (*(p)=(*(p)&~mem_mask)|(data&mem_mask))
struct alphasdana_state {u16 m_spi1_ctrl=0,m_spi1_rx=0;void spi1_ctrl_w(offs_t,u16,u16);};
'''+method+'''
int main(){alphasdana_state s;
for(unsigned width=1;width<=16;++width){
 for(unsigned mode: {0x100u,0x300u,0x500u}){s.m_spi1_rx=0x1234;s.spi1_ctrl_w(0,mode|(width-1),0xffff);assert(s.m_spi1_rx==0x1234);}
 s.spi1_ctrl_w(0,0x700|(width-1),0xffff);
 assert(s.m_spi1_rx==u16((1u<<width)-1));assert(!(s.m_spi1_ctrl&0x100));
}
s.spi1_ctrl_w(0,0x0600,0xff00);s.spi1_ctrl_w(0,7,0xff);assert(s.m_spi1_ctrl==0x607);
s.spi1_ctrl_w(0,0x0700,0xff00);assert(s.m_spi1_rx==0xff);
}
'''.replace('#include <cassert>','#include <cassert>\n#include <initializer_list>'))

    def test_actual_stylus_gpio_and_12bit_spi2_adc_path(self):
        # Compile the actual production GPIO inline methods and ADC/SPI2
        # functions under ASAN/UBSAN. Only documented pen transactions are
        # accepted; the existing ST keyboard slave remains independent.
        src=DRIVER.read_text()
        pf=src[src.index('    u8 pf_r(offs_t reg)'):src.index('    void pf_w(offs_t reg, u8 value)')]
        pg=src[src.index('    u8 pg_r(offs_t reg)'):src.index('    DANA_GPIO_PORT(pj, 5)')]
        adc=method_body(src,r'u16 alphasdana_state::pen_exchange\(unsigned width, u16 outgoing\)\s*')
        spi=method_body(src,r'void alphasdana_state::spi2_ctrl_w\(offs_t, u16 data, u16 mem_mask\)\s*')
        compile_logic('''#include <cstdint>
#include <cassert>
using u8=std::uint8_t; using u16=std::uint16_t; using u32=std::uint32_t; using offs_t=unsigned;
#define COMBINE_DATA(p) (*(p)=(*(p)&~mem_mask)|(data&mem_mask))
struct Port { unsigned value=0; unsigned read() const{return value;} };
struct alphasdana_state {
 Port pen,p_x,p_y;
 Port *m_pen_contact=&pen,*m_pen_x=&p_x,*m_pen_y=&p_y;
 u8 m_gpio[32]={};u8 m_pfsel=0xc5,m_pen_command=0;
 u16 m_pen_sample=0,m_spi2_data=0,m_spi2_ctrl=0;
 unsigned st_calls=0, irq_calls=0;
 u8 st_exchange(u8){++st_calls;return 0xaa;}
 void update_irq_lines(){++irq_calls;}
 u16 pen_exchange(unsigned,u16);
 void spi2_ctrl_w(offs_t,u16,u16);
'''+pf+pg+'''};
'''+adc+spi+'''
int main(){
 alphasdana_state s;
 s.m_gpio[9]=0x08;s.m_gpio[17]=0x04;
 assert(s.pf_r(1)&2); // No synthetic touch when pen lifted.
 s.pen.value=1;assert(!(s.pf_r(1)&2));
 s.m_gpio[12]=0x02;s.m_gpio[13]=0x02;assert(s.pf_r(1)&2); // Output latch preserved.
 s.m_gpio[12]=0;s.m_pfsel|=0x02;assert(s.pf_r(1)&2);
 s.m_pfsel&=~u8(0x02);assert(!(s.pf_r(1)&2));
 auto command=[&](u8 cmd){s.m_spi2_data=cmd;s.spi2_ctrl_w(0,0x2347,0xffff);};
 auto sample=[&](){s.m_spi2_data=0;s.spi2_ctrl_w(0,0x234f,0xffff);return s.m_spi2_data;};
 // PG2 is active-low; PE3 is deasserted. Two phases, X then Y.
 s.pg_w(1,0);
 command(0x90);assert(s.m_pen_command==0x90&&s.m_spi2_data==0xff);
 assert(sample()==u16(290U<<4)&&!s.m_pen_command);
 command(0xd0);assert(sample()==u16(200U<<4));
 s.p_x.value=65535;s.p_y.value=65535;
 command(0x90);assert(sample()==u16(3760U<<4));
 command(0xd0);assert(sample()==u16(3650U<<4));
 // Wrong order, unknown command or absent contact never creates a sample.
 assert(sample()==0xffff);
 command(0x55);assert(sample()==0xffff);
 command(0x90);s.pg_w(1,4);assert(!s.m_pen_command&&!s.m_pen_sample);
 s.pg_w(1,0);assert(sample()==0xffff);
 s.pen.value=0;command(0x90);assert(sample()==0xffff);
 s.pen.value=1;command(0x90);s.pen.value=0;assert(sample()==0xffff);
 // ST select still transfers the original keyboard response.
 s.pen.value=1;s.pg_w(1,4);s.m_gpio[9]=0;
 unsigned prev=s.st_calls;command(0x00);assert(s.st_calls==prev+1&&s.m_spi2_data==0xaa);
 // Overlapping chip selects are not an invented ADC or ST conversion.
 s.pg_w(1,0);prev=s.st_calls;command(0x90);
 assert(s.st_calls==prev&&s.m_spi2_data==0xff);
 assert(s.irq_calls>0);
}
''')
        for required in ('PORT_START("PEN")','PORT_START("PENX")','PORT_START("PENY")',
                         'save_item(NAME(m_pen_command));','save_item(NAME(m_pen_sample));'):
            self.assertIn(required,src)

    def test_actual_lcd_renderer_ram_pan_power_polarity_stride_and_bounds(self):
        src=DRIVER.read_text()
        method=method_body(src,r'u32 alphasdana_state::screen_update\(screen_device &, bitmap_rgb32 &bitmap, const rectangle &cliprect\)\s*')
        compile_logic('''#include <cstdint>
#include <vector>
#include <algorithm>
#include <cassert>
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;using u64=std::uint64_t;
#define BIT(v,n) (((v)>>(n))&1)
struct rgb_t {u32 value;rgb_t(unsigned r,unsigned g,unsigned b):value((r<<16)|(g<<8)|b){} operator u32() const{return value;}};
struct rectangle {int top() const{return 0;}int bottom() const{return 159;}int left() const{return 0;}int right() const{return 559;}};
struct bitmap_rgb32 {std::vector<u32> p=std::vector<u32>(560*160);void fill(u32 c,const rectangle&){std::fill(p.begin(),p.end(),c);}u32 &pix(int y,int x){return p.at(y*560+x);}};
struct screen_device {};
struct Ram {std::vector<u16> data=std::vector<u16>(0x200000);unsigned reads=0;u16 operator[](unsigned i){++reads;return data.at(i);}};
struct alphasdana_state {u32 m_lssa=0;u8 m_gpio[32]={},m_lckcon=0x80,m_lpicf=8,m_lvpw=35,m_lposr=0,m_lpolcf=0;u16 m_lxmax=560,m_lymax=159;Ram m_ram;u32 screen_update(screen_device&,bitmap_rgb32&,const rectangle&);};
'''+method+'''
int main(){alphasdana_state s;screen_device screen;bitmap_rgb32 b;rectangle c;
auto draw=[&]{s.m_ram.reads=0;s.screen_update(screen,b,c);};
u32 const off=0xbdbdaa,on=0x404040;
s.m_gpio[25]=0x80;s.m_lssa=0x8000;s.m_ram.data[0x4000]=0x8001;s.m_ram.data[(0x8000+11198)/2]=1;
draw();assert(b.pix(0,0)==on&&b.pix(0,1)==off&&b.pix(0,15)==on&&b.pix(159,559)==on);assert(s.m_ram.reads==560*160);
s.m_gpio[25]=0;draw();assert(!s.m_ram.reads&&b.pix(0,0)==off);
s.m_gpio[25]=0x80;s.m_lckcon=0;draw();assert(!s.m_ram.reads);s.m_lckcon=0x80;
s.m_lvpw=36;s.m_lposr=1;draw();assert(b.pix(0,0)==off&&b.pix(0,14)==on);
s.m_lpolcf=1;draw();assert(b.pix(0,0)==on&&b.pix(0,14)==off);
s.m_lvpw=35;draw();assert(!s.m_ram.reads); // Pan would cross the DMA row.
s.m_lposr=0;s.m_lssa=0x3ffffe;draw();assert(!s.m_ram.reads);
s.m_lssa=0xffffffff;draw();assert(!s.m_ram.reads);
s.m_lssa=0x8001;draw();assert(!s.m_ram.reads);
s.m_lssa=0x8000;s.m_lpicf=9;draw();assert(!s.m_ram.reads); // No invented greyscale.
s.m_lpicf=8;s.m_lxmax=16;s.m_lymax=0;s.m_lvpw=1;draw();assert(s.m_ram.reads==16&&b.pix(1,0)==off);
}
''')

    def test_dependency_maps_do_not_claim_spi1_for_old_binary_or_wrong_lane(self):
        for kind in ('read','write'):
            for a in range(0xfffff700,0xfffff70c):
                actual=f1.implemented_byte(a,kind,True,True)
                expected=a>=0xfffff704 or (kind=='read' and a<=0xfffff701) or (kind=='write' and 0xfffff702<=a<=0xfffff703)
                self.assertEqual(actual,expected,(hex(a),kind))
                self.assertFalse(f1.implemented_byte(a,kind,True))
        for a in (0xfffff6ff,0xfffff70c,0x00fff700):self.assertFalse(f1.implemented_byte(a,'read',True,True))
        src=(ROOT/'tests/f1_emutos_boot.lua').read_text();methods=src[src.index('local function implemented_byte'):src.index('emu.register_prestart')]
        check_lua('local e5=true;local cfg={integrated_hardware=true}\n'+methods+"\nassert(implemented_byte(0xfffff700,'read'))\nassert(not implemented_byte(0xfffff700,'write'))\nassert(not implemented_byte(0xfffff702,'read'))\nassert(implemented_byte(0xfffff703,'write'))")

    def test_native_input_ports_and_response_table_are_consistent(self):
        src=DRIVER.read_text();table=re.search(r'scans\[128\]=\{([^}]+)',src)[1]
        scans=[int(v,16) for v in table.split(',')]
        self.assertEqual(len(scans),128)
        self.assertEqual(scans[:4],[0x2b,0x7a,0x2e,0x7e])
        used=[v for v in scans if v];self.assertEqual(len(used),len(set(used)))
        self.assertGreaterEqual(len(used),74)
        for field in ('m_st_old_extra','m_st_queue','m_st_queue_pos','m_spi1_rx','m_spi1_ctrl'):
            self.assertIn('save_item(NAME('+field+'));',src)
        self.assertIn('count<8',src)

    def test_actual_uart_fifo_lanes_framing_interrupts_and_disabled_tx(self):
        src=DRIVER.read_text()
        a=src.index('// Reuse MAME\'s native asynchronous serial engine:')
        b=src.index('QUICKLOAD_LOAD_MEMBER',a)
        production=src[a:b]
        compile_logic('''#include <cstdint>
#include <cassert>
using u8=std::uint8_t;using u16=std::uint16_t;using u32=std::uint32_t;using offs_t=unsigned;
#define COMBINE_DATA(p) (*(p)=(*(p)&~mem_mask)|(data&mem_mask))
#define logerror(...) ((void)0)
enum {PARITY_NONE,PARITY_ODD,PARITY_EVEN,STOP_BITS_1,STOP_BITS_2};
struct alphasdana_state {
 u16 m_ustcnt1=0,m_ubaud1=2,m_umisc1=0,m_utx1=0,m_urx1=0,m_uart_rx_fifo[12]={};
 u8 m_uart_tx_fifo[8]={},m_uart_tx_head=0,m_uart_tx_count=0,m_uart_rx_head=0,m_uart_rx_count=0,m_uart_shift_byte=0;
 bool m_uart_tx_busy=false;u32 m_pending=0,m_uart_completed=0;int m_uart_txd=1;
 int baud=0,bits=0,parity=0,stops=0,shift=0,irq_updates=0,rx_line=1;bool peek=false;u8 received=0x41;
 auto &machine(){return *this;}bool side_effects_disabled() const{return peek;}
 u32 guest_system_clock_hz(){return 33161216;}
 void set_data_frame(int,int b,int p,int s){bits=b;parity=p;stops=s;}
 void set_rate(int b){baud=b;}
 void transmit_register_reset(){}void receive_register_reset(){}
 void transmit_register_setup(u8 b){shift=b;}int transmit_register_get_data_bit(){return 0;}
 void receive_register_extract(){}u8 get_received_char(){return received;}
 bool is_receive_parity_error(){return false;}bool is_receive_framing_error(){return false;}
 void rx_w(int b){rx_line=b;}void update_irq_lines(){++irq_updates;}
 void uart1_configure();void uart1_ustcnt_w(offs_t,u16,u16);u16 uart1_utx_r();u16 uart1_urx_r(offs_t,u16);
 void uart1_update_irq();void uart1_start_tx();void uart1_utx_w(offs_t,u16,u16);
 void tra_callback();void tra_complete();void rcv_complete();
};
'''+production+'''
int main(){alphasdana_state s;
s.uart1_utx_w(0,0x45,0xff);assert(s.m_utx1==0x45&&!s.m_uart_tx_busy&&!s.m_uart_tx_count&&!(s.m_pending&4));
s.uart1_ustcnt_w(0,0xe108,0xffff);assert(s.bits==8&&s.parity==PARITY_NONE&&s.stops==STOP_BITS_1);assert(s.baud==33161216/63/16);
// Status/control lane cannot enqueue a phantom data byte.
s.uart1_utx_w(0,0x800,0xff00);assert(!s.m_uart_tx_count&&!s.m_uart_tx_busy);
s.uart1_utx_w(0,0x41,0xff);assert(s.m_uart_tx_busy&&s.shift==0x41);assert(s.uart1_utx_r()&0x400);
for(unsigned i=0;i<8;++i)s.uart1_utx_w(0,0x42+i,0xff);
assert(s.m_uart_tx_count==8&&!(s.uart1_utx_r()&0xe000));
s.uart1_utx_w(0,0x99,0xff);assert(s.m_uart_tx_count==8); // Full FIFO cannot overwrite accepted bytes.
for(unsigned i=0;i<9;++i){assert(s.shift==int(0x41+i));s.tra_complete();}
assert(!s.m_uart_tx_busy&&s.m_uart_completed==9&&(s.uart1_utx_r()&0xe000)==0xe000);
s.uart1_ustcnt_w(0,0xe10c,0xffff);assert(s.m_pending&4); // Empty TX IRQ.
s.uart1_ustcnt_w(0,0xe108,0xffff);assert(!(s.m_pending&4));
s.rcv_complete();assert(s.m_uart_rx_count==1&&(s.m_pending&4));
s.peek=true;assert(s.uart1_urx_r(0,0xffff)==0x2041&&s.m_uart_rx_count==1);
s.peek=false;s.uart1_urx_r(0,0xff00);assert(s.m_uart_rx_count==1);
assert(s.uart1_urx_r(0,0xff)==0x2041&&!s.m_uart_rx_count&&!(s.m_pending&4));
for(unsigned i=0;i<13;++i){s.rcv_complete();}assert(s.m_uart_rx_count==12&&s.m_uart_rx_fifo[s.m_uart_rx_head]&0x800);
s.uart1_ustcnt_w(0,0,0xffff);assert(!s.m_uart_rx_count&&!s.m_uart_tx_count&&!s.m_uart_tx_busy&&s.baud==0&&!(s.m_pending&4));
s.uart1_ustcnt_w(0,0xaf00,0xffff);assert(s.bits==8&&s.parity==PARITY_ODD&&s.stops==STOP_BITS_2);
s.m_ubaud1=0x802;s.uart1_configure();assert(s.baud==0); // Unconnected UCLK never clocks itself.
s.m_umisc1=0x1000;s.m_ustcnt1=0xe100;s.tra_callback();assert(s.rx_line==0&&s.m_uart_txd==0);
}
''')

if __name__=='__main__':unittest.main()
