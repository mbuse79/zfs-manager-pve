# RC9: Vorbereitung eines Offline-Rollbacks von rpool / Root

**Nur auf dem dedizierten Testhost.** Das Webinterface kann aus Sicherheitsgründen keinen live gemounteten Proxmox-Root zurücksetzen. Nach den beiden Host-Warnungen hinterlegt die API genau einen signierten (24 Stunden gültigen) Auftrag in `/var/lib/pve-zfs-manager/offline-rollback/plan-*.json` (root:root 0600). Dieser Schritt ändert **keine** ZFS-Snapshots.

## Voraussetzungen

- Vollständig getestetes externes Host-/VM-/LXC-Backup und Zugriff auf lokale/virtuelle Rettungskonsole.
- Passendes ZFS-fähiges Proxmox-Rescue-Medium. Boot von diesem Medium, nicht vom zurückzurollenden Root.
- ZFS-Pool noch nicht im laufenden Proxmox importiert. `zpool import` / `zfs list` prüfen.
- Ziel-Snapshot und jüngere Snapshots sind nicht von Klonen/Holds/Bookmarks abhängig.
- Kein aktives oder untergeordnetes Dateisystem im Zielbaum darf während des Rollbacks gemountet sein.

## Technischer Ablauf im Rescue-System (Vorlage – nicht blind kopieren)

Annahme: Poolname `rpool`; ursprünglicher Host-Root `rpool/ROOT/pve-1`. Nur nach Bestätigung dieser Zuordnung auf dem betroffenen Testgerät.

1. `mkdir -p /mnt/pve-root`
2. `zpool import -N -R /mnt/pve-root rpool` – **nur wenn der Pool noch nicht importiert ist**.
3. `zfs mount rpool/ROOT/pve-1` – Host-Root unter `/mnt/pve-root` öffnen, sofern Mountpoint wie erwartet. Import-/Mount-Ausgaben prüfen.
4. `python3 /mnt/pve-root/usr/lib/pve-zfs-manager/offline_recovery.py --stage --root /mnt/pve-root` – überprüft Schlüssel-/Plan-Dateien und kopiert Auftrag und Hilfsprogramm in `/run/pve-zfs-manager-rescue` (RAM).
5. `zfs unmount rpool/ROOT/pve-1` – Host-Root und alle von der Zielaktion erfassten Datasets **müssen** danach ausgehängt sein.
6. `python3 /run/pve-zfs-manager-rescue/offline_recovery.py --check` – HMAC, 24h-Frist, originalen Snapshotbestand, Child-Mounts, Klone, Holds und Bookmarks vergleichen. Kein Schreibzugriff.
7. Erst nach erfolgreicher Prüfung und Backupverifikation: `python3 /run/pve-zfs-manager-rescue/offline_recovery.py --apply` – löscht nur ausdrücklich aufgeführte neuere Snapshots des **einen** Datasets und setzt genau dieses auf den Ziel-Snapshot zurück.
8. Boot-/EFI-Zustand (Proxmox Boot Tool, Kernel, Initramfs) prüfen, Pool ordnungsgemäß exportieren, anschließend Host booten und Datenbestand verifizieren. Gegebenenfalls Recovery-Spezialist hinzuziehen.

Weder GUI noch Helfer verlangen eine Eingabe von Dataset-/Snapshot-Namen; sie übernehmen die signierte Auswahl. `--apply` ist eine bewusste separate Rescue-Aktion. Ein bereits vorhandener, alter Offline-Auftrag verhindert das Staging weiterer Aufträge, bis dieser manuell inspiziert/archiviert wird.

**Warnung:** Die einzelnen ZFS-Zerstörungs- und Rollback-Schritte sind nicht atomar; es besteht ein Restrisiko eines partiellen Zustands bei einem Laufzeitfehler. Der Helfer und dieser Ablauf sind lokal gemockt, aber noch NICHT real in einem Rescue-Boot getestet. Darum im Testsystem zuerst mit unkritischen Datasets beginnen.
