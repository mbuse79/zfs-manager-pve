import unittest,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import universal
from test_installer import Installer,ROOT,SRC_GUI,SRC_NODES
class SimpleGroups(unittest.TestCase):
 def test_buttons_and_group_rows(self):
  s=(ROOT/'src/manager_patch.py').read_text()
  self.assertIn('group-snapshot',s)
  self.assertIn("widget.down('#guest-create').setHidden(kind!=='guest')",s)
  self.assertIn("title:zfsL('ZFS-Datasets')",s)
  self.assertIn("Resolve disks independently from tree layout",s)
 def test_upgrade_from_actual_v1_6(self):
  with tempfile.TemporaryDirectory() as tmp:
   i=Installer(root=Path(tmp),source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
   for f,s in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
    f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
   i.install()
   i.gui.write_text(i.gui.read_text().replace(universal.JS_INSERT,universal.V1_6_JS_INSERT,1))
   i.api.write_bytes(i.v1_6_api())
   i.state_file.write_text(i.state_file.read_text().replace(universal.VERSION,'1.0.0-final-group-installer'))
   self.assertEqual(i.classify()[0],'v1_6')
   i.install();i.status();self.assertEqual(i.classify()[0],'rc9')
