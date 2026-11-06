import tempfile,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from universal import Installer
from test_installer import SRC_GUI,SRC_NODES

class RegisteredPluginRepair(unittest.TestCase):
 def test_repair_modified_owned_module_and_lost_gui(self):
  with tempfile.TemporaryDirectory() as tmp:
   i=Installer(root=tmp,source=ROOT/'src',test_version='pve-manager/9.2.24/test',dry_system=True)
   for path,text in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
   i.install()
   old_api=i.api.read_bytes()
   i.api.write_bytes(old_api.replace(b'# Base inventory endpoints',b'# locally patched\n# Base inventory endpoints',1))
   i.gui.write_text(SRC_GUI)
   i.nodes.write_text(SRC_NODES)
   i.reconcile()
   self.assertEqual(i.api.read_bytes(),old_api)
   self.assertEqual(i.classify()[0],'rc9')
   self.assertEqual(i.classify()[1],'present')
   self.assertTrue(i.state().get('last_repair_backup'))

 def test_unknown_module_not_overwritten(self):
  with tempfile.TemporaryDirectory() as tmp:
   i=Installer(root=tmp,source=ROOT/'src',test_version='pve-manager/9.2.24/test',dry_system=True)
   for path,text in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
   i.install()
   i.api.write_bytes(b'package Other::Module;\n')
   with self.assertRaisesRegex(Exception,'Unbekannte API/Policy'):
    i.repair(force=True)
