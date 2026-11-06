import os
import subprocess
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import universal
class CLIv110(unittest.TestCase):
    def test_version_pattern(self):
        self.assertTrue(universal.COMPATIBLE.match('pve-manager/9.2.24/hash'))
        self.assertTrue(universal.COMPATIBLE.match('pve-manager/9.2.25/hash'))
        self.assertFalse(universal.COMPATIBLE.match('pve-manager/10.0.0/hash'))
    def test_german_help(self):
        p=subprocess.run([sys.executable,str(ROOT/'src/zfsm_cli.py'),'help','--lang','de'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('Hilfe anzeigen',p.stdout)
    def test_english_help(self):
        p=subprocess.run([sys.executable,str(ROOT/'src/zfsm_cli.py'),'help','--lang','en'],capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('Show this help',p.stdout)
    def test_force_noninteractive_refuses(self):
        p=subprocess.run([sys.executable,str(ROOT/'src/zfsm_cli.py'),'repair','--force'],capture_output=True,text=True,input='')
        self.assertNotEqual(p.returncode,0)
        self.assertIn('Abgebrochen',p.stdout) if os.environ.get('LANG','').startswith('de') else self.assertIn('Cancelled',p.stdout)
