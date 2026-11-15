"""v1.0.0-33: host-derived ZFS member mapping (all fixtures, no ZFS writes)."""
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src' / 'libexec'))
import pool_discovery as pools
import guest_policy


RPOOL = '''  pool: rpool
 state: ONLINE
config:

        NAME        STATE     READ WRITE CKSUM
        rpool       ONLINE       0     0     0
          mirror-0  ONLINE       0     0     0
            /dev/disk/by-id/nvme-A-part3  ONLINE 0 0 0
            /dev/disk/by-id/nvme-B-part3  ONLINE 0 0 0
errors: No known data errors
'''
RPOOL2 = '''  pool: rpool_2
 state: ONLINE
config:

        NAME        STATE     READ WRITE CKSUM
        rpool_2     ONLINE       0     0     0
          mirror-0  ONLINE       0     0     0
            /dev/disk/by-id/ata-FIKWOT-A-part1  ONLINE 0 0 0
            /dev/disk/by-id/ata-FIKWOT-B-part1  ONLINE 0 0 0
errors: No known data errors
'''


def test_discovery_system_and_pve_storage_are_dynamic(tmp_path, monkeypatch):
    cfg = tmp_path / 'storage.cfg'
    cfg.write_text('''zfspool: local-zfs
        pool rpool/data
zfspool: rpool_2
        pool rpool_2
pbs: PBS_4G
        datastore pbs
''')
    commands = []
    def fake_run(argv, timeout=10):
        commands.append(argv)
        if argv[:3] == ['/usr/sbin/zpool', 'list', '-H']:
            return 'rpool\nrpool_2\n'
        if argv[0] == '/usr/bin/findmnt':
            return 'zfs rpool/ROOT/pve-1\n'
        if argv[0] == '/usr/bin/lsblk':
            return '{"blockdevices":[]}'
        if argv[-2:] == ['-P', 'rpool']:
            return RPOOL
        if argv[-2:] == ['-P', 'rpool_2']:
            return RPOOL2
        raise AssertionError(argv)
    monkeypatch.setattr(pools, 'run', fake_run)
    result = pools.discover(cfg)
    assert [i['name'] for i in result] == ['rpool', 'rpool_2']
    assert result[0]['role'] == 'system-and-storage'
    assert result[1]['role'] == 'storage'
    assert result[1]['pve_storages'] == [{'id':'rpool_2','dataset':'rpool_2'}]
    assert result[1]['children'][0]['name'] == 'mirror-0'
    disks = result[1]['children'][0]['children']
    assert len(disks) == 2
    assert all(d['kind'] == 'disk' and d['status'] == 'ONLINE' for d in disks)
    assert all('/dev/sdb' not in json.dumps(i) for i in result)
    # Nothing here calls zfs destroy, zpool add, wipefs, or any mutation.
    assert all(argv[0] in ('/usr/sbin/zpool','/usr/bin/findmnt','/usr/bin/lsblk') for argv in commands)


def test_non_zfs_root_does_not_falsely_classify_system_pool(tmp_path, monkeypatch):
    cfg=tmp_path/'storage.cfg'
    cfg.write_text('')
    def fake(argv, timeout=10):
        if argv[1] == 'list':return 'backup\n'
        if argv[0].endswith('findmnt'):return 'ext4 /dev/sda2\n'
        if argv[0].endswith('lsblk'):return '{"blockdevices":[]}'
        return RPOOL.replace('rpool', 'backup')
    monkeypatch.setattr(pools, 'run', fake)
    output=pools.discover(cfg)
    assert output[0]['system_pool'] is False
    assert output[0]['role']=='additional'


def test_bulk_guest_statuses_missing_status_stays_unknown(tmp_path, monkeypatch):
    cfg=tmp_path/'storage.cfg'
    cfg.write_text('zfspool: data\n    pool rpool/data\n')
    vms=tmp_path/'qemu-server';vms.mkdir()
    lxcs=tmp_path/'lxc';lxcs.mkdir()
    (vms/'101.conf').write_text('name: test1\nscsi0: data:vm-101-disk-0,size=10G\n')
    (vms/'102.conf').write_text('name: test2\nscsi0: data:vm-102-disk-0,size=10G\n')
    calls=[]
    def fake_run(args, **kw):
        calls.append(args)
        class Result:
            returncode=0
            stdout='[{"type":"qemu","vmid":101,"status":"stopped"}]'
        return Result()
    def never_direct(*args):
        raise AssertionError('A full per-guest status sweep would be too slow')
    monkeypatch.setattr(guest_policy.subprocess, 'run', fake_run)
    monkeypatch.setattr(guest_policy, 'get_status', never_direct)
    rows=guest_policy.resolve_all(cfg,lxcs,vms,status_mode='bulk')
    assert len(calls)==1
    assert rows['rpool/data/vm-101-disk-0']['can_delete'] is True
    assert rows['rpool/data/vm-102-disk-0']['state']=='unknown'
    assert rows['rpool/data/vm-102-disk-0']['can_delete'] is False


def test_target_resolution_checks_only_selected_guest(tmp_path, monkeypatch):
    cfg=tmp_path/'storage.cfg'
    cfg.write_text('zfspool: data\n    pool rpool/data\n')
    vms=tmp_path/'qemu-server';vms.mkdir()
    lxcs=tmp_path/'lxc';lxcs.mkdir()
    for vmid in (101,102,103,104):
        (vms/f'{vmid}.conf').write_text(f'scsi0: data:vm-{vmid}-disk-0,size=10G\n')
    calls=[]
    def direct(kind, vmid):
        calls.append(vmid)
        return 'stopped'
    monkeypatch.setattr(guest_policy, 'get_status', direct)
    rows=guest_policy.resolve_all(cfg,lxcs,vms,status_mode='target',target_dataset='rpool/data/vm-103-disk-0')
    assert calls==[103]
    assert rows['rpool/data/vm-103-disk-0']['can_delete'] is True
    assert rows['rpool/data/vm-101-disk-0']['can_delete'] is False
