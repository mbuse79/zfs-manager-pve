import json
import shutil
import subprocess
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import universal
from universal import Installer, InstallError, IMPORT, ROUTE, manager_patch, manager_patch_rc5, previous_patch, OLD_JS_INSERT, JS_INSERT

SRC_GUI='''Ext.define('PVE.node.Config', {
    initComponent: function () {
        var me = this;
        var caps = Ext.state.Manager.get('GuiCap');
        me.items = [];
        if (caps.nodes['Sys.Console']) {
            me.items.push({ xtype: 'panel', itemId: 'jsconsole' });
        }
        if (caps.nodes['Sys.Audit']) {
            me.items.push(
                {
                    xtype: 'proxmoxNodeServiceView',
                    itemId: 'services',
                });
        }
    },
});
Ext.define('OtherClass', {});
'''
SRC_NODES='''package PVE::API2::Nodes::Nodeinfo;
use PVE::API2::VZDump;
__PACKAGE__->register_method({
    subclass => "PVE::API2::Disks",
    path => 'disks',
});
__PACKAGE__->register_method({
    name => 'index',
    path => '',
});
package PVE::API2::Nodes;
__PACKAGE__->register_method({
    name => 'index',
    path => '',
});
'''
class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.inst=Installer(root=self.root,source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
        for path,data in ((self.inst.gui,SRC_GUI),(self.inst.nodes,SRC_NODES)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(data)
    def tearDown(self):self.tmp.cleanup()
    def test_clean_install_repair_uninstall(self):
        i=self.inst
        self.assertEqual(i.check()[1:],('clean','clean'))
        self.assertEqual(i.gui.read_text(),SRC_GUI)
        i.install(); i.status()
        self.assertTrue(i.state_file.is_file())
        self.assertEqual(i.classify(),('rc9','present'))
        self.assertEqual(i.gui.read_text().count(manager_patch.BLOCK),1)
        self.assertIn(IMPORT,i.nodes.read_text())
        self.assertIn(ROUTE,i.nodes.read_text())
        self.assertEqual(len(i.secret.read_text().strip()),64)
        self.assertEqual(i.secret.stat().st_mode & 0o777,0o600)
        i.gui.write_text(SRC_GUI)  # simulated Proxmox GUI package upgrade
        with self.assertRaises(InstallError):i.status()
        i.repair();i.status()
        i.uninstall()
        self.assertEqual(i.gui.read_text(),SRC_GUI)
        self.assertEqual(i.nodes.read_text(),SRC_NODES)
        self.assertFalse(i.api.exists())
        self.assertFalse(i.state_file.exists())
        self.assertTrue(i.backup_root.exists())
        self.assertTrue(i.secret.is_file())  # don't remove auth secrets inadvertently
    def test_adopt_existing_rc2_without_replacing(self):
        i=self.inst
        i.gui.write_text(i.add_gui(SRC_GUI))
        i.nodes.write_text(i.add_route(SRC_NODES))
        api,policy=i.expected()
        i.api.parent.mkdir(parents=True,exist_ok=True)
        i.api.write_bytes(api)
        i.policy.parent.mkdir(parents=True,exist_ok=True)
        i.policy.write_bytes(policy)
        self.assertEqual(i.check()[1:],('rc9','present'))
        i.install();i.status()
        i.uninstall()
        self.assertEqual(i.classify(),('rc9','present'))
    def test_unknown_layout_rejected_without_changes(self):
        i=self.inst
        gui=SRC_GUI.replace("itemId: 'jsconsole'","itemId: 'different'")
        i.gui.write_text(gui)
        with self.assertRaises(InstallError):i.install()
        self.assertEqual(i.gui.read_text(),gui)
        self.assertFalse(i.state_file.exists())
    def test_fail_on_partial_existing_footprint(self):
        i=self.inst
        i.api.parent.mkdir(parents=True,exist_ok=True)
        i.api.write_text('unknown source')
        with self.assertRaises(InstallError):i.check()
    def test_refuse_unknown_pve_version(self):
        i=self.inst;i.test_version='pve-manager/10.0.0/test'
        with self.assertRaises(InstallError):i.install()
    def test_api_route_roundtrip(self):
        i=self.inst
        self.assertEqual(i.remove_route(i.add_route(SRC_NODES)),SRC_NODES)
        self.assertEqual(i.remove_gui(i.add_gui(SRC_GUI)),SRC_GUI)
    def test_admin_dir_symlink_rejected(self):
        i=self.inst;i.admindir.parent.mkdir(parents=True,exist_ok=True)
        i.admindir.symlink_to(i.root)
        with self.assertRaises(InstallError):i.check()
    def test_generated_gui_js_syntax(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node.js nur fuer Build-Test')
        gui=self.inst.add_gui(SRC_GUI)
        candidate=self.root/'synthetic-pvemanagerlib.js'
        candidate.write_text(gui)
        p=subprocess.run([node,'--check',str(candidate)],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
    def test_no_snapshot_or_cron_mutation(self):
        i=self.inst
        i.install()
        content=i.yearly.read_text()
        self.assertIn('--label=yearly --keep=3',content)
        self.assertNotIn('zfs snapshot',content)
        i.uninstall()
        self.assertEqual(content,i.yearly.read_text())  # cron retained after remove

    def test_adopted_install_repair_after_gui_update(self):
        i=self.inst
        i.gui.write_text(i.add_gui(SRC_GUI))
        i.nodes.write_text(i.add_route(SRC_NODES))
        api,policy=i.expected()
        i.api.parent.mkdir(parents=True,exist_ok=True); i.api.write_bytes(api)
        i.policy.parent.mkdir(parents=True,exist_ok=True); i.policy.write_bytes(policy)
        i.install()
        self.assertTrue(i.state()['adopted_rc2'])
        i.gui.write_text(SRC_GUI)
        with self.assertRaises(InstallError):i.status()
        i.repair()
        i.status()
        self.assertEqual(i.gui.read_text(),i.add_gui(SRC_GUI))
        i.uninstall() # Never remove originally adopted code
        self.assertEqual(i.gui.read_text(),i.add_gui(SRC_GUI))

    def test_upgrade_existing_registration_without_reinstalling_gui(self):
        i=self.inst
        i.install(); current_gui=i.gui.read_bytes()
        state=i.state();state['version']='1.0.0-rc3-installer'; i.save_state(state)
        i.install()
        self.assertEqual(i.state()['version'],universal.VERSION)
        self.assertEqual(i.gui.read_bytes(),current_gui)
        i.uninstall()

    def test_repair_rejects_tampered_adopted_backend(self):
        i=self.inst
        i.gui.write_text(i.add_gui(SRC_GUI));i.nodes.write_text(i.add_route(SRC_NODES))
        api,policy=i.expected()
        i.api.parent.mkdir(parents=True,exist_ok=True);i.api.write_bytes(api)
        i.policy.parent.mkdir(parents=True,exist_ok=True);i.policy.write_bytes(policy)
        i.install()
        i.gui.write_text(SRC_GUI)
        i.api.write_bytes(b'untrusted replacement')
        with self.assertRaises(InstallError):i.repair()
        self.assertEqual(i.gui.read_text(),SRC_GUI)

    def test_repair_rejects_unknown_layout_after_update(self):
        i=self.inst
        i.install()
        altered=SRC_GUI.replace("itemId: 'jsconsole'", "itemId: 'gone'")
        i.gui.write_text(altered)
        with self.assertRaises(InstallError):i.repair()
        self.assertEqual(i.gui.read_text(),altered)

    def test_clean_pve_911_with_matching_fingerprints(self):
        i=self.inst
        from universal import sha
        i.test_version='pve-manager/9.1.1/test'
        i.stock_911={'gui': sha(i.read(i.gui)), 'nodes': sha(i.read(i.nodes))}
        i.precheck()
        i.install()
        i.status()
        i.uninstall()
        self.assertEqual(i.gui.read_text(), SRC_GUI)
        self.assertEqual(i.nodes.read_text(), SRC_NODES)

    def test_clean_pve_911_wrong_original_hash_rejected(self):
        i=self.inst
        i.test_version='pve-manager/9.1.1/test'
        i.stock_911={'gui': '0'*64, 'nodes':'1'*64}
        before=i.gui.read_bytes()
        with self.assertRaises(InstallError):i.precheck()
        with self.assertRaises(InstallError):i.install()
        self.assertEqual(i.gui.read_bytes(),before)
        self.assertFalse(i.state_file.exists())

    def test_911_to_921_upgrade_repair(self):
        from universal import sha
        i=self.inst
        i.test_version='pve-manager/9.1.1/test'
        i.stock_911={'gui':sha(i.read(i.gui)), 'nodes':sha(i.read(i.nodes))}
        i.install()
        i.test_version='pve-manager/9.2.21/test'
        i.gui.write_text(SRC_GUI)
        i.nodes.write_text(SRC_NODES)
        with self.assertRaises(InstallError):i.status()
        i.repair()
        i.status()
        i.uninstall()

    def test_shell_prechecks_before_dependency_installation(self):
        content=(ROOT/'install.sh').read_text()
        self.assertIn('universal.py\" precheck',content)
        self.assertIn('--no-remove --no-upgrade',content)
        self.assertLess(content.index('universal.py\" precheck'),content.index('apt-get --simulate'))

    def test_shell_installer_calls_status_without_double_dash(self):
        content=(ROOT/'install.sh').read_text()
        self.assertIn('/usr/sbin/pve-zfs-manager status',content)
        self.assertNotIn('/usr/sbin/pve-zfs-manager --status',content)

    def test_upgrade_actual_rc5_code_to_rc6_migrates_exactly_once(self):
        i=self.inst
        legacy=previous_patch.HELPERS+manager_patch_rc5.BLOCK
        i.gui.write_text(SRC_GUI.replace("        if (caps.nodes['Sys.Audit']) {",legacy+"        if (caps.nodes['Sys.Audit']) {",1))
        # Confirm this is actually the legacy block in a valid source scope.
        self.assertEqual(i.classify()[0], 'rc5')
        i.nodes.write_text(i.add_route(SRC_NODES))
        api,pol=i.expected()
        i.api.parent.mkdir(parents=True,exist_ok=True);i.api.write_bytes(api)
        i.policy.parent.mkdir(parents=True,exist_ok=True);i.policy.write_bytes(pol)
        # Simulate existing RC5 registered state (adopted RC2 test system).
        i.save_state({'version':'1.0.0-rc5-installer','adopted_rc2':True,
                      'proxmox_at_install':'pve-manager/9.1.1/test'})
        i.install()
        self.assertEqual(i.classify(),('rc9','present'))
        self.assertEqual(i.gui.read_text().count(JS_INSERT),1)
        self.assertNotIn(OLD_JS_INSERT,i.gui.read_text())
        first=i.gui.read_bytes()
        i.install()
        self.assertEqual(i.gui.read_bytes(),first)
        self.assertEqual(i.state()['version'],universal.VERSION)

    def test_auto_reconcile_after_full_proxmox_upgrade(self):
        i=self.inst
        i.install()
        original=i.gui.read_bytes()
        i.gui.write_text(SRC_GUI)
        i.nodes.write_text(SRC_NODES)
        i.reconcile()
        i.status()
        self.assertEqual(i.gui.read_bytes(),original)
        self.assertEqual(i.nodes.read_text(),i.add_route(SRC_NODES))
        self.assertTrue(i.state()['last_repair_backup'])
        backup_count=len(list(i.backup_root.iterdir()))
        i.reconcile()
        self.assertEqual(len(list(i.backup_root.iterdir())),backup_count)
        self.assertEqual(i.gui.read_bytes(),original)

    def test_auto_reconcile_partial_api_only_upgrade(self):
        i=self.inst;i.install()
        old_gui=i.gui.read_bytes()
        i.nodes.write_text(SRC_NODES)
        i.reconcile()
        self.assertEqual(i.gui.read_bytes(),old_gui)
        i.status()

    def test_auto_reconcile_new_pve_recovers(self):
        i=self.inst;i.install()
        i.gui.write_text(SRC_GUI);i.nodes.write_text(SRC_NODES)
        i.test_version='pve-manager/9.2.24/test'
        i.reconcile()
        i.status()
        self.assertIn(universal.JS_INSERT,i.gui.read_text())
        self.assertIn("path => 'zfsmanager-ro'",i.nodes.read_text())

    def test_auto_reconcile_tampered_backend_refuses_changes(self):
        i=self.inst;i.install()
        i.gui.write_text(SRC_GUI);i.nodes.write_text(SRC_NODES)
        i.policy.write_text('unknown file')
        with self.assertRaises(InstallError):i.reconcile()
        self.assertEqual(i.gui.read_text(),SRC_GUI)
        self.assertEqual(i.nodes.read_text(),SRC_NODES)

    def test_reconcile_deferred_when_apt_dpkg_busy(self):
        from unittest.mock import patch
        i=self.inst;i.install()
        i.gui.write_text(SRC_GUI)
        old_root=i.root
        i.root=Path('/')
        try:
            with patch.object(i, '_package_manager_busy',return_value=True):
                i.reconcile()
        finally:
            i.root=old_root
        self.assertEqual(i.gui.read_text(),SRC_GUI)

    def test_js_dataset_row_click_and_state_preservation(self):
        src=(ROOT/'src/manager_patch.py').read_text()
        self.assertIn('cellclick: function (treeView, cell, cellIndex, record, row, index, event)',src)
        self.assertIn('toggleOnDblClick: false',src)
        self.assertIn("record.get('snapshot')",src)
        self.assertIn('.x-btn-inner',src)
        self.assertIn('.x-tree-expander',src)
        self.assertIn('state.expandedDatasets[dataset] === true',src)
        self.assertIn('node.isExpanded()',src)
        self.assertIn('PVELangCookie',src)
        self.assertIn("dataset-snapshot-create",src)

    def test_systemd_watch_and_fallback_timer_packaged(self):
        unit_dir=ROOT/'systemd'
        self.assertIn('PathChanged=/usr/share/pve-manager/js/pvemanagerlib.js',
                      (unit_dir/'pve-zfs-manager-reconcile.path').read_text())
        self.assertIn('PathChanged=/usr/share/perl5/PVE/API2/Nodes.pm',
                      (unit_dir/'pve-zfs-manager-reconcile.path').read_text())
        self.assertIn('OnUnitInactiveSec=2min',
                      (unit_dir/'pve-zfs-manager-reconcile.timer').read_text())
        self.assertIn('pve-zfs-manager reconcile',
                      (unit_dir/'pve-zfs-manager-reconcile.service').read_text())
        script=(ROOT/'build_deb.sh').read_text()
        self.assertIn('systemctl enable --now pve-zfs-manager-reconcile.path pve-zfs-manager-reconcile.timer',script)
        self.assertIn('systemctl disable --now',script)
        self.assertIn('reconcile|',script)


    def test_rc6_real_files_upgrade_to_rc8_with_backend_migration(self):
        from universal import RC6_JS_INSERT
        i=self.inst
        before_gui=SRC_GUI.replace("        if (caps.nodes['Sys.Audit']) {",
                                   RC6_JS_INSERT+"        if (caps.nodes['Sys.Audit']) {",1)
        i.gui.write_text(before_gui)
        i.nodes.write_text(i.add_route(SRC_NODES))
        i.api.parent.mkdir(parents=True,exist_ok=True);i.api.write_bytes(i.rc6_api())
        i.policy.parent.mkdir(parents=True,exist_ok=True)
        i.policy.write_bytes(i.expected()[1])
        i.save_state({'version':'1.0.0-rc6-installer','adopted_rc2':False,
                      'proxmox_at_install':'pve-manager/9.1.1/test'})
        self.assertEqual(i.check()[1:],('rc6','present'))
        i.install()
        i.status()
        self.assertEqual(i.classify(),('rc9','present'))
        self.assertEqual(i.api.read_bytes(),i.expected()[0])
        self.assertNotEqual(i.api.read_bytes(),i.rc6_api())
        self.assertEqual(i.state()['version'],universal.VERSION)
        first_gui=i.gui.read_bytes()
        first_api=i.api.read_bytes()
        i.install()
        self.assertEqual(i.gui.read_bytes(),first_gui)
        self.assertEqual(i.api.read_bytes(),first_api)
        self.assertTrue(any(p.name.startswith('migrate-') for p in i.backup_root.iterdir()))

    def test_rc6_migration_recovers_when_pve_overwrote_both_gui_api_hooks(self):
        i=self.inst
        i.api.parent.mkdir(parents=True,exist_ok=True);i.api.write_bytes(i.rc6_api())
        i.policy.parent.mkdir(parents=True,exist_ok=True);i.policy.write_bytes(i.expected()[1])
        i.save_state({'version':'1.0.0-rc6-installer','adopted_rc2':False,
                      'proxmox_at_install':'pve-manager/9.1.1/test'})
        i.install()
        i.status()
        self.assertEqual(i.nodes.read_text(),i.add_route(SRC_NODES))
        self.assertEqual(i.classify(),('rc9','present'))

    def test_rc6_tampered_backend_upgrade_fails_closed(self):
        from universal import RC6_JS_INSERT
        i=self.inst
        i.gui.write_text(SRC_GUI.replace("        if (caps.nodes['Sys.Audit']) {",
                                         RC6_JS_INSERT+"        if (caps.nodes['Sys.Audit']) {",1))
        i.nodes.write_text(i.add_route(SRC_NODES))
        i.api.parent.mkdir(parents=True,exist_ok=True);i.api.write_bytes(b'foreign code')
        i.policy.parent.mkdir(parents=True,exist_ok=True);i.policy.write_bytes(i.expected()[1])
        i.save_state({'version':'1.0.0-rc6-installer','adopted_rc2':False})
        before_gui=i.gui.read_bytes()
        with self.assertRaises(InstallError):i.install()
        self.assertEqual(i.gui.read_bytes(),before_gui)
        self.assertEqual(i.api.read_bytes(),b'foreign code')

    def test_one_cell_click_toggles_and_actions_remain_separate(self):
        from universal import manager_patch
        import re
        source=manager_patch.BLOCK
        start=source.index('cellclick: function (')
        end=source.index('\n                                },',start)
        function=source[start:].split('cellclick: ',1)[1][:end-start-len('cellclick: ')]+'\n}'
        self.assertIn('toggleOnDblClick: false',source)
        self.assertIn('dataset-snapshot-create',source)
        program='''const assert = require('node:assert/strict');
const click = FUNCTION;
let open = false, expansions = 0, collapses = 0;
let record = {get: (key) => key === 'snapshot' ? null : undefined,
  isExpanded: () => open,
  expand: () => {open = true;expansions++;},
  collapse: () => {open = false;collapses++;}};
click(null,null,0,record,null,0,{getTarget:()=>false});
assert.equal(expansions,1);
click(null,null,0,record,null,0,{getTarget:()=>false});
assert.equal(collapses,1);
click(null,null,0,record,null,0,{getTarget:()=>true});
assert.equal(expansions,1);
record.get = (key) => key === 'snapshot' ? 'snap1' : undefined;
click(null,null,0,record,null,0,{getTarget:()=>false});
assert.equal(expansions,1);
'''.replace('FUNCTION',function)
        node=shutil.which('node')
        if not node:self.skipTest('Node.js fehlt')
        result=subprocess.run([node,'-e',program],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_perl_host_snapshot_runtime_security_mock(self):
        if not shutil.which('perl'):self.skipTest('Perl fehlt')
        env=os.environ.copy()
        env['PERL5LIB']=str(ROOT/'src')
        run=subprocess.run(['perl',str(ROOT/'tests/perl_mock_rc7.pl')],
                           cwd=ROOT,capture_output=True,text=True,env=env)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertIn('PASS:',run.stdout)

    def test_backend_host_snapshot_creation_requires_explicit_dataset_and_admin(self):
        code=(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_text()
        self.assertIn("name=>'dataset_snapshot_create'",code)
        self.assertIn("_require_zfsmgr_admin($p->{node})",code)
        self.assertIn("confirm=>{type=>'string',maxLength=>240}",code)
        self.assertIn('Gast-Datentraeger erfordern Gast-Snapshot-Schnittstelle',code)
        self.assertIn("_run_zfs_write('snapshot'",code)
        self.assertIn("_run_capture('/usr/sbin/zfs', 'list'",code)

    def test_no_host_delete_or_rollback_execution_endpoint(self):
        code=(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_text()
        self.assertNotIn("path=>'dataset-snapshot-delete'",code)
        self.assertNotIn("path=>'dataset-rollback'",code)
        self.assertIn("path=>'guest-snapshot-delete'",code)
        self.assertIn("path=>'guest-rollback'",code)

if __name__=='__main__':unittest.main()

# Additional RC8 safety and release compatibility checks.
class RC8SafetyTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.i=Installer(root=self.root,source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
        for path,data in ((self.i.gui,SRC_GUI),(self.i.nodes,SRC_NODES)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(data)
    def tearDown(self):self.tmp.cleanup()
    def test_real_rc7_to_rc8_transaction(self):
        from universal import RC7_JS_INSERT
        i=self.i
        i.gui.write_text(SRC_GUI.replace("        if (caps.nodes['Sys.Audit']) {",RC7_JS_INSERT+"        if (caps.nodes['Sys.Audit']) {",1))
        i.nodes.write_text(i.add_route(SRC_NODES))
        i.api.parent.mkdir(parents=True,exist_ok=True)
        i.api.write_bytes(i.rc7_api())
        i.policy.parent.mkdir(parents=True,exist_ok=True)
        i.policy.write_bytes(i.expected()[1])
        i.save_state({'version':'1.0.0-rc7-installer','adopted_rc2':False,
                      'proxmox_at_install':'pve-manager/9.1.1/test'})
        self.assertEqual(i.check()[1:],('rc7','present'))
        i.install();i.status()
        self.assertEqual(i.classify(),('rc9','present'))
        self.assertEqual(i.api.read_bytes(),i.expected()[0])
        self.assertNotEqual(i.api.read_bytes(),i.rc7_api())
        self.assertTrue(any(x.name.startswith('migrate-') for x in i.backup_root.iterdir()))
        before=i.gui.read_bytes()
        i.install();i.status()
        self.assertEqual(i.gui.read_bytes(),before)
        i.uninstall()
    def test_rc7_to_rc8_invalid_backend_preserved(self):
        from universal import RC7_JS_INSERT
        i=self.i
        i.gui.write_text(SRC_GUI.replace("        if (caps.nodes['Sys.Audit']) {",RC7_JS_INSERT+"        if (caps.nodes['Sys.Audit']) {",1))
        i.nodes.write_text(i.add_route(SRC_NODES))
        i.api.parent.mkdir(parents=True,exist_ok=True)
        i.api.write_text('foreign backend')
        i.policy.parent.mkdir(parents=True,exist_ok=True)
        i.policy.write_bytes(i.expected()[1])
        i.save_state({'version':'1.0.0-rc7-installer','adopted_rc2':False})
        original=i.gui.read_bytes()
        with self.assertRaises(InstallError):i.install()
        self.assertEqual(i.gui.read_bytes(),original)
    def test_ui_has_no_text_confirmation_and_two_step_danger(self):
        src=(ROOT/'src/manager_patch.py').read_text()
        self.assertNotIn('zfsPrompt',src)
        self.assertNotIn('prompt:true',src)
        self.assertNotIn('Type the exact dataset name',src)
        self.assertIn('zfsCriticalWarning',src)
        self.assertIn('critical_ack:1',src)
        self.assertIn('critical_ack:0',src)
        self.assertIn('host-snapshot-delete-preview',src)
        self.assertIn('host-rollback-preview',src)
        self.assertIn('border:3px solid #c62828',src)
        self.assertIn('zfs-final-ack',src)
        self.assertIn('CREATE-DATASET:',src)
        self.assertIn('toggleOnDblClick: false',src)
    def test_perl_critical_ack_gate(self):
        proc=subprocess.run(['perl',str(ROOT/'tests/perl_mock_rc9.pl')],
            cwd=ROOT,env={**os.environ,'PERL5LIB':str(ROOT/'src')},capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)


class RC8R2RegressionTest(unittest.TestCase):
    def test_upgrade_installed_rc8_to_r2_and_idempotence(self):
        from universal import RC8_JS_INSERT
        with tempfile.TemporaryDirectory() as td:
            inst=Installer(root=td,source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
            inst.gui.parent.mkdir(parents=True,exist_ok=True)
            inst.nodes.parent.mkdir(parents=True,exist_ok=True)
            inst.gui.write_text(SRC_GUI.replace("        if (caps.nodes['Sys.Audit']) {",RC8_JS_INSERT+"        if (caps.nodes['Sys.Audit']) {",1))
            inst.nodes.write_text(inst.add_route(SRC_NODES))
            inst.api.parent.mkdir(parents=True,exist_ok=True)
            inst.api.write_bytes(inst.rc8r2_api())
            inst.policy.parent.mkdir(parents=True,exist_ok=True)
            inst.policy.write_bytes(inst.expected()[1])
            inst.save_state({'version':'1.0.0-rc8-installer','adopted_rc2':False})
            self.assertEqual(inst.classify(),('rc8','present'))
            self.assertEqual(inst.check()[1:],('rc8','present'))
            before_api=inst.api.read_bytes()
            inst.install()
            inst.status()
            self.assertEqual(inst.classify(),('rc9','present'))
            self.assertEqual(inst.state()['version'],universal.VERSION)
            self.assertNotEqual(inst.api.read_bytes(),before_api)
            self.assertEqual(inst.api.read_bytes(),inst.expected()[0])
            self.assertIn('safeZFSValue(title)',inst.gui.read_text())
            self.assertNotIn("'<strong>'+safe(title)",inst.gui.read_text())
            self.assertTrue(any(x.name.startswith('repair-') for x in inst.backup_root.iterdir()))
            updated=inst.gui.read_bytes()
            inst.install()
            self.assertEqual(inst.gui.read_bytes(),updated)
            inst.gui.write_text(SRC_GUI)
            inst.reconcile()
            inst.status()
            self.assertEqual(inst.gui.read_bytes(),updated)

    def test_rc8_r2_critical_modal_runs_in_actual_js_scope(self):
        node=shutil.which('node')
        if not node:self.skipTest('Node.js fehlt')
        block=manager_patch.BLOCK
        start=block.index('var zfsCriticalWarning = function')
        end=block.index("if (caps.nodes['Sys.Audit'])",start)
        expression=block[start:end]
        # Execute the actual outer-scope helper independently, where the
        # afterrender-only `safe` identifier is intentionally unavailable.
        runner=r"""
const vm=require('vm');
const assert=require('node:assert/strict');
let config, called=0, win;
const btn={disabled:true,setDisabled(v){this.disabled=v;},up(){return win;}};
const cb={checked:false,getValue(){return this.checked;},up(){return win;}};
const Ext={create(type,cfg){ assert.equal(type,'Ext.window.Window');config=cfg;
    win={show(){},close(){},down(selector){return selector==='#zfs-final-ack'?cb:btn;}};
    return win;
}};
const ctx={Ext,zfsL:s=>s,safeZFSValue:s=>String(s).replaceAll('<','&lt;')};
vm.runInNewContext(FUNCTION+'\nthis.zfsCriticalWarning=zfsCriticalWarning;',ctx);
ctx.zfsCriticalWarning('Critical <warning>','3 Snapshots','Confirm',()=>{called++;});
assert.match(config.items[0].html,/Critical &lt;warning>/);
assert.equal(config.items[1].itemId,'zfs-final-ack');
assert.equal(config.buttons[1].disabled,true);
cb.checked=true;
config.items[1].listeners.change(cb,true);
assert.equal(btn.disabled,false);
config.buttons[1].handler(btn);
assert.equal(called,1);
console.log('PASS: RC8-R2 critical UI opens and executes only after checkbox');
""".replace('FUNCTION',repr(expression))
        proc=subprocess.run([node,'-e',runner],capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)
        self.assertIn('PASS:',proc.stdout)

    def test_backend_still_rejects_missing_critical_ack(self):
        proc=subprocess.run(['perl',str(ROOT/'tests/perl_mock_rc9.pl')],
            cwd=ROOT,env={**os.environ,'PERL5LIB':str(ROOT/'src')},capture_output=True,text=True)
        self.assertEqual(proc.returncode,0,proc.stdout+proc.stderr)

    def test_install_script_points_to_release_package(self):
        wrapper=(ROOT/'install.sh').read_text()
        self.assertIn('pve-zfs-manager_1.0.0-32+docs2_all.deb',wrapper)
        self.assertNotIn('pve-zfs-manager_1.0.0~rc7-1_all.deb',wrapper)

class RC9RequirementsTest(unittest.TestCase):
    def test_rc8r2_real_upgrade_and_auto_reconcile(self):
        from universal import RC8R2_JS_INSERT
        with tempfile.TemporaryDirectory() as td:
            inst=Installer(root=td,source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
            inst.gui.parent.mkdir(parents=True,exist_ok=True)
            inst.nodes.parent.mkdir(parents=True,exist_ok=True)
            inst.gui.write_text(SRC_GUI.replace("        if (caps.nodes['Sys.Audit']) {",RC8R2_JS_INSERT+"        if (caps.nodes['Sys.Audit']) {",1))
            inst.nodes.write_text(inst.add_route(SRC_NODES))
            inst.api.parent.mkdir(parents=True,exist_ok=True)
            inst.api.write_bytes(inst.rc8r2_api())
            inst.policy.parent.mkdir(parents=True,exist_ok=True)
            inst.policy.write_bytes(inst.expected()[1])
            inst.save_state({'version':'1.0.0-rc8r2-installer','adopted_rc2':False})
            self.assertEqual(inst.check()[1:],('rc8r2','present'))
            old_api=inst.api.read_bytes()
            inst.install()
            inst.status()
            self.assertEqual(inst.state()['version'],universal.VERSION)
            self.assertEqual(inst.classify(),('rc9','present'))
            self.assertNotEqual(old_api,inst.api.read_bytes())
            inst.gui.write_text(SRC_GUI)
            inst.reconcile()
            inst.status()
            self.assertEqual(inst.classify(),('rc9','present'))
            self.assertLessEqual(len([x for x in inst.backup_root.iterdir() if x.is_dir()]), 2)

    def test_host_buttons_get_inherited_dataset_type(self):
        src=(ROOT/'src/manager_patch.py').read_text()
        self.assertIn("dataset: dataset, datasetType: datasetTypes[dataset] || '',\n                                            snapshot: String(snap.snapshot)",src)
        self.assertIn("!access && action !== 'create'",src)
        self.assertIn("host-snapshot-delete-preview",src)
        self.assertIn("host-rollback-stage",src)
        self.assertNotIn("function(){post('guest-rollback',{",src)
        self.assertNotIn("var deleteNow = function (isCritical)",src)

    def test_security_backend_mock_guest_vs_host(self):
        result=subprocess.run(['perl',str(ROOT/'tests/perl_mock_rc9.pl')],cwd=ROOT,
            env={**os.environ,'PERL5LIB':str(ROOT/'src')},capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_offline_helper_rejects_modified_or_mounted_snapshot(self):
        import importlib.util,hmac,hashlib,time
        from unittest.mock import patch
        p=ROOT/'src/offline_recovery.py'
        spec=importlib.util.spec_from_file_location('offline_recovery_rc9',p)
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        with tempfile.TemporaryDirectory() as td:
            m.BUNDLE=Path(td)/'rescue'
            m.BUNDLE.mkdir(mode=0o700)
            ds='rpool/ROOT/pve-1';snap='snap-old';now=int(time.time())
            rows=[('snap-old','1700000000','100'),('snap-new','1700001000','200')]
            fp=hashlib.sha256('|'.join(['HOST-V1','HOST-ROLLBACK',ds,snap,'yes','/']+[ ':'.join(x) for x in rows]).encode()).hexdigest()
            key='e'*64;expires=now+3000
            mac=hmac.new(key.encode(), '|'.join(['ZFSMGR-OFFLINE-1',ds,snap,fp,str(expires)]).encode(),hashlib.sha256).hexdigest()
            plan={'version':1,'dataset':ds,'snapshot':snap,'fingerprint':fp,
                'expires':expires,'signature':mac,'mounted_at_preview':'yes',
                'mountpoint':'/'}
            (m.BUNDLE/'plan.json').write_text(json.dumps(plan));(m.BUNDLE/'plan.json').chmod(0o600)
            (m.BUNDLE/'key').write_text(key);(m.BUNDLE/'key').chmod(0o600)
            def fake_run(*argv):
                if argv[0].endswith('findmnt'):return 'tmpfs\n'
                if argv[1]=='list' and '-r' in argv:return ds+'\tno\n'
                if argv[1]=='list' and '-t' in argv and 'bookmark' in argv:return ''
                if argv[1]=='list':return '\n'.join(f'{ds}@{n}\t{c}\t{t}' for n,c,t in rows)+'\n'
                if argv[1]=='get' and 'clones' in argv:return '-\n'
                if argv[1]=='get' and 'userrefs' in argv:return '0\n'
                return ''
            with patch.object(m,'run',side_effect=fake_run):
                selected=m.plan_from_bundle();newer,bounded=m.check_plan(selected)
                self.assertEqual(newer,['snap-new'])
                self.assertEqual(bounded,ds+'@snap-new')
                with patch.object(m,'run',side_effect=lambda *a:ds+'\tyes\n' if '-r' in a else fake_run(*a)):
                    with self.assertRaises(m.RescueError):m.check_plan(selected)
            plan['signature']='f'*64
            (m.BUNDLE/'plan.json').write_text(json.dumps(plan))
            with self.assertRaises(m.RescueError):m.plan_from_bundle()

class V1UpgradeTest(unittest.TestCase):
    def test_actual_rc9_to_v1(self):
        from universal import RC9_JS_INSERT
        with tempfile.TemporaryDirectory() as tmp:
            inst=Installer(root=Path(tmp),source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
            for path,data in ((inst.gui,SRC_GUI),(inst.nodes,SRC_NODES)):
                path.parent.mkdir(parents=True,exist_ok=True);path.write_text(data)
            inst.install()
            state=inst.state();state['version']='1.0.0-rc9-installer';inst.save_state(state)
            gui=inst.gui.read_text().replace(JS_INSERT,RC9_JS_INSERT,1)
            inst.gui.write_text(gui)
            inst.api.write_bytes(inst.rc9_api())
            self.assertEqual(inst.classify()[0],'rc9old')
            inst.install();inst.status()
            self.assertEqual(inst.state()['version'],universal.VERSION)
            self.assertEqual(inst.classify()[0],'rc9')
            inst.install();inst.status()
