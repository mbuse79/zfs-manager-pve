"""Real local archive/DEB fixtures under fakeroot; never install a package."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile

import pytest
import zfsm_cluster as cluster
import zfsm_cluster_cache as cache
import zfsm_cluster_remote as remote

pytestmark = pytest.mark.skipif(os.geteuid() != 0, reason='Root-owned bundle fixture: run separately with fakeroot')


@pytest.mark.parametrize('case', ['valid', 'corrupt-cache', 'bad-manifest', 'symlink', 'old-version', 'bad-mode'])
def test_verified_distribution_cache(case, monkeypatch):
    # Keep all cache ownership checks under fakeroot. Run the separate read-only
    # DEB metadata reader as the real unprivileged user: this container's tar
    # cannot emulate chown, which dpkg's metadata extraction otherwise attempts.
    real_check_output = subprocess.check_output
    def metadata_output(*args, **kwargs):
        env = dict(os.environ)
        env.pop('LD_PRELOAD', None)
        return real_check_output(*args, **kwargs, env=env)
    monkeypatch.setattr(cache.subprocess, 'check_output', metadata_output)
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='.cluster-cache-test-', dir=root) as td:
        td = Path(td)
        monkeypatch.setattr(cluster, 'STATE', td / 'state')
        monkeypatch.setattr(cache, '_store', lambda: cluster.Store(td / 'state/bundle'))
        # Store()'s default argument is the real path, so replace its default only
        # for this fixture's registration lock while retaining all safety checks.
        real_store = cluster.Store
        monkeypatch.setattr(cluster, 'Store', lambda path=None: real_store(path or td / 'state'))
        src = td / 'source'; src.mkdir()
        package = td / 'deb'; (package / 'DEBIAN').mkdir(parents=True); (package / 'DEBIAN').chmod(0o755)
        version = '1.0.0-34~rc9' if case == 'old-version' else cache.VERSION
        (package / 'DEBIAN/control').write_text('Package: pve-zfs-manager\nVersion: '+version+
            '\nArchitecture: all\nMaintainer: Fixture <fixture@example.invalid>\nDescription: Isolated metadata fixture\n')
        deb = src / ('pve-zfs-manager_' + cache.VERSION + '_all.deb')
        result = subprocess.run(['dpkg-deb', '--build', str(package), str(deb)], capture_output=True)
        assert result.returncode == 0, result.stderr.decode()
        (src / 'install_driver.py').write_text('raise Exception("MUST NOT EXECUTE")\n')
        (src / 'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n'
                                             for p in sorted(src.iterdir()) if p.name != 'SHA256SUMS'))
        if case == 'bad-manifest':
            (src / 'install_driver.py').write_text('modified')
        if case == 'symlink':
            (src / 'link').symlink_to('/etc/passwd')
        if case in ('bad-manifest', 'symlink', 'old-version'):
            with pytest.raises((ValueError, FileNotFoundError)):
                cache.register(src)
            assert not (td / 'state/bundle' / (cache.KEY + '.json')).exists()
            return
        meta = cache.register(src)
        assert meta['version'] == cache.VERSION
        assert meta['deb_sha256'] == hashlib.sha256(deb.read_bytes()).hexdigest()
        blob = td / 'state/bundle/package.zip'
        if case == 'corrupt-cache':
            blob.write_bytes(b'corrupt')
        elif case == 'bad-mode':
            blob.chmod(0o644)
        if case != 'valid':
            with pytest.raises(ValueError):
                cache.load()
            return
        assert cache.load() == (meta, blob.read_bytes())
        expanded = td / 'expanded'; expanded.mkdir()
        remote.unpack(cache.load()[1], meta['sha256'], expanded)
        assert (expanded / deb.name).read_bytes() == deb.read_bytes()
