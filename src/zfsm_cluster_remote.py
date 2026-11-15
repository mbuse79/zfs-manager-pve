#!/usr/bin/env python3
"""Trusted cluster transport helper; runs with Python's standard library only.

The controller sends this installed helper over authenticated SSH. Package code
is executed only after the pinned outer hash and the complete manifest pass.
"""
import hashlib
import fcntl
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import socket
import stat
import subprocess
import sys
import tempfile
import zipfile

MAX_ZIP = 100 * 1024 * 1024
MAX_EXPANDED = 200 * 1024 * 1024


def output(args, allowed=(0,)):
    p = subprocess.run(args, capture_output=True, text=True, timeout=30,
                       env={**os.environ, 'LC_ALL': 'C.UTF-8'})
    if p.returncode not in allowed:
        raise ValueError('Command failed: ' + args[0] + ': ' + p.stderr[-3000:])
    return p.stdout.strip()


def membership(rows):
    clusters = [r for r in rows if r.get('type') == 'cluster']
    if len(clusters) != 1 or clusters[0].get('quorate') != 1:
        raise ValueError('Cluster quorum required / Cluster-Quorum erforderlich')
    nodes = []
    for row in rows:
        if row.get('type') != 'node':
            continue
        name = row.get('name', '')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,62}', name):
            raise ValueError('Invalid cluster node name')
        nodeid = row.get('nodeid')
        if type(nodeid) is not int or nodeid < 1:
            raise ValueError('Invalid node ID')
        nodes.append({'name': name, 'nodeid': nodeid, 'online': row.get('online') == 1})
    if not nodes or len(nodes) > 64 or len({n['name'] for n in nodes}) != len(nodes):
        raise ValueError('Invalid cluster membership')
    identity = {'name': clusters[0]['name'],
                'nodes': sorted((n['name'], n['nodeid']) for n in nodes)}
    # JSON round trip ensures tuples/lists have the same representation remotely.
    return {'identity': json.loads(json.dumps(identity)), 'nodes': nodes}


def probe():
    package = output(['dpkg-query', '-W', '-f=${Status}\t${Version}',
                      'pve-zfs-manager'], (0, 1))
    return {'node': socket.gethostname().split('.')[0],
            'pve': output(['pveversion']),
            'arch': output(['dpkg', '--print-architecture']),
            'package': package,
            'audit': output(['dpkg', '--audit']),
            'cluster': membership(json.loads(output(['pvesh', 'get', '/cluster/status',
                                                     '--output-format', 'json'])))['identity']}


def unpack(data, digest, target):
    if len(data) > MAX_ZIP or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('ZIP SHA256 mismatch / ZIP-Prüfsumme stimmt nicht')
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        seen = set()
        size = 0
        if len(z.infolist()) > 5000:
            raise ValueError('Too many ZIP entries')
        for info in z.infolist():
            name = info.filename
            p = PurePosixPath(name)
            mode = info.external_attr >> 16
            canonical = p.as_posix()
            if (p.is_absolute() or '..' in p.parts or '\\' in name or
                    canonical != name.rstrip('/') or canonical in seen or
                    not p.parts or stat.S_IFMT(mode) not in (0, stat.S_IFREG, stat.S_IFDIR)):
                raise ValueError('Unsafe or duplicate ZIP entry')
            seen.add(canonical)
            size += info.file_size
            if size > MAX_EXPANDED:
                raise ValueError('Expanded ZIP too large')
        z.extractall(target)
    manifest = target / 'SHA256SUMS'
    entries = {}
    for line in manifest.read_text('ascii').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  ([A-Za-z0-9_.+~/ -]+)', line)
        if not match:
            raise ValueError('Invalid manifest')
        digest, name = match.groups()
        p = PurePosixPath(name)
        if (p.is_absolute() or '..' in p.parts or p.as_posix() != name or
                name == 'SHA256SUMS' or name in entries):
            raise ValueError('Unsafe manifest path')
        entries[name] = digest
    actual = {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()}
    if actual != set(entries) | {'SHA256SUMS'}:
        raise ValueError('Incomplete manifest')
    for name, digest in entries.items():
        if hashlib.sha256((target / name).read_bytes()).hexdigest() != digest:
            raise ValueError('Package checksum mismatch: ' + name)


def execute(mode, request, data):
    before = probe()
    if before != request['expected']:
        raise ValueError('Host changed; repeat preview / Host verändert; Vorschau erneuern')
    with tempfile.TemporaryDirectory(prefix='zfsm-cluster-') as td:
        target = Path(td)
        os.chmod(target, 0o700)
        unpack(data, request['sha256'], target)
        deb = target / ('pve-zfs-manager_' + request['version'] + '_all.deb')
        if (hashlib.sha256(deb.read_bytes()).hexdigest() != request['deb_sha256'] or
                output(['dpkg-deb', '-f', str(deb), 'Package']) != 'pve-zfs-manager' or
                output(['dpkg-deb', '-f', str(deb), 'Version']) != request['version']):
            raise ValueError('Unexpected DEB')
        args = [sys.executable, str(target / 'install_driver.py'), '--lang', request['lang']]
        if mode == 'check':
            args.append('--check-only')
        elif mode != 'install':
            raise ValueError('Invalid operation')
        if probe() != before:
            raise ValueError('Host changed before installer')
        p = subprocess.run(args, capture_output=True, text=True, timeout=600)
        result = {'ok': p.returncode == 0, 'log': (p.stdout + p.stderr)[-24000:]}
        if mode == 'install' and result['ok']:
            result['after'] = probe()
            expected = 'install ok installed\t' + request['version']
            if result['after']['package'] != expected:
                result['ok'] = False
                result['log'] += '\nInstalled package version/status does not match.'
        return result


def main():
    if os.geteuid() != 0:
        raise ValueError('root required / Root-Rechte erforderlich')
    mode = sys.argv[1]
    if mode == 'probe':
        result = probe()
    elif mode == 'health':
        p = subprocess.run(['/usr/sbin/pve-zfs-manager', 'check'], capture_output=True,
                           text=True, timeout=45)
        result = {'ok': p.returncode == 0, 'log': (p.stdout + p.stderr)[-24000:]}
    else:
        request = json.loads(sys.argv[2])
        if request['lang'] not in ('de', 'en'):
            raise ValueError('Invalid language')
        data = sys.stdin.buffer.read(MAX_ZIP + 1)
        fd = os.open('/run/pve-zfs-manager-cluster.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            meta = os.fstat(fd)
            if not stat.S_ISREG(meta.st_mode) or meta.st_uid != 0 or stat.S_IMODE(meta.st_mode) != 0o600:
                raise ValueError('Unsafe target deployment lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result = execute(mode, request, data)
        finally:
            os.close(fd)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(json.dumps({'ok': False, 'error': str(exc)}, ensure_ascii=False))
        sys.exit(1)
