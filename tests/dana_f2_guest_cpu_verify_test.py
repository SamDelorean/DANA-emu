#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Synthetic TEST-OF-VERIFIER ONLY. Never label these native EmuTOS PASS."""
from copy import deepcopy
import unittest
import dana_f2_guest_cpu_verify as v

def synthetic_receipt():
    events=[]
    def emit(origin,kind,**fields):
        e={"seq":len(events),"time":4.0+len(events)*0.005,
           "origin":origin,"kind":kind,**fields}
        if origin=="cpu":
            a=e["address"];m=e["mask"]
            e["lanes"]=([a,a+1] if m==0xffff else
                        [a] if m==0xff00 else [a+1])
            e["pc"]=0x86a8 if a==v.PF else 0x8530
            e["ir"]=0x4e71;e["sr"]=0x2700
        events.append(e)
    emit("debugger_breakpoint","PC_REACHED",label="_os_header",pc=0x2140)
    emit("debugger_breakpoint","PC_REACHED",label="_dana_poll_touchscreen",pc=0x86a4)
    emit("host_input","PEN_DOWN",value=1,penx_raw=32768,peny_raw=32768)
    emit("debugger_breakpoint","PC_REACHED",label="_dana_ts_rawread",pc=0x852c)
    emit("cpu","read",address=v.PF,mask=0xff,data=0)
    for command,lower,span in ((0x90,290,3470),(0xd0,200,3450)):
        sample=(lower+32768*span//65535)<<4
        for kind,addr,mask,data in (
            ("write",v.CTRL,0xffff,0x2247),
            ("write",v.DATA,0xffff,command),
            ("write",v.PG,0xff,0x19),
            ("write",v.CTRL,0xffff,0x2347),
            ("read",v.CTRL,0xffff,0x0080),
            ("write",v.DATA,0xffff,0),
            ("write",v.CTRL,0xffff,0x224f),
            ("write",v.CTRL,0xffff,0x234f),
            ("read",v.CTRL,0xffff,0x0080),
            ("write",v.PG,0xff,0x1d),
            ("read",v.DATA,0xffff,sample)):
            emit("cpu",kind,address=addr,mask=mask,data=data)
    return make_receipt(events)

def make_receipt(events):
    cnt=dict(cpu_pf1_reads=0,cpu_pg2_writes=0,cpu_spi2_reads=0,
             cpu_spi2_writes=0,pen_input_events=0,overflow=0)
    for e in events:
        if e["origin"]=="host_input":cnt["pen_input_events"]+=1
        elif e["origin"]=="cpu":
            if e["kind"]=="read" and 0xfffff429 in e["lanes"]:
                cnt["cpu_pf1_reads"]+=1
            if e["kind"]=="write" and 0xfffff431 in e["lanes"]:
                cnt["cpu_pg2_writes"]+=1
            if e["address"] in (v.DATA,v.CTRL):
                cnt["cpu_spi2_reads" if e["kind"]=="read" else "cpu_spi2_writes"]+=len(e["lanes"])
    return dict(schema="dana-f2-natural-guest-bus-v1",status="CAPTURED",
        origin="M68000_CPU_TAPS_AND_DEBUGGER_BREAKPOINTS",
        natural_execution_only=True,no_guest_pass_in_lua=True,
        guest_state="ORIGINAL_QUICKLOAD_ACTIVE",
        event_count=len(events),events=events,counters=cnt,
        guest_manifest_map_sha256=v.GUEST_MAP_SHA,
        expected_guest_image_sha256=v.GUEST_IMG_SHA,
        expected_guest_package_sha256=v.GUEST_PACKAGE_SHA)

class SyntheticVerifierUnitTests(unittest.TestCase):
    def test_complete_ordered_cpu_x_y_is_recognised_in_synthetic_fixture(self):
        result=v.evaluate(synthetic_receipt())
        self.assertEqual(result["status"],"PASS_GUEST_CPU_PEN_X_Y")
        self.assertFalse(result["full_boot_proven"])

    def test_one_axis_missing_not_pass(self):
        good=synthetic_receipt()
        incomplete=make_receipt(good["events"][:-1])
        result=v.evaluate(incomplete)
        self.assertEqual(result["status"],"PARTIAL_CPU_TOUCH")

    def test_cpu_pf1_read_from_wrong_address_or_pc_is_rejected(self):
        good=synthetic_receipt()
        changed=deepcopy(good)
        pf=next(e for e in changed["events"] if e.get("address")==v.PF)
        pf["pc"]=0x100000
        self.assertEqual(v.evaluate(changed)["status"],"BLOCKED_EVIDENCE")

    def test_no_guest_touch_poll_cannot_pass(self):
        good=synthetic_receipt()
        changed=[e for e in good["events"] if e.get("label")!="_dana_poll_touchscreen"]
        for seq,e in enumerate(changed):
            e=dict(e)
            e["seq"]=seq
            changed[seq]=e
        self.assertEqual(v.evaluate(make_receipt(changed))["status"],"NOT_REACHED")

    def test_dropped_events_and_guest_identity_are_rejected(self):
        good=synthetic_receipt()
        altered=deepcopy(good)
        altered["counters"]["overflow"]=1
        self.assertEqual(v.evaluate(altered)["status"],"BLOCKED_EVIDENCE")
        altered=deepcopy(good)
        altered["guest_manifest_map_sha256"]="0"*64
        self.assertEqual(v.evaluate(altered)["status"],"BLOCKED_EVIDENCE")

if __name__=="__main__":
    unittest.main()
