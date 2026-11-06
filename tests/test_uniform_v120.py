import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import manager_patch_v1_12
class Unified20(unittest.TestCase):
 def test_geometry(self):
  s=manager_patch_v1_12.BLOCK
  self.assertIn("disableSelection: true, height: 390",s)
  self.assertIn("rootVisible:false, height:390",s)
  self.assertIn('width: 245',s)
 def test_locale(self):
  s=manager_patch_v1_12.BLOCK
  for p in ("zfsL('ZFS Datasets')","zfsL('Not available')","zfsL('VMs / LXC')"):
   self.assertIn(p,s)
 def test_no_backend_modification(self):
  s=manager_patch_v1_12.BLOCK
  self.assertIn('onWidgetAttach',s)
  self.assertIn('zfsGroupAction',s)
