"""AutoSnap mandatory dependency and secure RC6 audit-driven installer."""
from pathlib import Path
import os
import subprocess
import textwrap
import pytest

ROOT=Path(__file__).resolve().parents[1]
HELPER=ROOT/'tests/fixtures/install-local-rc7.sh'


def test_dependency_is_mandatory_and_not_checkzfs_or_zsync():
    build=(ROOT/'build_deb.sh').read_text()
    control=build.split('cat > "$BUILD/DEBIAN/control" <<EOF',1)[1].split('EOF',1)[0]
    assert 'zfs-auto-snapshot' in control
    assert 'checkzfs' not in control.lower()
    assert 'zsync' not in control.lower()
    assert "PACKAGE_VERSION='1.0.0-34~rc9'" in build


def test_autosnap_install_not_done_in_dpkg_hooks():
    build=(ROOT/'build_deb.sh').read_text()
    preinst=build.split('cat > "$BUILD/DEBIAN/preinst"',1)[1].split("\nEOF",1)[0]
    postinst=build.split('cat > "$BUILD/DEBIAN/postinst"',1)[1].split("\nEOF",1)[0]
    assert 'apt-get' not in preinst+postinst
    assert 'zfs destroy' not in preinst+postinst


def test_install_helper_enforces_autosnap_and_no_other_upgrades():
    script=HELPER.read_text()
    assert 'zfs-auto-snapshot' in script
    assert 'apt-get --simulate --no-remove --no-upgrade --no-install-recommends install zfs-auto-snapshot' in script
    assert 'apt-get --yes --no-remove --no-upgrade --no-install-recommends install zfs-auto-snapshot' in script
    assert 'apt-get upgrade' not in script and 'apt-get update' not in script
    assert 'dpkg -i "$DEB"' in script
    assert script.index('python3 "$TMP/pkg/usr/lib/pve-zfs-manager/universal.py" precheck') < script.index('apt-get --simulate')
    assert script.index('apt-get --yes') < script.index('dpkg -i "$DEB"')


def test_install_helper_never_overwrites_cron_or_adds_prune_job():
    script=HELPER.read_text()
    assert 'zfsm_host_audit.py' in script
    assert 'keine automatische Änderung einer Admin-Konfiguration' in script
    assert 'systemctl enable' not in script
    assert 'crontab -r' not in script
    assert 'zfs destroy' not in script
    assert 'rm -rf' in script and '"$TMP"' in script


def _write_executable(path, body):
    path.write_text('#!/bin/bash\n'+textwrap.dedent(body))
    path.chmod(0o755)


def _simulate(tmp_path, autosnap_initial, apt_fails=False, omit_cron=False, pve_version='pve-manager/9.2.26/test', manual_cron_without_package=False):
    if os.geteuid()!=0:
        pytest.skip('Integration test executes only inside an isolated root mock')
    bin_dir=tmp_path/'mock-bin';bin_dir.mkdir()
    pkgdir=tmp_path/'package';pkgdir.mkdir()
    (pkgdir/'pve-zfs-manager_1.0.0-34~rc7_all.deb').write_bytes(b'fake-deb-not-for-installation')
    helper=pkgdir/'install-local.sh';helper.write_bytes(HELPER.read_bytes());helper.chmod(0o755)
    state=tmp_path/'state';state.mkdir()
    if (autosnap_initial and not omit_cron) or manual_cron_without_package:(state/'cron-present').touch()
    if autosnap_initial:
        (state/'auto-installed').touch()
        _write_executable(bin_dir/'zfs-auto-snapshot', 'exit 0\n')
    _write_executable(bin_dir/'pveversion',f"echo '{pve_version}'\n")
    _write_executable(bin_dir/'dpkg-query',r'''
      if [[ "$*" == *pve-zfs-manager* ]]; then exit 1; fi
      if [[ "$*" == *zfs-auto-snapshot* && -e "$FAKE_STATE/auto-installed" ]]; then
        echo 'install ok installed'; exit 0
      fi
      exit 1
    ''')
    _write_executable(bin_dir/'dpkg-deb',r'''
      if [[ "$1" == -f ]];then
        if [[ "$3" == Package ]];then echo pve-zfs-manager;else echo '1.0.0-34~rc7';fi
      elif [[ "$1" == -x ]];then
        mkdir -p "$3/usr/lib/pve-zfs-manager"
        echo '# precheck mock' > "$3/usr/lib/pve-zfs-manager/universal.py"
        echo '# inventory mock' > "$3/usr/lib/pve-zfs-manager/zfsm_host_audit.py"
        echo '# resolver mock' > "$3/usr/lib/pve-zfs-manager/zfsm_autosnap_resolve.py"
      else exit 1; fi
    ''')
    _write_executable(bin_dir/'python3',r'''
      if [[ "$2" == resolve ]]; then echo 'PASS: resolver simulated';exit 0;fi
      if [[ "$2" == precheck ]]; then
        echo 'PASS: precheck simulated';exit 0
      fi
      if [[ "$2" == --json ]]; then
        if [[ -f "$FAKE_STATE/auto-installed" ]]; then
          pkg=installed;ready=true;binary=true
        else
          pkg=absent;ready=false;binary=false
        fi
        if [[ -f "$FAKE_STATE/cron-present" ]]; then
          entries='[{"label":"hourly","keep":24,"source":"/etc/cron.hourly/zfs-auto-snapshot"}]'
        else
          entries='[]'
        fi
        printf '{"schema":1,"autosnap":{"package":"%s","binary":%s,"schedules":%s,"schedule_count":1,"duplicate_labels":[],"ready":%s},"replication":{"systemd_units":[],"native_pve_jobs":0},"warnings":[]}' "$pkg" "$binary" "$entries" "$ready"
        exit 0
      fi
      exit 1
    ''')
    _write_executable(bin_dir/'apt-get',r'''
      echo "$*" >> "$FAKE_STATE/apt-commands"
      if [[ -e "$FAKE_STATE/apt-fails" ]];then exit 1;fi
      if [[ "$*" == *--yes* ]];then
        touch "$FAKE_STATE/auto-installed" "$FAKE_STATE/cron-present"
        printf '#!/bin/sh\nexit 0\n' > "$FAKE_BIN/zfs-auto-snapshot"
        chmod 755 "$FAKE_BIN/zfs-auto-snapshot"
      fi
    ''')
    _write_executable(bin_dir/'dpkg',r'''
      if [[ "$1" == -i ]];then echo "$*" >> "$FAKE_STATE/dpkg-commands"; exit 0;fi
      exit 1
    ''')
    _write_executable(bin_dir/'zfsm', 'exit 0\n')
    if apt_fails:(state/'apt-fails').touch()
    env={**os.environ,'PATH':str(bin_dir)+':/usr/bin:/bin','FAKE_BIN':str(bin_dir),'FAKE_STATE':str(state)}
    res=subprocess.run(['bash',str(helper)],capture_output=True,text=True,env=env,timeout=12)
    return res,state


def test_present_autosnap_is_not_reinstalled(tmp_path):
    proc,state=_simulate(tmp_path,autosnap_initial=True)
    assert proc.returncode==0,proc.stderr+'\n'+proc.stdout
    assert not (state/'apt-commands').exists()
    assert (state/'dpkg-commands').exists()


def test_missing_autosnap_gets_installed_before_zfsm(tmp_path):
    proc,state=_simulate(tmp_path,autosnap_initial=False)
    assert proc.returncode==0,proc.stderr+'\n'+proc.stdout
    assert (state/'auto-installed').exists()
    apt=(state/'apt-commands').read_text().splitlines()
    assert len(apt)==2
    assert '--simulate' in apt[0]
    assert '--yes' in apt[1]
    assert all('zfs-auto-snapshot' in x and '--no-upgrade' in x for x in apt)
    assert (state/'dpkg-commands').exists()


def test_failed_dependency_install_stops_before_dpkg(tmp_path):
    proc,state=_simulate(tmp_path,autosnap_initial=False,apt_fails=True)
    assert proc.returncode!=0
    assert not (state/'dpkg-commands').exists()
    assert 'AutoSnap kann nicht sicher installiert werden' in proc.stderr


def test_intentionally_disabled_autosnap_schedules_are_respected(tmp_path):
    proc,state=_simulate(tmp_path,autosnap_initial=True,omit_cron=True)
    assert proc.returncode==0,proc.stderr+'\n'+proc.stdout
    assert (state/'dpkg-commands').exists()
    assert '0 aktive Zeitpläne' in proc.stdout


def test_non_pve9_stops_before_apt(tmp_path):
    proc,state=_simulate(tmp_path,autosnap_initial=False,pve_version='pve-manager/10.0.0/test')
    assert proc.returncode!=0
    assert not (state/'apt-commands').exists() and not (state/'dpkg-commands').exists()
    assert 'Proxmox VE 9.x erforderlich' in proc.stderr


def test_custom_cron_without_package_stops_before_apt(tmp_path):
    proc,state=_simulate(tmp_path,autosnap_initial=False,manual_cron_without_package=True)
    assert proc.returncode!=0
    assert not (state/'apt-commands').exists()
    assert not (state/'dpkg-commands').exists()
    assert 'Manuelle AutoSnap-Installation' in proc.stderr
