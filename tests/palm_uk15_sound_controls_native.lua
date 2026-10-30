-- SPDX-License-Identifier: BSD-3-Clause
-- Existing MAME sound controls on an original-Palm session; no guest injection.
local m=manager.machine
local frame=0
emu.register_frame_done(function()
 frame=frame+1
 if frame==10 then m:load(assert(os.getenv("DANA_KEYBOARD_STATE")))end
 if frame==40 then
  local before=m.sound.ui_mute
  m.sound.ui_mute=true
  assert(m.sound.ui_mute and m.sound.muted,"MAME UI mute must engage")
  m.sound.ui_mute=false
  assert(not m.sound.ui_mute,"MAME UI mute must release")
  m.sound.ui_mute=before
  local f=assert(io.open(assert(os.getenv("DANA_LCD_DUMP_DIR")).."/calendar.txt","w"))
  f:write("MAME_SOUND_UI_MUTE_AND_RESTORE_PASS\n");f:close()
 end
 if frame==50 then m:exit()end
end)
