# Installation and upgrade – v1.0.0-32

**Private packaging candidate (`1.0.0-32+docs2`):** The future reviewed binary has its own version and checksum; it is not yet live-tested and must not be published or described as the tested `1.0.0-32` binary. The tested 2026-11-07 baseline remains unchanged. See `PACKAGE-STATUS.md`.


**Validated final environment:** Proxmox VE 9.2.25. Root access is required. The exact final 1.0.0-32 Debian package was installed as an APT upgrade from RC1 on 2026-11-07; CLI and GUI were reported working by the test host owner.

1. Obtain the .deb from a trusted GitHub Release after public approval.
2. Verify the published SHA256 checksum. A checksum validates file integrity, **not** software trust or authenticity by itself.
3. Copy the .deb to the target Proxmox host and run:

```bash
apt install ./pve-zfs-manager_1.0.0-32_all.deb
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
systemd-run --unit=zfsm32-install --collect /usr/bin/apt-get install -y /root/pve-zfs-manager_1.0.0-32_all.deb
journalctl -u zfsm32-install -n 50 --no-pager
```

### Before production use

Keep independent backups and perform a recovery test. Destructive snapshot operations are not atomic across datasets. The software integrates into Proxmox's existing GUI/API files and may need repair after upstream changes. Do not assume compatibility with untested releases.

### Uninstall

```bash
apt remove pve-zfs-manager
```

Inspect retained backup and policy files rather than deleting Proxmox GUI files manually. Diagnostic commands include `zfsm check`, `zfsm backups` and `zfsm logs`.

> **Hinweis / note (2026-11-09):** The command examples above refer to the already tested historical `1.0.0-32` binary. Do not substitute the private `+docs2` candidate until its exact SHA256 and live validation are confirmed.
