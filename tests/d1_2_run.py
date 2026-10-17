#!/usr/bin/env python3
"""Run bounded D1.2 observations on one existing DIAG binary; never build or install."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from d1_2_verify import PIN, verify_suite

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parent

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value,indent=2)+'\n')

def lua(value):
    if isinstance(value,str):return json.dumps(value)
    if isinstance(value,list):return '{'+','.join(lua(x) for x in value)+'}'
    if isinstance(value,dict):return '{'+','.join('['+lua(k)+']='+lua(v) for k,v in value.items())+'}'
    if isinstance(value,int):return str(value)
    raise TypeError(type(value))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('diag',type=Path)
    parser.add_argument('evidence',type=Path,help='New directory outside source checkouts')
    args=parser.parse_args(); root=args.evidence.resolve()
    root.mkdir(parents=True,exist_ok=False)
    fixtures=json.loads((HERE/'d1_2_fixture_manifest.json').read_text())
    source_sha=subprocess.check_output(['git','-C',str(PROJECT),'rev-parse','HEAD'],text=True).strip()
    try:
        binary=args.diag.resolve()
        if not binary.is_file() or not os.access(binary,os.X_OK):
            raise RuntimeError('Executable missing: '+str(binary))
        # Reuse the D1.1 assertions with a single genuine DIAG executable.
        regression=subprocess.run(['bash',str(HERE/'d1_1_diag_smoke.sh'),'verify',
            str(binary),str(root/'d1_1-regression')],
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=300)
        (root/'d1_1-regression.log').write_text(regression.stdout)
        if regression.returncode:
            save(root/'result.json',{'status':'FAIL' if regression.returncode==1 else 'BLOCKED',
                                    'reason':'D1.1 regression did not pass'})
            return 1 if regression.returncode==1 else 2
        for variant in ('diag',):
            for index in range(1,10):
                case_name=f'RAM-{index:02}';name='RAM-01' if index==9 else case_name
                case=fixtures['cases'][name];directory=root/variant/case_name
                directory.mkdir(parents=True)
                code=bytes.fromhex(case['hex'])
                if hashlib.sha256(code).hexdigest()!=case['sha256']:
                    raise RuntimeError('Fixture hash mismatch')
                (directory/'fixture.bin').write_bytes(code)
                (directory/'fixture.s').write_text('\n'.join(i['source'] for i in case['instructions'])+'\n')
                (directory/'fixture.dis').write_text('\n'.join(f"{i['pc']:08x} {i['hex']} {i['disassembly']}" for i in case['instructions'])+'\n')
                plugin=directory/'plugin';plugin.mkdir()
                shutil.copyfile(HERE/'d1_2_boot.lua',plugin/'boot.lua')
                pcs=[i['pc'] for i in case['instructions']]
                if index in (6,7):pcs=pcs[:2]+[0x5000]
                config={'case':name,'variant':variant,'run':2 if index==9 else 1,
                        'hex':case['hex'],'fixture_sha256':case['sha256'],
                        'binary_sha256':digest(binary),'source_sha':source_sha,
                        'breakpoints':pcs,'endpoint':case['endpoint'],'output':str(directory)}
                config_path=directory/'config.lua';config_path.write_text('return '+lua(config)+'\n')
                environment=dict(os.environ);environment['DANA_D1_2_CONFIG']=str(config_path)
                command=[str(binary),'asmdana','-noreadconfig','-debug','-debugger','none',
                         '-pluginspath',str(plugin),'-plugins','-video','none','-sound','none',
                         '-nothrottle','-skip_gameinfo','-seconds_to_run','1']
                run={'mame_commit':PIN,'source_sha':source_sha,'binary_sha256':config['binary_sha256'],
                     'driver_sha256':digest(PROJECT/'src/mame/skeleton/alphasdana.cpp'),
                     'boot_sha256':digest(HERE/'d1_2_boot.lua'),
                     'fixture_manifest_sha256':digest(HERE/'d1_2_fixture_manifest.json'),
                     'command':command,'host_timeout_seconds':180,'virtual_cycles':20000,'instruction_budget':32}
                try:
                    with (directory/'console.log').open('wb') as console:
                        process=subprocess.run(command,cwd=directory,env=environment,
                                               stdout=console,stderr=subprocess.STDOUT,timeout=180)
                    run['exit_code']=process.returncode
                except subprocess.TimeoutExpired:
                    run.update(exit_code=None,reason='HOST_TIMEOUT')
                save(directory/'run.json',run)
                # Do not proceed after failed bootstrap or infrastructure failure.
                from d1_2_verify import check_run
                check=check_run(directory,name,variant,config['run'])
                save(directory/'verification.json',check)
                if check['status']!='PASS':
                    incomplete=verify_suite(root)
                    incomplete['first_issue']={'case':case_name,'variant':variant,'reason':check.get('reason')}
                    save(root/'result.json',incomplete)
                    return 1 if check['status']=='FAIL' else 2
        result=verify_suite(root);save(root/'result.json',result)
        return {'PASS':0,'FAIL':1,'BLOCKED':2}[result['status']]
    except (OSError,RuntimeError,subprocess.SubprocessError,ValueError) as error:
        save(root/'result.json',{'status':'BLOCKED','reason':str(error)})
        print('BLOCKED:',error)
        return 2

if __name__=='__main__':
    sys.exit(main())
