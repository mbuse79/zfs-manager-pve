#!/usr/bin/env python3
"""Small local CLI for the Proxmox ZFS Manager, without ZFS write commands."""
import argparse
import json
import locale
import os
from pathlib import Path
import subprocess
import sys

import universal

VERSION='1.0.0-32'
DE={
 'heading':'ZFS Manager for Proxmox VE', 'usage':'Verwendung', 'commands':'Befehle',
 'help':'Hilfe anzeigen', 'status':'Integration, Version und Dienste anzeigen',
 'version':'Plugin- und Proxmox-Version anzeigen', 'check':'Kompatibilität ohne Änderungen prüfen',
 'repair':'GUI/API-Integration reparieren', 'force':'Manueller Reparaturversuch mit Warnung',
 'backup':'Sicherung der aktuellen Integrationsdateien erstellen',
 'backups':'Verfügbare Sicherungen anzeigen', 'restore':'Sicherungen anzeigen; sichere Wiederherstellung nur für dieselbe PVE-Version',
 'logs':'Letzte Reparaturprotokolle anzeigen', 'services':'Überwachungsdienste anzeigen',
 'update-check':'Installiertes Plugin-Paket anzeigen (keine Updatequelle eingerichtet)',
 'capacity':'Pool-Kapazität, Snapshot-Verbrauch und Aufbewahrungsübersicht (nur lesend)',
 'confirm':'Reparatur trotz Kompatibilitätswarnung versuchen? [j/N]: ',
 'cancel':'Abgebrochen.', 'warning':'WARNUNG: Unbekannte Proxmox-Struktur. Keine blinden Änderungen; Schutzprüfungen bleiben aktiv.',
 'no_backup':'Keine Sicherungen vorhanden', 'snapshot':'Sicherung erstellt:',
 'restore_note':'Automatische Rücksicherung alter Proxmox-Dateien ist gesperrt. Bitte passende Sicherung und PVE-Version prüfen.',
 'error':'FEHLER',
}
EN={
 'heading':'ZFS Manager for Proxmox VE', 'usage':'Usage', 'commands':'Commands',
 'help':'Show this help', 'status':'Show integration, version, and service status',
 'version':'Show plugin and Proxmox version', 'check':'Read-only compatibility check',
 'repair':'Repair GUI/API integration', 'force':'Manual repair attempt with warning',
 'backup':'Back up the current integration files', 'backups':'List available backups',
 'restore':'List backups; restoration only with matching PVE version',
 'logs':'Show recent repair logs', 'services':'Show watcher service states',
 'update-check':'Show installed package (no update source configured)',
 'capacity':'Read-only pool capacity, snapshot usage and retention audit',
 'confirm':'Attempt repair despite compatibility warning? [y/N]: ',
 'cancel':'Cancelled.', 'warning':'WARNING: Unknown Proxmox layout. No blind modification; safety guards stay enabled.',
 'no_backup':'No backups found', 'snapshot':'Backup created:',
 'restore_note':'Automatic restore of old Proxmox files is blocked. Verify the backup and PVE version.',
 'error':'ERROR',
}
HELP_COMMANDS=('help','status','version','check','repair','backup','backups','restore','logs','services','update-check','capacity')

def language(requested=None):
    raw=(requested or os.environ.get('LC_ALL') or os.environ.get('LC_MESSAGES') or os.environ.get('LANG') or 'en').lower()
    return DE if raw.startswith('de') or (not requested and raw in ('c','c.utf-8','posix') and Path('/etc/default/locale').is_file() and 'de_' in Path('/etc/default/locale').read_text().lower()) else EN

def run(cmd):
    return subprocess.run(cmd,check=False).returncode

def main(argv=None):
    parser=argparse.ArgumentParser(add_help=False)
    parser.add_argument('command',nargs='?',default='help')
    parser.add_argument('--force',action='store_true')
    parser.add_argument('--json',action='store_true',help='JSON for zfsm capacity only')
    parser.add_argument('--lang',choices=('de','en'))
    parser.add_argument('-h','--help',action='store_true',dest='show_help')
    args=parser.parse_args(argv)
    t=language(args.lang)
    if args.show_help or args.command=='help':
        print(f'{t["heading"]} {VERSION}\n{t["usage"]}: zfsm <command> [--force] [--json] [--lang de|en]\n\n{t["commands"]}:')
        for cmd in HELP_COMMANDS:
            print(f'  zfsm {cmd:<14} {t[cmd]}')
        print(f'  zfsm repair --force  {t["force"]}')
        return 0
    if args.command not in HELP_COMMANDS:
        parser.print_usage(sys.stderr); return 2
    if (args.force and args.command!='repair') or (args.json and args.command!='capacity'):
        parser.print_usage(sys.stderr);return 2
    if args.command=='capacity':
        from zfsm_capacity import AuditError, collect_report
        try:
            report=collect_report()
        except (AuditError, OSError, subprocess.TimeoutExpired, ValueError) as exc:
            print(t['error']+': '+str(exc),file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(report,sort_keys=True,ensure_ascii=False))
            return 0
        def b(n):
            n=float(n)
            for unit in ('B','KiB','MiB','GiB','TiB','PiB'):
                if n < 1024 or unit=='PiB': return f'{n:.1f} {unit}'
                n/=1024
        for pool in report['pools']:
            label='WARNUNG' if pool['level']=='warning' else 'KRITISCH' if pool['level']=='critical' else 'OK'
            if t is EN: label='WARNING' if pool['level']=='warning' else 'CRITICAL' if pool['level']=='critical' else 'OK'
            print(f"{pool['name']}: {pool['capacity_percent']}%  {label}, " +
                  f"{b(pool['free'])} {'frei' if t is DE else 'free'}")
        print(f"{report['total_snapshots']} Snapshots; " +
              f"{b(report['snapshot_used_total_bytes'])} " +
              ('Snapshot-Verbrauch (keine Freigabeprognose)' if t is DE else 'snapshot used (not a reclaim forecast)'))
        for item in report['top_datasets'][:5]:
            print(f"  {item['dataset']}: {item['snapshots']} snap, {b(item['snapshot_used_bytes'])}")
        return 0
    if args.command=='version':
        print(f'{t["heading"]}: {VERSION}')
        return run(['pveversion'])
    if args.command=='update-check':
        return run(['dpkg-query','-W','pve-zfs-manager'])
    if args.command in ('logs','services'):
        if args.command=='logs':
            return run(['journalctl','-u','pve-zfs-manager-reconcile.service','-n','35','--no-pager'])
        units=('pve-zfs-manager-reconcile.path','pve-zfs-manager-reconcile.timer')
        labels=('Dateiwächter','Automatischer Timer') if t is DE else ('File watcher','Automatic timer')
        good=True
        for label,unit in zip(labels,units):
            active=subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True,check=False).stdout.strip()
            enabled=subprocess.run(['systemctl','is-enabled',unit],capture_output=True,text=True,check=False).stdout.strip()
            print(f'{label}: {active} ({enabled})')
            good=good and active=='active' and enabled=='enabled'
        print(('Gesamtstatus: OK' if good else 'Gesamtstatus: PRÜFEN') if t is DE else ('Overall: OK' if good else 'Overall: CHECK'))
        return 0 if good else 1
    if args.command in ('backups','restore'):
        root=Path('/var/lib/pve-zfs-manager/backups')
        entries=sorted((p for p in root.iterdir() if p.is_dir() and not p.is_symlink()),reverse=True) if root.is_dir() else []
        for p in entries[:30]:print(p.name)
        if not entries:print(t['no_backup'])
        if args.command=='restore':print(t['restore_note'])
        return 0 if args.command=='backups' else 2
    if args.command=='backup':
        if os.geteuid()!=0:print(t['error']+': root required',file=sys.stderr);return 1
        inst=universal.Installer()
        try:
            inst.check(allow_missing_dependencies=True)
            import datetime, secrets
            label='manual-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3)
            _, folder=inst.snapshot({'gui':inst.gui,'nodes':inst.nodes,'api':inst.api,'policy':inst.policy},label)
            print(t['snapshot'],folder);return 0
        except (universal.InstallError,OSError) as exc:
            print(t['error']+': '+str(exc),file=sys.stderr);return 1
    if args.command=='repair' and args.force:
        print(t['warning'])
        if not sys.stdin.isatty() or input(t['confirm']).strip().lower() not in ('j','ja','y','yes'):
            print(t['cancel']);return 1
    return run(['/usr/sbin/pve-zfs-manager', 'status' if args.command=='status' else 'check' if args.command=='check' else 'repair-force' if args.force else 'repair'])

if __name__=='__main__':sys.exit(main())
