"""Non-destructive offline simulation of the RC2 -> RC3 Proxmox upgrade."""
from pathlib import Path
import importlib.util
import hashlib
import tempfile
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from universal import Installer, JS_INSERT, VERSION
from test_repair_drift_v112 import SRC_GUI, SRC_NODES
import previous_patch


def test_rc2_upgrade_to_rc3_preserves_api_policy_and_old_backup():
    path=ROOT/'tests/fixtures/manager_patch_v134rc2.py'
    spec=importlib.util.spec_from_file_location('previous_rc2',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    previous_js=previous_patch.HELPERS+module.BLOCK
    assert previous_js!=JS_INSERT
    with tempfile.TemporaryDirectory() as tmp:
        ins=Installer(root=tmp,source=ROOT/'src',test_version='pve-manager/9.2.26/mock',dry_system=True)
        for path,data in ((ins.gui,SRC_GUI),(ins.nodes,SRC_NODES)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(data)
        ins.install()
        current_nodes=ins.nodes.read_bytes()
        current_api=ins.api.read_bytes()
        current_policy=ins.policy.read_bytes()
        old_gui=ins.gui.read_text().replace(JS_INSERT,previous_js)
        assert old_gui!=ins.gui.read_text()
        ins.gui.write_text(old_gui)
        state=ins.state()
        state['version']='1.0.0-34-rc2-dynamic-compat-installer'
        state['installed_hashes']['gui']=hashlib.sha256(old_gui.encode()).hexdigest()
        ins.save_state(state)
        ins.install()
        assert ins.state()['version']==VERSION
        assert ins.nodes.read_bytes()==current_nodes
        assert ins.api.read_bytes()==current_api
        assert ins.policy.read_bytes()==current_policy
        assert JS_INSERT in ins.gui.read_text()
        assert ins.backup_root.is_dir()
        ins.status()
