from pathlib import Path
import unittest
S=(Path(__file__).resolve().parents[1]/'src/manager_patch.py').read_text()
class Locale128(unittest.TestCase):
 def test_scrub_translation(self):
  self.assertIn("'Not available': 'Keine Angabe'",S)
  self.assertIn("raw === 'Keine Angabe'",S)
 def test_rollback_translation(self):
  self.assertIn("Ext.Msg.confirm(zfsL('Single-disk rollback')",S)
  self.assertIn("zfsL('All other disks remain unchanged.')",S)
  self.assertNotIn("Ext.Msg.confirm('Einzelplatten-Rollback'",S)
