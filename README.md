# BuMaVory ZFS Manager for Proxmox VE

**Verified packaging revision (`1.0.0-32+docs2`):** The exact DEB (SHA256 `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`) was installed via APT on `pve-test` (Proxmox VE 9.2.25) on **2026-11-09**. The maintainer confirmed `zfsm version`, `zfsm status`, `zfsm check`, `zfsm services` and the web interface. Its runtime code matches the previously tested `1.0.0-32`; this does not establish compatibility with other PVE versions or constitute an independent legal opinion. See `PACKAGE-STATUS.md`.


**ZFS snapshot management integrated into the existing Proxmox VE web interface.**

[Deutsch](README.de.md) | [Installation](INSTALL.md) | [Changelog](CHANGELOG.md) | [Security](SECURITY.md)

> **Independent community project.** BuMaVory ZFS Manager is not an official Proxmox product and is not affiliated with or endorsed by Proxmox Server Solutions GmbH.
>
> **Publication status (2026-11-10):** This repository is public. [v1.0.0-32](https://github.com/mbuse79/zfs-manager-pve/releases/tag/v1.0.0-32) was released with the exact tested `1.0.0-32+docs2` Debian package. `AGPL-3.0-only` applies to project contributions that the maintainer is entitled to license. The documented technical provenance review compared 33 project sources with 83 relevant Proxmox files and found no concrete unauthorized code copying within that scope. This is not an independent legal clearance.

## Features

- **Native Proxmox integration:** access from the Proxmox node UI on the existing port 8006; no separate management port.
- **VM/LXC overview:** group snapshots and all participating virtual disks under each guest.
- **ZFS dataset overview:** browse datasets, snapshots and capacity indicators.
- **Snapshot operations:** create, delete a selected snapshot, delete selected batches, and roll back with explicit confirmation.
- **Multi-disk safeguards:** show missing or incomplete snapshot targets and require an informed decision when relevant. Operations across datasets are **not atomic**.
- **Storage audit:** read-only pool capacity and snapshot/retention reporting; `zfsm capacity --json`.
- **Localization:** German and English, following the Proxmox interface language.
- **Maintenance:** CLI diagnostics, repair and backup functions, plus guarded integration recovery after supported Proxmox updates.

## Compatibility and test status

- Final **1.0.0-32** installed and tested on **Proxmox VE 9.2.25** on 2026-11-07 (APT upgrade from RC1).
- v1.0.0-32 was built from RC1 without modifying the snapshot API or GUI business logic.
- Historical `1.0.0-32` package SHA256: `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`. The reviewed release asset `1.0.0-32+docs2` was also installed and CLI/GUI-checked on 2026-11-09; its SHA256 is `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`.
- Other versions and deployments must be independently validated. No blanket compatibility claim for all PVE 9.x releases.

## Installing a release asset

### One-command quick installation

Run on a **Proxmox VE host as root**, preferably from SSH instead of the web shell:

```bash
wget -qO /root/bmv-zfs-manager-quick-install.sh 'https://raw.githubusercontent.com/mbuse79/zfs-manager-pve/main/quick-install.sh' && bash /root/bmv-zfs-manager-quick-install.sh
```

The [quick installer](quick-install.sh) downloads the published DEB to `/tmp`, verifies an **embedded SHA256 checksum**, performs a read-only GUI/API compatibility precheck and installs via `dpkg -i`. It installs the missing `zfs-auto-snapshot` dependency only if necessary, without general system upgrades or package removals. Installation is automatic on tested **PVE 9.2.25**. Newer PVE 9.x releases are not blocked merely by version: after a successful structural check the installer requires one explicit warning confirmation. Other major versions need a separately compatible package; the current DEB supports PVE 9.x only. If a newer ZFS Manager package is already installed, it is kept without downgrading. Keep independent backups. Review remote root scripts before running them; the script downloaded from `main` can change.

### Manual installation

Download `pve-zfs-manager_1.0.0-32+docs2_all.deb` from the repository's **Releases** page and verify its SHA256 checksum. On a compatible Proxmox host, as root:

```bash
apt install ./pve-zfs-manager_1.0.0-32+docs2_all.deb
zfsm version
zfsm status
zfsm check
```

Open the node's **ZFS Manager** entry in Proxmox VE and refresh the browser if necessary. See [INSTALL.md](INSTALL.md) for upgrading, verification and recovery notes.

## Command-line examples

```bash
zfsm help
zfsm status
zfsm check
zfsm capacity --json
zfsm backups
zfsm services
zfsm logs
```

## Safety

**Deletion and rollback can permanently change or destroy data.** Keep independent backups, inspect the target disks and snapshots, and test recovery on a non-production node first. ZFS snapshots are not replacements for backups. Reported snapshot `USED` is not a prediction of recoverable space.

## BuMaVory project family

BuMaVory is the intended umbrella name for separate infrastructure projects:

- BuMaVory ZFS Manager — this project.
- BuMaVory Samba Admin Center — separate project.
- BuMaVory ZFS Replication Manager — planned separate project.

## Contact

Maintainer: **BuMaVory Project** — [bumavory@buse.rocks](mailto:bumavory@buse.rocks). For confidential vulnerability reports, see [SECURITY.md](SECURITY.md).

## License and trademarks

**License for original project contributions: [GNU AGPLv3 only](LICENSE) (`AGPL-3.0-only`).** The scoped technical provenance and license review was performed on 2026-11-09; it did not identify concrete unauthorized copying in the inspected comparison corpus. If specific incorporated third-party material is identified later, the applicable rights and notices will be added. The project license does not relicense Proxmox VE or third-party code. See [CODE-PROVENANCE-REVIEW.md](CODE-PROVENANCE-REVIEW.md), [LICENSING-REVIEW.md](LICENSING-REVIEW.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Proxmox and Proxmox Virtual Environment are trademarks of their respective owners. See [TRADEMARK.md](TRADEMARK.md).

> **Hinweis / note (2026-11-10):** The intended release asset is `1.0.0-32+docs2` (SHA256 above), tested on `pve-test` on 2026-11-09. The original `1.0.0-32` remains a separate historical reference with a different checksum. / Das vorgesehene Release-Paket ist `1.0.0-32+docs2`; nicht mit dem älteren Paket verwechseln.

> **Documentation update (2026-11-10):** Corrections to `main` after publication do not change the existing release tag, tested DEB, or release source archive. The release assets reflect the tagged source.
