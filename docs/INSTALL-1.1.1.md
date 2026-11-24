# Version 1.1.1 — Installation / Upgrade

## Deutsch

Auf dem bewusst ausgewählten PVE-9-Knoten als root ausführen. Der vollständige
ZIP-Installer aktualisiert auch die Testversionen 1.1.1~test1 bis ~test6.
Bestehende Snapshot- und Aufbewahrungseinstellungen bleiben erhalten.

Zuerst Bootstrap herunterladen und seine feste Prüfsumme vergleichen:

```bash
mkdir -p /root/bmv-zfsm-1.1.1
chmod 700 /root/bmv-zfsm-1.1.1
cd /root/bmv-zfsm-1.1.1
wget -O bootstrap-1.1.1.sh 'https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.1.1/bootstrap-1.1.1.sh'
echo '9f65bbec8a89fdb7d30e88e1af2e1c395a5684325f13cba5a1cb1542d8102e6a  bootstrap-1.1.1.sh' | sha256sum -c -
wget -O SHA256SUMS 'https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.1.1/SHA256SUMS'
```

Nur bei erfolgreicher Bootstrap-Prüfung fortfahren:

```bash
paket_url='https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.1.1/BuMaVory-ZFS-Manager-1.1.1.zip'
paket_sha="$(awk '$2 == "BuMaVory-ZFS-Manager-1.1.1.zip" {print $1}' SHA256SUMS)"
bash ./bootstrap-1.1.1.sh "$paket_url" "$paket_sha" --check-only --lang de
```

Nach erfolgreicher Vorprüfung installieren:

```bash
bash ./bootstrap-1.1.1.sh "$paket_url" "$paket_sha" --lang de
zfsm version --lang de
zfsm check --lang de
zfsm services --lang de
zfsm update check --lang de
```

Danach die Oberfläche mit Strg+F5 neu laden. Auf bereits aktualisierten Knoten
stehen die gastweisen AutoSnap-Einstellungen, vollständige Gast-Snapshot-Löschung,
dezente Statusfarben und die aufgeräumte Dataset-Liste bereit. Replikationsbereiche
werden über Alle Datasets anzeigen eingeblendet. In ZFSM-Updates werden täglich
geprüfte stabile Versionen angezeigt und nach Vorprüfung ausdrücklich installiert.
Die Updateprüfung installiert niemals automatisch. Details: UPDATES.md.

Die geprüfte vollständige ZIP ist auch für die optionale Clusterverteilung nötig.
Eine alleinige DEB-Installation erzeugt keine lokale Verteilungskopie. Die Prüfung
der Archive erfolgt vor enthaltenem Paketcode. Der Einstieg benötigt kein unzip;
fehlende ausdrücklich vorgesehene Abhängigkeiten liegen geprüft bei. Keine allgemeinen
Systemupgrades, automatische Paketreparatur, Downgrades oder Paketentfernungen.
Bei STOP nicht mit --force oder apt -f fortfahren, sondern die Ursache prüfen.
Die Installation selbst löscht keine Snapshots. Bereits aktive Zeitpläne können
weiterhin entsprechend ihrer Aufbewahrung ältere automatische Snapshots entfernen.

Entpackte Lieferung: zuerst bash install-local.sh --check-only --lang de, danach
bash install-local.sh --lang de. Für Quellarchive diese versionierte Anleitung
verwenden; eine ältere quick-install.sh im Archiv ist kein aktueller Einstieg.
Die zusätzlich bereitgestellte quick-install-1.1.1.sh ist auf die endgültigen
Release-Prüfsummen gepinnt.

## English

Run the same verified commands with --lang en as root on the selected PVE-9 node.
Start with --check-only and install only after a successful preflight. Use the
complete ZIP for cluster support. The bootstrap does not require unzip. It verifies
the outer archive and full inner manifest before package code, uses exact package
plans and retains existing settings. No general upgrade, automatic repair or downgrade.
Reload the UI with Ctrl+F5. ZFSM updates checks stable releases daily and requires
an explicit root@pam confirmation before installation. Existing schedules may still
prune older automatic snapshots according to their configured retention.
