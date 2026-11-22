"""Preserve the separate replication panel while migrating our bounded GUI block."""
from pathlib import Path
import importlib.util
import previous_patch
import tempfile

import pytest
from universal import Installer, InstallError, JS_INSERT, sha
from test_installer import SRC_GUI, SRC_NODES

ROOT = Path(__file__).resolve().parents[1]
LOOKUP = "me.items.findIndex(function (item) {return item.itemId === 'zfsmanager-readonly';})"
# Operator-reported menu adjacency logic, with an isolated sample panel.
NEIGHBOR = """    var panel = {itemId:'replication-test',listeners:{afterrender:function (p) {p.zrmRefresh();}}};
    // Executed immediately before node.Config's callParent: all menu configs exist.
    var index=""" + LOOKUP + """;
    if(index>=0) {me.items.splice(index+1,0,panel);} else {
        var system=me.items.findIndex(function(item) {return item.xtype === 'proxmoxNodeServiceView';});
        me.items.splice(system>=0 ? system : me.items.length,0,panel);
    }
"""


def make(root):
    i = Installer(root=root, source=ROOT/'src', test_version='pve-manager/9.1.1/test', dry_system=True)
    # Validate the real 9.1.1 stock-file guard against these isolated inputs.
    i.stock_911 = {'gui': sha(SRC_GUI.encode()), 'nodes': sha(SRC_NODES.encode())}
    for path, data in ((i.gui, SRC_GUI), (i.nodes, SRC_NODES)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    i.install()
    # Actual RC9 fixture: same backend SHA and block size as the operator report.
    spec = importlib.util.spec_from_file_location('replication_rc9', ROOT/'tests/fixtures/manager_patch_v134rc9.py')
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    gui = i.gui.read_text().replace(JS_INSERT, previous_patch.HELPERS+old.BLOCK, 1)
    state = i.state()
    state['installed_hashes']['gui'] = sha(gui.encode())
    old_api = (ROOT/'tests/fixtures/ZFSSnapshotViewer_v134rc9.pm').read_bytes()
    i.api.write_bytes(old_api)
    state['installed_hashes']['api'] = sha(old_api)
    gui = gui.replace("    },\n});\nExt.define('OtherClass'", NEIGHBOR + "    },\n});\nExt.define('OtherClass'", 1)
    assert NEIGHBOR in gui
    i.gui.write_text(gui)
    i.nodes.write_text(i.nodes.read_text()+'\n# Separate replication API registration remains intact\n')
    state['version'] = '1.0.0-34-rc9-dynamic-compat-installer'
    i.save_state(state)
    return i


def test_registered_rc9_upgrade_preserves_external_gui_and_api_and_backup():
    with tempfile.TemporaryDirectory() as root:
        i = make(root)
        before = i.gui.read_text()
        before_nodes = i.nodes.read_bytes()
        start, stop = i.owned_gui_drift_span(before)
        assert i.precheck()[1:] == ('owned-drift', 'present')
        assert i.gui.read_text() == before  # preflight never writes
        i.install()
        assert i.gui.read_text() == before[:start] + JS_INSERT + before[stop:]
        assert i.nodes.read_bytes() == before_nodes
        assert i.gui.read_text().count(NEIGHBOR) == 1
        i.status()
        assert any(p.read_bytes() == before.encode() for p in i.backup_root.rglob('gui.orig'))
        i.reconcile()
        assert i.gui.read_text().count(NEIGHBOR) == 1
        assert i.nodes.read_bytes() == before_nodes


@pytest.mark.parametrize('change', ['unknown-reference', 'second-panel', 'duplicate-lookup', 'outside-scope', 'unregistered', 'damaged-marker'])
def test_other_references_and_invalid_ownership_still_rejected_without_writes(change):
    with tempfile.TemporaryDirectory() as root:
        i = make(root)
        text = i.gui.read_text()
        if change == 'unknown-reference':
            text = text.replace(LOOKUP, LOOKUP.replace('item.itemId', 'item.name'), 1)
        elif change == 'second-panel':
            text = text.replace(NEIGHBOR, NEIGHBOR+"    me.items.push({itemId:'zfsmanager-readonly'});\n", 1)
        elif change == 'duplicate-lookup':
            text = text.replace(NEIGHBOR, NEIGHBOR+'    var second='+LOOKUP+';\n', 1)
        elif change == 'outside-scope':
            text = text.replace(NEIGHBOR, '', 1) + '\n' + NEIGHBOR
        elif change == 'unregistered':
            i.state_file.unlink()
        elif change == 'damaged-marker':
            text = text.replace('END PVE-ZFS-MANAGER-READONLY-v1.0.0-rc9', 'END PVE-ZFS-MANAGER-READONLY-damaged', 1)
        i.gui.write_text(text)
        before = {p: p.read_bytes() for p in (i.gui, i.nodes, i.api, i.policy)}
        with pytest.raises(InstallError):
            i.precheck()
        assert all(p.read_bytes() == data for p, data in before.items())
