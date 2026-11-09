# ZFS Manager for Proxmox VE 1.0.0-32 – Installation

**Private Paket-Prüffassung (`1.0.0-32+docs2`):** Die aktualisierte DEB hat eine eigene Version und Prüfsumme. Sie wurde noch nicht live getestet und darf nicht mit der am 07.11.2026 getesteten `1.0.0-32` verwechselt oder veröffentlicht werden. Siehe `PACKAGE-STATUS.md`.


**Inoffizielles Community-Projekt.** Technische Final-Version auf Grundlage des auf Proxmox VE 9.2.25 getesteten RC1.

1. Debian-Paket `pve-zfs-manager_1.0.0-32_all.deb` auf den Proxmox-Host kopieren.
2. Prüfsumme mit `sha256sum` gegen die veröffentlichte SHA256SUMS vergleichen.
3. Als root installieren:

```bash
apt install ./pve-zfs-manager_1.0.0-32_all.deb
```

4. Prüfung:

```bash
zfsm version
zfsm status
zfsm check
zfsm capacity --json
```

5. Im Browser Proxmox VE (Port 8006) öffnen, mit Strg+F5 aktualisieren und unter dem Knoten `ZFS Manager` auswählen.

**Rückfall:** Vorheriges RC1-Paket und Sicherungen aufbewahren. `zfsm backups`, `zfsm logs` und `zfsm check` helfen bei der Analyse. Bei geändertem Proxmox-GUI-Layout nicht blind rücksichern. Die Software greift zur Integration auf Proxmox-Dateien zu und ist nicht offiziell von Proxmox unterstützt.

**Sicherheit:** Snapshot-Löschungen können endgültig sein. Sammellöschungen auf mehreren Datenträgern sind nicht atomar. Unabhängige Backups erforderlich. Die Kapazitäts-CLI ist nur lesend.

**Öffentliche Veröffentlichung:** Vor einem öffentlichen GitHub-Release müssen die in `PUBLICATION-CHECKLIST.md` genannten Lizenz- und Maintainerangaben bestätigt werden.

> **Hinweis / note (2026-11-09):** The command examples above refer to the already tested historical `1.0.0-32` binary. Do not substitute the private `+docs2` candidate until its exact SHA256 and live validation are confirmed.
