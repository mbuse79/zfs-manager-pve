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
- [x] Compare the project integration code with the provided `pve-manager` 9.2.25 GUI/API files; document short literal anchors and routine API-pattern matches in `CODE-PROVENANCE-REVIEW.md`. This is a **partial technical comparison**, not legal clearance.
- [x] Expand provisional `THIRD_PARTY_NOTICES.md` to distinguish host-only dependencies from potential bundled fragments.
- [ ] Verify actual origin and rights of original and adapted project sources, including historical code variants and Proxmox anchors.
- [ ] Complete attribution and rights review for potentially incorporated fragments; revise `debian/copyright`, file headers/SPDX and notices **where justified by actual evidence**.
- [ ] Correct demonstrably outdated **embedded DEB documents**, including `LICENSING-REVIEW.md` that wrongly claims an old maintainer address. Preserve the original verified DEB; prepare a documentation-corrected candidate with a **new SHA256** and test the exact new artifact before publication.
- [ ] Reconcile all approved copyright/notices with those embedded in that publication candidate.
- [x] Maintainer reported a successful email function test for `bumavory@buse.rocks` on 2026-11-09 (separate external delivery/response evidence not independently inspected).
- [ ] Enable GitHub private vulnerability reporting for the public launch if available.
- [ ] Review all historical documents for publication suitability; normal deletion leaves them in the Git history.
- [ ] Prepare an approved public source archive, excluding obsolete private reports; verify its checksums.
- [ ] Create and verify a Git tag v1.0.0-32 and release assets, **only after legal clearance**.
- [ ] Change repository visibility to Public only after release approval.

The original tested DEB remains a valid technical reference and needs no retest. However, its embedded licensing-review document is demonstrably obsolete. A **different, corrected public DEB** requires its own SHA256 and validation (including packaging checks and a host smoke test), even when runtime files remain byte-for-byte identical. Do not mislabel the new artifact with the old hash.
