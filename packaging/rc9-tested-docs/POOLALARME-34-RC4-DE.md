# BuMaVory ZFS Manager 1.0.0-34 RC4 – ausschließlich Pool-Speicheralarme

**Testversion, noch kein öffentlicher Release.**

## Änderung

ZFS-Quotas und Refquotas einzelner Gastspeicher (VMs/LXC), auch in replizierten
Datasets, beschränken die Größe eines konkreten Datenträgers. Sie sagen nichts
darüber aus, ob ein **gesamter ZFS-Pool** knapp an freiem Speicher ist. Deshalb
dürfen diese Werte keine ZFS-Manager-Poolalarme auslösen.

- **Warnungen ausschließlich nach physischer ZFS-Pool-Belegung:** ab 80 % Warnung,
  ab 90 % kritischer Administratoralarm, ab 95 % Notfallwarnung.
- Datenquelle: `zpool list -H -p -o name,size,alloc,free,health`.
- Keine Warnungen, Push-Meldungen oder roten Kästen für LXC-/VM-`quota`,
  `refquota` und `avail` – auch nicht für Kopien unter Replikationspfaden.
- Aus RC2/RC3 gespeicherte `dataset:*`- und `monitor:datasets`-Alarmzustände
  werden beim nächsten automatischen Monitorlauf **ohne** Entwarnungsnachrichten
  verworfen. Snapshotdaten werden dabei nicht verändert.
- Fehlende Proxmox-Benachrichtigungsziele sind **nur bei einem aktiven Poolalarm**
  im ZFS-Manager eine Warnung. `zfsm emergency notify-check` und `notify-test`
  bleiben für Administratoren verfügbar.
- Poolzustand, Scrub-/Fehlerstatus und physische Pool-Datenträger bleiben im
  ZFS Manager sichtbar. Die reguläre Dataset-/Snapshot-Verwaltung bleibt erhalten.

## Sicherheitsgrenzen

Diese Änderung betrifft ausschließlich die Auswahl und Anzeige von Alarmen.
Sie ändert **nicht** ZFS-Pools, Volumes, Snapshots, Kontingente oder
Löschvorschauen. Auch die automatisierte Snapshot-Bereinigung bleibt im
Standardzustand **AUS**.

## Nach Installation (nur lesend)

```bash
zfsm version
zfsm check
zfsm emergency status
zpool list -o name,size,alloc,free,capacity,health
```

Wird keine physische Pool-Auslastung von mindestens 80 % ermittelt,
zeigt die Oberfläche keine Speicherwarnung an. Poolwarnungen sind weiterhin
aktiv und werden mit Wiederholungen über konfigurierte Proxmox-Ziele versendet.
**Hinweis:** Der Versand an ein Ziel ist nicht mit dem erfolgreichen Empfang
durch einen Administrator gleichzusetzen. Der Test der realen Zustellung steht
separat aus.
