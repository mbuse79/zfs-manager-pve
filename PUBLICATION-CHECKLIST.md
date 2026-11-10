# BuMaVory ZFS Manager 1.0.0-32 — publication checklist

**Updated 2026-11-10 after publication:** The exact `1.0.0-32+docs2` package was installed and CLI/GUI-tested on `pve-test` (PVE 9.2.25) on 2026-11-09. The repository and release `v1.0.0-32` are now public. Completed publication steps and remaining rights/security follow-ups are listed separately.


- [x] Create private repository and add EN/DE READMEs and documentation.
- [x] Recover and inspect technical final source and the **already tested** Debian package.
- [x] Execute Python regression tests (138 passed on 2026-11-09 in Git bundle checkout).
- [x] Verify all 33 Python/Perl source files match the tested final Debian package.
- [x] Check integrity of the Git history: 14 commits, no tags in the 2026-11-10 live private GitHub mirror; baseline `main` at `0db3b44`.
- [x] Run heuristic text-based secret/private-address scan; no confirmed credentials detected (not exhaustive).
- [x] Maintainer selected AGPL-3.0-only for project-owned contributions; complete `LICENSE` exists.
- [x] Final DEB has version 1.0.0-32 and maintainer BuMaVory Project <bumavory@buse.rocks>.
- [x] **Final DEB was installed and CLI/GUI tested** on Proxmox VE 9.2.25 on 2026-11-07; SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`.
- [x] Add draft `debian/copyright` and informational `THIRD_PARTY_NOTICES.md`.
- [x] Compare the project integration code with the provided `pve-manager` 9.2.25 GUI/API files; document short literal anchors and routine API-pattern matches in `CODE-PROVENANCE-REVIEW.md`. This is a **partial technical comparison**, not legal clearance.
- [x] Expand provisional `THIRD_PARTY_NOTICES.md` to distinguish host-only dependencies from potential bundled fragments.
- [x] Record the maintainer origin declaration and complete the defined technical comparison of 33 project files with 83 `pve-manager` files. No confirmed unauthorized code copying found within this scope; a universal original-source verification was not possible.
- [ ] Conditional follow-up: if concrete incorporated third-party fragments are identified later, document origin, copyright, license and required notices in `debian/copyright`, headers/SPDX and `THIRD_PARTY_NOTICES.md`. No specific offending fragment has been confirmed by the existing comparison.
- [x] Separate `+docs2` documentation-corrected DEB prepared, checksum verified, runtime compared, and the exact package installed and GUI/CLI-tested on 2026-11-09. The old original DEB is preserved.
- [x] Publish and verify the separate documentation-corrected `1.0.0-32+docs2` DEB (including revised copyright/notices) with a distinct SHA256 and successful live CLI/GUI check on 2026-11-09. Any future source-only edits on `main` do not retroactively alter these bundled documents.
- [x] Maintainer reported a successful email function test for `bumavory@buse.rocks` on 2026-11-09 (separate external delivery/response evidence not independently inspected).
- [x] Enable GitHub private vulnerability reporting (`gh api .../private-vulnerability-reporting` returned `enabled: true` on 2026-11-10).
- [ ] Finish reviewing historical documents for public suitability. The three identified internal audit files were removed from reachable history before publication; cached or external copies may persist.
- [x] Prepare the release source archive (101 files) and verify its checksum. Before final publication, keep source archive consistent with the chosen Git tag and the release asset `SHA256SUMS`.
- [x] Publish tag `v1.0.0-32` at cleaned commit `75aedfca` with three release assets and matching SHA256 digests. Scoped technical provenance review is completed; no independent comprehensive legal opinion is claimed.
- [x] Change the repository visibility to Public and publish `v1.0.0-32` on 2026-11-10.

The original tested DEB remains a valid technical reference, distinct from `+docs2`. The exact documentation-corrected `+docs2` artifact has its own SHA256 and successfully completed an APT host smoke test on 2026-11-09. Do not mix the two package files or hashes.
