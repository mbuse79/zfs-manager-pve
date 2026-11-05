# BuMaVory ZFS Manager for Proxmox VE

**ZFS snapshot management integrated directly into Proxmox Virtual Environment.**

BuMaVory ZFS Manager is an independent management extension for Proxmox VE. It provides a graphical interface for ZFS snapshots, virtual machines, LXC containers, storage monitoring and recovery operations.

The project is developed under the **BuMaVory** name and is not an official Proxmox product.

## Features

### Proxmox integration

- Integrated into the existing Proxmox web interface
- No separate management web server or port required
- German and English language support
- Interface adapts to the Proxmox environment
- Persistent navigation and expandable snapshot views

### VM and LXC snapshot management

- Snapshot overview grouped by virtual machine or container
- Support for guests with multiple virtual disks
- Coordinated snapshot creation, deletion and rollback
- Individual disk snapshot operations
- Selection and batch deletion of snapshots
- Explicit handling of incomplete snapshot groups
- Confirmation dialogs for destructive operations

### ZFS dataset management

- Dedicated ZFS dataset overview
- Snapshot listing and management
- Individual snapshot deletion
- Storage capacity information
- Visual utilization indicators
- Snapshot and retention analysis

### Monitoring and maintenance

- Read-only capacity and retention analysis
- Dynamic Proxmox version compatibility checks
- Installation repair and recovery functions
- Automatic integration repair after supported updates
- Backup and restore utilities
- Command-line management using `zfsm`

## Compatibility

The release candidate has been tested on:

- **Proxmox VE 9.2.25**
- ZFS-backed storage
- Virtual machines and LXC containers

Other versions may require additional validation. Compatibility checks are not a guarantee that every Proxmox release is supported.

## Installation

Once the public release is available, download the Debian package from the GitHub Releases section.

Copy the package to your Proxmox host and install it as root:

```bash
apt install ./pve-zfs-manager_1.0.0-32_all.deb
```

Verify the installation:

```bash
zfsm version
zfsm status
zfsm check
```

The ZFS Manager should appear in the Proxmox web interface.

## Command-line interface

The `zfsm` command provides administration and diagnostic functions.

Examples:

```bash
zfsm help
zfsm status
zfsm version
zfsm check
zfsm capacity --json
zfsm services
zfsm backups
zfsm logs
```

Additional commands support repair, backup and restore operations.

Use `zfsm help` for the available commands.

## Safety

ZFS snapshot deletion and rollback operations can permanently affect stored data.

Before performing destructive operations:

- Maintain independent, verified backups.
- Verify the selected guest, dataset and snapshot.
- Check the affected disks and snapshots.
- Review the confirmation dialogs carefully.
- Test recovery procedures before relying on them in production.

Snapshots are not a substitute for backups.

## Development status

**Current version:** `1.0.0-32`

The final package has passed local regression testing. The release candidate was also tested on a Proxmox VE 9.2.25 system.

The project is being prepared for its first public release.

## Project family

BuMaVory is intended as a common name for independent infrastructure management projects:

- **BuMaVory ZFS Manager** — ZFS management for Proxmox VE
- **BuMaVory Samba Admin Center** — Samba and Active Directory administration
- **BuMaVory ZFS Replication Manager** — planned ZFS replication management

Each project is intended to remain independently usable.

## License

The open-source license and third-party code attribution are being finalized before public publication.

## Disclaimer

This is an independent community project.

It is not developed, endorsed or supported by Proxmox Server Solutions GmbH.

Proxmox and Proxmox Virtual Environment are trademarks of their respective owners.
