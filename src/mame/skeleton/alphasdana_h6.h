// license:BSD-3-Clause
// copyright-holders:DANA-emu contributors
// Passive observation only. No radio device, network, ACK, IRQ or power rail.

void alphasdana_state::h6_trace(char const *event,u32 address,u16 value,u16 mask)
{
    if(!(ioport("H6_MONITOR")->read()&1) || m_h6_events>=512)return;
    ++m_h6_events;
    static char const *const requests[]={"UNKNOWN","OFF_REQUESTED","ACTIVE_REQUESTED","SLEEP_REQUESTED","WAKE_REQUESTED"};
    bool const driven=(m_gpio[24]&m_gpio[27]&1)!=0;
    char const *pad=driven?((m_gpio[25]&1)?"HIGH":"LOW"):"UNDRIVEN";
    logerror("DANA_H6 time=%.12f profile=%u pc=%08x event=%s address=%08x mask=%04x value=%04x software_request=%s digital_pad=%s controller_pending=%08x verified_board_rail=NO_VERIFICADO measured_current=NO_VERIFICADO\n",
        machine().time().as_double(),unsigned(m_storage_board),u32(m_maincpu->state_int(STATE_GENPCBASE)),
        event,address,mask,value,requests[m_h6_request],pad,m_pending);
}

void alphasdana_state::h6_pk_observe(offs_t reg,u8 value)
{
    // The original NetIF sets/clears PKDATA.0 behind a CSA size gate. This
    // is a requested action on Wireless, never a measured module state.
    if(m_storage_board==3 && reg==1)m_h6_request=(value&1)?2:1;
    h6_trace("PK_CONTROL",0xfffff440+u32(reg),value,0xff);
}
