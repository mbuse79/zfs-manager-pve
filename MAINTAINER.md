# Maintainer contact / Maintainer-Kontakt

**Project / Projekt:** BuMaVory ZFS Manager for Proxmox VE  
**Maintainer / Ansprechpartner:** BuMaVory Project  
**E-mail / E-Mail:** [bumavory@buse.rocks](mailto:bumavory@buse.rocks)

The mailbox has been reported as configured by its operator. An independent delivery test has not been performed here. / Das Postfach ist laut Betreiber eingerichtet. Ein unabhängiger Zustelltest wurde hier noch nicht durchgeführt.

**Private security reporting / Vertrauliche Sicherheitsmeldungen:** See [SECURITY.md](SECURITY.md).

## Debian package build (private QA, public rights check still pending)

```bash
ZFSM_MAINTAINER_NAME="BuMaVory Project" \
ZFSM_MAINTAINER_EMAIL="bumavory@buse.rocks" \
./build_deb.sh

dpkg-deb -f pve-zfs-manager_1.0.0-32_all.deb Maintainer
```

The previous technical final `.deb` contains the old placeholder email and **must not be publicly released**. The new build uses the confirmed project address and includes `LICENSE` and `debian/copyright`. Manual source provenance and live install checks are still required before making the repo public.
