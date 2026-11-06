# BuMaVory ZFS Manager 1.0.0-32 — publication checklist

- [x] Create private repository and add EN/DE READMEs and documentation.
- [x] Recover and inspect the actual technical final source and Debian package.
- [x] Execute Python regression tests (134 passed in local checkout on 2026-11-06).
- [x] Verify installed snapshot API and GUI source match the final build source.
- [x] Run heuristic secret/private-address scan on original final source.
- [x] Prepare a packaging guard for real maintainer and approved licensing.
- [ ] Confirm owners of the code, copied Proxmox fragments and contributors.
- [ ] Approve `AGPL-3.0-only` or another compatible license **explicitly**.
- [ ] Add unmodified `LICENSE` and verified `debian/copyright` (template provided).
- [x] Record the maintainer contact **bumavory@buse.rocks** (mailbox confirmed configured by project owner).
- [x] Document a confidential security reporting address in SECURITY.md.
- [ ] Verify message delivery and optionally enable GitHub private vulnerability reporting.
- [ ] Rebuild the Debian package and run regression + metadata checks.
- [ ] Install the rebuilt final on a disposable PVE 9.2.25 host.
- [ ] Create GitHub tag and release assets with checksums, after approval.
- [ ] Change repository visibility to Public only after clearance.
