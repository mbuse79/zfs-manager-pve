#!/usr/bin/env bash
# Standalone entrypoint: no unzip required. Trust its separately supplied SHA256.
set -Eeuo pipefail
exec python3 - "$@" <<'PYBOOT'
import hashlib, os, re
from pathlib import Path

def verify(root):
    root=Path(root)
    manifest=root/'SHA256SUMS'
    if manifest.is_symlink() or not manifest.is_file(): raise ValueError('Missing manifest')
    entries={}
    for line in manifest.read_text('ascii').splitlines():
        match=re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.+~/ -]+)',line)
        if not match: raise ValueError('Invalid manifest line')
        digest,name=match.groups()
        parts=Path(name).parts
        if Path(name).is_absolute() or '..' in parts or name in entries or name=='SHA256SUMS':
            raise ValueError('Unsafe or duplicate manifest path')
        entries[name]=digest
    actual=set()
    for p in root.rglob('*'):
        if p.is_symlink(): raise ValueError('Symlink forbidden')
        if p.is_file(): actual.add(p.relative_to(root).as_posix())
        elif not p.is_dir(): raise ValueError('Special file forbidden')
    if actual != set(entries)|{'SHA256SUMS'}: raise ValueError('Incomplete manifest or extra files')
    for name,digest in entries.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=digest: raise ValueError('SHA256 mismatch: '+name)

import shutil, stat, subprocess, sys, tempfile, urllib.request, zipfile
if len(sys.argv)<3 or not sys.argv[1].startswith('https://') or not re.fullmatch('[a-fA-F0-9]{64}',sys.argv[2]):
    raise SystemExit('Usage: bash bootstrap-1.1.1.sh HTTPS-ZIP-URL ZIP-SHA256 [--check-only] [--lang de|en]')
with tempfile.TemporaryDirectory(prefix='zfsm-bootstrap-') as td:
    os.chmod(td,0o700)
    archive=Path(td)/'release.zip'
    with urllib.request.urlopen(sys.argv[1],timeout=60) as response:
        if not response.url.startswith('https://'): raise ValueError('HTTPS redirect required')
        with archive.open('wb') as dest:
            total=0
            while True:
                chunk=response.read(1024*1024)
                if not chunk: break
                total+=len(chunk)
                if total>100*1024*1024: raise ValueError('Archive too large')
                dest.write(chunk)
    if hashlib.sha256(archive.read_bytes()).hexdigest()!=sys.argv[2].lower(): raise ValueError('ZIP-SHA256 mismatch')
    target=Path(td)/'package';target.mkdir(mode=0o700)
    with zipfile.ZipFile(archive) as z:
        seen=set();total=0
        if len(z.infolist())>5000: raise ValueError('Too many entries')
        for info in z.infolist():
            name=info.filename;path=Path(name)
            mode=info.external_attr>>16
            if path.is_absolute() or '..' in path.parts or '\\' in name or path.as_posix()!=name.rstrip('/') or name in seen:
                raise ValueError('Unsafe/duplicate ZIP name')
            seen.add(name)
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in (0,stat.S_IFREG,stat.S_IFDIR)):
                raise ValueError('ZIP special file forbidden')
            total+=info.file_size
            if total>200*1024*1024: raise ValueError('Expanded archive too large')
        z.extractall(target)
    verify(target)
    raise SystemExit(subprocess.run(['bash',str(target/'install-local.sh'),*sys.argv[3:]]).returncode)
PYBOOT
