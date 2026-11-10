# Packaging and provenance status — live-tested revision `1.0.0-32+docs2`

**Created:** 2026-11-09. **Public release verified:** 2026-11-10, tag `v1.0.0-32`, branch `main`. The published `.deb` is the exact `1.0.0-32+docs2` package tested on 2026-11-09. Older private-draft statements below have been superseded.

## Versions and validation

| Asset | Status |
| --- | --- |
| `pve-zfs-manager_1.0.0-32_all.deb` | Historical final reference; SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`. Installed and CLI/GUI-tested by maintainer on PVE 9.2.25 on 2026-11-07. |
| `pve-zfs-manager_1.0.0-32+docs1_all.deb` | Previous **unreleased**, offline-only documentation QA package. Not installed. |
| `pve-zfs-manager_1.0.0-32+docs2_all.deb` | Separate Debian revision with documentation and metadata updates only. Offline runtime comparison documented in QA report; **exact DEB installed on `pve-test` with Proxmox VE 9.2.25 on 2026-11-09**, CLI and GUI confirmed by maintainer. SHA256 `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`. |

The CLI/backend may continue to display functional version `1.0.0-32`; the package manager distinguishes this packaging-only revision with `+docs2` in `dpkg-query`. This is intentional.

## Inclusions and historical documents

- Full unmodified AGPLv3 text (`LICENSE`) and a separate FSF license-text notice in `debian/copyright`.
- Current project-specific `THIRD_PARTY_NOTICES.md`, `CODE-PROVENANCE-REVIEW.md`, and `LICENSING-REVIEW.md` included in the binary package.
- The old 2026-11-03 `ZFS-Manager-1.0.0-32-Final-und-Veroeffentlichung.pdf` remains in the *source repository* strictly as a **historical report**. Its references to missing maintainer contact and an untested 1.0.0-32 are superseded by successful 2026-11-07/09 testing. The PDF is **not bundled** into the new DEB.
- `PUBLICATION-GATE-2026-11-09.md` is an internal gate document, not an installation instruction; it is part of the source-review snapshot but not shipped as a Debian manual.

## Public release and remaining review items (2026-11-10)

1. Project maintainer confirms, to the best of their knowledge, the origin of the core implementation and any specific third-party copied templates. No unverified blanket authorship is claimed.
2. Any confirmed external contributions must retain applicable license, copyright attribution and source notices, if required. Comparisons of limited `pve-manager` samples are only partial technical evidence.
3. **Completed 2026-11-09:** Exact `+docs2` DEB SHA256 verified, installed and CLI/GUI-checked on `pve-test`; backup taken before upgrade.
4. **GitHub live status (2026-11-10):** The three known internal reports were removed from reachable Git history without changing the file tree. The verified public release tag `v1.0.0-32` points to `75aedfca1e58622ac78395e02ac04366649c1987`. Three assets and their published SHA256 checksums were confirmed. Later `main` documentation commits do not alter that tag.
5. **Published 2026-11-10:** The repository and release are public. Remaining provenance, attribution and private vulnerability reporting checks are still open; publication does not imply they were completed.

*Technical packaging record; not legal advice.*
