#!/usr/bin/env python3
"""Small, reversible Proxmox 9.2.21 node menu smoke test.

No API, ZFS calls, daemons, proxmox restarts, index.html.tpl changes or monkeypatching.
"""
import argparse
import datetime
import hashlib
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile

PVE_JS = Path('/usr/share/pve-manager/js/pvemanagerlib.js')
INDEX_TPL = Path('/usr/share/pve-manager/index.html.tpl')
NODES_PM = Path('/usr/share/perl5/PVE/API2/Nodes.pm')
BACKUP_ROOT = Path('/root/pve-zfs-navtest-backups')
NODE_CLASS = "Ext.define('PVE.node.Config', {"
ANCHOR = """        if (caps.nodes['Sys.Audit']) {
            me.items.push(
                {
                    xtype: 'proxmoxNodeServiceView',"""
BEGIN = '        // BEGIN PVE-ZFS-MANAGER-NAVTEST-v0.4.0a\n'
END = '        // END PVE-ZFS-MANAGER-NAVTEST-v0.4.0a\n'
BLOCK = (
    BEGIN +
    """        // Node-only, static ExtJS panel. This does not call the backend or touch ZFS.
        if (caps.nodes['Sys.Audit']) {
            me.items.push({
                xtype: 'panel',
                title: 'ZFS Manager (Test)',
                iconCls: 'fa fa-database',
                itemId: 'zfsmanager-navtest',
                bodyPadding: 24,
                html: '<h2>ZFS Manager - Navigationstest</h2><p>Menue und Inhaltsbereich sind verbunden.</p><p>Keine ZFS-Funktionen aktiv. Kein Zugriff auf Snapshots.</p>',
            });
        }
""" + END
)


def hash_bytes(data):
    return hashlib.sha256(data).hexdigest()


def source_scope(text):
    start = text.find(NODE_CLASS)
    if start == -1 or text.count(NODE_CLASS) != 1:
        raise RuntimeError('PVE.node.Config nicht eindeutig gefunden')
    stop = text.find('\nExt.define(', start + len(NODE_CLASS))
    if stop == -1:
        raise RuntimeError('Ende von PVE.node.Config nicht gefunden')
    return start, stop


def modify(text):
    if BEGIN in text or END in text:
        raise RuntimeError('Navigationstest ist bereits eingebaut')
    start, stop = source_scope(text)
    scope = text[start:stop]
    if scope.count(ANCHOR) != 1:
        raise RuntimeError('System-Menueanker nicht eindeutig; Installation verweigert')
    shell_marker = "itemId: 'jsconsole'"
    i = scope.find(shell_marker)
    j = scope.find(ANCHOR)
    if i == -1 or not (i < j and j - i < 2000):
        raise RuntimeError('Shell/System-Abfolge unerwartet; Installation verweigert')
    return text[:start] + scope.replace(ANCHOR, BLOCK + ANCHOR, 1) + text[stop:]


def remove(text):
    if text.count(BLOCK) != 1:
        raise RuntimeError('Eingebauter Testblock fehlt oder ist veraendert; keine automatische Ruecknahme')
    return text.replace(BLOCK, '', 1)


def hostcheck():
    if os.geteuid() != 0:
        raise RuntimeError('Nur als root auf dem Test-Proxmox ausfuehren')
    if subprocess.run(['hostname', '-s'], capture_output=True, text=True, check=True).stdout.strip() != 'pve':
        raise RuntimeError('Nur auf Testknoten mit Hostname pve erlaubt')
    version = subprocess.run(['pveversion'], capture_output=True, text=True, check=True).stdout.strip()
    if not version.startswith('pve-manager/9.2.21/'):
        raise RuntimeError('Nur fuer pve-manager 9.2.21 freigegeben: ' + version)
    if not PVE_JS.is_file() or PVE_JS.is_symlink():
        raise RuntimeError('Proxmox-JavaScript-Datei fehlt oder ist ein Symlink')
    if INDEX_TPL.is_file() and 'pve-zfs-manager.js' in INDEX_TPL.read_text(errors='replace'):
        raise RuntimeError('Alte ZFS-Manager-GUI noch vorhanden')
    if NODES_PM.is_file() and "path => 'zfsmanager'" in NODES_PM.read_text(errors='replace'):
        raise RuntimeError('Alte ZFS-Manager-API noch vorhanden')
    return version


def write_atomic(path, data):
    old = path.stat()
    fd, tempname = tempfile.mkstemp(prefix='.pve-zfs-navtest-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tempname, stat.S_IMODE(old.st_mode))
        os.chown(tempname, old.st_uid, old.st_gid)
        os.replace(tempname, path)
    finally:
        if os.path.exists(tempname):
            os.unlink(tempname)


def run(command):
    ver = hostcheck()
    oldbytes = PVE_JS.read_bytes()
    text = oldbytes.decode('utf-8')
    if command == 'check':
        changed = modify(text)
        if changed.replace(BLOCK, '', 1) != text:
            raise RuntimeError('Interner Einfuegetest fehlgeschlagen')
        print('PASS: ', ver)
        print('PASS: Eindeutiger Einhaengepunkt zwischen Shell und System')
        print('PASS: Patch wieder verlustfrei entfernbar')
        print('PASS: Keine Systemdatei geaendert, keine Dienste neu gestartet')
    elif command == 'install':
        changed = modify(text).encode('utf-8')
        base = BACKUP_ROOT / datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        base.mkdir(parents=True, exist_ok=False)
        backup = base / 'pvemanagerlib.js.original'
        shutil.copy2(PVE_JS, backup)
        (base / 'original.sha256').write_text(hash_bytes(oldbytes) + '  pvemanagerlib.js.original\n')
        write_atomic(PVE_JS, changed)
        if PVE_JS.read_bytes() != changed:
            write_atomic(PVE_JS, oldbytes)
            raise RuntimeError('Nachkontrolle fehlgeschlagen; urspruengliche Datei restauriert')
        print('Installiert: Nur statischer Menue-/Inhaltstest auf Host pve.')
        print('Originalbackup:', backup)
        print('Proxmox-Dienste wurden NICHT neu gestartet.')
        print('Browser: https://<proxmox-host>:8006 (Hard-Refresh/privates Fenster).')
        print('Bei Anzeigefehlern sofort: bash install.sh --rollback')
    elif command == 'remove':
        changed = remove(text).encode('utf-8')
        write_atomic(PVE_JS, changed)
        print('Testmenue entfernt. Alle anderen Inhalte der Datei erhalten.')
        print('Backups bleiben erhalten:', BACKUP_ROOT)
        print('Browser hart neu laden. Keine Dienste neu gestartet.')
    else:
        raise RuntimeError('Unbekannter Modus')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['check', 'install', 'remove'])
    args = parser.parse_args()
    try:
        run(args.command)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print('ABBRUCH:', exc, file=sys.stderr)
        sys.exit(1)
