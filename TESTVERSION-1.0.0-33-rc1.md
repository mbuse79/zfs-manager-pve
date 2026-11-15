# BuMaVory ZFS Manager 1.0.0-33 RC1 – TEST ONLY

**Not an official release.** Built from the verified published 1.0.0-32+docs2 source archive
(SHA256 `447705f9ce11d9ccb8678d44d0cfe5d87b5bdf1b86ac11b012bed401c9aed1a8`).
The public GitHub release `v1.0.0-32` and production package remain unchanged.

## Changes

- Dynamic ZFS pool topology via read-only `zpool list`, `zpool status -P`, `findmnt`,
  `lsblk` and Proxmox `storage.cfg`. Pool roles are derived at runtime; no fixed
  `rpool` or `rpool_2` assumptions. Unrelated PBS/passthrough disks are not advertised
  as unused/available storage.
- New authenticated read-only API route `pool-topology`, shown in a collapsible pool/vdev/disk tree.
- Fast UI guest-status list via a single read-only `pvesh get /cluster/resources --type vm`.
  Missing status is `unknown` and disables destructive controls.
- Destructive per-guest `resolve` retains a fresh `qm status` / `pct status` check
  for the selected guest. Existing preview tokens, rights checks and ZFS write
  validation are retained.

## Known limitations

- Only PVE 9.x package compatibility; final 9.2.26 validation is pending.
- More CPU optimization for multi-snapshot delete previews may be required after measurements.
- Root filesystem and pool membership are detected automatically when readable;
  unavailable information is reported as unknown, never assumed.
- Root UI still requires a browser smoke test; offline unit tests cannot prove PVE integration.

## Install for a *test host only*, after a backup

Do not use the old public one-liner. Copy the attached Debian package to the test host
and run `dpkg -i ./pve-zfs-manager_1.0.0-33~rc1_all.deb`, then `zfsm status`
and `zfsm check`. Do not deploy to production PVE4 yet.
