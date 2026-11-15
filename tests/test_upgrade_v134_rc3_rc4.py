"""RC3 -> RC4 offline upgrade: GUI changes only, no destructive changes."""
from pathlib import Path
import importlib.util
import hashlib
import tempfile
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from universal import Installer, VERSION, JS_INSERT
from test_repair_drift_v112 import SRC_GUI, SRC_NODES
import previous_patch


def test_rc3_upgrade_to_rc4_preserves_api_policy_and_backups():
    path=ROOT/'tests/fixtures/manager_patch_v134rc3.py'
    spec=importlib.util.spec_from_file_location('previous_rc3',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    old_js=previous_patch.HELPERS+module.BLOCK
    assert old_js!=JS_INSERT
    with tempfile.TemporaryDirectory() as temp:
        installer=Installer(root=temp,source=ROOT/'src',test_version='pve-manager/9.2.26/mock',dry_system=True)
        for path,content in [(installer.gui,SRC_GUI),(installer.nodes,SRC_NODES)]:
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)
        installer.install()
        api=installer.api.read_bytes()
        policy=installer.policy.read_bytes()
        nodes=installer.nodes.read_bytes()
        old_gui=installer.gui.read_text().replace(JS_INSERT,old_js)
        installer.gui.write_text(old_gui)
        state=installer.state()
        state['version']='1.0.0-34-rc3-dynamic-compat-installer'
        state['installed_hashes']['gui']=hashlib.sha256(old_gui.encode()).hexdigest()
        installer.save_state(state)
        installer.install()
        assert installer.state()['version']==VERSION
        assert installer.gui.read_text().count(JS_INSERT)==1
        assert installer.api.read_bytes()==api
        assert installer.policy.read_bytes()==policy
        assert installer.nodes.read_bytes()==nodes
        assert installer.backup_root.exists()
        installer.status()
