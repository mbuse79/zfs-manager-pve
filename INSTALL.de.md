# Installation und Upgrade – v1.0.0-32

**Geprüfte RC-Umgebung:** Proxmox VE 9.2.25. Root-Rechte erforderlich. Die Finalversion selbst wurde auf dem echten Testhost noch nicht gesondert installiert.

1. Nach Freigabe der öffentlichen Version die `.deb` aus einer vertrauenswürdigen GitHub-Veröffentlichung herunterladen.
2. Die veröffentlichte SHA256-Prüfsumme kontrollieren. Eine Prüfsumme bestätigt die Dateiintegrität, **nicht allein die Vertrauenswürdigkeit** der Software.
3. Das Paket auf den Proxmox-Host übertragen und aus dem Verzeichnis der `.deb` installieren:

```bash
apt install ./pve-zfs-manager_1.0.0-32_all.deb
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
systemd-run --unit=zfsm32-install --collect /usr/bin/apt-get install -y /root/pve-zfs-manager_1.0.0-32_all.deb
journalctl -u zfsm32-install -n 50 --no-pager
```

### Vor dem Produktiveinsatz

Unabhängige Backups und einen Wiederherstellungstest einplanen. Lösch- und Rollback-Aktionen über mehrere Datasets sind nicht atomar. Für die Integration werden vorhandene Proxmox-GUI-/API-Dateien angebunden; nach Updates können Reparaturen erforderlich sein. Nicht getestete Versionen gelten nicht automatisch als kompatibel.

### Deinstallation

```bash
apt remove pve-zfs-manager
```

Vorhandene Sicherungen und Konfigurationsdateien prüfen. Nicht manuell in Proxmox-GUI-Dateien löschen. Zur Diagnose dienen `zfsm check`, `zfsm backups` und `zfsm logs`.
