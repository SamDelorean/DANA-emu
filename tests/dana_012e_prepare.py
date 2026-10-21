#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Read-only prerequisites and new forensic copies. Never writes source inputs."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tarfile

HISTORICAL_SOURCE='56a0a0040edfc161e45c1131692a64c3649fe3af'
HISTORICAL_DRIVER_SHA='6bff19e0ae1e6c7a1f99a86fcfa2fbe235ac096c6624a10f6600fbd8851ddcf0'
BUILD_SOURCE='581601b49acb6603af2a100817d0f06fed17ed96'
DRIVER='src/mame/skeleton/alphasdana.cpp'
DRIVER_SHA='e8211be78dfb2bf4cdc0ccabd444c97d715dc37d189d4f113f2f1cbf05b573e2'
INDEX='evidence_sha256.json'
INDEX_SHA='c804cbc536215a5eed3db6cf3025f64dde2ddbfce10dff5eddab3021d7ab40dd'
ARCHIVE_SHA='1fc1d8417eea975c80f29a74aa53e6ccc8fd835b2d2cc924951afec748364a18'
SUBSET_MEMBERS=frozenset(('binary_qualification.json','source-manifest.json','job_result.json',
    'native-pfsel.log','pfsel/result.json','pfsel/reset/result.json','pfsel/save_restore/result.json'))
DISPUTED_ACTUAL='56f40dfb00b27a33fe4fdf797cdb5c16e1c1910d8c0e441302bc19c8c6156e6a'
DISPUTED_EXPECTED='6be10c77aa5b9c0c5b3ee4844568ffd071a158640e16bfe04c76e9ecdb0a626e'
RAM_MEMBERS=('pfsel/reset/final.ram','pfsel/save_restore/final.ram','pfsel/save_restore/restored.ram')


def digest(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def metadata(path):
    """Stable lstat facts; exclude atime because evidence reads may update it."""
    s=Path(path).lstat()
    return dict(device=s.st_dev,inode=s.st_ino,bytes=s.st_size,mode=s.st_mode,
        links=s.st_nlink,uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns,ctime_ns=s.st_ctime_ns)


def preserve_selection(root,destination,audited,max_files=256,max_bytes=128*1024*1024):
    """Preserve the selected bytes, even when invalid, into a NEW bounded tar.

    This is evidence retention, never a replacement source for integrity tests.
    Symlink targets and special files are never read. Partial copies stay labelled.
    """
    root=Path(root).absolute();destination=Path(destination).absolute()
    result=dict(status='BLOCKED',selected_root=str(root),resolved_root=str(root.resolve()),
        archive=str(destination),files=[],errors=[],max_files=max_files,max_bytes=max_bytes,
        input_writes=0,test_selection_replaced=False)
    created=False
    try:
        if destination.resolve().is_relative_to(root.resolve()):raise ValueError('FORENSICS_OUTPUT_INSIDE_INPUT')
        if root.is_symlink() or not root.is_dir():raise ValueError('FORENSICS_ROOT_NOT_REGULAR_DIRECTORY')
        result['root_before']=metadata(root)
        paths=sorted(root.rglob('*'))
        if len(paths)>max_files:raise ValueError('FORENSICS_FILE_COUNT_BOUND')
        sizes=sum(p.lstat().st_size for p in paths if stat.S_ISREG(p.lstat().st_mode))
        if sizes>max_bytes:raise ValueError('FORENSICS_BYTE_BOUND')
        known={r['relative_path']:r for r in audited.get('files',[])}
        class Reader:
            def __init__(self,stream):self.stream=stream;self.hash=hashlib.sha256()
            def read(self,size):
                data=self.stream.read(size);self.hash.update(data);return data
        # Exclusive creation; no overwrite, extraction, cleanup or input chmod.
        with destination.open('xb') as output,tarfile.open(fileobj=output,mode='w') as archive:
            created=True
            for path in paths:
                name=str(path.relative_to(root));before=metadata(path)
                row=dict(relative_path=name,selected_path=str(path),resolved_path=str(path.resolve()),
                    origin='ACTUAL_SELECTED_DIRECTORY_BEFORE_OR_AFTER_TESTS',before=before,
                    index_path=audited.get('index'),index_sha256=audited.get('actual_index_sha256'),
                    expected_sha256=known.get(name,{}).get('expected_sha256'),
                    audited_sha256=known.get(name,{}).get('actual_sha256'))
                result['files'].append(row)
                item=tarfile.TarInfo('selection/'+name);item.uid=before['uid'];item.gid=before['gid']
                item.mode=stat.S_IMODE(before['mode']);item.mtime=before['mtime_ns']/1000000000
                if stat.S_ISREG(before['mode']):
                    # Reject replacement of the leaf with a symlink between lstat/open.
                    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
                    with os.fdopen(fd,'rb') as stream:
                        opened=os.fstat(stream.fileno())
                        if (opened.st_dev,opened.st_ino)!=(before['device'],before['inode']):raise ValueError('FORENSICS_OPEN_RACE:'+name)
                        item.size=before['bytes'];reader=Reader(stream);archive.addfile(item,reader)
                        row['captured_sha256']=reader.hash.hexdigest()
                    if row['audited_sha256'] and row['captured_sha256']!=row['audited_sha256']:
                        result['errors'].append('CHANGED_SINCE_AUDIT:'+name)
                elif stat.S_ISDIR(before['mode']):item.type=tarfile.DIRTYPE;archive.addfile(item)
                elif stat.S_ISLNK(before['mode']):
                    item.type=tarfile.SYMTYPE;item.linkname=os.readlink(path);row['link_target']=item.linkname
                    archive.addfile(item)
                else:raise ValueError('FORENSICS_SPECIAL_FILE:'+name)
                row['after']=metadata(path)
                if row['after']!=before:result['errors'].append('CHANGED_DURING_CAPTURE:'+name)
        result['root_after']=metadata(root)
        if result['root_after']!=result['root_before']:result['errors'].append('DIRECTORY_CHANGED_DURING_CAPTURE')
        if not result['errors']:result['status']='PRESERVED'
    except (OSError,ValueError,tarfile.TarError) as exc:result['errors'].append(str(exc))
    if created and destination.is_file():
        result.update(archive_sha256=digest(destination),archive_bytes=destination.stat().st_size)
    return result


def unique_object(pairs):
    result={}
    for name,value in pairs:
        if name in result:raise ValueError('DUPLICATE_JSON_KEY:'+name)
        result[name]=value
    return result


def read_index(content):
    if hashlib.sha256(content).hexdigest()!=INDEX_SHA:raise ValueError('ORIGINAL_INDEX_SHA256')
    index=json.loads(content,object_pairs_hook=unique_object)
    if not isinstance(index,dict) or len(index)!=40:raise ValueError('ORIGINAL_INDEX_INVENTORY')
    for name,value in index.items():
        path=PurePosixPath(name)
        if (path.is_absolute() or str(path)!=name or '..' in path.parts or '\\' in name
                or name==INDEX or not re.fullmatch('[0-9a-f]{64}',value)):
            raise ValueError('UNSAFE_INDEX_ENTRY:'+name)
    return index


def source_report(project):
    project=Path(project).absolute();report=dict(status='BLOCKED',project=str(project),resolved_project=str(project.resolve()),pins=[],errors=[])
    def git(*args):return subprocess.check_output(['git','-C',str(project),*args],stderr=subprocess.PIPE).decode().strip()
    for pin,wanted in ((HISTORICAL_SOURCE,HISTORICAL_DRIVER_SHA),(BUILD_SOURCE,DRIVER_SHA)):
        row=dict(commit=pin,driver=DRIVER,expected_sha256=wanted,status='BLOCKED')
        try:
            if git('rev-parse','--verify',pin+'^{commit}')!=pin:raise ValueError('WRONG_COMMIT')
            content=subprocess.check_output(['git','-C',str(project),'show',pin+':'+DRIVER],stderr=subprocess.PIPE)
            row['actual_sha256']=hashlib.sha256(content).hexdigest()
            if row['actual_sha256']!=wanted:raise ValueError('PINNED_DRIVER_SHA256')
            row['status']='PASS'
        except (OSError,ValueError,subprocess.SubprocessError) as exc:
            row['reason']=str(exc);report['errors'].append('PIN_UNAVAILABLE_OR_CHANGED:'+pin)
        report['pins'].append(row)
    try:
        report['HEAD']=git('rev-parse','HEAD');report['driver_sha256']=digest(project/DRIVER)
        if report['driver_sha256']!=DRIVER_SHA:raise ValueError('CURRENT_DRIVER_SHA256')
        if git('diff','--name-only',BUILD_SOURCE,'HEAD','--','src','overlays') or git('diff','--name-only','HEAD','--','src','overlays'):
            raise ValueError('PRODUCTION_OR_OVERLAYS_CHANGED')
    except (OSError,ValueError,subprocess.SubprocessError) as exc:report['errors'].append(str(exc))
    if not report['errors']:report['status']='PASS'
    return report


def audit_directory(root,scope='full'):
    """Verify the actual test selection, not another directory with a good index."""
    root=Path(root).absolute()
    report=dict(status='BLOCKED',scope=scope,selection='EXPLICIT_DANA_012C_EVIDENCE_DIR',
        selected_root=str(root),resolved_root=str(root.resolve()),index=str(root/INDEX),
        index_relative_path=INDEX,origin='EXPLICIT_DANA_012C_EVIDENCE_DIR',expected_index_sha256=INDEX_SHA,files=[],errors=[])
    report['process_context']=dict(cwd=os.getcwd(),environment_DANA_012C_EVIDENCE_DIR=os.getenv('DANA_012C_EVIDENCE_DIR'))
    try:
        if scope not in ('full','provided-subset'):raise ValueError('EXPLICIT_EVIDENCE_SCOPE_REQUIRED')
        if root.is_symlink() or not root.is_dir():raise ValueError('EVIDENCE_ROOT_NOT_REGULAR_DIRECTORY')
        report['root_metadata']=metadata(root)
        paths=list(root.rglob('*'))
        if any(p.is_symlink() or not (p.is_file() or p.is_dir()) for p in paths):raise ValueError('SYMLINK_OR_SPECIAL_EVIDENCE')
        report['actual_index_sha256']=digest(root/INDEX)
        index=read_index((root/INDEX).read_bytes());report['indexed_members']=len(index)
        present={str(p.relative_to(root)) for p in paths if p.is_file()}-{INDEX}
        required=set(index) if scope=='full' else set(SUBSET_MEMBERS)
        if present!=required:report['errors'].append('SELECTION_INVENTORY')
        report['missing_required']=sorted(required-present);report['unexpected']=sorted(present-required)
        report['absent_indexed_members']=sorted(set(index)-present)
        report['disputed_expected_candidates']=[n for n,h in index.items() if h==DISPUTED_EXPECTED]
        for name in sorted(present):
            path=root/name;actual=digest(path);expected=index.get(name)
            row=dict(relative_path=name,selected_path=str(path),resolved_path=str(path.resolve()),
                index=str(root/INDEX),index_sha256=report['actual_index_sha256'],
                expected_sha256=expected,actual_sha256=actual,bytes=path.stat().st_size,
                filesystem=metadata(path),
                origin='EXPLICIT_SELECTED_DIRECTORY',expected_origin='PINNED_ORIGINAL_012C_INDEX',
                status='PASS' if actual==expected else 'BLOCKED')
            report['files'].append(row)
            if actual!=expected:report['errors'].append('EVIDENCE_SHA256:'+name)
        if not report['errors']:report['status']='PASS'
    except (OSError,ValueError,TypeError) as exc:report['errors'].append(str(exc))
    byname={e['relative_path']:e for e in report['files']}
    report['disputed_ram']=[]
    for name in RAM_MEMBERS:
        path=root/name
        row=byname.get(name,dict(relative_path=name,selected_path=str(path),resolved_path=str(path.resolve()),
            index=str(root/INDEX),expected_index_sha256=INDEX_SHA,expected_sha256=DISPUTED_EXPECTED,
            actual_sha256=None,origin='EXPLICIT_SELECTED_DIRECTORY',expected_origin='PINNED_ORIGINAL_012C_INDEX',
            status='BLOCKED',reason='NOT_HASHED_OR_UNAVAILABLE; NO_PATH_ATTRIBUTION'))
        # Still diagnose the three known paths if the selected index is wrong;
        # expected identity comes from the pinned original catalog, never that index.
        if row['actual_sha256'] is None:
            safe=not root.is_symlink() and all(not (root/Path(*PurePosixPath(name).parts[:i])).is_symlink()
                for i in range(1,len(PurePosixPath(name).parts)+1))
            try:
                if safe and path.is_file():row.update(actual_sha256=digest(path),bytes=path.stat().st_size,reason='SELECTION_NOT_VERIFIED')
            except OSError as exc:row['reason']=str(exc)
        row['selection_index_verified']=report.get('actual_index_sha256')==INDEX_SHA
        report['disputed_ram'].append(row)
    return report


def audit_archive(path):
    """Audit exact original bytes; no extraction, fallback selection or repair."""
    path=Path(path).absolute();report=dict(status='BLOCKED',path=str(path),origin='EXPLICIT_ORIGINAL_012C_ARCHIVE',expected_sha256=ARCHIVE_SHA,errors=[])
    try:
        if path.is_symlink() or not path.is_file():raise ValueError('ARCHIVE_NOT_REGULAR_FILE')
        report['actual_sha256']=digest(path)
        if report['actual_sha256']!=ARCHIVE_SHA:raise ValueError('ORIGINAL_ARCHIVE_SHA256')
        with tarfile.open(path,'r:gz') as archive:
            members=[m for m in archive.getmembers() if not m.isdir()]
            if len(members)>256 or sum(m.size for m in members)>128*1024*1024:raise ValueError('ARCHIVE_BUDGET')
            if any(not m.isfile() or not m.name.startswith('evidence/') or '..' in PurePosixPath(m.name).parts
                   or str(PurePosixPath(m.name))!=m.name or '\\' in m.name for m in members):raise ValueError('ARCHIVE_MEMBER')
            if len({m.name for m in members})!=len(members):raise ValueError('DUPLICATE_ARCHIVE_MEMBER')
            content={m.name[9:]:archive.extractfile(m).read() for m in members}
        index=read_index(content[INDEX]);report['index_sha256']=hashlib.sha256(content[INDEX]).hexdigest()
        if set(index)!=set(content)-{INDEX}:raise ValueError('ARCHIVE_INVENTORY')
        report['files']=[]
        for name,expected in sorted(index.items()):
            actual=hashlib.sha256(content[name]).hexdigest()
            report['files'].append(dict(member='evidence/'+name,relative_path=name,
                expected_sha256=expected,actual_sha256=actual,origin='PINNED_ORIGINAL_012C_ARCHIVE',
                archive_path=str(path),archive_sha256=report['actual_sha256'],index_sha256=report['index_sha256']))
            if actual!=expected:report['errors'].append('ARCHIVE_MEMBER_SHA256:'+name)
        if not report['errors']:report.update(status='PASS',verified_members=len(index))
    except (OSError,ValueError,TypeError,KeyError,tarfile.TarError) as exc:report['errors'].append(str(exc))
    return report


def preflight(project,evidence,scope='full',archive=None):
    sources=source_report(project);selected=audit_directory(evidence,scope)
    result=dict(status='PASS',source=sources,selected_evidence=selected,archive=None,repairs=0,index_writes=0)
    if archive is not None:result['archive']=audit_archive(archive)
    if scope=='full' and archive is None:
        result['archive']=dict(status='BLOCKED',errors=['ORIGINAL_ARCHIVE_REQUIRED_FOR_FULL_PREPARATION'])
    if any(row and row['status']!='PASS' for row in (sources,selected,result['archive'])):result['status']='BLOCKED'
    archived={e['member'][9:]:e for e in (result['archive'] or {}).get('files',[])}
    result['ram_comparison']=[]
    for row in selected['disputed_ram']:
        member=archived.get(row['relative_path']);actual=row['actual_sha256']
        archive_actual=member['actual_sha256'] if member else None
        if not row['selection_index_verified']:assessment='SELECTION_INDEX_NOT_VERIFIED; WRONG_DIRECTORY_OR_INDEX_UNRESOLVED'
        elif actual is None:assessment='BLOCKED_SELECTED_BYTES_UNAVAILABLE'
        elif actual!=row['expected_sha256']:
            assessment=('SELECTED_COPY_DIVERGES_FROM_AUTHENTIC_ARCHIVE; ALTERATION_OR_WRONG_SELECTION_UNRESOLVED'
                if (result['archive'] or {}).get('status')=='PASS' else 'SELECTED_INTEGRITY_FAILURE; ORIGINAL_ARCHIVE_NOT_VERIFIED')
        else:assessment='SELECTED_BYTES_MATCH_ORIGINAL_INDEX'
        if member and archive_actual!=member['expected_sha256']:assessment='ARCHIVE_MEMBER_INDEX_INCONSISTENCY; KEEP_BLOCKED'
        result['ram_comparison'].append(dict(row,archive_path=str(Path(archive).absolute()) if archive else None,
            archive_member='evidence/'+row['relative_path'],archive_actual_sha256=archive_actual,
            archive_status=(result['archive'] or {}).get('status','UNAVAILABLE'),assessment=assessment))
    result['reported_discrepancy']=dict(reported_actual_sha256=DISPUTED_ACTUAL,expected_sha256=DISPUTED_EXPECTED,
        attribution='REQUIRES_ACTUAL_SELECTED_FILE; HASH_ALONE_DOES_NOT_IDENTIFY_A_PATH',candidate_keys=list(RAM_MEMBERS))
    result['scope_note']='ALL_40_INDEXED_FILES_AND_ORIGINAL_ARCHIVE' if scope=='full' else 'ONLY_7_SUPPLIED_FILES; 33_NATIVE_FILES_UNAVAILABLE; NOT_FULL_ARCHIVE_QUALIFICATION'
    return result
