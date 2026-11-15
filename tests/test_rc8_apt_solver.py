"""Real APT solver with a private dpkg status, no host installations."""
from pathlib import Path
import subprocess
import importlib.util

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('rc8_driver_solver',ROOT/'install_driver.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)

def test_explicit_upgrade_with_real_apt_and_private_status(tmp_path):
    pkg=tmp_path/'pkg';control=pkg/'DEBIAN';control.mkdir(parents=True)
    pkg.chmod(0o755);control.chmod(0o755)
    (control/'control').write_text('Package: zfsm-upgrade-fixture\nVersion: 2\nArchitecture: all\nMaintainer: Test <test@localhost>\nDescription: Offline solver fixture\n')
    deb=tmp_path/'zfsm-upgrade-fixture_2_all.deb'
    subprocess.run(['dpkg-deb','--root-owner-group','--build',str(pkg),str(deb)],check=True,capture_output=True)
    status=tmp_path/'status'
    status.write_text('Package: zfsm-upgrade-fixture\nStatus: install ok installed\nArchitecture: all\nVersion: 1\nMaintainer: Test <test@localhost>\nDescription: Offline solver fixture\n\n')
    args=['apt-get','--simulate','--no-remove','--no-install-recommends','-o','Dir::State::status='+str(status),'-o','Dir::Etc::sourcelist=-','-o','Dir::Etc::sourceparts=-']
    restricted=subprocess.run([*args,'--no-upgrade','install',str(deb)],check=True,capture_output=True,text=True)
    assert not any(x.startswith('Inst ') for x in restricted.stdout.splitlines())
    proper=subprocess.run([*args,'install',str(deb)],check=True,capture_output=True,text=True)
    driver.plan_changes(proper.stdout,['zfsm-upgrade-fixture'])
    assert 'Inst zfsm-upgrade-fixture [1] (2 ' in proper.stdout
    assert 'Version: 1' in status.read_text()
