# Third-party components and technical attribution review

**Status 2026-11-10:** Scoped technical provenance and attribution review **completed and documented**: 33 project sources compared with 83 relevant `pve-manager` 9.2.25 files; no concrete unauthorized code copying established in this corpus. These findings are **not an independent legal opinion or exhaustive review of all possible upstream sources**. The public release `v1.0.0-32` retains this documented scope. See [`CODE-PROVENANCE-REVIEW.md`](CODE-PROVENANCE-REVIEW.md) and [`LICENSING-REVIEW.md`](LICENSING-REVIEW.md).

## Host components — normally installed separately, not bundled as full sources

- **Proxmox Virtual Environment / `pve-manager`** — third-party host software. The separately supplied `pve-manager` **9.2.25** Debian package identifies **Proxmox Server Solutions GmbH (2010–2026)** and **AGPL-3+** in `usr/share/doc/pve-manager/copyright`. https://github.com/proxmox/pve-manager
- **OpenZFS / `zfsutils-linux`** — existing host-side ZFS implementation/tools. https://openzfs.org/
- **`zfs-auto-snapshot`** — optional/existing host-side automation; verify the license of the particular installed package and version.
- **Perl, Python, Debian/system libraries** — runtime/host dependencies; their licenses are not changed by BuMaVory.
- **ExtJS and Proxmox UI libraries** — interfaces/frameworks accessed by the injected UI; the independent copyright/license status of separately installed components must be preserved. No claim is made that the framework belongs to BuMaVory.

**Do not infer that all these host dependencies are redistributed inside the ZFS Manager .deb.** Each has its own notices, licenses and packaging status.

## Upstream structures referenced by our integration

A static comparison of 33 project Python/Perl sources against 83 JavaScript/Perl files from the user-supplied `pve-manager_9.2.25_all.deb` found:

- `src/patch_nav.py`: a short literal `PVE.node.Config` / `proxmoxNodeServiceView` menu search anchor corresponding to `pvemanagerlib.js`.
- `src/universal.py`: insertion markers for Proxmox GUI (`pvemanagerlib.js`) and API (`PVE/API2/Nodes.pm`); the installer patches the **already installed host files**, rather than bundling these complete originals.
- `src/PVE/API2/ZFSSnapshotViewer.pm` and historical variants: short conventional `register_method` API field patterns also occurring in `Nodes.pm`.
- `src/manager_patch.py` and historical GUI variants: no exact sequence of at least 45 consecutive tokens shared with the inspected `pve-manager` GUI corpus; this does **not** rule out other or adapted sources.

Such interface patterns and short anchors are **not, by themselves, proof of copyright infringement or independently licensed code copies**. If any copyright-relevant original fragments are later confirmed as incorporated, preserve the actual upstream copyright, license and relevant source notices in the correct package and files.

## License scope and conditional attribution maintenance

`AGPL-3.0-only` has been selected **only for contributions that the project may license**. The repository's current `debian/copyright` still has a broad `Files: *` entry and needs file-/fragment-level review if third-party code is found. The historical tested baseline DEB `1.0.0-32` retains older copyright and third-party notices. The published `+docs2` package bundles this updated notice and was installed and CLI/GUI-checked on `pve-test` (PVE 9.2.25) on 2026-11-09. This technical validation is not a legal clearance. No third-party copyright ownership has been inferred from API calls or imports.

**Publication update:** The repository and `v1.0.0-32` release were published on 2026-11-10 after the documented scoped technical comparison. The technical review did not establish concrete unauthorized copying. If identifiable third-party code is later found, the corresponding notices and source attributions must be added. No independent legal clearance is claimed; do not infer that host components are bundled.
