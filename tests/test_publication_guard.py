from pathlib import Path
import subprocess
import os

ROOT=Path(__file__).resolve().parents[1]

def test_public_build_requires_contact():
    env={**os.environ}
    env.pop('ZFSM_MAINTAINER_EMAIL',None)
    result=subprocess.run(['bash',str(ROOT/'build_deb.sh')], cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode == 2
    assert 'ZFSM_MAINTAINER_EMAIL' in result.stderr

def test_public_build_requires_approved_license():
    env={**os.environ,'ZFSM_MAINTAINER_EMAIL':'maintainer@release-test.org'}
    result=subprocess.run(['bash',str(ROOT/'build_deb.sh')],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode == 2
    assert 'LICENSE and Debian copyright' in result.stderr

def test_runtime_sources_remain_expected_rc1_compatible():
    assert (ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_bytes()==(ROOT/'tests/fixtures/ZFSSnapshotViewer_v129.pm').read_bytes()
