"""Release 1.0.0-32: fixture-backed pure audit + GUI parity and safety."""
from pathlib import Path
import importlib.util
import json
import re
import subprocess
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src'
spec=importlib.util.spec_from_file_location('zfsm_capacity',SRC/'zfsm_capacity.py')
cap=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)

POOLS=['rpool\t107374182400\t85899345920\t21474836480\tONLINE',
       'tank\t107374182400\t75161927680\t32212254720\tONLINE']
SNAPS=['rpool/data/subvol-700-disk-0@zfs-auto-snap_hourly-20261102\t1000\t1048576',
       'rpool/data/subvol-700-disk-0@zfs-auto-snap_hourly-20261103\t2000\t1048576',
       'rpool/data/subvol-700-disk-1@zfs-auto-snap_hourly-20261103\t2000\t524288',
       'rpool/ROOT@zfsmgr-manual\t2100\t1048576']

class Capacity30(unittest.TestCase):
    def test_pool_levels_at_boundaries(self):
        x=cap.parse_pool_lines([
            'a\t100\t69\t31\tONLINE', 'b\t100\t70\t30\tONLINE',
            'c\t100\t79\t21\tONLINE', 'd\t100\t80\t20\tONLINE'])
        self.assertEqual([v['level'] for v in x], ['normal','warning','warning','critical'])

    def test_snapshot_sum_is_not_reclaim_forecast(self):
        r=cap.build_report(cap.parse_pool_lines(POOLS),cap.parse_snapshot_lines(SNAPS),
                           {'hourly':1,'frequent':0},now=3000)
        self.assertEqual(r['total_snapshots'],4)
        self.assertEqual(r['snapshot_used_total_bytes'],3670016)
        self.assertFalse(r['snapshot_used_is_reclaim_forecast'])
        self.assertEqual(r['top_datasets'][0]['dataset'],'rpool/data/subvol-700-disk-0')
        self.assertEqual(r['retention'][1]['over_keep_observed'],1)
        self.assertIsNone(r['retention'][0]['over_keep_observed'])  # disabled != delete
        self.assertFalse(r['actions_performed'])

    def test_unknown_policy_never_infers_pruning(self):
        r=cap.build_report([],cap.parse_snapshot_lines(SNAPS),{},now=3000)
        for policy in r['retention']:
            self.assertIsNone(policy['over_keep_observed'])

    def test_reject_bad_rows(self):
        for raw in ('rpool@a\t-1\t1', 'rpool@a\t123\t1\t0', 'invalid', 'rpool@a\tx\t1'):
            with self.assertRaises(cap.AuditError): cap.parse_snapshot_lines([raw])
        for raw in ('pool\t100\t200\t0\tONLINE','pool\t100\tbad\t0\tONLINE'):
            with self.assertRaises(cap.AuditError):cap.parse_pool_lines([raw])

    def test_retention_disabled_and_symlink(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'cron';p.write_text('# PVE-ZFS-MANAGER-DISABLED */15 * * * * root zfs-auto-snapshot --label=frequent --keep=96\n')
            self.assertEqual(cap.read_retention_file('frequent',p),0)
            link=Path(tmp)/'link';link.symlink_to(p)
            self.assertIsNone(cap.read_retention_file('frequent',link))

    def test_collect_is_strictly_read_only(self):
        commands=[]
        def runner(cmd,**kwargs):
            commands.append(cmd)
            if cmd[0]=='/usr/sbin/zpool':return SimpleNamespace(returncode=0,stdout='\n'.join(POOLS)+'\n')
            if cmd[0]=='/usr/sbin/zfs':return SimpleNamespace(returncode=0,stdout='\n'.join(SNAPS)+'\n')
            raise AssertionError('unexpected executable')
        report=cap.collect_report(runner=runner,cron_files={},now=3000)
        self.assertEqual(len(commands),2)
        self.assertEqual(report['total_snapshots'],4)
        self.assertEqual(commands[0][:3],['/usr/sbin/zpool','list','-H'])
        self.assertEqual(commands[1][:3],['/usr/sbin/zfs','list','-H'])
        for cmd in commands:
            self.assertNotIn('destroy',cmd)
            self.assertNotIn('set',cmd)

    def test_cli_help_and_json_restrict(self):
        import sys
        sys.path.insert(0,str(SRC))
        import zfsm_cli
        from io import StringIO
        with patch.object(zfsm_cli,'collect_report',create=True):
            self.assertEqual(zfsm_cli.main(['capacity','--force']),2)
            self.assertEqual(zfsm_cli.main(['status','--json']),2)
        self.assertEqual(zfsm_cli.VERSION,'1.0.0-32')
        self.assertIn('capacity',zfsm_cli.HELP_COMMANDS)

    def test_js_capacity_report_parity(self):
        gui=(SRC/'manager_patch.py').read_text()
        match=re.search(r'var zfsmCapacityReport = function \(pools, snapshots, retention, nowSeconds\) \{.*?\n        \};',gui,re.S)
        self.assertIsNotNone(match)
        proc=subprocess.run(['node','-e',"""
            "use strict";
            %s
            var fixture=JSON.parse(process.argv[1]);
            process.stdout.write(JSON.stringify(zfsmCapacityReport(fixture.pools,fixture.snapshots,fixture.retention,3000)));
        """%match.group(0),json.dumps({'pools':[{'name':'rpool','size':100,'alloc':80,'free':20}],
            'snapshots':[{'dataset':'rpool/a','snapshot':'zfs-auto-snap_hourly-1','used':42,'creation':1000},
                         {'dataset':'rpool/a','snapshot':'zfs-auto-snap_hourly-2','used':43,'creation':2000}],
            'retention':[{'label':'hourly','keep':1}]})],check=True,capture_output=True,text=True)
        r=json.loads(proc.stdout)
        self.assertEqual(r['pools'][0]['level'],'critical')
        self.assertEqual(r['topDatasets'][0]['used'],85)
        self.assertEqual(r['policies'][0]['aboveKeep'],1)

    def test_gui_escaped_and_no_backend_write_changes(self):
        gui=(SRC/'manager_patch.py').read_text()
        api=(SRC/'PVE/API2/ZFSSnapshotViewer.pm').read_bytes()
        prev=(ROOT/'tests/fixtures/ZFSSnapshotViewer_v129.pm').read_bytes()
        self.assertEqual(api,prev)
        self.assertIn("itemId: 'zfs-capacity-audit'",gui)
        self.assertIn("enc(r.dataset)",gui)
        self.assertIn('retention-update',gui)  # existing write path retained
        self.assertIn("'zfsmanager-ro/snapshots'",gui)
        self.assertNotIn('/zfsmanager-ro/capacity-update',gui)

if __name__=='__main__':unittest.main()

class ActualUpgrade30(unittest.TestCase):
    def test_29_to_30_in_isolated_proxmox_fixture(self):
        import sys
        sys.path.insert(0,str(SRC))
        from universal import Installer, JS_INSERT
        from test_repair_drift_v112 import SRC_GUI, SRC_NODES
        import previous_patch
        spec=importlib.util.spec_from_file_location('historical_patch29',
            ROOT/'tests/fixtures/manager_patch_v129.py')
        old=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)
        with tempfile.TemporaryDirectory() as temp:
            i=Installer(root=temp,source=SRC,test_version='pve-manager/9.2.24/test',dry_system=True)
            for p,txt in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
                p.parent.mkdir(parents=True,exist_ok=True)
                p.write_text(txt)
            i.install()
            # Simulate a registered v29 installation, without touching host files.
            oldgui=i.gui.read_text().replace(JS_INSERT,previous_patch.HELPERS+old.BLOCK)
            i.gui.write_text(oldgui)
            state=i.state()
            state['version']='1.0.0-29-dynamic-compat-installer'
            state['installed_hashes']['gui']=i.sha(oldgui.encode()) if hasattr(i,'sha') else __import__('hashlib').sha256(oldgui.encode()).hexdigest()
            i.save_state(state)
            i.install()
            self.assertEqual(i.state()['version'],'1.0.0-32-dynamic-compat-installer')
            self.assertIn('zfs-capacity-audit',i.gui.read_text())
            i.status()

    def test_cli_json_output_with_mock_report(self):
        import sys
        from io import StringIO
        sys.path.insert(0,str(SRC))
        import zfsm_cli, zfsm_capacity
        item=cap.build_report(cap.parse_pool_lines(POOLS),cap.parse_snapshot_lines(SNAPS),{},now=3000)
        buf=StringIO()
        with patch.object(zfsm_capacity,'collect_report',return_value=item),patch('sys.stdout',buf):
            status=zfsm_cli.main(['capacity','--json'])
        self.assertEqual(status,0)
        doc=json.loads(buf.getvalue())
        self.assertEqual(doc['schema'],1)
        self.assertFalse(doc['actions_performed'])
        self.assertFalse(doc['snapshot_used_is_reclaim_forecast'])
