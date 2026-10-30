-- SPDX-License-Identifier: BSD-3-Clause
-- 81 distinct physical inputs consumed by the ORIGINAL Palm OS M68000 code.
if _G.DANA_ST81_PALM_RUNNING then return end
_G.DANA_ST81_PALM_RUNNING=true
local m=manager.machine
local cpu=m.devices[":maincpu"]
local b=cpu.spaces.program
local dest=assert(os.getenv("DANA_LCD_DUMP_DIR"))
local state=assert(os.getenv("DANA_KEYBOARD_STATE"))
local keys=dofile(assert(os.getenv("DANA_KEYBOARD_INVENTORY")))
assert(#keys==81)
local fields,by_scan={},{}
for i,k in ipairs(keys)do
 fields[i]=assert(m.ioport.ports[k.tag].fields[k.name],k.name)
 by_scan[k.scan]=fields[i]
end
local out=assert(io.open(dest.."/keyboard.txt","w"))
local c=assert(io.open(dest.."/calendar.txt","w"));c:write("Original Palm 81-key campaign\n");c:close()
local frame,row=0,0
local seen,host_seen,released,chords={},{},{},{}
local packet={}
local headers,releases=0,0
local function dump(n)
 local base=b:read_u16(0xfffffa00)*65536+b:read_u16(0xfffffa02)
 local buf={}
 for a=base,base+11198,2 do local w=b:read_u16(a);buf[#buf+1]=string.char(w>>8,w&255)end
 local f=assert(io.open(string.format("%s/key-%02d.bin",dest,n),"wb"));f:write(table.concat(buf));f:close()
end
local tap=b:install_read_tap(0xfffff800,0xfffff801,"original_palm_all81",function(a,d,mask)
 local pc=cpu.state.CURPC.value
 local v=d&255
 if pc==0x1007e648 or pc==0x1007ecaa then
  headers=headers+1;packet={}
  if v==0x40 then releases=releases+1;if row>0 then released[row]=true end end
  out:write(string.format("F=%d ROW=%d HEADER=%02X PC=%08X\n",frame,row,v,pc));out:flush()
 elseif pc==0x1007e896 or pc==0x1007ed40 then
  seen[v]=true;packet[v]=true
  out:write(string.format("F=%d ROW=%d CODE=%02X PC=%08X\n",frame,row,v,pc));out:flush()
 end
end)
local first,interval=100,75
local combos={{9,43},{123,109},{70,11},{19,43},{105,112}}
local combo_first=first+81*interval+100
local finish=combo_first+#combos*100+100
emu.register_frame_done(function()
 frame=frame+1
 if frame>=first and frame<first+81*interval then
  row=math.floor((frame-first)/interval)+1
  local t=(frame-first)%interval
  if t==0 then
   for _,f in ipairs(fields)do f:clear_value()end
   m:load(state)
  end
  if t==8 then fields[row]:set_value(1)end
  if t==10 then host_seen[row]=(m.ioport.ports[keys[row].tag]:read()&keys[row].mask)~=0 end
  if t==12 then fields[row]:clear_value()end
  if keys[row].scan==15 then
   if t==32 then fields[row]:set_value(1)end
   if t==36 then fields[row]:clear_value()end
  end
  if t==65 then dump(row)end
 elseif frame>=combo_first and frame<combo_first+#combos*100 then
  row=0
  local i=math.floor((frame-combo_first)/100)+1
  local t=(frame-combo_first)%100
  if t==0 then m:load(state)end
  if t==8 then by_scan[combos[i][1]]:set_value(1);by_scan[combos[i][2]]:set_value(1)end
  if t==13 then chords[i]=packet[combos[i][1]]and packet[combos[i][2]]end
  if t==18 then by_scan[combos[i][1]]:clear_value();by_scan[combos[i][2]]:clear_value()end
 end
 if frame==finish and tap then
  local found,missing,host_missing,release_missing,matched={},{},{},{},{}
  for i,k in ipairs(keys)do
   if seen[k.scan]then found[#found+1]=k.scan else missing[#missing+1]=k.scan end
   if not host_seen[i]then host_missing[#host_missing+1]=k.scan end
   if not released[i]then release_missing[#release_missing+1]=k.scan end
  end
  for i=1,#combos do if chords[i]then matched[#matched+1]=i end end
  local f=assert(io.open(dest.."/all81.json","w"))
  f:write('{"expected":81,"seen":['..table.concat(found,",")..'],"missing":['..table.concat(missing,",")..'],"host_missing":['..table.concat(host_missing,",")..'],"release_missing":['..table.concat(release_missing,",")..'],"chords":['..table.concat(matched,",")..'],"headers":'..headers..',"releases":'..releases..'}');f:close()
  out:close();m:exit()
  assert(#missing==0 and #host_missing==0 and #release_missing==0 and #matched==5,"Original Palm 81-key campaign incomplete")
 end
end)
