"""Upgrade the published RC9 GUI/API bytes in an isolated filesystem."""
import importlib.util
from pathlib import Path

from universal import Installer, JS_INSERT, VERSION, sha
import previous_patch
from test_repair_drift_v112 import SRC_GUI, SRC_NODES

ROOT = Path(__file__).resolve().parents[1]


def test_published_rc9_to_rc10_preserves_node_configuration(tmp_path):
    spec = importlib.util.spec_from_file_location('published_rc9_gui', ROOT/'tests/fixtures/manager_patch_v134rc9.py')
    old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
    i = Installer(root=tmp_path, source=ROOT/'src', test_version='pve-manager/9.2.26/mock', dry_system=True)
    for path, value in ((i.gui, SRC_GUI), (i.nodes, SRC_NODES)):
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(value)
    i.install()
    i.gui.write_text(i.gui.read_text().replace(JS_INSERT, previous_patch.HELPERS + old.BLOCK))
    i.api.write_bytes((ROOT/'tests/fixtures/ZFSSnapshotViewer_v134rc9.pm').read_bytes())
    state = i.state(); state['version'] = '1.0.0-34-rc9-dynamic-compat-installer'
    state['installed_hashes']['gui'] = sha(i.gui.read_bytes())
    state['installed_hashes']['api'] = sha(i.api.read_bytes()); i.save_state(state)
    emergency = i.admindir/'emergency.json'; emergency.write_text('{"auto_enabled":false}')
    i.yearly.write_text('# private administrator schedule; disabled\n')
    keep = [emergency, i.yearly, i.secret, i.admin, i.policy, i.nodes]
    before = {p:p.read_bytes() for p in keep}
    i.install()
    assert i.state()['version'] == VERSION
    assert i.api.read_bytes() == (ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_bytes()
    assert i.gui.read_text().count(JS_INSERT) == 1
    assert before == {p:p.read_bytes() for p in keep}
