# Installation and upgrade – v1.0.0-32

**Validated RC environment:** Proxmox VE 9.2.25. Root access is required. The final version itself has not yet been live-installed on the test host.

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
