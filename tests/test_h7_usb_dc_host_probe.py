#!/usr/bin/env python3
"""Host-only protocol tests; never substitutes for guest M68000 evidence."""
import socket
import sys
import threading
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from h7_usb_dc_host_probe import UsbTransport, UsbProbeError, HEADER, ACK, NAK, MAX_PAYLOAD

class PeerTests(unittest.TestCase):
    def pair(self):
        a,b=socket.socketpair()
        self.addCleanup(a.close);self.addCleanup(b.close)
        a.settimeout(2);b.settimeout(2)
        return a,b
    def test_status_framing_and_length(self):
        a,b=self.pair()
        def peer():
            req=b.recv(16)
            magic,v,op,addr,ep,flags,hs,n,seq=HEADER.unpack(req)
            self.assertEqual((magic,v,op,addr,ep,n),(b'DUSB',1,0x10,0,0,8))
            b.sendall(HEADER.pack(b'DUSB',1,0x90,0,0,0,ACK,8,seq)+bytes([1,1,0,1,0,0,0,0]))
        thread=threading.Thread(target=peer);thread.start()
        st,data=UsbTransport(a).exchange(0x10,length=8)
        thread.join(timeout=2)
        self.assertEqual((st,len(data),data[1]),(0,8,1))
    def test_no_fabricated_descriptor(self):
        from h7_usb_dc_host_probe import probe
        class Fake:
            def __init__(self):self.ops=[]
            def exchange(self,op,**kw):
                self.ops.append(op)
                if op==1:return ACK,b''
                if op==0x10:return ACK,bytes([1,0,0,0,0,0,0,0])
                raise AssertionError('Guest did not connect: host must not send RESET or SETUP')
        f=Fake();r=probe(f,0.03)
        self.assertEqual(r['status'],'BLOCKED_NO_GUEST_SOFTCONNECT')
        self.assertNotIn(7,f.ops)
        self.assertNotIn(3,f.ops)
    def test_reject_oversized_payload(self):
        a,b=self.pair()
        with self.assertRaises(ValueError):UsbTransport(a).exchange(7,payload=b'X'*(MAX_PAYLOAD+1))
    def test_mismatch_sequence_rejected(self):
        a,b=self.pair()
        def peer():
            req=b.recv(16)
            magic,v,op,addr,ep,flags,hs,n,seq=HEADER.unpack(req)
            b.sendall(HEADER.pack(magic,v,op|0x80,addr,ep,0,ACK,0,seq+1))
        t=threading.Thread(target=peer);t.start()
        with self.assertRaises(UsbProbeError):UsbTransport(a).exchange(1)
        t.join(timeout=2)

if __name__=='__main__':unittest.main()
