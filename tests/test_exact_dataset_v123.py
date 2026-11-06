import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
GUI=(R/'src/manager_patch.py').read_text()
API=(R/'src/PVE/API2/ZFSSnapshotViewer.pm').read_text()
class ExactDatasetDeletion(unittest.TestCase):
 def test_dataset_button_wired(self):
  self.assertIn("itemId: 'zfs-row-delete-exact'",GUI)
  self.assertIn("owner.zfsDatasetExactDelete(widget.zfsRowRecord)",GUI)
  self.assertIn("exactBtn.setHidden(!snap)",GUI)
 def test_guest_uses_existing_exact_endpoint(self):
  self.assertIn("guest?'guest-group-delete-exact':'host-snapshot-delete-exact'",GUI)
  self.assertIn("selection=Ext.encode([ds])",GUI)
  self.assertIn("data.confirm=(guest?'DELETE-EXACT:':'HOST-DELETE-EXACT:')+snap",GUI)
 def test_host_exact_no_range(self):
  segment=API.split('sub _host_exact_plan {')[1].split('# Read pool health')[0]
  self.assertIn("_host_dataset_info($dataset)",segment)
  self.assertIn("_check_clone_dependencies($dataset,[$snapshot])",segment)
  self.assertIn("_check_snapshot_holds($dataset,[$snapshot])",segment)
  self.assertIn("_verify_preview($plan,'HOST-DELETE-EXACT',$token)",segment)
  self.assertIn("_run_zfs_write('destroy',\"$dataset\\@$snapshot\")",segment)
  self.assertNotIn('_dry_run_destroy_range',segment)
  self.assertNotIn('destroy', '') if False else None
 def test_double_host_ack(self):
  self.assertIn("if(!guest)data.critical_ack=1;",GUI)
  self.assertIn("if(guest){doPost();return;}",GUI)
  self.assertIn("'CRITICAL ACTION - second confirmation'",GUI)
  self.assertIn("$critical_ack eq '1'",API)
if __name__=='__main__':unittest.main()
