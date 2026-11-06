import unittest,tempfile,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from test_installer import Installer, ROOT, SRC_GUI, SRC_NODES
import universal
class UpgradeFrom18(unittest.TestCase):
 def test_exact_v18_upgrade(self):
  with tempfile.TemporaryDirectory() as td:
   i=Installer(root=Path(td),source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
   for f,s in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
    f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
   i.install()
   i.gui.write_text(i.gui.read_text().replace(universal.JS_INSERT,universal.V1_8_JS_INSERT,1))
   i.state_file.write_text(i.state_file.read_text().replace(universal.VERSION,'1.0.0-snapshot-tree-installer'))
   self.assertEqual(i.classify()[0],'v1_8')
   i.install();i.status()
   self.assertEqual(i.classify()[0],'rc9')
 def test_pro_gui_contract(self):
  p=(ROOT/'src/manager_patch.py').read_text()
  for marker in ('expandedGuestSnapshots','expandedGuests','zfs-show-all-datasets',"snapCount:groups.length",'state.guestAccess[dataset]',"state.expandedGuests[k]===true"):
   self.assertIn(marker,p)
