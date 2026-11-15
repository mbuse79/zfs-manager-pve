#!/usr/bin/env bash
# RC8: verify a private snapshot of ALL package files before executing included code.
set -Eeuo pipefail
HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 - "$HERE" "$@" <<'PYVERIFY'
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

import shutil, subprocess, sys, tempfile
with tempfile.TemporaryDirectory(prefix='zfsm-verified-') as td:
    os.chmod(td,0o700)
    source=Path(sys.argv[1])
    # Refuse links before copying; do not dereference untrusted paths.
    if any(p.is_symlink() for p in source.rglob('*')): raise ValueError('Symlink forbidden')
    shutil.copytree(source,Path(td)/'package',symlinks=True)
    target=Path(td)/'package'
    verify(target)
    raise SystemExit(subprocess.run([sys.executable,str(target/'install_driver.py'),*sys.argv[2:]]).returncode)
PYVERIFY
