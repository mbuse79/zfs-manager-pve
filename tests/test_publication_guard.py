from pathlib import Path
import subprocess
import os
import tempfile
import shutil

ROOT=Path(__file__).resolve().parents[1]

def test_public_build_requires_contact():
    env={**os.environ}
    env.pop('ZFSM_MAINTAINER_EMAIL',None)
    result=subprocess.run(['bash',str(ROOT/'build_deb.sh')], cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode == 2
    assert 'ZFSM_MAINTAINER_EMAIL' in result.stderr

def test_public_build_requires_approved_license():
    env={**os.environ,'ZFSM_MAINTAINER_EMAIL':'maintainer@release-test.org'}
    with tempfile.TemporaryDirectory() as d:
        scratch=Path(d)
        shutil.copy2(ROOT/'build_deb.sh',scratch/'build_deb.sh')
        result=subprocess.run(['bash',str(scratch/'build_deb.sh')],cwd=scratch,env=env,capture_output=True,text=True)
        assert result.returncode == 2
        assert 'LICENSE and Debian copyright' in result.stderr

def test_runtime_sources_remain_expected_rc1_compatible():
    assert (ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_bytes()==(ROOT/'tests/fixtures/ZFSSnapshotViewer_v129.pm').read_bytes()


def test_selected_license_and_project_contact():
    assert (ROOT/'LICENSE').read_text(encoding='utf-8').startswith('                    GNU AFFERO GENERAL PUBLIC LICENSE')
    assert 'Version 3, 19 November 2007' in (ROOT/'LICENSE').read_text(encoding='utf-8')
    assert 'AGPL-3.0-only' in (ROOT/'debian/copyright').read_text(encoding='utf-8')
    assert 'bumavory@buse.rocks' in (ROOT/'MAINTAINER.md').read_text(encoding='utf-8')
