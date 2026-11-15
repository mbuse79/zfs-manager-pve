"""RC7: real cron guard lines are not jobs; actual duplicates require selection."""
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import zfsm_host_audit as audit
from zfsm_autosnap_resolve import ConflictError, resolve_conflicts, restore_backup, backup_list, MARKER, _plan


def run(argv,timeout=5):
    if argv[0]=='dpkg-query':return 'ii '
    if argv[0]=='pvesr':return 'JobID Target Schedule Enabled\n'
    return ''


def fixture(root):
    a=root/'etc/cron.hourly/zfs-auto-snapshot';a.parent.mkdir(parents=True)
    a.write_text('#!/bin/sh\n# Only call zfs-auto-snapshot if it is available\n'
                 'which zfs-auto-snapshot > /dev/null || exit 0\n'
                 'exec zfs-auto-snapshot --quiet --syslog --label=hourly --keep=24 //\n')
    b=root/'etc/cron.d/custom-hourly';b.parent.mkdir(parents=True)
    b.write_text('# custom backup schedule\n0 * * * * root /usr/sbin/zfs-auto-snapshot --label=hourly --keep=12 //\n')
    return a,b


def inv(root):
    return audit.discover(root=root,run=run,which=lambda c:'/usr/sbin/'+c)


def test_proxmox_cron_guard_not_counted(tmp_path):
    a,b=fixture(tmp_path)
    b.unlink()
    r=inv(tmp_path)
    assert r['autosnap']['schedule_count']==1
    assert r['autosnap']['duplicate_labels']==[]
    assert r['autosnap']['schedules'][0]['line']==4
    assert r['autosnap']['ready']


def test_real_pve4_six_jobs_not_ten(tmp_path):
    a,b=fixture(tmp_path);b.unlink()
    for kind,keep in (('daily',7),('weekly',3),('monthly',3)):
        f=tmp_path/f'etc/cron.{kind}/zfs-auto-snapshot'
        f.parent.mkdir(parents=True)
        f.write_text('which zfs-auto-snapshot >/dev/null || exit 0\n'
                     f'exec zfs-auto-snapshot --label={kind} --keep={keep} //\n')
    frequently=tmp_path/'etc/cron.d/zfs-auto-snapshot'
    frequently.parent.mkdir(parents=True,exist_ok=True)
    frequently.write_text('*/15 * * * * root which zfs-auto-snapshot >/dev/null || exit 0 ; zfs-auto-snapshot --label=frequent --keep=9 //\n')
    yearly=tmp_path/'etc/cron.d/pve-zfs-manager-yearly'
    yearly.write_text('17 3 1 1 * root /usr/sbin/zfs-auto-snapshot --label=yearly --keep=2 //\n')
    r=inv(tmp_path)
    assert r['autosnap']['schedule_count']==6
    assert r['autosnap']['duplicate_labels']==[]
    assert r['autosnap']['ready']


def test_interactive_keep_standard_deactivates_custom_and_backs_up(tmp_path):
    a,b=fixture(tmp_path)
    r=inv(tmp_path)
    assert r['autosnap']['duplicate_labels']==['hourly']
    answers=iter(('2','ja')) if r['autosnap']['schedules'][1]['standard'] else iter(('1','ja'))
    # Safe ordering is alphabetical: /etc/cron.d/custom-hourly first, standard second.
    report=[]
    folder=resolve_conflicts(root=tmp_path,report=r,ask=lambda x:next(answers),output=report.append)
    assert folder and folder.is_dir()
    assert MARKER in b.read_text()
    assert MARKER not in a.read_text()
    assert inv(tmp_path)['autosnap']['duplicate_labels']==[]
    assert inv(tmp_path)['autosnap']['schedule_count']==1
    assert (folder/'manifest.json').is_file()
    assert (folder/'file-00.orig').read_bytes().startswith(b'# custom backup schedule')
    assert any('PASS' in s for s in report)


def test_interactive_keep_custom_deactivates_standard_only(tmp_path):
    a,b=fixture(tmp_path)
    old=b.read_bytes()
    answers=iter(('1','ja'))
    folder=resolve_conflicts(root=tmp_path,report=inv(tmp_path),ask=lambda x:next(answers),output=lambda x:None)
    assert MARKER in a.read_text()
    assert b.read_bytes()==old
    assert folder.is_dir()
    assert inv(tmp_path)['autosnap']['schedules'][0]['keep']==12


def test_declined_or_invalid_selection_changes_nothing(tmp_path):
    a,b=fixture(tmp_path)
    original=(a.read_bytes(),b.read_bytes())
    for choices in (('0',),('1','n'),('garbage',)):
        answers=iter(choices)
        with pytest.raises(ConflictError):
            resolve_conflicts(root=tmp_path,report=inv(tmp_path),ask=lambda x:next(answers),output=lambda x:None)
        assert (a.read_bytes(),b.read_bytes())==original
    assert not (tmp_path/'var').exists()


def test_stale_inventory_detected_before_write(tmp_path):
    a,b=fixture(tmp_path)
    r=inv(tmp_path)
    b.write_text(b.read_text().replace('--keep=12','--keep=10'))
    answers=iter(('2','ja'))
    with pytest.raises(ConflictError):
        resolve_conflicts(root=tmp_path,report=r,ask=lambda x:next(answers),output=lambda x:None)
    assert MARKER not in b.read_text()


def test_unknown_real_job_requires_selection(tmp_path):
    a,b=fixture(tmp_path);b.unlink()
    bad=tmp_path/'etc/cron.d/unknown-job';bad.write_text('0 * * * * root /usr/sbin/zfs-auto-snapshot //\n')
    r=inv(tmp_path)
    assert not r['autosnap']['duplicate_labels']
    assert r['autosnap']['schedule_count']==2
    answers=iter(('d','ja'))
    folder=resolve_conflicts(root=tmp_path,report=r,ask=lambda x:next(answers),output=lambda x:None)
    assert folder and MARKER in bad.read_text()
    assert inv(tmp_path)['autosnap']['schedule_count']==1


def test_symlinked_cron_source_not_changed(tmp_path):
    a,b=fixture(tmp_path)
    link=tmp_path/'etc/cron.d/linked';link.symlink_to(b)
    # Discovery ignores the link, source edits remain restricted to real files.
    r=inv(tmp_path)
    assert len(r['autosnap']['schedules'])==2
    with pytest.raises(ConflictError):
        _plan(tmp_path,[{'source':'/etc/cron.d/linked','line':2,'label':'hourly','keep':12}])


def test_backup_restore_rejects_unapproved_or_modified_config(tmp_path):
    a,b=fixture(tmp_path)
    before=(a.read_bytes(),b.read_bytes())
    answers=iter(('2','ja'))
    job=resolve_conflicts(root=tmp_path,report=inv(tmp_path),ask=lambda x:next(answers),output=lambda x:None)
    assert job.name in backup_list(tmp_path)
    with pytest.raises(ConflictError):
        restore_backup(job.name,root=tmp_path,ask=lambda x:'n',output=lambda x:None)
    b.write_text(b.read_text()+'# changed after resolution\n')
    with pytest.raises(ConflictError):
        restore_backup(job.name,root=tmp_path,ask=lambda x:'ja',output=lambda x:None)
    b.write_text(b.read_text().replace('# changed after resolution\n',''))
    restore_backup(job.name,root=tmp_path,ask=lambda x:'ja',output=lambda x:None)
    assert (a.read_bytes(),b.read_bytes())==before
    assert inv(tmp_path)['autosnap']['duplicate_labels']==['hourly']
