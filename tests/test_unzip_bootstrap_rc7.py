"""RC7: missing unzip is handled before ZIP extraction (no real APT calls)."""
import hashlib
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _exe(directory, name, body):
    target = directory / name
    target.write_text('#!/bin/bash\nset -Eeuo pipefail\n' + body)
    target.chmod(0o755)
    return target


def _sandbox(tmp_path, apt_inst_lines='Inst unzip (6.0-2 [amd64])'):
    if os.geteuid() != 0:
        pytest.skip('Bootstrap root requirement must be mocked as root')
    binpath = tmp_path / 'bin'
    binpath.mkdir()
    for name in ('bash', 'sha256sum', 'grep', 'awk', 'mv', 'mkdir', 'chmod', 'rm', 'cp', 'ln', 'dirname', 'cat'):
        src = shutil.which(name)
        assert src
        (binpath / name).symlink_to(src)
    (binpath / 'python3').symlink_to(shutil.which('python3'))
    _exe(binpath, 'pveversion', "echo 'pve-manager/9.1.1/test'\n")
    _exe(binpath, 'wget', '''while [[ $# -gt 0 ]]; do
      if [[ "$1" == '-O' ]]; then dest="$2"; shift 2; else shift; fi
    done
    cp "$ZFSM_TEST_ZIP" "$dest"
    ''')
    _exe(binpath,'dpkg-query', "echo 'deinstalliert'; exit 0\n")
    _exe(binpath,'dpkg-deb', "if [[ \"${*: -1}\" == 'Version' ]]; then echo '1.0.0-34~rc7'; else echo 'pve-zfs-manager'; fi\n")
    _exe(binpath,'apt-get', '''echo "$*" >> "$ZFSM_APT_LOG"
    if [[ "$*" == *'--simulate'* ]]; then
        cat "$ZFSM_TEST_APT_SIM"
    else
        ln -s /usr/bin/unzip "$(dirname "$0")/unzip"
    fi
    ''')
    # The realistic prerequisite package already exists on the host.
    fake_zip = tmp_path / 'rc7.zip'
    with zipfile.ZipFile(fake_zip, 'w') as z:
        deb = b'test-deb'
        sh = b'#!/bin/bash\necho RC7-INSTALL-OK\n'
        manifest = (hashlib.sha256(deb).hexdigest() + '  pve-zfs-manager_1.0.0-34~rc7_all.deb\n'
                    + hashlib.sha256(sh).hexdigest() + '  install-local.sh\n').encode()
        z.writestr('pve-zfs-manager_1.0.0-34~rc7_all.deb',deb)
        z.writestr('install-local.sh',sh)
        z.writestr('SHA256SUMS',manifest)
    apt_sim = tmp_path / 'apt-plan'
    apt_sim.write_text(apt_inst_lines+'\n')
    apt_log = tmp_path / 'apt.log'
    env = dict(os.environ, PATH=str(binpath), ZFSM_RC7_DIR=str(tmp_path / 'install'),
               ZFSM_TEST_ZIP=str(fake_zip), ZFSM_TEST_APT_SIM=str(apt_sim), ZFSM_APT_LOG=str(apt_log))
    return env, fake_zip, apt_log, binpath


def _run(env, archive):
    return subprocess.run([str(ROOT / 'bootstrap-rc7.sh'), 'https://nextcloud.example.invalid/s/example/download',
                           hashlib.sha256(archive.read_bytes()).hexdigest()],
                          env=env, text=True, capture_output=True, timeout=15)


def test_missing_unzip_is_installed_before_extract(tmp_path):
    env, archive, apt_log, binpath = _sandbox(tmp_path)
    result = _run(env, archive)
    assert result.returncode == 0, result.stdout+result.stderr
    assert 'PASS: unzip installiert' in result.stdout
    assert 'RC7-INSTALL-OK' in result.stdout
    assert '--simulate --no-remove --no-upgrade --no-install-recommends install unzip' in apt_log.read_text()
    assert '--yes --no-remove --no-upgrade --no-install-recommends install unzip' in apt_log.read_text()
    assert (binpath/'unzip').exists()


def test_abort_if_apt_proposes_an_upgrade(tmp_path):
    env, archive, apt_log, binpath = _sandbox(tmp_path,'Inst sensitive-package (2.0 [amd64])\nInst unzip (6.0 [amd64])')
    # Present an already installed dependency, which may not be upgraded.
    script=binpath/'dpkg-query'
    _exe(binpath,'dpkg-query', '''if [[ "$*" == *sensitive-package* ]]; then
      echo 'install ok installed'
    else
      echo 'deinstalliert'
    fi
    ''')
    result = _run(env, archive)
    assert result.returncode != 0
    assert 'bereits installiertes Paket ändern' in result.stderr
    assert '--yes' not in apt_log.read_text()
    assert not (binpath/'unzip').exists()


def test_bad_zip_hash_does_not_install_unzip(tmp_path):
    env, archive, apt_log, binpath = _sandbox(tmp_path)
    res=subprocess.run([str(ROOT/'bootstrap-rc7.sh'), 'https://nextcloud.example.invalid/s/example/download',
                        'f'*64], env=env, text=True, capture_output=True, timeout=15)
    assert res.returncode != 0
    assert 'ZIP-SHA256 stimmt nicht' in res.stderr
    assert not apt_log.exists()
