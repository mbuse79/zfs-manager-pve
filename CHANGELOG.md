# Changelog

## 1.0.0-32+docs2 — Private documentation-only package candidate (2026-11-09)

- No changes to the 1.0.0-32 runtime functionality, installed API/GUI scripts, systemd units or Debian maintainer scripts.
- Synchronizes licensing/provenance documents with reviewed repository notes and acknowledges the 2026-11-07 final-version host test.
- Removes a superseded 2026-11-03 PDF from the *binary* package; the old source-tree PDF is retained only as historical material.
- Includes a separate packaging revision because the DEB payload differs from both `1.0.0-32` and the private `+docs1` QA draft.
- Offline-tested only; **not publicly released** and **not yet installed/validated on Proxmox**. Rights clearance remains open.


## 1.0.0-32 — Technical final build (public release pending)

- Final Debian version number derived from the tested `1.0.0-32~rc1`.
- Distribution documentation and source layout prepared for publication.
- Obsolete hardcoded private browser IP removed from a legacy helper.
- No changes to snapshot API or core GUI business logic relative to RC1.
- Final package was installed and checked on `pve-test` / Proxmox VE 9.2.25 on 2026-11-07 (maintainer-reported CLI/GUI pass).

## 1.0.0-32~rc1 — Release candidate

- Local `.deb` package installation tested on Proxmox VE 9.2.25.
- CLI/status/integration checks completed on the test system.
- Corrected English/German singular/plural guest count text.

## Selected earlier changes

- **1.0.0-31:** full-row snapshot selection highlight; survived a Proxmox VE update to 9.2.25.
- **1.0.0-30:** read-only capacity and retention audit, including `zfsm capacity --json`.
- **1.0.0-27:** improved grouped checkbox selection, batch deletion and compact confirmations.
- **1.0.0-23:** exact single-snapshot deletion without deleting newer snapshots.

Detailed historical changelogs are available in the original source archive, but should be reviewed before bulk publication.
