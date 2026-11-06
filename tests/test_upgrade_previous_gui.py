import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import universal
class MigrationRegression(unittest.TestCase):
    def test_previous_gui_block_recognized_and_reversible(self):
        self.assertNotEqual(universal.V1_2_JS_INSERT,universal.JS_INSERT)
        former='head\n'+universal.V1_2_JS_INSERT+'\ntail'
        upgraded=former.replace(universal.V1_2_JS_INSERT, universal.JS_INSERT,1)
        self.assertEqual(upgraded.replace(universal.JS_INSERT,universal.V1_2_JS_INSERT,1),former)
        self.assertEqual(upgraded.count(universal.JS_INSERT),1)
if __name__=='__main__':unittest.main()

class PreviousReleaseIntegration(unittest.TestCase):
    def test_actual_v1_0_0_4_upgrade(self):
        import tempfile
        from test_installer import Installer, SRC_GUI, SRC_NODES, ROOT
        with tempfile.TemporaryDirectory() as tmp:
            i=Installer(root=Path(tmp),source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
            for path,content in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
                path.parent.mkdir(parents=True,exist_ok=True)
                path.write_text(content)
            i.install()
            i.gui.write_text(i.gui.read_text().replace(universal.JS_INSERT,universal.V1_4_JS_INSERT,1))
            i.api.write_bytes(i.v1_4_api())
            i.state_file.write_text(i.state_file.read_text().replace(universal.VERSION,'1.0.0-final-test-installer'))
            self.assertEqual(i.classify()[0],'v1_4')
            i.install()
            i.status()
            self.assertEqual(i.classify()[0],'rc9')
            self.assertEqual(i.api.read_bytes(),i.expected()[0])
