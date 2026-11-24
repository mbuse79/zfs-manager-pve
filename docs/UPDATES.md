# ZFSM updates / ZFSM-Updates

Available in release 1.1.1; existing 1.1 downloads remain unchanged.

## Deutsch

Der installierte Manager prüft täglich und nach dem Booten zeitversetzt das neueste
**stabile** Release von `mbuse79/zfs-manager-pve` auf GitHub. Die Prüfung lädt nur
Release-Metadaten und speichert das Ergebnis lokal. Sie installiert nichts und
führt keinen heruntergeladenen Paketcode aus. Der Dienst benötigt HTTPS-Zugriff
auf GitHub; bei Netz-/API-Fehlern erscheint ein Fehler statt einer Updatezusage.

In der ZFSM-Werkzeugleiste öffnet **ZFSM-Updates** den Status mit installierter und
neuester stabiler Version sowie dem Zeitpunkt der letzten Prüfung. Bei einem
neueren Release steht dort **Update verfügbar**. **Jetzt prüfen** aktualisiert
die Metadaten. Installationen sind `root@pam` vorbehalten; API-Tokens und delegierte
Snapshot-Administratoren dürfen keine Pakete aktualisieren.

**Update installieren** lädt zunächst die vollständige Release-ZIP und die
veröffentlichten Prüfsummen, prüft GitHub-Asset-Digests (sofern vorhanden), ZIP und
inneres Manifest, Paketname, Version und Architektur. Anschließend läuft die
vorhandene Installer-Vorprüfung einschließlich exakter APT-Planprüfung. Erst nach
erfolgreicher Vorprüfung kann das Bestätigungshäkchen gesetzt und die
**Installation bestätigt** werden. Die Vorschau gilt fünf Minuten und einmalig.
Geänderte PVE-/Paketstände, unfertige Paketkonfiguration und manipulierte Dateien
führen zum Abbruch. Die Prüfsummen werden über die festen HTTPS-Releaseadressen
bezogen; es handelt sich nicht um eine zusätzliche unabhängige GPG-Signatur.

Nur dieser bewusst ausgewählte Knoten wird aktualisiert. Bestehende
Sicherheitsprüfungen, Einstellungen und Zeitpläne bleiben über den normalen
Installer erhalten. Keine allgemeine Systemaktualisierung, automatische
Paketreparatur oder Installation von Test-/Vorabversionen. Eine neuere lokale
Testversion wird nicht durch ein älteres stabiles Release ersetzt.

**Aufgabenprotokoll** zeigt den laufenden PVE-Auftrag. Der eigentliche Lauf wird
als unabhängiger Systemauftrag gestartet und behält seinen Status auch bei einem
Neustart der PVE-API während der Paketkonfiguration. Das Schließen des Fensters
stoppt ihn nicht. Nach einem Fehler oder einer Unterbrechung zuerst Protokoll und
Paketstatus prüfen; ein bereits verwendeter Plan lässt sich nicht erneut starten.
Nach Erfolg die Oberfläche mit Strg+F5 neu laden. Reale Updateinstallation auf einem
PVE-Host ist noch separat zu bestätigen; die Testnachweise verwenden isolierte
Pakete und API-Fixtures.

CLI:

```bash
zfsm update status --json
zfsm update check --json
systemctl status pve-zfs-manager-update-check.timer
```

`zfsm update-check` ist ein Alias für die echte Prüfung. Cache und Aufträge liegen
rootgeschützt unter `/var/lib/pve-zfs-manager/updates`. Ein Öffnen/Aktualisieren der
Oberfläche löst keine Netzwerkprüfung und keine Installation aus.

## English

A systemd timer checks the latest published stable GitHub release daily and after
boot with a randomized delay. Checks fetch metadata only and never install or run
package code. The ZFSM toolbar displays cached status and offers a manual check.

Only `root@pam` may stage or install updates. Staging verifies the complete release
ZIP, release checksums, available GitHub asset digests, the full inner manifest and
DEB metadata before running the existing installer's read-only preflight. Installation
requires a checked acknowledgment and a five-minute, single-use plan; host/version
changes and unfinished package configuration block it. Existing installer protections
and exact APT plans remain enforced. Release trust is based on the fixed repository
and HTTPS checksums, not an additional independent signing key.

Updates apply to the selected node only. No automatic installation, prerelease
channel, downgrade, general system upgrade, or automatic package repair is performed.
Task logs are available through PVE; closing the window does not stop a running job.
Inspect uncertain failures before retrying and reload the browser after success.
Real PVE update execution remains unverified until confirmed by an operator.
