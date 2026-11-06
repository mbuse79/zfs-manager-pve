import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import manager_patch
class UI115(unittest.TestCase):
 def test_guest_titles_translated(self):
  s=manager_patch.BLOCK
  for value in ('VM / LXC – Snapshot management','Guests, their disks and snapshots. Manage individual disks or the whole VM/LXC.','Not all disks are permitted for this action.'):
   self.assertIn('zfsL('+repr(value)+')',s)
 def test_dataset_tab_translated(self):
  self.assertIn("zfsL('<h3>ZFS Datasets and Snapshots</h3>')",manager_patch.BLOCK)
  self.assertIn("text:zfsL('Snapshots')",manager_patch.BLOCK)
 def test_lang_comes_from_proxmox(self):
  self.assertIn('PVELangCookie',manager_patch.BLOCK)
  self.assertIn('pve-lang-',manager_patch.BLOCK)
