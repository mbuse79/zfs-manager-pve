#!/usr/bin/env python3
"""Interactive, backed-up de-duplication of *cron entries*, never ZFS snapshots.

Used by the ZIP installer before dpkg. Fail closed if no TTY or unsupported
cron source. No cron edits are performed without explicit per-label choice and
an additional confirmation. Replication services are outside this module.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import secrets
import stat
import sys
import tempfile
from pathlib import Path

import zfsm_host_audit as audit

MARKER = '# ZFSM-AUTOSNAP-DUPLICATE-DISABLED '
BACKUPS = '/var/lib/pve-zfs-manager/autosnap-conflict-backups'
MAX_BYTES = audit.MAX_FILE_BYTES

class ConflictError(Exception):
    pass


def _hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _ask_tty():
    """Read /dev/tty even when bash runs from a heredoc on a PVE console."""
    try:
        tty = open('/dev/tty', 'r+', encoding='utf-8', buffering=1)
    except OSError as exc:
        raise ConflictError('Keine interaktive Konsole verfügbar. Keine Änderungen.\n'
                            'Installer direkt in einer Proxmox-Shell starten.') from exc
    return tty


def _safe_path(root: Path, source: str) -> Path:
    if not source.startswith('/') or source.startswith('//') or '..' in Path(source).parts:
        raise ConflictError('Unsichere Cron-Dateiquelle')
    rel = Path(source).relative_to('/')
    parts = rel.parts
    allowed = (parts[:2] == ('etc','cron.d') and len(parts) == 3 or
               len(parts) == 3 and parts[:2] in (('etc','cron.hourly'),('etc','cron.daily'),
                   ('etc','cron.weekly'),('etc','cron.monthly'),('etc','cron.yearly')) or
               parts == ('etc','crontab'))
    if not allowed: raise ConflictError('Cron-Quelle nicht automatisch änderbar: '+source)
    path = root / rel
    if path.is_symlink() or not path.is_file():
        raise ConflictError('Fehlende oder verlinkte Cron-Datei: '+source)
    # Check every directory component for symlinks (e.g. a substituted cron.d).
    cur = root
    for comp in parts[:-1]:
        cur = cur / comp
        if cur.is_symlink():raise ConflictError('Verlinktes Cron-Verzeichnis: '+source)
    meta = path.stat()
    if not stat.S_ISREG(meta.st_mode) or meta.st_size > MAX_BYTES:
        raise ConflictError('Ungeeignete/zu große Cron-Datei: '+source)
    if root == Path('/') and (meta.st_uid != 0 or meta.st_mode & 0o022):
        raise ConflictError('Unsichere Eigentums-/Schreibrechte: '+source)
    return path


def _replace(path: Path, data: bytes, original_stat):
    fd, tmp = tempfile.mkstemp(prefix='.zfsm-autosnap-', dir=str(path.parent))
    try:
        with os.fdopen(fd,'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp,stat.S_IMODE(original_stat.st_mode))
        if os.geteuid() == 0:os.chown(tmp,original_stat.st_uid,original_stat.st_gid)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)


def _validate_entry(line: str, entry: dict):
    if line.lstrip().startswith('#') or not audit.autosnap_invocation(line):
        raise ConflictError('AutoSnap-Regel hat sich seit der Erkennung verändert: '+entry['source'])
    match_label = audit.LABEL_RE.search(line)
    match_keep = audit.KEEP_RE.search(line)
    label = match_label.group(1) if match_label else 'unknown'
    keep = int(match_keep.group(1)) if match_keep else None
    if label != entry['label'] or keep != entry['keep']:
        raise ConflictError('AutoSnap-Regel hat sich verändert: '+entry['source'])


def _plan(root: Path, selected: list[dict]):
    """Pure inspection: calculate entire-file edits, no modifications."""
    changes = {}
    for entry in selected:
        source = entry['source']
        if source == 'root crontab':
            # We do not replace /var/spool/cron directly or silently alter crontab.
            raise ConflictError('Root-Crontab-Konflikt: nicht automatisch änderbar; manuelle Prüfung nötig.')
        path = _safe_path(root,source)
        if source not in changes:
            raw = path.read_bytes()
            if b'\x00' in raw:raise ConflictError('Binärdaten in Cron-Datei: '+source)
            try: txt = raw.decode('utf-8')
            except UnicodeDecodeError as exc: raise ConflictError('Cron-Datei nicht UTF-8: '+source) from exc
            changes[source] = {'path':path,'before':raw,'stat':path.stat(),
                               'lines':txt.splitlines(keepends=True),'disabled':set()}
        change = changes[source]
        lineno = entry['line']
        if not isinstance(lineno,int) or not (1 <= lineno <= len(change['lines'])):
            raise ConflictError('Zeilennummer ungültig: '+source)
        line = change['lines'][lineno-1]
        _validate_entry(line,entry)
        change['disabled'].add(lineno)
    for source,change in changes.items():
        new_lines = list(change['lines'])
        for lineno in sorted(change['disabled']):
            new_lines[lineno-1] = MARKER + new_lines[lineno-1]
        change['after'] = ''.join(new_lines).encode('utf-8')
        if change['after'] == change['before']:raise ConflictError('Keine Änderungen errechnet')
    return changes


def _backup_and_apply(root: Path, changes: dict, backup_dir: Path|None=None):
    """Persist backups before modifying any cron config, rollback on error."""
    home = backup_dir or (root / BACKUPS.lstrip('/'))
    if home.is_symlink() or (home.exists() and not home.is_dir()):
        raise ConflictError('Sicherungsverzeichnis ist kein reguläres Verzeichnis')
    home.mkdir(parents=True,mode=0o700,exist_ok=True)
    if root == Path('/') and (home.stat().st_uid != 0 or home.stat().st_mode & 0o077):
        raise ConflictError('Sicherungsverzeichnis hat unsichere Rechte')
    label=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(4)
    job=home/label
    job.mkdir(mode=0o700)
    manifest=[]
    for index,(source,item) in enumerate(sorted(changes.items())):
        backup=job/('file-%02d.orig' % index)
        backup.write_bytes(item['before'])
        backup.chmod(0o600)
        manifest.append({'source':source,'file':backup.name,
                         'before_sha256':_hash(item['before']),
                         'after_sha256':_hash(item['after']),
                         'disabled_lines':sorted(item['disabled'])})
    state=job/'manifest.json'
    state.write_text(json.dumps({'schema':1,'files':manifest},ensure_ascii=False,indent=2)+'\n')
    state.chmod(0o600)
    touched=[]
    try:
        for source,item in sorted(changes.items()):
            # Re-check immediately before replacing to prevent overwriting changes
            # made concurrently by the administrator or the package manager.
            path=_safe_path(root,source)
            if _hash(path.read_bytes()) != _hash(item['before']):
                raise ConflictError('Cron-Datei zwischenzeitlich verändert: '+source)
            _replace(path,item['after'],item['stat'])
            touched.append((path,item))
    except Exception as exc:
        for path,item in reversed(touched):
            try:
                if _hash(path.read_bytes()) == _hash(item['after']):
                    _replace(path,item['before'],item['stat'])
            except Exception as rollback_exc:
                print('WARNUNG: Automatischer Rückbau fehlgeschlagen bei '+str(path)+': '+str(rollback_exc),file=sys.stderr)
        raise ConflictError('Änderung abgebrochen; Sicherung: '+str(job)+'; Grund: '+str(exc)) from exc
    return job


def _get_choice(ask, prompt, choices):
    answer=ask(prompt).strip().lower()
    if answer not in choices:raise ConflictError('Keine gültige Auswahl; nichts verändert.')
    return answer


def resolve_conflicts(*, root='/', report=None, ask=None, output=print, backup_dir=None):
    """Explicit per-label selection + second confirmation before reversible edits."""
    root=Path(root)
    if root == Path('/') and os.geteuid()!=0:raise ConflictError('Root-Rechte erforderlich')
    report=report if report is not None else audit.discover(root=root)
    rows=report['autosnap']['schedules']
    duplicates=report['autosnap']['duplicate_labels']
    unknown=[s for s in rows if s['label']=='unknown' or s['keep'] is None]
    if not duplicates and not unknown:
        output('PASS: Keine doppelten oder unklaren AutoSnap-Aufträge; keine Änderung nötig.')
        return None
    if ask is None:
        tty=_ask_tty()
        def ask(prompt):
            from cli_locale import english
            tty.write(english(prompt) if os.environ.get('ZFSM_CLI_LANG')=='en' else prompt)
            return tty.readline()
    selected=[]
    output('AutoSnap-Konflikte erkannt: Nur Cron-Regeln werden nach Auswahl deaktiviert.')
    output('Vorher wird eine Sicherung erstellt. Snapshots und Replikationen bleiben unangetastet.')
    for label in duplicates:
        group=[s for s in rows if s['label']==label]
        output('\nDoppelte Aufbewahrungsart: '+label)
        for n,s in enumerate(group,1):
            output(f"  {n}) {s['source']}:{s['line']} | behalte {s['keep']}" +
                   (' | Standard' if s['standard'] else ' | Benutzerregel'))
        output('  0) Abbrechen (nichts ändern)')
        ans=_get_choice(ask,'Welche Regel behalten? [0-'+str(len(group))+']: ',
                        {str(i) for i in range(len(group)+1)})
        if ans=='0':raise ConflictError('Vom Administrator abgebrochen; nichts verändert.')
        selected.extend(s for i,s in enumerate(group,1) if i != int(ans))
    if unknown:
        output('\nNicht eindeutig identifizierte AutoSnap-Aufträge:')
        for s in unknown:
            output(f"  {s['source']}:{s['line']} | Art: {s['label']}, Aufbewahrung: {s['keep']}")
            ans=_get_choice(ask,'Diesen unklaren Auftrag deaktivieren? [d=ja / a=abbrechen]: ',{'d','a'})
            if ans=='a':raise ConflictError('Unbekannte Regel bleibt bestehen; keine Änderung.')
            selected.append(s)
    changes=_plan(root,selected)  # validate all files before asking confirmation
    output('\nVorgesehene Änderungen: '+str(len(selected))+' AutoSnap-Regel(n) in '+str(len(changes))+' Datei(en) deaktivieren.')
    for src in sorted(changes):output('  '+src)
    answer=_get_choice(ask,'Jetzt mit Sicherung deaktivieren? [JA/N]: ',{'ja','n'})
    if answer != 'ja':raise ConflictError('Nicht bestätigt; nichts verändert.')
    folder=_backup_and_apply(root,changes,backup_dir=backup_dir)
    output('PASS: Duplikate deaktiviert; Sicherung: '+str(folder))
    # Rescan, checking that intended duplicate/unknown entries vanished.
    again=audit.discover(root=root)
    if again['autosnap']['duplicate_labels'] or any(s['label']=='unknown' or s['keep'] is None for s in again['autosnap']['schedules']):
        raise ConflictError('Nachprüfung meldet weitere Konflikte. Sicherung: '+str(folder))
    return folder



def backup_list(root='/'):
    home=Path(root)/BACKUPS.lstrip('/')
    if not home.is_dir() or home.is_symlink():return []
    return [p.name for p in sorted(home.iterdir(),reverse=True)
            if p.is_dir() and not p.is_symlink() and
            re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{8}',p.name)][:30]


def restore_backup(name, *, root='/', ask=None, output=print):
    """Undo only our own exact edits. Stop if an admin changed the file since."""
    if not re.fullmatch(r'\d{8}T\d{6}Z-[a-f0-9]{8}',name):
        raise ConflictError('Ungültiger Sicherungsname')
    root=Path(root)
    if root == Path('/') and os.geteuid()!=0:raise ConflictError('Root-Rechte erforderlich')
    base=root/BACKUPS.lstrip('/')
    job=base/name
    if base.is_symlink() or job.is_symlink() or not job.is_dir():
        raise ConflictError('Sicherung nicht gefunden oder verlinkt')
    manifest=job/'manifest.json'
    if manifest.is_symlink() or not manifest.is_file():
        raise ConflictError('Sicherungsmanifest fehlt')
    data=json.loads(manifest.read_text())
    if data.get('schema')!=1 or not isinstance(data.get('files'),list) or not data['files']:
        raise ConflictError('Sicherungsmanifest ungültig')
    changes={}
    for entry in data['files']:
        source=entry['source']
        if not isinstance(entry.get('file'),str) or not re.fullmatch(r'file-\d{2}\.orig',entry['file']):
            raise ConflictError('Sicherungsdatei ungültig')
        path=_safe_path(root,source)
        oldfile=job/entry['file']
        if oldfile.is_symlink() or not oldfile.is_file():raise ConflictError('Sicherung fehlt')
        raw=oldfile.read_bytes()
        current=path.read_bytes()
        if _hash(raw)!=entry['before_sha256'] or _hash(current)!=entry['after_sha256']:
            raise ConflictError('Cron-Datei seit Bereinigung geändert; sicherer Rückbau gestoppt: '+source)
        changes[source]={'path':path,'before':current,'after':raw,'stat':path.stat()}
    output('Sicherung: '+name)
    for source in sorted(changes):output('  Wiederherstellen: '+source)
    if ask is None:
        tty=_ask_tty()
        def ask(prompt):
            from cli_locale import english
            tty.write(english(prompt) if os.environ.get('ZFSM_CLI_LANG')=='en' else prompt)
            return tty.readline()
    if _get_choice(ask,'Originale Cron-Regeln wiederherstellen? [JA/N]: ',{'ja','n'})!='ja':
        raise ConflictError('Rückbau nicht bestätigt; nichts verändert')
    touched=[]
    try:
        for source,item in sorted(changes.items()):
            path=_safe_path(root,source)
            if _hash(path.read_bytes())!=_hash(item['before']):
                raise ConflictError('Datei geändert während des Rückbaus: '+source)
            _replace(path,item['after'],item['stat'])
            touched.append((path,item))
    except Exception as exc:
        for path,item in reversed(touched):
            try:
                if _hash(path.read_bytes())==_hash(item['after']):
                    _replace(path,item['before'],item['stat'])
            except OSError as rollback_exc:
                print('WARNUNG: Rückbau des Rückbaus fehlgeschlagen: '+str(rollback_exc),file=sys.stderr)
        raise ConflictError('Rückbau fehlgeschlagen: '+str(exc)) from exc
    output('PASS: Originale Cron-Konfiguration aus '+name+' wiederhergestellt')


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description='AutoSnap-Konflikte mit Auswahl und Sicherung auflösen')
    parser.add_argument('mode',choices=('resolve','backups','restore'))
    parser.add_argument('backup_id',nargs='?')
    args=parser.parse_args(argv)
    try:
        if args.mode=='resolve':
            if args.backup_id:raise ConflictError('Keine Sicherungs-ID bei resolve angeben')
            resolve_conflicts(output=print)
        elif args.mode=='backups':
            if args.backup_id:raise ConflictError('Keine Sicherungs-ID bei backups angeben')
            for name in backup_list():print(name)
        else:
            if not args.backup_id:raise ConflictError('Aufruf: zfsm autosnap restore SICHERUNGS-ID')
            restore_backup(args.backup_id,output=print)
        return 0
    except (ConflictError,OSError,ValueError) as exc:
        print('STOPP: '+str(exc),file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
