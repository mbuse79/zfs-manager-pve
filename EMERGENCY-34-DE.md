**RC4-Änderung:** Es gibt nur noch 80/90/95-%-Alarme für die physische
ZFS-Pool-Auslastung. Keine Quota-/Refquota-Warnungen für VMs, LXC oder
Replikations-Datasets. Siehe `POOLALARME-34-RC4-DE.md`.

# ZFS Manager 1.0.0-34 RC2 – ZFS-Speicherwarnungen und Notfallbereinigung

**TESTVERSION. Für produktive Systeme zunächst nur die Warn-/Vorschau-Funktionen prüfen.**

## Warnstufen

- Ab **80 %**: Warnung, gelbe Anzeige, regelmäßiger Eintrag ins Systemjournal.
- Ab **90 %**: **KRITISCH**, dauerhaft roter Hinweis im ZFS-Manager, Journalmeldung mit Administrator-Handlungsbedarf.
- Ab **95 %**: **NOTFALL**, verschärfter Warnzustand.
- Neue Warnungen/Erhöhungen werden beim Monitoring (alle 5 Minuten) protokolliert; bestehende Warnungen nach 60 Minuten erneut, bis der Wert sinkt (Wiederholintervall per Konfigurationsdatei anpassbar).
- `zfsm status` / `zfsm check` zeigen die kritische Kapazität auch außerhalb der Oberfläche.

Die Anzeige im Proxmox-Plugin und die Systemjournal-Meldungen sind implementiert. Der Versand über den nativen Proxmox-Notification-Matcher ist in RC2 integriert. **Ein passendes Benachrichtigungsziel und ein funktionierender Matcher müssen vom Administrator eingerichtet und mit `zfsm emergency notify-test` real geprüft werden.** Ohne Ziel bleibt die Warnung in Oberfläche, Terminal und Journal. Details siehe `BENACHRICHTIGUNGEN-34-RC2-DE.md`.

## Sicherheitsregeln für die 15 ältesten

- Maximal 15 **physische ZFS-Snapshot-Objekte** pro Bereinigungsdurchlauf, weltweit nach Erstellzeit sortiert **innerhalb des gewählten Pools**.
- Von jeder vorhandenen Art `frequent`, `hourly`, `daily`, `weekly`, `monthly`, `yearly` bleibt **auf jedem Dataset** mindestens ein Snapshot übrig, selbst wenn dieser viele Jahre alt ist.
- Es werden nur Namen mit dem Muster `zfs-auto-snap_<art>-...` berücksichtigt. **Manuelle** und alle anderen Snapshotnamen werden nicht automatisch entfernt.
- Keine Snapshots mit ZFS-Holds (`userrefs > 0`) oder bekannten abhängigen Klonen.
- Konservativer Ausschluss von Datasets mit Namen, die auf Replikation, `zsync`, Backups, PBS oder Smoketests hinweisen. Zusätzliche Pfade unter `excluded_datasets` konfigurierbar.
- Daten auf Gastlaufwerken nur bei eindeutig erkannter Proxmox-Zuordnung, **gestopptem** Gast und **vollständiger** Gruppe. Bei Unsicherheit bleibt die Gruppe unangetastet. Gastlaufwerke ohne sichere Zuordnung werden übersprungen.
- Root-, Boot- und Pool-Stammdatasets standardmäßig ausgeschlossen; nur spezieller Rescue-Modus kann systemische ROOT-Datasets nach expliziter Freigabe berücksichtigen.
- Vor jeder Löschung wird eine Vorschau neu geprüft; signierte GUI-Freigaben gelten maximal fünf Minuten. `zfs destroy -n -v` kontrolliert alle Zielnamen vor der ersten Veränderung. Nach jeder Löschung wird der Mindestbestand erneut kontrolliert.
- Mehrere ZFS-Löschungen sind **nicht atomar**. Bei Fehlern können bereits gelöschte Snapshots nicht automatisch wiederhergestellt werden; das Ergebnis bzw. die Fehlermeldung nennt den Teilstatus.
- Der bei Snapshots angezeigte ZFS-`USED`-Wert ist **keine Freigabeprognose**; die freigegebene Speichermenge kann kleiner oder null sein.

**Grenze der Erkennung:** ZFS kennt keine universelle Eigenschaft »wird von Replikation benötigt«. Falls ein Replikationstool automatisch benannte Snapshots als Grundlage einer Übertragung verwendet, müssen diese über Snapshot-Bezeichnung/Hold oder `excluded_datasets` ausdrücklich geschützt werden. Ein konfigurierter Replikationspfad wird nicht blind verändert, jedoch ist vollständiger automatischer Fremdtool-Schutz ohne dessen API nicht garantiert.

## Befehle nach Installation (PVE-Host)

```bash
# Komplett lesend, ohne Änderungen
zfsm emergency status
zfsm emergency preview --pool rpool --count 15
zfsm emergency preview --pool rpool_2 --count 15

# Nach 2 manuellen Bestätigungen: bis zu 15 ausgewählte Snapshots löschen
zfsm emergency cleanup --pool rpool --count 15

# Automatische Bereinigung ist ab Werk AUS. Erst nach Freigabe aktivieren:
zfsm emergency config --enable-auto-pool rpool --ack-risk

# Global wieder deaktivieren:
zfsm emergency config --disable-auto

# Monitoring über systemd, ohne manuellen Eingriff
systemctl status pve-zfs-manager-emergency.timer
journalctl -t zfsm-emergency -n 40 --no-pager
```

Im Webinterface: **ZFS Manager → Pool wählen → NOTFALL – Speicher freigeben → Vorschau → Sicherheitsbestätigung → zweite Bestätigung**. Automatische Bereinigung kann pro Pool nach Administrator-Bestätigung aktiviert und global deaktiviert werden. Bei 80 % führt ein aktivierter Pool maximal einen Bereinigungsdurchlauf pro Timerprüfung aus; daraufhin wird die Auslastung beim nächsten Lauf erneut kontrolliert. Die Bereinigung wird niemals ohne Einwilligung aktiviert.

## Recovery, wenn Proxmox nicht startet

Im Rescue-System ZFS installieren/aktivieren, die Zielpools **kontrolliert importieren** (keine blinden Force-Imports!) und die einzelne Datei `zfsm_emergency.py` aus dem ZIP dorthin kopieren. `python3`, `zpool` und `zfs` müssen vorhanden sein. Die Befehle sind auch ohne laufenden Proxmox-Konfigurationsdienst ausführbar:

```bash
python3 ./zfsm_emergency.py rescue-preview --pool rpool --count 15
python3 ./zfsm_emergency.py rescue-preview --pool rpool --count 15 --include-system
# Nur wenn die Vorschau genau überprüft wurde und eine Rettungssicherung vorliegt:
python3 ./zfsm_emergency.py rescue-cleanup --pool rpool --count 15 --include-system
```

Rescue überspringt grundsätzlich Gast-Datenträger, deren vollständige Proxmox-Konfiguration offline nicht sicher überprüfbar ist. `--include-system` erlaubt nach zwei Bestätigungen nur automatische Snapshots in `ROOT`-Datasets; Pool-Stamm und `boot/efi` bleiben geschützt. Es erfolgt **kein** automatischer ZFS-Import, kein automatisches Rollback und kein ungefragtes Löschen. Ein Rescue-Einsatz ist nur für erfahrene Administratoren vorgesehen.
