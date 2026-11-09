# BuMaVory ZFS Manager 1.0.0-32 — publication checklist

- [x] Create private repository and add EN/DE READMEs and documentation.
- [x] Recover and inspect technical final source and the **already tested** Debian package.
- [x] Execute Python regression tests (138 passed on 2026-11-09 in Git bundle checkout).
- [x] Verify all 33 Python/Perl source files match the tested final Debian package.
- [x] Check integrity of the reachable Git history (10 commits; branch main, no tags as exported).
- [x] Run heuristic text-based secret/private-address scan; no confirmed credentials detected (not exhaustive).
- [x] Maintainer selected AGPL-3.0-only for project-owned contributions; complete `LICENSE` exists.
- [x] Final DEB has version 1.0.0-32 and maintainer BuMaVory Project <bumavory@buse.rocks>.
- [x] **Final DEB was installed and CLI/GUI tested** on Proxmox VE 9.2.25 on 2026-11-07; SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`.
- [x] Add draft `debian/copyright` and informational `THIRD_PARTY_NOTICES.md`.
- [ ] Verify actual origin and rights of original and adapted project sources, including historical code variants and Proxmox anchors.
- [ ] Revise `debian/copyright`, code comments/SPDX notices and `THIRD_PARTY_NOTICES.md` as justified by provenance findings.
- [ ] Perform independent delivery/reply test of bumavory@buse.rocks; consider private GitHub vulnerability reporting.
- [ ] Review all historical documents for publication suitability; normal deletion leaves them in the Git history.
- [ ] Prepare an approved public source archive, excluding obsolete private reports; verify its checksums.
- [ ] Create and verify a Git tag v1.0.0-32 and release assets, **only after legal clearance**.
- [ ] Change repository visibility to Public only after release approval.

No new Debian build or PVE install is required solely to correct repository documentation, provided the released DEB is exactly the tested SHA256 above. Any changed code/binary requires fresh validation.
