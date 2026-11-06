import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import manager_patch_v1_12, zfsm_cli
class Release118(unittest.TestCase):
 def test_dataset_original_tree_layout_restored(self):
  src=manager_patch_v1_12.BLOCK
  self.assertIn("disableSelection: true, height: 390, rootVisible: false",src)
  self.assertNotIn("height: 390, scrollable: 'y', rootVisible: false",src)
  self.assertIn("dataIndex: 'count'",src)
  self.assertIn("dataIndex: 'used'",src)
 def test_language_and_host_dialogs(self):
  src=manager_patch_v1_12.BLOCK
  self.assertIn("zfsL('Not all disks are permitted for this action.')",src)
  self.assertIn("zfsL('Host security preview incomplete')",src)
  self.assertIn("zfsL('I confirm this action.')",src)
  self.assertIn('PVELangCookie',src)
  self.assertIn("text === 'Keine Angabe'",src)
 def test_cli_version(self):
  self.assertEqual(zfsm_cli.VERSION,'1.0.0-32')
if __name__=='__main__':unittest.main()
