"""v1.0.0-32: visual marking only; selection, expansion and writes remain unchanged."""
import re
from pathlib import Path
from manager_patch import BLOCK


def test_both_tree_views_have_selection_based_row_classes():
    assert BLOCK.count('getRowClass: function(rec)') == 2
    assert "if (!rec || !rec.get('batchMarked')) { return ''; }" in BLOCK
    assert "rec.get('kind') === 'group-snapshot'" in BLOCK
    assert "rec.get('kind') === 'snapshot' && rec.parentNode" in BLOCK
    assert "rec.parentNode.get('kind') === 'group-snapshot'" in BLOCK
    assert "rec.get('snapshot') && rec.get('batchMarked')" in BLOCK


def test_visual_classes_for_group_disk_and_dataset():
    assert "return 'zfsm-marked-snapshot';" in BLOCK
    assert "return 'zfsm-marked-disk';" in BLOCK
    assert "? 'zfsm-marked-snapshot' : '';" in BLOCK
    assert ".zfsm-marked-snapshot .x-grid-cell" in BLOCK
    assert ".zfsm-marked-disk .x-grid-cell" in BLOCK


def test_colours_theme_neutral_hover_focus_and_left_marker():
    assert 'rgba(38,130,220,.30)' in BLOCK
    assert 'rgba(38,130,220,.14)' in BLOCK
    assert '.x-grid-item-over' in BLOCK
    assert '.x-grid-item-selected' in BLOCK
    assert 'box-shadow: inset 4px 0 0 #2997ed' in BLOCK
    assert "document.getElementById('zfsm-batch-highlights-v131')" in BLOCK


def test_checkbox_selection_does_not_change_expansion():
    # Do not auto-expand or collapse when a group checkbox is checked.
    start = BLOCK.index("listeners:{checkchange:function(col,rowIndex,checked){")
    end = BLOCK.index("{xtype:'treecolumn'", start)
    check_handler = BLOCK[start:end]
    assert "rec.eachChild(function(child)" in check_handler
    assert "child.set('batchMarked', checked)" in check_handler
    assert 'rec.expand(' not in check_handler
    assert 'rec.collapse(' not in check_handler
    assert 'batchMarked' in check_handler


def test_selection_restores_across_refresh_and_remains_read_only():
    assert "batchMarked:!!view.zfsmBatchGuest[k+'@'+n]" in BLOCK
    assert "batchMarked:!!view.zfsmBatchDataset[dataset+'@'+snap.snapshot]" in BLOCK
    # Inspect packaged main ZFS API without executing ZFS actions.
    api = Path(__file__).resolve().parents[1] / 'src/PVE/API2/ZFSSnapshotViewer.pm'
    assert api.is_file()
    assert 'sub _batch_delete' in api.read_text()
