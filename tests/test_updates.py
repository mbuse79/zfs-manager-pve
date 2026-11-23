"""No network or host changes: exercise trusted release and single-use update flow."""
from contextlib import contextmanager
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import zipfile

import pytest
import zfsm_updates as u

PLAN, APPLY = 'a'*32, 'b'*32


def release(archive=b'payload'):
    tag, name = 'v2.0', 'BuMaVory-ZFS-Manager-2.0.zip'
    sums = (hashlib.sha256(archive).hexdigest()+'  '+name+'\n').encode()
    files = {name: archive, 'SHA256SUMS': sums}
    obj = {'draft': False, 'prerelease': False, 'tag_name': tag, 'assets': []}
    responses = {}
    for key, data in files.items():
        url = 'https://github.com/'+u.REPO+'/releases/download/'+tag+'/'+key
        obj['assets'].append({'name': key, 'size': len(data), 'digest': 'sha256:'+hashlib.sha256(data).hexdigest(), 'browser_download_url': url})
        responses[url] = data
    responses[u.API] = json.dumps(obj).encode()
    return obj, responses


def bundle_bytes():
    files = {'install-local.sh': b'#!/bin/sh\nexit 0\n', 'install_driver.py': b'# isolated fixture\n',
             'pve-zfs-manager_2.0_all.deb': b'fixture deb metadata read is mocked'}
    files['SHA256SUMS'] = ''.join(hashlib.sha256(raw).hexdigest()+'  '+name+'\n' for name, raw in files.items()).encode()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as z:
        for name, raw in files.items():
            z.writestr(name, raw)
    return stream.getvalue()


class MemoryStore:
    def __init__(self, root):
        self.root = root
        self.data = {}
        self.locked = False

    def read(self, key):
        if key not in self.data:
            raise FileNotFoundError(key)
        return copy.deepcopy(self.data[key])

    def write(self, key, value):
        self.data[key] = copy.deepcopy(value)

    @contextmanager
    def lock(self):
        if self.locked:
            raise u.UpdateError('busy')
        self.locked = True
        try:
            yield
        finally:
            self.locked = False


@pytest.fixture
def manager(tmp_path, monkeypatch):
    _, responses = release(bundle_bytes())
    state = {'version': '1.1.1~test4', 'pve': 'pve-manager/9.1.1/fixture', 'audit': '', 'commands': [], 'downloads': []}

    def fetch(url, limit):
        state['downloads'].append(url)
        raw = responses[url]
        assert len(raw) <= limit
        return raw

    def command(args, timeout=30):
        state['commands'].append(args)
        if args[0] == 'pveversion':
            return state['pve']
        if args[:2] == ['dpkg', '--audit']:
            return state['audit']
        if args[0] == 'dpkg-deb':
            return {'Package': 'pve-zfs-manager', 'Version': '2.0', 'Architecture': 'all'}[args[-1]]
        if args[0] == 'bash':
            if '--check-only' not in args:
                if state.get('fail_install'):
                    raise u.UpdateError('injected dpkg failure; state may be partial')
                state['version'] = '2.0'
            return 'fixture precheck/install output'
        raise AssertionError(args)

    monkeypatch.setattr(u, 'run', command)
    updater = u.Updater(store=MemoryStore(tmp_path), fetch=fetch, current=lambda: state['version'])
    return updater, state, responses


def test_status_is_cached_read_only_and_daily_check_never_executes_package(manager):
    updater, state, _ = manager
    assert updater.status()['checked_at'] is None
    assert not state['downloads'] and not state['commands'] and not updater.store.data
    status = updater.check()
    assert status['available'] and status['latest_version'] == '2.0'
    assert state['downloads'] == [u.API]
    assert not state['commands']
    count = len(state['downloads'])
    assert updater.status()['available']
    assert len(state['downloads']) == count


@pytest.mark.parametrize('change', ['draft', 'prerelease', 'bad-tag', 'missing', 'duplicate', 'wrong-repo', 'http', 'digest'])
def test_untrusted_release_metadata_rejected(change):
    data, _ = release()
    if change in ('draft', 'prerelease'):
        data[change] = True
    elif change == 'bad-tag':
        data['tag_name'] = 'v2.0;id'
    elif change == 'missing':
        data['assets'].pop()
    elif change == 'duplicate':
        data['assets'].append(data['assets'][0])
    elif change in ('wrong-repo', 'http'):
        data['assets'][0]['browser_download_url'] = 'http://example.org/package.zip'
    elif change == 'digest':
        data['assets'][0]['digest'] = 'sha256:bad'
    with pytest.raises(u.UpdateError):
        u.release_info(json.dumps(data))


@pytest.mark.parametrize('url', ['http://github.com/x', 'https://evil.test/x', 'https://github.com@evil.test/x',
                                  'https://user:pass@github.com/x', 'https://github.com:444/x'])
def test_redirect_trust_boundary(url):
    with pytest.raises(u.UpdateError):
        u.safe_url(url)


def test_check_failure_is_visible_and_does_not_offer_cached_update(manager):
    updater, state, responses = manager
    updater.check()
    responses[u.API] = b'broken metadata'
    status = updater.check()
    assert status['error'] and not status['available']
    assert not state['commands']


def test_prepare_then_confirmed_install_is_single_use(manager, monkeypatch):
    updater, state, _ = manager
    plan = updater.prepare(PLAN)
    assert plan['status'] == 'prepared' and plan['ready']
    assert not any(c[0] == 'bash' and '--check-only' not in c for c in state['commands'])
    # Unit flow uses an injected archive reader. Real ownership enforcement is
    # tested separately below; production CLI never exposes path/reader overrides.
    monkeypatch.setattr(updater, 'read_archive', lambda ident: (updater.store.root/('bundle-'+ident+'.zip')).read_bytes())
    result = updater.install(APPLY, PLAN, True)
    assert result['status'] == 'installed' and state['version'] == '2.0'
    assert updater.store.read(PLAN)['status'] == 'used'
    assert not (updater.store.root/('bundle-'+PLAN+'.zip')).exists()
    with pytest.raises(u.UpdateError):
        updater.install('c'*32, PLAN, True)


@pytest.mark.parametrize('case', ['no-confirm', 'expired', 'used', 'package-changed', 'pve-changed', 'pending-dpkg', 'corrupt-zip'])
def test_stale_or_unconfirmed_plan_never_installs(manager, monkeypatch, case):
    updater, state, _ = manager
    updater.prepare(PLAN)
    monkeypatch.setattr(updater, 'read_archive', lambda ident: (updater.store.root/('bundle-'+ident+'.zip')).read_bytes())
    if case == 'expired':
        updater.store.data[PLAN]['expires_at'] = 1
    elif case == 'used':
        updater.store.data[PLAN]['status'] = 'used'
    elif case == 'package-changed':
        state['version'] = '1.2'
    elif case == 'pve-changed':
        state['pve'] = 'pve-manager/9.2.1/changed'
    elif case == 'pending-dpkg':
        state['audit'] = 'unfinished kernel configuration'
    elif case == 'corrupt-zip':
        (updater.store.root/('bundle-'+PLAN+'.zip')).write_bytes(b'tampered')
    with pytest.raises((u.UpdateError, ValueError, OSError)):
        updater.install(APPLY, PLAN, case != 'no-confirm')
    assert not any(c[0] == 'bash' and '--check-only' not in c for c in state['commands'])


def test_failed_install_consumes_plan_and_reports_uncertain_state(manager, monkeypatch):
    updater, state, _ = manager
    updater.prepare(PLAN)
    monkeypatch.setattr(updater, 'read_archive', lambda ident: (updater.store.root/('bundle-'+ident+'.zip')).read_bytes())
    state['fail_install'] = True
    with pytest.raises(u.UpdateError):
        updater.execute('install', APPLY, PLAN, True)
    assert updater.store.read(PLAN)['status'] == 'used'
    assert updater.job(APPLY)['status'] == 'failed'
    assert 'partial' in updater.job(APPLY)['error']


def test_staged_file_symlink_and_unsafe_mode_rejected(manager):
    updater, _, _ = manager
    updater.prepare(PLAN)
    archive = updater.store.root/('bundle-'+PLAN+'.zip')
    archive.chmod(0o644)
    with pytest.raises(u.UpdateError):
        updater.read_archive(PLAN)
    archive.unlink()
    target = updater.store.root/'other'
    target.write_bytes(b'outside')
    archive.symlink_to(target)
    with pytest.raises(OSError):
        updater.read_archive(PLAN)


def test_old_stable_release_not_offered_to_newer_test_version(manager):
    updater, state, _ = manager
    state['version'] = '2.1~test1'
    assert not updater.check()['available']
    with pytest.raises(u.UpdateError):
        updater.prepare(PLAN)
    assert not state['commands'] or all(c[0] != 'bash' for c in state['commands'])


def test_checksum_duplicate_and_missing_target():
    with pytest.raises(u.UpdateError):
        u.checksum_manifest((('a'*64+'  file.zip\n')*2).encode(), 'file.zip')
    with pytest.raises(u.UpdateError):
        u.checksum_manifest(('a'*64+'  ../file.zip\n').encode(), 'file.zip')


def test_cli_requires_root(monkeypatch):
    monkeypatch.setattr(u.os, 'geteuid', lambda: 1000)
    with pytest.raises(SystemExit) as error:
        u.main(['check', '--json'])
    assert error.value.code == 2

@pytest.mark.parametrize('case', ['github-digest', 'manifest-digest', 'traversal', 'missing-manifest', 'wrong-deb'])
def test_download_and_package_tampering_stops_before_package_code(manager, monkeypatch, case):
    updater, state, responses = manager
    obj = json.loads(responses[u.API])
    zipurl = obj['assets'][0]['browser_download_url']
    sumsurl = obj['assets'][1]['browser_download_url']
    if case == 'github-digest':
        obj['assets'][0]['digest'] = 'sha256:'+'0'*64
    elif case == 'manifest-digest':
        responses[sumsurl] = ('0'*64+'  BuMaVory-ZFS-Manager-2.0.zip\n').encode()
        obj['assets'][1]['digest'] = 'sha256:'+hashlib.sha256(responses[sumsurl]).hexdigest()
    elif case in ('traversal', 'missing-manifest'):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as z:
            z.writestr('../escape' if case == 'traversal' else 'other', b'bad')
        obj, fresh = release(stream.getvalue())
        responses.clear()
        responses.update(fresh)
    elif case == 'wrong-deb':
        original = u.run
        monkeypatch.setattr(u, 'run', lambda args, **kwargs: 'other-package' if args[0] == 'dpkg-deb' else original(args, **kwargs))
    responses[u.API] = json.dumps(obj).encode()
    with pytest.raises((u.UpdateError, ValueError, OSError)):
        updater.prepare(PLAN)
    assert not any(c[0] == 'bash' for c in state['commands'])


def test_parallel_update_operation_is_rejected(manager):
    updater, state, _ = manager
    with updater.store.lock():
        with pytest.raises(u.UpdateError, match='busy'):
            updater.prepare(PLAN)
    assert not state['commands'] and not state['downloads']


def test_secure_archive_reader_with_root_owned_fixture(manager):
    if os.geteuid() != 0:
        pytest.skip('root-owned archive is exercised separately under fakeroot')
    updater, _, _ = manager
    updater.prepare(PLAN)
    raw = updater.read_archive(PLAN)
    assert hashlib.sha256(raw).hexdigest() == updater.store.read(PLAN)['digest']
    archive = updater.store.root/('bundle-'+PLAN+'.zip')
    archive.chmod(0o644)
    with pytest.raises(u.UpdateError):
        updater.read_archive(PLAN)


@pytest.mark.parametrize('command', ['status', 'job'])
def test_failed_status_and_jobs_remain_readable_as_json(manager, monkeypatch, capsys, command):
    updater, _, _ = manager
    updater.store.write(u.CACHE, {'checked_at': 1, 'latest_version': None, 'error': 'offline'})
    updater.store.write(PLAN, {'job': PLAN, 'status': 'failed', 'error': 'fixture failure'})
    monkeypatch.setattr(u.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(u, 'Updater', lambda: updater)
    args = [command, '--json'] + (['--job', PLAN] if command == 'job' else [])
    assert u.main(args) == 0
    assert json.loads(capsys.readouterr().out)['error']


def test_job_progress_exists_before_slow_metadata_fetch(manager):
    updater, _, _ = manager
    original = updater.fetch
    def fetch(url, limit):
        assert updater.job(PLAN)['status'] == 'running'
        assert updater.job(PLAN)['phase'] == 'check'
        return original(url, limit)
    updater.fetch = fetch
    assert updater.execute('check', PLAN)['status'] == 'complete'


def test_daily_service_entrypoint_only_checks_metadata(manager, monkeypatch, capsys):
    import configparser
    import shlex
    import zfsm_cli
    root = Path(__file__).resolve().parents[1]
    service = configparser.ConfigParser(interpolation=None)
    service.read(root/'systemd/pve-zfs-manager-update-check.service')
    timer = configparser.ConfigParser(interpolation=None)
    timer.read(root/'systemd/pve-zfs-manager-update-check.timer')
    assert timer['Timer']['OnCalendar'] == 'daily'
    args = shlex.split(service['Service']['ExecStart'])
    assert args[0] == '/usr/sbin/zfsm'
    updater, state, _ = manager
    monkeypatch.setattr(u.os, 'geteuid', lambda: 0)
    monkeypatch.setattr(u, 'Updater', lambda: updater)
    assert zfsm_cli.main(args[1:]) == 0
    assert json.loads(capsys.readouterr().out)['automatic_installation'] is False
    assert state['downloads'] == [u.API]
    assert not state['commands']
