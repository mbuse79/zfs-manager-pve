# BuMaVory ZFS Manager für Proxmox VE

**Geprüfte Paketrevision (`1.0.0-32+docs2`):** Die exakte DEB (SHA256 `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`) wurde am **09.11.2026** per APT auf `pve-test` mit Proxmox VE 9.2.25 installiert. Der Maintainer bestätigte `zfsm version`, `zfsm status`, `zfsm check`, `zfsm services` und die Weboberfläche. Der Laufzeitcode ist gegenüber der zuvor getesteten `1.0.0-32` unverändert. Dies ist keine Kompatibilitätsfreigabe für andere PVE-Versionen und kein unabhängiges Rechtsgutachten. Siehe `PACKAGE-STATUS.md`.


**ZFS-Snapshots direkt in der vorhandenen Proxmox-Weboberfläche verwalten.**

[English](README.md) | [Installation](INSTALL.de.md) | [Änderungen](CHANGELOG.md) | [Sicherheit](SECURITY.md)

> **Unabhängiges Community-Projekt.** BuMaVory ZFS Manager ist kein offizielles Produkt von Proxmox und wird nicht von Proxmox Server Solutions GmbH entwickelt oder unterstützt.
>
> **Veröffentlichungsstand (10.11.2026):** Das Repository ist öffentlich. [v1.0.0-32](https://github.com/mbuse79/zfs-manager-pve/releases/tag/v1.0.0-32) wurde mit dem geprüften Debian-Paket `1.0.0-32+docs2` veröffentlicht. `AGPL-3.0-only` gilt für Projektbeiträge, soweit die entsprechenden Rechte bestehen. Die technische Codeherkunfts- und Lizenzprüfung wurde durchgeführt: 33 Projektdateien wurden mit 83 relevanten Proxmox-Dateien verglichen. Dabei wurde im geprüften Umfang keine konkrete unzulässige Fremdcodeübernahme nachgewiesen. Die Prüfung ist kein unabhängiges Rechtsgutachten.

## Funktionen

- **Direkte Proxmox-Integration:** Eintrag unter dem jeweiligen Proxmox-Knoten, Nutzung des vorhandenen Ports 8006; kein eigener Webserver-Port.
- **VMs und LXC:** Snapshots und zugehörige Datenträger eines Gastes gruppiert anzeigen.
- **ZFS-Datasets:** eigene Übersicht der Datasets, Snapshots und Speicherauslastung.
- **Snapshot-Verwaltung:** erstellen, gezielt einzeln löschen, mehrere ausgewählte Snapshots löschen und Rollback mit Bestätigung.
- **Schutz bei mehreren Datenträgern:** fehlende Snapshot-Ziele erkennen und bei unvollständigen Gruppen eine bewusste Entscheidung verlangen. Operationen über mehrere Datasets sind **nicht atomar**.
- **Kapazitätsprüfung:** lesende Auswertung von Pools, Snapshot-Belegung und Aufbewahrungsinformationen; Ausgabe über `zfsm capacity --json`.
- **Sprachen:** Deutsch und Englisch entsprechend der Proxmox-Oberfläche.
- **Wartung:** Diagnose, Reparatur, Sicherungen und überwachte Wiederherstellung der Integration nach unterstützten Proxmox-Updates.

## Kompatibilität und Teststand

- Die Finalversion **1.0.0-32** wurde am 07.11.2026 auf **Proxmox VE 9.2.25** mittels APT-Upgrade von RC1 installiert und geprüft.
- Die Finalversion v1.0.0-32 basiert auf RC1; Snapshot-API und GUI-Geschäftslogik sind unverändert.
- Die historische Final-DEB hat SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`. Das aktuelle Releasepaket `1.0.0-32+docs2` (SHA256 `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`) wurde am 09.11.2026 ebenfalls auf `pve-test` installiert; CLI und Oberfläche funktionieren laut Betreiber.
- Andere Proxmox-Versionen müssen jeweils geprüft werden. Es gibt keine pauschale Freigabe aller PVE-9.x-Versionen.

## Installation

### Schnellinstallation (ein Befehl)

Auf dem **Proxmox-VE-Host** als **root**, vorzugsweise über SSH statt über die Web-Shell:

```bash
wget -qO /root/bmv-zfs-manager-quick-install.sh 'https://raw.githubusercontent.com/mbuse79/zfs-manager-pve/main/quick-install.sh' && bash /root/bmv-zfs-manager-quick-install.sh
```

Das [Schnellinstallationsskript](quick-install.sh) lädt die veröffentlichte DEB nach `/tmp`, prüft deren **fest hinterlegte SHA256-Prüfsumme**, führt vor Änderungen einen schreibgeschützten PVE-GUI/API-Kompatibilitätstest durch und installiert per `dpkg -i`. Nur falls `zfs-auto-snapshot` fehlt, wird diese Abhängigkeit ohne allgemeine System-Upgrades oder Paketentfernungen installiert. Auf PVE **9.2.25** läuft die Installation automatisch; bei anderen PVE-9-Versionen wird vor der Installation eine ausdrückliche Bestätigung verlangt. Andere Hauptversionen werden abgelehnt. Bestehende unabhängige Backups sind erforderlich. Vor dem Ausführen eines aus dem Internet geladenen Root-Skripts den Inhalt prüfen; der Download von `main` ist veränderbar.

### Manuelle Installation

Das veröffentlichte Paket `pve-zfs-manager_1.0.0-32+docs2_all.deb` aus den **GitHub-Releases** laden und die SHA256-Prüfsumme prüfen. Auf dem Proxmox-Host als root:

```bash
apt install ./pve-zfs-manager_1.0.0-32+docs2_all.deb
zfsm version
zfsm status
zfsm check
```

Im Proxmox-Webinterface unter dem jeweiligen Knoten **ZFS Manager** öffnen. Falls nötig, die Browserseite neu laden. Mehr dazu in [INSTALL.de.md](INSTALL.de.md).

## CLI-Beispiele

```bash
zfsm help
zfsm status
zfsm check
zfsm capacity --json
zfsm backups
zfsm services
zfsm logs
```

## Sicherheit

**Löschen und Rollback können Daten unwiderruflich verändern oder vernichten.** Unabhängige Backups anlegen, die betroffenen Datenträger und Snapshots prüfen und Wiederherstellungsabläufe zuerst auf einem Testsystem ausprobieren. Snapshots ersetzen keine Backups. Der ZFS-Wert `USED` ist keine Vorhersage, wie viel Speicher eine Löschung freigibt.

## Die BuMaVory-Projektfamilie

BuMaVory ist als gemeinsame Dachmarke für voneinander unabhängige Softwareprojekte vorgesehen:

- BuMaVory ZFS Manager – dieses Projekt.
- BuMaVory Samba Admin Center – separates Projekt.
- BuMaVory ZFS Replication Manager – geplantes separates Projekt.

## Kontakt

Maintainer: **BuMaVory Project** — [bumavory@buse.rocks](mailto:bumavory@buse.rocks). Sicherheitsmeldungen bitte vertraulich senden; siehe [SECURITY.md](SECURITY.md).

## Lizenz und Marken

**Lizenz für eigene Projektbeiträge: [GNU AGPLv3 only](LICENSE) (`AGPL-3.0-only`).** Der technische Codeherkunfts- und Lizenzabgleich wurde am 09.11.2026 dokumentiert; im untersuchten Vergleichskorpus wurde keine konkrete unzulässige Fremdcodeübernahme nachgewiesen. Tatsächlich später belegte fremde Quelltextanteile erhalten die jeweils erforderlichen Urheberrechts- und Lizenzhinweise. Die eigene Lizenzwahl betrifft nicht automatisch Proxmox VE oder andere Drittwerke. Siehe [CODE-PROVENANCE-REVIEW.md](CODE-PROVENANCE-REVIEW.md), [LICENSING-REVIEW.md](LICENSING-REVIEW.md) und [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Proxmox und Proxmox Virtual Environment sind Marken der jeweiligen Rechteinhaber. Siehe [TRADEMARK.md](TRADEMARK.md).

> **Hinweis / note (2026-11-10):** The intended release asset is `1.0.0-32+docs2` (SHA256 above), tested on `pve-test` on 2026-11-09. The original `1.0.0-32` remains a separate historical reference with a different checksum. / Das vorgesehene Release-Paket ist `1.0.0-32+docs2`; nicht mit dem älteren Paket verwechseln.

> **Dokumentationsupdate (10.11.2026):** Korrekturen auf `main` nach der Veröffentlichung verändern weder den bestehenden Release-Tag noch die getestete DEB oder das Quellarchiv. Die Release-Dateien entsprechen dem Stand des Tags.
