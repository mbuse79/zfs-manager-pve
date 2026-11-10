# Installation und Upgrade – v1.0.0-32

**Geprüfte Paketrevision (`1.0.0-32+docs2`):** Die exakte DEB (SHA256 `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`) wurde am **09.11.2026** per APT auf `pve-test` mit Proxmox VE 9.2.25 installiert. Der Maintainer bestätigte `zfsm version`, `zfsm status`, `zfsm check`, `zfsm services` und die Weboberfläche. Der Laufzeitcode ist gegenüber der zuvor getesteten `1.0.0-32` unverändert. Dies ist weder eine Kompatibilitätsfreigabe für andere PVE-Versionen noch eine abgeschlossene Rechteprüfung. Siehe `PACKAGE-STATUS.md`.


**Geprüfte Umgebung:** Proxmox VE 9.2.25. Root-Rechte erforderlich. Die exakte DEB `1.0.0-32+docs2` wurde am 09.11.2026 per APT-Upgrade von `1.0.0-32` installiert; CLI und GUI wurden vom Betreiber erfolgreich bestätigt.

1. Die veröffentlichte `.deb` aus dem [GitHub-Release v1.0.0-32](https://github.com/mbuse79/zfs-manager-pve/releases/tag/v1.0.0-32) herunterladen.
2. Die veröffentlichte SHA256-Prüfsumme kontrollieren. Eine Prüfsumme bestätigt die Dateiintegrität, **nicht allein die Vertrauenswürdigkeit** der Software.
3. Das Paket auf den Proxmox-Host übertragen und aus dem Verzeichnis der `.deb` installieren:

```bash
apt install ./pve-zfs-manager_1.0.0-32+docs2_all.deb
```

Anschließend prüfen:

```bash
dpkg-query -W pve-zfs-manager
zfsm version
zfsm status
zfsm check
zfsm capacity --json
```

Das Proxmox-Webinterface auf Port 8006 öffnen und unter dem Knoten **ZFS Manager** auswählen. Bei Bedarf mit Strg+F5 aktualisieren.

### Falls die Web-Shell unterbrochen wird

Beim Nachladen der Proxmox-Oberfläche kann die Browser-Shell getrennt werden. Zuerst den Paketstatus prüfen. Alternativ lässt sich ein vertrauenswürdiges lokales Paket mit einer eigenen systemd-Unit installieren:

```bash
systemd-run --unit=zfsm32-install --collect /usr/bin/apt-get install -y /root/pve-zfs-manager_1.0.0-32+docs2_all.deb
journalctl -u zfsm32-install -n 50 --no-pager
```

### Vor dem Produktiveinsatz

Unabhängige Backups und einen Wiederherstellungstest einplanen. Lösch- und Rollback-Aktionen über mehrere Datasets sind nicht atomar. Für die Integration werden vorhandene Proxmox-GUI-/API-Dateien angebunden; nach Updates können Reparaturen erforderlich sein. Nicht getestete Versionen gelten nicht automatisch als kompatibel.

### Deinstallation

```bash
apt remove pve-zfs-manager
```

Vorhandene Sicherungen und Konfigurationsdateien prüfen. Nicht manuell in Proxmox-GUI-Dateien löschen. Zur Diagnose dienen `zfsm check`, `zfsm backups` und `zfsm logs`.

> **Hinweis / note (2026-11-10):** The intended release asset is `1.0.0-32+docs2` (SHA256 above), tested on `pve-test` on 2026-11-09. The original `1.0.0-32` remains a separate historical reference with a different checksum. / Das vorgesehene Release-Paket ist `1.0.0-32+docs2`; nicht mit dem älteren Paket verwechseln.
