#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""One HOLD-only D7.5 campaign; existing dana-diag only, disposable images only.
No invocation, source modification, build or T operation occurs on import.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import selectors
import time
import struct
import subprocess
import tempfile

BASE_BINARY='01ad4619bf82964c11d96049a3ff6c9ebfdcca84cbe0df470dcc3f88c0711417'
ENTRY=0x2140
MARKER=0x20000
BUFFER=0x21000

class NativeBlocked(RuntimeError):
    pass


def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def crc7(data):
    crc=0
    for value in data:
        for bit in range(7,-1,-1):
            fb=((value>>bit)^(crc>>6))&1
            crc=(crc<<1)&127
            if fb: crc^=9
    return (crc<<1)|1


def crc16(data):
    crc=0
    for value in data:
        crc^=value<<8
        for _ in range(8): crc=((crc<<1)^(0x1021 if crc&0x8000 else 0))&65535
    return crc


class Code:
    """Small diagnostic byte encoder, not a CPU or firmware implementation."""
    def __init__(self): self.data=bytearray(); self.labels={}; self.fixups=[]; self.count=0
    def w(self,*words):
        for word in words: self.data+=struct.pack('>H',word&65535)
    def l(self,value): self.data+=struct.pack('>I',value)
    def label(self,name): self.labels[name]=ENTRY+len(self.data)
    def unique(self): self.count+=1; return f'label_{self.count}'
    def absolute(self,opcode,name):
        self.w(opcode);self.fixups.append((len(self.data),name));self.l(0)
    def jsr(self,name): self.absolute(0x4eb9,name)
    def jump(self,name): self.absolute(0x4ef9,name)
    def move_w(self,value,address): self.w(0x33fc,value);self.l(address)
    def move_b(self,value,address): self.w(0x13fc,value);self.l(address)
    def send(self,value): self.w(0x303c,value);self.jsr('spi')
    def expect(self,value):
        self.w(0x0c40,value,0x6706);self.jump('fail') # cmpi.w; beq.s over jmp.l
    def record(self,address): self.w(0x33c0);self.l(address)
    def command(self,op,arg=0,expected=0):
        packet=bytes([0x40|op])+struct.pack('>I',arg)
        for v in packet+bytes([crc7(packet)]): self.send(v)
        if op==12:self.send(255) # SPI stuff byte
        self.jsr('response');self.expect(expected)
    def select(self,slot):
        self.move_b(0 if slot==0 else 8,0xfffff439)
        self.move_b(4 if slot==0 else 0,0xfffff429)
    def init(self,slot):
        self.select(slot);self.command(0,expected=1);self.command(8,0x1aa,1)
        for v in [0,0,1,0xaa]:self.send(255);self.expect(v)
        self.command(55,expected=1);self.command(41,0x40000000)
        self.command(59,1)
    def block(self,seed,token,expected,bad_crc=False,partial=None):
        data=bytes((seed+i)&255 for i in range(512))
        self.send(token)
        for value in data[:partial]: self.send(value)
        if partial is not None:return
        crc=crc16(data)^(1 if bad_crc else 0)
        self.send(crc>>8);self.send(crc&255)
        self.jsr('response');self.record(MARKER+4);self.expect(expected)
        self.jsr('busy')
    def read_blocks(self,start,count,buffer):
        self.command(17 if count==1 else 18,start*512)
        for block in range(count):
            self.jsr('response');self.expect(0xfe)
            for i in range(512):
                self.send(255);self.w(0x13c0);self.l(buffer+block*512+i)
            self.send(255);self.send(255)
        if count>1:self.command(12)
    def finish(self):
        self.label('done')
        self.move_w(0xa55a,MARKER);self.w(0x4e72,0x2700)
        self.label('fail');self.record(MARKER+6);self.move_w(0xdead,MARKER);self.w(0x4e72,0x2700)
        self.label('spi');self.w(0x33c0);self.l(0xfffff702)
        self.w(0x0079,0x0100);self.l(0xfffff704)
        self.label('xch');self.w(0x0839,0);self.l(0xfffff704)
        self.w(0x6600,((self.labels['xch']-(ENTRY+len(self.data)+2))&65535))
        self.w(0x3039);self.l(0xfffff700);self.w(0x4e75)
        for name,response in [('response',True),('busy',False)]:
            self.label(name);self.w(0x3e3c,4095 if not response else 15) # move.w #limit,d7
            self.w(0x7c00) # moveq #0,d6 (busy sample count)
            loop=ENTRY+len(self.data);self.send(255);self.w(0x0c40,255)
            done=self.unique()
            self.w(0x6706 if response else 0x6606);self.jump(done)
            # Above inverse condition skips jump: response waits FF, busy waits non-FF.
            if not response:self.w(0x5246) # addq.w #1,d6
            self.w(0x51cf,((loop-(ENTRY+len(self.data)+2))&65535));self.jump('fail')
            self.label(done)
            if not response:
                self.w(0x33c6);self.l(MARKER+8)
            self.w(0x4e75)
        for pos,name in self.fixups:struct.pack_into('>I',self.data,pos,self.labels[name])
        payload=bytes(self.data);end=ENTRY+len(payload)
        header=bytearray(64);header[:8]=b'DANARAM1'
        struct.pack_into('>8I',header,8,ENTRY,ENTRY,len(payload),0x1000,0x400000,0x2000,end,end)
        header[40:60]=hashlib.sha1(payload).digest();struct.pack_into('>I',header,60,1)
        return bytes(header)+payload


def fixture(mode):
    c=Code()
    if mode=='reset_partial':
        c.w(0x3039);c.l(MARKER);c.w(0x0c40,0x5a5a,0x6606);c.jump('done')
    for address,value in [(0xfffff408,0x20),(0xfffff409,0x20),(0xfffff40b,0x20),
                          (0xfffff440,0x20),(0xfffff441,0x20),(0xfffff443,0x20),
                          (0xfffff438,8),(0xfffff439,8),(0xfffff43b,8),
                          (0xfffff428,4),(0xfffff429,4),(0xfffff42b,4)]:c.move_b(value,address)
    c.move_w(0x0607,0xfffff704)
    for _ in range(10):c.send(255)
    c.init(0);c.select(2);c.init(1)
    buffers=[]
    for slot in range(2):
        c.select(slot);seed=0x31+slot*0x40
        if mode in ('write','protected','crc','io_error','partial','power_partial','eject_partial','close_partial','reset_partial'):
            c.command(24,(16 if mode=='io_error' else 2)*512)
            partial=127 if mode in ('partial','power_partial','eject_partial','close_partial','reset_partial') else None
            expected=0x0b if mode=='crc' else (0x0d if mode in ('protected','io_error') or (mode=='write' and slot==1) else 5)
            c.block(seed,0xfe,expected,mode=='crc',partial)
            if partial is not None:
                if mode=='power_partial':c.move_b(0,0xfffff409 if slot==0 else 0xfffff441)
                if mode in ('eject_partial','close_partial','reset_partial'):
                    c.move_w(0x5a5a if mode=='reset_partial' else 0xa55a,MARKER)
                    c.w(0x4e72,0x2700);break
                c.select(2)
        if mode in ('write','reopen'):
            if mode=='write' and slot==0:
                c.command(25,4*512)
                c.block(seed+1,0xfc,5);c.block(seed+2,0xfc,5)
                c.send(0xfd);c.jsr('busy')
            c.read_blocks(2,1,BUFFER+slot*2048)
            c.read_blocks(4,2,BUFFER+slot*2048+512)
            buffers.append((BUFFER+slot*2048,1536))
        elif mode=='both_write':
            c.command(24,2*512);c.block(seed,0xfe,5)
            c.command(25,4*512);c.block(seed+1,0xfc,5);c.block(seed+2,0xfc,5)
            c.send(0xfd);c.jsr('busy')
            c.read_blocks(2,1,BUFFER+slot*2048);c.read_blocks(4,2,BUFFER+slot*2048+512)
            buffers.append((BUFFER+slot*2048,1536))
    return c.finish(),buffers


def lua_script(result,buffers,mask,eject=False,snapshot=False,state=None):
    # Lua observes guest-owned results; it never writes SD registers or sectors.
    return f'''
local machine=manager.machine
local cpu=machine.devices[":maincpu"]
local memory=cpu.spaces["program"]
local frames=0
local done=false
local fields=machine.ioport.ports[":SDWRITE"].fields
fields["SD0 image writes"]:set_value({mask & 1})
fields["SD1 image writes"]:set_value({mask & 2})
local transactions=0
local tap=memory:install_write_tap(0xfffff700,0xfffff70b,"d75_spi_cpu",function(offset,data,mem_mask)
    transactions=transactions+1
end)
local saved=false
local save_frame=0
local reset_sent=false
local load_requested=false
local load_observed=false
local state_path={json.dumps(str(state),ensure_ascii=False) if state else 'nil'}
local load_notifier=emu.add_machine_post_load_notifier(function() load_observed=true end)
emu.register_frame_done(function()
    frames=frames+1
    if done then return end
    if frames>1800 then done=true;machine:exit();return end
    local value=memory:read_u16({MARKER})
    if value==0x5a5a and not reset_sent then reset_sent=true;machine:soft_reset();return end
    if value==0xa55a or value==0xdead then
        if state_path and not load_requested then load_requested=true;machine:load(state_path);return end
        if state_path and not load_observed then return end
        if {str(snapshot).lower()} and not saved then machine:save("d75");saved=true;save_frame=frames;return end
        if {str(snapshot).lower()} and saved and frames-save_frame<5 then return end
        if {str(eject).lower()} then
            for _,image in pairs(machine.images) do if image.image_type_name=="sdcard" then image:unload() end end
        end
        local file=assert(io.open({json.dumps(str(result),ensure_ascii=False)},"w"))
        file:write(string.format('{{"marker":%d,"pc":%d,"sr":%d,"sp":%d,"spi_cpu_writes":%d,"token":%d,"busy_samples":%d,"buffers":[',value,cpu.state["PC"].value,cpu.state["SR"].value,cpu.state["SP"].value,transactions,memory:read_u16({MARKER+4}),memory:read_u16({MARKER+8})))
        local ranges={{{','.join('{'+str(a)+','+str(n)+'}' for a,n in buffers)}}}
        for j,range in ipairs(ranges) do
            if j>1 then file:write(',') end
            file:write('"')
            for i=0,range[2]-1 do file:write(string.format('%02x',memory:read_u8(range[1]+i))) end
            file:write('"')
        end
        file:write(']}}');file:close();done=true;machine:exit()
    elseif frames>1800 then done=true;machine:exit() end
end)
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--diag',required=True,type=Path)
    parser.add_argument('--diag-sha256',required=True)
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if os.environ.get('DANA_D75_NATIVE_AUTHORIZED')!='YES':parser.error('HOLD: fresh native authorization required')
    if not args.diag.is_absolute() or args.diag.name!='dana-diag':parser.error('Only the existing absolute dana-diag path is permitted')
    if args.diag_sha256==BASE_BINARY or sha(args.diag)!=args.diag_sha256:parser.error('BLOCKED: wrong/unchanged read-only DIAG binary')
    contract=json.loads((Path(__file__).with_name('d7_5_status.json')).read_text())
    for artifact,expected in contract['campaign_sha256'].items():
        if sha(Path(__file__).resolve().parents[1]/artifact)!=expected:parser.error('BLOCKED: campaign artifact hash mismatch')
    if not args.source.is_absolute():parser.error('BLOCKED: explicit absolute canonical source directory required')
    for path,expected in contract['production_sha256'].items():
        if sha(args.source/Path(path).name)!=expected:parser.error('BLOCKED: canonical installed production source mismatch')
    if not args.output.is_absolute() or args.output.exists():parser.error('Require a new absolute evidence directory; no existing media accepted')
    args.output.mkdir(parents=True)
    root=args.output
    cards=[root/'DISPOSABLE_SD0.img',root/'DISPOSABLE_SD1.img']
    original=[bytes([0x11+i])*16384 for i in range(2)]
    for p,b in zip(cards,original):p.write_bytes(b)
    results=[]
    def run(mode,mask,fault=False,snapshot=False,state=None):
        folder=root/(mode+('_state' if state else ''));folder.mkdir()
        package,ranges=fixture(mode if not state else 'reopen')
        (folder/'diagnostic.dana').write_bytes(package)
        (folder/'control.lua').write_text(lua_script(folder/'cpu.json',ranges,mask,mode=='eject_partial',snapshot,state))
        def limit():
            if fault:
                import resource
                signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
                resource.setrlimit(resource.RLIMIT_FSIZE,(4096,4096))
        command=[str(args.diag),'asmdana','-quickload',str(folder/'diagnostic.dana'),'-sd1',str(cards[0]),'-sd2',str(cards[1]),
                 '-autoboot_script',str(folder/'control.lua'),'-autoboot_delay','0','-video','none','-sound','none','-nothrottle',
                 '-nowriteconfig','-cfg_directory',str(root/'cfg'),'-nvram_directory',str(root/'nvram'),'-state_directory',str(root/'states'),'-oslog']
        before=[sha(p) for p in cards]
        process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,preexec_fn=limit if fault else None)
        output=bytearray();deadline=time.monotonic()+90
        poll=selectors.DefaultSelector();poll.register(process.stdout,selectors.EVENT_READ)
        try:
            while poll.get_map():
                if time.monotonic()>deadline:raise NativeBlocked('Native wall timeout')
                for key,_ in poll.select(1):
                    chunk=os.read(key.fileobj.fileno(),65536)
                    if not chunk:poll.unregister(key.fileobj);continue
                    if len(output)+len(chunk)>2*1024*1024:raise NativeBlocked('Native output budget exceeded')
                    output+=chunk
            process.wait(timeout=5)
        finally:
            if process.poll() is None:process.kill();process.wait(timeout=5)
            (folder/'native.log').write_bytes(output)
            poll.close()
        observation=json.loads((folder/'cpu.json').read_text()) if (folder/'cpu.json').exists() else {}
        record={'case':mode,'process_rc':process.returncode,'diag_sha256':args.diag_sha256,'before':before,'after':[sha(p) for p in cards],'cpu':observation}
        record['status']='PASS' if process.returncode==0 and observation.get('marker')==0xa55a and (state or observation.get('spi_cpu_writes',0)>0) else ('FAIL' if observation.get('marker')==0xdead else 'BLOCKED')
        if mode=='both_write' and observation.get('busy_samples',0)<=0:record['status']='FAIL'
        results.append(record)
        if record['status']=='BLOCKED':raise NativeBlocked('Native evidence missing or ambiguous: '+mode)
        if record['status']!='PASS':raise RuntimeError('Native CPU case failed: '+mode)
        return observation
    try:
        for mode in ('protected','crc','partial','power_partial','eject_partial','close_partial','reset_partial','io_error'):
            mask=0 if mode=='protected' else 3
            before=[p.read_bytes() for p in cards]
            run(mode,mask,mode=='io_error')
            if mode=='io_error' and b'BACKEND_WRITE_OR_SHORT_WRITE' not in (root/mode/'native.log').read_bytes():
                raise RuntimeError('Real backend failure was not observed')
            if [p.read_bytes() for p in cards]!=before:raise RuntimeError('Rejected/interrupted write modified disposable media: '+mode)
        run('write',1) # card0 enabled, card1 must still reject
        if cards[1].read_bytes()!=original[1]:raise RuntimeError('Independent SD1 protection failed')
        for p,b in zip(cards,original):p.write_bytes(b) # reset ONLY this campaign's own disposable images
        first=run('both_write',3,snapshot=True)
        persisted=[p.read_bytes() for p in cards]
        second=run('reopen',3) # separate process proves normal-close/reopen persistence
        for slot in range(2):
            expected=b''.join(bytes((0x31+slot*0x40+extra+i)&255 for i in range(512)) for extra in range(3))
            if bytes.fromhex(first['buffers'][slot])!=expected or bytes.fromhex(second['buffers'][slot])!=expected:
                raise RuntimeError('CPU readback differs from written bytes')
            full_expected=bytearray(original[slot])
            for lba,extra in [(2,0),(4,1),(5,2)]:
                full_expected[lba*512:(lba+1)*512]=expected[extra*512:(extra+1)*512]
                if persisted[slot][lba*512:(lba+1)*512]!=expected[extra*512:(extra+1)*512]:raise RuntimeError('Host image persistence mismatch')
            if persisted[slot]!=full_expected:raise RuntimeError('Unexpected changes outside target sectors')
        states=list((root/'states').rglob('d75.sta'))
        if len(states)!=1:raise RuntimeError('Native snapshot was not created uniquely')
        run('snapshot_restore',3,state=states[0])
        try:run('snapshot_protection',1,state=states[0])
        except RuntimeError:
            results[-1]['status']='PASS' if b'write protection differs' in (root/'snapshot_protection_state/native.log').read_bytes() else 'BLOCKED'
        if results[-1]['case']!='snapshot_protection' or results[-1]['status']!='PASS':raise RuntimeError('Saved write-policy mismatch not conclusively rejected')
        # Old state must be rejected after external bytes change; preserve the
        # altered disposable image and full logs rather than restoring a hash.
        with cards[0].open('r+b') as image:image.seek(512);image.write(b'D75_STALE_MEDIA')
        try:run('snapshot_stale',3,state=states[0])
        except RuntimeError:
            results[-1]['status']='PASS' if b'image changed' in (root/'snapshot_stale_state/native.log').read_bytes() else 'BLOCKED'
        if results[-1]['case']!='snapshot_stale' or results[-1]['status']!='PASS':raise RuntimeError('Stale media restore not conclusively rejected')
        status='PASS'
    except Exception as error:
        status='BLOCKED' if isinstance(error,NativeBlocked) else 'FAIL';results.append({'error':str(error),'status':status})
    (root/'result.json').write_text(json.dumps({'increment':'D7.5','status':status,'cases':results,'power_loss_durability':'UNQUALIFIED_NO_FSYNC'},indent=2)+'\n')
    if status!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
