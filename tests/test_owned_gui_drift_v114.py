import tempfile, unittest, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from universal import Installer, InstallError, JS_INSERT
from test_installer import SRC_GUI, SRC_NODES

class GuiDriftRepair14(unittest.TestCase):
 def make(self, tmp):
  i=Installer(root=tmp,source=ROOT/'src',test_version='pve-manager/9.1.6/test',dry_system=True)
  for path,content in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
   path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content)
  i.install()
  return i
 def test_exact_reported_user_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   i=self.make(tmp)
   original=i.gui.read_text()
   old="title: 'ZFS Manager'"
   self.assertEqual(original.count(old),1)
   modified=original.replace(old,"title: 'ZFS Manager Reparaturtest'",1)
   i.gui.write_text(modified)
   self.assertEqual(i.classify()[0],'owned-drift')
   with self.assertRaises(InstallError): i.status()
   i.reconcile()
   self.assertEqual(i.gui.read_text(),original)
   i.status()
   self.assertTrue(i.state().get('last_repair_backup'))
 def test_unregistered_or_unbounded_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   i=self.make(tmp)
   text=i.gui.read_text().replace("title: 'ZFS Manager'","title: 'ZFS Manager Reparaturtest'",1)
   i.gui.write_text(text)
   i.state_file.unlink()
   with self.assertRaises(InstallError):i.classify()
  with tempfile.TemporaryDirectory() as tmp:
   i=self.make(tmp)
   text=i.gui.read_text().replace('END PVE-ZFS-MANAGER-READONLY-v1.0.0-rc9','END PVE-ZFS-MANAGER-READONLY-tampered',1)
   i.gui.write_text(text)
   with self.assertRaises(InstallError):i.repair()
