# ZFS Manager for Proxmox VE - v1.0.0-32 (2026-11-03)

**Documentation-only Debian revision `1.0.0-32+docs2` (2026-11-09): Live-tested; release approval separate.**
The original `1.0.0-32` was installed and CLI/GUI-checked on `pve-test` (Proxmox VE 9.2.25) on 2026-11-07. The exact `+docs2` package was installed as an APT upgrade on 2026-11-09; `zfsm version`, `status`, `check`, `services` and the GUI were confirmed by the maintainer. Runtime components are byte-identical to the baseline. The test does not certify other PVE versions, production use or third-party rights.


Stable version number from successfully installed and browser-checked `1.0.0-32~rc1` on test host `pve-test` (Proxmox VE 9.2.25).

## Included

- Native ZFS Manager node panel on Proxmox port 8006, with guest and dataset tabs.
- Grouped multi-disk and per-disk snapshots; guarded create, delete, exact batch delete, and rollback actions.
- Incomplete snapshot group handling with explicit preview of existing/missing targets.
- Selection highlighting and compact confirmation dialogs.
- Read-only pool capacity, snapshot usage, and retention audit (`zfsm capacity --json`).
- German/English UI, CLI help/status/check/repair/backup/logs/services.
- Self-repair after supported Proxmox 9.x updates with controlled file backups.

## Release caveats

- Tested on Proxmox VE **9.2.25** in one user test environment. Other Proxmox versions, hardware and storage layouts are not validated.
- Single or grouped snapshot destruction can be irreversible; multiple disk deletion is not atomic.
- Snapshot `used` does not predict reclaimed storage space.
- This is third-party community software; it modifies Proxmox integration files and is not supported by Proxmox.
- Legal/open-source publication is conditional on the licensing and maintainer review in `LICENSING-REVIEW.md`.

## Regression basis

RC1 and final: user confirmed APT upgrade to the exact `1.0.0-32` on 2026-11-07, `zfsm version/status/check/services` and GUI on Proxmox VE 9.2.25. Final differs from RC1 in release metadata, nonfunctional documentation, an obsolete hard-coded helper URL, and the CLI display name; ZFS snapshot API and GUI block remain unchanged.
