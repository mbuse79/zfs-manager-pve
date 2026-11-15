## 1.0.0-34 RC10 – Cluster-Testversion (15.11.2026)

- Native Clusterübersicht mit ausdrücklicher Knotenauswahl, temporärer Vorprüfung,
  einmaliger Bestätigung und Proxmox-Hintergrundauftrag; zusätzlich `zfsm cluster`.
- Root-only, bestehende Proxmox-SSH-Vertrauensbeziehung, Quorum, Versions-/Identitäts-
  und Prüfsummenprüfung; Verteilung des geprüften RC10 aus einer rootgeschützten lokalen Paketkopie.
- Keine automatische Verteilung, Konfigurationssynchronisierung oder Downgrades;
  Teilfehler stoppen die Verteilung und bleiben je Knoten sichtbar.
- Testpaket mit vollständiger ZIP und DEB; kein öffentlicher Release oder realer Clustertest.
- Details und Testplan: `docs/CLUSTER-INSTALL.md`.

## Veröffentlichung RC9 (15.11.2026)

- Betreiber bestätigt erfolgreiche angeforderte Praxistests und beauftragt die Veröffentlichung.
- Paketversion und getestetes DEB bleiben unverändert; öffentliche Dokumentation und bereinigte Lieferarchive ergänzt.
- Kontrollbuild: alle 77 Payload-/Kontrolldateien und Dateirechte stimmen überein.

## 1.0.0-34 RC9 – kompakte Oberfläche nach Entwurf (13.11.2026)

- Native Poolübersicht mit CAP-Balken, getrennt von FRAG.
- Einklappbare technische Details, Snapshot-Auswertung und Dienste.
- Gastfilter; genau zwei Snapshot-Tabs, Auswahl und Aufklappzustand erhalten.
- Gemeinsame Aufbewahrungsansicht mit beobachteter Gesamtsumme; Änderung prüfen.
- Explizite Owner-Selektoren für verschachtelte Bedienelemente; DE/EN geprüft.
- Snapshot-API und Schutzmodule unverändert zu RC8; Installerfix1 übernommen.
- Neuer Testkandidat; Freigabe nach erneuten Praxistests auf beiden Hosts.

## 1.0.0-34 RC8 – Rekonstruktion aus RC7 (13.11.2026)

- PVE-9-Hauptversionsgrenze ohne Minor-/Patch-Rückfrage; Strukturprüfungen bleiben aktiv.
- Vollständige Manifestprüfung vor enthaltenem Installationscode; privater Arbeitsstand.
- Python-ZIP-Einstieg ohne unzip; geprüfte lokale Abhängigkeiten, exakte APT-Simulation.
- Kein System-/Proxmox-Upgrade; kein Downgrade des Managers. Alternative Snapshot-Backends werden ohne Adapter als Konflikt gemeldet.
- Doppelte Kapazitätsanzeige entfernt; Aufbewahrung, beobachtete Anzahl und Cron-Quelle zusammengeführt.
- DE/EN-Wörterbuch bereinigt, CLI-Sprachweitergabe ergänzt. JSON bleibt unverändert.
- Leere erfolgreiche Pool-Abfrage zulässig; echte Abfragefehler bleiben Fehler.
- Snapshot-API, Gastschutz und automatische Löschvorgaben unverändert.
- RC7-Changelog-Eintrag wird im DEB mitgeliefert; er fehlte im ursprünglichen RC7-DEB.
- Testkandidat, keine Veröffentlichung und keine bestätigten PVE-Praxistests.

## 1.0.0-34 RC7 (11.11.2026) – AutoSnap-Konfliktauswahl und unzip-Bootstrap

- AutoSnap-Doppelerkennung korrigiert: Paket-Sicherheitsprüfungen (`which`/`command -v`) zählen nicht als eigene Zeitplan-Aufträge.
- Bei echten Konflikten: bestehende Cron-Zeitpläne zur Auswahl anbieten, übrige Regeln nur nach Bestätigung deaktivieren und vollständig sichern.
- `zfsm autosnap backups` und `zfsm autosnap restore SICHERUNGS-ID` für nachvollziehbare Wiederherstellung.
- Fehlendes `unzip` bei ZIP-Installationen vor dem Entpacken kontrolliert über APT nachinstallieren (vorher Simulation, keine Upgrades/Entfernungen).
- Replikation bleibt ein separates Projekt und wird vom ZFS Manager nicht verwaltet.

## 1.0.0-34 RC6 (11.11.2026) – Hostinventur und vorhandene Dienste übernehmen

- Vor jeder Installationsänderung lesende Erkennung von AutoSnap, systemd-/Cron-Aufträgen, CheckZFS, manuellem zsync und nativer Proxmox-Replikation.
- Neue CLI `zfsm inventory` beziehungsweise `zfsm inventory --json` und kompakte Hostprüfungsanzeige im Proxmox-ZFS-Manager.
- Keine zweite Snapshot-Bereinigung anlegen; bestehende AutoSnap-Zeitpläne erhalten und bei doppelten Arten sicher stoppen.
- Manuell installierte Replikation trotz `rc`-Paketstatus erkennen, **ohne** Replikation zu verwalten oder ihre Konfiguration zu verändern.
- Schutzlogik, Notfalllöschung und bestehende Poolwarnungen bleiben unverändert; automatische Notfallbereinigung bleibt AUS.

## 1.0.0-34 RC5 (11.11.2026) – AutoSnap als Pflichtkomponente mit sicherem Installer

- Vorhandenes `zfs-auto-snapshot` wird erkannt und übernommen, ohne Cron-Einstellungen zu überschreiben.
- Fehlt AutoSnap, installiert der ZIP-Installer automatisch nur dieses Paket aus vorhandenen APT-Quellen (inklusive Simulation; ohne allgemeines Upgrade/Entfernen).
- Vor Installation werden Debian-Metadaten, Proxmox-9.x-Kompatibilität, SHA256-Manifest und AutoSnap-Cron-Regeln geprüft.
- `checkzfs`, zsync und andere Werkzeuge bleiben optional. Keine neuen Bereinigungsdienste.
- ZFS-Manager-Snapshotlöschung und Notfall-Backend unverändert; automatische Notfallbereinigung standardmäßig AUS.

## 1.0.0-34 RC4 (11.11.2026) – Poolalarme statt Gast-Quota-Fehlalarme

- Nur noch physische ZFS-Pool-Auslastung (`zpool list`: `ALLOC/SIZE`) löst die 80/90/95-%-Speicherwarnungen aus.
- `quota`, `refquota` und `AVAIL` einzelner LXC-/VM-Datasets (einschließlich Replikationskopien) erzeugen **keine** ZFS-Manager-Alarme und keine Proxmox-Push-Nachrichten mehr.
- Veraltete Dataset-Warnzustände aus RC2/RC3 werden beim nächsten Timerlauf ohne künstliche Entwarnungs-Push-Nachrichten verworfen.
- Ohne ZFS-Pool-Alarm gibt es keinen roten Hinweis auf fehlende Proxmox-Benachrichtigungsziele; bei echter Pool-Warnung wird auf fehlende Zustellung hingewiesen.
- Unveränderte Notfall-Vorschau, Snapshot-Schutz und automatische Bereinigung weiterhin standardmäßig AUS.

## 1.0.0-34 RC3 (11.11.2026) – Oberflächenkorrektur

- Laufwerksliste wächst bis maximal 540 px passend zur Datenträgeranzahl; bei vielen Laufwerken interne Scrollleiste.
- ZFS-Pools beim erstmaligen Öffnen geschlossen; Mirror-/RAIDZ-Zweige beim Öffnen eines Pools standardmäßig offen.
- Manuellen Aufklappzustand der Pools über automatische Aktualisierungen erhalten.
- Pooltopologie passt ihre Höhe an sichtbare Zeilen an, bis maximal 540 px.
- Keine Änderungen an ZFS-Löschregeln, Replikationsschutz oder aktiver Bereinigung.

## 1.0.0-34 RC2 (11.11.2026, Testversion – nicht auf GitHub freigegeben)

- Benachrichtigungen bei kritischer Pool- oder Dataset-Auslastung über das bereits konfigurierte Proxmox-VE-Benachrichtigungssystem (PVE::Notify); Empfangstest mit `zfsm emergency notify-test`.
- ZFS-Quota/Refquota und effektiv verfügbaren Dataset-Speicher getrennt überwachen.
- Wiederholungsalarme, Entwarnungen und erneuter Versand nach Fehlern; keine ungefragte Einrichtung von E-Mail-/Gotify-/Webhook-Zielen.
- Rote Warnung auch für kritische Dataset-Limits; fehlende Benachrichtigungsziele sichtbar.
- Standardmäßig weiterhin keinerlei automatische Snapshot-Löschung; bestehende RC1-Schutzregeln unverändert.
- 173 bestandene Offline-Tests, darunter RC1-zu-RC2-Upgrade und Perl-Aufruf gegen einen isolierten Teststub.

## 1.0.0-34~rc1 – Geschützte Snapshot-Notfallbereinigung (Testversion, 2026-11-10)
- 80/90/95-%-Poolwarnungen, roter Admin-Alarm in der ZFS-Manager-GUI, CLI-Status und systemd-Journalüberwachung.
- Maximal 15 älteste automatisch benannte Snapshots je Durchlauf; letzten Snapshot jeder Art auf jedem Dataset unabhängig vom Alter schützen.
- Geschützte Replikationspfade, manuelle Snapshots, Holds, Klone und ungeklärte Gastzuordnungen ausschließen.
- Notfall-Vorschau und zweimal bestätigtes Löschen per GUI und CLI; opt-in automatische Bereinigung, standardmäßig AUS.
- CLI-Rescue-Vorschau für offline importierte ZFS-Pools ohne laufende PVE-Dienste.
- Externe Push-Benachrichtigungen (Gotify/ntfy/PVE Notifications) sind noch nicht in RC1 eingebaut.

## 1.0.0-33~rc1 (unreleased test candidate, 2026-11-10)

- Read-only dynamic Proxmox system/storage-pool and ZFS mirror/RAID topology.
- Pool members identified from imported `zpool status -P` devices; no disk is labeled free.
- Single bulk Proxmox guest-state inventory for UI; signed destructive checks still use fresh per-guest status.
- Added regression fixtures and isolated upgrade test from published 1.0.0-32 source.
- Not yet validated on a live Proxmox host. Do not deploy to production before a test-host check.

# Changelog

## 1.0.0-32+docs2 — Private documentation-only package candidate (2026-11-09)

- No changes to the 1.0.0-32 runtime functionality, installed API/GUI scripts, systemd units or Debian maintainer scripts.
- Synchronizes licensing/provenance documents with reviewed repository notes and acknowledges the 2026-11-07 final-version host test.
- Removes a superseded 2026-11-03 PDF from the *binary* package; the old source-tree PDF is retained only as historical material.
- Includes a separate packaging revision because the DEB payload differs from both `1.0.0-32` and the private `+docs1` QA draft.
- Exact `1.0.0-32+docs2` DEB installed as an APT upgrade on `pve-test` / Proxmox VE 9.2.25 on 2026-11-09; CLI and web UI confirmed by the maintainer. The public-release decision and remaining rights assessment are separate.


## 1.0.0-32 — Technical final build (public release pending)

- Final Debian version number derived from the tested `1.0.0-32~rc1`.
- Distribution documentation and source layout prepared for publication.
- Obsolete hardcoded private browser IP removed from a legacy helper.
- No changes to snapshot API or core GUI business logic relative to RC1.
- Final package was installed and checked on `pve-test` / Proxmox VE 9.2.25 on 2026-11-07 (maintainer-reported CLI/GUI pass).

## 1.0.0-32~rc1 — Release candidate

- Local `.deb` package installation tested on Proxmox VE 9.2.25.
- CLI/status/integration checks completed on the test system.
- Corrected English/German singular/plural guest count text.

## Selected earlier changes

- **1.0.0-31:** full-row snapshot selection highlight; survived a Proxmox VE update to 9.2.25.
- **1.0.0-30:** read-only capacity and retention audit, including `zfsm capacity --json`.
- **1.0.0-27:** improved grouped checkbox selection, batch deletion and compact confirmations.
- **1.0.0-23:** exact single-snapshot deletion without deleting newer snapshots.

Detailed historical changelogs are available in the original source archive, but should be reviewed before bulk publication.
