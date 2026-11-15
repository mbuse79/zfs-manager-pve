#!/usr/bin/env python3
"""Bounded, strictly read-only discovery of ZFS tooling on a PVE host.

The ZFS Manager owns AutoSnap UI/retention. Other replication products are
recognized only for avoiding unsafe conflicting housekeeping; their control
belongs to a separate Replication Manager. No passwords or unit ExecStart
arguments leave this module.
"""
import json
import re
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

STANDARD = {
    'frequent': 'etc/cron.d/zfs-auto-snapshot',
    'hourly': 'etc/cron.hourly/zfs-auto-snapshot',
    'daily': 'etc/cron.daily/zfs-auto-snapshot',
    'weekly': 'etc/cron.weekly/zfs-auto-snapshot',
    'monthly': 'etc/cron.monthly/zfs-auto-snapshot',
    'yearly': 'etc/cron.d/pve-zfs-manager-yearly',
}
CRON_DIRS = ('etc/cron.d','etc/cron.hourly','etc/cron.daily',
             'etc/cron.weekly','etc/cron.monthly','etc/cron.yearly')
UNIT_DIRS = ('etc/systemd/system', 'usr/lib/systemd/system', 'lib/systemd/system')
REPL_RE = re.compile(r'(?i)(?:bashclub.?zsync|(?<![a-z])zsync(?![a-z])|syncoid|sanoid|zrepl|pvesr\s)')
OTHER_CLEAN = re.compile(r'(?i)(?:\bzfs\s+(?:destroy|release)\b|\bzfs-auto-snapshot\b|\bsnapper\b|\bprune\b)')
AUTOSNAP_RE = re.compile(r'(?<![\w-])zfs-auto-snapshot(?![\w-])')
LABEL_RE = re.compile(r'--label(?:=|\s+)([a-z]+)')
KEEP_RE = re.compile(r'--keep(?:=|\s+)([0-9]+)')
MAX_FILES = 1200
MAX_FILE_BYTES = 64 * 1024
# Cron scripts routinely check that AutoSnap exists before invoking it.
# That guard is not a schedule and must not count as an 'unknown' rule.
PROBE_RE = re.compile(r'(?i)\b(?:which|command\s+-v|type\s+-[a-z]+|test\s+-x)\s+(?:/usr/sbin/)?zfs-auto-snapshot\b')


def autosnap_invocation(line):
    if not AUTOSNAP_RE.search(line):
        return False
    # A normal invocation with --label is never dismissed by a preceding
    # 'which' guard on the same cron.d line.
    if LABEL_RE.search(line) or KEEP_RE.search(line):
        return True
    if PROBE_RE.search(line):
        return False
    return True  # Unknown real command: require manual review rather than guessing.


def active_entries(text):
    return [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1)
            if line.strip() and not line.lstrip().startswith('#')]


def output(argv, timeout=5, runner=subprocess.run):
    try:
        proc = runner(argv, capture_output=True, text=True, timeout=timeout, check=False)
        return proc.stdout[:100_000] if proc.returncode == 0 else ''
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return ''


def load_text(path):
    try:
        if not path.is_file() or path.stat().st_size > MAX_FILE_BYTES:
            return ''
        return path.read_text('utf-8', errors='replace')
    except (OSError, UnicodeError):
        return ''


def active_lines(text):
    return [line.strip() for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith('#')]


def package_status(name, run=output):
    status = run(['dpkg-query','-W','-f=${db:Status-Abbrev}',name]).strip()
    return 'installed' if status.startswith('ii') else 'removed-config-left' if status.startswith('rc') else 'absent'


def discover(root='/', run=output, which=shutil.which):
    """Inventory only, injectable root/runner for isolated unit tests."""
    root = Path(root)
    def here(rel): return root / rel
    def path_label(path):
        return '/' + str(path.relative_to(root))
    has_binary = bool(which('zfs-auto-snapshot'))
    installed = package_status('zfs-auto-snapshot', run=run)
    schedules = []
    cron_external, cron_cleanup, cron_check = set(), set(), set()
    seen_paths = set()
    scanned = 0
    # Scan cron rules even when the package manager reports no package.
    for rel in CRON_DIRS:
        location = here(rel)
        if not location.is_dir():
            continue
        for f in sorted(location.iterdir()):
            if not f.is_file() or f.is_symlink():
                continue
            scanned += 1
            if scanned > MAX_FILES: break
            seen_paths.add(str(f))
            for lineno, ln in active_entries(load_text(f)):
                if REPL_RE.search(ln):cron_external.add(path_label(f))
                elif 'checkzfs' in ln.lower():cron_check.add(path_label(f))
                elif OTHER_CLEAN.search(ln) and not AUTOSNAP_RE.search(ln):
                    cron_cleanup.add(path_label(f))
                if not autosnap_invocation(ln): continue
                label = LABEL_RE.search(ln)
                keep = KEEP_RE.search(ln)
                schedules.append({'label':label.group(1) if label else 'unknown',
                                  'keep':int(keep.group(1)) if keep else None,
                                  'source':path_label(f), 'line':lineno, 'standard':path_label(f).lstrip('/') in STANDARD.values()})
        if scanned > MAX_FILES: break
    # Cron may be defined in /etc/crontab rather than /etc/cron.d.
    for rel in ('etc/crontab',):
        f = here(rel)
        for lineno, ln in active_entries(load_text(f)):
            if REPL_RE.search(ln):cron_external.add(path_label(f))
            elif 'checkzfs' in ln.lower():cron_check.add(path_label(f))
            elif OTHER_CLEAN.search(ln) and not AUTOSNAP_RE.search(ln):cron_cleanup.add(path_label(f))
            if not autosnap_invocation(ln): continue
            label,keep=LABEL_RE.search(ln),KEEP_RE.search(ln)
            schedules.append({'label':label.group(1) if label else 'unknown',
                              'keep':int(keep.group(1)) if keep else None,
                              'source':path_label(f),'line':lineno,'standard':False})
    # Root's crontab may have additional cleanup tasks; never disclose its raw content.
    root_crontab = run(['crontab','-l','-u','root']) if root == Path('/') else ''
    for lineno, ln in active_entries(root_crontab):
        if REPL_RE.search(ln):cron_external.add('root crontab')
        elif 'checkzfs' in ln.lower():cron_check.add('root crontab')
        elif OTHER_CLEAN.search(ln) and not AUTOSNAP_RE.search(ln):cron_cleanup.add('root crontab')
        if not autosnap_invocation(ln):continue
        label,keep=LABEL_RE.search(ln),KEEP_RE.search(ln)
        schedules.append({'label':label.group(1) if label else 'unknown',
                          'keep':int(keep.group(1)) if keep else None,
                          'source':'root crontab','line':lineno,'standard':False})
    count = Counter(s['label'] for s in schedules)
    duplicate_labels = sorted(k for k,v in count.items() if k!='unknown' and v > 1)
    unknown = any(s['label']=='unknown' or s['keep'] is None for s in schedules)
    active_autosnap = bool(schedules)
    # Detect running or configured replication/cleanup outside the package DB.
    # Return UNIT NAMES ONLY; ExecStart can contain credentials and must be private.
    units, external, cleanup, check_units = {},set(),set(),set()
    scanned_units = 0
    for rel in UNIT_DIRS:
        d = here(rel)
        if not d.is_dir():continue
        for glob in ('*.service','*.timer','*.path'):
            for f in sorted(d.glob(glob)):
                if f.is_symlink() or not f.is_file() or f.name in units:continue
                scanned_units += 1
                if scanned_units > MAX_FILES:break
                lines = active_lines(load_text(f))
                body = '\n'.join(lines)
                if REPL_RE.search(body) or REPL_RE.search(f.name):
                    external.add(f.name)
                elif 'checkzfs' in body.lower() or 'checkzfs' in f.name.lower():
                    check_units.add(f.name)
                elif OTHER_CLEAN.search(body) and not f.name.startswith('pve-zfs-manager'):
                    cleanup.add(f.name)
                units[f.name]=True
    # Native PVE replication is a separate controller, not owned by ZFS Manager.
    timer_output = run(['systemctl','list-timers','--all','--no-pager','--no-legend']) if root == Path('/') else ''
    active_timers = sorted(f for f in external if f.endswith('.timer') and f in timer_output)
    native = run(['pvesr','list'],timeout=8) if root == Path('/') else run(['pvesr','list'])
    native_count = sum(1 for line in native.splitlines()[1:] if line.strip()) if native.strip() else 0
    zsync_status = package_status('bashclub-zsync',run=run)
    detected_manual_zsync = any('zsync' in name.lower() for name in external)
    # A missing command in PATH is not proof that no manually installed binary exists.
    external_detected = bool(external or cron_external or native_count or zsync_status=='installed')
    warnings = []
    if duplicate_labels: warnings.append('Doppelte AutoSnap-Zeitpläne: ' + ', '.join(duplicate_labels))
    if unknown: warnings.append('AutoSnap-Auftrag ohne eindeutige Art oder Aufbewahrung')
    if not active_autosnap: warnings.append('Keine aktive AutoSnap-Zeitplanregel erkannt')
    if zsync_status=='removed-config-left' and detected_manual_zsync:
        warnings.append('Manuell gestarteter zsync-Dienst trotz entferntem DEB erkannt; nicht ersetzen')
    if cleanup or cron_cleanup: warnings.append('Weitere Bereinigungsdienste erkannt; keine parallele Bereinigung anlegen')
    autosnap = {'package':installed,'binary':has_binary,
                'schedules':schedules, 'schedule_count':len(schedules),
                'duplicate_labels':duplicate_labels,
                'ready':installed=='installed' and has_binary and active_autosnap and not duplicate_labels and not unknown}
    return {'schema':1,'mode':'read-only','autosnap':autosnap,
            'replication':{'detected':external_detected,'systemd_units':sorted(external),
                           'active_timers':active_timers,'cron_sources':sorted(cron_external),
                           'native_pve_jobs':native_count,'zsync_package':zsync_status,
                           'manual_zsync_detected':detected_manual_zsync,
                           'management':'external-only; snapshot protection'},
            'monitoring':{'checkzfs_package':package_status('bashclub-checkzfs',run=run),
                          'checkzfs_binary':bool(which('checkzfs')),'systemd_units':sorted(check_units),
                          'cron_sources':sorted(cron_check)},
            'other_cleanup_units':sorted(cleanup),'other_cleanup_cron':sorted(cron_cleanup), 'warnings':warnings,
            'new_cleanup_timer_needed':False,
            'autosnap_action':('adopt' if autosnap['ready'] else 'install' if installed!='installed' else 'review'),
            'policy':'Do not manage replication or create duplicate cleanup schedules'}


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description='ZFS Manager: sichere Host-Inventur (nur lesend)')
    parser.add_argument('--json',action='store_true')
    args=parser.parse_args(argv)
    data=discover()
    if args.json:
        print(json.dumps(data,ensure_ascii=False,sort_keys=True))
    else:
        a=data['autosnap'];r=data['replication'];c=data['monitoring']
        print('AutoSnap: '+a['package']+' | '+str(a['schedule_count'])+' Zeitpläne | '+('OK' if a['ready'] else 'PRÜFEN'))
        for s in a['schedules']:
            print('  '+s['label']+': behalte '+str(s['keep'])+' | '+s['source'])
        print('Replikation (nur Erkennung/Schutz): '+str(len(r['systemd_units']))+
              ' Systemd-Units, '+str(r['native_pve_jobs'])+' native PVE-Aufträge')
        print('CheckZFS: '+c['checkzfs_package']+' | '+str(len(c['cron_sources']))+' Cron-Quellen')
        for warning in data['warnings']:
            print('HINWEIS: '+warning)
        print('Keine Replikation wird verwaltet. Kein zusätzlicher Bereinigungstimer wird angelegt.')
    return 0

if __name__=='__main__':sys.exit(main())
