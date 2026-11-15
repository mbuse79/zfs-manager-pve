#!/usr/bin/env python3
"""Opt-in cluster deployment of an locally registered, verified ZFSM bundle.

No automatic rollout, scheduler, credential provisioning or configuration sync.
Root-only plans are single-use and expire five minutes after preparation.
"""
import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import stat
import subprocess
import sys
import tempfile
import time

import zfsm_cluster_remote as remote

STATE = Path('/var/lib/pve-zfs-manager/cluster')
RELEASE = {'version': '1.0.0-34~rc10+fix2', 'cache': True}


class ClusterError(Exception):
    pass


def canonical(data):
    return json.dumps(data, sort_keys=True, separators=(',', ':'))


def job_id(value):
    if not re.fullmatch('[a-f0-9]{32}', value):
        raise ClusterError('Invalid job ID / Ungültige Auftragskennung')
    return value


class Store:
    def __init__(self, root=STATE):
        self.root = Path(root)

    def directory(self, create=False):
        # Refuse substituted ancestors, including an unsafe parent state directory.
        for parent in reversed((self.root, *self.root.parents)[:-1]):
            if create and not parent.exists():
                parent.mkdir(mode=0o700)
            meta = parent.lstat()
            if not stat.S_ISDIR(meta.st_mode) or meta.st_uid != 0 or meta.st_mode & 0o022:
                raise ClusterError('Unsafe cluster state directory')

    def read(self, key):
        self.directory()
        fd = os.open(self.root / (job_id(key) + '.json'), os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd) as f:
            meta = os.fstat(f.fileno())
            if not stat.S_ISREG(meta.st_mode) or meta.st_uid != 0 or stat.S_IMODE(meta.st_mode) != 0o600 or meta.st_size > 2_000_000:
                raise ClusterError('Unsafe cluster job file')
            return json.load(f)

    def write(self, key, data):
        job_id(key)
        self.directory(create=True)
        fd, tmp = tempfile.mkstemp(prefix='.job-', dir=self.root)
        try:
            with os.fdopen(fd, 'w') as f:
                f.write(canonical(data))
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.root / (key + '.json'))
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    @contextmanager
    def lock(self):
        self.directory(create=True)
        fd = os.open(self.root / 'deploy.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            meta = os.fstat(fd)
            if not stat.S_ISREG(meta.st_mode) or meta.st_uid != 0 or stat.S_IMODE(meta.st_mode) != 0o600:
                raise ClusterError('Unsafe deployment lock')
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ClusterError('Deployment already running / Clusterinstallation läuft bereits') from exc
            yield
        finally:
            os.close(fd)


def inventory():
    rows = json.loads(remote.output(['pvesh', 'get', '/cluster/status', '--output-format', 'json']))
    return remote.membership(rows)


def ssh_command(node):
    # Let Proxmox resolve the cluster address and its per-node known_hosts file.
    # Strict host-key checking is explicit even on PVE versions that fall back
    # to the system known_hosts configuration. No trust material is created.
    code = ('PVE::Cluster::cfs_update(1); '
            'my $members = PVE::Cluster::get_members(); '
            'my $member = ref($members) eq "HASH" ? $members->{$ARGV[0]} : undef; '
            'die "No cluster member address; DNS fallback refused\\n" '
            'unless ref($member) eq "HASH" && defined($member->{ip}); '
            'my $info = PVE::SSHInfo::get_ssh_info($ARGV[0]); '
            'die "SSH address differs from cluster membership\\n" '
            'unless $info->{ip} eq $member->{ip}; '
            'print JSON::PP::encode_json(PVE::SSHInfo::ssh_info_to_command($info, '
            '"-T", "-oStrictHostKeyChecking=yes", "-oConnectTimeout=8", '
            '"-oServerAliveInterval=10", "-oServerAliveCountMax=3"));')
    p = subprocess.run(['/usr/bin/perl', '-MPVE::SSHInfo', '-MJSON::PP', '-e', code, node],
                       capture_output=True, text=True, timeout=15)
    if p.returncode:
        raise ClusterError('Proxmox cluster SSH configuration unavailable / '
                           'Proxmox-Cluster-SSH-Konfiguration nicht verfügbar: ' + p.stderr[-2000:])
    command = json.loads(p.stdout)
    if (not isinstance(command, list) or len(command) < 3 or command[0] != '/usr/bin/ssh' or
            not all(isinstance(x, str) for x in command) or
            '-oStrictHostKeyChecking=yes' not in command or not command[-1].startswith('root@')):
        raise ClusterError('Invalid Proxmox SSH command')
    try:
        ipaddress.ip_address(command[-1][len('root@'):])
    except ValueError as exc:
        raise ClusterError('Numeric cluster address required; DNS fallback refused / '
                           'Numerische Clusteradresse erforderlich; kein DNS-Fallback') from exc
    return command


def transport(node, mode, request=None, bundle=None):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,62}', node):
        raise ClusterError('Invalid target node')
    source = Path(remote.__file__).read_text()
    args = ['/usr/bin/python3', '-c', source, mode]
    if request is not None:
        args.append(canonical(request))
    # Always use the cluster's existing SSH trust; never accept new host keys or
    # change authorized_keys, DNS, credentials or cluster files.
    if node != remote.socket.gethostname().split('.')[0]:
        args = [*ssh_command(node), shlex.join(args)]
    try:
        p = subprocess.run(args, input=bundle or b'', capture_output=True,
                           timeout=660 if mode == 'install' else 180)
    except subprocess.TimeoutExpired as exc:
        raise ClusterError('SSH/installer timeout; inspect target before retry / '
                           'Zeitlimit; Ziel vor Wiederholung prüfen: ' + node) from exc
    if len(p.stdout) > 100000:
        raise ClusterError('Excessive transport output: ' + node)
    try:
        data = json.loads(p.stdout)
    except (ValueError, UnicodeError) as exc:
        raise ClusterError('SSH/Python connection failed: ' + node + ': ' +
                           p.stderr.decode(errors='replace')[-2000:]) from exc
    if p.returncode or 'error' in data:
        raise ClusterError(node + ': ' + data.get('error', 'Transport failed'))
    return data


def bundle_bytes():
    if RELEASE.get('cache'):
        from zfsm_cluster_cache import load
        meta, data = load()
        if meta != RELEASE:
            raise ClusterError('Registered bundle changed; repeat preview / Clusterpaket verändert; Vorschau erneuern')
        return data
    raise ClusterError('Verified local cluster bundle required / Geprüftes lokales Clusterpaket erforderlich')


def selection(names, cluster):
    names = names.split(',') if isinstance(names, str) else list(names)
    known = {n['name']: n for n in cluster['nodes']}
    if not names or len(names) > 64 or len(set(names)) != len(names) or any(n not in known for n in names):
        raise ClusterError('Select existing cluster nodes explicitly / Clusterknoten ausdrücklich auswählen')
    # Install the coordinator last so a local GUI/API replacement cannot interrupt
    # preparation of the remaining targets.
    local = remote.socket.gethostname().split('.')[0]
    return sorted(names, key=lambda n: (n == local, n))


def inspect(node, cluster, probe):
    if not next(n['online'] for n in cluster['nodes'] if n['name'] == node):
        raise ClusterError('Offline node / Knoten offline: ' + node)
    if probe.get('node') != node or probe.get('cluster') != cluster['identity']:
        raise ClusterError('Target identity/membership mismatch / Falscher Zielknoten oder Cluster: ' + node)
    if not re.match(r'^pve-manager/9\.\d+\.\d+/', probe.get('pve', '')):
        raise ClusterError('PVE 9.x required / PVE 9.x erforderlich: ' + node)
    if probe.get('arch') not in ('amd64',):
        raise ClusterError('Bundled dependency architecture unsupported: ' + node)
    if probe.get('audit'):
        raise ClusterError('Unfinished package operations / Unfertige Paketvorgänge: ' + node + '\n' + probe['audit'])
    package = probe.get('package', '')
    if package:
        if not package.startswith('install ok installed\t'):
            # dpkg retains harmless residual-config entries after removal.
            if package.startswith('deinstall ok config-files\t'):
                return 'install'
            raise ClusterError('Incomplete ZFSM package state: ' + node)
        version = package.split('\t', 1)[1]
        p = subprocess.run(['dpkg', '--compare-versions', version, 'ge', RELEASE['version']])
        if p.returncode not in (0, 1):
            raise ClusterError('Invalid installed package version')
        if p.returncode == 0:
            return 'unchanged'
    return 'install'


class Controller:
    def __init__(self, store=None, roster=inventory, send=transport, fetch=bundle_bytes, now=time.time):
        self.store = store or Store()
        self.roster, self.send, self.fetch, self.now = roster, send, fetch, now

    def request(self, probe, lang):
        return {**RELEASE, 'expected': probe, 'lang': lang}

    def prepare(self, key, nodes, lang='de'):
        with self.store.lock():
            report = {'kind': 'preview', 'status': 'running', 'release': RELEASE,
                      'results': [], 'ready': False, 'lang': lang}
            self.store.write(key, report)
            try:
                cluster = self.roster()
                nodes = selection(nodes, cluster)
                report.update(cluster=cluster['identity'], nodes=nodes)
                bundle = self.fetch()
                for node in nodes:
                    row = {'node': node, 'status': 'blocked'}
                    report['results'].append(row)
                    try:
                        if not next(n['online'] for n in cluster['nodes'] if n['name'] == node):
                            raise ClusterError('Offline / Knoten offline')
                        probe = self.send(node, 'probe')
                        action = inspect(node, cluster, probe)
                        row.update(probe=probe, action=action)
                        if action == 'install':
                            check = self.send(node, 'check', self.request(probe, lang), bundle)
                        else:
                            check = self.send(node, 'health')
                        row['log'] = check['log']
                        if not check['ok']:
                            raise ClusterError('Preflight/integration failed; review node / Vorprüfung oder Integration fehlgeschlagen; Knoten prüfen')
                        row['status'] = 'ready' if action == 'install' else 'unchanged'
                    except (ClusterError, ValueError, OSError) as exc:
                        row['error'] = str(exc)
                    self.store.write(key, report)
                report['ready'] = all(r['status'] != 'blocked' for r in report['results'])
                report['expires'] = int(self.now()) + 300
                report['status'] = 'complete'
            except Exception as exc:
                report.update(status='failed', error=str(exc))
            self.store.write(key, report)
            return report

    def apply(self, key, plan_key):
        with self.store.lock():
            report = {'kind': 'install', 'status': 'running', 'results': []}
            self.store.write(key, report)
            try:
                plan = self.store.read(plan_key)
                if (plan.get('kind') != 'preview' or plan.get('status') != 'complete' or
                        not plan.get('ready') or plan.get('used') or
                        not self.now() < plan.get('expires', 0) <= self.now() + 300 or
                        plan.get('release') != RELEASE):
                    raise ClusterError('Preview invalid/expired/used; repeat / Vorschau ungültig, abgelaufen oder verbraucht')
                plan['used'] = True  # Consume even when a later check fails.
                self.store.write(plan_key, plan)
                report['results'] = [{'node': r['node'], 'status': 'not_started'} for r in plan['results']]
                cluster = self.roster()
                nodes = selection(plan['nodes'], cluster)
                if cluster['identity'] != plan['cluster'] or nodes != plan['nodes']:
                    raise ClusterError('Cluster membership changed / Clusterzusammensetzung verändert')
                bundle = self.fetch()
                # Recheck every target before the first actual installation.
                for row in plan['results']:
                    node = row['node']
                    probe = self.send(node, 'probe')
                    action = inspect(node, cluster, probe)
                    if probe != row['probe'] or action != row['action']:
                        raise ClusterError('Host changed; repeat preview: ' + node)
                    if action == 'install':
                        check = self.send(node, 'check', self.request(probe, plan['lang']), bundle)
                    else:
                        check = self.send(node, 'health')
                    if not check['ok']:
                        raise ClusterError(node + ': ' + check['log'])
                for row, result in zip(plan['results'], report['results']):
                    node = row['node']
                    if row['action'] == 'unchanged':
                        result['status'] = 'unchanged'
                        continue
                    fresh = self.roster()
                    if fresh['identity'] != plan['cluster']:
                        raise ClusterError('Cluster membership changed; rollout stopped')
                    probe = self.send(node, 'probe')
                    inspect(node, fresh, probe)
                    if probe != row['probe']:
                        raise ClusterError('Host changed immediately before installation: ' + node)
                    result['status'] = 'installing'
                    self.store.write(key, report)
                    outcome = self.send(node, 'install', self.request(probe, plan['lang']), bundle)
                    result.update(status='installed' if outcome['ok'] else 'failed', log=outcome['log'])
                    self.store.write(key, report)
                    if not outcome['ok']:
                        raise ClusterError('Installation failed; rollout stopped / Installation fehlgeschlagen; Verteilung gestoppt: ' + node)
                report['status'] = 'complete'
            except Exception as exc:
                report.update(status='failed', error=str(exc))
                for result in report['results']:
                    if result['status'] == 'installing':
                        result['status'] = 'unknown'
            self.store.write(key, report)
            return report


def main(argv=None, lang='de'):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--lang' in argv:
        index = argv.index('--lang')
        if index + 1 < len(argv) and argv[index + 1] in ('de', 'en'):
            lang = argv[index + 1]
    de = lang == 'de'
    class Parser(argparse.ArgumentParser):
        def __init__(self, *args, **kwargs):
            kwargs['add_help'] = False
            super().__init__(*args, **kwargs)
            self.add_argument('-h', '--help', action='help', help='Diese Hilfe anzeigen' if de else 'Show this help')
            self._positionals.title = 'Befehle' if de else 'Commands'
            self._optionals.title = 'Optionen' if de else 'Options'

        def format_help(self):
            text = super().format_help()
            return text.replace('usage:', 'Verwendung:', 1) if de else text

    parser = Parser(prog='zfsm cluster',description=('Optionale Clusterinstallation; keine automatische Verteilung.' if de else 'Optional cluster installation; no automatic rollout.'))
    sub = parser.add_subparsers(dest='command', required=True, parser_class=Parser)
    sub.add_parser('status', help='Clusterknoten anzeigen' if de else 'List cluster nodes')
    preview = sub.add_parser('preview', help='Gewählte Knoten prüfen' if de else 'Check selected nodes')
    preview.add_argument('--nodes', required=True, help='Knoten, durch Komma getrennt' if de else 'Comma-separated node names')
    preview.add_argument('--job', default=None, help=argparse.SUPPRESS)
    apply = sub.add_parser('install', help='Bestätigte Vorschau ausführen' if de else 'Apply a confirmed preview')
    apply.add_argument('--plan', required=True)
    apply.add_argument('--job', default=None, help=argparse.SUPPRESS)
    apply.add_argument('--confirmed', action='store_true', help=argparse.SUPPRESS)
    job = sub.add_parser('job', help='Auftragsbericht anzeigen' if de else 'Show job report')
    job.add_argument('--job', required=True)
    parser.add_argument('--lang', choices=('de', 'en'), default=lang)
    args = parser.parse_args(argv)
    lang = args.lang
    if os.geteuid() != 0:
        raise ClusterError('Root-Rechte erforderlich / root required')
    if args.command != 'job':
        global RELEASE
        from zfsm_cluster_cache import load
        try:
            RELEASE, _ = load()
        except FileNotFoundError as exc:
            raise ClusterError('RC10 cluster bundle missing. Install using the full verified ZIP. / '
                               'RC10-Clusterpaket fehlt. Mit der vollständigen geprüften ZIP installieren.') from exc
    if args.command == 'status':
        print(json.dumps({'release': RELEASE, **inventory()}, ensure_ascii=False))
        return 0
    if args.command == 'job':
        print(json.dumps(Store().read(args.job), ensure_ascii=False))
        return 0
    key = job_id(args.job) if args.job else secrets.token_hex(16)
    if args.command == 'install' and not args.confirmed:
        plan = Store().read(args.plan)
        print(('Zielknoten: ' if de else 'Target nodes: ') + ', '.join(plan['nodes']))
        print(('Paketversion: ' if de else 'Package version: ') + RELEASE['version'])
        if not sys.stdin.isatty() or input('Installation starten? [j/N]: ' if de else 'Start installation? [y/N]: ').lower() not in ('j', 'ja', 'y', 'yes'):
            raise ClusterError('Abgebrochen / Cancelled')
    report = (Controller().prepare(key, args.nodes, lang) if args.command == 'preview'
              else Controller().apply(key, job_id(args.plan)))
    print(json.dumps({'job': key, **report}, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'complete' else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
