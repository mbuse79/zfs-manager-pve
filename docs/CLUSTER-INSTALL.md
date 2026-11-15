# Optionale Clusterinstallation / Optional cluster installation

**Unveröffentlichter Entwicklungsstand auf Basis von RC9.** Der veröffentlichte
RC9-Release enthält diese Funktion noch nicht. Kein neuer Versionsname und kein
Installationspaket werden mit dieser Änderung freigegeben.

## Deutsch

ZFS Manager erhält eine Schaltfläche **Clusterinstallation** in der vorhandenen
Proxmox-Oberfläche. Der Steuerknoten ist der Knoten, über den die Weboberfläche
geöffnet wurde (`Proxmox.NodeName`), auch wenn links ein anderer Knoten ausgewählt
ist. Die Funktion benötigt zunächst einen entsprechend aktualisierten Steuerknoten.

1. Als `root@pam` öffnen und Zielknoten ausdrücklich auswählen. Keine Vorauswahl;
   die Checkbox im Tabellenkopf kann alle verfügbaren Knoten auswählen. Offline-
   Knoten bleiben gesperrt.
2. **Ausgewählte Knoten prüfen** lädt das fest gepinnte öffentliche Paket einmal
   auf den Steuerknoten. Es wird zur Vorprüfung vorübergehend auf die ausgewählten
   Knoten übertragen, vollständig geprüft und anschließend wieder entfernt.
   Dieser Schritt installiert keine Pakete und verändert keine Zeitpläne.
3. Die Vorschau zeigt Version, Paketstatus und Installerergebnis je Knoten.
   Gleiche oder neuere vollständig installierte Versionen werden nach einer
   Integrationsprüfung als unverändert ausgewiesen. Eine defekte Integration wird
   gemeldet, nicht automatisch repariert oder durch eine ältere Version ersetzt.
4. Häkchen setzen und **Auf ausgewählten Knoten installieren** bestätigen. Eine
   Vorschau gilt fünf Minuten und ist einmal verwendbar. Alle ausgewählten Knoten
   werden vor der ersten Installation erneut geprüft. Installation nacheinander,
   Steuerknoten zuletzt, sofern überhaupt eine Installation auf ihm nötig ist.
5. Ergebnis und Proxmox-Aufgabenprotokoll prüfen. Beim ersten Installationsfehler
   stoppt die Verteilung. Bereits installierte Knoten bleiben installiert;
   weitere Knoten stehen auf „Nicht gestartet“. Bei Verbindungsabbruch kann das
   Ergebnis eines Knotens unbekannt sein. Vor einem neuen Versuch dort den
   Paket-/Integrationsstatus prüfen. Das Schließen des Dialogs stoppt keine Aufgabe.

Der erste Entwicklungsschritt verteilt bewusst den **veröffentlichten RC9**:

- Version: `1.0.0-34~rc9`
- ZIP-SHA256: `7b2ba31290b5e45913f7a715075b1b844e4d57f151f8effd39fcb5e747768e5e`
- DEB-SHA256: `f48f7cfef9aacd070a3185c896b49b85149c90fe4b4595a15929bd2dee6a776f`

Das ist keine automatische Verteilung beliebiger Dateien vom Steuerknoten.
Eine spätere Zielversion muss ausdrücklich mit Herkunft und Prüfsummen registriert
werden. Die Clusterfunktion selbst ist derzeit nur im Entwicklungsquellstand des
Steuerknotens vorhanden; sie wird durch das Verteilen des bestehenden RC9-Pakets
nicht auf die Zielknoten nachgerüstet.

Die vorhandene Proxmox-SSH-Anbindung (`PVE::SSHInfo`) bestimmt Zieladresse,
HostKeyAlias und gegebenenfalls die knotenspezifische `ssh_known_hosts`-Datei.
Hostschlüsselprüfung bleibt strikt; unbekannte Schlüssel oder fehlende Root-SSH-
Anmeldung müssen vorab durch den Administrator geklärt werden. Es werden keine
Schlüssel, Passwörter oder SSH-Freigaben erzeugt. API-Tokens und lediglich lokal
freigegebene Snapshot-Administratoren dürfen keine Clusterinstallation starten.

CLI nach Installation eines zukünftigen geprüften Pakets mit dieser Funktion:

```bash
zfsm cluster status --lang de
zfsm cluster preview --nodes node-a,node-b --lang de
zfsm cluster install --plan VORSCHAU_ID --lang de
```

`node-a,node-b` durch bewusst ausgewählte Clusterknoten ersetzen. Die Vorschau gibt
ihre 32-stellige Kennung als `job` aus. `install` verlangt eine interaktive
Bestätigung; ohne Konsole erfolgt keine Installation. Die GUI nutzt denselben
Verteilungskern in einem Proxmox-Hintergrundauftrag.

Bestehende Konfigurationen, individuelle Zeitpläne und Sicherheitsabfragen bleiben
auf jedem Knoten lokal. Keine Konfigurationssynchronisierung, kein Beitrittsdienst,
kein Zeitgeber für automatische Nachinstallation und keine Paketentfernung.
Quorum und übereinstimmende Clusterzugehörigkeit sind erforderlich. Nur PVE 9.x;
keine Minor-/Patch-Whitelist. Die gebündelten Zusatzabhängigkeiten setzen aktuell
amd64 voraus. Die vorhandenen Struktur-, Snapshot-Programm-, APT- und Prüfsummen-
Prüfungen des verifizierten Installers gelten weiterhin. Kein allgemeines Upgrade,
keine automatische Paketreparatur und keine Aktivierung der Notfallbereinigung.

## Teststatus und notwendiger Praxistest

Automatisch geprüft: simulierte Clusterknoten, Auswahlgrenzen, Quorum, Hostidentität,
Paket-/Versionswechsel, Zeitablauf und Einmalnutzung, Vorprüfungsfehler, Teilfehler,
Verbindungsabbruch, SSH-Vertrauensoptionen, unsichere Archive und Eigentums-/Lock-
Prüfungen. Die bisherigen Snapshot-Handler bleiben außerhalb des separat markierten
Clusterblocks bytegleich. Reale ExtJS-7-Browsertests in DE/EN prüfen Auswahl,
Offline-Sperre, Steuerknoten-Routing, Vorschau, Bestätigung und HTML-Escaping.

**Noch nicht durchgeführt:** echte Cluster-SSH-Verbindung, Installation über diese
Funktion auf realen PVE-Knoten, realer Verbindungsabbruch während `dpkg` und
Mehrfachstart von verschiedenen realen Steuerknoten. Bisherige RC9-Hosttests sind
kein Nachweis für diese neue Funktion. Keine Produktionshosts wurden angesprochen.

Vor einer neuen Testpaketfreigabe auf einem entbehrlichen PVE-9-Testcluster prüfen:

- Neuinstallation und Upgrade eines älteren Managers, bestehende Zeitpläne und
  Konfigurationen vor/nach dem Test vergleichen; automatische Notfallbereinigung
  bleibt ohne vorherige ausdrückliche Aktivierung AUS.
- Gleiche/neue Version unverändert, Offline-Knoten, fehlendes Quorum, unbekannter
  SSH-Hostschlüssel und nicht unterstützter Snapshot-Scheduler verständlich gesperrt.
- Vom Steuerknoten aus einen anderen Knoten auswählen und den Clusterdialog öffnen;
  Aufträge müssen weiterhin auf dem Steuerknoten laufen.
- Fehler auf einem mittleren Testknoten: vorherige Ergebnisse erhalten, nachfolgende
  Knoten unberührt. Wiederholung ausschließlich nach Prüfung des unklaren Zustands.

## English

This is **unreleased source development**, not part of the published RC9 package.
The native **Cluster installation** dialog uses the web session's origin node as
coordinator even when another node is selected. Select targets explicitly, run the
preflight, review each result, tick the approval box and confirm installation.
Offline nodes cannot be selected. Temporary staging during preflight does not
install packages. Plans expire after five minutes and are single-use.

The initial target is the exact published RC9 artifact pinned above. This does not
copy arbitrary local files or distribute the new cluster controller itself. Same
or newer installations are checked and left unchanged. Newer target releases must
be explicitly registered with their trusted checksums. Existing per-node settings,
schedules and safety controls are retained; there is no configuration sync or
automatic installation on cluster join.

Only `root@pam` can use the API. The CLI requires local root. Existing Proxmox
cluster SSH configuration is used with strict host-key verification and batch mode;
no credentials or trust material are provisioned. Quorum and matching membership
are required. Every target is checked again before the first installation; the
coordinator is processed last. Rollout stops on failure and reports completed,
failed, uncertain and unstarted targets separately. Closing the window does not
cancel the background task. Inspect uncertain targets before retrying.

Automated tests use isolated fixtures and a real ExtJS 7 browser. Actual cluster SSH,
cross-node package installation, interrupted `dpkg` and multiple real coordinators
have **not** been tested. A disposable PVE-9 test cluster is required before a new
test package can be approved. Existing RC9 live-host results do not validate this
new feature. No hosts were accessed or modified during development.
