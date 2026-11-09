from pathlib import Path
import zfsm_cli
from universal import VERSION

ROOT=Path(__file__).resolve().parents[1]

def test_final_version_consistency():
    assert zfsm_cli.VERSION=='1.0.0-32'
    assert VERSION=='1.0.0-32-dynamic-compat-installer'
    assert "PACKAGE_VERSION='1.0.0-32+docs2'" in (ROOT/'build_deb.sh').read_text()
    assert 'pve-zfs-manager_1.0.0-32+docs2_all.deb' in (ROOT/'install.sh').read_text()

def test_publication_safety_docs_and_no_hardcoded_private_url():
    for name in ('README.md','INSTALL.md','TRADEMARK.md','SECURITY.md','PUBLICATION-CHECKLIST.md','LICENSING-REVIEW.md'):
        assert (ROOT/name).exists()
    assert 'https://<proxmox-host>:8006' in (ROOT/'src/patch_nav.py').read_text()

def test_upstream_snapshot_api_identical_to_rc_fixture():
    assert (ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_bytes()==(ROOT/'tests/fixtures/ZFSSnapshotViewer_v129.pm').read_bytes()

def test_rc1_to_final_upgrade_on_pve_925():
    import tempfile
    from universal import Installer
    from test_repair_drift_v112 import SRC_GUI, SRC_NODES
    with tempfile.TemporaryDirectory() as d:
        i=Installer(root=d,source=ROOT/'src',test_version='pve-manager/9.2.25/mock',dry_system=True)
        for p, contents in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(contents)
        i.install()
        st=i.state()
        st['version']='1.0.0-32~rc1-dynamic-compat-installer'
        i.save_state(st)
        i.install()
        assert i.state()['version']==VERSION
        i.status()
