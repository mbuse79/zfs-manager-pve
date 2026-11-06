import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SingleDisk(unittest.TestCase):
 def test_one_disk_only(self):
  s=(ROOT/'src/manager_patch.py').read_text()
  self.assertIn("var chosen=Ext.encode([ds]);",s)
  self.assertIn("zfsSingleDiskRollback(node)",s)
  self.assertIn("guest-group-rollback",s)
  self.assertIn("plan.disks.length!==1",s)
  self.assertIn("!a.can_delete",s)
  self.assertNotIn("!a.can_rollback || !rec.get('allDisks')",s)
 def test_guest_name(self):
  self.assertIn("'display_name':",(ROOT/'src/libexec/guest_policy.py').read_text())
  self.assertIn("g.name?' – '+g.name",(ROOT/'src/manager_patch.py').read_text())
