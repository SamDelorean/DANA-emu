    .text
    .globl dana_mmio01
dana_mmio01:
    move.l #0xfffff300, %a0
    move.b  #0x40, (%a0)
    move.b  (%a0), %d0
    move.l #0xfffef300, %a0
    move.b  (%a0), %d0
    move.l #0xfffff301, %a0
    move.b  (%a0), %d0
    rts
