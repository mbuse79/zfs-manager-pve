"""Upgrade RC4 -> RC5 must not touch GUI/API, guest policy, or ZFS datasets."""
from pathlib import Path
import hashlib
import tempfile
from universal import Installer, VERSION
from test_repair_drift_v112 import SRC_GUI, SRC_NODES

ROOT=Path(__file__).resolve().parents[1]


def test_rc4_to_rc5_is_installer_only_upgrade():
    assert VERSION=='1.1-cluster-installer'
    with tempfile.TemporaryDirectory() as td:
        i=Installer(root=td,source=ROOT/'src',test_version='pve-manager/9.2.26/mock',dry_system=True)
        for path,content in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(content)
        i.install()
        before={f:getattr(i,f).read_bytes() for f in ('gui','nodes','api','policy')}
        saved=i.state()
        saved['version']='1.0.0-34-rc4-dynamic-compat-installer'
        i.save_state(saved)
        i.install()
        assert i.state()['version']==VERSION
        for name,old in before.items():
            assert getattr(i,name).read_bytes()==old, f'{name} changed on installer-only upgrade'
        assert all(i.state()['installed_hashes'][k]==hashlib.sha256(v).hexdigest() for k,v in before.items())
        i.status()
