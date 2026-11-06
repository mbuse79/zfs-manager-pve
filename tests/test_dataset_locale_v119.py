import unittest,sys,re
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
import manager_patch_v1_12

class LocaleDataset19(unittest.TestCase):
 def test_renderer_catches_locale_errors(self):
  s=manager_patch_v1_12.BLOCK
  self.assertIn('var safeZFSDate = function',s)
  self.assertIn('catch (err)',s)
  self.assertIn('safeZFSDate(n)',s)
  self.assertIn("'de-DE' : 'en-US'",s)
 def test_catalog_does_not_call_itself(self):
  s=manager_patch_v1_12.BLOCK
  t=s.split('var zfsTDe = {',1)[1].split('var zfsL = function',1)[0]
  self.assertNotRegex(t,r':\s*zfsL\(')
 def test_snapshot_actions_intact(self):
  s=manager_patch_v1_12.BLOCK
  for label in ('zfs-row-create','zfs-row-delete','zfs-row-rollback','onWidgetAttach'):
   self.assertIn(label,s)
