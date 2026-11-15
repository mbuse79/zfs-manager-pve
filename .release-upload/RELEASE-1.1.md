# BuMaVory ZFS Manager 1.1

Version **1.1** veröffentlicht den vom Betreiber bestätigten RC10-Fix2-Funktionsstand mit einheitlicher Paket-, CLI-, GUI- und Cluster-Versionskennung.

- Optionale Clusterinstallation: Knoten bewusst auswählen, Vorprüfung lesen und Installation bestätigen. Keine automatische Verteilung oder Konfigurationssynchronisierung.
- Vorhandene Cluster-Mitgliedsadressen und Root-SSH-Vertrauensbeziehungen; Clusterzustand vor SSH-Abfrage laden, kein DNS-Fallback bei fehlendem Mitglied. IPv4/IPv6 im Code unterstützt; keine Fabric erforderlich.
- Vollständige ZIP-/Dateiprüfung vor enthaltenem Paketcode. Bestehende Einstellungen, Zeitpläne und Snapshot-/Replikations-/Löschschutzregeln bleiben erhalten. Kein allgemeines System-/Proxmox-Upgrade. Automatische Notfallbereinigung standardmäßig AUS.

**Installation:** die vollständige `BuMaVory-ZFS-Manager-1.1.zip` und `bootstrap-1.1.sh` verwenden. Eine reine DEB-Installation registriert keine Cluster-Verteilungskopie. [Anleitung DE/EN](https://github.com/mbuse79/zfs-manager-pve/blob/v1.1/docs/INSTALL-1.1.md). Der zusätzlich gelieferte `quick-install-1.1.sh` enthält feste ZIP-/Bootstrap-Prüfsummen; der Schnellinstaller auf `main` wird auf diese Lieferung aktualisiert. In Quellarchiven die versionierte Anleitung verwenden.

**Nachweise:** 307 unterschiedliche automatisierte Tests und DE-/EN-Browsertests mit echtem ExtJS 7 und API-Fixtures. Alle 43 Laufzeitdateien entsprechen Fix2 nach Normalisierung ausschließlich der Versions-/GUI-Texte in fünf Dateien. Der Betreiber bestätigte die Fix2-Clusterinstallation auf PVE 9.2.26 und 9.2.21. Das exakte 1.1-DEB wurde neu gebaut und automatisch geprüft; kein neuer unabhängiger Hosttest wird behauptet. Reale Offline-Rettung, Abbruch während dpkg und parallele reale Steuerknoten bleiben ungeprüft. Einzelheiten in `RELEASE-QA.md` und `qa/V1.1-VALIDATION.json`.

DEB SHA256: `02aced7abd67ac6d4e675eedf5758004e67f7e9435cb32b06790cb0b0983a4f5`

ZIP SHA256: `fcdde5fba9bbcf29ca2a5463a586de65689a014f1f9e47bd81040720957873ed`

Bootstrap SHA256: `45c447c682b0ed325e5a9c0aae84c13b1af6b1422b54ce28b8df956bd0e62403`

Vollständige ZIP mit DEB, Quellstand/Builddateien, Installern, zusätzlichen Abhängigkeiten samt Lizenzen/korrespondierenden Quellen und innerem Manifest. `SHA256SUMS` prüft die einzelnen Release-Dateien. Ältere Releases und ihre Assets bleiben unverändert.

---

Version 1.1 publishes the operator-confirmed Fix2 functionality with consistent release identification. Optional confirmed cluster rollout uses the complete verified local bundle and existing Proxmox SSH trust. Use the full ZIP and versioned installation guide. The exact 1.1 package was rebuilt and automatically tested; the prior operator host evidence applies to Fix2. Project contributions are AGPL-3.0-only; third-party rights and corresponding sources remain separately scoped. See the source archive and license notices.
