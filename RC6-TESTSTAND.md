# BuMaVory ZFS Manager 1.0.0-34 RC6 – Teststand

- 199 Offline-Tests bestanden (Python/pytest, Proxmox-API-Mocks, GUI-Verhalten).
- JavaScript-Parserprüfung mit `node --check` bestanden.
- `bash -n install-local.sh` und `bash -n build_deb.sh` bestanden.
- Isoliertes Upgrade von registrierter **RC5** mit echtem damaligem GUI-/API-Quellstand auf **RC6** bestanden; API/GUI neu, Gast-Policy und Proxmox-Nodes-Route unverändert, Sicherungen vorhanden.
- Sicherheit: AutoSnap bereits vorhanden, fehlendes AutoSnap mit APT-Vorprüfung, freiwillig deaktivierte Zeitpläne, doppelte Zeitpläne, vorhandene Cron-Aufträge ohne Paket, manuelles zsync und native Proxmox-Replikation geprüft.
- Nicht ausgeführt: Live-Installation auf PVE4, Snapshot-Löschung, Replikationsänderung, APT-Änderung, zpool/zfs-Schreibbefehl.
- Keine zweite automatische Bereinigung. Automatische ZFS-Manager-Notfallbereinigung bleibt deaktiviert.
