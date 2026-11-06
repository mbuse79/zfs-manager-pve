# BuMaVory release 1.0.0-32 — licensing and provenance review

**State: not approved for public distribution.** An automated scan and
package inspection cannot independently establish ownership of all source code.

## Findings

- Existing final Debian package metadata declares the placeholder maintainer
  `contact@example.invalid`. The current GitHub-source build script
  now refuses to build without a real supplied contact.
- No agreed and complete `LICENSE` existed in the provided final source archive.
- Active Python and Perl files lacked SPDX/license headers in the inspected
  original archive; original ownership and upstream text provenance are
  therefore not automatically verified.
- The code uses host-provided Proxmox libraries and patches existing
  Proxmox JS/Perl files during installation. The supplied API Perl module and
  injected JS are separate source files, but any copied/adapted upstream
  fragments still require individual upstream license/copyright verification.
- Proxmox reports AGPLv3 for its VE code. An AGPL-3.0-only outbound license
  is a candidate, but the rights holder has not approved it yet.

## Release gates (all required)

1. Confirm actual author(s), the copyright holder(s) and distribution rights
   for all code, including generated/copied/adapted upstream fragments.
2. Obtain approval of an outbound license, then insert its **complete
   unmodified text** as `LICENSE` and add appropriate SPDX/notice headers.
3. Identify and credit third-party material in `debian/copyright` (start from
   `debian/copyright.template`; do not just rename without verifying it).
4. Provide real `ZFSM_MAINTAINER_EMAIL` and optionally
   `ZFSM_MAINTAINER_NAME`; rebuild/retest the deb.
5. Conduct the final PVE 9.2.25 live-install verification on the newly built
   released artifact and set up a confidential vulnerability reporting route.

References:
https://proxmox.com/en/about/open-source/developers
https://www.gnu.org/licenses/license-compatibility.html
https://www.debian.org/doc/debian-policy/ch-binary.html#the-maintainer-of-a-package
