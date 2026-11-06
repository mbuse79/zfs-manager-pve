# BuMaVory release 1.0.0-32 — licensing and provenance review

**State: AGPL-3.0-only selected for original portions; NOT approved for public distribution until remaining provenance checks.** An automated scan and
package inspection cannot independently establish ownership of all source code.

## Findings

- The existing final Debian package still declares the **obsolete** placeholder maintainer
  `contact@example.invalid` and must not be published unchanged. The maintainer
  has confirmed **bumavory@buse.rocks** is configured. The GitHub-source build
  script requires a real `ZFSM_MAINTAINER_EMAIL`; it will use the confirmed address
  when supplied explicitly. Mail delivery remains to be tested independently.
- A complete unmodified AGPLv3 `LICENSE` has now been added to the preparation source tree; it was absent from the old final source archive.
- Active Python and Perl files lacked SPDX/license headers in the inspected
  original archive; original ownership and upstream text provenance are
  therefore not automatically verified.
- The code uses host-provided Proxmox libraries and patches existing
  Proxmox JS/Perl files during installation. The supplied API Perl module and
  injected JS are separate source files, but any copied/adapted upstream
  fragments still require individual upstream license/copyright verification.
- Proxmox reports AGPLv3 for its VE code. The maintainer selected
  `AGPL-3.0-only` on 2026-11-06 for the project-authored portions.
  Rights over any copied/adapted upstream code are NOT thereby established.

## Release gates (all required)

1. Confirm actual author(s), the copyright holder(s) and distribution rights
   for all code, including generated/copied/adapted upstream fragments.
2. **Done for project-authored parts:** `AGPL-3.0-only` selected and
   complete unmodified text added as `LICENSE`. File-by-file authorship/SPDX
   attribution remains part of the outstanding manual rights review.
3. **Partially done:** a `debian/copyright` statement was drafted for
   original contributions and full license. Identify and credit any adapted
   upstream material before public distribution; no third-party authors are
   silently claimed as BuMaVory contributors.
4. Rebuild/retest with the confirmed contact (private verification build; not a public release until provenance review):
   `ZFSM_MAINTAINER_NAME="BuMaVory Project" ZFSM_MAINTAINER_EMAIL=bumavory@buse.rocks ./build_deb.sh`.
   Verify Debian control metadata with `dpkg-deb -f pve-zfs-manager_1.0.0-32_all.deb Maintainer`.
5. Conduct the final PVE 9.2.25 live-install verification on the newly built
   released artifact and set up a confidential vulnerability reporting route.

References:
https://proxmox.com/en/about/open-source/developers
https://www.gnu.org/licenses/license-compatibility.html
https://www.debian.org/doc/debian-policy/ch-binary.html#the-maintainer-of-a-package
