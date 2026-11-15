"""Cluster fixtures: no SSH connections, package installs or real PVE hosts."""
import copy
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
import zfsm_cluster as c
import zfsm_cluster_remote as r

A, B, C = 'a' * 32, 'b' * 32, 'c' * 32


class MemoryStore:
    def __init__(self):
        self.data = {}
        self.locked = False

    def write(self, key, value):
        self.data[key] = copy.deepcopy(value)

    def read(self, key):
        return copy.deepcopy(self.data[key])

    @contextmanager
    def lock(self):
        if self.locked:
            raise c.ClusterError('Already locked')
        self.locked = True
        try:
            yield
        finally:
            self.locked = False


class Fixture:
    def __init__(self):
        self.cluster = r.membership([
            {'type': 'cluster', 'name': 'fixture', 'quorate': 1},
            *[{'type': 'node', 'name': n, 'nodeid': i, 'online': 1}
              for i, n in enumerate(('node-a', 'node-b', 'node-c'), 1)]])
        self.probes = {n['name']: {'node': n['name'], 'pve': 'pve-manager/9.99.123/mock',
                       'arch': 'amd64', 'package': '', 'audit': '',
                       'cluster': self.cluster['identity']} for n in self.cluster['nodes']}
        self.calls = []
        self.fail_check = self.fail_install = self.disconnect = None
        self.bad_health = False
        self.clock = 10000
        self.store = MemoryStore()
        self.controller = c.Controller(store=self.store, roster=lambda: copy.deepcopy(self.cluster),
                                       send=self.send, fetch=lambda: b'verified-fixture', now=lambda: self.clock)

    def send(self, node, mode, request=None, bundle=None):
        self.calls.append((node, mode))
        if mode == 'probe':
            return copy.deepcopy(self.probes[node])
        if mode == 'health':
            return {'ok': not self.bad_health, 'log': 'existing integration check'}
        assert request['expected'] == self.probes[node]
        assert request['sha256'] == c.RELEASE['sha256']
        assert bundle == b'verified-fixture'
        if mode == 'check':
            return {'ok': node != self.fail_check, 'log': 'APT/conflict check'}
        assert mode == 'install'
        if node == self.disconnect:
            raise c.ClusterError('SSH connection lost')
        if node == self.fail_install:
            return {'ok': False, 'log': 'postinst failure'}
        self.probes[node]['package'] = 'install ok installed\t' + c.RELEASE['version']
        return {'ok': True, 'log': 'installed; configuration retained'}


def test_preview_never_installs_then_only_explicit_targets_apply():
    f = Fixture()
    p = f.controller.prepare(A, 'node-a,node-c')
    assert p['ready'] and p['expires'] == 10300
    assert all(mode != 'install' for _, mode in f.calls)
    result = f.controller.apply(B, A)
    assert result['status'] == 'complete'
    assert [(n, m) for n, m in f.calls if m == 'install'] == [('node-a', 'install'), ('node-c', 'install')]
    assert not any(n == 'node-b' for n, _ in f.calls)
    assert f.controller.apply(C, A)['status'] == 'failed'  # Single use.


@pytest.mark.parametrize('nodes', ['', 'node-a,node-a', 'outside', '-oProxyCommand=id', 'node-a;id'])
def test_bad_selection_cannot_reach_ssh(nodes):
    f = Fixture()
    assert f.controller.prepare(A, nodes)['status'] == 'failed'
    assert not f.calls


@pytest.mark.parametrize('change', ['offline', 'wrong-host', 'wrong-cluster', 'pve8', 'pve10', 'audit', 'partial', 'arch', 'conflict'])
def test_target_preflight_blocks_apply_without_installation(change):
    f = Fixture()
    probe = f.probes['node-b']
    if change == 'offline':
        f.cluster['nodes'][1]['online'] = False
    elif change == 'wrong-host':
        probe['node'] = 'unexpected'
    elif change == 'wrong-cluster':
        probe['cluster'] = {'name': 'other', 'nodes': []}
    elif change.startswith('pve'):
        probe['pve'] = 'pve-manager/' + change[3:] + '.1.1/mock'
    elif change == 'audit':
        probe['audit'] = 'kernel unpacked but unconfigured'
    elif change == 'partial':
        probe['package'] = 'install ok unpacked\t1.0'
    elif change == 'arch':
        probe['arch'] = 'arm64'
    else:
        f.fail_check = 'node-b'
    p = f.controller.prepare(A, 'node-a,node-b')
    assert not p['ready']
    assert p['results'][1]['status'] == 'blocked'
    assert f.controller.apply(B, A)['status'] == 'failed'
    assert not any(m == 'install' for _, m in f.calls)


@pytest.mark.parametrize('change', ['expired', 'membership', 'pve-version', 'package', 'offline', 'conflict', 'release'])
def test_revalidation_before_first_install(change):
    f = Fixture()
    assert f.controller.prepare(A, 'node-a,node-b')['ready']
    if change == 'expired':
        f.clock += 300
    elif change == 'membership':
        f.cluster['identity']['name'] = 'changed'
    elif change == 'pve-version':
        f.probes['node-b']['pve'] = 'pve-manager/9.1.999/new'
    elif change == 'package':
        f.probes['node-b']['package'] = 'install ok installed\t1.0'
    elif change == 'offline':
        f.cluster['nodes'][1]['online'] = False
    elif change == 'conflict':
        f.fail_check = 'node-b'
    else:
        f.store.data[A]['release']['sha256'] = 'f' * 64
    assert f.controller.apply(B, A)['status'] == 'failed'
    assert not any(m == 'install' for _, m in f.calls)


@pytest.mark.parametrize('disconnect', [False, True])
def test_partial_failure_stops_and_reports_not_started_nodes(disconnect):
    f = Fixture()
    assert f.controller.prepare(A, 'node-a,node-b,node-c')['ready']
    if disconnect:
        f.disconnect = 'node-b'
    else:
        f.fail_install = 'node-b'
    result = f.controller.apply(B, A)
    assert result['status'] == 'failed'
    assert [x['status'] for x in result['results']] == ['installed', 'unknown' if disconnect else 'failed', 'not_started']
    assert ('node-c', 'install') not in f.calls


@pytest.mark.parametrize('version', [c.RELEASE['version'], '9.0.0'])
def test_same_or_newer_version_never_reinstalled_or_downgraded(version):
    f = Fixture()
    f.probes['node-a']['package'] = 'install ok installed\t' + version
    assert f.controller.prepare(A, 'node-a')['results'][0]['status'] == 'unchanged'
    assert f.controller.apply(B, A)['status'] == 'complete'
    assert ('node-a', 'health') in f.calls
    assert not any(m == 'install' for _, m in f.calls)


def test_equal_version_broken_integration_is_reported_without_blind_repair():
    f = Fixture()
    f.probes['node-a']['package'] = 'install ok installed\t' + c.RELEASE['version']
    f.bad_health = True
    assert not f.controller.prepare(A, 'node-a')['ready']
    assert not any(m == 'install' for _, m in f.calls)


def test_quorum_required_and_coordinator_last(monkeypatch):
    with pytest.raises(ValueError, match='quorum'):
        r.membership([{'type': 'cluster', 'name': 'fixture', 'quorate': 0}])
    f = Fixture()
    monkeypatch.setattr(r.socket, 'gethostname', lambda: 'node-a')
    assert c.selection('node-a,node-b,node-c', f.cluster) == ['node-b', 'node-c', 'node-a']


def test_transport_uses_existing_trust_and_never_shell_or_password_fallback(monkeypatch):
    calls = []
    monkeypatch.setattr(r.socket, 'gethostname', lambda: 'coordinator')
    monkeypatch.setattr(c, 'ssh_command', lambda node: ['/usr/bin/ssh', '-oBatchMode=yes',
        '-oStrictHostKeyChecking=yes', '-oHostKeyAlias='+node, 'root@'+node])
    def run(args, **kwargs):
        calls.append((args, kwargs))
        return subprocess.CompletedProcess(args, 0, stdout=b'{"ok":true}', stderr=b'')
    monkeypatch.setattr(c.subprocess, 'run', run)
    c.transport('node-a', 'probe')
    args, kwargs = calls[0]
    assert args[0] == '/usr/bin/ssh'
    assert '-oBatchMode=yes' in args and '-oStrictHostKeyChecking=yes' in args
    assert args[-2] == 'root@node-a'
    assert not kwargs.get('shell')
    with pytest.raises(c.ClusterError):
        c.transport('node-a;touch /tmp/bad', 'probe')
    assert len(calls) == 1


def test_native_proxmox_ssh_info_supplies_address_and_host_key_file(monkeypatch):
    def run(args, **kwargs):
        assert args[:3] == ['/usr/bin/perl', '-MPVE::SSHInfo', '-MJSON::PP']
        assert 'get_ssh_info($ARGV[0])' in args[4]
        assert 'ssh_info_to_command' in args[4]
        assert 'StrictHostKeyChecking=yes' in args[4]
        assert args[-1] == 'node-a'
        command = ['/usr/bin/ssh','-o','HostKeyAlias=node-a','-o',
            'UserKnownHostsFile=/etc/pve/nodes/node-a/ssh_known_hosts',
            '-oStrictHostKeyChecking=yes','root@192.0.2.10']
        return subprocess.CompletedProcess(args,0,stdout=json.dumps(command),stderr='')
    monkeypatch.setattr(c.subprocess,'run',run)
    command=c.ssh_command('node-a')
    assert command[-1]=='root@192.0.2.10'
    assert 'UserKnownHostsFile=/etc/pve/nodes/node-a/ssh_known_hosts' in command


def archive(files, manifest=None):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as z:
        for name, payload in files.items():
            z.writestr(name, payload)
        if manifest is None:
            manifest = ''.join(hashlib.sha256(v).hexdigest() + '  ' + k + '\n' for k, v in files.items())
        z.writestr('SHA256SUMS', manifest)
    return data.getvalue()


@pytest.mark.parametrize('case', ['outer', 'missing', 'modified', 'traversal', 'symlink', 'duplicate', 'extra'])
def test_no_package_code_executes_before_all_checksums_pass(case, tmp_path, monkeypatch):
    data = archive({'install_driver.py': b'raise Exception("NEVER EXECUTE")'})
    digest = hashlib.sha256(data).hexdigest()
    if case == 'outer':
        digest = '0' * 64
    elif case == 'missing':
        data = archive({'install_driver.py': b'no'}, '')
    elif case == 'modified':
        data = archive({'install_driver.py': b'no'}, '0' * 64 + '  install_driver.py\n')
    elif case == 'traversal':
        data = archive({'../escape.py': b'bad'})
    elif case == 'extra':
        data = archive({'install_driver.py': b'no'}, '0' * 64 + '  absent\n')
    elif case in ('symlink', 'duplicate'):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w') as z:
            info = zipfile.ZipInfo('payload')
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            if case == 'symlink':
                z.writestr(info, '/etc/shadow')
            else:
                z.writestr('payload', 'one')
                with pytest.warns(UserWarning):
                    z.writestr('payload', 'two')
        data = buf.getvalue()
    if case != 'outer':
        digest = hashlib.sha256(data).hexdigest()
    monkeypatch.setattr(r, 'probe', lambda: {'node': 'fixture'})
    monkeypatch.setattr(r.subprocess, 'run', lambda *a, **k: pytest.fail('Package code executed'))
    with pytest.raises((ValueError, OSError)):
        r.execute('check', {'expected': {'node': 'fixture'}, 'sha256': digest}, data)
    assert not (tmp_path.parent / 'escape.py').exists()


def test_valid_archive_full_manifest(tmp_path):
    data = archive({'install_driver.py': b'print("fixture")', 'dependencies/LICENSE': b'fixture license'})
    r.unpack(data, hashlib.sha256(data).hexdigest(), tmp_path)
    assert (tmp_path / 'dependencies/LICENSE').read_bytes() == b'fixture license'


def test_store_rejects_symlinked_state(tmp_path):
    target = tmp_path / 'target'
    target.mkdir()
    link = tmp_path / 'link'
    link.symlink_to(target)
    with pytest.raises((c.ClusterError, PermissionError)):
        c.Store(link).write(A, {'test': True})


@pytest.mark.skipif(os.geteuid() != 0, reason='Run this root-ownership fixture separately with fakeroot')
def test_cluster_root_owned_store_and_single_controller_lock():
    # The fixture lives under the checkout, never a real host state directory.
    with tempfile.TemporaryDirectory(prefix='.cluster-store-test-', dir=ROOT) as td:
        store = c.Store(Path(td) / 'state')
        store.write(A, {'kind': 'fixture'})
        assert store.read(A) == {'kind': 'fixture'}
        path = store.root / (A + '.json')
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
        with store.lock():
            with pytest.raises(c.ClusterError, match='already running'):
                with store.lock():
                    pytest.fail('Concurrent controller acquired lock')
        path.chmod(0o644)
        with pytest.raises(c.ClusterError, match='Unsafe cluster job file'):
            store.read(A)
        path.unlink()
        path.symlink_to(Path(td) / 'outside')
        with pytest.raises(OSError):
            store.read(A)
        root_link = Path(td) / 'linked-state'
        root_link.symlink_to(store.root)
        with pytest.raises(c.ClusterError, match='Unsafe cluster state directory'):
            c.Store(root_link).write(B, {})


def test_cluster_api_root_token_confirmation_and_input_checks():
    p = subprocess.run(['perl', '-I', str(ROOT / 'src'), str(ROOT / 'tests/perl_mock_cluster.pl')],
                       capture_output=True, text=True)
    assert p.returncode == 0, p.stdout + p.stderr
