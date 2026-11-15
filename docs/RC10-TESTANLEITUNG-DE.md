# RC10-Testpaket – 1.0.0-34~rc10

Nicht öffentlich freigegebene Testversion mit optionaler Clusterinstallation.
Die bisherigen RC9-Tests bestätigen diese neue Clusterfunktion nicht. Zunächst
auf einer entbehrlichen PVE-9-Testumgebung prüfen. Keine Veröffentlichung vor
bestätigten neuen Praxistests.

## Installation auf dem Steuerknoten

Das vollständige ZIP und dessen separat gelieferte SHA256 verwenden. ZIP mit
Python oder unzip entpacken; der eigenständige `bootstrap-rc10.sh` benötigt kein
vorinstalliertes unzip. Er wird ebenfalls vor Ausführung separat geprüft.

In der Root-Shell des Test-PVE in das entpackte Paketverzeichnis wechseln:

```bash
bash install-local.sh --check-only --lang de
```

Erst nach erfolgreicher Vorprüfung installieren:

```bash
bash install-local.sh --lang de
zfsm version --lang de
zfsm check --lang de
zfsm services --lang de
zfsm emergency status --lang de
```

Erwartet: Paketversion `1.0.0-34~rc10`, erfolgreiche Integrationsprüfung und
vorhandene Zeitpläne unverändert. Automatische Notfallbereinigung bleibt ohne
vorherige ausdrückliche Aktivierung AUS. Der geprüfte ZIP-Installer registriert
eine rootgeschützte Verteilungskopie des RC10-Pakets außerhalb des DEB. Diese
enthält keine Host-Konfigurationen. Reine DEB-Installation erzeugt diese Kopie
nicht; für Clusterverteilung deshalb die vollständige ZIP verwenden.

Bei bereits installiertem RC10 kann derselbe geprüfte ZIP-Installer die
Verteilungskopie ergänzen, ohne das Paket erneut zu installieren. Eine neuere
Paketversion wird nicht herabgestuft.

## Clusterfunktion testen

Weboberfläche mit Strg+F5 neu laden und als `root@pam` anmelden. ZFS Manager →
**Clusterinstallation** öffnen. Der Steuerknoten bleibt der Ursprung der
Websitzung, auch wenn links ein anderer Knoten ausgewählt ist.

1. Zuerst genau einen entbehrlichen Online-Testknoten auswählen.
2. **Ausgewählte Knoten prüfen**. Version, Paketstatus und Vorprüfung lesen.
   Noch keine Pakete werden installiert. Die Übertragung verwendet bestehende
   Proxmox-Cluster-SSH-Vertrauensbeziehungen; unbekannte Schlüssel bleiben gesperrt.
3. Häkchen setzen und **Auf ausgewählten Knoten installieren** bestätigen.
4. Aufgabenprotokoll und Ergebnis je Knoten prüfen; auf dem Ziel müssen Paket
   **RC10** und dessen API/GUI vorhanden sein. Konfigurationen und individuelle
   Zeitpläne vor/nach dem Versuch vergleichen.
5. Erst danach mehrere entbehrliche Testknoten auswählen. Gleiche oder neuere
   Versionen bleiben unverändert. Offline-Knoten sind nicht auswählbar.

Vorschau: fünf Minuten gültig, einmal verwendbar. Bei Fehler stoppt die
Verteilung. Abgeschlossene Installationen werden nicht zurückgerollt. Bei
Verbindungsabbruch einen als unklar gemeldeten Zielzustand vor Wiederholung
manuell prüfen. Fensterschließen stoppt keine Hintergrundaufgabe.

CLI-Alternative nach der ZIP-Installation:

```bash
zfsm cluster status --lang de
zfsm cluster preview --nodes node-a,node-b --lang de
zfsm cluster install --plan VORSCHAU_ID --lang de
```

Beispielnamen durch die bewusst gewählten Testknoten und `VORSCHAU_ID` durch
die ausgegebene 32-stellige `job`-Kennung ersetzen. Die CLI verlangt zusätzlich
eine interaktive Bestätigung. Ohne diese Bestätigung keine Installation.

## Prüfbericht zurückgeben

Steuerknoten-/Zielversion, erfolgreiche Vorprüfung, Installationsergebnis und
eventuelle Fehlermeldung nennen. Prüfen, ob die vorhandenen Zeitpläne und
Konfigurationen erhalten blieben und die Oberfläche nach Wechsel zwischen den
Knoten funktioniert. Keine Schlüssel oder Zugangsdaten in Ausgaben aufnehmen.
Details zu Sperren und Abbruchfällen: `CLUSTER-INSTALL.md`.

Noch nicht nachgewiesen sind reale Cluster-SSH-Installation, mehrere reale
Steuerknoten und realer Verbindungsabbruch während dpkg. Diese Punkte bleiben bis
zu neuen Praxistests offen. Keine echte Snapshot-Löschung oder Rollback ist für
den Clusterinstallationstest erforderlich.
