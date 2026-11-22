# Guest snapshot controls / Gastweise Snapshot-Aktionen

Development change after release 1.1; not included in the existing 1.1 downloads.
Entwicklungsstand nach Release 1.1; nicht in den vorhandenen 1.1-Downloads enthalten.

## Deutsch

Im Tab **VMs / LXC** stehen direkt in jeder Gastzeile zwei zusätzliche Aktionen:

- **AutoSnap ausschließen** setzt die ZFS-Eigenschaft `com.sun:auto-snapshot`
  und die sechs Intervall-Eigenschaften (frequent, hourly, daily, weekly,
  monthly, yearly) auf `false`, auf allen aktuell konfigurierten und eindeutig
  zugeordneten ZFS-Datenträgern des Gasts. Der Ausschluss bleibt in ZFS gespeichert
  und wird in der Gastzeile angezeigt. Manuelle Snapshots bleiben möglich.
  Die Aktion selbst entfernt keine bestehenden Snapshots und verändert keine Cronjobs.
- **AutoSnap einschalten** setzt dieselben Eigenschaften ausdrücklich auf `true`.
  Das aktiviert alle vorhandenen AutoSnap-Intervalle für diese Datenträger;
  frühere individuelle oder geerbte Eigenschaftswerte werden nicht wiederhergestellt.
  Die vorhandenen Zeitpläne und ihre Aufbewahrung gelten weiterhin.
- **Alle Snapshots löschen** ermittelt serverseitig sämtliche Snapshots auf allen
  aktuell zugeordneten ZFS-Datenträgern genau dieses Gasts. Auch unterschiedlich
  benannte oder nur auf einzelnen Datenträgern vorhandene Snapshots werden in der
  Vorschau vollständig aufgeführt. Gelöscht werden nur diese einzelnen Snapshot-Ziele,
  ohne rekursives Löschen, Dataset-Löschung oder Veränderung anderer Gäste.

Beide Aktionen verlangen einen Snapshot-Administrator, eine fünf Minuten gültige
signierte Vorschau, eine aktiv gesetzte Checkbox und eine weitere Bestätigung.
Vor der Ausführung werden die Zuordnung und der relevante Zustand erneut geprüft.
Löschen verlangt zusätzlich einen gestoppten, ungeschützten und ungesperrten Gast;
vorhandene Proxmox-Snapshot-Metadaten, Holds, Clones oder Bookmarks können die Aktion
sperren. Ein Gast muss für die AutoSnap-Einstellung nicht angehalten werden.

Die Eigenschaften gelten für die vorhandenen ZFS-Datenträger, nicht als dynamische
VMID-Regel: Nach Hinzufügen, Ersetzen oder Verschieben von Datenträgern den Ausschluss
prüfen und erneut anwenden. Nicht-ZFS-Datenträger und Snapshot-Verfahren anderer
Produkte werden damit nicht gesteuert. Ein bereits laufender AutoSnap-Prozess wird
nicht abgebrochen. Nach dem Löschen kann ein aktiver Zeitplan neue Snapshots erzeugen;
falls unerwünscht, zuerst AutoSnap ausschließen.

Mehrere Datenträger werden nacheinander verarbeitet. Bei Fehlern stoppt die Aktion;
abgeschlossene und fehlgeschlagene/unklare Ziele werden gemeldet. Kein automatischer
Rollback. Bestehende Grenzen von maximal 32 zugeordneten ZFS-Datenträgern und
500 Snapshots je Dataset bleiben erhalten; bei Überschreitung wird abgebrochen,
nicht still gekürzt. Snapshots sind kein Ersatz für unabhängige Backups.

## English

The **VMs / LXC** tab adds guest-row actions to exclude a guest's currently configured
ZFS disks from AutoSnap, explicitly enable them again, or delete all their snapshots.
Exclusion sets `com.sun:auto-snapshot` and its six interval properties to `false`;
enabling sets all seven properties to `true`, rather than restoring earlier custom
or inherited values. Manual snapshots remain available. Changing these properties
itself deletes no snapshots and does not change schedules.

Exclusion persists on the existing datasets. It is not a dynamic VMID rule: review
and reapply it after adding, replacing or moving disks. Non-ZFS disks, other snapshot
products and already running AutoSnap processes are outside its scope. Active
schedules can create new snapshots after deletion; exclude AutoSnap first if needed.

Delete-all resolves every current ZFS disk server-side and previews each exact
snapshot target, including incomplete groups. It requires a stopped guest and retains
existing protection, lock, Proxmox-metadata, clone, hold and bookmark checks. It never
recursively destroys datasets. Both actions require administrator authorization,
a signed five-minute preview, a checked acknowledgment and another confirmation.
Guest configuration and relevant state changes invalidate the preview.

Multi-disk operations are sequential and non-atomic. Failures stop later writes and
report completed and failed/uncertain targets, without automatic rollback. Existing
limits of 32 ZFS disks per guest and 500 snapshots per dataset fail closed rather than
silently truncating results. Keep independent backups.

## Upgrade alongside the replication panel / Upgrade mit Replikationspanel

A registered RC9 installation can be migrated when the independent replication
panel uses the exact read-only `me.items.findIndex` lookup of our menu item to
position itself. The lookup must occur once inside `PVE.node.Config`. Only the
bounded ZFS Manager block is replaced; the replication panel and unrelated API
registrations remain byte-for-byte unchanged. Other stray references, duplicate
manager fragments, missing registration and damaged markers still stop preflight.

Eine registrierte RC9-Installation lässt sich auch mit dem separaten
Replikationspanel aktualisieren, wenn dessen exakter lesender Menüverweis einmal
innerhalb von `PVE.node.Config` steht. Nur der begrenzte ZFS-Manager-Block wird
ersetzt. Replikationspanel und fremde API-Einträge bleiben unverändert. Andere
zusätzliche Verweise, doppelte Manager-Blöcke, fehlende Registrierung und beschädigte
Marker führen weiterhin zum Abbruch der Vorprüfung.
