# Version 1.1 — Installation / Upgrade

## Deutsch

Auf dem bewusst ausgewählten PVE-9-Steuerknoten als root ausführen. Erst prüfen,
danach installieren. Für die Clusterfunktion die vollständige ZIP verwenden;
eine reine DEB-Installation erzeugt keine Verteilungskopie.

```bash
mkdir -p /root/bmv-zfsm-1.1
chmod 700 /root/bmv-zfsm-1.1
cd /root/bmv-zfsm-1.1
wget -O bootstrap-1.1.sh 'https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.1/bootstrap-1.1.sh'
echo '45c447c682b0ed325e5a9c0aae84c13b1af6b1422b54ce28b8df956bd0e62403  bootstrap-1.1.sh' | sha256sum -c -
wget -O SHA256SUMS 'https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.1/SHA256SUMS'
```

Nur nach erfolgreicher Bootstrap-Prüfung fortfahren. Die ZIP-Prüfsumme aus der
Release-Datei lesen; alternativ direkt mit dem veröffentlichten SHA256 vergleichen:

```bash
paket_url='https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.1/BuMaVory-ZFS-Manager-1.1.zip'
paket_sha="$(awk '$2 == "BuMaVory-ZFS-Manager-1.1.zip" {print $1}' SHA256SUMS)"
bash ./bootstrap-1.1.sh "$paket_url" "$paket_sha" --check-only --lang de
```

Nach erfolgreicher Vorprüfung bewusst installieren:

```bash
bash ./bootstrap-1.1.sh "$paket_url" "$paket_sha" --lang de
zfsm version --lang de
zfsm check --lang de
zfsm services --lang de
zfsm emergency status --lang de
```

Der Einstieg funktioniert ohne unzip. Der Installer prüft die äußere ZIP und alle
enthaltenen Dateien vor Paketcode, installiert ausschließlich die geprüften lokalen
Pakete nach exakter APT-Simulation und behält bestehende Einstellungen/Zeitpläne.
Keine allgemeinen Upgrades, keine automatische Paketreparatur, keine Downgrades.
Gleiche Version: keine Paket-Neuinstallation; die geprüfte Verteilungskopie kann
bei erneutem vollständigem ZIP-Aufruf ergänzt werden.

Entpackte ZIP: im Paketverzeichnis zuerst `bash install-local.sh --check-only --lang de`,
danach `bash install-local.sh --lang de`. Niemals Skripte aus unvollständig
heruntergeladenen oder ungeprüften Paketverzeichnissen ausführen.

## Cluster

Weboberfläche mit Strg+F5 neu laden. Als `root@pam` → ZFS Manager →
Clusterinstallation. Ziele ausdrücklich auswählen, Vorprüfung lesen, Häkchen setzen
und Installation bestätigen. Vorhandene Cluster-IP-Adressen, Quorum, erreichbares
SSH und gültige bestehende Hostschlüssel erforderlich; keine Fabric erforderlich.
IPv4/IPv6 werden im Code unterstützt. Ein eigener Ethernet-Praxistest wurde nicht
separat dokumentiert. Details: [CLUSTER-INSTALL.md](CLUSTER-INSTALL.md).

Bei Fehler stoppt die Verteilung; fertige Knoten bleiben installiert. Unklare
Zielzustände vor Wiederholung prüfen. Fensterschließen stoppt keine Aufgabe.
Automatische Notfallbereinigung bleibt ohne vorherige Aktivierung AUS.

## English

Use the complete ZIP on the chosen PVE-9 coordinator as root. Verify the pinned
bootstrap hash above, then run the same commands with `--lang en`. Start with
`--check-only` and install only after a successful preflight. The bootstrap does
not require unzip. All archive members are verified before contained package code.
No general system/Proxmox upgrade, automatic package repair or downgrade is used.
A bare DEB does not register the cluster distribution copy; use the full ZIP.

For cluster deployment, log in as root@pam, explicitly select nodes, inspect the
preflight and confirm. Existing node settings/schedules remain local. Existing
cluster member IP addresses and root SSH trust are used; no Fabric is required.
Quorum and reachable SSH are necessary. Failed rollout stops; completed installs
remain. Inspect uncertain targets before retrying. Keep independent backups.
The operator tested the Fix2 predecessor; exact 1.1 host installation, interrupted
dpkg, concurrent real coordinators and real offline rescue remain unverified.
