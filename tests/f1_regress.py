#!/usr/bin/env python3
"""Only the impacted, already-qualified RAM-01/RAM-08 cases on existing DIAG."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from d1_2_run import lua,digest,save
from d1_2_verify import check_run,PIN
HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('diag',type=Path);p.add_argument('evidence',type=Path)
    args=p.parse_args();root=args.evidence.resolve();root.mkdir(parents=True,exist_ok=False)
    results={}
    try:
        binary=args.diag.resolve()
        if not binary.is_file():raise RuntimeError('Missing DIAG executable')
        fixtures=json.loads((HERE/'d1_2_fixture_manifest.json').read_text())
        source=subprocess.check_output(['git','-C',str(HERE.parent),'rev-parse','HEAD'],text=True).strip()
        for name in ('RAM-01','RAM-08'):
            case=fixtures['cases'][name];directory=root/name;directory.mkdir()
            if hashlib.sha256(bytes.fromhex(case['hex'])).hexdigest()!=case['sha256']:
                raise RuntimeError('Fixture identity mismatch')
            plugin=directory/'plugin';plugin.mkdir();shutil.copyfile(HERE/'d1_2_boot.lua',plugin/'boot.lua')
            cfg={'case':name,'variant':'diag','run':1,'hex':case['hex'],'fixture_sha256':case['sha256'],
                 'binary_sha256':digest(binary),'source_sha':source,'output':str(directory),
                 'breakpoints':[i['pc'] for i in case['instructions']],'endpoint':case['endpoint']}
            path=directory/'config.lua';path.write_text('return '+lua(cfg)+'\n')
            cmd=[str(binary),'asmdana','-noreadconfig','-debug','-debugger','none',
                 '-pluginspath',str(plugin),'-plugins','-video','none','-sound','none',
                 '-nothrottle','-skip_gameinfo','-seconds_to_run','1']
            record={'mame_commit':PIN,'binary_sha256':cfg['binary_sha256'],'source_sha':source,'command':cmd}
            try:
                with (directory/'console.log').open('wb') as f:
                    proc=subprocess.run(cmd,cwd=directory,env=dict(os.environ,DANA_D1_2_CONFIG=str(path)),
                                        stdout=f,stderr=subprocess.STDOUT,timeout=180)
                record['exit_code']=proc.returncode
            except subprocess.TimeoutExpired:record.update(exit_code=None,reason='HOST_TIMEOUT')
            save(directory/'run.json',record);results[name]=check_run(directory,name,'diag',1)
        statuses=[r['status'] for r in results.values()]
        status='FAIL' if 'FAIL' in statuses else 'BLOCKED' if 'BLOCKED' in statuses else 'PASS'
        result={'status':status,'cases':results}
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        result={'status':'BLOCKED','reason':str(error),'cases':results}
    save(root/'result.json',result);print(result['status']);return {'PASS':0,'FAIL':1,'BLOCKED':2}[result['status']]
if __name__=='__main__':sys.exit(main())
