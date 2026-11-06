import unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
class BatchSafety(unittest.TestCase):
 def test_only_exact_destroy(self):
  s=(R/'src/PVE/API2/ZFSSnapshotViewer.pm').read_text();part=s[s.index('# v1.0.0-26:'):s.index('# Read pool health',s.index('# v1.0.0-26:'))]
  self.assertIn("_run_zfs_write('destroy',$target)",part)
  self.assertNotIn("'-r'",part)
  self.assertIn("_verify_preview($plan,'DELETE-BATCH-EXACT',$token)",part)
  self.assertIn("_check_clone_dependencies",part)
  self.assertIn("_check_snapshot_holds",part)
  self.assertIn("'destroy','-n','-v'",part)
 def test_guest_and_host_scopes(self):
  s=(R/'src/PVE/API2/ZFSSnapshotViewer.pm').read_text()
  self.assertIn("_selected_guest_disks($selection,1,'modify')",s)
  self.assertIn("_host_exact_plan($dataset,$snap)",s)
  self.assertIn("$scope eq 'host'",s)
  self.assertIn('non_atomic=>1',s)
 def test_ui(self):
  s=(R/'src/manager_patch.py').read_text()
  self.assertEqual(s.count("text:zfsL('Batch delete')"),2)
  self.assertEqual(s.count("text:zfsL('Select')"),2)
  self.assertIn('view.zfsmRunBatch=function(kind)',s)
  self.assertIn("post.confirm='DELETE-BATCH-EXACT'",s)
 def test_version(self):
  s=(R/'src/universal.py').read_text()
  self.assertIn('1.0.0-32-dynamic-compat-installer',s)
  self.assertIn("operation='reload'",s)
if __name__=='__main__':unittest.main()
