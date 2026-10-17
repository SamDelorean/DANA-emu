#!/usr/bin/env python3
"""Fetch verified-source CrossMiNT archives into isolated storage; do not install systemwide."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import urllib.request

URLS = {
    'gcc': 'https://tho-otto.m68k.eu/download/mint/gcc-4.6.4-mint-bin-linux64.tar.xz',
    'binutils': 'https://tho-otto.m68k.eu/download/mint/binutils-2.30-mint-bin-linux64.tar.xz',
}
MAX_ARCHIVE = 150 * 1024 * 1024
MAX_EXPANDED = 800 * 1024 * 1024


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as inp:
        for block in iter(lambda: inp.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def acquire(label, source_path, directory):
    if source_path is not None:
        path = Path(source_path).resolve()
        if not path.is_file():
            raise RuntimeError(f'BLOCKED_ARCHIVE_MISSING: {path}')
    else:
        path = directory / URLS[label].rsplit('/', 1)[1]
        if not path.exists():
            with urllib.request.urlopen(URLS[label], timeout=90) as response:
                with path.open('xb') as output:
                    copied = 0
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        copied += len(chunk)
                        if copied > MAX_ARCHIVE:
                            raise RuntimeError('BLOCKED_ARCHIVE_TOO_LARGE: ' + label)
                        output.write(chunk)
    if path.stat().st_size > MAX_ARCHIVE:
        raise RuntimeError('BLOCKED_ARCHIVE_TOO_LARGE: ' + label)
    return path


def verify_members(archive, dest):
    """Reject paths, symlink targets and special files escaping isolated staging."""
    root = dest.resolve()
    expanded = 0
    with tarfile.open(archive, 'r:xz') as tar:
        for member in tar:
            name = PurePosixPath(member.name)
            if (name.is_absolute() or not name.parts or '..' in name.parts or
                    not (member.isfile() or member.isdir() or member.issym() or member.islnk())):
                raise RuntimeError('BLOCKED_UNSAFE_ARCHIVE_MEMBER: ' + member.name)
            target = (root / member.name).resolve(strict=False)
            if not target.is_relative_to(root):
                raise RuntimeError('BLOCKED_ARCHIVE_PATH_ESCAPE: ' + member.name)
            if member.issym() or member.islnk():
                base = target.parent if member.issym() else root
                link = (base / member.linkname).resolve(strict=False)
                if not link.is_relative_to(root):
                    raise RuntimeError('BLOCKED_ARCHIVE_LINK_ESCAPE: ' + member.name)
            expanded += member.size
            if expanded > MAX_EXPANDED:
                raise RuntimeError('BLOCKED_ARCHIVE_EXPANSION_LIMIT')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--gcc-archive', type=Path)
    parser.add_argument('--binutils-archive', type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists():
        raise SystemExit('BLOCKED_OUTPUT_EXISTS: ' + str(out))
    out.mkdir(parents=True)
    record = {'status': 'BLOCKED', 'sources': URLS, 'archives': {}}
    try:
        for label, supplied in [('gcc', args.gcc_archive), ('binutils', args.binutils_archive)]:
            archive = acquire(label, supplied, out)
            record['archives'][label] = {'path': str(archive), 'bytes': archive.stat().st_size,
                                         'sha256': sha256(archive), 'source': 'provided' if supplied else URLS[label]}
            verify_members(archive, out / 'unpacked')
        target = out / 'unpacked'
        target.mkdir()
        # Checked first: archive entries cannot escape this directory.
        for label, supplied in [('gcc', args.gcc_archive), ('binutils', args.binutils_archive)]:
            with tarfile.open(record['archives'][label]['path'], 'r:xz') as tar:
                tar.extractall(target)
        gcc_paths = [p for p in target.rglob('m68k-atari-mint-gcc') if p.is_file() and os.access(p, os.X_OK)]
        if len(gcc_paths) != 1:
            raise RuntimeError('BLOCKED_GCC_LAYOUT: expected one executable, got ' + str(len(gcc_paths)))
        bindir = gcc_paths[0].parent
        for name in ('as', 'ld', 'objcopy'):
            if not (bindir / ('m68k-atari-mint-' + name)).is_file():
                raise RuntimeError('BLOCKED_BINUTILS_LAYOUT: ' + name)
        record['status'] = 'READY_FOR_ABI_PREFLIGHT'
        record['bin_dir'] = str(bindir)
    except Exception as exc:
        record['reason'] = str(exc)
    finally:
        (out / 'toolchain_manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))
    return 0 if record['status'] == 'READY_FOR_ABI_PREFLIGHT' else 2


if __name__ == '__main__':
    raise SystemExit(main())
