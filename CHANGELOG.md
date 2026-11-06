# Changelog

## 1.0.0-32 — Technical final build (public release pending)

- Final Debian version number derived from the tested `1.0.0-32~rc1`.
- Distribution documentation and source layout prepared for publication.
- Obsolete hardcoded private browser IP removed from a legacy helper.
- No changes to snapshot API or core GUI business logic relative to RC1.
- Final package built and regression tests run locally. A separate live installation of the final `.deb` is still pending.

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
