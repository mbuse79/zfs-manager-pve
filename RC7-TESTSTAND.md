# ZFS Manager 1.0.0-34 RC7 – Offline-Teststand (11.11.2026)

- 211 pytest-Tests bestanden, einschließlich dreier isolierter Bootstrap-Szenarien.
- Fehlendes `unzip`: APT-Simulation → APT-Installation im isolierten Mock → Entpacken → Installerstart.
- APT würde ein installiertes Paket aktualisieren: Abbruch vor jeder Installation.
- ZIP-SHA256 falsch: Abbruch vor APT und Entpacken.
- Falsche AutoSnap-Doppelmeldung durch `which zfs-auto-snapshot` behoben.
- Echte doppelte AutoSnap-Cron-Regeln: interaktive Auswahl, Bestätigung,
  Sicherung, deaktivierte Zeilen rückholbar.
- Release-DEB mit dpkg-deb erstellt und Metadaten geprüft.

Praxistests auf PVE4 und Testhost `pve` stehen noch aus. Es wurden keine
realen ZFS-Pools, Snapshots, Replikationen oder Proxmox-Hosts verändert.
