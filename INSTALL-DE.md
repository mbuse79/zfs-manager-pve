# ZFS Manager for Proxmox VE 1.0.0-32 – Installation

**Geprüfte Paketrevision (`1.0.0-32+docs2`):** Die exakte DEB (SHA256 `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`) wurde am **09.11.2026** per APT auf `pve-test` mit Proxmox VE 9.2.25 installiert. Der Maintainer bestätigte `zfsm version`, `zfsm status`, `zfsm check`, `zfsm services` und die Weboberfläche. Der Laufzeitcode ist gegenüber der zuvor getesteten `1.0.0-32` unverändert. Dies ist weder eine Kompatibilitätsfreigabe für andere PVE-Versionen noch eine abgeschlossene Rechteprüfung. Siehe `PACKAGE-STATUS.md`.


**Inoffizielles Community-Projekt.** Technische Final-Version auf Grundlage des auf Proxmox VE 9.2.25 getesteten RC1.

1. Debian-Paket `pve-zfs-manager_1.0.0-32+docs2_all.deb` auf den Proxmox-Host kopieren.
2. Prüfsumme mit `sha256sum` gegen die veröffentlichte SHA256SUMS vergleichen.
3. Als root installieren:

```bash
apt install ./pve-zfs-manager_1.0.0-32+docs2_all.deb
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

**Öffentlicher Release (10.11.2026):** `v1.0.0-32` ist veröffentlicht. Installation und Sicherheitshinweise gelten weiterhin. Offene Fragen zu Herkunft und Drittanbieterrechten sind in `LICENSING-REVIEW.md` dokumentiert.

> **Hinweis / note (2026-11-10):** The intended release asset is `1.0.0-32+docs2` (SHA256 above), tested on `pve-test` on 2026-11-09. The original `1.0.0-32` remains a separate historical reference with a different checksum. / Das vorgesehene Release-Paket ist `1.0.0-32+docs2`; nicht mit dem älteren Paket verwechseln.
