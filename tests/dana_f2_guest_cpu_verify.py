#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Independently verify CPU-origin EmuTOS F2 pen evidence; never run MAME.

PASS requires NATURAL guest milestone and real CPU 8-bit + 16-bit SPI2
transactions. A host Lua MMIO exercise alone cannot satisfy this verifier.
"""
import argparse
import json
from pathlib import Path

GUEST_PACKAGE_SHA="c201c8527df87fa6a8788d8ac59f43298666196fefeee12dcac68295cb281b9d"
GUEST_IMG_SHA="ba590da2661bc582c19bb24d65db04667daf37a17d7aa51fb462b945933ba0a3"
GUEST_MAP_SHA="17cc980e675e2e1b50e713b9029f6fc3e51d3e55392deb99d53552d4b3af3e68"
TEXT_START=0x2140
TEXT_LIMIT=TEXT_START+223748
POLL_START=0x86a4
POLL_END=0x8816
RAW_START=0x852c
RAW_END=0x85a2
PF=0xfffff428
PG=0xfffff430
DATA=0xfffff800
CTRL=0xfffff802

def verdict(status,why,**data):
    return dict(status=status,scope="NATURAL_EMUTOS_CPU_PEN_ONLY",reason=why,**data)

def evaluate(receipt):
    if (not isinstance(receipt,dict) or
            receipt.get("schema")!="dana-f2-natural-guest-bus-v1" or
            receipt.get("status")!="CAPTURED" or
            receipt.get("origin")!="M68000_CPU_TAPS_AND_DEBUGGER_BREAKPOINTS" or
            receipt.get("natural_execution_only") is not True or
            receipt.get("no_guest_pass_in_lua") is not True):
        return verdict("BLOCKED_EVIDENCE","UNTRUSTED_OR_WRONG_NATIVE_OBSERVER")
    if any(receipt.get(k)!=v for k,v in (
            ("guest_manifest_map_sha256",GUEST_MAP_SHA),
            ("expected_guest_image_sha256",GUEST_IMG_SHA),
            ("expected_guest_package_sha256",GUEST_PACKAGE_SHA))):
        return verdict("BLOCKED_EVIDENCE","ORIGINAL_GUEST_IDENTITY_MISMATCH")
    events=receipt.get("events")
    counts=receipt.get("counters")
    if not isinstance(events,list) or not isinstance(counts,dict) or len(events)>20000:
        return verdict("BLOCKED_EVIDENCE","EVENT_SHAPE_OR_LIMIT")
    if receipt.get("event_count")!=len(events):
        return verdict("BLOCKED_EVIDENCE","EVENT_COUNT_MISMATCH")
    cpu=[]
    host=[]
    bp=[]
    time=0.0
    actual={"cpu_pf1_reads":0,"cpu_pg2_writes":0,
            "cpu_spi2_reads":0,"cpu_spi2_writes":0,"pen_input_events":0}
    for index,e in enumerate(events):
        if not isinstance(e,dict) or e.get("seq")!=index or not isinstance(e.get("time"),(int,float)):
            return verdict("BLOCKED_EVIDENCE","EVENT_SEQUENCE_OR_TIMESTAMP")
        if e["time"]<time or e["time"]>13: return verdict("BLOCKED_EVIDENCE","UNBOUNDED_OR_REORDERED_TIME")
        time=e["time"]
        origin=e.get("origin")
        if origin=="cpu":
            if e.get("kind") not in ("read","write") or any(type(e.get(k)) is not int
                       for k in ("pc","ir","sr","address","mask","data")):
                return verdict("BLOCKED_EVIDENCE","MALFORMED_NATIVE_CPU_BUS")
            if not TEXT_START<=e["pc"]<TEXT_LIMIT:
                return verdict("BLOCKED_EVIDENCE","BUS_CPU_PC_OUTSIDE_PINNED_EMUTOS_TEXT",pc=e["pc"])
            if e["address"]%2 or e["mask"] not in (0xff,0xff00,0xffff):
                return verdict("BLOCKED_EVIDENCE","INCORRECT_16BIT_BUS_LANES")
            lanes=([e["address"],e["address"]+1] if e["mask"]==0xffff else
                   [e["address"]] if e["mask"]==0xff00 else [e["address"]+1])
            if e.get("lanes")!=lanes:
                return verdict("BLOCKED_EVIDENCE","INCORRECT_EFFECTIVE_BYTE_LANES")
            if e["address"] not in (PF,PG,DATA,CTRL):
                return verdict("BLOCKED_EVIDENCE","UNEXPECTED_BUS_REGISTER",address=e["address"])
            if e["kind"]=="read" and 0xfffff429 in lanes:
                actual["cpu_pf1_reads"]+=1
            if e["kind"]=="write" and 0xfffff431 in lanes:
                actual["cpu_pg2_writes"]+=1
            if e["address"] in (DATA,CTRL):
                actual["cpu_spi2_reads" if e["kind"]=="read" else "cpu_spi2_writes"]+=len(lanes)
            cpu.append(e)
        elif origin=="host_input":
            if e.get("kind")!="PEN_DOWN" or e.get("value")!=1:
                return verdict("BLOCKED_EVIDENCE","FORGED_HOST_ACTION")
            if any(type(e.get(k)) is not int or not 0<=e[k]<=65535 for k in ("penx_raw","peny_raw")):
                return verdict("BLOCKED_EVIDENCE","HOST_COORDINATE_NOT_RECORDED")
            actual["pen_input_events"]+=1
            host.append(e)
        elif origin=="debugger_breakpoint":
            if e.get("kind")!="PC_REACHED" or type(e.get("pc")) is not int:
                return verdict("BLOCKED_EVIDENCE","WRONG_NATIVE_BREAKPOINT_SHAPE")
            expected={"_os_header":0x2140,"_dana_init":0x827e,
                "_dana_kbd_init":0x8428,"_dana_ts_rawread":RAW_START,
                "_dana_poll_touchscreen":POLL_START}
            if expected.get(e.get("label"))!=e["pc"]:
                return verdict("BLOCKED_EVIDENCE","BREAKPOINT_NOT_PINNED_EMUTOS_PC")
            bp.append(e)
        else:
            return verdict("BLOCKED_EVIDENCE","UNRECOGNIZED_EVENT_ORIGIN")
    if any(counts.get(k)!=n for k,n in actual.items()):
        return verdict("BLOCKED_EVIDENCE","COUNTERS_DO_NOT_MATCH_EVENTS")
    if counts.get("overflow")!=0:
        return verdict("BLOCKED_EVIDENCE","INCOMPLETE_RAW_EVENT_LOG",overflow=counts.get("overflow"))
    if receipt.get("guest_state")!="ORIGINAL_QUICKLOAD_ACTIVE":
        return verdict("BLOCKED_GUEST","AUTHENTIC_QUICKLOAD_NOT_OBSERVED")
    names={b["label"] for b in bp}
    milestones=sorted(names)
    if "_os_header" not in names:
        return verdict("BLOCKED_GUEST","ORIGINAL_EMUTOS_ENTRY_NOT_OBSERVED",milestones=milestones)
    if len(host)!=1:
        return verdict("BLOCKED_EVIDENCE","PEN_HOST_INJECTION_NOT_EXACTLY_ONCE")
    if "_dana_poll_touchscreen" not in names:
        return verdict("NOT_REACHED","GUEST_TOUCHSCREEN_POLL_NOT_REACHED_WITHIN_BOUND",
                       milestones=milestones,cpu_bus_events=len(cpu))
    if "_dana_ts_rawread" not in names:
        return verdict("PARTIAL_CPU_TOUCH","POLL_REACHED_BUT_RAW_ADC_READ_NOT_CALLED",
                       milestones=milestones,cpu_bus_events=len(cpu))
    pen=host[0]
    pf_after=[e for e in cpu if e["seq"]>pen["seq"]
        and e["kind"]=="read" and e["address"]==PF
        and e["mask"]==0xff and not(e["data"]&2)
        and POLL_START<=e["pc"]<POLL_END]
    if not pf_after:
        return verdict("PARTIAL_CPU_TOUCH","NO_CPU_PF1_ACTIVE_LOW_READ_IN_GUEST_TOUCH_POLL",
                       milestones=milestones)
    def matches(e,kind,addr,value=None,check=None):
        if kind is None and addr is None:
            return check is not None and check(e)
        if e["kind"]!=kind or e["address"]!=addr:
            return False
        if addr in (DATA,CTRL) and e["mask"]!=0xffff:
            return False
        return (check(e["data"]) if check is not None else
                value is None or e["data"]==value)
    def pg_low(e):
        return e["kind"]=="write" and e["address"]==PG and e["mask"]==0xff and not e["data"]&4
    def pg_high(e):
        return e["kind"]=="write" and e["address"]==PG and e["mask"]==0xff and bool(e["data"]&4)
    def find_sequence(start,command,expected):
        spec=[
            ("write",CTRL,0x2247,None),
            ("write",DATA,command,None),
            (None,None,None,pg_low),
            ("write",CTRL,0x2347,None),
            ("read",CTRL,None,lambda v:bool(v&0x80)),
            ("write",DATA,0,None),
            ("write",CTRL,0x224f,None),
            ("write",CTRL,0x234f,None),
            ("read",CTRL,None,lambda v:bool(v&0x80)),
            (None,None,None,pg_high),
            ("read",DATA,expected,None)]
        for head in range(start,len(cpu)):
            if not matches(cpu[head],*spec[0]):continue
            found=[cpu[head]]
            pos=head+1
            for pred in spec[1:]:
                while pos<len(cpu) and not matches(cpu[pos],*pred):
                    pos+=1
                if pos>=len(cpu):break
                found.append(cpu[pos]);pos+=1
            if len(found)==len(spec):
                # CPU transaction all occurred after real contact, plus
                # PC-matched original guest source. No host MMIO writes.
                return pos,[(x["seq"],x["pc"]) for x in found]
        return None,None
    x=(290+(pen["penx_raw"]*3470)//65535)<<4
    y=(200+(pen["peny_raw"]*3450)//65535)<<4
    after=next((i for i,e in enumerate(cpu) if e["seq"]>pen["seq"]),len(cpu))
    nextx,seqx=find_sequence(after,0x90,x)
    nexty,seqy=find_sequence(nextx if nextx is not None else after,0xd0,y)
    if not seqx or not seqy:
        return verdict("PARTIAL_CPU_TOUCH","MISSING_COMPLETE_ORDERED_8_AND_16_BIT_CPU_SPI2_TRANSACTIONS",
                       milestones=milestones,PF1_cpu_read_seq=pf_after[0]["seq"],
                       expected_x=x,expected_y=y,found_x=bool(seqx),found_y=bool(seqy),
                       bus_events=len(cpu))
    return verdict("PASS_GUEST_CPU_PEN_X_Y","AUTHENTIC_ORIGINAL_GUEST_CPU_PF1_PG2_SPI2_ADC_BOTH_AXES",
                   milestones=milestones,raw_cpu_events=len(cpu),pen_trigger_seq=pen["seq"],
                   pf1_cpu_read_seq=pf_after[0]["seq"],x_word=x,y_word=y,
                   x_sequence=seqx,y_sequence=seqy,full_boot_proven=False)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("receipt",type=Path)
    ap.add_argument("report",type=Path)
    args=ap.parse_args()
    if not args.receipt.is_file() or args.receipt.stat().st_size>8*1024*1024:
        outcome=verdict("BLOCKED_EVIDENCE","RECEIPT_NOT_PRESENT_OR_OVERSIZED")
    else:
        try:outcome=evaluate(json.loads(args.receipt.read_text()))
        except (ValueError,KeyError,TypeError,OverflowError) as exc:
            outcome=verdict("BLOCKED_EVIDENCE","INVALID_NATIVE_RECEIPT",error=str(exc))
    args.report.write_text(json.dumps(outcome,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:outcome[k] for k in ("status","reason","scope")},sort_keys=True))
    return 0 if outcome["status"]=="PASS_GUEST_CPU_PEN_X_Y" else 2

if __name__=="__main__":
    raise SystemExit(main())
