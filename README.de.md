# BuMaVory ZFS Manager für Proxmox VE

**ZFS-Snapshots direkt in der vorhandenen Proxmox-Weboberfläche verwalten.**

[English](README.md) | [Installation](INSTALL.de.md) | [Änderungen](CHANGELOG.md) | [Sicherheit](SECURITY.md)

> **Unabhängiges Community-Projekt.** BuMaVory ZFS Manager ist kein offizielles Produkt von Proxmox und wird nicht von Proxmox Server Solutions GmbH entwickelt oder unterstützt.
>
> **Veröffentlichungsstand:** v1.0.0-32 ist ein technisch fertig gebautes Paket, das für die erste öffentliche Veröffentlichung vorbereitet wird. Lizenzprüfung, echte Maintainer-Kontaktdaten und der abschließende Installationstest stehen noch aus. Das private Repository ist noch keine öffentlich freigegebene Open-Source-Veröffentlichung.

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

- Die Vorabversion RC1 wurde auf **Proxmox VE 9.2.25** installiert und geprüft.
- Die Finalversion v1.0.0-32 basiert auf RC1; Snapshot-API und GUI-Geschäftslogik sind unverändert.
- Die finale `.deb` wurde **noch nicht gesondert auf dem echten Testhost installiert**.
- Andere Proxmox-Versionen müssen jeweils geprüft werden. Es gibt keine pauschale Freigabe aller PVE-9.x-Versionen.

## Installation

Sobald die öffentliche Version freigegeben ist, das Paket `pve-zfs-manager_1.0.0-32_all.deb` aus den **GitHub-Releases** laden und die SHA256-Prüfsumme prüfen. Auf dem Proxmox-Host als root:

```bash
apt install ./pve-zfs-manager_1.0.0-32_all.deb
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

## Lizenz und Marken

Die Lizenz und Hinweise auf Fremdcode werden **noch geprüft**. Diese README vergibt ausdrücklich noch keine Open-Source-Lizenz. Näheres in [LICENSING-REVIEW.md](LICENSING-REVIEW.md) und [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Proxmox und Proxmox Virtual Environment sind Marken der jeweiligen Rechteinhaber. Siehe [TRADEMARK.md](TRADEMARK.md).
