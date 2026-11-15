"""RC6: safe discovery of existing services and fail-closed retention adoption."""
from pathlib import Path
import importlib.util
import subprocess
import tempfile
from unittest.mock import patch
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import zfsm_host_audit as ha
from universal import Installer, JS_INSERT, VERSION
from test_repair_drift_v112 import SRC_GUI,SRC_NODES
import previous_patch


def mockrun(argv, timeout=5):
    key=' '.join(argv)
    if 'dpkg-query' in key:
        if 'zfs-auto-snapshot' in key:return 'ii '
        if 'bashclub-zsync' in key:return 'rc '
        if 'bashclub-checkzfs' in key:return 'ii '
        return ''
    if argv[:2]==['pvesr','list']:
        return 'JobID Target Schedule Enabled\n120-0 local/pve2 */15 yes\n'
    return ''


def make_cron(root, kind='hourly',keep=24):
    path=root/ha.STANDARD[kind]
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text('exec zfs-auto-snapshot --quiet --label='+kind+' --keep='+str(keep)+' //\n')
    return path


def make_unit(root,name,body):
    path=root/'etc/systemd/system'/name
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(body)


def test_real_pve4_pattern_detects_manual_zsync_and_preserves_autosnap(tmp_path):
    make_cron(tmp_path)
    make_cron(tmp_path,'daily',7)
    make_unit(tmp_path,'pve4-zsync-production.service',
              '[Service]\nExecStart=/opt/bashclub-zsync-test/bashclub-zsync -c /private/secret.conf\n')
    make_unit(tmp_path,'pve4-zsync-production.timer',
              '[Timer]\nUnit=pve4-zsync-production.service\n')
    r=ha.discover(root=tmp_path,run=mockrun,which=lambda cmd:'/bin/'+cmd)
    assert r['autosnap']['ready']
    assert r['autosnap']['schedule_count']==2
    assert r['autosnap_action']=='adopt'
    assert r['replication']['manual_zsync_detected']
    assert r['replication']['zsync_package']=='removed-config-left'
    assert r['replication']['native_pve_jobs']==1
    assert r['new_cleanup_timer_needed'] is False
    # Do not leak private paths, options or contents of unit definitions.
    assert '/private/secret' not in str(r) and '/opt/' not in str(r)
    assert list((tmp_path/'etc/cron.hourly').iterdir())[0].read_text().endswith('--keep=24 //\n')


def test_duplicate_autosnap_schedule_is_detected(tmp_path):
    make_cron(tmp_path)
    custom=tmp_path/'etc/cron.d/other-autosnap';custom.parent.mkdir(parents=True,exist_ok=True)
    custom.write_text('0 * * * * root /usr/sbin/zfs-auto-snapshot --label=hourly --keep=12 //\n')
    r=ha.discover(root=tmp_path,run=mockrun,which=lambda cmd:'/bin/'+cmd)
    assert r['autosnap']['duplicate_labels']==['hourly']
    assert not r['autosnap']['ready']
    assert r['autosnap_action']=='review'


def test_no_autosnap_package_requires_install_but_no_second_timer(tmp_path):
    def runner(argv,timeout=5):
        if argv[0]=='dpkg-query':return ''
        return ''
    r=ha.discover(root=tmp_path,run=runner,which=lambda cmd:None)
    assert r['autosnap_action']=='install'
    assert not r['new_cleanup_timer_needed']


def test_does_not_report_private_systemd_command_arguments(tmp_path):
    make_unit(tmp_path,'custom-cleaner.service','[Service]\nExecStart=/usr/local/bin/zfs destroy -r sensitive@name\n')
    r=ha.discover(root=tmp_path,run=mockrun,which=lambda cmd:None)
    assert 'custom-cleaner.service' in r['other_cleanup_units']
    assert 'sensitive@name' not in str(r)


def test_inventory_cli_json_and_gui_api_are_read_only():
    gui=(ROOT/'src/manager_patch.py').read_text()
    api=(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_text()
    assert 'zfsmRenderHostInventory' in gui
    assert "'zfsmanager-ro/host-inventory'" in gui
    assert "path => 'host-inventory', method => 'GET'" in api
    assert "['Sys.Audit']" in api
    assert 'zfsm_host_audit.py' in api
    assert 'zfs destroy' not in (ROOT/'src/zfsm_host_audit.py').read_text().replace('zfs destroy', '')


def test_upgrade_rc5_gui_and_api_is_reversible_with_backup():
    fixture=ROOT/'tests/fixtures/manager_patch_v134rc5.py'
    spec=importlib.util.spec_from_file_location('previous_rc5',fixture)
    old=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    with tempfile.TemporaryDirectory() as td:
        i=Installer(root=td,source=ROOT/'src',test_version='pve-manager/9.2.26/mock',dry_system=True)
        for f,txt in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
            f.parent.mkdir(parents=True,exist_ok=True);f.write_text(txt)
        i.install()
        before_policy=i.policy.read_bytes()
        before_nodes=i.nodes.read_bytes()
        legacy=previous_patch.HELPERS+old.BLOCK
        old_gui=i.gui.read_text().replace(JS_INSERT,legacy)
        old_api=(ROOT/'tests/fixtures/ZFSSnapshotViewer_v134rc5.pm').read_bytes()
        i.gui.write_text(old_gui)
        i.api.write_bytes(old_api)
        s=i.state();s['version']='1.0.0-34-rc5-dynamic-compat-installer'
        from hashlib import sha256
        s['installed_hashes']['gui']=sha256(old_gui.encode()).hexdigest()
        s['installed_hashes']['api']=sha256(old_api).hexdigest()
        i.save_state(s)
        i.install()
        assert i.state()['version']==VERSION
        assert i.gui.read_text().count(JS_INSERT)==1
        assert i.api.read_bytes()==(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_bytes()
        assert i.policy.read_bytes()==before_policy
        assert i.nodes.read_bytes()==before_nodes
        assert i.state().get('last_repair_backup')
        i.status()


def test_custom_cron_replicator_and_cleaner_detected_without_arguments(tmp_path):
    make_cron(tmp_path)
    f=tmp_path/'etc/cron.d/custom-cleaner';f.parent.mkdir(parents=True,exist_ok=True)
    f.write_text('0 1 * * * root zfs destroy tank@secret_snapshot\n'
                 '5 1 * * * root /usr/local/bin/zsync -c /private/credentials.conf\n'
                 '20 1 * * * root checkzfs --secret NOT_FOR_LOGGING\n')
    report=ha.discover(root=tmp_path,run=mockrun,which=lambda cmd:'/bin/'+cmd)
    assert '/etc/cron.d/custom-cleaner' in report['replication']['cron_sources']
    assert '/etc/cron.d/custom-cleaner' in report['monitoring']['cron_sources']
    assert '/etc/cron.d/custom-cleaner' in report['other_cleanup_cron']
    assert '/private/credentials' not in str(report)
    assert 'NOT_FOR_LOGGING' not in str(report)
