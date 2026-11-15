# Installation and upgrade – v1.0.0-32

**Verified packaging revision (`1.0.0-32+docs2`):** The exact DEB (SHA256 `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`) was installed via APT on `pve-test` (Proxmox VE 9.2.25) on **2026-11-09**. The maintainer confirmed `zfsm version`, `zfsm status`, `zfsm check`, `zfsm services` and the web interface. Its runtime code matches the previously tested `1.0.0-32`; this does not establish compatibility with other PVE versions or complete the rights review. See `PACKAGE-STATUS.md`.


**Validated final environment:** Proxmox VE 9.2.25. Root access is required. The exact `1.0.0-32+docs2` Debian package was installed as an APT upgrade from `1.0.0-32` on 2026-11-09; CLI and GUI were reported working by the test host owner.

1. Obtain the .deb from a trusted GitHub Release after public approval.
2. Verify the published SHA256 checksum. A checksum validates file integrity, **not** software trust or authenticity by itself.
3. Copy the .deb to the target Proxmox host and run:

```bash
apt install ./pve-zfs-manager_1.0.0-32+docs2_all.deb
```

Check the installation:

```bash
dpkg-query -W pve-zfs-manager
zfsm version
zfsm status
zfsm check
zfsm capacity --json
```

Visit the Proxmox VE interface on port 8006 and select **ZFS Manager** under the node. Refresh (Ctrl+F5) if needed.

### If the web shell disconnects

A Proxmox GUI refresh may interrupt an active browser shell. First check whether the package install completed. An optional alternative for a trusted local DEB is:

```bash
systemd-run --unit=zfsm32-install --collect /usr/bin/apt-get install -y /root/pve-zfs-manager_1.0.0-32+docs2_all.deb
journalctl -u zfsm32-install -n 50 --no-pager
```

### Before production use

Keep independent backups and perform a recovery test. Destructive snapshot operations are not atomic across datasets. The software integrates into Proxmox's existing GUI/API files and may need repair after upstream changes. Do not assume compatibility with untested releases.

### Uninstall

```bash
apt remove pve-zfs-manager
```

Inspect retained backup and policy files rather than deleting Proxmox GUI files manually. Diagnostic commands include `zfsm check`, `zfsm backups` and `zfsm logs`.

> **Hinweis / note (2026-11-10):** The intended release asset is `1.0.0-32+docs2` (SHA256 above), tested on `pve-test` on 2026-11-09. The original `1.0.0-32` remains a separate historical reference with a different checksum. / Das vorgesehene Release-Paket ist `1.0.0-32+docs2`; nicht mit dem älteren Paket verwechseln.
