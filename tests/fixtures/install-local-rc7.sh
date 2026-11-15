#!/usr/bin/env bash
# BuMaVory ZFS Manager 1.0.0-34 RC7 – package-local installer.
# AutoSnap is mandatory. Never upgrade/remove unrelated packages or touch ZFS datasets.
# This script expects the official .deb alongside it (or in the same unpacked folder).
set -Eeuo pipefail

HERE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DEB="$HERE/pve-zfs-manager_1.0.0-34~rc7_all.deb"
EXPECTED_VERSION='1.0.0-34~rc7'

die() { echo "STOPP: $*" >&2; exit 1; }
step() { printf '\n==> %s\n' "$*"; }

if [[ "${EUID}" -ne 0 ]]; then die 'Bitte als root auf dem Proxmox-Host ausführen.'; fi
for executable in pveversion dpkg dpkg-query dpkg-deb python3 apt-get sha256sum; do
  command -v "$executable" >/dev/null 2>&1 || die "Befehl fehlt: $executable"
done
VERSION="$(pveversion)" || die 'pveversion ist nicht verfügbar'
case "$VERSION" in pve-manager/9.*) : ;; *) die "Proxmox VE 9.x erforderlich; erkannt: $VERSION" ;; esac
[[ -f "$DEB" && ! -L "$DEB" ]] || die "DEB nicht gefunden: $DEB"
[[ "$(dpkg-deb -f "$DEB" Package)" == pve-zfs-manager ]] || die 'Falscher Paketname'
[[ "$(dpkg-deb -f "$DEB" Version)" == "$EXPECTED_VERSION" ]] || die 'Falsche Paketversion'
if dpkg-query -W -f='${Version}' pve-zfs-manager >/dev/null 2>&1; then
  CURRENT="$(dpkg-query -W -f='${Version}' pve-zfs-manager)"
  if dpkg --compare-versions "$CURRENT" gt "$EXPECTED_VERSION"; then
    die "Eine neuere Version ($CURRENT) ist bereits vorhanden; kein Downgrade."
  fi
fi

# Check package content before APT. Installer precheck makes NO modifications.
TMP="$(mktemp -d /tmp/zfsm-autosnap-rc7.XXXXXXXX)" || die 'Temporäres Verzeichnis fehlt'
chmod 700 "$TMP"
trap 'rm -rf -- "$TMP"' EXIT
step "Proxmox-Kompatibilität prüfen (nur lesend): $VERSION"
dpkg-deb -x "$DEB" "$TMP/pkg" || die 'DEB konnte nicht gelesen werden'
python3 "$TMP/pkg/usr/lib/pve-zfs-manager/universal.py" precheck || die 'Kompatibilitätsprüfung nicht bestanden'

step 'Paketintegrität prüfen'
# When the ZIP release manifest is alongside the DEB, verify its exact hash.
if [[ -f "$HERE/SHA256SUMS" ]]; then
  expected="$(awk -v file="$(basename "$DEB")" '$2==file {print $1}' "$HERE/SHA256SUMS")"
  [[ "$expected" =~ ^[0-9a-fA-F]{64}$ ]] || die 'Ungültiger oder fehlender SHA256SUMS-Eintrag'
  actual="$(sha256sum "$DEB")"; actual="${actual%% *}"
  [[ "${actual,,}" == "${expected,,}" ]] || die 'DEB-Prüfsumme stimmt nicht'
  echo 'PASS: SHA256 geprüft'
else
  echo 'HINWEIS: Kein SHA256SUMS daneben; Prüfsumme des ZIP/DEB separat prüfen.'
fi

step 'Vorhandene ZFS-Dienste und Zeitpläne erkennen (nur lesend)'
AUDITOR="$TMP/pkg/usr/lib/pve-zfs-manager/zfsm_host_audit.py"
[[ -f "$AUDITOR" && ! -L "$AUDITOR" ]] || die 'Host-Inventur im DEB fehlt.'
python3 "$AUDITOR" --json > "$TMP/inventory-before.json" || die 'Host-Inventur fehlgeschlagen, keine Aenderungen.'
/usr/bin/python3 - "$TMP/inventory-before.json" <<'PYINVENTORY'
import json,sys
with open(sys.argv[1],encoding='utf-8') as fh: report=json.load(fh)
a=report['autosnap'];r=report['replication']
print('AutoSnap: %s | %d vorhandene Zeitpläne' % (a['package'],a['schedule_count']))
print('Externe Replikation: %d Systemd-Units, %d native PVE-Aufträge – nur Erkennung' %
      (len(r['systemd_units']),r['native_pve_jobs']))
for warning in report['warnings'][:12]: print('HINWEIS:',warning)
# A package that is absent but already has custom AutoSnap files can be a
# manually installed copy. Installing the distro package would create duplicates.
if a['package'] != 'installed' and (a['binary'] or a['schedules']):
    print('STOPP: Manuelle AutoSnap-Installation/Zeitpläne ohne DEB erkannt. Nicht überschreiben; bitte zuerst prüfen.',file=sys.stderr)
    sys.exit(1)
# Real conflicts will be presented for an explicit per-label selection below.
PYINVENTORY

step 'AutoSnap-Konflikte mit Auswahl und Sicherung bereinigen (nur falls vorhanden)'
RESOLVER="$TMP/pkg/usr/lib/pve-zfs-manager/zfsm_autosnap_resolve.py"
[[ -f "$RESOLVER" && ! -L "$RESOLVER" ]] || die 'Sicherer AutoSnap-Konfliktassistent fehlt im DEB'
python3 "$RESOLVER" resolve || die 'AutoSnap-Konflikte nicht bestätigt oder nicht sicher bereinigt. ZFS Manager unverändert.'

step 'Pflichtkomponente AutoSnap prüfen'
if dpkg-query -W -f='${Status}' zfs-auto-snapshot 2>/dev/null | grep -Fxq 'install ok installed'; then
  echo 'PASS: zfs-auto-snapshot bereits installiert – keine Paketänderung.'
else
  echo 'AutoSnap fehlt. Installation von AutoSnap (plus nötigen Abhängigkeiten) aus vorhandenen APT-Quellen.'
  echo 'Es werden keine allgemeinen Upgrades, Paketentfernungen oder Recommends ausgeführt.'
  # No apt update, package upgrade, removal or auto-fix. APT's solver must succeed first.
  apt-get --simulate --no-remove --no-upgrade --no-install-recommends install zfs-auto-snapshot || \
    die 'AutoSnap kann nicht sicher installiert werden. ZFS Manager bleibt unverändert.'
  apt-get --yes --no-remove --no-upgrade --no-install-recommends install zfs-auto-snapshot || \
    die 'AutoSnap-Installation fehlgeschlagen; ZFS Manager wurde nicht installiert.'
fi

command -v zfs-auto-snapshot >/dev/null 2>&1 || die 'AutoSnap ist nicht ausführbar.'
# Re-scan after optional APT installation. Custom existing schedules are adopted;
# never install duplicate timers or silently overwrite administrators' cron jobs.
python3 "$AUDITOR" --json > "$TMP/inventory-after.json" || die 'Host-Inventur nach AutoSnap-Installation fehlgeschlagen.'
/usr/bin/python3 - "$TMP/inventory-after.json" <<'PYVERIFY'
import json,sys
with open(sys.argv[1],encoding='utf-8') as fh: d=json.load(fh)
a=d['autosnap']
if a['package'] != 'installed' or not a['binary']:
    print('STOPP: AutoSnap-Paket oder Programm fehlt; keine automatische Änderung einer Admin-Konfiguration.',file=sys.stderr)
    sys.exit(1)
if a['duplicate_labels']:
    print('STOPP: Doppelte AutoSnap-Labels: '+', '.join(a['duplicate_labels']),file=sys.stderr)
    sys.exit(1)
if any(s['keep'] is None or s['label']=='unknown' for s in a['schedules']):
    print('STOPP: Vorhandene AutoSnap-Regel nicht eindeutig; manuell prüfen.',file=sys.stderr)
    sys.exit(1)
print('PASS: AutoSnap-Konfiguration übernommen. '+str(len(a['schedules']))+' aktive Zeitpläne; keine zusätzliche Bereinigung erstellt.')
PYVERIFY
step 'Vorhandene AutoSnap-Regeln respektieren'

step 'ZFS Manager installieren (ohne allgemeines System-Upgrade)'
# dpkg itself cannot and must not invoke APT while holding the package lock.
dpkg -i "$DEB" || die 'DEB-Installation fehlgeschlagen, bitte Ausgabe prüfen.'
step 'Installation und Überwachung kontrollieren'
zfsm version
zfsm status
zfsm check
zfsm emergency status
printf '\nPASS: ZFS Manager %s und Pflichtkomponente AutoSnap installiert.\n' "$EXPECTED_VERSION"
echo 'Hinweis: AutoSnap wird durch die bestehenden Cron-Zeitpläne ausgeführt; Auto-Cleanup des ZFS Managers bleibt AUS.'
