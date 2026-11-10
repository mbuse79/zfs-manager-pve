# Release Notes – ZFS Manager for Proxmox VE 1.0.0-32

**Version:** `1.0.0-32`  
**Stand:** 09.11.2026
**Status:** Öffentlich veröffentlicht am 10.11.2026 als `v1.0.0-32` mit der geprüften DEB `1.0.0-32+docs2`.
**Getestete Proxmox-Version:** 9.2.25 (`1.0.0-32` am 07.11.2026 sowie die exakte `+docs2`-DEB am 09.11.2026 live geprüft)

## Paketrevision `1.0.0-32+docs2`

Nur Dokumentations-/Copyrightbeilagen und Debian-Paketversion angepasst; installierte Runtime bleibt identisch zur am 07.11.2026 geprüften `1.0.0-32`. Die exakte `+docs2`-DEB wurde am **09.11.2026** auf `pve-test` per APT installiert; CLI, Dienste und Weboberfläche wurden bestätigt. Die öffentliche Veröffentlichung erfolgte am 10.11.2026; die Prüfung verbleibender Drittanbieterrechte ist unabhängig davon noch offen.

## Funktionsumfang

- Native Integration in die Weboberfläche auf Port 8006.
- Zwei Registerkarten für VMs/LXC sowie ZFS-Datasets und deren Snapshots.
- Gemeinsame Snapshot-Aktionen über mehrere Datenträger und gezielte Einzel-/Sammellöschung.
- Aufklappbare Snapshots, unabhängige Checkbox-Auswahl und deutliche Hervorhebung.
- Kompakte Bestätigungen, getrennte Sicherheitsschritte für kritische Host-Aktionen.
- Speicher- und Snapshot-Audit inklusive `zfsm capacity --json`.
- Automatische Kompatibilitätsprüfung/Wiederherstellung nach unterstützten PVE-Updates.
- CLI-Kommandos für Status, Prüfung, Reparatur, Sicherungen und Dienste.
- Deutsch/Englisch anhand der Proxmox-Oberflächensprache.

## Änderungen gegenüber RC1

- Debian-Versionsnummer von `1.0.0-32~rc1` auf `1.0.0-32` umgestellt.
- Veröffentlichungsunterlagen und Marken-/Sicherheitshinweise ergänzt.
- Fest eingetragene lokale IP-Adresse aus altem Hilfsskript entfernt.
- Öffentliche Produktbezeichnung in der CLI neutralisiert.
- Snapshot-API und eigentliche GUI-Logik unverändert übernommen.

## Grenzen

Bisher nur die genannte Testumgebung praktisch abgenommen. Mehrplatten-Sammellöschungen sind nicht atomar. Snapshot-Verbrauch ist keine sichere Prognose für freigebbaren Speicher. In Produktion vorab unabhängige Tests und Backups durchführen.

## Öffentliche Lizenzierung

Der Release `v1.0.0-32` ist seit dem 10.11.2026 öffentlich. Die Maintainer-Adresse ist `bumavory@buse.rocks` (im Debian-Paket bestätigt; E-Mail-Funktionstest laut Maintainer am 09.11.2026 erfolgreich). Die mögliche Herkunft fremder Vorlagen und deren Rechtehinweise sind unabhängig von der Veröffentlichung weiterhin zu prüfen.
