# Maintainer contact / Maintainer-Kontakt

**Stand 2026-11-09:** `bumavory@buse.rocks` wurde nach Mitteilung des Maintainers erfolgreich getestet. Das Referenzpaket `1.0.0-32` hat die korrekten Control-Metadaten. Die private Paketrevision `+docs2` benötigt vor öffentlicher Verteilung einen eigenen Proxmox-Test.


**Project / Projekt:** BuMaVory ZFS Manager for Proxmox VE  
**Maintainer / Ansprechpartner:** BuMaVory Project  
**E-mail / E-Mail:** [bumavory@buse.rocks](mailto:bumavory@buse.rocks)

On 2026-11-09 the maintainer reported a successful email configuration/function test. A separately documented delivery-and-reply test from an unrelated sender has not been independently examined. / Am 09.11.2026 meldete der Maintainer einen erfolgreichen E-Mail-Funktionstest. Ein gesondert dokumentierter Zustell- und Antworttest von einem unabhängigen Absender liegt für diese Prüfung nicht vor.

**Private security reporting / Vertrauliche Sicherheitsmeldungen:** See [SECURITY.md](SECURITY.md).

## Debian package build (private QA, public rights check still pending)

```bash
ZFSM_MAINTAINER_NAME="BuMaVory Project" \
ZFSM_MAINTAINER_EMAIL="bumavory@buse.rocks" \
./build_deb.sh

dpkg-deb -f pve-zfs-manager_1.0.0-32_all.deb Maintainer
```

The final tested `.deb` **already contains** `Maintainer: BuMaVory Project <bumavory@buse.rocks>` (SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`) and was installed successfully on PVE 9.2.25 on 2026-11-07. **Do not rebuild simply to correct the maintainer address.** However, this exact package contains outdated embedded release/licensing documentation; any publication candidate with corrected packaged documents needs a distinct hash and renewed artifact validation. The remaining provenance/attribution review must be completed before public distribution; see `PUBLICATION-GATE-2026-11-09.md`.
