#!/usr/bin/env python3
"""Explicit admin allowlist management, requires root; never assigns PVE RBAC rights."""
from pathlib import Path
import argparse, os, re, sys, tempfile
PATH=Path('/etc/pve-zfs-manager/admins.conf')
USER=re.compile(r'^[a-zA-Z0-9_.-]{1,64}@[a-zA-Z0-9_.-]{1,64}$')

def main():
    parser=argparse.ArgumentParser(description='Root-controlled additional ZFS Manager administrators')
    parser.add_argument('action',choices=['list','add','remove'])
    parser.add_argument('user',nargs='?')
    opt=parser.parse_args()
    if os.geteuid()!=0: parser.error('root erforderlich')
    if PATH.is_symlink() or not PATH.is_file() or PATH.stat().st_uid!=0 or (PATH.stat().st_mode & 0o777)!=0o600:
        parser.error('Unsichere oder fehlende Admin-Datei')
    lines=PATH.read_text().splitlines()
    members=set(l for l in lines if l and not l.startswith('#'))
    if opt.action=='list':
        print('root@pam (fest)')
        for v in sorted(members):print(v)
        return
    if not opt.user or not USER.fullmatch(opt.user) or opt.user=='root@pam':
        parser.error('Eindeutiger PVE-Benutzer erforderlich (nicht root@pam oder Token)')
    if opt.action=='add':members.add(opt.user)
    else:members.discard(opt.user)
    fd,tmp=tempfile.mkstemp(dir=PATH.parent,prefix='.admins-')
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as f:
            f.write('# Explicit additional administrators; requires Sys.Modify AND Permissions.Modify\n')
            for v in sorted(members): f.write(v+'\n')
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp,PATH)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    print('Admin-Liste aktualisiert. Weitere PVE-Rechte werden NICHT automatisch vergeben.')
if __name__=='__main__': main()
