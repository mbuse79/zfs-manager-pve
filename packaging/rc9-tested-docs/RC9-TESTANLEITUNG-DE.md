# RC9 – Oberfläche nach freigegebenem Entwurf

Version: 1.0.0-34~rc9. Grundlage: RC8 einschließlich Installerfix1.
Die RC8-Neuinstallation auf PVE 9.1.1 und das RC7→RC8-Upgrade auf pve4/PVE 9.2.26
wurden im Chat durch Hostausgaben belegt. Diese Nachweise sind keine RC9-Praxistests.

## Neue Oberfläche

- Eine Pooltabelle mit getrennten CAP-/FRAG-Werten und CAP-Balken.
- Datenträger, Topologie und Scrub beim Start eingeklappt; Details-Schaltfläche.
- Genau zwei Snapshot-Tabs; Gast-/Snapshotfilter verändert nur die Anzeige.
- Bestehende Einzel-, Gruppen-, Bereichs- und exakte Aktionen bleiben verfügbar.
- Snapshot-Verbrauch und Dienste/Replikation einklappbar.
- Eine Aufbewahrungstabelle: Vorgabe je Dataset, beobachtete Gesamtsumme, Quelle.
- Änderung prüfen öffnet weiterhin die vorhandene Bestätigung vor dem Speichern.
- Erweiterte Bereinigungssteuerung in einem eigenen eingeklappten Bereich unter
  Dienste/Replikation. Die Warnung bei einem echten Poolalarm bleibt oben sichtbar.
- Automatische Bereinigung bleibt bei Neuinstallation AUS; bestehende Aktivierungen
  werden nicht zurückgesetzt. Keine Zeitpläne, Secrets oder Gastschutzregeln geändert.

Die native ExtJS-Umsetzung folgt dem Entwurf. Zeilenaktionen behalten die vorhandenen
funktionierenden Erstellen-/Lösch-/Rollback-Workflows; es wird kein neuer generischer
Vorschau-Endpunkt erfunden. Erstellen und Vorschau sind entsprechend beschriftet.

## Installation und Upgrade

Auf dem Fedora-PC nur eine SSH-Verbindung zum jeweiligen PVE-Host öffnen.
Alle folgenden Installationsbefehle gehören in die Root-Shell des PVE-Hosts.
Zuerst die Test-PVE aktualisieren, dann pve4. Vorher unabhängige Sicherungen und
Zugang über eine separate Konsole bereithalten.

ZIP und Bootstrap anhand der separat bereitgestellten RC9-DELIVERY-SHA256SUMS
prüfen. Die dort enthaltene ZIP-Prüfsumme im Bootstrap-Aufruf einsetzen:

```bash
bash bootstrap-rc9.sh 'HTTPS-DOWNLOADLINK-ZUR-RC9-ZIP' 'ZIP-SHA256' --check-only --lang de
```

Erst nach erfolgreichem Prüfmodus denselben Aufruf ohne --check-only ausführen:

```bash
bash bootstrap-rc9.sh 'HTTPS-DOWNLOADLINK-ZUR-RC9-ZIP' 'ZIP-SHA256' --lang de
```

Der bereits geprüfte generische bootstrap-rc8.sh kann ebenfalls die neue RC9-ZIP
prüfen und starten; dafür unbedingt deren neue Prüfsumme verwenden. Der lokale Weg
nach vertrauenswürdig geprüfter Entpackung lautet bash install-local.sh --check-only
und anschließend bash install-local.sh --lang de.

PVE 9.x ohne Minor-/Patch-Rückfrage; reale Strukturfehler bleiben Abbruchgründe.
APT simuliert ausschließlich den Manager und erforderliche mitgelieferte fehlende
Abhängigkeiten. Keine zusätzlichen Installationen, Konfigurationen oder Entfernungen.
Tatsächlich installiert dpkg nur die geprüften lokalen DEBs. Keine allgemeinen
Upgrades, keine automatische Fehlerreparatur. Bereits gleiche/neue Manager-Versionen
werden nicht neu installiert oder herabgestuft.

AutoSnap und unzip werden bei Bedarf aus den mitgelieferten Debian-13/Trixie-DEBs
installiert. Die Binärabhängigkeit unzip ist amd64. Python, Perl, cron, ZFS und PVE
gehören zur Hostbasis; fehlen weitere Komponenten, stoppt der Installer. Es wird
kein alternativer Scheduler-Adapter behauptet: nicht unterstützte konkurrierende
Programme und unklare manuelle Regeln benötigen weiterhin eine Konfliktklärung.

## Kurzer Test auf beiden Hosts

```bash
dpkg-query -W pve-zfs-manager zfs-auto-snapshot
zfsm version --lang de
zfsm check --lang de
zfsm services --lang de
zfsm emergency status --lang de
dpkg --audit
```

Auf Fedora direkt die Webadresse des jeweils aktualisierten Hosts öffnen, nicht
nur einen anderen Knoten in der Clusteroberfläche auswählen. Strg+Umschalt+R,
dann ZFS Manager öffnen. Angezeigt werden muss RC9-Testversion.

1. DE/EN prüfen: Poolübersicht, CAP/FRAG, beide Tabs und eine Aufbewahrungstabelle.
2. Details öffnen, Gast öffnen, Filter setzen/löschen und Aktualisieren drücken.
   Aufklappzustände und Auswahl sollen erhalten bleiben. Ausgeblendete ausgewählte
   Snapshots bleiben ausgewählt; vor Aktionen immer die vollständige Vorschau prüfen.
3. Änderung prüfen nur bei bewusst geänderter Vorgabe testen und in der Bestätigung
   abbrechen. Auf pve4 keine produktive Aufbewahrung reduzieren und keine Snapshot-
   Löschungen/Rollbacks zur reinen GUI-Prüfung ausführen.
4. Neuinstallation bzw. Upgrade, erhaltene Einstellungen und Darstellung bestätigen.

## Rückbau und Veröffentlichung

GUI/API-Änderungen werden vor dem Upgrade unter /var/lib/pve-zfs-manager/backups
transaktional gesichert. Kein blindes Kopieren alter PVE-Dateien und kein automatischer
Paket-Downgrade. zfsm restore ist weiterhin keine ausführende Restore-Funktion.
Bei Fehlern Ausgabe/Backup sichern und den Rückbau gezielt prüfen.

Veröffentlichung ist vom Nutzer nach bestätigten erfolgreichen RC9-Praxistests
auf Test-PVE und pve4 beauftragt. Bis zu dieser Bestätigung keine Veröffentlichung.
Der später veröffentlichte Stand muss dem tatsächlich getesteten DEB entsprechen.
