#!/usr/bin/env python3
"""Read-only, fail-closed, Proxmox zfspool guest-disk resolver.

Never invokes a ZFS write. Does not infer guest ownership from dataset names.
Filesystem roots are overridable only in injected unit tests via Python calls;
this CLI uses fixed system paths.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

DATASET = re.compile(r"^[A-Za-z0-9_.:~-]+(?:/[A-Za-z0-9_.:~-]+)*$")
STORAGE_ID = re.compile(r"^[a-zA-Z][a-zA-Z0-9_.-]{0,63}$")
DISK = re.compile(r"^(?:vm|subvol)-(\d+)-disk-\d+(?:-[A-Za-z0-9_.-]+)?$")
VOLUME = re.compile(r"^([A-Za-z][A-Za-z0-9_.-]{0,63}):((?:vm|subvol)-\d+-disk-\d+(?:-[A-Za-z0-9_.-]+)?)$")
KEYS_LXC = re.compile(r"^(?:rootfs|mp\d+)$")
KEYS_VM = re.compile(r"^(?:(?:scsi|virtio|sata|ide|efidisk|tpmstate)\d+)$")

class PolicyError(Exception):
    pass

def read_text(path):
    if not path.is_file():
        raise PolicyError(f"Konfigurationsdatei fehlt: {path}")
    data = path.read_text('utf-8')
    if len(data) > 512_000 or '\0' in data:
        raise PolicyError('Konfigurationsdatei zu gross/ungueltig')
    return data

def storage_pools(text):
    result = {}
    current = None
    options = {}
    def store():
        if current and current[0] == 'zfspool':
            name = current[1]
            pool = options.get('pool', '')
            if not DATASET.fullmatch(pool):
                raise PolicyError('ZFS-Pool in storage.cfg ungueltig')
            if options.get('disable', '0') == '1':
                return
            result[name] = pool
    for line in text.splitlines() + ['end: end']:
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line.startswith((' ', '\t')):
            store()
            hit = re.fullmatch(r'([a-zA-Z0-9_-]+):\s+([a-zA-Z0-9_.-]+)', line.strip())
            current = (hit.group(1), hit.group(2)) if hit else None
            options = {}
        elif current:
            pair = line.strip().split(None,1)
            if len(pair) == 2:
                options[pair[0]] = pair[1]
    return result

def live_guest_config(text):
    # The active guest configuration ends at the first Proxmox snapshot section.
    lines = []
    contains_snapshots = False
    for line in text.splitlines():
        if line.startswith('['):
            contains_snapshots = True
            break
        lines.append(line)
    opts = {}
    for line in lines:
        if ':' not in line or line.lstrip().startswith('#'):
            continue
        name, value = line.split(':',1)
        opts[name.strip()] = value.strip()
    return opts, contains_snapshots

def get_volid(s):
    first = s.split(',',1)[0].removeprefix('volume=').removeprefix('file=')
    match = VOLUME.fullmatch(first)
    return (match.group(1), match.group(2)) if match else None

def get_status(guest, vmid):
    binary = '/usr/sbin/pct' if guest == 'lxc' else '/usr/sbin/qm'
    proc = subprocess.run([binary, 'status', str(vmid)], capture_output=True,
                          text=True, timeout=8, check=False)
    if proc.returncode or not re.search(r'\bstatus:\s+(stopped|running)\b', proc.stdout):
        raise PolicyError('Gaststatus nicht eindeutig ermittelbar')
    return re.search(r'\bstatus:\s+(stopped|running)\b', proc.stdout).group(1)

def resolve_all(storage_file=Path('/etc/pve/storage.cfg'),
                lxc_dir=Path('/etc/pve/lxc'), vm_dir=Path('/etc/pve/qemu-server'),
                check_status=True):
    pools = storage_pools(read_text(storage_file))
    owners = {}
    for kind, directory, key_regex in [('lxc', lxc_dir, KEYS_LXC), ('vm', vm_dir, KEYS_VM)]:
        if not directory.is_dir():
            continue
        for path in directory.glob('*.conf'):
            if not re.fullmatch(r'[1-9]\d{1,8}\.conf', path.name):
                continue
            vmid = int(path.stem)
            raw = read_text(path)
            opts, has_pve_snapshots = live_guest_config(raw)
            disks, non_zfs_disks = [], []
            for key, value in opts.items():
                if not key_regex.fullmatch(key):
                    continue
                # ideX media=cdrom is not a writable guest disk.
                if kind == 'vm' and (value.startswith('none') or 'media=cdrom' in value):
                    continue
                volid = get_volid(value)
                if volid and volid[0] in pools:
                    store, volume = volid
                    if not DISK.fullmatch(volume) or int(DISK.fullmatch(volume).group(1)) != vmid:
                        raise PolicyError(f'Verdaechtige Laufwerkszuordnung bei Gast {vmid}')
                    if (kind == 'vm' and not volume.startswith('vm-')) or (kind == 'lxc' and not volume.startswith('subvol-')):
                        raise PolicyError(f'Unerwarteter Laufwerkstyp bei Gast {vmid}')
                    disks.append((key, pools[store] + '/' + volume))
                else:
                    non_zfs_disks.append(key)
            if not disks:
                continue
            state = get_status(kind,vmid) if check_status else 'stopped'
            protections = bool(opts.get('lock') or opts.get('template') == '1' or opts.get('protection') == '1')
            fingerprint = hashlib.sha256((raw + '\0' + read_text(storage_file)).encode()).hexdigest()
            # Include non-ZFS guest media in the multi-volume check; no partial live rollback.
            single_disk = len(disks) == 1 and len(non_zfs_disks) == 0
            for key, dataset in disks:
                if dataset in owners:
                    raise PolicyError('Mehrdeutiger Dataset-Besitzer: ' + dataset)
                owners[dataset] = {
                    'dataset': dataset, 'guest': kind, 'vmid': vmid, 'drive': key,
                    'display_name': opts.get('name' if kind == 'vm' else 'hostname','')[:100],
                    'state': state, 'disk_count': len(disks),
                    'other_disks': len(non_zfs_disks), 'single_disk': single_disk,
                    'protected': protections or has_pve_snapshots,
                    'fingerprint': fingerprint,
                    'can_create': not protections,
                    'can_delete': not (protections or has_pve_snapshots) and state == 'stopped',
                    'can_rollback': not (protections or has_pve_snapshots) and state == 'stopped' and len(non_zfs_disks) == 0,
                }
    return owners

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['list','resolve'])
    parser.add_argument('--dataset')
    parser.add_argument('--create', action='store_true')
    parser.add_argument('--stop', action='store_true')
    parser.add_argument('--rollback', action='store_true')
    args = parser.parse_args()
    owners = resolve_all()
    if args.command == 'list':
        print(json.dumps(list(owners.values()), separators=(',',':')))
        return
    if not args.dataset or not DATASET.fullmatch(args.dataset):
        raise PolicyError('Ungueltiges Dataset')
    row = owners.get(args.dataset)
    if not row or (row['protected'] and not (args.create and row['can_create'])):
        raise PolicyError('Dataset nicht eindeutig einem freigegebenen Gastdatentraeger zugeordnet')
    if args.create and not row['can_create']:
        raise PolicyError('Gast durch Sperre/Vorlage/Schutzstatus blockiert')
    if args.stop and row['state'] != 'stopped':
        raise PolicyError('Gast muss fuer diese Aktion gestoppt sein')
    if args.rollback and not row['single_disk']:
        raise PolicyError('Mehrere/zusätzliche Gastlaufwerke: einzelnes Dataset-Rollback gesperrt')
    print(json.dumps(row, separators=(',',':')))

if __name__ == '__main__':
    try:
        main()
    except (PolicyError, OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        print('GESPERRT: ' + str(exc), file=sys.stderr)
        sys.exit(2)
