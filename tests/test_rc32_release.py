"""RC1: minimal UI polish + no snapshot/API regressions + PVE9.2.25 migration."""
import hashlib
from pathlib import Path
import tempfile
from universal import Installer, VERSION, JS_INSERT
from test_repair_drift_v112 import SRC_GUI, SRC_NODES
import previous_patch
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
VER="1.0.0-32"

def test_versions_and_cli_are_consistent():
    import zfsm_cli
    assert zfsm_cli.VERSION == VER
    assert VERSION == VER+'-dynamic-compat-installer'
    assert 'pve-zfs-manager_'+VER+'+docs2_all.deb' in (ROOT/'install.sh').read_text()
    assert "PACKAGE_VERSION='"+VER+"+docs2'" in (ROOT/'build_deb.sh').read_text()

def test_single_guest_singular_both_languages():
    from manager_patch import BLOCK
    assert "'guest found. ': 'Gast erkannt. '" in BLOCK
    assert "roots.length===1 ? 'guest found. ' : 'guests found. '" in BLOCK
    assert "'guests found. ': 'Gäste erkannt. '" in BLOCK

def test_snapshot_backend_untouched():
    # RC is UI polish, not a reimplementation of ZFS operations.
    current=(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_bytes()
    previous=(ROOT/'tests/fixtures/ZFSSnapshotViewer_v129.pm').read_bytes()
    assert current == previous

def test_upgrade_31_to_rc_on_pve_925():
    spec=importlib.util.spec_from_file_location('patch31',ROOT/'tests/fixtures/manager_patch_v131.py')
    old=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    with tempfile.TemporaryDirectory() as temp:
        i=Installer(root=temp,source=ROOT/'src',test_version='pve-manager/9.2.25/mock',dry_system=True)
        for path,txt in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(txt)
        i.install()
        old_gui=i.gui.read_text().replace(JS_INSERT,previous_patch.HELPERS+old.BLOCK)
        assert old_gui != i.gui.read_text()
        i.gui.write_text(old_gui)
        state=i.state()
        state['version']='1.0.0-31-dynamic-compat-installer'
        state['installed_hashes']['gui']=hashlib.sha256(old_gui.encode()).hexdigest()
        i.save_state(state)
        i.install()
        assert i.state()['version']==VERSION
        assert i.classify()==('rc9','present')
        i.status()
        i.reconcile()
        assert i.classify()==('rc9','present')
