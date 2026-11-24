#!/usr/bin/env python3
"""RC8 local installer. Invoked only after the outer manifest was verified."""
import argparse
from contextlib import contextmanager
import fcntl
import stat
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

VERSION = '1.1.1'
HERE = Path(__file__).resolve().parent

def run(argv, **kw):
    return subprocess.run(argv, check=True, text=True, **kw)

def output(argv):
    return run(argv, capture_output=True).stdout.strip()

def installed(name):
    p = subprocess.run(['dpkg-query','-W','-f=${Status}\t${Version}',name],capture_output=True,text=True)
    return p.stdout.split('\t',1)[1].strip() if p.returncode == 0 and '\t' in p.stdout and (name=='pve-zfs-manager' or p.stdout.startswith('install ok installed\t')) else None

def plan_changes(text, allowed):
    planned = set()
    for line in text.splitlines():
        if line.startswith(('Remv ', 'Purg ')):
            raise RuntimeError('Unexpected package action: '+line)
        if line.startswith('Conf ') and line.split()[1].split(':')[0] not in allowed:
            raise RuntimeError('Unexpected configuration: '+line)
        if line.startswith('Inst '):
            name = line.split()[1].split(':')[0]
            if name not in allowed or name in planned:
                raise RuntimeError('Unexpected package installation: '+line)
            planned.add(name)
    if planned != set(allowed):
        raise RuntimeError('APT plan does not match the exact requested packages; expected: '+', '.join(sorted(allowed))+'; planned: '+', '.join(sorted(planned))+'\n'+text)

ALTERNATIVES = ('sanoid','zrepl','zfs-autobackup','pyznap','znapzend','snapper')
def competing(root=Path('/'), which=shutil.which):
    """Conservative detection, never claim an unimplemented backend adapter."""
    found=set()
    for name in ALTERNATIVES:
        if which(name) or (root/'etc'/name).exists(): found.add(name)
    locations = ['etc/crontab','var/spool/cron/crontabs/root']
    for rel in ('etc/cron.d','etc/cron.hourly','etc/cron.daily','etc/cron.weekly','etc/cron.monthly',
                'etc/systemd/system','usr/lib/systemd/system','lib/systemd/system'):
        d=root/rel
        if d.is_dir(): locations.extend(str(p.relative_to(root)) for p in d.iterdir() if p.is_file())
    for rel in locations:
        p=root/rel
        if not p.is_file() or p.stat().st_size > 65536: continue
        lines='\n'.join(x for x in p.read_text(errors='replace').splitlines() if not x.lstrip().startswith('#'))
        for name in ALTERNATIVES:
            if re.search(r'(?<![\w-])'+re.escape(name)+r'(?![\w-])',lines) or name in p.name:
                found.add(name)
    return sorted(found)

@contextmanager
def package_lock(path=Path('/run/lock/pve-zfs-manager-install.lock')):
    """Serialize ZIP installer writes without bypassing dpkg's own locks."""
    fd=os.open(path,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        meta=os.fstat(fd)
        if not stat.S_ISREG(meta.st_mode) or meta.st_uid!=0 or stat.S_IMODE(meta.st_mode)!=0o600:
            raise RuntimeError('Unsafe package installation lock / Unsichere Installationssperre')
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError('Another ZFSM installation is running / Eine ZFSM-Installation laeuft bereits') from exc
        yield
    finally:
        os.close(fd)

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--check-only',action='store_true')
    parser.add_argument('--lang',choices=['de','en'],default='de')
    args=parser.parse_args(argv)
    de=args.lang=='de'
    def say(german,english): print(german if de else english,flush=True)
    if os.geteuid()!=0: raise RuntimeError('root required / Root-Rechte erforderlich')
    version=output(['pveversion'])
    if not re.match(r'^pve-manager/9\.\d+\.\d+/',version):
        raise RuntimeError('Only PVE 9.x is supported / Nur PVE 9.x unterstützt: '+version)
    deb=HERE/('pve-zfs-manager_'+VERSION+'_all.deb')
    if output(['dpkg-deb','-f',str(deb),'Package'])!='pve-zfs-manager' or output(['dpkg-deb','-f',str(deb),'Version'])!=VERSION:
        raise RuntimeError('Wrong package metadata / Falsche Paketmetadaten')
    current=installed('pve-zfs-manager')
    if current and subprocess.run(['dpkg','--compare-versions',current,'ge',VERSION]).returncode==0:
        if current == VERSION and not args.check_only:
            sys.path.insert(0, '/usr/lib/pve-zfs-manager')
            from zfsm_cluster_cache import register
            register(HERE)
        say('Gleiche oder neuere Version vorhanden; keine Änderung: '+current,'Same or newer version installed; no change: '+current)
        return 0
    alternative=competing()
    if alternative:
        raise RuntimeError('Kein unterstützter Adapter / No supported adapter: '+', '.join(alternative)+
                           '. Konflikt zuerst manuell klären; keine parallelen Zeitpläne. / Resolve conflict first; no parallel schedules.')
    with tempfile.TemporaryDirectory(prefix='zfsm-rc8-') as td:
        os.chmod(td,0o700)
        run(['dpkg-deb','-x',str(deb),td])
        source=Path(td)/'usr/lib/pve-zfs-manager'
        run([sys.executable,str(source/'universal.py'),'precheck'])
        sys.path.insert(0,str(source))
        from zfsm_host_audit import discover
        audit=discover()
        a=audit['autosnap']
        if a['duplicate_labels'] or any(x['keep'] is None or x['label']=='unknown' for x in a['schedules']):
            raise RuntimeError('AutoSnap-Konflikt: Zeitpläne zuerst prüfen / Review conflicting or unknown AutoSnap schedules')
        if audit['other_cleanup_units'] or audit['other_cleanup_cron']:
            raise RuntimeError('Weitere Bereinigungsdienste: manuell prüfen / Other cleanup services require review')
        existing_cron=any((Path('/etc')/d/'zfs-auto-snapshot').exists() for d in ('cron.d','cron.hourly','cron.daily','cron.weekly','cron.monthly'))
        if not installed('zfs-auto-snapshot') and (a['binary'] or a['schedules'] or existing_cron):
            raise RuntimeError('Manuelle AutoSnap-Installation: nicht überschreiben / Do not overwrite manual AutoSnap installation')
        missing=[]
        for name in ('unzip','zfs-auto-snapshot'):
            if not installed(name): missing.append(name)
        archives=[]
        arch=output(['dpkg','--print-architecture'])
        for name in missing:
            candidates=list((HERE/'dependencies').glob(name+'_*.deb'))
            if len(candidates)!=1: raise RuntimeError('Missing/ambiguous bundled dependency: '+name)
            p=candidates[0]
            if output(['dpkg-deb','-f',str(p),'Package'])!=name or output(['dpkg-deb','-f',str(p),'Architecture']) not in ('all',arch):
                raise RuntimeError('Dependency package/architecture mismatch: '+name)
            archives.append(str(p))
        # Ensure even empty package installations cannot leave unmet dependencies.
        def simulate():
            cmd=['apt-get','--simulate','--no-remove','--no-install-recommends','install',*archives,str(deb)]
            plan=output(cmd)
            plan_changes(plan,[*missing,'pve-zfs-manager'])
            return plan
        simulate()
        say('Prüfmodus erfolgreich; keine Änderungen.' if args.check_only else 'Vorprüfung erfolgreich.',
            'Check completed; no changes.' if args.check_only else 'Preflight completed.')
        if args.check_only: return 0
        with package_lock():
            # Repeat every volatile guard immediately before applying the fixed plan.
            if output(['pveversion'])!=version or installed('pve-zfs-manager')!=current or competing()!=alternative:
                raise RuntimeError('Host state changed; rerun / Hostzustand verändert; erneut prüfen')
            run([sys.executable,str(source/'universal.py'),'precheck'])
            if discover()!=audit: raise RuntimeError('Inventory changed / Inventur verändert')
            for name in missing:
                if installed(name): raise RuntimeError('Dependency state changed: '+name)
            simulate()
            # dpkg installs only verified local files; it never resolves additional packages.
            run(['dpkg','-i',*archives,str(deb)])
        for cmd in (['zfsm','version','--lang',args.lang],['zfsm','check','--lang',args.lang],['zfsm','services','--lang',args.lang]): run(cmd)
        from zfsm_cluster_cache import register
        register(HERE)
        say('Version 1.1.1 installiert. Bestehende Sicherheits- und Bereinigungseinstellungen bleiben erhalten.',
            'Version 1.1.1 installed. Existing safety and cleanup settings are preserved.')
    return 0

if __name__=='__main__':
    try: sys.exit(main())
    except (RuntimeError,OSError,subprocess.CalledProcessError) as exc:
        print('STOP: '+str(exc),file=sys.stderr);sys.exit(1)
