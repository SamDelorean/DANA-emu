/* Test-owned MC68000 qualification fixture; not firmware or an emulator. */
.text
.macro snapshot destination
    moveq #0,%d0
    move.b 0xfffff42b.l,%d0
    move.w %d0,\destination\().l
.endm
.macro writebyte value,address
    move.b #\value,\address\().l
.endm
start:
    tst.w 0x20000.l
    bne.w post
    move.w #1,0x20000.l
    snapshot 0x10000
    writebyte 0,0xfffff42b
    snapshot 0x10002
    snapshot 0x10004
    writebyte 1,0xfffff42b
    snapshot 0x10006
    snapshot 0x10008
    writebyte 0x80,0xfffff42b
    snapshot 0x1000a
    snapshot 0x1000c
    writebyte 0xff,0xfffff42b
    snapshot 0x1000e
    snapshot 0x10010
    writebyte 0x7e,0xfffff42a
    snapshot 0x10012
    moveq #0,%d0
    move.b 0xfffff42a.l,%d0
    move.w #0x12a5,0xfffff42a.l
    moveq #0,%d0
    move.w 0xfffff42a.l,%d0
    move.w %d0,0x10014.l
    writebyte 0,0x00fff42b
    snapshot 0x10016
    writebyte 0x5a,0xfffff42b
    snapshot 0x10018
endpoint:
    stop #0x2700
post:
    moveq #0,%d0
    move.b 0xfffff42b.l,%d0
    move.w %d0,0x20002.l
    stop #0x2700
