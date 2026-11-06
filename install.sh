#!/bin/bash
# Legacy wrapper; prefer direct apt installation of the .deb.
# Safe to run as "bash install.sh" from an extracted release archive.
set -o pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)" || exit 1
MODE="${1:---install}"
DEB="$HERE/pve-zfs-manager_1.0.0-32_all.deb"
if [[ "${EUID}" -ne 0 ]]; then
  echo 'STOPP: Bitte als root auf dem Proxmox-Host ausführen.' >&2
  exit 1
fi
case "$MODE" in
  --check)
    python3 "$HERE/src/universal.py" check
    ;;
  --install)
    if [[ ! -f "$DEB" ]]; then
      echo "STOPP: Debian-Paket fehlt: $DEB" >&2; exit 1
    fi
    # Check version, stock hash and integration shape before touching APT.
    python3 "$HERE/src/universal.py" precheck || exit 1
    if ! command -v zfs-auto-snapshot >/dev/null 2>&1; then
      if ! command -v apt-get >/dev/null 2>&1; then
        echo 'STOPP: apt-get fehlt; bitte zfs-auto-snapshot bereitstellen.' >&2; exit 1
      fi
      echo '===== Fehlende Voraussetzung: zfs-auto-snapshot ====='
      echo 'Nur dieses fehlende Paket installieren; keine Paket-Upgrades und keine Entfernungen.'
      apt-get --simulate --no-remove --no-upgrade --no-install-recommends install zfs-auto-snapshot || exit 1
      apt-get --yes --no-remove --no-upgrade --no-install-recommends install zfs-auto-snapshot || exit 1
    fi
    python3 "$HERE/src/universal.py" check || exit 1
    # dpkg --install is permitted to recover a previously unpacked, unconfigured
    # ZFS Manager. Do not reject an interrupted earlier package setup here.
    echo '===== Debian-Paket installieren ====='
    dpkg --install "$DEB" || exit 1
    /usr/sbin/pve-zfs-manager status
    ;;
  --status|--repair|--reconcile|--rollback|--uninstall)
    if [[ ! -x /usr/sbin/pve-zfs-manager ]]; then
      echo 'STOPP: ZFS Manager ist noch nicht als Debian-Paket installiert.' >&2;exit 1
    fi
    if [[ "$MODE" == --uninstall || "$MODE" == --rollback ]];then
      echo '===== ZFS Manager entfernen; Backups und private Konfiguration bleiben erhalten ====='
      dpkg --remove pve-zfs-manager
    else
      /usr/sbin/pve-zfs-manager "${MODE#--}"
    fi
    ;;
  *)
    echo 'Aufruf: bash install.sh [--check|--install|--status|--repair|--reconcile|--uninstall|--rollback]' >&2
    exit 2
    ;;
esac
