import unittest,sys,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import universal
from test_installer import Installer,ROOT,SRC_GUI,SRC_NODES
class SnapshotTree(unittest.TestCase):
 def test_tree_and_actions(self):
  s=(ROOT/'src/manager_patch.py').read_text()
  for x in ("expanded:state.expandedGuests[k]===true,\n                                    children:groups", "members.push({kind:'snapshot'", "allDisks:all", "panel.zfsTestAction('delete',node)", "panel.zfsSingleDiskRollback(node)", "panel.zfsGroupAction('create',{guest:node,direct:true})", "Object.keys(state.guestAccess||{})"):
   self.assertIn(x,s)
 def test_previous_gui_upgrade(self):
  with tempfile.TemporaryDirectory() as tmp:
   i=Installer(root=Path(tmp),source=ROOT/'src',test_version='pve-manager/9.2.21/test',dry_system=True)
   for f,s in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
    f.parent.mkdir(parents=True,exist_ok=True);f.write_text(s)
   i.install()
   i.gui.write_text(i.gui.read_text().replace(universal.JS_INSERT,universal.V1_7_JS_INSERT,1))
   i.state_file.write_text(i.state_file.read_text().replace(universal.VERSION,'1.0.0-simple-groups-installer'))
   self.assertEqual(i.classify()[0],'v1_7')
   i.install();i.status();self.assertEqual(i.classify()[0],'rc9')
