# Install RC9 / RC9 installieren

Published package: `pve-zfs-manager_1.0.0-34~rc9_all.deb`.
SHA256: `f48f7cfef9aacd070a3185c896b49b85149c90fe4b4595a15929bd2dee6a776f`.
The DEB is the exact operator-tested file; it was not rebuilt for publication.

## Deutsch

Alle Befehle auf dem jeweiligen **PVE-Host als root**, nicht auf dem Arbeitsplatz-PC.
Vorher unabhängige Sicherungen und Zugang über eine separate Konsole bereithalten.
Der Weg unterstützt Neuinstallation und RC7-/RC8-Upgrade. PVE 9.x wird ohne
Minor-/Patch-Rückfrage strukturell geprüft. Bei unbekannter Struktur sicherer Abbruch.

Bootstrap und äußere Prüfsummen aus dem offiziellen GitHub-Release herunterladen:

```bash
mkdir -p /root/bmv-rc9
chmod 700 /root/bmv-rc9
cd /root/bmv-rc9
wget -O bootstrap-rc9.sh 'https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.0.0-34-rc9/bootstrap-rc9.sh'
wget -O SHA256SUMS 'https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.0.0-34-rc9/SHA256SUMS'
echo 'ae5cf53ac8bed2bc71e1ede9502de95b018828387505a11b37124ce4c34ac0d5  bootstrap-rc9.sh' | sha256sum -c -
```

Nur nach `bootstrap-rc9.sh: OK` und eigener Prüfung des Skriptinhalts fortfahren.
Das äußere Manifest kommt aus demselben Release und ist kein unabhängiger
Herkunftsnachweis. Repository/Übertragungsweg prüfen; keine blinde Root-Pipeline.
Der Bootstrap prüft die ZIP-SHA256, entpackt sicher mit Python ohne unzip und
prüft sämtliche enthaltenen Dateien, bevor Installer oder Paketcode gestartet wird.

Prüfmodus ohne Installation:

```bash
RC9_ZIP_SHA256="$(awk '$2=="BuMaVory-ZFS-Manager-1.0.0-34-rc9.zip" {print $1}' SHA256SUMS)"
bash ./bootstrap-rc9.sh \
  'https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.0.0-34-rc9/BuMaVory-ZFS-Manager-1.0.0-34-rc9.zip' \
  "$RC9_ZIP_SHA256" --check-only --lang de
```

Erst nach erfolgreicher Vorprüfung installieren (in derselben Shell):

```bash
bash ./bootstrap-rc9.sh \
  'https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.0.0-34-rc9/BuMaVory-ZFS-Manager-1.0.0-34-rc9.zip' \
  "$RC9_ZIP_SHA256" --lang de
```

Es werden nur die geprüften lokalen Pakete installiert. Die APT-Simulation muss
exakt den Manager und erforderliche fehlende mitgelieferte Abhängigkeiten planen.
Zusätzliche Inst/Conf-Aktionen, Entfernen und Downgrades werden nicht freigegeben.
Keine automatischen allgemeinen Upgrades, kein apt -f install. Fehlende
Basisabhängigkeiten oder fremde Scheduler benötigen eine eigene Prüfung.
Debian-13/Trixie-Abhängigkeiten: unzip amd64 und zfs-auto-snapshot all. PVE/Python/
Perl/cron/ZFS sind Hostbasis, keine mitgelieferten Ersatzpakete.

Nach der Installation direkt die Webadresse dieses Hosts öffnen und mit
Strg+Umschalt+R neu laden. Ein anderer ausgewählter Clusterknoten liefert nicht
unbedingt dieselbe auf dem Webserver geladene GUI-Datei. Danach prüfen:

```bash
zfsm version --lang de
zfsm check --lang de
zfsm services --lang de
zfsm emergency status --lang de
dpkg --audit
```

Bestehende Zeitpläne, Secrets und Einstellungen bleiben erhalten. Automatische
Notfallbereinigung bleibt bei Neuinstallation AUS; bestehende Aktivierungen bleiben.
Die normale AutoSnap-Aufbewahrung wirkt weiterhin bei ihren Zeitplanläufen.
Keine produktiven Löschungen/Rollbacks zur bloßen GUI-Prüfung ausführen.
Integrationsbackups: /var/lib/pve-zfs-manager/backups. Kein automatischer
Paket-Downgrade und kein blindes Zurückkopieren alter Proxmox-Dateien; Rückbau bei
Problemen gezielt prüfen. zfsm restore ist keine automatische Wiederherstellung.

## English

Run the commands on the target **PVE host as root**, not on a workstation. Keep
independent backups and separate console access. Download the bootstrap and outer
SHA256SUMS as above and verify the pinned bootstrap checksum before execution.
Use the same commands with `--lang en`; run `--check-only` first, then omit that
flag only after successful preflight. Fresh installation and RC7/RC8 upgrades use
the same route. The installer does not perform general system/Proxmox upgrades.
PVE 9.x minor/patch numbers are accepted; incompatible structures still stop safely.
Unsupported competing schedulers are not silently replaced.

The public ZIP/source checksums differ from the private test delivery because
internal handover documents were omitted and public documentation was added.
The DEB and executable installer/bootstrap bytes are unchanged. Packaged historical
manuals are frozen in packaging/rc9-tested-docs to preserve the tested DEB contents.
Current release information is in the repository documentation and RELEASE-QA.md.
