# BuMaVory ZFS Manager 1.0.0-34 RC5 – AutoSnap Pflichtkomponente

**`zfs-auto-snapshot` ist eine feste Paketabhängigkeit.** Fehlt es, installiert der
mitgelieferte lokale Installer (`install-local.sh`) es automatisch aus den auf dem
PVE-Host konfigurierten APT-Paketquellen. Eine Simulation wird vorher erfolgreich
geprüft. Es gibt **keine allgemeinen Upgrades oder Entfernungen**, kein zusätzliches
Repository und keine zweite Snapshot-Cron-Konfiguration.

## Installation (vollständige ZIP entpacken)

```bash
bash install-local.sh
```

Diese Datei muss neben `pve-zfs-manager_1.0.0-34~rc5_all.deb` liegen. Die zugehörige
`SHA256SUMS` wird automatisch geprüft, wenn vorhanden. Die komplette ZIP sollte
zusätzlich gegen die separat veröffentlichte SHA256-Prüfsumme verifiziert werden.

## Neuinstallation ohne AutoSnap

1. PVE 9.x und Paketinhalt lesend prüfen, bevor APT verändert wird.
2. Bei fehlendem AutoSnap genau `zfs-auto-snapshot` simulieren und installieren:
   `apt-get --no-remove --no-upgrade --no-install-recommends install zfs-auto-snapshot`.
3. Vorhandene Cron-Dateien und ausführbares AutoSnap verifizieren.
4. Das DEB mit `dpkg -i` installieren und `zfsm`-Status prüfen.

**Wichtig:** Ein nacktes `dpkg -i` löst fehlende Debian-Abhängigkeiten nicht selbst
auf. Wer den Installer umgeht, muss stattdessen einen APT-basierten Paketinstallationsweg
verwenden. Es gibt absichtlich keinen `apt`-Aufruf in Debian-`preinst`/`postinst`,
weil dabei die Paketverwaltung gesperrt wäre.

## Upgrade bestehender Hosts

Ein vorhandenes AutoSnap bleibt unverändert; seine Cron-Dateien und Aufbewahrungswerte
werden weder zurückgesetzt noch neu angelegt. Der ZFS Manager liest und verwaltet
bereits die bestehenden Aufbewahrungswerte, installiert aber keinen zweiten Prune-Timer.
`checkzfs`, `bashclub-zsync` und `Checkmk` werden nicht benötigt und nicht verändert.

Bei frisch installiertem AutoSnap werden dessen **vorhandene Paket-Zeitpläne** aktiv.
Das kann beim nächsten Cron-Lauf neue automatische Snapshots auf geeigneten Datasets
erstellen. Vererbung und Auswahl über `com.sun:auto-snapshot` müssen bei Bedarf vom
Administrator angepasst werden. Der getrennte **ZFS-Manager-Auto-Notfall-Cleanup**
bleibt bei der Installation deaktiviert.
