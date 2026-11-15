#!/usr/bin/env bash
# RC7 ZIP bootstrap: verify package first, install missing unzip with APT,
# then unpack and run the guarded ZFS Manager installer.
# Usage: bash bootstrap-rc7.sh 'https://nextcloud.example/s/TOKEN/download' SHA256
# This bootstrap has no automatic snapshot deletion or replication management.
set -Eeuo pipefail

stop() { printf 'STOPP: %s\n' "$*" >&2; exit 1; }
step() { printf '\n=== %s ===\n' "$*"; }

[[ $# == 2 ]] || stop 'Aufruf: bash bootstrap-rc7.sh NEXTCLOUD-HTTPS-DOWNLOADURL ZIP-SHA256'
[[ $EUID == 0 ]] || stop 'Bitte als root auf dem Proxmox-Host ausführen.'
URL="$1"
EXPECTED_SHA256="${2,,}"
[[ "$URL" == https://* ]] || stop 'Nur HTTPS-Downloadlinks sind erlaubt.'
[[ "$EXPECTED_SHA256" =~ ^[0-9a-f]{64}$ ]] || stop 'Ungültige SHA256-Prüfsumme.'
for tool in pveversion wget sha256sum apt-get dpkg-query dpkg-deb python3; do
  command -v "$tool" >/dev/null 2>&1 || stop "Erforderlicher Befehl fehlt: $tool"
done
PVE_VERSION="$(pveversion)" || stop 'Proxmox-Version konnte nicht geprüft werden.'
case "$PVE_VERSION" in
  pve-manager/9.*) : ;;
  *) stop "Nur Proxmox VE 9.x unterstützt: $PVE_VERSION" ;;
esac

DIR="${ZFSM_RC7_DIR:-/root/zfsm34-rc7}"
ZIP="$DIR/zfsm34-rc7.zip"
TMP_ZIP="$DIR/.zfsm34-rc7-download-$$.zip"
mkdir -p -- "$DIR"
chmod 700 "$DIR"
trap 'rm -f -- "$TMP_ZIP"' EXIT

step "Proxmox: $PVE_VERSION"
step 'RC7-ZIP über HTTPS laden'
wget --https-only --tries=3 --timeout=30 -O "$TMP_ZIP" "$URL" || stop 'ZIP-Download fehlgeschlagen.'
step 'Release-Prüfsumme kontrollieren – vor Paketinstallation und Entpacken'
ACTUAL_SHA256="$(sha256sum "$TMP_ZIP")"
ACTUAL_SHA256="${ACTUAL_SHA256%% *}"
[[ "${ACTUAL_SHA256,,}" == "$EXPECTED_SHA256" ]] || stop 'ZIP-SHA256 stimmt nicht. Keine Änderungen am Host.'
mv -f -- "$TMP_ZIP" "$ZIP"
echo 'PASS: ZIP-Prüfsumme stimmt.'

if ! command -v unzip >/dev/null 2>&1; then
  step 'unzip fehlt – sichere automatische APT-Nachinstallation'
  # Simulate before making any change, and reject changes to installed packages.
  PLAN="$(apt-get --simulate --no-remove --no-upgrade --no-install-recommends install unzip)" ||
    stop 'APT-Simulation für unzip fehlgeschlagen. ZFS Manager wurde nicht installiert.'
  printf '%s\n' "$PLAN"
  if printf '%s\n' "$PLAN" | grep -Eq '^(Remv|Purg) '; then
    stop 'APT würde vorhandene Pakete entfernen. Abbruch.'
  fi
  while IFS= read -r pkg; do
    if dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -Fxq 'install ok installed'; then
      stop "APT würde ein bereits installiertes Paket ändern: $pkg"
    fi
  done < <(printf '%s\n' "$PLAN" | awk '/^Inst / {print $2}')
  if ! printf '%s\n' "$PLAN" | grep -Eq '^Inst unzip([ :]|$)'; then
    stop 'APT-Simulation plant keine Installation von unzip. Bitte Paketquellen prüfen.'
  fi
  DEBIAN_FRONTEND=noninteractive apt-get --yes --no-remove --no-upgrade --no-install-recommends install unzip ||
    stop 'APT-Installation von unzip fehlgeschlagen; ZFS Manager bleibt unverändert.'
  command -v unzip >/dev/null 2>&1 || stop 'unzip ist nach APT weiterhin nicht verfügbar.'
  echo 'PASS: unzip installiert.'
else
  echo 'PASS: unzip bereits vorhanden – keine Paketänderung.'
fi

step 'Paket entpacken und alle Paket-Prüfsummen prüfen'
unzip -oq "$ZIP" -d "$DIR" || stop 'ZIP konnte nicht entpackt werden.'
[[ -f "$DIR/SHA256SUMS" && -f "$DIR/install-local.sh" ]] || stop 'ZIP-Paket unvollständig.'
( cd "$DIR" && sha256sum -c SHA256SUMS ) || stop 'Einzeldatei-Prüfsummen stimmen nicht.'
DEB="$DIR/pve-zfs-manager_1.0.0-34~rc7_all.deb"
[[ -f "$DEB" ]] || stop 'RC7-DEB fehlt.'
[[ "$(dpkg-deb -f "$DEB" Package)" == 'pve-zfs-manager' ]] || stop 'Falscher Paketname.'
[[ "$(dpkg-deb -f "$DEB" Version)" == '1.0.0-34~rc7' ]] || stop 'Falsche Paketversion.'

step 'Host-Inventur, AutoSnap-Konfliktauswahl und RC7-Installation'
bash "$DIR/install-local.sh"
step 'RC7 wurde erfolgreich installiert'
