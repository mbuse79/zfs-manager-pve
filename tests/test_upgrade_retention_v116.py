import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from universal import Installer, VERSION
from test_repair_drift_v112 import SRC_GUI, SRC_NODES

class UpgradeRetention16(unittest.TestCase):
    def fresh(self,tmp):
        i=Installer(root=tmp,source=ROOT/'src',test_version='pve-manager/9.2.24/test',dry_system=True)
        for path,text in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(text)
        i.install()
        return i

    def test_upgrade_from_14_and_incomplete_15(self):
        with tempfile.TemporaryDirectory() as tmp:
            i=self.fresh(tmp)
            for prior in ['1.0.0-14-dynamic-compat-installer','1.0.0-15-dynamic-compat-installer']:
                state=i.state();state['version']=prior;i.save_state(state)
                # Simulate previous packaging installed but GUI belongs to older version / drift.
                gui=i.gui.read_text()
                i.gui.write_text(gui.replace("title: 'ZFS Manager'", "title: 'ZFS Manager Reparaturtest'",1))
                i.install()
                self.assertEqual(i.state()['version'],VERSION)
                i.status()

    def test_backup_retention_preserves_manual(self):
        with tempfile.TemporaryDirectory() as tmp:
            i=self.fresh(tmp)
            root=i.backup_root
            manual=root/'manual-20261101T120000Z-aaaaaa';manual.mkdir()
            for name in ('repair-20261101T120100Z-000001','repair-20261101T120200Z-000002',
                         'repair-20261101T120300Z-000003','migrate-20261101T120400Z-000004'):
                (root/name).mkdir()
            unknown=root/'user-kept';unknown.mkdir()
            i.prune_automatic_backups()
            self.assertEqual(len([p for p in root.iterdir() if p.name.startswith(('repair-','migrate-'))]),2)
            self.assertTrue(manual.exists());self.assertTrue(unknown.exists())

    def test_new_install_without_registered_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            i=self.fresh(tmp)
            self.assertEqual(i.state()['version'],VERSION)
            i.status()

if __name__=='__main__':unittest.main()
