# RC9 – kompakte native Proxmox-Oberfläche

Aus dem freigegebenen Vorabbild rekonstruierte native ExtJS-Umsetzung auf RC8
inklusive Installerfix1. Eigener Testkandidat 1.0.0-34~rc9.

Aktive Änderungen: manager_patch.py (Anordnung, Fieldsets, CAP-Balken, Gastfilter,
Sprachkorrekturen, responsive Baumhöhe), Paket-/CLI-/Installerversionen und Dokumente.
Der ursprüngliche Snapshot-Workflow inklusive aller Bestätigungen bleibt erhalten.

Datenträger/Topologie/Scrub und Verbrauch sind einklappbar. Details, Filter, beide
Tabs und eine gemeinsame Aufbewahrung sind vorhanden. Gefährliche Bereinigungs-
steuerung bleibt verfügbar, liegt aber unter den erweiterten Dienstinformationen.
Echte kritische Poolwarnungen bleiben im oberen Bereich deutlich sichtbar.

Verschachtelte Komponenten verwenden explizite Owner-Selektoren. Dies verhindert,
dass Schaltflächen/Filter/Retention auf eine innere Tab-Seite statt das Plugin zeigen.
Der Gastfilter verbirgt keine Datenträger innerhalb einer Snapshotgruppe; alle
Schutz- und Vollständigkeitsprüfungen sowie der Batch-Auswahlzustand bleiben erhalten.
Die Darstellung 1 disks wurde zu 1 disk/1 Datenträger korrigiert. Beobachtet gesamt
bezeichnet ausdrücklich alle Datasets. Bestehende Cron-Quellen werden exakt gezeigt.

PVE-9.x-Unterstützung und Installerfix1 bleiben erhalten. Kein allgemeines APT-
Upgrade; keine neue Versions-Whitelist. API, Gastschutz, Offline-Rettung, Emergency-
Löschlogik, Inventur, Schedulererkennung und Löschvorgaben bleiben bytegleich zu RC8.

Keine Produktivinstallation durch den Agenten und keine Veröffentlichung im Build.
RC9 muss auf den beiden Betreiber-Testwegen erneut bestätigt werden.
