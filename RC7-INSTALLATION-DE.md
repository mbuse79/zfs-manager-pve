# BuMaVory ZFS Manager 1.0.0-34 RC7 – sichere Installation

RC7 ist ein **Testpaket** und ersetzt keine Prüfung der Proxmox-Schnittstellen am Zielhost.

## Automatische Installation der ZIP-Voraussetzung unzip

Bei Installationen über einen Nextcloud-ZIP-Download wird `unzip` zum Entpacken
benötigt. Eine Prüfung **innerhalb** `install-local.sh` kommt dafür zu spät.

Das Release enthält daher `bootstrap-rc7.sh`, welches **vor dem Entpacken**
prüft, ob `unzip` verfügbar ist. Fehlt das Werkzeug, wird es durch APT aus den
konfigurierten Paketquellen mit folgenden Schritten nachinstalliert:

1. Prüfen, dass Proxmox VE 9.x läuft.
2. Release-ZIP über HTTPS laden und gegen den separat übermittelten SHA256-Wert prüfen.
3. `apt-get --simulate --no-remove --no-upgrade --no-install-recommends install unzip` ausführen.
4. Verweigern, wenn die Simulation installierte Pakete verändern oder Pakete entfernen würde.
5. Nur dann `apt-get --yes --no-remove --no-upgrade --no-install-recommends install unzip` aufrufen.
6. ZIP entpacken, Dateiprüfsummen und DEB-Version prüfen und `install-local.sh` starten.

Kein automatisches `apt update`, kein allgemeines Upgrade, kein Entfernen
vorhandener Pakete. Kann APT die Installation nicht sicher durchführen,
bricht der Installer ab und lässt den ZFS Manager unverändert.

Der Start erfolgt als Root mit einer separat verfügbaren Kopie der
`bootstrap-rc7.sh`:

```bash
bash bootstrap-rc7.sh 'https://NEXTCLOUD/s/FREIGABE/download' 'SHA256-DES-ZIP-ARCHIVS'
```

Wenn nur die ZIP-Datei bereitgestellt wird, muss der Startblock die identische
unzip-Prüfung **vor** `unzip -oq` durchführen. Nicht erst `install-local.sh`
starten und hoffen, dass `unzip` vorhanden ist.

## AutoSnap-Konflikte

RC7 korrigiert die falsche Erkennung der üblichen `which zfs-auto-snapshot`
Prüfzeilen als eigene Cron-Aufträge. Wirkliche doppelte Aufbewahrungsregeln
werden interaktiv aufgelistet. Der Administrator wählt die zu erhaltende Regel,
anschließend wird erst nach nochmaliger ausdrücklicher Bestätigung eine
Sicherung abgelegt und die anderen Cron-Zeilen deaktiviert. Keine ZFS-Snapshots
werden hierbei gelöscht. Ohne Terminal oder Auswahl erfolgt keine Änderung.

Bashclub-zsync und Proxmox-Replikation werden nur erkannt. Die getrennte
Replikationsverwaltung gehört zum späteren ZFS Replication Manager.
