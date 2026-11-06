# Quality assurance - v1.0.0-32

## Live checks already reported by test host owner
- Proxmox VE 9.2.25 and `1.0.0-32~rc1` installed with apt from local DEB, with compatibility PASS and backup.
- `zfsm help/status/services`, GUI and read-only capacity audit displayed as expected.
- Snapshot selection, multi-disk handling, batch deletion and translations confirmed in preceding `1.0.0-27`..`1.0.0-31` releases.

## Final build checks
- Test suite executed on clean copied source, including regression and simulated upgrades.
- JavaScript parse tested, Debian control and maintainer scripts checked, package contents verified.
- Confirmed byte-identical snapshot backend/API and GUI integration block between final and RC1.

## Limits
- Final Debian version not yet installed on real host.
- PVE 9.2.25 is the only live environment validated for RC1; no release claim for all 9.x hosts.
- Dark mode and all failure cases not exhaustively validated; test carefully before production use.
- Legal publication readiness separate; see licensing review.
