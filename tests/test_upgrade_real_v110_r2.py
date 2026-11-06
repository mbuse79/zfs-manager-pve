import unittest,tempfile,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from universal import Installer,JS_INSERT,V1_10_JS_INSERT,VERSION
from test_installer import SRC_GUI,SRC_NODES
class ActualV110Migration(unittest.TestCase):
 def test_real_v110_half_configured_to_v111(self):
  with tempfile.TemporaryDirectory() as tmp:
   i=Installer(root=tmp,source=ROOT/'src',test_version='pve-manager/9.2.24/test',dry_system=True)
   for p,x in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(x)
   i.install()
   i.gui.write_text(i.gui.read_text().replace(JS_INSERT,V1_10_JS_INSERT,1))
   i.policy.write_bytes(i.v1_10_policy())
   state=i.state();state['version']='1.0.0-10-dynamic-compat-installer';i.save_state(state)
   assert i.classify()[0]=='v1_10'
   i.install()
   self.assertEqual(i.classify()[0],'rc9')
   self.assertEqual(i.policy.read_bytes(),i.expected()[1])
   self.assertEqual(i.state()['version'],VERSION)
   i.status()
