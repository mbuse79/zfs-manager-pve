#!/bin/bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# Private packaging-only documentation revision; source/runtime version remains 1.0.0-32.
PACKAGE_VERSION='1.0.0-32+docs2'
PACKAGE_FILE="pve-zfs-manager_${PACKAGE_VERSION}_all.deb"
# Passing packaging checks is not a legal provenance/redistribution clearance.

# PUBLIC RELEASE GATES. A legal open-source release must have an approved
# LICENSE, copyright/third-party attribution, and reachable maintainer.
# No changes are made to the host or build files before these checks succeed.
MAINTAINER_NAME="${ZFSM_MAINTAINER_NAME:-BuMaVory ZFS Manager Maintainers}"
MAINTAINER_EMAIL="${ZFSM_MAINTAINER_EMAIL:-}"
if [[ ! "$MAINTAINER_EMAIL" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] ||
   [[ "$MAINTAINER_EMAIL" == *.invalid ]] || [[ "$MAINTAINER_EMAIL" == *example.* ]]; then
  echo "STOP: Set ZFSM_MAINTAINER_EMAIL to a real, authorized and reachable contact." >&2
  exit 2
fi
if [[ ! "$MAINTAINER_NAME" =~ ^[A-Za-z0-9_.\ ,+-]+$ ]]; then
  echo "STOP: Invalid ZFSM_MAINTAINER_NAME; use a simple package maintainer name." >&2
  exit 2
fi
if [[ ! -s "$HERE/LICENSE" ]] || [[ ! -s "$HERE/debian/copyright" ]]; then
  echo 'STOP: Approved LICENSE and Debian copyright file are required before packaging.' >&2
  exit 2
fi
BUILD="$HERE/_deb_build"
rm -rf "$BUILD"
mkdir -p "$BUILD/lib/systemd/system" "$BUILD/DEBIAN" "$BUILD/usr/lib/pve-zfs-manager/libexec" "$BUILD/usr/lib/pve-zfs-manager/PVE/API2" "$BUILD/usr/sbin" "$BUILD/usr/share/doc/pve-zfs-manager"
cp "$HERE/systemd/"*.service "$HERE/systemd/"*.timer "$HERE/systemd/"*.path "$BUILD/lib/systemd/system/"
cp "$HERE/src/"*.py "$BUILD/usr/lib/pve-zfs-manager/"
cp "$HERE/src/libexec/guest_policy.py" "$HERE/src/libexec/guest_policy_rc9.py" "$HERE/src/libexec/guest_policy_v1_10.py" "$BUILD/usr/lib/pve-zfs-manager/libexec/"
cp "$HERE/src/PVE/API2/ZFSSnapshotViewer_rc9.pm" "$BUILD/usr/lib/pve-zfs-manager/PVE/API2/"
cp "$HERE/src/PVE/API2/ZFSSnapshotViewer_rc6.pm" "$BUILD/usr/lib/pve-zfs-manager/PVE/API2/"
cp "$HERE/src/PVE/API2/ZFSSnapshotViewer_rc8r2.pm" "$BUILD/usr/lib/pve-zfs-manager/PVE/API2/"
cp "$HERE/src/PVE/API2/ZFSSnapshotViewer_rc7.pm" "$BUILD/usr/lib/pve-zfs-manager/PVE/API2/"
cp "$HERE/src/PVE/API2/ZFSSnapshotViewer_v1_6.pm" "$HERE/src/PVE/API2/ZFSSnapshotViewer_v1_5.pm" "$HERE/src/PVE/API2/ZFSSnapshotViewer_v1_4.pm" "$BUILD/usr/lib/pve-zfs-manager/PVE/API2/"
cp "$HERE/src/PVE/API2/ZFSSnapshotViewer.pm" "$BUILD/usr/lib/pve-zfs-manager/PVE/API2/"
cp "$HERE/README.md" "$HERE/CHANGELOG.md" "$HERE/RELEASE_NOTES.md" "$HERE/INSTALL.md" "$HERE/SECURITY.md" "$HERE/TRADEMARK.md" "$HERE/THIRD_PARTY_NOTICES.md" "$HERE/RELEASE-QA.md" "$HERE/LICENSING-REVIEW.md" "$HERE/INSTALL-DE.md" "$HERE/RELEASE_NOTES-DE.md" "$BUILD/usr/share/doc/pve-zfs-manager/"
cp "$HERE/CODE-PROVENANCE-REVIEW.md" "$HERE/MAINTAINER.md" "$HERE/INSTALL.de.md" "$HERE/PACKAGE-STATUS.md" "$BUILD/usr/share/doc/pve-zfs-manager/"
cp "$HERE/LICENSE" "$BUILD/usr/share/doc/pve-zfs-manager/LICENSE"
cp "$HERE/debian/copyright" "$BUILD/usr/share/doc/pve-zfs-manager/copyright"
cat > "$BUILD/DEBIAN/control" <<EOF
Package: pve-zfs-manager
Version: ${PACKAGE_VERSION}
Section: admin
Priority: optional
Architecture: all
Maintainer: ${MAINTAINER_NAME} <${MAINTAINER_EMAIL}>
Depends: python3, perl, pve-manager (>= 9.1.1), zfsutils-linux, zfs-auto-snapshot
Description: ZFS Manager integration for Proxmox VE (community release)
 Integrated ZFS status and guarded snapshot management in the
 Proxmox node UI at port 8006. Uses structural compatibility checks for supported PVE 9.x layouts.
 This package patches known GUI/API hooks with guarded rollback.
 Unofficial community software; validate independently before production use.
EOF
cat > "$BUILD/DEBIAN/preinst" <<'EOF'
#!/bin/sh
set -e
case "$1" in
  install|upgrade)
    if ! command -v pveversion >/dev/null 2>&1; then
      echo 'STOPP: Proxmox VE wurde nicht gefunden.' >&2; exit 1
    fi
    case "$(pveversion)" in
      pve-manager/9.*) : ;;
      *) echo 'STOPP: Nicht unterstützte Proxmox-Hauptversion.' >&2; exit 1 ;;
    esac
    ;;
esac
exit 0
EOF
cat > "$BUILD/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
case "$1" in
  configure)
    python3 /usr/lib/pve-zfs-manager/universal.py install
    systemctl daemon-reload
    systemctl enable --now pve-zfs-manager-reconcile.path pve-zfs-manager-reconcile.timer
    ;;
esac
exit 0
EOF
cat > "$BUILD/DEBIAN/prerm" <<'EOF'
#!/bin/sh
set -e
case "$1" in
  remove)
    systemctl disable --now pve-zfs-manager-reconcile.path pve-zfs-manager-reconcile.timer || true
    systemctl stop pve-zfs-manager-reconcile.service || true
    python3 /usr/lib/pve-zfs-manager/universal.py uninstall
    ;;
  upgrade|deconfigure) : ;;
esac
exit 0
EOF
cat > "$BUILD/DEBIAN/postrm" <<'EOF'
#!/bin/sh
set -e
# Never delete private backups, admin policies, or existing snapshots.
case "$1" in remove|purge) systemctl daemon-reload || true ;; esac
# Cleanup of user-specific data requires a separate explicit request.
exit 0
EOF
cat > "$BUILD/usr/sbin/zfsm" <<'EOF'
#!/bin/sh
exec python3 /usr/lib/pve-zfs-manager/zfsm_cli.py "$@"
EOF
cat > "$BUILD/usr/sbin/pve-zfs-manager-admin" <<'EOF'
#!/bin/sh
exec python3 /usr/lib/pve-zfs-manager/adminctl.py "$@"
EOF
cat > "$BUILD/usr/sbin/pve-zfs-manager" <<'EOF'
#!/bin/sh
if [ "$#" -ne 1 ]; then
  echo 'Aufruf: pve-zfs-manager [--]check|install|status|repair|repair-force|reconcile|uninstall|rollback' >&2
  exit 2
fi
case "$1" in
  --check|--install|--status|--repair|--reconcile|--uninstall|--rollback)
    exec python3 /usr/lib/pve-zfs-manager/universal.py "${1#--}" ;;
  *) exec python3 /usr/lib/pve-zfs-manager/universal.py "$1" ;;
esac
EOF
chmod 755 "$BUILD/DEBIAN/preinst" "$BUILD/DEBIAN/postinst" "$BUILD/DEBIAN/prerm" "$BUILD/DEBIAN/postrm" "$BUILD/usr/sbin/pve-zfs-manager" "$BUILD/usr/sbin/pve-zfs-manager-admin" "$BUILD/usr/sbin/zfsm"
find "$BUILD/usr/lib/pve-zfs-manager" -type f -exec chmod 644 '{}' +
chmod 755 "$BUILD/usr/lib/pve-zfs-manager/universal.py" "$BUILD/usr/lib/pve-zfs-manager/adminctl.py"
find "$BUILD" -type d -exec chmod g-s {} +
find "$BUILD" -type d -exec chmod 0755 {} +
dpkg-deb --root-owner-group --build "$BUILD" "$HERE/$PACKAGE_FILE"
echo '===== Kontrollinformationen ====='
dpkg-deb -I "$HERE/$PACKAGE_FILE" | head -50
