#!/usr/bin/env bash
# Compatibility wrapper; for package installations use install-local.sh.
set -Eeuo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${1:---install}" == "--install" ]]; then
  exec bash "$HERE/install-local.sh"
fi
case "${1:-}" in
  --check) exec bash "$HERE/install-local.sh" --check-only ;;
  --status|--repair|--reconcile) exec /usr/sbin/pve-zfs-manager "${1#--}" ;;
  *) echo 'Aufruf: bash install.sh [--install|--check|--status|--repair|--reconcile]' >&2;exit 2 ;;
esac
