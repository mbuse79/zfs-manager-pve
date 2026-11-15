**Hinweis für RC4:** Die unten beschriebenen Dataset-/Quota-Alarme wurden auf
ausdrücklichen Wunsch des Administrators mit 1.0.0-34 RC4 abgeschaltet.
Für aktuelle Alarmregeln siehe `POOLALARME-34-RC4-DE.md`.
Der restliche Text dokumentiert den früheren RC2-Stand.

# BuMaVory ZFS Manager 1.0.0-34 RC2 – Benachrichtigungen und Dataset-Limits

**Testversion. Auf PVE4 ist bisher RC1 installiert. RC2 ändert keine ZFS-Pools oder Snapshots bei der Installation.**

## Neu

- Pool-Grenzwerte: ab 80 % Warnung, ab 90 % kritisch, ab 95 % Notfall.
- Quotas und `refquota` pro Dataset: Warnung ab 80 %, kritisch ab 90 %, Notfall ab 95 % des jeweiligen Limits. Ohne explizite Quota warnen wir separat, wenn bei Datasets mit mindestens 1 GiB belegtem Speicher weniger als 1 GiB effektiv verfügbar sind (kritisch unter 256 MiB, Notfall unter 64 MiB). Dabei ist `AVAIL` die ZFS-Dataset-Verfügbarkeit, **nicht** die physische Pool-Freiheit.
- Aktiver Versand über das vorhandene **Proxmox-VE-Benachrichtigungssystem** (`PVE::Notify`), das unter *Datacenter → Notifications* konfigurierte Mail-/Gotify-/Webhook-Ziele nutzt. Das Plugin erzeugt keine neuen Ziele, speichert keine Zugangsdaten und verändert keine Proxmox-Benachrichtigungseinstellungen.
- Journalmeldung beim erstmaligen Erreichen, beim Schweregradwechsel und alle 60 Minuten (Wert in `/etc/pve-zfs-manager/emergency.json` anpassbar).
- Proxmox-Benachrichtigung beim erstmaligen Erreichen, beim Schweregradwechsel und wiederholt nach dem eingestellten Intervall. Fehlschlagende Versandversuche werden beim nächsten Timerlauf erneut versucht. Die Warnung bleibt in der Weboberfläche sichtbar. Bei normalisiertem Zustand wird eine Entwarnung erzeugt.
- Dataset-Alarme werden pro Pool zusammengefasst, um Nachrichtenfluten bei vielen LXC-Datasets zu vermeiden. Die Benutzeroberfläche nennt besonders betroffene Datasets.
- Wenn die Dataset-Prüfung fehlschlägt, wird dies als eigener kritischer Alarm gemeldet.
- Die automatische Snapshot-Bereinigung bleibt **standardmäßig ausgeschaltet**. Die Schutzregeln der RC1 (letzter Snapshot jeder Art pro Dataset auch bei hohem Alter, Ausschluss manueller und bekannter Replikations-Snapshots) sind unverändert.

## Zustellung einrichten und nachprüfen

1. In Proxmox **Datacenter → Notifications** mindestens ein Ziel (Mail, Gotify oder Webhook) konfigurieren und sicherstellen, dass der Standard-Matcher bzw. ein passender Matcher die Ereignisse weiterleitet. Proxmox bietet eigene Testfunktionen für einzelne Ziele.
2. Auf dem Proxmox-Host ohne Änderungen: `zfsm emergency notify-check`.
3. Danach bewusst eine **Testnachricht** über das Proxmox-System auslösen: `zfsm emergency notify-test` (sendet eine echte Nachricht, löscht nichts). Im tatsächlichen Ziel, z. B. Gotify oder im E-Mail-Postfach, den Empfang kontrollieren.
4. Monitoring prüfen: `zfsm emergency status`, `systemctl is-active pve-zfs-manager-emergency.timer`, `journalctl -t zfsm-emergency -n 30 --no-pager`.

**Wichtig:** Ein erfolgreiches `notify-test` bedeutet, dass Proxmox den Versand angenommen hat. Nur die Bestätigung im Empfangskanal beweist, dass der Administrator erreicht wurde. Ein vorhandenes Ziel allein ist kein Zustellungsnachweis.

## Sicherheits-/Betriebshinweise

- Überwachung alle fünf Minuten; erneute Warnung standardmäßig alle 60 Minuten. Es wird nicht alle fünf Minuten eine neue Push-Nachricht erzeugt, solange der Versand erfolgreich war.
- Pool-Auslastung basiert auf `zpool list` (`ALLOC/SIZE`); Proxmox-Speicheranzeige und Dataset-Quotas können andere Werte zeigen. Diese werden separat dargestellt.
- `notify-check` ist rein lesend. `notify-test` versendet eine einmalige Testbenachrichtigung. `emergency preview` ist nur eine Vorschau. `emergency cleanup` und der aktivierte Automatikmodus sind **destruktiv** und bedürfen separater Freigabe.
- Die Perl-Proxmox-Benachrichtigungsfunktion muss auf PVE4 praktisch getestet werden. In der Offline-Testumgebung wurde nur das Aufrufprotokoll simuliert; eine reale Zustellung wurde noch nicht bestätigt.
- Bei Fehlern oder wenn noch kein Benachrichtigungsziel eingerichtet ist, erscheinen Hinweise in der ZFS-Manager-Oberfläche; das Systemjournal bleibt als lokaler Fallback erhalten.
