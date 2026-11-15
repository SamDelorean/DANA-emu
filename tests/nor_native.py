#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""H3: synthetic disposable NOR, real reset/68000/CSA/SDRAM/bus accesses.

No vendor image is opened by this generator. Lua observes journals and drives
explicit external WP/RP pins; it never writes CPU state, RAM or MMIO.
"""
import argparse, hashlib, json, os, re, shutil, struct, subprocess
from pathlib import Path
from d7_5_native import Code, ENTRY, MARKER

BASE=0x10000000
TARGET=BASE+0x40000

def rd(c,a): c.w(0x3039);c.l(a)
def check(c,a,v,mask=65535):
    rd(c,a)
    if mask!=65535:c.w(0x0240,mask)
    c.expect(v)
def stage(c,n):c.move_w(n,MARKER+2)
def cmd(c,v,a=BASE):c.move_w(v,a)
def poll(c,mask=0x80,value=0x80):
    name=c.unique();c.label(name);rd(c,BASE);c.w(0x0240,mask,0x0c40,value,0x6706);c.jump(name)
def unlock(c,a):cmd(c,0x60,a);cmd(c,0xd0,a)
def program(c,a,v,op=0x40):
    cmd(c,op);c.move_w(v,a);poll(c);check(c,BASE,0x80,0xba);cmd(c,255)
def erase(c,a):cmd(c,0x20,a);cmd(c,0xd0,a);poll(c);check(c,BASE,0x80,0xba);cmd(c,255)
def wait(c,ticks):
    # Existing real Timer1, CLK32, free-running. No host sleeps or fake READY.
    c.move_w(0,0xfffff600);c.move_w(0,0xfffff602);c.move_w(65535,0xfffff604);c.move_w(0x109,0xfffff600)
    name=c.unique();c.label(name);rd(c,0xfffff608);c.w(0x0c40,ticks,0x6406);c.jump(name)
def finish(c):
    c.label('done');c.move_w(0xa55a,MARKER);c.w(0x4e72,0x2700)
    c.label('fail');c.record(MARKER+6);c.move_w(0xdead,MARKER);c.w(0x4e72,0x2700)
    for pos,name in c.fixups:struct.pack_into('>I',c.data,pos,c.labels[name])
    return bytes(c.data)

def payload(mode):
    c=Code();c.w(0x46fc,0x2700);c.move_w(0,0xfffffb0a)
    if mode=='watchdog':
        rd(c,MARKER);c.w(0x0c40,0x5a5a,0x6606);c.jump('after_watchdog')
    if mode in ['persist','otp']:
        c.w(0x1039);c.l(0xfffff419);c.w(0x0240,1,0x0c40,1,0x6606);c.jump('otp_readback'if mode=='otp'else'persistent_readback')
    for i in range(0,64,2):c.move_w(0,MARKER+i)
    stage(c,1)
    if mode=='identify':
        cmd(c,0x90);check(c,BASE,0x20);check(c,BASE+2,0x8849);check(c,TARGET+4,1)
        c.move_b(0xff,BASE);check(c,BASE,0);check(c,BASE+2,0x316)
        c.move_b(0x90,BASE);check(c,BASE,0x20);cmd(c,255)
        cmd(c,0x98)
        expected={0x10:81,0x11:82,0x12:89,0x13:3,0x15:0x35,0x1b:0x27,0x1c:0x36,0x1d:0xb4,0x1e:0xc6,0x1f:4,0x20:4,0x21:10,0x22:0,0x23:5,0x24:5,0x25:3,0x26:0,0x27:23,0x28:1,0x2a:3,0x2c:2,0x2d:7,0x2f:0x20,0x31:0x7e,0x34:1,0x35:80,0x36:82,0x37:73,0x38:49,0x39:48,0x3a:0x66,0x3e:1,0x3f:3,0x41:0x30,0x42:0xc0,0x43:1,0x44:0x80,0x46:3,0x47:4}
        for a,v in expected.items():check(c,BASE+2*a,v)
        cmd(c,0x70);check(c,BASE,0x80);cmd(c,255);stage(c,2)
        # Array aliases follow 23 chip address lines, not source file length.
        check(c,BASE+0x800002,0x316);check(c,BASE+0x7ffffe,65535)
    elif mode in ['program','persist']:
        unlock(c,TARGET);program(c,TARGET,0x1234);check(c,TARGET,0x1234)
        program(c,TARGET+2,0x5678,0x10);check(c,TARGET+2,0x5678);stage(c,3)
        cmd(c,0x40);c.move_w(65535,TARGET);poll(c);check(c,BASE,0x90,0xba)
        cmd(c,0x50);check(c,BASE,0x80);cmd(c,255);check(c,TARGET,0x1234)
        c.move_w(0x1111,TARGET+4);check(c,TARGET+4,65535)
        # Firmware's command-byte / word-data sequence.
        c.move_b(0xff,BASE);c.move_b(0x40,BASE);c.move_w(0xabcd,TARGET+6);poll(c);cmd(c,255);check(c,TARGET+6,0xabcd)
    elif mode=='erase':
        for a in [BASE+0x2000,BASE+0x4000,TARGET,TARGET+0x10000,BASE+0x7f0000]:unlock(c,a);program(c,a,0)
        stage(c,4);erase(c,BASE+0x2004);check(c,BASE+0x2000,65535);check(c,BASE+0x4000,0)
        # Both ends of a regular block; neighbours must remain untouched.
        program(c,TARGET+0xfffe,0);erase(c,TARGET+0x1234);check(c,TARGET,65535);check(c,TARGET+0xfffe,65535);check(c,TARGET+0x10000,0)
        erase(c,BASE+0x7ffffe);check(c,BASE+0x7f0000,65535);stage(c,5)
    elif mode=='protect':
        cmd(c,0x40);c.move_w(0,TARGET);check(c,BASE,0x92);cmd(c,0x50);cmd(c,255);check(c,TARGET,65535)
        cmd(c,0x20,TARGET);cmd(c,0xd0,TARGET);check(c,BASE,0xa2);cmd(c,0x50)
        unlock(c,TARGET);program(c,TARGET,0x55aa)
        cmd(c,0x60,TARGET);cmd(c,1,TARGET);cmd(c,0x90);check(c,TARGET+4,1)
        unlock(c,TARGET);cmd(c,0x60,TARGET);cmd(c,0x2f,TARGET);cmd(c,0x90);check(c,TARGET+4,3)
        unlock(c,TARGET);cmd(c,0x90);check(c,TARGET+4,2);cmd(c,255)
        stage(c,6);wait(c,4096);cmd(c,0x90);check(c,TARGET+4,3);unlock(c,TARGET);cmd(c,0x90);check(c,TARGET+4,3)
        stage(c,7);wait(c,4096);cmd(c,0x90);check(c,TARGET+4,2);cmd(c,255)
    elif mode in ['suspend','save','reset-cpu']:
        unlock(c,TARGET);unlock(c,TARGET+0x10000);program(c,TARGET,0)
        cmd(c,0x20,TARGET);cmd(c,0xd0,TARGET)
        if mode=='save':
            stage(c,20);c.move_w(0x5a5a,MARKER);poll(c);cmd(c,255);check(c,TARGET,65535)
        else:
            check(c,BASE,0,0x80);cmd(c,255);check(c,BASE,0,0x80) # FF ignored while busy.
            cmd(c,0xb0);poll(c);check(c,BASE,0xc0,0xc4);cmd(c,255);check(c,BASE+2,0x316)
            stage(c,8)
            if mode=='reset-cpu':
                # The 68000 RESET instruction resets external devices, not itself;
                # firmware soft reset must preserve NOR modes/locks/pending erase.
                c.w(0x4e70);cmd(c,0x70);check(c,BASE,0xc0,0xc4)
            else:
                program(c,TARGET+0x10000,0x3456);check(c,TARGET+0x10000,0x3456)
                cmd(c,0x70);check(c,BASE,0xc0,0xc4)
                cmd(c,0x60,TARGET);cmd(c,1,TARGET) # locking paused target cannot cancel accepted erase
            cmd(c,0xd0);poll(c);cmd(c,255);check(c,TARGET,65535)
    elif mode=='timing':
        unlock(c,TARGET);c.move_w(0,0xfffff600);c.move_w(0,0xfffff602);c.move_w(65535,0xfffff604);c.move_w(0x109,0xfffff600)
        rd(c,0xfffff608);c.record(MARKER+0x10);cmd(c,0x20,TARGET);cmd(c,0xd0,TARGET);poll(c)
        rd(c,0xfffff608);c.w(0x9079);c.l(MARKER+0x10);c.record(MARKER+0x12)
        c.w(0x0c40,32760,0x6406);c.jump('fail');c.w(0x0c40,32780,0x6306);c.jump('fail');cmd(c,255)
    elif mode=='vpp-off':
        unlock(c,TARGET);cmd(c,0x40);c.move_w(0,TARGET);check(c,BASE,0x88);cmd(c,0x50);cmd(c,255);check(c,TARGET,65535)
    elif mode=='multi':
        unlock(c,TARGET)
        for op,n in [(0x30,2),(0x56,4)]:
            a=TARGET+(0 if n==2 else 8);cmd(c,op)
            for i in range(n):c.move_w(0x1230+i,a+i*2)
            poll(c);check(c,BASE,0x80,0xba);cmd(c,255)
            for i in range(n):check(c,a+i*2,0x1230+i)
    elif mode=='multi-vdd':
        unlock(c,TARGET);cmd(c,0x56);check(c,BASE,0x88);cmd(c,0x50);cmd(c,255);check(c,TARGET,65535)
    elif mode=='invalid':
        unlock(c,TARGET)
        for v in [0,0xf0,0xaa,0x55,0x80,0x30]:
            if v==0x30:continue # legitimate double program requires 12V
            cmd(c,v,TARGET)
        cmd(c,255);check(c,TARGET,65535)
        cmd(c,0x20,TARGET);cmd(c,0x12,TARGET);check(c,BASE,0xb0);cmd(c,0x50);cmd(c,255)
        # No chip erase opcode exists; 10 is a word-program setup, not erase.
        check(c,BASE+0x4000,65535)
    elif mode=='otp':
        cmd(c,0x90);rd(c,BASE+0x102);c.record(MARKER+0x20);check(c,BASE+0x100,2);check(c,BASE+0x10a,65535)
        cmd(c,0xc0);c.move_w(0x1234,BASE+0x10a);poll(c);cmd(c,0x90);check(c,BASE+0x10a,0x1234)
        cmd(c,0xc0);c.move_w(0,BASE+0x100);poll(c);cmd(c,0x90);check(c,BASE+0x100,0)
        cmd(c,0xc0);c.move_w(0,BASE+0x10c);check(c,BASE,0x92);cmd(c,0x50);cmd(c,0x90);check(c,BASE+0x10c,65535)
        rd(c,BASE+0x102);c.w(0xb079);c.l(MARKER+0x20);c.w(0x6706);c.jump('fail');cmd(c,255)
    elif mode=='powercut':
        c.w(0x1039);c.l(0xfffff419);c.w(0x0240,1,0x0c40,1,0x6606);c.jump('after_cut')
        unlock(c,TARGET);program(c,TARGET,0);cmd(c,0x20,TARGET);cmd(c,0xd0,TARGET);check(c,BASE,0,0x80);stage(c,70);c.move_w(0x5a5a,MARKER);c.w(0x4e72,0x2700)
        c.label('after_cut');c.w(0x1039);c.l(0xfffff419);c.w(0x0240,2,0x0c40,2,0x6606);c.jump('erase_cut')
        rd(c,TARGET);c.jump('fail');c.label('erase_cut');unlock(c,TARGET);erase(c,TARGET);check(c,TARGET,65535)
    elif mode=='program-suspend':
        unlock(c,TARGET);cmd(c,0x40);c.move_w(0x1234,TARGET);cmd(c,0xb0);poll(c);check(c,BASE,0x84,0x84)
        cmd(c,255);check(c,BASE+2,0x316);cmd(c,0xd0);poll(c);cmd(c,255);check(c,TARGET,0x1234)
    elif mode=='watchdog':
        unlock(c,TARGET);program(c,TARGET,0);cmd(c,0x20,TARGET);cmd(c,0xd0,TARGET);cmd(c,0xb0);poll(c);cmd(c,255)
        c.move_w(0x5a5a,MARKER);c.move_w(1,0xfffffb0a);c.w(0x4e72,0x2700)
        c.label('after_watchdog');cmd(c,0x70);check(c,BASE,0xc0,0xc4);cmd(c,0x90);check(c,TARGET+4,0);cmd(c,0xd0);poll(c);cmd(c,255);check(c,TARGET,65535);stage(c,40)
    elif mode in ['save-program','save-nested','save-setup']:
        unlock(c,TARGET);unlock(c,TARGET+0x10000)
        if mode=='save-nested':
            cmd(c,0x20,TARGET+0x10000);cmd(c,0xd0,TARGET+0x10000);cmd(c,0xb0);poll(c)
        if mode=='save-setup':
            cmd(c,0x56);c.move_w(0x1234,TARGET);c.move_w(0x5678,TARGET+2)
        else:
            cmd(c,0x40);c.move_w(0x1234,TARGET);cmd(c,0xb0);poll(c);check(c,BASE,0x84,0x84)
        c.move_w(0x5a5a,MARKER);wait(c,4096)
        if mode=='save-setup':c.move_w(0xabcd,TARGET+4);c.move_w(0xef01,TARGET+6)
        else:cmd(c,0xd0)
        poll(c);cmd(c,255);check(c,TARGET,0x1234)
        if mode=='save-setup':check(c,TARGET+6,0xef01)
        if mode=='save-nested':cmd(c,0xd0);poll(c);cmd(c,255);check(c,TARGET+0x10000,65535)
    elif mode=='reverse-group':
        unlock(c,TARGET);cmd(c,0x30);c.move_w(0x5678,TARGET+2);c.move_w(0x1234,TARGET);poll(c);cmd(c,255);check(c,TARGET,0x1234);check(c,TARGET+2,0x5678)
    elif mode=='group-alignment':
        unlock(c,TARGET);cmd(c,0x56);c.move_w(0x1234,TARGET+2);c.move_w(0x1234,TARGET+4);c.move_w(0x1234,TARGET+6);c.move_w(0x1234,TARGET+8)
        check(c,BASE,0x90);cmd(c,0x50);cmd(c,255);check(c,TARGET+2,65535)
    elif mode=='readback':
        check(c,TARGET,0x1234);check(c,TARGET+2,0x5678);check(c,TARGET+6,0xabcd)
        cmd(c,0x90);check(c,TARGET+4,1);cmd(c,255) # volatile locks return at power-on
    elif mode=='cs-ro':
        unlock(c,TARGET);cmd(c,255);c.move_b(0,0xfffff000);c.move_w(0x80bf,0xfffff110)
        cmd(c,0x40);c.move_w(0,TARGET);check(c,TARGET,65535)
        c.w(0x1039);c.l(0xfffff000);c.w(0x0240,0x40);c.expect(0x40);c.move_w(0x00bf,0xfffff110)
    elif mode in ['address-error','cs-berr']:
        c.w(0x23fc);c.fixups.append((len(c.data),'native_exception'));c.l(0);c.l(12 if mode=='address-error'else 8)
        if mode=='cs-berr':c.move_w(0x80bf,0xfffff110);c.move_w(0x40,TARGET)
        else:rd(c,TARGET+1)
        c.jump('fail');c.label('native_exception')
        if mode=='cs-berr':
            c.w(0x1039);c.l(0xfffff000);c.w(0x0240,0x40);c.expect(0x40);check(c,TARGET,65535)
        stage(c,60)
    elif mode=='partial-data':unlock(c,TARGET);cmd(c,0x40);c.move_b(0,TARGET)
    elif mode=='width':c.move_w(0x003f,0xfffff110);rd(c,TARGET)
    elif mode=='unmapped':rd(c,0x20000000)
    elif mode=='unknown':rd(c,BASE+0x600000)
    elif mode=='erase-unknown':unlock(c,BASE+0x600000);erase(c,BASE+0x600000);check(c,BASE+0x600000,65535)
    elif mode=='rp':
        unlock(c,TARGET);program(c,TARGET,0);cmd(c,0x20,TARGET);cmd(c,0xd0,TARGET);stage(c,30)
        wait(c,8192);cmd(c,0x90);check(c,TARGET+4,1);unlock(c,TARGET);erase(c,TARGET);check(c,TARGET,65535)
    else:raise ValueError(mode)
    if mode=='persist':
        c.jump('done');c.label('persistent_readback');stage(c,50)
        check(c,TARGET,0x1234);check(c,TARGET+2,0x5678);check(c,TARGET+6,0xabcd)
        cmd(c,0x90);check(c,TARGET+4,1);cmd(c,255)
    if mode=='otp':
        c.jump('done');c.label('otp_readback');stage(c,51);cmd(c,0x90);check(c,BASE+0x100,0);check(c,BASE+0x10a,0x1234);check(c,BASE+0x10c,65535);cmd(c,255)
    return finish(c)

def fixture(mode,body=None,size=0x800000):
    if body is None:body=payload(mode)
    assert len(body)<0x1e000
    # Full, explicitly synthetic 8 MiB silicon seed; no private data.
    image=bytearray(b'\xff'*size);struct.pack_into('>II',image,0,0x316,BASE+0x2a2)
    b=Code();b.w(0x46fc,0x2700);b.move_b(0xf0,0xfffff000);b.move_w(0,0xfffffb0a)
    for a,v in [(0xfffff100,0x8000),(0xfffff106,0),(0xfffff116,0x02bf),(0xfffffc02,0x8000),(0xfffffc04,0xc83f),(0xfffffc04,0xd03f),(0xfffffc04,0xd43f),(0xfffff110,0x00bf)]:b.move_w(v,a)
    b.w(0x207c);b.l(BASE+0x1000);b.w(0x227c);b.l(ENTRY);b.w(0x303c,len(body)//2-1)
    loop=len(b.data);b.w(0x32d8,0x51c8,(loop-(len(b.data)+4))&65535)
    b.w(0x2e7c);b.l(0x1000);b.w(0x4ef9);b.l(ENTRY)
    image[0x2a2:0x2a2+len(b.data)]=b.data;image[0x1000:0x1000+len(body)]=body
    if mode in ['unknown','erase-unknown']:image=image[:0x5d0000]
    return image

def main():
    p=argparse.ArgumentParser();p.add_argument('--mode',required=True);p.add_argument('--case',required=True);p.add_argument('--installed',action='store_true');p.add_argument('--reuse',type=Path);p.add_argument('--reference',action='store_true');p.add_argument('--load-state',type=Path);p.add_argument('--expect-rejection',action='store_true');p.add_argument('--save-final',action='store_true');p.add_argument('--chip',choices=['m28w640hcb','m29w320db'],default='m28w640hcb')
    a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.case);root=Path(__file__).resolve().parents[1];folder=root/'local-evidence/runtime-compare'/a.case;folder.mkdir(parents=True,exist_ok=False)
    binary=root/('runtime/diag/bin/dana-diag'if a.installed else'runtime/diag/source/danadiagd')
    cfg=folder/'cfg';cfg.mkdir()
    for name in ['asmdana.cfg','default.cfg']:shutil.copy2(root/'config/palm-uk15'/name,cfg/name)
    f=cfg/'asmdana.cfg';s=f.read_text();s=s.replace('</input>',f'<port tag=":NOR_WORK" type="CONFIG" mask="1" defvalue="0" value="{0 if a.reference else 1}"/><port tag=":NOR_VPP" type="CONFIG" mask="3" defvalue="1" value="{0 if a.mode=="vpp-off" and not a.reference else 2 if a.mode=="accelerated"or(a.chip=="m28w640hcb"and a.mode in ["multi","group-alignment","save-setup","reverse-group"]) else 1}"/></input>')
    if a.mode in ['unknown','erase-unknown']:s=s.replace('tag=":NOR_FACTORY" type="CONFIG" mask="1" defvalue="0" value="1"','tag=":NOR_FACTORY" type="CONFIG" mask="1" defvalue="0" value="0"')
    if a.mode in ['readback','otp-readback','powercut-read','powercut-erase','protection-readback']:s=s.replace('tag=":GPIO1VALUE" type="CONFIG" mask="255" defvalue="0" value="0"','tag=":GPIO1VALUE" type="CONFIG" mask="255" defvalue="0" value="'+str(3 if a.mode=='powercut-erase'else 1)+'"')
    f.write_text(s)
    # Readback uses exactly the original seed, not a newly generated program.
    rom=a.reuse/'seed.bin'if a.reuse else folder/'seed.bin'
    if not a.reuse:
        if a.chip=='m29w320db':
            from nor_st_native import payload as st_payload
            rom.write_bytes(fixture(a.mode,st_payload(a.mode),0x400000))
        else:rom.write_bytes(fixture(a.mode))
        rom.chmod(0o444) # The firmware seed is never writable media.
    before=hashlib.sha256(rom.read_bytes()).hexdigest();nvram=a.reuse/'nvram'if a.reuse else folder/'nvram';state=folder/'pending.sta'
    disk_before={str(p.relative_to(nvram)):hashlib.sha256(p.read_bytes()).hexdigest()for p in nvram.rglob('*')if p.is_file()}if nvram.exists()else{}
    # Reopening persistence executes an independent CPU test selected by an
    # external input, not modified seed bytes; see ROM dispatcher below.
    lua='''local m=manager.machine;local cpu=m.devices[":maincpu"];local b=cpu.spaces.program;local frame=0
local saved=false;local loaded=false;local restored=false;local pin=0;local events={};local count=0
local note=emu.add_machine_post_load_notifier(function()restored=true end)
local tap=b:install_write_tap(0x20000,0x2003f,"h3_cpu_journal",function(addr,data,mask)
 count=count+1;if count<180 then table.insert(events,string.format('{"address":%d,"data":%d,"time":%.12f}',addr,data,m.time:as_double()))end
end)
emu.register_frame_done(function()
 if not tap or not note then return end;frame=frame+1;local v=b:read_u16(0x20000);local st=b:read_u16(0x20002)
 if MODE=="protect" and st==6 and pin==0 then pin=1;m.ioport.ports[":NOR_WP"].fields["Virtual NOR WP input (PCB routing unverified)"].user_value=0 end
 if MODE=="protect" and st==7 and pin==1 then pin=2;m.ioport.ports[":NOR_WP"].fields["Virtual NOR WP input (PCB routing unverified)"].user_value=1 end
 if (MODE=="factory-lock" or MODE=="factory-unprotect") then
  if st==80 and pin==0 then pin=1;m.ioport.ports[":NOR_RP"].fields["Virtual NOR RP input (not tied to MCU reset)"].user_value=2 end
  if st==81 and pin==1 then pin=2;m.ioport.ports[":NOR_RP"].fields["Virtual NOR RP input (not tied to MCU reset)"].user_value=1 end
 end
 if MODE=="rp" and st==30 then
  if pin==0 then pin=1;m.ioport.ports[":NOR_RP"].fields["Virtual NOR RP input (not tied to MCU reset)"].user_value=0
  elseif pin==1 then pin=2;m.ioport.ports[":NOR_RP"].fields["Virtual NOR RP input (not tied to MCU reset)"].user_value=1 end
 end
 if SAVING and v==0x5a5a and not saved then saved=true;m:save(STATE)end
 if SAVING and v==0xa55a and not loaded then loaded=true;m:load(STATE);return end
 if FINAL_SAVE and v==0xa55a and not saved then saved=true;m:save(STATE);return end
 if v==0xa55a or v==0xdead or frame>6000 or (MODE=="powercut" and st==70) then
  if SAVING and v==0xa55a and not restored and frame<6000 then return end
  local f=assert(io.open(RESULT,"w"));f:write(string.format('{"marker":%d,"stage":%d,"failure_d0":%d,"pc":%d,"frames":%d,"restored":%s,"events":[%s]}',v,st,b:read_u16(0x20006),cpu.state.CURPC.value,frame,tostring(restored),table.concat(events,",")));f:close();m:exit()
 end
end)
'''.replace('SAVING','true'if a.mode in ['save','save-program','save-nested','save-setup','save-unlock']else'false').replace('FINAL_SAVE','true'if a.save_final else'false').replace('MODE',json.dumps(a.mode)).replace('STATE',json.dumps(str(state))).replace('RESULT',json.dumps(str(folder/'cpu.json')))
    (folder/'observe.lua').write_text(lua)
    command=[str(binary),'asmdana','-video','none','-sound','none','-nothrottle','-skip_gameinfo','-nowriteconfig','-cfg_directory',str(cfg),'-nvram_directory',str(nvram),'-state_directory',str(folder/'states'),'-rom',str(rom),'-autoboot_delay','0','-autoboot_script',str(folder/'observe.lua'),'-log','-oslog']
    command+=['-nor',a.chip]
    if a.load_state:command+=['-state',str(a.load_state)]
    env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',TMPDIR=str(folder))
    with (folder/'run.out').open('w')as out:r=subprocess.run(command,cwd=root/'runtime/diag',env=env,stdout=out,stderr=subprocess.STDOUT,timeout=100)
    data=json.loads((folder/'cpu.json').read_text())if (folder/'cpu.json').exists()else{}
    text=(folder/'run.out').read_text();faults={'partial-data':'NOR_X16_DATA_STROBES_UNQUALIFIED','width':'NOR_X16_BUS_WIDTH_REQUIRED','unmapped':'EXTERNAL_DECODE_OR_PROTECTION','unknown':'FLASH_BYTES_NOT_SUPPLIED','powercut-read':'FLASH_BYTES_NOT_SUPPLIED','group-alignment':'NOR_MULTIWORD_ADDRESS_UNDEFINED'}
    if a.chip=='m29w320db'and a.mode=='reference':faults['reference']='NOR_REFERENCE_SESSION_WRITE_DISABLED'
    expected=faults.get(a.mode)
    data['expected_guard']=expected
    data['qualification']='STORAGE_GUARD'if a.expect_rejection else'BUS_GUARD'if expected else'POWER_CUT_PENDING'if a.mode=='powercut'else'CPU_FUNCTIONAL'
    ok=expected in text if expected else data.get('marker')==(0x5a5a if a.mode=='powercut'else 0xa55a) and 'DANA_PHYSICAL_BLOCKED'not in text
    data.update(mode=a.mode,chip=a.chip,returncode=r.returncode,seed_sha256=before,seed_preserved=before==hashlib.sha256(rom.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    disk_after={str(p.relative_to(nvram)):hashlib.sha256(p.read_bytes()).hexdigest()for p in nvram.rglob('*')if p.is_file()}if nvram.exists()else{}
    data['working_storage_preserved']=disk_before==disk_after
    if a.expect_rejection:
        data['pass']=r.returncode!=0 and any(t in text for t in ['NOR save-state conflicts','NOR working-storage checksum mismatch','different seed/profile','incompatible header','Truncated NOR working storage']) and disk_before==disk_after and data['seed_preserved']
    else:data['pass']=bool(ok and r.returncode==0 and data['seed_preserved'] and not any(t in text for t in ['LUA ERROR','Lua error','Error in Lua']) and (a.mode not in ['save','save-program','save-nested','save-setup','save-unlock']or data.get('restored')))
    (folder/'result.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:v for k,v in data.items()if k!='events'}),flush=True)
    if not data['pass']:print(text[-3500:]);raise SystemExit(1)
if __name__=='__main__':main()
