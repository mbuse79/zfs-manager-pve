# Maintainer contact / Maintainer-Kontakt

**Stand 10.11.2026:** Der öffentliche Release `v1.0.0-32` enthält die am 09.11.2026 auf `pve-test` (Proxmox VE 9.2.25) installierte und per CLI/Weboberfläche geprüfte Paketrevision `1.0.0-32+docs2`. Der Maintainer meldete die Adresse `bumavory@buse.rocks` als funktionsfähig. Eine vollständige Prüfung der Drittanbieterrechte liegt nicht vor.


**Project / Projekt:** BuMaVory ZFS Manager for Proxmox VE  
**Maintainer / Ansprechpartner:** BuMaVory Project  
**E-mail / E-Mail:** [bumavory@buse.rocks](mailto:bumavory@buse.rocks)

On 2026-11-09 the maintainer reported a successful email configuration/function test. A separately documented delivery-and-reply test from an unrelated sender has not been independently examined. / Am 09.11.2026 meldete der Maintainer einen erfolgreichen E-Mail-Funktionstest. Ein gesondert dokumentierter Zustell- und Antworttest von einem unabhängigen Absender liegt für diese Prüfung nicht vor.

**Private security reporting / Vertrauliche Sicherheitsmeldungen:** See [SECURITY.md](SECURITY.md).

## Debian package build (public release; rights review ongoing)

```bash
ZFSM_MAINTAINER_NAME="BuMaVory Project" \
ZFSM_MAINTAINER_EMAIL="bumavory@buse.rocks" \
./build_deb.sh

dpkg-deb -f pve-zfs-manager_1.0.0-32+docs2_all.deb Maintainer
```

The historical `1.0.0-32` DEB (SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`) was successfully tested on PVE 9.2.25 on 2026-11-07. The published `1.0.0-32+docs2` DEB (SHA256 `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`) was installed and GUI/CLI-tested on 2026-11-09. Both use `BuMaVory Project <bumavory@buse.rocks>` as maintainer. No rebuild is needed to correct that field. Third-party provenance review remains open; see `LICENSING-REVIEW.md`.
