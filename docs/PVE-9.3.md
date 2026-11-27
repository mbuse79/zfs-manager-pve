# PVE 9.3: Kompatibilität und nächste Integrationsschritte

Stand 27.11.2026. Der Betreiber meldet, dass ZFSM das Update auf PVE 9.3.1
überstanden hat. Das ist kein vollständiger Funktionstest aller Schreibaktionen.

## Installation und Kapazitätsalarm

Der Installer prüft zuerst `zfsm check --integration-only`. Ein Fehler bleibt
fatal. Anschließend läuft der normale `zfsm check`: kritische Poolbelegung bleibt
sichtbar, ihr Exitcode 2 allein verwirft aber nicht mehr eine erfolgreiche
Installation und verhindert nicht die Registrierung des geprüften Clusterpakets.
Andere Fehler stoppen weiterhin. `zfsm check` ohne Zusatz behält seine bisherige
Alarmsemantik. Keine Schwellen, Bereinigungsregeln oder Zeitpläne werden geändert.

Die Struktur-Fixture prüft Reparatur nach einem simulierten Paketwechsel auf
9.3.1 mit den bestehenden synthetischen GUI/API-Ankern. Echte 9.3-Dateien und
Live-Tests für Gastzuordnung, Vorschau, Webupdate und Cluster sind separat nötig.

## Gastidentität: Quellprüfung

Offizieller Quellcode:
https://github.com/proxmox/pve-guest-common/blob/master/src/PVE/GuestIdentity.pm
https://github.com/proxmox/pve-container/blob/master/src/PVE/LXC/Config.pm

Die Gastidentität steht in der top-level `meta`-Eigenschaft als `uid` und `rtime`.
`uid` besteht aus 20 Zeichen `[a-z2-7]`; `rtime` beschreibt die Registrierung im
Cluster. Es ist keine SMBIOS-UUID und keine VMID. Der Quellcode nennt 9.2.33 als
Mindestversion der unterstützenden pve-manager-Pakete: die Fähigkeit darf daher
nicht allein an einer 9.3-Versionsabfrage hängen. Ältere Knoten können meta beim
Schreiben verlieren. Restore-/Import-Konflikte werden durch Proxmox behandelt.

Für dauerhafte AutoSnap-Regeln sind zunächst lesende Erkennung, fehlende und
mehrdeutige Identitäten, Restore/Klon und gemischte Cluster zu prüfen. Eine ID
allein erlaubt keine Snapshot-Löschung; aktuelle Gast-/Datenträgerzuordnung,
Schutzstatus, Vorschau und Fingerprint bleiben erforderlich. Dieser Stand führt
noch keine neue persistente Gastregel ein und schreibt keine Gastkonfiguration.

## Weitere Kandidaten

Verschachtelte Proxmox-Benachrichtigungsregeln können bestehende ZFSM-Ereignisse
mit `origin=zfs-manager` und `type=zfs-manager-capacity` routen. ZFSM soll weiterhin
keine Benachrichtigungsziele oder geheimen Zugangsdaten selbst ändern.
API-Zugriffslog und APT-Verlauf helfen bei Diagnose; HA-Wartungsstatus kann in
Vorprüfungen angezeigt werden. Konkrete Endpunkte sind vor Implementierung zu prüfen.
Storage-Plugin-Formulare ersetzen keine Knotenpanel-Schnittstelle.

Offizielle Übersicht:
https://proxmox.com/en/about/company-details/press-releases/proxmox-virtual-environment-9-3
