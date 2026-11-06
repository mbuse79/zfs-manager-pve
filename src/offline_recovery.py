#!/usr/bin/env python3
"""RC9 offline rescue runner: signed one-use plan only, never on running PVE.

Run --stage --root /mnt/pve-root after importing the pool in rescue and
mounting host root; unmount that dataset before --check/--apply from /run.
"""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import time

BUNDLE=Path('/run/pve-zfs-manager-rescue')
DATASET_RE=re.compile(r'^[A-Za-z0-9_.:~-]+(?:/[A-Za-z0-9_.:~-]+)*$')
SNAP_RE=re.compile(r'^[A-Za-z0-9_.:-]{1,128}$')

class RescueError(Exception):pass

def secure_file(path, maxsize):
    if path.is_symlink(): raise RescueError(f'Symlink verweigert: {path}')
    st=path.stat()
    if not stat.S_ISREG(st.st_mode) or st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o600:
        raise RescueError(f'Unsichere Besitzer/Rechte: {path}')
    if st.st_nlink!=1 or st.st_size>maxsize or st.st_size<1:
        raise RescueError(f'Unsichere Datei: {path}')
    return path.read_bytes()

def run(*args):
    cp=subprocess.run(args,capture_output=True,text=True,timeout=30)
    if cp.returncode:raise RescueError('Befehl fehlgeschlagen: '+' '.join(args)+'\n'+cp.stderr[-300:])
    if len(cp.stdout)>100000:raise RescueError('Ausgabe zu groß')
    return cp.stdout

def require_tmpfs():
    # Never copy the private HMAC secret to a persistent /run in unusual rescue media.
    fs=run('/usr/bin/findmnt','-n','-o','FSTYPE','/run').strip()
    if fs!='tmpfs':raise RescueError('Rescue /run ist kein tmpfs - Kopie des Schluessels verweigert')

def extract_stage(root):
    require_tmpfs()
    base=root/'var/lib/pve-zfs-manager/offline-rollback'
    if base.is_symlink() or not base.is_dir():raise RescueError('Kein sicherer Planordner')
    st=base.stat()
    if st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o700:raise RescueError('Unsicherer Planordner')
    plans=list(base.glob('plan-*.json'))
    if len(plans)!=1:raise RescueError('Erwartet genau EINEN Offline-Auftrag')
    raw=secure_file(plans[0],8192)
    key=secure_file(root/'etc/pve-zfs-manager/preview.key',256).strip()
    if not re.fullmatch(rb'[a-f0-9]{64}',key):raise RescueError('Schlüssel ungültig')
    BUNDLE.mkdir(mode=0o700,exist_ok=True)
    st=BUNDLE.stat()
    if BUNDLE.is_symlink() or st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o700:
        raise RescueError('RAM-Sicherungsverzeichnis unsicher')
    for name,blob in [('plan.json',raw),('key',key)]:
        path=BUNDLE/name
        fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as f:f.write(blob)
    me=Path(__file__).resolve()
    # Copy the runner to tmpfs before the host filesystem is unmounted.
    dest=BUNDLE/'offline_recovery.py'
    if dest.exists():raise RescueError('Runner bereits vorhanden')
    dest.write_bytes(me.read_bytes());dest.chmod(0o700)
    print('PASS: Signierter Auftrag und Runner ins Rescue-RAM gesichert.')
    print('Danach das Host-Dateisystem aushaengen und nur vom RAM aus --check / --apply ausfuehren.')

def plan_from_bundle():
    require_tmpfs()
    st=BUNDLE.stat()
    if BUNDLE.is_symlink() or st.st_uid!=0 or stat.S_IMODE(st.st_mode)!=0o700:
        raise RescueError('Unsicherer RAM-Ordner')
    obj=json.loads(secure_file(BUNDLE/'plan.json',8192))
    key=secure_file(BUNDLE/'key',256).strip()
    if type(obj)!=dict or obj.get('version')!=1:raise RescueError('Unbekanntes Planformat')
    dataset=obj.get('dataset');snap=obj.get('snapshot');fingerprint=obj.get('fingerprint')
    expires=obj.get('expires');signature=obj.get('signature')
    if not isinstance(dataset,str) or len(dataset)>200 or not DATASET_RE.fullmatch(dataset):raise RescueError('Dataset ungültig')
    if not isinstance(snap,str) or not SNAP_RE.fullmatch(snap):raise RescueError('Snapshot ungültig')
    if not isinstance(fingerprint,str) or not re.fullmatch('[a-f0-9]{64}',fingerprint):raise RescueError('Fingerprint ungültig')
    if type(expires)!=int or not(time.time()<expires<=time.time()+86400):raise RescueError('Offline-Auftrag abgelaufen')
    if not isinstance(signature,str) or not re.fullmatch('[a-f0-9]{64}',signature):raise RescueError('Signatur ungültig')
    mac=hmac.new(key,('|'.join(['ZFSMGR-OFFLINE-1',dataset,snap,fingerprint,str(expires)])).encode(),hashlib.sha256).hexdigest()
    if not hmac.compare_digest(mac,signature):raise RescueError('Signatur passt nicht')
    return obj

def check_plan(obj):
    ds=obj['dataset'];snap=obj['snapshot']
    # ROOT mounted anywhere (and any mounted descendant) => never execute.
    mounts=run('/usr/sbin/zfs','list','-H','-r','-t','filesystem','-o','name,mounted',ds)
    for line in mounts.splitlines():
        cols=line.split('\t')
        if len(cols)!=2 or cols[1] not in ('yes','no','-'):
            raise RescueError('Mountstatus nicht eindeutig')
        if cols[1]=='yes':raise RescueError(f'ZFS-Dataset ist noch gemountet: {cols[0]}')
    raw=run('/usr/sbin/zfs','list','-H','-p','-t','snapshot',
            '-o','name,creation,createtxg','-s','createtxg','-d','1',ds)
    rows=[]
    for line in raw.splitlines():
        cols=line.split('\t')
        if len(cols)!=3 or not cols[0].startswith(ds+'@') or not all(x.isdecimal() for x in cols[1:]):
            raise RescueError('Snapshotliste ungültig')
        name=cols[0][len(ds)+1:]
        if not SNAP_RE.fullmatch(name):raise RescueError('Snapshotname nicht zugelassen')
        rows.append((name,cols[1],cols[2]))
    if snap not in [x[0] for x in rows]:raise RescueError('Snapshot existiert nicht mehr')
    material=['HOST-V1','HOST-ROLLBACK',ds,snap,obj['mounted_at_preview'],obj['mountpoint']]
    material += [':'.join(x) for x in rows]
    digest=hashlib.sha256('|'.join(material).encode()).hexdigest()
    if digest!=obj['fingerprint']:raise RescueError('Snapshots oder Datenset-Eigenschaften seit Vorschau verändert')
    later=[x[0] for x in rows[[x[0] for x in rows].index(snap)+1:]]
    bookmarks=run('/usr/sbin/zfs','list','-H','-t','bookmark','-o','name','-d','1',ds)
    if bookmarks.strip():raise RescueError('ZFS Bookmarks vorhanden')
    for n in [snap]+later:
        full=f'{ds}@{n}'
        if run('/usr/sbin/zfs','get','-H','-o','value','clones',full).strip()!='-':
            raise RescueError('Abhängige Klone vorhanden')
        if run('/usr/sbin/zfs','get','-H','-o','value','userrefs',full).strip()!='0':
            raise RescueError('Snapshot-Hold vorhanden')
    bounded=f'{ds}@{later[0]}%{later[-1]}' if len(later)>1 else (f'{ds}@{later[0]}' if later else None)
    if bounded:run('/usr/sbin/zfs','destroy','-n','-v',bounded)
    return later,bounded

def execute():
    # The actual execution is intentionally NOT available in the Proxmox GUI.
    # Require a rescue OS, an unmounted pool, the staged authenticated bundle.
    obj=plan_from_bundle()
    later,bounded=check_plan(obj)
    print('GEPRUEFT:',obj['dataset']+'@'+obj['snapshot'])
    print('Zu entfernende neuere Snapshots:',len(later))
    return obj,later,bounded

def main():
    ap=argparse.ArgumentParser()
    group=ap.add_mutually_exclusive_group(required=True)
    group.add_argument('--stage',action='store_true')
    group.add_argument('--check',action='store_true')
    group.add_argument('--apply',action='store_true')
    ap.add_argument('--root',default='/mnt/pve-root')
    args=ap.parse_args()
    if os.geteuid()!=0:raise RescueError('Nur root')
    if args.stage:
        extract_stage(Path(args.root));return
    obj,later,bounded=execute()
    if args.check:
        print('PASS: Nur geprüft. KEIN Rollback ausgeführt.');return
    # Requires a deliberate command after prior stage/check, without entering dataset names.
    if bounded:run('/usr/sbin/zfs','destroy',bounded)
    run('/usr/sbin/zfs','rollback',obj['dataset']+'@'+obj['snapshot'])
    done=BUNDLE/'plan.json'
    done.rename(BUNDLE/'plan-applied.json')
    print('PASS: Offline-Rollback abgeschlossen. Bootkonfiguration vor Neustart prüfen.')

if __name__=='__main__':
    try:main()
    except (RescueError,RuntimeError,OSError,ValueError,subprocess.SubprocessError) as e:
        print('STOPP:',e,file=sys.stderr);sys.exit(1)
