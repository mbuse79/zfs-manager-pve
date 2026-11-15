# RC8-Rekonstruktion aus RC7

Grundlage ist das hochgeladene RC7-Testpaket mit vollständigem Quellstand, nicht
der ältere GitHub-Release v1.0.0-32. Historische RC8-Prüfsummen wurden nicht genutzt.
GitHub-main wurde lesend als e7504c11e02efb9db7987d2e0e9559feee60b589 bestätigt.

## Änderungen

- `install-local.sh`: prüft eine private Kopie sämtlicher Paketdateien gegen das
  vollständige Manifest, bevor `install_driver.py` oder ein Precheck ausgeführt wird.
- `bootstrap-rc8.sh`: unabhängiger HTTPS-Einstieg mit ZIP-SHA256, sicherer
  Python-Entpackung, Manifestprüfung; keine Voraussetzung eines vorhandenen unzip.
- `install_driver.py`: PVE 9.x, --check-only, --lang de|en, gleiche/neue Versionen,
  Inventur und Konflikte, wiederholte Vorprüfung, ausschließlich lokale DEBs.
  Die Simulation verweigert zusätzliche Inst/Conf-Aktionen, Entfernen und unvollständige
  Pläne. Tatsächliche Ausführung mit dpkg; keine allgemeinen Upgrades/Downgrades.
- `build_deb.sh`: Version 1.0.0-34~rc8, PVE >=9.0 und <10. Keine Minor-Whitelist.
  RC7-Changelog wird jetzt im DEB mitgeliefert.
- `zfsm_backends.py`: konservative lesende Erkennung konkurrierender Scheduler.
  Keine Adapter für Sanoid/zrepl/etc.; Konflikt wird gemeldet, nicht automatisch gelöst.
- `universal.py`: zusätzliche Konfliktprüfung; vorhandener individueller yearly-Cron
  verhindert eine parallele yearly-Regel. Struktur-/Besitz-/Transaktionsschutz erhalten.
- `manager_patch.py`: eine Kapazitätstabelle; eine Aufbewahrungstabelle mit Vorgabe,
  beobachteter Anzahl und Cron-Quelle; keine beobachtete Null vor erfolgreicher Abfrage.
  DE/EN-Lücken und doppelte Wörterbuchschlüssel korrigiert, Inventurhinweise übersetzt.
- CLI: Sprachwahl zu Inventory, Emergency und AutoSnap weitergegeben. Bestätigungen
  verwenden weiterhin identische Tokens. Maschinenlesbare JSON-Ausgaben unverändert.
- `zfsm_emergency.py`: erfolgreiche leere Poolliste ist zulässig. Der Fehlerpfad bei
  fehlgeschlagener zpool-Abfrage bleibt erhalten; keine Änderung der Löschlogik.

## Unverändert gegenüber RC7

Alle Perl-Snapshot-API-Dateien, Gastschutzdateien und der Offline-Rescue-Helfer
bleiben bytegleich. Emergency-Auswahl, Dryruns, Holds/Clones/Bookmarks, Gast-/Root-
Schutz, HMAC- und Replikationsschutz wurden nicht abgeschwächt. Kein Default für
automatisches Löschen geändert. Bestehende explizite Aktivierungen bleiben erhalten.
API/Policy und Paket-Laufzeitdateien werden zusätzlich beim Build verglichen.

## Testabgrenzung

Neue RC8-Tests decken Integrität vor Code, ZIP-Fehler, exakte APT-Pläne, frische
Installation/RC7-Upgrade mit Prozess-Mocks, Versionsgrenzen, Sprachschlüssel und
Zeitplanerhalt ab. Historische RC7-Installer-Mocks bleiben als ausdrücklich
historische Fixtures erhalten; sie gelten nicht als RC8-End-to-End-Installation.
Chromium prüft den echten GUI-Block und die beiden Tabellenrenderer mit ExtJS-Mocks
und Beispieldaten auf Deutsch/Englisch. Echte PVE-Integration, Hardware und Rettungs-
Boot sind nicht durch diese Tests belegt. Details im QA-Bericht.

## Lieferung

DEB, Quellarchiv mit Builddateien/Tests, Installer/Bootstrap, Abhängigkeits-DEBs,
Lizenztexte, korrespondierende Debian-/Upstreamquellen, Paketmetadaten und Prüfsummen.
Die vorgesehenen PVE-Basisabhängigkeiten werden nicht gebündelt oder aktualisiert.
Testanleitung: RC8-TESTANLEITUNG-DE.md. Veröffentlichung bleibt bis zur bestätigten
Prüfung auf pve4 und einer frischen PVE 9 gesperrt.
