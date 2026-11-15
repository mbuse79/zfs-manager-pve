#!/usr/bin/env python3
"""Read-only, dynamic ZFS pool/physical-member topology for Proxmox VE.

Never decides whether a disk is free and never writes to ZFS or block devices.
Only zpool-imported pools are shown. PBS/passthrough disks therefore cannot
appear as unused storage here merely because they exist in `lsblk`.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import sys

POOL_RE = re.compile(r'^[A-Za-z0-9_.:-]{1,128}$')


def run(args, timeout=10):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, check=False)
    if p.returncode or len(p.stdout) > 1_000_000:
        raise RuntimeError('Lesende Abfrage fehlgeschlagen: ' + args[0])
    return p.stdout


def root_pool(pool_names):
    try:
        value = run(['/usr/bin/findmnt', '-n', '-o', 'FSTYPE,SOURCE', '-T', '/']).strip()
        parts = value.split(None, 1)
        if len(parts) == 2 and parts[0] == 'zfs':
            name = parts[1].split('/', 1)[0]
            if name in pool_names:
                return name
    except (OSError, RuntimeError, subprocess.TimeoutExpired):
        pass
    return None


def configured_storages(text):
    """Map ZFS pool names to enabled Proxmox storage IDs and dataset names."""
    result = {}
    current = None
    data = {}

    def finish():
        if not current or current[0] != 'zfspool' or data.get('disable') == '1':
            return
        dataset = data.get('pool', '')
        if not dataset or not all(POOL_RE.fullmatch(p) for p in dataset.split('/')):
            return
        pool = dataset.split('/', 1)[0]
        result.setdefault(pool, []).append({'id': current[1], 'dataset': dataset})

    for line in text.splitlines() + ['end: end']:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if line[0] not in (' ', '\t'):
            finish()
            m = re.fullmatch(r'([a-zA-Z0-9_-]+):\s+([a-zA-Z0-9_.-]+)', line.strip())
            current = (m.group(1), m.group(2)) if m else None
            data = {}
        elif current:
            parts = line.strip().split(None, 1)
            if len(parts) == 2:
                data[parts[0]] = parts[1]
    return result


def disk_metadata():
    """Optional model and physical size, keyed by resolved /dev paths."""
    try:
        raw = run(['/usr/bin/lsblk', '--json', '--bytes', '--output',
                   'PATH,KNAME,PKNAME,MODEL,SIZE,TYPE'], 5)
        data = json.loads(raw)
        rows = {}
        def add(items):
            for row in items:
                if not isinstance(row, dict):
                    continue
                name = row.get('path')
                if isinstance(name, str):
                    rows[os.path.realpath(name)] = row
                add(row.get('children', []))
        add(data.get('blockdevices', []))
        return rows
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, TypeError):
        return {}


def member_info(path, metadata):
    dev = os.path.realpath(path) if path.startswith('/dev/') else path
    entry = metadata.get(dev, {})
    if entry.get('type') == 'part':
        parent = entry.get('pkname')
        # lsblk returns a kernel block name; never derive device roles from name patterns.
        if isinstance(parent, str):
            entry = metadata.get('/dev/' + parent, entry)
    model = entry.get('model') or ''
    size = entry.get('size')
    return {'device': path, 'resolved_device': dev,
            'model': str(model).strip()[:100],
            'size_bytes': size if isinstance(size, int) and size >= 0 else None}


def parse_status(raw, pool, metadata):
    """Preserve zpool indentation as nested vdev / member nodes."""
    root = {'name': pool, 'kind': 'pool', 'status': 'UNKNOWN', 'children': []}
    in_config = False
    stack = []
    base_indent = None
    for line in raw.splitlines():
        if line.strip() == 'config:':
            in_config = True
            continue
        if not in_config:
            continue
        if line.strip().startswith('errors:'):
            break
        match = re.match(r'^(\s*)(\S+)\s+(ONLINE|DEGRADED|FAULTED|UNAVAIL|OFFLINE|REMOVED|AVAIL|INUSE|SUSPENDED)(?:\s|$)', line)
        if not match or match.group(2) == 'NAME':
            continue
        indent, name, status = len(match.group(1)), match.group(2), match.group(3)
        if base_indent is None:
            base_indent = indent
        if indent == base_indent and name == pool:
            root['status'] = status
            stack = [(indent, root)]
            continue
        if not stack:
            continue
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else root
        is_disk = name.startswith('/dev/')
        node = {'name': name, 'kind': 'disk' if is_disk else 'vdev',
                'status': status, 'children': []}
        if is_disk:
            node.update(member_info(name, metadata))
        parent['children'].append(node)
        stack.append((indent, node))
    return root


def discover(storage_file=Path('/etc/pve/storage.cfg')):
    names = [p.strip() for p in run(['/usr/sbin/zpool', 'list', '-H', '-o', 'name']).splitlines()]
    if len(names) > 100 or not all(POOL_RE.fullmatch(n) for n in names):
        raise RuntimeError('Ungueltige ZFS-Poolliste')
    text = storage_file.read_text('utf-8') if storage_file.is_file() else ''
    if len(text) > 512_000:
        raise RuntimeError('Proxmox-Speicherkonfiguration zu lang')
    storages = configured_storages(text)
    root = root_pool(set(names))
    metadata = disk_metadata()
    result = []
    for name in names:
        entry = parse_status(run(['/usr/sbin/zpool', 'status', '-P', name]), name, metadata)
        entry['system_pool'] = name == root
        entry['pve_storages'] = storages.get(name, [])
        # No claim that an unconfigured ZFS pool is free or safe to repurpose.
        entry['role'] = ('system-and-storage' if entry['system_pool'] and entry['pve_storages']
                         else 'system' if entry['system_pool']
                         else 'storage' if entry['pve_storages'] else 'additional')
        result.append(entry)
    return result


def main():
    if sys.argv[1:] != ['--json']:
        raise RuntimeError('Aufruf: pool_discovery.py --json')
    print(json.dumps(discover(), ensure_ascii=False, separators=(',', ':')))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as exc:
        print('Pool-Erkennung fehlgeschlagen: ' + str(exc), file=sys.stderr)
        sys.exit(2)
