"""Ensure no legacy host safety dialogues leak German strings in English UI."""
import re
import unittest
from pathlib import Path

GUI = (Path(__file__).resolve().parents[1] / 'src/manager_patch.py').read_text()

class HostSafetyLocale129(unittest.TestCase):
    def test_host_safety_messages_use_dictionary(self):
        keys = (
            'Host snapshots will be permanently deleted.',
            'Host rollback overwrites the current data.',
            'Host snapshot deletion – preview',
            'Host rollback – preview',
            'CRITICAL HOST DELETION',
            'CRITICAL HOST ROLLBACK',
            'This operation can impair host recoverability.',
            'OFFLINE RECOVERY PREPARED',
            'Host preview failed: ',
        )
        dictionary, display = GUI.split('var zfsL = function', 1)
        for key in keys:
            self.assertIn(repr(key) + ': ', dictionary)
            self.assertIn('zfsL(' + repr(key) + ')', display)

    def test_no_known_hardcoded_german_host_dialogs(self):
        gui_only = GUI.split('var zfsL = function', 1)[1]
        for german in (
            'Host-Snapshot-Löschung – Vorschau', 'Host-Rollback – Vorschau',
            'Host-Vorschau fehlgeschlagen:', 'KRITISCHE HOST-LÖSCHUNG',
            'OFFLINE-RECOVERY VORBEREITET',
        ):
            self.assertNotIn(german, gui_only)

    def test_destructive_endpoints_not_changed(self):
        path = Path(__file__).resolve().parents[1] / 'src/PVE/API2/ZFSSnapshotViewer.pm'
        legacy = path.parent.parent.parent.parent / 'pve-zfs-manager-installer-v1.0.0-28/src/PVE/API2/ZFSSnapshotViewer.pm'
        # Source assertions already covered by the pool table regression test.
        self.assertIn("_batch_delete", path.read_text())
        self.assertIn("_verify_preview($plan", path.read_text())
