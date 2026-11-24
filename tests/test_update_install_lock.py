from pathlib import Path
import importlib.util
import os

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('update_install_driver', ROOT/'install_driver.py')
driver = importlib.util.module_from_spec(spec)
spec.loader.exec_module(driver)


def test_package_lock_rejects_symlink(tmp_path):
    target = tmp_path/'target'
    target.write_text('untouched')
    link = tmp_path/'lock'
    link.symlink_to(target)
    with pytest.raises(OSError):
        with driver.package_lock(link):
            pytest.fail('symlink lock accepted')
    assert target.read_text() == 'untouched'


def test_package_lock_serializes_and_releases_root_owned_fixture(tmp_path):
    if os.geteuid() != 0:
        pytest.skip('root-owned lock is exercised separately under fakeroot')
    path = tmp_path/'lock'
    with driver.package_lock(path):
        with pytest.raises(RuntimeError, match='already|bereits'):
            with driver.package_lock(path):
                pytest.fail('parallel installation accepted')
    with driver.package_lock(path):
        pass
    path.chmod(0o644)
    with pytest.raises(RuntimeError, match='Unsafe'):
        with driver.package_lock(path):
            pytest.fail('unsafe lock accepted')
