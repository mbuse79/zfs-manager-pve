# Packaging and provenance status — private candidate `1.0.0-32+docs2`

**Created:** 2026-11-09. **PRIVATE QA ONLY.** No release tag was created and GitHub visibility remains unchanged.

## Versions and validation

| Asset | Status |
| --- | --- |
| `pve-zfs-manager_1.0.0-32_all.deb` | Historical final reference; SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`. Installed and CLI/GUI-tested by maintainer on PVE 9.2.25 on 2026-11-07. |
| `pve-zfs-manager_1.0.0-32+docs1_all.deb` | Previous **unreleased**, offline-only documentation QA package. Not installed. |
| `pve-zfs-manager_1.0.0-32+docs2_all.deb` | New PRIVATE candidate built from the accompanying staged source snapshot; documentation and metadata updates only. Offline validation and full baseline runtime comparison documented in QA report. **No live installation yet.** |

The CLI/backend may continue to display functional version `1.0.0-32`; the package manager distinguishes this packaging-only revision with `+docs2` in `dpkg-query`. This is intentional.

## Inclusions and historical documents

- Full unmodified AGPLv3 text (`LICENSE`) and a separate FSF license-text notice in `debian/copyright`.
- Current project-specific `THIRD_PARTY_NOTICES.md`, `CODE-PROVENANCE-REVIEW.md`, and `LICENSING-REVIEW.md` included in the binary package.
- The old 2026-11-03 `ZFS-Manager-1.0.0-32-Final-und-Veroeffentlichung.pdf` remains in the *source repository* strictly as a **historical report**. Its references to missing maintainer contact and an untested 1.0.0-32 are superseded by successful 2026-11-07/09 testing. The PDF is **not bundled** into the new DEB.
- `PUBLICATION-GATE-2026-11-09.md` is an internal gate document, not an installation instruction; it is part of the source-review snapshot but not shipped as a Debian manual.

## Publication is NOT authorized yet

1. Project maintainer confirms, to the best of their knowledge, the origin of the core implementation and any specific third-party copied templates. No unverified blanket authorship is claimed.
2. Any confirmed external contributions must retain applicable license, copyright attribution and source notices, if required. Comparisons of limited `pve-manager` samples are only partial technical evidence.
3. The exact candidate DEB SHA256 is checked and that **same** package installed/checked on `pve-test` (non-destructive smoke test, with backups).
4. Source tree, license/notice files and release assets are matched to the definitive Git commit (currently the provided bundle is older than the maintainer-confirmed remote HEAD). Review full reachable Git history before making the repository public.
5. Only then: deliberate public release decision and publication; no tag/release upload automatically performed.

*Technical packaging record; not legal advice.*
