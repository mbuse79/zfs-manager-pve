"""Actual release 33 RC1 -> 34 RC1 migration in a fake PVE 9.2.26 root."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from universal import Installer, JS_INSERT, VERSION
from test_repair_drift_v112 import SRC_GUI, SRC_NODES
import previous_patch

ROOT=Path(__file__).resolve().parents[1]


def test_upgrade_33_to_34_preserves_proxmox_and_snapshot_backend():
    spec=importlib.util.spec_from_file_location('old33',ROOT/'tests/fixtures/manager_patch_v133.py')
    old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    old33api=(ROOT/'tests/fixtures/ZFSSnapshotViewer_v133.pm').read_bytes()
    with tempfile.TemporaryDirectory() as temp:
        ins=Installer(root=temp,source=ROOT/'src',test_version='pve-manager/9.2.26/mock',dry_system=True)
        for path,txt in ((ins.gui,SRC_GUI),(ins.nodes,SRC_NODES)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(txt)
        ins.install()
        current=ins.gui.read_text()
        prior=current.replace(JS_INSERT,previous_patch.HELPERS+old.BLOCK)
        assert prior!=current
        ins.gui.write_text(prior)
        ins.api.write_bytes(old33api)
        state=ins.state()
        state['version']='1.0.0-33-rc1-dynamic-compat-installer'
        state['installed_hashes']['gui']=hashlib.sha256(prior.encode()).hexdigest()
        state['installed_hashes']['api']=hashlib.sha256(old33api).hexdigest()
        ins.save_state(state)
        ins.install()
        assert ins.state()['version']==VERSION
        assert ins.read(ins.api)==ins.expected()[0]
        assert ins.classify()==('rc9','present')
        assert ins.read(ins.gui).decode().count('emergency-preview')>=1
        ins.status()
        assert ins.backup_root.is_dir()
