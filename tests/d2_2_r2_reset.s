/* SPDX-License-Identifier: BSD-3-Clause */
/* Static assembly cross-check. Assemble in a private directory containing portc_a.bin. */
.text
_start:
    tst.w (0x00020000).l
    bne.w post_reset
    move.w #1,(0x00020000).l
    .incbin "portc_a.bin"
post_reset:
    move.w (0xfffff412).l,%d0
    move.w %d0,(0x00020002).l
    stop #0x2700
