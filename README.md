# BuMaVory ZFS Manager for Proxmox VE

**ZFS snapshot management integrated into the existing Proxmox VE web interface.**

[Deutsch](README.de.md) | [Installation](INSTALL.md) | [Changelog](CHANGELOG.md) | [Security](SECURITY.md)

> **Independent community project.** BuMaVory ZFS Manager is not an official Proxmox product and is not affiliated with or endorsed by Proxmox Server Solutions GmbH.
>
> **Publication status:** v1.0.0-32 is a technical final build under preparation for a first public release. The `AGPL-3.0-only` license has been selected for original contributions; third-party rights review is still pending. The exact final .deb was successfully upgraded from RC1 on Proxmox VE 9.2.25 on 2026-11-07. Maintainer reports a successful email function test (2026-11-09); independent external delivery evidence has not been inspected. This private repository is not yet a public open-source release.

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
- Final package SHA256: `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`. `zfsm version`, `status`, `check`, `services` and GUI were reported working by the test host owner.
- Other versions and deployments must be independently validated. No blanket compatibility claim for all PVE 9.x releases.

## Installing a release asset

When an approved public release is available, download `pve-zfs-manager_1.0.0-32_all.deb` from the repository's **Releases** page and verify its SHA256 checksum. On a compatible Proxmox host, as root:

```bash
apt install ./pve-zfs-manager_1.0.0-32_all.deb
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

**License for original project contributions: [GNU AGPLv3 only](LICENSE) (`AGPL-3.0-only`).** Third-party source ownership and attribution are still under review. This selection does not relicense Proxmox VE or other parties' code; see [LICENSING-REVIEW.md](LICENSING-REVIEW.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Proxmox and Proxmox Virtual Environment are trademarks of their respective owners. See [TRADEMARK.md](TRADEMARK.md).
