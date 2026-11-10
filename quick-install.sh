#!/usr/bin/env bash
# BuMaVory ZFS Manager – public, version-pinned quick installer (v1.0.0-32).
# Download to /tmp, verify an embedded SHA256, precheck, and install via dpkg.
# This script does not upgrade Proxmox or perform ZFS snapshot operations.
set -Eeuo pipefail

REPO='mbuse79/zfs-manager-pve'
RELEASE='v1.0.0-32'
PACKAGE_VERSION='1.0.0-32+docs2'
DEB="pve-zfs-manager_${PACKAGE_VERSION}_all.deb"
DEB_SHA256='3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d'
URL="https://github.com/${REPO}/releases/download/${RELEASE}/pve-zfs-manager_1.0.0-32%2Bdocs2_all.deb"

say() { printf '\n==> %s\n' "$*"; }
fail() { printf 'STOPP: %s\n' "$*" >&2; exit 1; }

MODE='install'
case "${1:-}" in
  '') ;;
  --download-only) MODE='download' ;;
  -h|--help)
    printf 'BuMaVory ZFS Manager %s\nAufruf: bash quick-install.sh [--download-only]\n' "$PACKAGE_VERSION"
    exit 0 ;;
  *) fail 'Unbekannter Parameter. Erlaubt: --download-only oder --help.' ;;
esac
[[ $# -le 1 ]] || fail 'Zu viele Parameter.'
[[ $EUID -eq 0 ]] || fail 'Bitte als root direkt auf einem Proxmox-VE-Host starten.'
for command_name in pveversion wget sha256sum dpkg dpkg-deb dpkg-query python3; do
  command -v "$command_name" >/dev/null 2>&1 || fail "Benötigter Befehl fehlt: $command_name"
done

PVE_VERSION="$(pveversion)" || fail 'Proxmox VE ist nicht erreichbar.'
# No fixed PVE-minor-version cutoff: a newer PVE 9.x is evaluated by the
# actual read-only integration precheck below instead of rejected by version.
# The immutable published DEB itself only supports PVE 9.x (preinst and
# universal.py); a future PVE 10 needs a separately tested compatible release.
case "$PVE_VERSION" in
  pve-manager/9.*) ;;
  pve-manager/*)
    fail "Das veroeffentlichte Paket enthaelt derzeit nur PVE-9-Kompatibilitaet. $PVE_VERSION benoetigt eine passend getestete neue DEB; die Sperre im Paket wird NICHT umgangen." ;;
  *) fail "Proxmox VE nicht erkannt: $PVE_VERSION" ;;
esac
say "Erkannter Host: $PVE_VERSION"

WORKDIR="$(mktemp -d /tmp/bm-zfsmanager-install.XXXXXXXX)" || fail 'Kann /tmp-Arbeitsverzeichnis nicht anlegen.'
chmod 700 "$WORKDIR"
trap 'rm -rf -- "$WORKDIR"' EXIT
PACKAGE_PATH="$WORKDIR/$DEB"

say 'Offizielle Release-DEB nach /tmp herunterladen'
wget --https-only --tries=3 --timeout=30 -O "$PACKAGE_PATH" "$URL" || fail 'Download von GitHub fehlgeschlagen.'

say 'Feste SHA256-Prüfsumme aus dem verifizierten Release vergleichen'
printf '%s  %s\n' "$DEB_SHA256" "$PACKAGE_PATH" | sha256sum -c - || fail 'SHA256 ist falsch! Paket wird NICHT installiert.'

[[ "$(dpkg-deb -f "$PACKAGE_PATH" Package)" == 'pve-zfs-manager' ]] || fail 'Unerwarteter Debian-Paketname.'
[[ "$(dpkg-deb -f "$PACKAGE_PATH" Version)" == "$PACKAGE_VERSION" ]] || fail 'Unerwartete Debian-Paketversion.'
[[ "$(dpkg-deb -f "$PACKAGE_PATH" Architecture)" == 'all' ]] || fail 'Unerwartete Debian-Architektur.'

if [[ "$MODE" == 'download' ]]; then
  # A fixed path is used only after verified download. Avoid overwriting symlinks.
  DEST="/tmp/$DEB"
  [[ ! -L "$DEST" ]] || fail "Unsicherer Symlink am Ziel: $DEST"
  install -m 0600 "$PACKAGE_PATH" "$DEST"
  say "Download-only fertig: $DEST (SHA256 geprüft; keine Installation)"
  exit 0
fi

CURRENT_VERSION="$(dpkg-query -W -f='${Version}' pve-zfs-manager 2>/dev/null || true)"
if [[ -n "$CURRENT_VERSION" ]]; then
  printf 'Vorhandener ZFS Manager: %s\n' "$CURRENT_VERSION"
  if dpkg --compare-versions "$CURRENT_VERSION" gt "$PACKAGE_VERSION"; then
    say "Bereits installierte ZFS-Manager-Version $CURRENT_VERSION ist neuer als $PACKAGE_VERSION."
    printf '%s\n' 'Kein Downgrade und kein Installationsfehler: Die neuere Version bleibt erhalten.'
    if command -v zfsm >/dev/null 2>&1; then
      zfsm version
      zfsm status
      zfsm check
    fi
    exit 0
  fi
  if [[ "$CURRENT_VERSION" == "$PACKAGE_VERSION" ]] && \
       [[ "$(dpkg-query -W -f='${Status}' pve-zfs-manager 2>/dev/null || true)" == 'install ok installed' ]]; then
    say 'Gleiche Paketversion ist bereits vollständig installiert – keine Neuinstallation.'
    zfsm version
    zfsm status
    zfsm check
    exit 0
  fi
fi

say 'Proxmox-GUI/API-Struktur vor der Installation schreibgeschützt prüfen'
mkdir -p "$WORKDIR/unpacked"
dpkg-deb -x "$PACKAGE_PATH" "$WORKDIR/unpacked" || fail 'Paket kann nicht entpackt werden.'
python3 "$WORKDIR/unpacked/usr/lib/pve-zfs-manager/universal.py" precheck || \
  fail 'PVE-GUI/API-Integrationspruefung fehlgeschlagen. Keine Installation vorgenommen (nicht nur wegen einer neueren Versionsnummer).'

# A newer/unlisted PVE 9.x is NOT blocked by its version. After successful
# structural checks, warn and ask once before modifying the host.
if [[ "$PVE_VERSION" != pve-manager/9.2.25/* ]]; then
  say "Integrationsvorpruefung auch auf $PVE_VERSION erfolgreich"
  printf 'WARNUNG: Die Release-DEB wurde bislang nur auf PVE 9.2.25 live getestet.\n'
  printf 'Deine PVE-Version ist nicht einzeln im Freigabetest bestaetigt.\n'
  [[ -r /dev/tty ]] || fail 'Keine interaktive Zustimmung verfuegbar; der Strukturtest selbst war erfolgreich.'
  printf 'Installation trotz nicht live getesteter PVE-Version fortsetzen? Bitte JA eingeben: '
  IFS= read -r confirmation </dev/tty || fail 'Keine Bestaetigung erhalten.'
  [[ "$confirmation" == 'JA' ]] || fail 'Keine Zustimmung zur Installation; keine Aenderungen ausgefuehrt.'
fi

if [[ "$(dpkg-query -W -f='${Status}' zfs-auto-snapshot 2>/dev/null || true)" != 'install ok installed' ]]; then
  say 'Benötigte Abhängigkeit zfs-auto-snapshot fehlt; nur diese Abhängigkeit installieren'
  command -v apt-get >/dev/null 2>&1 || fail 'apt-get fehlt.'
  apt-get --simulate --no-remove --no-upgrade --no-install-recommends install zfs-auto-snapshot || \
    fail 'Abhängigkeit kann ohne Paket-Upgrades/Entfernungen nicht installiert werden.'
  apt-get --yes --no-remove --no-upgrade --no-install-recommends install zfs-auto-snapshot || \
    fail 'Abhängigkeit konnte nicht installiert werden.'
fi

say 'Geprüfte DEB per dpkg installieren – kein allgemeines System-Upgrade'
dpkg -i "$PACKAGE_PATH" || fail 'dpkg-Installation nicht erfolgreich; keine automatische apt-Reparatur.'

say 'Installation abschließend prüfen'
dpkg-query -W -f='${Package} ${Version} ${Status}\n' pve-zfs-manager
zfsm version
zfsm status
zfsm check
zfsm services
say 'FERTIG: Im Proxmox-Webinterface unter dem Knoten ZFS Manager öffnen (ggf. Strg+F5).'
printf 'Sicherheit: Unabhängige Backups behalten. Snapshot-Löschungen/Rollbacks sind potentiell destruktiv.\n'
