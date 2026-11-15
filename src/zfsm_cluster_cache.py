"""Root-owned, verified distribution copy of the locally installed RC10 bundle.

Kept outside the DEB to avoid self-referential hashes in the distribution archive.
Only the already verified ZIP installer registers it; node settings are excluded.
"""
import hashlib
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import zipfile

import zfsm_cluster_remote as remote

VERSION = '1.0.0-34~rc10+fix1'
KEY = '0' * 32


def _store():
    from zfsm_cluster import Store, STATE
    return Store(STATE / 'bundle')


def load():
    store = _store()
    meta = store.read(KEY)
    if (meta.get('version') != VERSION or meta.get('cache') is not True or
            set(meta) != {'version', 'sha256', 'deb_sha256', 'cache'} or
            any(not re.fullmatch('[a-f0-9]{64}', str(meta.get(k, '')))
                for k in ('sha256', 'deb_sha256'))):
        raise ValueError('Invalid cluster bundle registration / Ungültige Clusterpaket-Registrierung')
    fd = os.open(store.root / 'package.zip', os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as f:
        s = os.fstat(f.fileno())
        if (not stat.S_ISREG(s.st_mode) or s.st_uid != 0 or
                stat.S_IMODE(s.st_mode) != 0o600 or s.st_size > remote.MAX_ZIP):
            raise ValueError('Unsafe cluster bundle / Unsicheres Clusterpaket')
        data = f.read(remote.MAX_ZIP + 1)
    if hashlib.sha256(data).hexdigest() != meta['sha256']:
        raise ValueError('Cluster bundle checksum mismatch / Clusterpaket-Prüfsumme stimmt nicht')
    return meta, data


def register(source):
    """Called by the verified installer, never by an inventory/status request."""
    if os.geteuid() != 0:
        raise PermissionError('root required')
    source = Path(source)
    store = _store()
    store.directory(create=True)
    # Registration and deployment share the same coordinator lock.
    from zfsm_cluster import Store
    with Store().lock():
        fd, name = tempfile.mkstemp(prefix='.bundle-', dir=store.root)
        try:
            os.close(fd)
            total = 0
            with zipfile.ZipFile(name, 'w', compression=zipfile.ZIP_DEFLATED) as z:
                for p in sorted(source.rglob('*')):
                    if p.is_symlink() or not (p.is_dir() or p.is_file()):
                        raise ValueError('Unsafe bundle source')
                    if p.is_file():
                        total += p.stat().st_size
                        if total > remote.MAX_EXPANDED:
                            raise ValueError('Bundle too large')
                        z.write(p, p.relative_to(source).as_posix())
            data = Path(name).read_bytes()
            digest = hashlib.sha256(data).hexdigest()
            with tempfile.TemporaryDirectory(prefix='zfsm-cluster-register-') as td:
                target = Path(td)
                remote.unpack(data, digest, target)
                deb = target / ('pve-zfs-manager_' + VERSION + '_all.deb')
                for field, expected in [('Package', 'pve-zfs-manager'), ('Version', VERSION)]:
                    actual = subprocess.check_output(['dpkg-deb', '-f', str(deb), field], text=True).strip()
                    if actual != expected:
                        raise ValueError('Cluster DEB metadata mismatch')
                meta = {'version': VERSION, 'sha256': digest,
                        'deb_sha256': hashlib.sha256(deb.read_bytes()).hexdigest(), 'cache': True}
            os.chmod(name, 0o600)
            os.replace(name, store.root / 'package.zip')
            store.write(KEY, meta)
        finally:
            if os.path.exists(name):
                os.unlink(name)
    return meta
