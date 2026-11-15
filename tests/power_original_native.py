#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Passive original-UK1.5 power audit; only external raw inputs are driven."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--case',required=True);p.add_argument('--pg1',type=int,choices=[0,1],required=True);p.add_argument('--installed',action='store_true');a=p.parse_args();assert re.fullmatch('[A-Za-z0-9_-]+',a.case)
 root=Path(__file__).resolve().parents[1];folder=root/'local-evidence/runtime-compare/h5-20261115'/a.case;folder.mkdir(parents=True,exist_ok=False);cfg=folder/'cfg';cfg.mkdir()
 for n in ['asmdana.cfg','default.cfg']:shutil.copy2(root/'config/palm-uk15'/n,cfg/n)
 path=cfg/'asmdana.cfg';s=path.read_text().replace('</input>',f'<port tag=":POWER_ADC_A4" type="CONFIG" mask="4095" defvalue="4095" value="1536"/><port tag=":POWER_ADC_E4" type="CONFIG" mask="4095" defvalue="4095" value="3072"/><port tag=":POWER_PG1" type="CONFIG" mask="2" defvalue="2" value="{a.pg1*2}"/></input>');path.write_text(s)
 rom=root/'runtime/diag/work/uk15_qualify_20261025/UK15_private.raw';before=hashlib.sha256(rom.read_bytes()).hexdigest();assert before=='2f607705738e470d892bfefb9a5dcae1fb3c4195d070c358224e20c93bf365e3'
 lua=r'''local m=manager.machine;local cpu=m.devices[":maincpu"];local b=cpu.spaces.program
local taps={};local buffers={};local last_data=0;local command=0;local adc={};local classes={};local writes={};local charge={};local changed=false;local frames=0
local function field(tag)local p=m.ioport.ports[tag];for _,f in pairs(p.fields)do return f end end
local function buffer(addr)
 if addr<0 or addr>0x3ffff0 or buffers[addr]then return end
 buffers[addr]=true
 taps[#taps+1]=b:install_write_tap(addr,addr+9,"h5_original_battery_buffer",function(ad,d,mask)
  local pc=cpu.state.CURPC.value
  if pc==0x1007b62e or pc==0x1007b634 then classes[#classes+1]=d&255 end
  if pc==0x1007b780 or pc==0x1007b948 or pc==0x1007b754 or pc==0x1007b8e6 then
   writes[#writes+1]=string.format('{"pc":%d,"data":%d,"time":%.9f}',pc,d&65535,m.time:as_double())
  end
 end)
end
taps[#taps+1]=b:install_read_tap(0xfffff430,0xfffff431,"h5_original_pg1",function(ad,d,mask)
 if cpu.state.CURPC.value==0x1007b618 then buffer(cpu.state.A2.value)end
end)
taps[#taps+1]=b:install_write_tap(0xfffff800,0xfffff803,"h5_original_adc_command",function(ad,d,mask)
 if ad==0xfffff800 then last_data=d&65535 end
 if ad==0xfffff802 and(d&0x30f)==0x306 then command=(last_data<<1)&255 end
end)
taps[#taps+1]=b:install_read_tap(0xfffff800,0xfffff801,"h5_original_adc_data",function(ad,d,mask)
 if cpu.state.CURPC.value==0x1007b172 and(command==0xa4 or command==0xe4)and #adc<3000 then
  adc[#adc+1]=string.format('{"command":%d,"raw":%d,"time":%.9f}',command,(d>>3)&4095,m.time:as_double())
 end
end)
taps[#taps+1]=b:install_write_tap(0xfffff438,0xfffff439,"h5_original_charge_output",function(ad,d,mask)
 local pc=cpu.state.CURPC.value
 if pc==0x1007bc4e or pc==0x1007bc6c or pc==0x1007bc72 then
  charge[#charge+1]=string.format('{"pc":%d,"data":%d,"mask":%d,"time":%.9f}',pc,d,mask,m.time:as_double())
 end
end)
emu.register_frame_done(function()
 if not taps[1]then return end;frames=frames+1;local t=m.time:as_double()
 if t>12 and not changed then
  changed=true;field(":POWER_ADC_A4").user_value=2048;field(":POWER_ADC_E4").user_value=4095
 end
 if t>45 then
  local cls={};for _,v in ipairs(classes)do cls[#cls+1]=tostring(v)end
  local f=assert(io.open(RESULT,"w"));f:write(string.format('{"frames":%d,"time":%.9f,"changed_external_inputs":%s,"adc":[%s],"classes":[%s],"battery_writes":[%s],"charge_writes":[%s]}',frames,t,tostring(changed),table.concat(adc,","),table.concat(cls,","),table.concat(writes,","),table.concat(charge,",")));f:close();m:exit()
 end
end)
'''.replace('RESULT',json.dumps(str(folder/'observed.json')));(folder/'observe.lua').write_text(lua)
 binary=root/('runtime/diag/bin/dana-diag'if a.installed else'runtime/diag/source/danadiagd')
 command=[str(binary),'asmdana','-rom',str(rom),'-cfg_directory',str(cfg),'-nvram_directory',str(folder/'nvram'),'-state_directory',str(folder/'states'),'-video','none','-nothrottle','-skip_gameinfo','-nowriteconfig','-autoboot_delay','0','-autoboot_script',str(folder/'observe.lua'),'-log','-oslog']
 env=os.environ.copy();env.update(SDL_VIDEODRIVER='dummy',SDL_AUDIODRIVER='dummy',TMPDIR=str(folder))
 with(folder/'run.out').open('w')as f:r=subprocess.run(command,cwd=root/'runtime/diag',env=env,stdout=f,stderr=subprocess.STDOUT,timeout=160)
 data=json.loads((folder/'observed.json').read_text())if(folder/'observed.json').exists()else{};log=(folder/'run.out').read_text()
 observed_a4={v['raw']for v in data.get('adc',[])if v['command']==0xa4};observed_e4={v['raw']for v in data.get('adc',[])if v['command']==0xe4};raw_writes={v['data']for v in data.get('battery_writes',[])}
 ok=r.returncode==0 and {1536,2048}<=observed_a4 and {3072,4095}<=observed_e4 and (0 if a.pg1 else 4)in data.get('classes',[]) and {1536,2048}<=raw_writes and bool(data.get('charge_writes')) and not any(t in log for t in ['LUA ERROR','Lua error','Error in Lua','DANA_PHYSICAL_BLOCKED'])
 data.update(pg1_level=a.pg1,adc_a4_codes=sorted(observed_a4),adc_e4_codes=sorted(observed_e4),original_battery_raw_values=sorted(raw_writes),returncode=r.returncode,rom_preserved=before==hashlib.sha256(rom.read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),pass_=bool(ok))
 (folder/'result.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps({k:v for k,v in data.items()if k not in ['adc','battery_writes','charge_writes']}),flush=True)
 if not ok:print(log[-2500:]);raise SystemExit(1)
if __name__=='__main__':main()
