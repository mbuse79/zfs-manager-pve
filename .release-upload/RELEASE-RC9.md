RC9 bringt die kompakte native ZFS-Manager-Oberfläche: Poolübersicht mit CAP/FRAG, einklappbare Details, zwei Snapshot-Tabs und eine zusammengeführte Aufbewahrungstabelle. Der Installer unterstützt Neuinstallation und RC7-/RC8-Upgrade auf strukturell passenden PVE-9.x-Versionen, ohne allgemeine System-/Proxmox-Upgrades.

Der Betreiber hat am 15.11.2026 die angeforderten Praxistests auf Test-PVE und bestehendem Host als erfolgreich bestätigt und die Veröffentlichung beauftragt. Zusätzlich: 252 unterschiedliche lokale Regressionstests sowie DE/EN-Browsertests mit echtem ExtJS 7 und API-Fixtures. Kein realer Offline-Rescue-Test wird behauptet.

**Das veröffentlichte DEB ist bytegleich zum getesteten Paket:**
`f48f7cfef9aacd070a3185c896b49b85149c90fe4b4595a15929bd2dee6a776f`

- `BuMaVory-ZFS-Manager-1.0.0-34-rc9.zip`: vollständige Lieferung mit DEB, Quellen/Builddateien, Installern, zusätzlichen Abhängigkeiten samt Lizenzen/korrespondierenden Quellen und Manifest.
- `bootstrap-rc9.sh`: SHA256 `ae5cf53ac8bed2bc71e1ede9502de95b018828387505a11b37124ce4c34ac0d5`.
- `SHA256SUMS`: äußere Prüfsummen aller Release-Dateien.
- GitHub ersetzt im einzelnen DEB-Dateinamen `~` durch `.`. Die Paketversion bleibt `1.0.0-34~rc9`; im ZIP bleibt der ursprüngliche Dateiname erhalten.
- [Öffentliche Installation und Prüfmodus](https://github.com/mbuse79/zfs-manager-pve/blob/main/docs/INSTALL-RC9.md).

Die öffentliche ZIP hat eine neue Prüfsumme, weil interne Übergabeunterlagen entfallen und öffentliche Dokumentation ergänzt wurde. DEB und ausführbare Installer bleiben unverändert. Sicherheits-/Gast-/Replikationsschutz bleibt erhalten; automatische Notfallbereinigung ist standardmäßig AUS. Bestehende AutoSnap-Aufbewahrung kann weiterhin bei Zeitplanläufen ältere automatische Snapshots entfernen.

RC9 bleibt mit seiner getesteten Versionskennung ein **Release Candidate**. Der ältere stabile Release v1.0.0-32 und dessen Assets bleiben unverändert. `quick-install.sh` richtet sich weiterhin an diesen älteren stabilen Release; für RC9 den versionierten Bootstrap/ZIP-Weg verwenden.

---

RC9 provides the compact native UI and guarded PVE-9.x fresh-install/upgrade path. The operator confirmed the requested practice tests and authorized publication. The DEB is the exact tested artifact; the public ZIP/source checksums are new because internal handovers were omitted and public documentation added. See the installation guide, source archive and SHA256SUMS. Destructive operations remain guarded; no real offline-rescue hardware validation is claimed. Third-party dependencies retain their own licenses and corresponding sources.
