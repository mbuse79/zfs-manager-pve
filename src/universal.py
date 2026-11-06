#!/usr/bin/env python3
"""PVE ZFS Manager integration installer (stable release, fail-closed).

This file does not run any `zfs` writes. Supports 9.1.1 stock install,
9.2.21, and adopting an unchanged v1.0.0-rc2 installation.
"""
import hashlib
import fcntl
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

import manager_patch
import manager_patch_v1_12
import manager_patch_v1_2
import manager_patch_v1_10
import manager_patch_v1_8
import manager_patch_v1_7
import manager_patch_v1_6
import manager_patch_v1_5
import manager_patch_v1_4
import manager_patch_rc7
import manager_patch_rc8
import manager_patch_rc8r2
import manager_patch_rc9
import manager_patch_rc5
import manager_patch_rc6
import previous_patch
import patch_nav

VERSION = '1.0.0-32-dynamic-compat-installer'
COMPATIBLE = re.compile(r'^pve-manager/(?:9\.[0-9]+\.[0-9]+)/')
# SHA256 of stock 9.1.1 files reported by the fresh pvetest2 node on 2026-10-23.
# Guard against unexpected customizations despite compatible-looking navigation anchors.
STOCK_911 = {
    'gui': '5dc4993b0647911c21b4ce1bf2dc2fbc1fde42a56d3ef3c5b9835b2512aee4c7',
    'nodes': 'eca4584ffcd1e812c3d516ca00ee1d352f56c8c4422d5bd232ba84ae2c7cdb99',
}
ROUTE = "__PACKAGE__->register_method({\n    subclass => \"PVE::API2::ZFSSnapshotViewer\",\n    path => 'zfsmanager-ro',\n});\n"
IMPORT = 'use PVE::API2::ZFSSnapshotViewer;\n'
ROUTE_BEGIN = '# BEGIN PVE-ZFS-MANAGER-ROUTE\n'
ROUTE_END = '# END PVE-ZFS-MANAGER-ROUTE\n'
IMPORT_BEGIN = '# BEGIN PVE-ZFS-MANAGER-IMPORT\n'
IMPORT_END = '# END PVE-ZFS-MANAGER-IMPORT\n'
JS_INSERT = previous_patch.HELPERS + manager_patch.BLOCK
V1_12_JS_INSERT = previous_patch.HELPERS + manager_patch_v1_12.BLOCK
V1_10_JS_INSERT = previous_patch.HELPERS + manager_patch_v1_10.BLOCK
V1_2_JS_INSERT = previous_patch.HELPERS + manager_patch_v1_2.BLOCK
V1_8_JS_INSERT = previous_patch.HELPERS + manager_patch_v1_8.BLOCK
V1_7_JS_INSERT = previous_patch.HELPERS + manager_patch_v1_7.BLOCK
V1_6_JS_INSERT = previous_patch.HELPERS + manager_patch_v1_6.BLOCK
V1_5_JS_INSERT = previous_patch.HELPERS + manager_patch_v1_5.BLOCK
V1_4_JS_INSERT = previous_patch.HELPERS + manager_patch_v1_4.BLOCK
RC9_JS_INSERT = previous_patch.HELPERS + manager_patch_rc9.BLOCK
RC8R2_JS_INSERT = previous_patch.HELPERS + manager_patch_rc8r2.BLOCK
RC8_JS_INSERT = previous_patch.HELPERS + manager_patch_rc8.BLOCK
RC7_JS_INSERT = previous_patch.HELPERS + manager_patch_rc7.BLOCK
RC6_JS_INSERT = previous_patch.HELPERS + manager_patch_rc6.BLOCK
OLD_JS_INSERT = previous_patch.HELPERS + manager_patch_rc5.BLOCK

class InstallError(RuntimeError):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Installer:
    def __init__(self, root='/', source=None, test_version=None, dry_system=False):
        self.root=Path(root)
        self.source=Path(source or Path(__file__).resolve().parent)
        self.test_version=test_version
        self.dry_system=dry_system
        self.gui=self.path('/usr/share/pve-manager/js/pvemanagerlib.js')
        self.nodes=self.path('/usr/share/perl5/PVE/API2/Nodes.pm')
        self.api=self.path('/usr/share/perl5/PVE/API2/ZFSSnapshotViewer.pm')
        self.policy=self.path('/usr/local/libexec/pve-zfs-manager/guest_policy.py')
        self.yearly=self.path('/etc/cron.d/pve-zfs-manager-yearly')
        self.admindir=self.path('/etc/pve-zfs-manager')
        self.admin=self.admindir/'admins.conf'
        self.secret=self.admindir/'preview.key'
        self.state_dir=self.path('/var/lib/pve-zfs-manager')
        self.state_file=self.state_dir/'state.json'
        self.backup_root=self.state_dir/'backups'
    def path(self, name):
        return self.root/name.lstrip('/')
    def version(self):
        if self.test_version is not None: return self.test_version
        cmd=subprocess.run(['pveversion'],capture_output=True,text=True)
        if cmd.returncode: raise InstallError('pveversion fehlt oder ist fehlerhaft: Kein Proxmox VE')
        return cmd.stdout.strip()
    def prerequisites(self, check_dependencies=True):
        if self.root==Path('/') and os.geteuid()!=0:
            raise InstallError('Installation erfordert root-Rechte')
        version=self.version()
        if not COMPATIBLE.match(version):
            raise InstallError('Nicht unterstützte Hauptversion von Proxmox VE: '+version)
        for path in (self.gui,self.nodes): self.read(path)
        if check_dependencies and self.root==Path('/'):
            for exe in ('zfs','zpool','zfs-auto-snapshot','python3','perl','systemctl'):
                if shutil.which(exe) is None: raise InstallError('Voraussetzung fehlt: '+exe)
            for f in ('/etc/cron.d/zfs-auto-snapshot','/etc/cron.hourly/zfs-auto-snapshot', '/etc/cron.daily/zfs-auto-snapshot','/etc/cron.weekly/zfs-auto-snapshot','/etc/cron.monthly/zfs-auto-snapshot'):
                if not self.path(f).is_file(): raise InstallError('Cron-Regel fehlt: '+f)
        return version
    @staticmethod
    def read(path):
        if path.is_symlink() or not path.is_file(): raise InstallError('Datei fehlt oder ist Symlink: '+str(path))
        return path.read_bytes()
    @staticmethod
    def validate_normal_file(path):
        if path.is_symlink(): raise InstallError('Symlink nicht erlaubt: '+str(path))
        if path.exists() and not path.is_file(): raise InstallError('Kein reguläres File: '+str(path))
    def expected(self):
        return self.read(self.source/'PVE/API2/ZFSSnapshotViewer.pm'),self.read(self.source/'libexec/guest_policy.py')
    def v1_10_policy(self):
        return self.read(self.source/'libexec/guest_policy_v1_10.py')
    def rc9_policy(self):
        return self.read(self.source/'libexec/guest_policy_rc9.py')
    def v1_6_api(self):
        return self.read(self.source/'PVE/API2/ZFSSnapshotViewer_v1_6.pm')
    def v1_5_api(self):
        return self.read(self.source/'PVE/API2/ZFSSnapshotViewer_v1_5.pm')
    def v1_4_api(self):
        return self.read(self.source/'PVE/API2/ZFSSnapshotViewer_v1_4.pm')
    def rc9_api(self):
        return self.read(self.source/'PVE/API2/ZFSSnapshotViewer_rc9.pm')
    def rc8r2_api(self):
        return self.read(self.source/'PVE/API2/ZFSSnapshotViewer_rc8r2.pm')
    def rc7_api(self):
        return self.read(self.source/'PVE/API2/ZFSSnapshotViewer_rc7.pm')
    def rc6_api(self):
        return self.read(self.source/'PVE/API2/ZFSSnapshotViewer_rc6.pm')
    def owned_gui_drift_span(self, gui):
        """Identify our bounded injected GUI block after local drift.

        Never adopt an unregistered installation or arbitrary content outside
        the two exact markers; require both markers once inside node scope.
        """
        if not self.state() or not self.state().get('installed_hashes'):
            return None
        begin='        // BEGIN PVE-ZFS-MANAGER-READONLY-HELPERS-v0.4.0b\n'
        end='        // END PVE-ZFS-MANAGER-READONLY-v1.0.0-rc9\n'
        if gui.count(begin)!=1 or gui.count(end)!=1:
            return None
        start=gui.index(begin)
        stop=gui.index(end)+len(end)
        if start>=stop or stop-start>300_000:
            return None
        scope_start,scope_end=patch_nav.source_scope(gui)
        if not(scope_start<=start<stop<=scope_end):
            return None
        block=gui[start:stop]
        # Structural ownership markers cannot be taken from unrelated JS.
        if block.count('PVE-ZFS-MANAGER-READONLY')!=4:
            return None
        if block.count('zfsmanager-readonly')<1:
            return None
        clean=gui[:start]+gui[stop:]
        if 'PVE-ZFS-MANAGER' in clean or 'zfsmanager-readonly' in clean:
            return None
        try:
            patch_nav.modify(clean)
        except (RuntimeError,ValueError):
            return None
        return start,stop

    def classify(self):
        gui=self.read(self.gui).decode('utf-8')
        nodes=self.read(self.nodes).decode('utf-8')
        if gui.count(JS_INSERT)==1:
            gui_state='rc9'
        elif gui.count(V1_12_JS_INSERT)==1:
            gui_state='v1_12'
        elif gui.count(V1_10_JS_INSERT)==1:
            gui_state='v1_10'
        elif gui.count(V1_8_JS_INSERT)==1:
            gui_state='v1_8'
        elif gui.count(V1_7_JS_INSERT)==1:
            gui_state='v1_7'
        elif gui.count(V1_6_JS_INSERT)==1:
            gui_state='v1_6'
        elif gui.count(V1_5_JS_INSERT)==1:
            gui_state='v1_5'
        elif gui.count(V1_4_JS_INSERT)==1:
            gui_state='v1_4'
        elif gui.count(V1_2_JS_INSERT)==1:
            gui_state='v1_2'
        elif gui.count(RC9_JS_INSERT)==1:
            gui_state='rc9old'
        elif gui.count(RC8R2_JS_INSERT)==1:
            gui_state='rc8r2'
        elif gui.count(RC8_JS_INSERT)==1:
            gui_state='rc8'
        elif gui.count(RC7_JS_INSERT)==1:
            gui_state='rc7'
        elif gui.count(RC6_JS_INSERT)==1:
            gui_state='rc6'
        elif gui.count(OLD_JS_INSERT)==1:
            gui_state='rc5'
        elif self.owned_gui_drift_span(gui) is not None:
            gui_state='owned-drift'
        elif 'PVE-ZFS-MANAGER' in gui or 'zfsmanager-readonly' in gui:
            raise InstallError('Unbekannte/ältere GUI-Erweiterung vorhanden; manuelle Migration erforderlich')
        else:
            # Verify exact unmodified shell/system insertion structure.
            try:
                patch_nav.modify(gui)
            except (RuntimeError,ValueError) as ex:
                raise InstallError('Proxmox GUI-Struktur unbekannt: '+str(ex))
            gui_state='clean'
        if nodes.count("path => 'zfsmanager-ro'")==1:
            node_state='present'
            if nodes.count('subclass => "PVE::API2::ZFSSnapshotViewer"')!=1 or nodes.count(IMPORT.strip())!=1:
                raise InstallError('ZFS-API-Route vorhanden, aber Format nicht bekannt')
        elif "zfsmanager-ro" in nodes or 'PVE-ZFS-MANAGER-ROUTE' in nodes:
            raise InstallError('Unbekannte API-Route vorhanden')
        else:
            self.add_route(nodes)  # throws on unknown structure
            node_state='clean'
        return gui_state,node_state
    def verify_911_originals(self, version, gui_state, node_state):
        # A stock 9.1.1 file may be independently replaced by a package update.
        # Verify every clean file, including partly overwritten integrations.
        if version.startswith('pve-manager/9.1.1/'):
            wanted=getattr(self,'stock_911',STOCK_911)
            for label,mode,path in (('gui',gui_state,self.gui),
                                    ('nodes',node_state,self.nodes)):
                if mode=='clean' and sha(self.read(path))!=wanted[label]:
                    raise InstallError('9.1.1 '+label+
                                       ' hat nicht die geprüfte Original-Prüfsumme; Abbruch')
    def precheck(self):
        version, gui, node = self.check(allow_missing_dependencies=True)
        print('PASS: PVE-Integrationsstruktur und Versionsschutz: '+version+' | GUI: '+gui+' | API: '+node)
        return version, gui, node
    def add_gui(self, src):
        start,stop=patch_nav.source_scope(src)
        scope=src[start:stop]
        if scope.count(patch_nav.ANCHOR)!=1 or "itemId: 'jsconsole'" not in scope:
            raise InstallError('Unbekannte Knotenmenü-Struktur')
        if scope.find("itemId: 'jsconsole'")>scope.find(patch_nav.ANCHOR):
            raise InstallError('Shell/System-Reihenfolge unerwartet')
        if 'PVE-ZFS-MANAGER' in src: raise InstallError('ZFS Manager schon eingebunden')
        return src[:start]+scope.replace(patch_nav.ANCHOR,JS_INSERT+patch_nav.ANCHOR,1)+src[stop:]
    def remove_gui(self, src):
        start,stop=patch_nav.source_scope(src)
        if src.count(JS_INSERT)==1 and JS_INSERT in src[start:stop]:
            return src.replace(JS_INSERT,'',1)
        if src.count(V1_12_JS_INSERT)==1 and V1_12_JS_INSERT in src[start:stop]:
            return src.replace(V1_12_JS_INSERT,'',1)
        if src.count(V1_10_JS_INSERT)==1 and V1_10_JS_INSERT in src[start:stop]:
            return src.replace(V1_10_JS_INSERT,'',1)
        if src.count(V1_4_JS_INSERT)==1 and V1_4_JS_INSERT in src[start:stop]:
            return src.replace(V1_4_JS_INSERT,'',1)
        if src.count(V1_2_JS_INSERT)==1 and V1_2_JS_INSERT in src[start:stop]:
            return src.replace(V1_2_JS_INSERT,'',1)
        if src.count(RC8R2_JS_INSERT)==1 and RC8R2_JS_INSERT in src[start:stop]:
            return src.replace(RC8R2_JS_INSERT,'',1)
        if src.count(RC8_JS_INSERT)==1 and RC8_JS_INSERT in src[start:stop]:
            return src.replace(RC8_JS_INSERT,'',1)
        if src.count(RC7_JS_INSERT)==1 and RC7_JS_INSERT in src[start:stop]:
            return src.replace(RC7_JS_INSERT,'',1)
        if src.count(RC6_JS_INSERT)==1 and RC6_JS_INSERT in src[start:stop]:
            return src.replace(RC6_JS_INSERT,'',1)
        if src.count(OLD_JS_INSERT)==1 and OLD_JS_INSERT in src[start:stop]:
            return src.replace(OLD_JS_INSERT,'',1)
        raise InstallError('GUI-Block geändert; sichere Entfernung nicht möglich')
    def add_route(self, src):
        anchor='use PVE::API2::VZDump;\n'
        index="__PACKAGE__->register_method({\n    name => 'index',"
        if src.count(anchor)!=1 or src.count(index)<1:
            raise InstallError('Nodes.pm passt nicht zur freigegebenen Struktur')
        if 'ZFSSnapshotViewer' in src or 'zfsmanager-ro' in src:
            raise InstallError('Route existiert schon')
        i=src.index(index)
        # first Nodeinfo index must be before cluster Nodes package.
        if 'package PVE::API2::Nodes::Nodeinfo;' in src:
            p=src.index('package PVE::API2::Nodes::Nodeinfo;')
            if not (p<i): raise InstallError('Nodes.pm index-Route außerhalb Nodeinfo')
        src=src.replace(anchor,anchor+IMPORT_BEGIN+IMPORT+IMPORT_END,1)
        i=src.index(index)
        return src[:i]+ROUTE_BEGIN+ROUTE+ROUTE_END+'\n'+src[i:]
    def remove_route(self, src):
        start=IMPORT_BEGIN+IMPORT+IMPORT_END
        end=ROUTE_BEGIN+ROUTE+ROUTE_END+'\n'
        if src.count(start)!=1 or src.count(end)!=1:
            raise InstallError('API-Route weicht von bekanntem Format ab')
        return src.replace(start,'',1).replace(end,'',1)
    def snapshot(self, paths, transaction):
        backup=self.backup_root/transaction
        backup.mkdir(parents=True,mode=0o700,exist_ok=False)
        result={}
        for label,path in paths.items():
            if path.exists():
                raw=self.read(path)
                file=backup/(label+'.orig')
                file.write_bytes(raw);file.chmod(0o600)
                result[label]={'exists':True,'sha256':sha(raw)}
            else: result[label]={'exists':False}
        return result,backup
    @staticmethod
    def atomic(path,data,mode=None):
        path.parent.mkdir(parents=True,exist_ok=True)
        if path.is_symlink(): raise InstallError('Datei ist Symlink: '+str(path))
        original_stat=path.stat() if path.exists() else None
        fd,tmp=tempfile.mkstemp(prefix='.zfsmgr-',dir=path.parent)
        try:
            with os.fdopen(fd,'wb') as f:
                f.write(data);f.flush();os.fsync(f.fileno())
            if mode is not None:os.chmod(tmp,mode)
            elif original_stat is not None:os.chmod(tmp,stat.S_IMODE(original_stat.st_mode))
            else:os.chmod(tmp,0o644)
            if original_stat is not None:os.chown(tmp,original_stat.st_uid,original_stat.st_gid)
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp):os.unlink(tmp)
    def restart(self):
        if self.dry_system or self.root!=Path('/'): return
        for command in (['perl','-c',str(self.api)],['perl','-c',str(self.nodes)]):
            p=subprocess.run(command,capture_output=True,text=True)
            if p.returncode: raise InstallError('Perl-Syntaxprüfung fehlgeschlagen: '+p.stderr[-1000:])
        # Prefer a reload for the web proxy so active web-shell sessions
        # are not disconnected when the unit supports reloading.
        for svc in ('pvedaemon','pveproxy'):
            can_reload=subprocess.run(['systemctl','show','-p','CanReload','--value',svc],
                capture_output=True,text=True)
            operation='reload' if can_reload.returncode == 0 and can_reload.stdout.strip() == 'yes' else 'restart'
            p=subprocess.run(['systemctl',operation,svc],capture_output=True,text=True)
            if p.returncode:
                raise InstallError('Proxmox-Dienst konnte nicht '+operation+' werden: '+svc+': '+p.stderr)
    def state(self):
        if self.state_file.is_symlink(): raise InstallError('Installerzustand ist Symlink')
        if not self.state_file.is_file(): return None
        return json.loads(self.state_file.read_text())
    def save_state(self,obj):
        self.state_dir.mkdir(parents=True,mode=0o700,exist_ok=True)
        self.atomic(self.state_file,(json.dumps(obj,ensure_ascii=False,indent=2)+'\n').encode(),0o600)
    @staticmethod
    def registered_state(state):
        """Recognize a previous installation by ownership evidence, not its version."""
        if not isinstance(state, dict) or not isinstance(state.get('version'), str):
            return False
        hashes=state.get('installed_hashes')
        return (isinstance(hashes, dict) and
                all(isinstance(hashes.get(key), str) and
                    re.fullmatch(r'[a-fA-F0-9]{64}', hashes[key])
                    for key in ('gui','nodes','api','policy')))

    def prune_automatic_backups(self, keep=2):
        """Keep two recent automatic backups; preserve all unrecognized/manual names.

        Called ONLY after successful commit, never during a failed transaction.
        """
        if not self.backup_root.is_dir() or self.backup_root.is_symlink():
            return
        auto=re.compile(r'^(?:repair-|migrate-|upgrade-rc9-)?\d{8}T\d{6}Z-[a-f0-9]{6}$')
        entries=[]
        for p in self.backup_root.iterdir():
            if auto.fullmatch(p.name) and p.is_dir() and not p.is_symlink():
                entries.append(p)
        entries.sort(key=lambda p:p.name,reverse=True)
        for old in entries[keep:]:
            shutil.rmtree(old)

    def owned_modules_recognized(self):
        """Only an existing registered installation and our named module paths qualify."""
        state=self.state()
        if not state or not state.get('version') or not state.get('installed_hashes'):
            return False
        for path, markers in ((self.api,(b'package PVE::API2::ZFSSnapshotViewer;',b'guest-group-create')),
                              (self.policy,(b'class PolicyError',b'can_create'))):
            self.validate_normal_file(path)
            raw=self.read(path)
            if len(raw)>2_000_000 or not all(marker in raw for marker in markers):
                return False
        return True

    def check(self, allow_missing_dependencies=False):
        version=self.prerequisites(check_dependencies=not allow_missing_dependencies)
        gui,node=self.classify()
        self.verify_911_originals(version,gui,node)
        api,policy=self.expected()
        registered = self.state()
        known_old = bool(registered and registered.get('version') and (self.owned_modules_recognized() or (self.api.is_file() and self.read(self.api) in (self.v1_6_api(),self.v1_5_api(),self.v1_4_api(),self.rc9_api(),self.rc8r2_api(),self.rc7_api(),self.rc6_api()))))
        if gui in ('owned-drift','rc9','v1_12','v1_10','v1_8','v1_7','v1_6','v1_5','v1_4','v1_2','rc9old','rc8r2','rc8','rc7','rc6','rc5'):
            for p in (self.api,self.policy):self.validate_normal_file(p)
            valid_api = (self.api.is_file() and (
                self.read(self.api) == api or
                (known_old and self.read(self.api) in (self.v1_6_api(),self.v1_5_api(),self.v1_4_api(),self.rc9_api(),self.rc8r2_api(),self.rc7_api(),self.rc6_api()))))
            if not valid_api and not self.owned_modules_recognized(): raise InstallError('Backend nicht aus einem geprüften Release')
            if (not self.policy.is_file() or self.read(self.policy) not in ((policy, self.rc9_policy(), self.v1_10_policy()) if known_old else (policy,))) and not self.owned_modules_recognized():
                raise InstallError('Gast-Policy nicht aus einem geprüften Release')
        if self.admindir.is_symlink() or (self.admindir.exists() and not self.admindir.is_dir()):
            raise InstallError('Ungültiges Administratorkonfigurationsverzeichnis')
        for p in (self.api,self.policy,self.secret,self.admin,self.yearly):
            self.validate_normal_file(p)
        # After pve-manager package upgrades the stock GUI/Nodes.pm overwrite
        # our blocks but the independently installed API/policy remain present.
        # This is safe ONLY if registration and both installed modules match.
        if gui=='clean' and (self.api.exists() or self.policy.exists()):
            if not registered or not self.api.is_file() or not self.policy.is_file() or \
               self.read(self.api) not in ((api,self.v1_6_api(),self.v1_5_api(),self.v1_4_api(),self.rc9_api(),self.rc8r2_api(),self.rc7_api(),self.rc6_api()) if known_old else (api,)) or self.read(self.policy) not in ((policy,self.rc9_policy(),self.v1_10_policy()) if registered.get('version') in ('1.0.0-13-dynamic-compat-installer', '1.0.0-12-dynamic-compat-installer', '1.0.0-11-dynamic-compat-installer', '1.0.0-10-dynamic-compat-installer', '1.0.0-professional-guest-tree-installer', '1.0.0-snapshot-tree-installer', '1.0.0-simple-groups-installer', '1.0.0-final-group-installer', '1.0.0-final-test-installer', '1.0.0-rc9-installer', '1.0.0-rc8r2-installer', '1.0.0-rc8-installer','1.0.0-rc7-installer','1.0.0-rc6-installer','1.0.0-rc5-installer') else (policy,)):
                if not self.owned_modules_recognized(): raise InstallError('Vorhandenes API- oder Gast-Policy-Modul ohne bekannte Installation - Abbruch')
        if (gui=='clean' and node=='present') or (gui in ('rc8r2','rc8','rc7','rc6','rc5') and node=='clean'):
            if not registered:
                raise InstallError('Teilintegration ohne bekannten Installerzustand')
        return version,gui,node
    def install(self):
        version,gui_state,node_state=self.check()
        state=self.state()
        if state:
            # RC6 and earlier used an API that could not create standalone
            # snapshots. Migrate exactly that known module together with the GUI.
            # Back up the new PVE files and restore byte-for-byte on failure.
            old_api=self.read(self.api)
            legacy_apis=(self.v1_6_api(),self.v1_5_api(),self.v1_4_api(),self.rc9_api(),self.rc8r2_api(),self.rc7_api(),self.rc6_api())
            old_policy=self.read(self.policy)
            migrate_policy=(old_policy == self.v1_10_policy() and old_policy != self.expected()[1])
            if old_api in legacy_apis or migrate_policy:
                if not state.get('version') or not (self.owned_modules_recognized() or old_api in legacy_apis):
                    raise InstallError('Vorgängerinstallation nicht eindeutig als ZFS Manager erkannt')
                targets={'gui':self.gui,'nodes':self.nodes,'api':self.api,'policy':self.policy}
                self.snapshot(targets,'migrate-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3))
                before={name:self.read(path) for name,path in targets.items()}
                try:
                    self.atomic(self.api,self.expected()[0])
                    self.atomic(self.policy,self.expected()[1],0o755)
                    self.repair()
                except BaseException:
                    for name,path in targets.items():
                        self.atomic(path,before[name])
                    try:self.restart()
                    except Exception:pass
                    raise
            elif old_api in (self.v1_6_api(),self.v1_5_api(),self.v1_4_api(),self.rc9_api()):
                targets={'gui':self.gui,'nodes':self.nodes,'api':self.api,'policy':self.policy}
                self.snapshot(targets,'upgrade-rc9-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3))
                before={name:self.read(path) for name,path in targets.items()}
                try:
                    self.atomic(self.api,self.expected()[0])
                    self.atomic(self.policy,self.expected()[1],0o755)
                    self.repair()
                except BaseException:
                    for name,path in targets.items():
                        self.atomic(path,before[name])
                    try:self.restart()
                    except Exception:pass
                    raise
            else:
                self.repair()
            if state.get('version') != VERSION:
                state=self.state() or state
                state['version'] = VERSION
                state['installer_upgraded_at'] = datetime.now(timezone.utc).isoformat()
                self.save_state(state)
                try:self.prune_automatic_backups()
                except OSError as ex:print('WARNUNG: Alte Sicherungen nicht bereinigt: '+str(ex))
                print('PASS: Registrierte ZFS-Manager-Installation auf '+VERSION+' aktualisiert')
            else:
                print('Schon installiert; keine Änderung erforderlich')
            return
        files={'gui':self.gui,'nodes':self.nodes,'api':self.api,'policy':self.policy,'yearly':self.yearly,'admin':self.admin,'secret':self.secret}
        previous,backup=self.snapshot(files,datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+secrets.token_hex(3))
        before={k: (self.read(p) if p.exists() else None) for k,p in files.items()}
        changed=[]
        api_source,policy_source=self.expected()
        try:
            if gui_state=='clean':
                self.atomic(self.api,api_source);changed.append('api')
                self.atomic(self.policy,policy_source,0o755);changed.append('policy')
                self.atomic(self.nodes,self.add_route(before['nodes'].decode()).encode());changed.append('nodes')
                self.atomic(self.gui,self.add_gui(before['gui'].decode()).encode());changed.append('gui')
            self.admindir.mkdir(parents=True,mode=0o700,exist_ok=True)
            if before['secret'] is None:
                self.atomic(self.secret,(secrets.token_hex(32)+'\n').encode(),0o600);changed.append('secret')
            if before['admin'] is None:
                self.atomic(self.admin,b'# Additional permitted admins; root@pam is always included\n',0o600);changed.append('admin')
            for p in (self.secret,self.admin):
                if p.stat().st_uid!=0 and self.root==Path('/'):raise InstallError('Admin-Datei nicht root-owned')
                if stat.S_IMODE(p.stat().st_mode)!=0o600:raise InstallError('Unsichere Admin-Dateirechte')
            if before['yearly'] is None:
                self.atomic(self.yearly,b'PATH=/usr/sbin:/usr/bin:/sbin:/bin\n# PVE ZFS Manager yearly, January 1st at 03:17\n17 3 1 1 * root /usr/sbin/zfs-auto-snapshot --quiet --syslog --label=yearly --keep=3 //\n',0o644)
                changed.append('yearly')
            self.restart()
            current={k:sha(self.read(p)) for k,p in files.items()}
            self.save_state({'version':VERSION,'proxmox_at_install':version,'adopted_rc2':gui_state!='clean','initial':previous,'backup_dir':str(backup),'installed_hashes':current,'installed_at':datetime.now(timezone.utc).isoformat()})
            try:self.prune_automatic_backups()
            except OSError as ex:print('WARNUNG: Alte Sicherungen nicht bereinigt: '+str(ex))
            print('PASS: '+VERSION+' installiert / übernommen. Sicherung: '+str(backup))
        except BaseException:
            for label in reversed(changed):
                try:
                    if before[label] is None:files[label].unlink(missing_ok=True)
                    else:self.atomic(files[label],before[label])
                except Exception as e:print('WARNUNG: Rückbau von '+label+': '+str(e),file=sys.stderr)
            if changed: 
                try:self.restart()
                except Exception:pass
            raise
    def status(self):
        version=self.prerequisites()
        s=self.state()
        if not s: raise InstallError('Kein registrierter Installerzustand vorhanden')
        api,pol=self.expected()
        guib=self.read(self.gui).decode('utf-8');nodes=self.read(self.nodes).decode('utf-8')
        errors=[]
        if guib.count(JS_INSERT)!=1:errors.append('GUI-Einbindung fehlt/ist verändert')
        if nodes.count("path => 'zfsmanager-ro'")!=1:errors.append('API-Route fehlt/ist verändert')
        if self.read(self.api)!=api:errors.append('API-Datei verändert')
        if self.read(self.policy)!=pol:errors.append('Gast-Policy verändert')
        if errors:raise InstallError('INTEGRATION FEHLT - automatische Pruefung/Reparatur vorgesehen: ' + '; '.join(errors))
        print('PASS: '+VERSION+' integriert. Proxmox: '+version)
    def repair(self, force=False):
        s=self.state()
        if not s:raise InstallError('Keine bestehende Installation - zuerst installieren')
        if not (self.registered_state(s) or (s.get('version') and self.api.is_file() and self.read(self.api) in (self.expected()[0],self.v1_6_api(),self.v1_5_api(),self.v1_4_api(),self.rc9_api(),self.rc8r2_api(),self.rc7_api(),self.rc6_api()))):
            raise InstallError('Ungültiger Installerzustand: Eigentumsnachweis fehlt')
        version=self.prerequisites()
        api,pol=self.expected()
        changed_modules=(self.read(self.api)!=api or self.read(self.policy)!=pol)
        # Recognized, registered plugin files may differ after a local fix or PVE upgrade.
        # Do not overwrite unrelated files, symlinks or unknown unregistered modules.
        if changed_modules and not self.owned_modules_recognized():
            raise InstallError('Unbekannte API/Policy-Datei; nicht als eigene Installation erkannt')
        gui=self.read(self.gui).decode('utf-8')
        nodes=self.read(self.nodes).decode('utf-8')
        mode,route=self.classify()  # rejects foreign or damaged fragments
        self.verify_911_originals(version,mode,route)
        if mode=='owned-drift':
            start,stop=self.owned_gui_drift_span(gui)
            if start is None: raise InstallError('GUI-Blockgrenzen verloren')
            updated_gui=gui[:start]+JS_INSERT+gui[stop:]
        elif mode=='v1_12':
            updated_gui=gui.replace(V1_12_JS_INSERT,JS_INSERT,1)
        elif mode=='v1_10':
            updated_gui=gui.replace(V1_10_JS_INSERT,JS_INSERT,1)
        elif mode=='v1_8':
            updated_gui=gui.replace(V1_8_JS_INSERT,JS_INSERT,1)
        elif mode=='v1_7':
            updated_gui=gui.replace(V1_7_JS_INSERT,JS_INSERT,1)
        elif mode=='v1_6':
            updated_gui=gui.replace(V1_6_JS_INSERT,JS_INSERT,1)
        elif mode=='v1_5':
            updated_gui=gui.replace(V1_5_JS_INSERT,JS_INSERT,1)
        elif mode=='v1_4':
            updated_gui=gui.replace(V1_4_JS_INSERT,JS_INSERT,1)
        elif mode=='v1_2':
            updated_gui=gui.replace(V1_2_JS_INSERT,JS_INSERT,1)
        elif mode=='rc9old':
            updated_gui=gui.replace(RC9_JS_INSERT,JS_INSERT,1)
        elif mode=='rc8r2':
            updated_gui=gui.replace(RC8R2_JS_INSERT,JS_INSERT,1)
        elif mode=='rc8':
            updated_gui=gui.replace(RC8_JS_INSERT,JS_INSERT,1)
        elif mode=='rc7':
            updated_gui=gui.replace(RC7_JS_INSERT,JS_INSERT,1)
        elif mode=='rc6':
            updated_gui=gui.replace(RC6_JS_INSERT,JS_INSERT,1)
        elif mode=='rc5':
            updated_gui=gui.replace(OLD_JS_INSERT,JS_INSERT,1)
        elif mode=='clean':
            updated_gui=self.add_gui(gui)
        else:
            updated_gui=gui
        updated_nodes=self.add_route(nodes) if route=='clean' else nodes
        if updated_gui==gui and updated_nodes==nodes and not changed_modules:
            self.status()
            return
        # Verify exact source roundtrip (including migration) BEFORE writing.
        if mode=='clean' and self.remove_gui(updated_gui)!=gui:
            raise InstallError('GUI-Roundtrip fehlgeschlagen')
        if mode=='owned-drift':
            start,stop=self.owned_gui_drift_span(gui)
            if updated_gui.replace(JS_INSERT,gui[start:stop],1)!=gui:
                raise InstallError('GUI-Drift-Roundtrip fehlgeschlagen')
        if mode=='v1_12' and updated_gui.replace(JS_INSERT,V1_12_JS_INSERT,1)!=gui:
            raise InstallError('1.0.0-12-GUI-Migration nicht reversibel')
        if mode=='v1_10' and updated_gui.replace(JS_INSERT,V1_10_JS_INSERT,1)!=gui:
            raise InstallError('1.0.0-10-GUI-Migration nicht reversibel')
        if mode=='v1_8' and updated_gui.replace(JS_INSERT,V1_8_JS_INSERT,1)!=gui:
            raise InstallError('1.0.0-8-GUI-Migration nicht reversibel')
        if mode=='v1_7' and updated_gui.replace(JS_INSERT,V1_7_JS_INSERT,1)!=gui:
            raise InstallError('1.0.0-7-GUI-Migration nicht reversibel')
        if mode=='v1_6' and updated_gui.replace(JS_INSERT,V1_6_JS_INSERT,1)!=gui:
            raise InstallError('1.0.0-6-GUI-Migration nicht reversibel')
        if mode=='v1_5' and updated_gui.replace(JS_INSERT,V1_5_JS_INSERT,1)!=gui:
            raise InstallError('1.0.0-5-GUI-Migration nicht reversibel')
        if mode=='v1_2' and updated_gui.replace(JS_INSERT,V1_2_JS_INSERT,1)!=gui:
            raise InstallError('1.0.0-2-GUI-Migration nicht reversibel')
        if mode=='rc9old' and updated_gui.replace(JS_INSERT,RC9_JS_INSERT,1)!=gui:
            raise InstallError('RC9-GUI-Migration nicht reversibel')
        if mode=='rc8r2' and updated_gui.replace(JS_INSERT,RC8R2_JS_INSERT,1)!=gui:
            raise InstallError('RC8-R2-GUI-Migration nicht reversibel')
        if mode=='rc8' and updated_gui.replace(JS_INSERT,RC8_JS_INSERT,1)!=gui:
            raise InstallError('RC8-GUI-Migration nicht reversibel')
        if mode=='rc7' and updated_gui.replace(JS_INSERT,RC7_JS_INSERT,1)!=gui:
            raise InstallError('RC7-GUI-Migration nicht reversibel')
        if mode=='rc6' and updated_gui.replace(JS_INSERT,RC6_JS_INSERT,1)!=gui:
            raise InstallError('RC6-GUI-Migration nicht reversibel')
        if mode=='rc5' and updated_gui.replace(JS_INSERT,OLD_JS_INSERT,1)!=gui:
            raise InstallError('RC5-GUI-Migration nicht reversibel')
        if route=='clean' and self.remove_route(updated_nodes)!=nodes:
            raise InstallError('API-Roundtrip fehlgeschlagen')
        # Create a dedicated rescue copy of both current PVE files for EVERY
        # recovery. A previous 9.1.1 backup is never copied over 9.2.21.
        details,folder=self.snapshot(
            {'gui':self.gui,'nodes':self.nodes,'api':self.api,'policy':self.policy},
            'repair-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+
            '-'+secrets.token_hex(3),
        )
        original_gui,original_nodes=gui.encode(),nodes.encode()
        original_api,original_policy=self.read(self.api),self.read(self.policy)
        try:
            if changed_modules:
                self.atomic(self.api,api)
                self.atomic(self.policy,pol,0o755)
            if updated_nodes!=nodes:self.atomic(self.nodes,updated_nodes.encode())
            if updated_gui!=gui:self.atomic(self.gui,updated_gui.encode())
            self.restart()
            # Status is verified with NEW RC8-R2 fingerprint, not just markers.
            self.status()
            s['last_repair_at']=datetime.now(timezone.utc).isoformat()
            s['last_repair_proxmox']=version
            s['last_repair_backup']=str(folder)
            s['last_repair_previous_hashes']=details
            self.save_state(s)
            try:self.prune_automatic_backups()
            except OSError as ex:print('WARNUNG: Alte Sicherungen nicht bereinigt: '+str(ex))
            print('PASS: Bekannte GUI/API automatisch/sicher wiederhergestellt; Backup: '+str(folder))
        except BaseException:
            self.atomic(self.gui,original_gui)
            self.atomic(self.nodes,original_nodes)
            self.atomic(self.api,original_api)
            self.atomic(self.policy,original_policy,0o755)
            try:self.restart()
            except Exception:pass
            raise

    @staticmethod
    def _package_manager_busy():
        """Probe Debian's POSIX record locks, not flock(1) locks.

        Running halfway through an APT transaction could break Proxmox.
        Treat missing/unreadable lock files as busy and retry on next timer.
        """
        locked=[]
        try:
            for name in ('/var/lib/dpkg/lock','/var/lib/dpkg/lock-frontend'):
                fd=os.open(name,os.O_RDWR|os.O_CLOEXEC|os.O_NOFOLLOW)
                try:
                    fcntl.lockf(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                except (OSError,BlockingIOError):
                    os.close(fd)
                    return True
                locked.append(fd)
            return False
        except OSError:
            return True
        finally:
            for fd in locked:
                try:os.close(fd)
                except OSError:pass

    def reconcile(self):
        # Meant for systemd timer/path unit: never install missing packages,
        # never write ZFS, never patch unknown Proxmox releases.
        if not self.state():
            print('INFO: Keine registrierte Installation; nichts zu tun')
            return
        if self.root==Path('/'):
            if self._package_manager_busy():
                print('INFO: Paketverwaltung aktiv/unklar; Reparatur auf nächste Prüfung verschoben')
                return
            for package in ('pve-manager','pve-zfs-manager'):
                result=subprocess.run(['dpkg-query','-W','-f=${Status}',package],
                                      capture_output=True,text=True)
                if result.returncode or result.stdout.strip()!='install ok installed':
                    print('INFO: '+package+' noch nicht vollständig konfiguriert; später erneut prüfen')
                    return
        # A mismatch is never silently "accepted"; only known, reversible
        # patch modifications are attempted. Exceptions propagate to journal.
        self.repair()
        print('PASS: Automatische Integrationskontrolle abgeschlossen')

    def uninstall(self):
        # Exact-block removal can also be safe after a Proxmox update, while
        # unknown/changed injected blocks still force a stop.
        if self.root==Path('/') and os.geteuid()!=0:
            raise InstallError('Deinstallation erfordert root-Rechte')
        s=self.state()
        if not s:raise InstallError('Keine registrierte Installation')
        if s.get('adopted_rc2'):
            print('HINWEIS: Vorbestehende rc2-Integration wird nicht entfernt; nur Installerregistrierung')
            self.state_file.unlink();return
        gui=self.read(self.gui).decode();nodes=self.read(self.nodes).decode()
        out_gui=self.remove_gui(gui).encode();out_nodes=self.remove_route(nodes).encode()
        api,pol=self.expected()
        if self.read(self.api)!=api or self.read(self.policy)!=pol:
            raise InstallError('API/Policy verändert, uninstall verweigert')
        s['removed_at']=datetime.now(timezone.utc).isoformat()
        before={'gui':self.read(self.gui),'nodes':self.read(self.nodes),'api':api,'policy':pol}
        try:
            self.atomic(self.gui,out_gui);self.atomic(self.nodes,out_nodes)
            self.api.unlink();self.policy.unlink()
            self.restart()
            self.state_file.unlink()
            print('PASS: ZFS-Manager-Einbindung entfernt. Backups/Privatkonfiguration erhalten')
        except BaseException:
            for k,p in (('gui',self.gui),('nodes',self.nodes),('api',self.api),('policy',self.policy)):
                try:self.atomic(p,before[k])
                except Exception:pass
            try:self.restart()
            except Exception:pass
            raise
    def rollback(self):
        # For this first public build, rollback means returning to state before installation
        return self.uninstall()


def main(argv):
    if (len(argv)!=2 or argv[1] not in ('precheck','check','install','status','repair','repair-force','reconcile','uninstall','rollback')):
        print('Aufruf: python3 universal.py precheck|check|install|status|repair|reconcile|uninstall|rollback',file=sys.stderr)
        return 2
    try:
        installer=Installer()
        if argv[1]=='precheck':
            installer.precheck()
        elif argv[1]=='repair-force':
            installer.repair(force=True)
        elif argv[1]=='check':
            version,gui,node=installer.check()
            if installer.state() and (gui not in ('rc9','v1_12','v1_10','v1_8','v1_7','v1_6','v1_5','v1_4','v1_2','rc9old','rc8r2','rc8','rc7','rc6','rc5') or node!='present'):
                print('WARNUNG: Installiertes Plugin unvollstaendig nach Update. '
                      'Die automatische Reparatur prueft nur bekannte Proxmox-Versionen. '
                      'GUI: '+gui+' | API: '+node)
                return 1
            print('PASS: '+version+' | GUI: '+gui+' | API: '+node+' (keine Änderung)')
        else:getattr(installer,argv[1])()
        return 0
    except (InstallError,OSError,ValueError,subprocess.SubprocessError) as e:
        print('STOPP: '+str(e),file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main(sys.argv))
