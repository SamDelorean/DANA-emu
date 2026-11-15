#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""M29W320DB native bus programs; shared synthetic-reset harness, no vendor bytes."""
from d7_5_native import Code, MARKER
from nor_native import BASE, TARGET, rd, check, stage, wait, finish, payload as intel_payload

def command(c,v,a=BASE):c.move_w(v,a)
def unlock(c,op):
    c.move_b(0xaa,BASE+0xaaa);c.move_b(0x55,BASE+0x554);c.move_b(op,BASE+0xaaa)
def poll(c,a,value=0x80):
    loop=c.unique();c.label(loop);rd(c,a);c.w(0x0240,0x80,0x0c40,value,0x6706);c.jump(loop)
def program(c,a,v,bypass=False):
    if bypass:command(c,0xa0)
    else:unlock(c,0xa0)
    c.move_w(v,a);poll(c,a,v&0x80);check(c,a,v)
def erase_start(c,a):unlock(c,0x80);c.move_b(0xaa,BASE+0xaaa);c.move_b(0x55,BASE+0x554);c.move_b(0x30,a)
def erase(c,a):erase_start(c,a);poll(c,a);check(c,a,65535)
def identify(c):unlock(c,0x90)

def payload(mode):
    if mode in ['width','unmapped','address-error','cs-berr','cs-ro']:return intel_payload(mode)
    c=Code();c.w(0x46fc,0x2700);c.move_w(0,0xfffffb0a)
    if mode=='watchdog':
        rd(c,MARKER);c.w(0x0c40,0x5a5a,0x6606);c.jump('after_watchdog')
    for i in range(0,64,2):c.move_w(0,MARKER+i)
    stage(c,1)
    if mode in ['persist','powercut','factory-lock']:
        c.w(0x1039);c.l(0xfffff419);c.w(0x0240,1,0x0c40,1,0x6606);c.jump('reopen')
    if mode=='identify':
        identify(c);check(c,BASE,0x20);check(c,BASE+2,0x22cb);check(c,TARGET+4,0)
        command(c,0x98,BASE+0xaa)
        expected={0x10:81,0x11:82,0x12:89,0x13:2,0x15:0x40,0x1b:0x27,0x1c:0x36,0x1d:0xb5,0x1e:0xc5,0x1f:4,0x20:0,0x21:10,0x23:5,0x25:4,0x27:22,0x28:2,0x2c:4,0x2d:0,0x2f:0x40,0x31:1,0x33:0x20,0x35:0,0x37:0x80,0x39:0x3e,0x3c:1,0x40:80,0x41:82,0x42:73,0x43:49,0x44:48,0x46:2,0x47:1,0x48:1,0x49:4,0x4f:2}
        for a,v in expected.items():check(c,BASE+2*a,v)
        rd(c,BASE+0xc2);c.record(MARKER+0x20);command(c,0xf0);check(c,BASE+2,0x22cb)
        command(c,0xf0);check(c,BASE+2,0x316);check(c,BASE+0x400002,0x316);check(c,BASE+0x3ffffe,65535)
    elif mode in ['program','persist']:
        program(c,TARGET,0x1234);program(c,TARGET+2,0x5678)
        c.move_w(0x1111,TARGET+4);check(c,TARGET+4,65535)
        unlock(c,0x20);program(c,TARGET+6,0xabcd,True);command(c,0xf0)
        # Read/reset clears errors but does not leave unlock-bypass.
        program(c,TARGET+8,0xaabb,True);command(c,0x90);command(c,0)
        unlock(c,0xa0);c.move_w(65535,TARGET);wait(c,2);check(c,TARGET,0x20,0x20)
        command(c,0xf0);check(c,TARGET,0x1234)
    elif mode=='erase':
        for a in [BASE+0x3000,BASE+0x4000,BASE+0x6000,BASE+0x8000,BASE+0x10000,BASE+0x3f0000]:program(c,a,0)
        erase(c,BASE+0x4000);check(c,BASE+0x3000,0);check(c,BASE+0x6000,0)
        erase(c,BASE+0x8000);check(c,BASE+0x6000,0);check(c,BASE+0x10000,0)
        erase(c,BASE+0x3ffffe);check(c,BASE+0x3f0000,65535)
        erase(c,BASE+0x3000);check(c,BASE+2,65535);check(c,BASE+0x6000,0)
    elif mode=='chip':
        program(c,BASE+0x3000,0);program(c,TARGET,0);program(c,BASE+0x3ffffe,0)
        unlock(c,0x80);c.move_b(0xaa,BASE+0xaaa);c.move_b(0x55,BASE+0x554);c.move_b(0x10,BASE+0xaaa)
        check(c,TARGET,0,0x80);command(c,0xb0);command(c,0xf0);check(c,TARGET,0,0x80)
        poll(c,TARGET);check(c,BASE+0x3000,65535);check(c,TARGET,65535);check(c,BASE+0x3ffffe,65535)
    elif mode in ['suspend','multi','save','watchdog']:
        program(c,TARGET,0);program(c,TARGET+0x10000,0);erase_start(c,TARGET)
        if mode=='multi':
            command(c,0x30,TARGET+0x10000);command(c,0xb0);poll(c,TARGET);check(c,BASE+2,0x316);command(c,0x30);poll(c,TARGET);check(c,TARGET+0x10000,65535)
        elif mode=='save':c.move_w(0x5a5a,MARKER);poll(c,TARGET);check(c,TARGET,65535)
        else:
            wait(c,4);check(c,TARGET,8,8);command(c,0xb0);poll(c,TARGET)
            rd(c,TARGET);c.w(0x3200);rd(c,TARGET);c.w(0xb340,0x0240,4);c.expect(4)
            rd(c,TARGET);c.w(0x3200);rd(c,TARGET);c.w(0xb340,0x0240,0x40);c.expect(0)
            check(c,BASE+2,0x316)
            if mode=='watchdog':
                c.move_w(0x5a5a,MARKER);c.move_w(1,0xfffffb0a);c.w(0x4e72,0x2700);c.label('after_watchdog');check(c,TARGET,0x80,0x80)
            else:
                program(c,TARGET+0x20000,0x3456);identify(c);check(c,BASE+2,0x22cb);command(c,0xf0)
            command(c,0x30);poll(c,TARGET);check(c,TARGET,65535);check(c,TARGET+0x10000,0)
    elif mode=='save-unlock':
        c.move_b(0xaa,BASE+0xaaa);c.move_b(0x55,BASE+0x554);c.move_w(0x5a5a,MARKER);wait(c,4096)
        c.move_b(0xa0,BASE+0xaaa);c.move_w(0x1234,TARGET);poll(c,TARGET,0);check(c,TARGET,0x1234)
    elif mode=='timing':
        c.move_w(0,0xfffff600);c.move_w(0,0xfffff602);c.move_w(65535,0xfffff604);c.move_w(0x109,0xfffff600)
        rd(c,0xfffff608);c.record(MARKER+0x10);erase_start(c,TARGET);check(c,TARGET,0,8)
        poll(c,TARGET);rd(c,0xfffff608);c.w(0x9079);c.l(MARKER+0x10);c.record(MARKER+0x12)
        c.w(0x0c40,26210,0x6406);c.jump('fail');c.w(0x0c40,26225,0x6306);c.jump('fail')
    elif mode=='protect':
        stage(c,6);wait(c,4096);unlock(c,0xa0);c.move_w(0,BASE+0x3000);wait(c,2);check(c,BASE+0x3000,65535)
        program(c,TARGET,0x1234);erase_start(c,BASE+0x3000);wait(c,8);check(c,BASE+0x3000,65535)
        identify(c);check(c,BASE+4,1);command(c,0xf0);stage(c,7);wait(c,4096);program(c,BASE+0x3000,0)
    elif mode=='rp':
        program(c,TARGET,0);erase_start(c,TARGET);stage(c,30);wait(c,8192);erase(c,TARGET);check(c,TARGET,65535)
    elif mode=='powercut':
        program(c,TARGET,0);erase_start(c,TARGET);check(c,TARGET,0,0x80);stage(c,70);c.move_w(0x5a5a,MARKER);c.w(0x4e72,0x2700)
    elif mode=='invalid':
        for a,v in [(BASE,0xaa),(BASE+0x554,0x55),(BASE+0xaaa,0xa0),(TARGET,0x1234)]:command(c,v,a)
        check(c,TARGET,65535);command(c,0x90);check(c,BASE+2,0x316)
    elif mode=='accelerated':program(c,TARGET,0x1234,True)
    elif mode=='factory-lock':
        stage(c,80);wait(c,4096);command(c,0x60,TARGET+4);command(c,0x60,TARGET+0xc);wait(c,4)
        command(c,0x40,TARGET+4);wait(c,1);check(c,TARGET+4,1);command(c,0xf0)
        stage(c,81);wait(c,4096);identify(c);check(c,TARGET+4,1);command(c,0xf0)
        unlock(c,0xa0);c.move_w(0,TARGET);wait(c,1);check(c,TARGET,65535)
    elif mode=='factory-unprotect':
        stage(c,80);wait(c,4096)
        bases=[0,0x4000,0x6000,0x8000]+list(range(0x10000,0x400000,0x10000))
        for a in bases:
            command(c,0x60,BASE+a+4);command(c,0x60,BASE+a+4);wait(c,4)
        command(c,0x60,BASE+0x84);command(c,0x60,BASE+0x84);wait(c,400)
        for a in bases:command(c,0x40,BASE+a+0x84);wait(c,1);check(c,BASE+a+0x84,0)
        command(c,0xf0);stage(c,81);wait(c,4096);identify(c);check(c,TARGET+4,0);command(c,0xf0);program(c,TARGET,0x1234)
    elif mode=='partial-data':unlock(c,0xa0);c.move_b(0,TARGET)
    elif mode=='reference':program(c,TARGET,0x1234)
    else:raise ValueError(mode)
    if mode in ['persist','powercut','factory-lock']:
        c.jump('done');c.label('reopen');stage(c,50)
        if mode=='persist':check(c,TARGET,0x1234);check(c,TARGET+2,0x5678);check(c,TARGET+6,0xabcd);check(c,TARGET+8,0xaabb)
        elif mode=='factory-lock':
            identify(c);check(c,TARGET+4,1);command(c,0xf0);unlock(c,0xa0);c.move_w(0,TARGET);wait(c,1);check(c,TARGET,65535)
        else:
            c.w(0x1039);c.l(0xfffff419);c.w(0x0240,2,0x0c40,2,0x6606);c.jump('recover_cut')
            rd(c,TARGET);c.jump('fail');c.label('recover_cut');erase(c,TARGET);check(c,TARGET,65535)
    return finish(c)
