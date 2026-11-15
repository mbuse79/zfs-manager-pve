# BuMaVory ZFS Manager 1.0.0-34~rc8 – Testanleitung

Rekonstruktion aus dem geprüften RC7-Testpaket. Kein öffentlicher Release.
PVE4 bezeichnet den Hostnamen pve4 mit PVE 9, nicht Proxmox VE 4.
Vor Veröffentlichung müssen der Betreiber erfolgreiche Tests auf pve4 und einer
frischen PVE 9 bestätigen. Es wurden hier keine Proxmox-Hosts verändert.

## Umfang und Grenzen

Alle PVE-9.x-Versionen werden ohne Rückfrage zur Minor-/Patch-Version geprüft.
Unbekannte GUI/API-Strukturen stoppen weiterhin sicher. PVE 8/10 sind gesperrt.
Mitgelieferte Binärabhängigkeiten: Debian 13/Trixie, amd64; AutoSnap ist all.
Python 3, Bash, Perl, APT/dpkg, cron und ZFS/PVE gehören zur frischen PVE-9-Basis.
Fehlen weitere Basisabhängigkeiten, stoppt die Simulation vor jeder Installation;
keine unbeabsichtigte automatische Nachrüstung oder Aktualisierung.

Unterstützter Scheduler ist zfs-auto-snapshot. Vorhandenes paketiertes AutoSnap
wird übernommen, einschließlich deaktivierter Regeln und individueller Zeitpläne.
Sanoid, zrepl, zfs-autobackup, pyznap, znapzend und Snapper haben keinen Adapter.
Bei Erkennung wird verständlich abgebrochen; keine Unterstützung wird behauptet.
Manuelle AutoSnap-Installationen ohne DEB und unbekannte Bereinigungsregeln werden
nicht überschrieben. Sie benötigen eine manuelle Prüfung. Die Erkennung ist
konservativ und kann keine beliebig benannten privaten Scheduler ausschließen.
Replikationsverwaltung bleibt ein separates Projekt.

## Vertrauen und Integrität

ZIP-SHA256 und SHA256 des separat bereitgestellten Bootstrap-Skripts anhand der
mitgelieferten äußeren Prüfsummendatei bzw. eines vertrauenswürdigen Übertragungswegs
prüfen. Ein Manifest aus demselben Download ist kein unabhängiger Herkunftsnachweis.
Nicht ungeprüft Skripte ausführen. Keine Pipes wie curl | bash.
Der Bootstrap prüft erst die ZIP, entpackt mit Python (unzip ist nicht erforderlich),
verweigert Traversal, Links, doppelte ZIP-Namen und Größenüberschreitungen und prüft
alle Dateien gegen SHA256SUMS. Der lokale Installer prüft erneut eine private Kopie
vor Ausführung des Treibers, Prechecks oder Paketcodes. Source-Archive enthalten
zusätzlich SOURCE-SHA256SUMS.

## Prüfmodus ohne Installation

Die ZIP auf dem jeweiligen Host als root mit Python entpacken. Beispiel im
Verzeichnis mit heruntergeladener ZIP und der separat geprüften SHA256-Datei:

```bash
sha256sum -c RC8-DELIVERY-SHA256SUMS
python3 -m zipfile -e BuMaVory-ZFS-Manager-1.0.0-34-rc8-Testpaket.zip rc8-test
bash rc8-test/install-local.sh --check-only --lang de
```

Der manuelle Python-Entpackbefehl setzt voraus, dass die vertrauenswürdige äußere
ZIP-Prüfsumme erfolgreich war. Für ungeprüfte Archive ausschließlich den gehärteten
Bootstrap benutzen. Prüfmodus liest Hostdaten und simuliert APT, installiert nichts.
Temporäre Dateien entstehen unter /tmp und werden entfernt.

Alternativ ohne bereits installiertes unzip, mit separat geprüftem Bootstrap:

```bash
bash bootstrap-rc8.sh 'https://DEINE-FREIGABE/download' '64-STELLIGE-ZIP-SHA256' --check-only --lang de
```

Die Platzhalter durch den eigenen Downloadlink und die tatsächliche ZIP-Prüfsumme
ersetzen. Der Bootstrap lädt ausschließlich HTTPS. Er ist kein Online-Updater.

## RC7-Upgrade auf pve4

Vorher unabhängige Sicherungen und Zugang über eine separate Konsole bereithalten.
RC7-DEB und bisherige Konfiguration sichern. Zunächst den Prüfmodus ausführen.
Auf pve4 mit vorhandenem AutoSnap wird dieses nicht erneut installiert.
Nach erfolgreicher Prüfung die Installation bewusst als Betreiber starten:

```bash
bash rc8-test/install-local.sh --lang de
dpkg-query -W pve-zfs-manager zfs-auto-snapshot
zfsm version --lang de
zfsm check --lang de
zfsm services --lang de
zfsm emergency status
```

Es wird kein allgemeines APT-Upgrade und keine automatische Fehlerreparatur
angestoßen. APT muss exakt die erwarteten fehlenden lokalen Abhängigkeiten und den
Manager planen; andere Aktionen führen zum Abbruch. Die tatsächliche Installation
erfolgt nur mit dpkg aus den geprüften lokalen DEBs. Bei Paketfehlern Ausgabe sichern;
kein apt -f install, kein --force und kein erneuter Versuch ohne Diagnose.

Gleiche/neue Manager-Version: keine Neuinstallation/kein Downgrade. Paketmanager-
Sperren nicht umgehen. Paketinstallation ist nicht atomar; bei einem späteren
Konfigurationsfehler können Abhängigkeiten bereits installiert sein.

## Frische PVE 9

Gleicher Prüf- und Installationsweg. Fehlen unzip oder AutoSnap, werden die
mitgelieferten DEBs nach Simulation installiert. AutoSnap liefert seine normalen
Cron-Regeln; der Manager erzeugt keinen zweiten Scheduler. Ein vorhandener
individueller yearly-Zeitplan verhindert eine weitere yearly-Regel.
Fehlende ZFS-Pools werden als leer dargestellt; echte Abfragefehler bleiben Fehler.

## Kurzer Praxistest auf beiden Hosts

1. CLI mit --lang de und --lang en prüfen: help, version, check, services, capacity,
   inventory, emergency status. --lang steht beim Hauptbefehl vor oder nach dem
   Unterbefehl; JSON mit capacity --json und emergency status --json separat prüfen.
2. Proxmox-GUI in Deutsch und Englisch öffnen. Beide Snapshot-Tabs, Pool/CAP/FRAG,
   eine Kapazitätstabelle und die zusammengeführte Aufbewahrung prüfen. Auswahl,
   Aufklappzustand und Scrollposition nach manuellem Refresh kontrollieren.
3. Auf pve4 nur lesend prüfen, keine produktiven Snapshots löschen/zurücksetzen.
   Auf frischer, entbehrlicher PVE Testdaten für Erstellen und Vorschauen nutzen.
   Löschen/Rollback nur mit eigenem ausdrücklich freigegebenem Testplan und Backup.
4. Vorher/nachher eigene Zeitpläne und Einstellungen vergleichen. Automatisches
   Löschen bleibt auf einer Neuinstallation AUS. Eine vorher ausdrücklich aktive
   Einstellung bleibt erhalten. Keine AutoSnap-Aufbewahrung zur Prüfung reduzieren.
5. Host, PVE-/Paketversion, ZIP-SHA256, Ergebnisse und Fehlermeldungen zurückmelden.

## Rückbau

Integrationsänderungen werden vom Installer transaktional unter
/var/lib/pve-zfs-manager/backups gesichert; individuelle Policies/Secrets bleiben.
Bei Fehlern erst Logs/Backup sichern. zfsm restore ist weiterhin keine automatische
Wiederherstellung. Kein blindes Kopieren alter Proxmox-Dateien. Ein Paket-Downgrade
auf das gesicherte RC7-DEB und die Rücknahme der GUI müssen gesondert geprüft werden;
der RC8-Installer führt kein Downgrade aus. Kein vollautomatischer RC8→RC7-Rollback
wird behauptet. Rescue-/Root-Rollback ist nicht Teil dieses Testplans.

## Sprache und bekannte Grenzen

DE/EN-Projekttexte und CLI-Sprachwahl wurden mit Fixtures geprüft. JSON-Schemata,
Systemausgaben, Namen, ZFS-Scrubtexte und fremde Fehlermeldungen bleiben unverändert.
Die persönlichen Proxmox-Webspracheinstellungen werden von der lokalen CLI nicht
abgefragt. Englische Sicherheitsabfragen erläutern weiterhin dieselben erforderlichen
Bestätigungstokens JA und LOESCHEN; Schutzschritte werden nicht verkürzt.
Der Chromium-Test nutzt ExtJS-Mocks: keine Behauptung einer vollständigen echten
Proxmox-Browserprüfung. Offline-Rescue ist weiterhin nur mockbasiert geprüft.
