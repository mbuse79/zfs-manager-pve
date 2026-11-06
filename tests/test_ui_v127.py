import unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1]/'src/manager_patch.py'
class GUI27(unittest.TestCase):
 def test_checkbox_click_cannot_toggle_tree(self):
  t=P.read_text();self.assertIn("cellIndex !== 1",t)
 def test_disk_children_mirror_parent_selection(self):
  t=P.read_text();self.assertIn("rec.eachChild(function(child)",t)
  self.assertIn("members.forEach(function(m){m.batchMarked",t)
 def test_compact_batch_preview(self):
  t=P.read_text();self.assertIn("width:470",t)
  self.assertIn("itemId:'zfsm-batch-details',hidden:true",t)
  self.assertIn("zfsL('Show details')",t)
 def test_host_additional_confirmation(self):
  t=P.read_text();self.assertIn("if(scope==='host')",t)
  self.assertIn("zfsL('Critical host dataset')",t)
 def test_language_keys(self):
  t=P.read_text();self.assertIn("create:zfsL('Grouped snapshot')",t)
  self.assertIn('"Incomplete": "unvollständig"',t)
 def test_backend_guard_still_present(self):
  t=(P.parent/'PVE/API2/ZFSSnapshotViewer.pm').read_text()
  self.assertIn('_verify_preview($plan',t)
  self.assertIn('critical_ack',t)
