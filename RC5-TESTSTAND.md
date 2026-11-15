# BuMaVory ZFS Manager 1.0.0-34 RC5 – Teststand vom 11.11.2026

Diese Testversion ergänzt **ausschließlich den Installationsweg für die verpflichtende
Komponente `zfs-auto-snapshot`** und aktualisiert die Versionskennung. Die Proxmox-GUI,
ZFS-Snapshot-API, Gast-Policy, Notfalllöschregeln und Replikationseinstellungen bleiben
gegenüber RC4 unverändert.

## Neue Installation

Die ZIP vollständig entpacken und als root **auf dem Proxmox-VE-9.x-Host** ausführen:

```bash
bash install-local.sh
```

Dieser Helfer prüft den Host und das Release-DEB zuerst lesend und lässt bei fehlendem
`zfs-auto-snapshot` eine APT-Simulation und anschließend die gezielte Installation
von AutoSnap samt zwingenden Abhängigkeiten laufen. Keine allgemeinen Upgrades,
keine Paketentfernung. Bestehende Cron-Konfigurationen bleiben unverändert.

**Nicht einfach `dpkg -i` auf einem Host ohne AutoSnap verwenden:** `dpkg` löst
fehlende Abhängigkeiten nicht selbst auf. Das DEB deklariert AutoSnap zusätzlich als
verpflichtende Debian-Abhängigkeit.

## Upgrade / bestehende Installation

Bestehende AutoSnap-Einstellungen werden nur überprüft, nicht überschrieben.
Die automatische ZFS-Manager-Notfallbereinigung bleibt standardmäßig deaktiviert.

Geprüft: 191 isolierte Python-Tests inkl. Installer-Mocks und Upgrade-Simulation,
Shell-Syntax sowie DEB-Metadaten. **Keine Live-Installation dieser RC5 auf PVE4**.
