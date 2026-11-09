# Release Notes – ZFS Manager for Proxmox VE 1.0.0-32

**Version:** `1.0.0-32`  
**Stand:** 09.11.2026
**Status:** Technisches Final-Paket, Vorbereitung der öffentlichen Veröffentlichung  
**Getestete Proxmox-Version:** 9.2.25 (Finalversion `1.0.0-32` am 07.11.2026 live geprüft; `+docs2` noch nicht live geprüft)

## Paketrevision `1.0.0-32+docs2`

Nur Dokumentations-/Copyrightbeilagen und Debian-Paketversion angepasst; installierte Runtime bleibt identisch zur am 07.11.2026 geprüften `1.0.0-32`. Diese private QA-Revision wurde noch **nicht** auf einem Proxmox-Host installiert und wird nicht öffentlich vertrieben. Die rechtliche Herkunftsfreigabe ist weiterhin offen.

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

Die technische Final-Version ist noch nicht automatisch zur Veröffentlichung freigegeben. Die Maintainer-Adresse ist `bumavory@buse.rocks` (im Referenzpaket bestätigt; E-Mail-Funktionstest vom Maintainer am 09.11.2026 bestätigt). Codeherkunft und Rechte an möglicherweise übernommenen Vorlagen bleiben vor Veröffentlichung zu klären.
