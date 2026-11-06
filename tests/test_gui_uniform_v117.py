import unittest
from pathlib import Path
from sys import path
path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import manager_patch_v1_12
class TestUniformGUI(unittest.TestCase):
    def test_guest_english_and_german_text_are_localized(self):
        s = manager_patch_v1_12.BLOCK
        for t in ("zfsL('Advanced: selected disks')", "zfsL('VM / LXC – Snapshot management')", "zfsL(' guest detected. ')", "zfsL('Show all datasets (including VM/LXC)')", "zfsL('Disks')"):
            self.assertIn(t, s)
        self.assertNotIn("' Gaeste erkannt.", s)
    def test_both_trees_have_same_scrolling_height(self):
        s = manager_patch_v1_12.BLOCK
        self.assertIn("height:390, scrollable:'y'",s)
        self.assertIn("height: 390, rootVisible: false",s)
    def test_actions_share_button_styling(self):
        s = manager_patch_v1_12.BLOCK
        self.assertIn("itemId:'guest-create',text:zfsL('Create')",s)
        self.assertIn("itemId:'guest-delete',text:zfsL('Delete')",s)
        self.assertIn("itemId: 'zfs-row-create', text: zfsL(\"Create\")",s)
if __name__ == '__main__': unittest.main()
