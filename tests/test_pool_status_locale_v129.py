"""Regression: actual Scrub table renderer must localize API placeholders."""
from pathlib import Path
import json
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUI = (ROOT / 'src/manager_patch.py').read_text()
API = (ROOT / 'src/PVE/API2/ZFSSnapshotViewer.pm').read_text()

class PoolStatusLocale129(unittest.TestCase):
    def test_api_does_not_emit_german_fallbacks(self):
        live = API.split("name=>'pool_scan'", 1)[1].split("# RC9: Separate", 1)[0]
        self.assertIn("scan=>$scan//'Not available'", live)
        self.assertIn("errors=>$errors//'Not available'", live)
        self.assertIn("state=>$state//'Unknown'", live)
        self.assertNotIn("scan=>$scan//'Keine Angabe'", live)
        self.assertNotIn("errors=>$errors//'Keine Angabe'", live)

    def test_scrub_columns_use_the_translating_renderer(self):
        table = GUI.split("itemId: 'zfs-ro-scan'", 1)[1].split("itemId: 'zfs-ro-snapshots'", 1)[0]
        for name in ('state', 'scan', 'errors'):
            self.assertRegex(table, r"dataIndex:'" + name + r"'[^\n]*renderer:zfsPoolStatusValue")
        self.assertIn("return safeZFSValue(zfsL(canonical));", GUI)

    def test_older_backend_values_are_normalized(self):
        for old in ("raw === 'Keine Angabe'", "raw === 'Unbekannt'", "raw === 'Keine bekannten Datenfehler'"):
            self.assertIn(old, GUI)

    @unittest.skipUnless(shutil.which('node'), 'Node.js required for runtime renderer test')
    def test_renderer_de_and_en(self):
        match = re.search(r"var zfsPoolStatusValue = function \(value\) \{.*?\n        \};", GUI, re.S)
        self.assertIsNotNone(match, 'renderer missing')
        js = match.group(0)
        cases = {
            'en': {'Keine Angabe': 'Not available', 'Not available': 'Not available',
                   'Unbekannt': 'Unknown', 'Keine bekannten Datenfehler': 'No known data errors',
                   'ONLINE': 'ONLINE', 'scrub repaired 0B in 1s': 'scrub repaired 0B in 1s'},
            'de': {'Keine Angabe': 'Keine Angabe', 'Not available': 'Keine Angabe',
                   'Unbekannt': 'Unbekannt', 'No known data errors': 'Keine bekannten Datenfehler',
                   'ONLINE': 'ONLINE', 'scrub repaired 0B in 1s': 'scrub repaired 0B in 1s'},
        }
        script = """
        var zfsLanguage = process.argv[1];
        var zfsTDe = {'Not available':'Keine Angabe','Unknown':'Unbekannt',
                      'No known data errors':'Keine bekannten Datenfehler'};
        var zfsL = function(text) { return zfsLanguage === 'de' ? (zfsTDe[text] || text) : text; };
        var safeZFSValue = function(text) {return String(text);};
        """ + js + """
        var result = {};
        for (var key of JSON.parse(process.argv[2])) result[key] = zfsPoolStatusValue(key);
        process.stdout.write(JSON.stringify(result));
        """
        for lang, expected in cases.items():
            run = subprocess.run(['node', '-e', script, lang, json.dumps(list(expected))], text=True,
                                 capture_output=True, check=True)
            self.assertEqual(json.loads(run.stdout), expected)

    def test_snapshot_write_paths_unmodified(self):
        original = (ROOT.parent / 'pve-zfs-manager-installer-v1.0.0-28/src/PVE/API2/ZFSSnapshotViewer.pm')
        if original.exists():
            first = original.read_text().split("# Read pool health", 1)[0]
            second = API.split("# Read pool health", 1)[0]
            self.assertEqual(first, second)
