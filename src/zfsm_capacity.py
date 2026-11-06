#!/usr/bin/env python3
"""Read-only ZFS capacity and snapshot-retention audit.

IMPORTANT: snapshot ``used`` is ZFS's per-snapshot accounting, never a
prediction of bytes reclaimed by deleting several snapshots. No ZFS writes,
cron edits or dataset mounts are performed here.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
import re
import subprocess
from pathlib import Path

LABELS = ('frequent', 'hourly', 'daily', 'weekly', 'monthly', 'yearly')
CRON_FILES = {
    'frequent': '/etc/cron.d/zfs-auto-snapshot',
    'hourly': '/etc/cron.hourly/zfs-auto-snapshot',
    'daily': '/etc/cron.daily/zfs-auto-snapshot',
    'weekly': '/etc/cron.weekly/zfs-auto-snapshot',
    'monthly': '/etc/cron.monthly/zfs-auto-snapshot',
    'yearly': '/etc/cron.d/pve-zfs-manager-yearly',
}
SNAP_PREFIX = re.compile(r'^zfs-auto-snap_(frequent|hourly|daily|weekly|monthly|yearly)-')
MAX_ROWS = 10000
MAX_BYTES = 16 * 1024 * 1024


class AuditError(ValueError):
    pass


def _positive(value, label):
    s = str(value)
    if not s.isascii() or not s.isdigit():
        raise AuditError(f'Invalid non-negative {label}: {s[:40]!r}')
    return int(s)


def parse_pool_lines(lines):
    items = []
    seen = set()
    for line in lines:
        cols = line.rstrip('\n').split('\t')
        if len(cols) != 5:
            raise AuditError('Unexpected zpool list columns')
        name, size, allocated, free, health = cols
        if not name or name in seen or '/' in name or '@' in name or len(name) > 200:
            raise AuditError('Invalid/duplicate pool name')
        seen.add(name)
        total = _positive(size, 'pool size')
        used = _positive(allocated, 'pool allocated')
        available = _positive(free, 'pool free')
        if used > total or available > total:
            raise AuditError('Invalid pool accounting')
        percent = round(100.0 * used / total, 1) if total else 0.0
        risk = 'critical' if percent >= 80 else 'warning' if percent >= 70 else 'normal'
        items.append({'name': name, 'size': total, 'allocated': used, 'free': available,
                      'capacity_percent': percent, 'level': risk, 'health': health})
        if len(items) > 128:
            raise AuditError('Pool limit exceeded')
    return sorted(items, key=lambda x: x['name'])


def parse_snapshot_lines(lines):
    out = []
    for line in lines:
        cols = line.rstrip('\n').split('\t')
        if len(cols) != 3 or '@' not in cols[0]:
            raise AuditError('Unexpected zfs snapshot columns')
        name, creation, used = cols
        ds, snap = name.split('@', 1)
        if not ds or not snap or len(name) > 1024 or any(c in name for c in '\r\n\x00'):
            raise AuditError('Invalid snapshot name')
        out.append({'dataset': ds, 'snapshot': snap,
                    'creation': _positive(creation, 'creation'),
                    'used': _positive(used, 'snapshot used')})
        if len(out) > MAX_ROWS:
            raise AuditError('Snapshot limit exceeded')
    return out


def read_retention_file(label, file):
    """Return configured --keep or None if unknown; no privileged assumptions."""
    path = Path(file)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32768:
        return None
    found = []
    for line in path.read_text(errors='replace').splitlines():
        if len(line) > 2048:
            return None
        disabled = line.startswith('# PVE-ZFS-MANAGER-DISABLED ')
        if disabled:
            line = line.removeprefix('# PVE-ZFS-MANAGER-DISABLED ')
        elif line.lstrip().startswith('#'):
            continue
        if 'zfs-auto-snapshot' not in line:
            continue
        match = re.search(r'--label=([a-z]+)(?=\s|$)', line)
        if not match or match.group(1) != label:
            continue
        keep = re.findall(r'(?<!\S)--keep=(\d+)(?=\s|$)', line)
        if len(keep) != 1:
            return None
        value = int(keep[0]); found.append(0 if disabled else value)
    return found[0] if len(found) == 1 else None


def build_report(pools, snapshots, policy, *, now=None, top_limit=10):
    """Pure audit algorithm, also used for fixture-backed integration tests."""
    if now is None:
        now = int(datetime.now(timezone.utc).timestamp())
    ds_stats = {}
    groups = defaultdict(lambda: defaultdict(int))
    labels_total = defaultdict(int)
    for item in snapshots:
        dataset, snap = item['dataset'], item['snapshot']
        if dataset not in ds_stats:
            ds_stats[dataset] = {'dataset': dataset, 'snapshots': 0, 'snapshot_used_bytes': 0,
                                 'oldest_creation': None, 'newest_creation': None}
        row = ds_stats[dataset]
        row['snapshots'] += 1
        row['snapshot_used_bytes'] += item['used']
        created = item['creation']
        row['oldest_creation'] = created if row['oldest_creation'] is None else min(row['oldest_creation'], created)
        row['newest_creation'] = created if row['newest_creation'] is None else max(row['newest_creation'], created)
        m = SNAP_PREFIX.match(snap)
        if m:
            groups[m.group(1)][dataset] += 1
            labels_total[m.group(1)] += 1
    ranked = sorted(ds_stats.values(), key=lambda d: (-d['snapshot_used_bytes'], -d['snapshots'], d['dataset']))
    for row in ranked:
        row['oldest_age_days'] = max(0, (now - row['oldest_creation']) // 86400)
    retention = []
    for label in LABELS:
        keep = policy.get(label)
        over = sum(max(0, count - keep) for count in groups[label].values()) if isinstance(keep, int) and keep > 0 else None
        retention.append({'label': label, 'keep': keep, 'observed_snapshots': labels_total[label],
                          'datasets': len(groups[label]), 'over_keep_observed': over,
                          'disabled': keep == 0,
                          'over_keep_is_deletion_forecast': False})
    return {'schema': 1, 'generated_at': int(now), 'pools': pools,
            'total_snapshots': len(snapshots), 'datasets_with_snapshots': len(ranked),
            'snapshot_used_total_bytes': sum(item['used'] for item in snapshots),
            'top_datasets': ranked[:top_limit], 'retention': retention,
            'snapshot_used_is_reclaim_forecast': False,
            'actions_performed': False}


def _capture(command, *, runner=subprocess.run):
    # Fixed, read-only binary paths and arguments; no shell or user input.
    result = runner(command, capture_output=True, text=True, timeout=25, check=False)
    if result.returncode != 0:
        raise AuditError(f'Read-only command failed: {command[0]} (exit {result.returncode})')
    if len(result.stdout.encode('utf-8')) > MAX_BYTES:
        raise AuditError('ZFS output limit exceeded')
    lines = result.stdout.splitlines()
    if len(lines) > MAX_ROWS + 128:
        raise AuditError('ZFS row limit exceeded')
    return lines


def collect_report(*, runner=subprocess.run, cron_files=None, now=None):
    pools = parse_pool_lines(_capture(['/usr/sbin/zpool', 'list', '-H', '-p', '-o',
                                       'name,size,alloc,free,health'], runner=runner))
    snapshots = parse_snapshot_lines(_capture(['/usr/sbin/zfs', 'list', '-H', '-p', '-t', 'snapshot',
                                               '-o', 'name,creation,used'], runner=runner))
    locations = CRON_FILES if cron_files is None else cron_files
    policy = {label: read_retention_file(label, locations[label]) if label in locations else None for label in LABELS}
    return build_report(pools, snapshots, policy, now=now)
