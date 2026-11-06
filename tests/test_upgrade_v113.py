import sys, unittest, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from universal import Installer, JS_INSERT, V1_12_JS_INSERT
from test_repair_drift_v112 import SRC_GUI, SRC_NODES

class UpgradeAndReconcile13(unittest.TestCase):
 def test_migrate_v12_to_v13_and_auto_repair(self):
  with tempfile.TemporaryDirectory() as tmp:
   i=Installer(root=tmp,source=ROOT/'src',test_version='pve-manager/9.2.24/test',dry_system=True)
   for path,text in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text)
   i.install()
   gui=i.gui.read_text()
   self.assertEqual(gui.count(JS_INSERT),1)
   i.gui.write_text(gui.replace(JS_INSERT,V1_12_JS_INSERT))
   i.state_file.write_text(i.state_file.read_text().replace('1.0.0-13-dynamic-compat-installer','1.0.0-12-dynamic-compat-installer'))
   self.assertEqual(i.classify()[0],'v1_12')
   i.install()
   self.assertEqual(i.classify()[0],'rc9')
   self.assertEqual(i.state()['version'],'1.0.0-32-dynamic-compat-installer')
   i.gui.write_text(SRC_GUI)
   i.nodes.write_text(SRC_NODES)
   i.reconcile()
   self.assertEqual(i.classify(),('rc9','present'))
