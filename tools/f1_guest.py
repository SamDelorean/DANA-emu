#!/usr/bin/env python3
"""Build/validate the pinned original EmuTOS-Dana and emit a native RAM package."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys

PIN='9c42ef0f2c2fa9d1e217fced9da68901b2326e8b'
HEADER=struct.Struct('>8s8I20sI')
REQUIRED=('__text','_os_header','_main','_stktop','__low_stram_end','__bss','__ebss')
QUALIFIED_ARTIFACTS={
    'emutos.img':(223748,'ba590da2661bc582c19bb24d65db04667daf37a17d7aa51fb462b945933ba0a3'),
    'emutos-dana.rom':(223792,'efb055e5ac02526db069aec23c4b71b092fc48317aa4305e93a4a2f4e369243c'),
    'emutos.map':(124540,'17cc980e675e2e1b50e713b9029f6fc3e51d3e55392deb99d53552d4b3af3e68'),
    'emutos.dana':(223812,'c201c8527df87fa6a8788d8ac59f43298666196fefeee12dcac68295cb281b9d'),
}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def symbols(text):
    result={}
    for name in REQUIRED:
        found=re.findall(r'^\s*(0x[0-9a-fA-F]+)\s+'+re.escape(name)+r'(?:\s|$)',text,re.M)
        if len(set(found))!=1:
            raise ValueError('Missing/ambiguous map symbol '+name)
        result[name]=int(found[0],16)
    for name in ('_realmain','meminit','_biosmain','_dana_init'):
        found=re.findall(r'^\s*(0x[0-9a-fA-F]+)\s+'+re.escape(name)+r'(?:\s|$)',text,re.M)
        if len(set(found))==1:result[name]=int(found[0],16)
    return result

def startup(syms,image):
    # _realmain is a local assembly label and need not appear in a GNU map.
    # Resolve the exact unconditional startup branches from the built bytes.
    base=syms['__text'];main=syms['_main'];offset=main-base
    if len(image)<4 or image[0]!=0x60 or image[1] in (0,255):
        raise ValueError('Expected pinned OS header BRA.s')
    target=base+2+int.from_bytes(image[1:2],'big',signed=True)
    if target!=main or offset<0 or offset+4>len(image) or image[offset:offset+2]!=b'\x60\x00':
        raise ValueError('Header/_main branch differs from generated map')
    realmain=main+2+int.from_bytes(image[offset+2:offset+4],'big',signed=True)
    if not base<=realmain<base+len(image):raise ValueError('Startup branch leaves image')
    if '_realmain' in syms and syms['_realmain']!=realmain:raise ValueError('Local startup symbol mismatch')
    syms['_realmain']=realmain
    return syms

def package(directory, source_sha=None, compiler=None):
    directory=Path(directory)
    if source_sha is None:
        provenance=json.loads((directory/'build_provenance.json').read_text())
        if provenance.get('exit_code')!=0 or 'dana' not in provenance.get('command',[]):
            raise ValueError('Successful original dana build provenance required')
        source_sha=provenance.get('source_commit');compiler=provenance.get('compiler')
    if source_sha!=PIN:raise ValueError('Wrong EmuTOS source revision')
    paths={name:directory/name for name in ('emutos.img','emutos-dana.rom','emutos.map')}
    syms=symbols(paths['emutos.map'].read_text())
    image=paths['emutos.img'].read_bytes();rom=paths['emutos-dana.rom'].read_bytes()
    syms=startup(syms,image)
    base=syms['__text'];entry=syms['_os_header'];stack=syms['_stktop'];low=syms['__low_stram_end']
    bss,ebss=syms['__bss'],syms['__ebss']
    if not (base==entry==0x2140 and 0<len(image)<=0x400000-base and len(image)%2==0):
        raise ValueError('Image length/base/entry differs from pinned R-direct contract')
    if not (0x800<=stack<=low<=base and stack%2==0 and base+len(image)<=bss<=ebss<=0x400000):
        raise ValueError('Guest layout overlaps stack/low RAM/BSS or exceeds RAM')
    if not all(base<=syms[name]<base+len(image) for name in ('_main','_realmain')):
        raise ValueError('Guest startup symbols outside image')
    # Historical first-stage copy must include the *exact* linked image once.
    offset=rom.find(image)
    if offset<0 or rom.find(image,offset+1)>=0:raise ValueError('First-stage ROM/image mismatch')
    if image[0]&0xf0!=0x60:raise ValueError('OS header does not start with a branch')
    header=HEADER.pack(b'DANARAM1',entry,base,len(image),stack,0x400000,low,bss,ebss,
                       hashlib.sha1(image).digest(),1)
    data=header+image
    manifest={'schema':'dana-f1-guest-v1','source_commit':source_sha,'target':'dana',
        'compiler':compiler,'symbols':syms,'ram_bytes':0x400000,'embedded_image_offset':offset,
        'profile':{'name':'R-direct','sr':0x2700,'phystop':0x400000,'warm_magic':0},
        'artifacts':{name:{'size':path.stat().st_size,'sha256':sha(path)} for name,path in paths.items()},
        'package':{'size':len(data),'sha256':hashlib.sha256(data).hexdigest()},
        'historical_booter_256k_compatible':len(image)%4==0 and len(image)<=262144}
    (directory/'emutos.dana').write_bytes(data)
    (directory/'guest_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest

def validate(directory):
    directory=Path(directory);manifest=json.loads((directory/'guest_manifest.json').read_text())
    if manifest['source_commit']!=PIN:raise ValueError('Wrong source provenance')
    for name,record in manifest['artifacts'].items():
        if name not in ('emutos.img','emutos-dana.rom','emutos.map'):raise ValueError('Unknown artifact')
        path=directory/name
        if path.stat().st_size!=record['size'] or sha(path)!=record['sha256']:
            raise ValueError('Artifact integrity mismatch: '+name)
    data=(directory/'emutos.dana').read_bytes()
    if len(data)!=manifest['package']['size'] or hashlib.sha256(data).hexdigest()!=manifest['package']['sha256']:
        raise ValueError('RAM package integrity mismatch')
    syms=startup(symbols((directory/'emutos.map').read_text()),(directory/'emutos.img').read_bytes())
    if syms!=manifest['symbols']:raise ValueError('Map binding mismatch')
    fields=HEADER.unpack(data[:64]);image=(directory/'emutos.img').read_bytes()
    expected=HEADER.pack(b'DANARAM1',syms['_os_header'],syms['__text'],len(image),syms['_stktop'],
                         0x400000,syms['__low_stram_end'],syms['__bss'],syms['__ebss'],hashlib.sha1(image).digest(),1)
    if data[:64]!=expected or data[64:]!=image:raise ValueError('Native loader envelope mismatch')
    if not (fields[1]==fields[2]==0x2140 and 0<len(image)<=0x400000-0x2140 and len(image)%2==0
            and 0x800<=syms['_stktop']<=syms['__low_stram_end']<=0x2140
            and 0x2140+len(image)<=syms['__bss']<=syms['__ebss']<=0x400000):
        raise ValueError('Invalid RAM package layout')
    return manifest

def validate_qualified(directory):
    """Read-only E4 input gate. Never package, repair or rebuild an input."""
    directory=Path(directory)
    for name,(size,digest) in QUALIFIED_ARTIFACTS.items():
        p=directory/name
        if not p.is_file() or p.is_symlink() or p.stat().st_size!=size or sha(p)!=digest:
            raise ValueError('Qualified E1/E2 artifact mismatch: '+name)
    manifest=validate(directory)
    if set(manifest['artifacts'])!=set(QUALIFIED_ARTIFACTS)-{'emutos.dana'}:
        raise ValueError('Incomplete original artifact manifest')
    provenance=json.loads((directory/'build_provenance.json').read_text())
    if (provenance.get('source_commit')!=PIN or provenance.get('exit_code')!=0
            or not isinstance(provenance.get('command'),list)
            or 'dana' not in provenance['command'] or not provenance.get('compiler')
            or manifest.get('target')!='dana' or manifest.get('compiler')!=provenance['compiler']):
        raise ValueError('Original successful Dana build provenance required')
    return manifest

def build(source,output,prefix):
    source=Path(source).resolve();output=Path(output).resolve()
    if output.exists():raise ValueError('Build output must be new')
    if subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()!=PIN:
        raise ValueError('Guest checkout is not pinned source')
    # Always archive into a private fresh area; do not clean a reference checkout.
    output.mkdir(parents=True);stage=output/'source';stage.mkdir()
    archive=subprocess.Popen(['git','-C',str(source),'archive',PIN],stdout=subprocess.PIPE)
    unpack=subprocess.run(['tar','-x','-C',str(stage)],stdin=archive.stdout)
    archive.stdout.close()
    if archive.wait() or unpack.returncode:raise RuntimeError('Guest source extraction failed')
    compiler=shutil.which(prefix+'gcc')
    if not compiler:raise RuntimeError('BLOCKED_TOOLCHAIN: '+prefix+'gcc unavailable')
    version=subprocess.check_output([compiler,'--version'],text=True).splitlines()[0]
    multilib=subprocess.check_output([compiler,'-print-multi-lib'],text=True)
    # mshort changes the ABI; a Linux libgcc without matching multilib is not a
    # suitable substitute for the real MiNT/bare-metal toolchain.
    if 'mshort' not in multilib:raise RuntimeError('BLOCKED_TOOLCHAIN_ABI: no mshort runtime multilib')
    command=['make','-j3','dana','TOOLCHAIN_PREFIX='+prefix]
    if 'elf' in prefix:command+=['ELF=1']
    with (output/'build.log').open('wb') as log:
        result=subprocess.run(command,cwd=stage,stdout=log,stderr=subprocess.STDOUT)
    (output/'build_provenance.json').write_text(json.dumps({'source_commit':PIN,'command':command,
            'compiler':version,'multilib':multilib,'exit_code':result.returncode},indent=2)+'\n')
    if result.returncode:raise RuntimeError('BLOCKED_GUEST_BUILD: see build.log')
    for name in ('emutos.img','emutos-dana.rom','emutos.map'):shutil.copy2(stage/name,output/name)
    return package(output)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='mode',required=True)
    b=sub.add_parser('build');b.add_argument('source',type=Path);b.add_argument('output',type=Path)
    b.add_argument('--prefix',default='m68k-atari-mint-')
    for name in ('package','validate'):
        p=sub.add_parser(name);p.add_argument('directory',type=Path)
    args=parser.parse_args()
    try:
        result=build(args.source,args.output,args.prefix) if args.mode=='build' else package(args.directory) if args.mode=='package' else validate(args.directory)
        print(json.dumps({'status':'PASS_INPUT_VALIDATION','manifest':result},indent=2))
    except (OSError,ValueError,RuntimeError,subprocess.SubprocessError) as error:
        print(json.dumps({'status':'BLOCKED','domain':'INPUT_OR_TOOLCHAIN','reason':str(error)}));sys.exit(2)
