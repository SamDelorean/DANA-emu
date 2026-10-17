    .text
    .globl dana_mmio01
dana_mmio01:
    movea.l #0xfffff300, %a0
    move.b  #0x40, (%a0)
    move.b  (%a0), %d0
    movea.l #0xfffef300, %a0
    move.b  (%a0), %d0
    movea.l #0xfffff301, %a0
    move.b  (%a0), %d0
    stop    #0x2700
