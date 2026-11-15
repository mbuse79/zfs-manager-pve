"""Offline upgrade of actual installed 1.0.0-34 RC1 GUI to RC2."""
import hashlib
import tempfile
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from universal import Installer, JS_INSERT, VERSION
from test_repair_drift_v112 import SRC_GUI, SRC_NODES
import previous_patch, manager_patch
import importlib.util
ROOT=Path(__file__).resolve().parents[1]


def test_upgrade_rc1_to_rc2_preserves_nodes_api_and_installer_backup():
    spec=importlib.util.spec_from_file_location('old34',ROOT/'tests/fixtures/manager_patch_v134rc1.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    old_block=previous_patch.HELPERS+mod.BLOCK
    assert old_block!=JS_INSERT
    with tempfile.TemporaryDirectory() as tmp:
        ins=Installer(root=tmp,source=ROOT/'src',test_version='pve-manager/9.2.26/mock',dry_system=True)
        for path,data in ((ins.gui,SRC_GUI),(ins.nodes,SRC_NODES)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(data)
        ins.install()
        new_nodes=ins.nodes.read_bytes()
        new_api=ins.api.read_bytes()
        previous_gui=ins.gui.read_text().replace(JS_INSERT,old_block)
        ins.gui.write_text(previous_gui)
        state=ins.state()
        state['version']='1.0.0-34-rc1-dynamic-compat-installer'
        state['installed_hashes']['gui']=hashlib.sha256(previous_gui.encode()).hexdigest()
        ins.save_state(state)
        ins.install()
        assert ins.state()['version']==VERSION
        assert ins.nodes.read_bytes()==new_nodes
        assert ins.api.read_bytes()==new_api
        assert JS_INSERT in ins.gui.read_text()
        assert ins.backup_root.is_dir()
        ins.status()
