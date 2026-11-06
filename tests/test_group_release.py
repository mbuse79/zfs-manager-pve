import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import universal
from test_installer import Installer, ROOT, SRC_GUI, SRC_NODES
import tempfile
class GroupRelease(unittest.TestCase):
    def test_group_endpoints_and_separate_tabs(self):
        api=(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_text()
        ui=(ROOT/'src/manager_patch.py').read_text()
        for endpoint in ['guest-group-create','guest-group-delete',
                         'guest-group-rollback']:
            self.assertIn(endpoint,api)
        self.assertIn("title:zfsL('VMs / LXC')",ui)
        self.assertIn("title:zfsL('ZFS-Datasets')",ui)
        self.assertIn('Gemeinsamer Snapshot',ui)
        self.assertIn('Gemeinsam löschen',ui)
    def test_install_from_actual_1_0_0_5_gui_and_api(self):
        with tempfile.TemporaryDirectory() as tmp:
            i=Installer(root=Path(tmp),source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
            for path,content in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(content)
            i.install()
            i.gui.write_text(i.gui.read_text().replace(universal.JS_INSERT, universal.V1_5_JS_INSERT,1))
            i.api.write_bytes(i.v1_5_api())
            i.state_file.write_text(i.state_file.read_text().replace(universal.VERSION,'1.0.0-final-test-installer'))
            self.assertEqual(i.classify()[0],'v1_5')
            i.install()
            i.status()
            self.assertEqual(i.api.read_bytes(),i.expected()[0])
            self.assertEqual(i.classify()[0],'rc9')
if __name__=='__main__':unittest.main()
