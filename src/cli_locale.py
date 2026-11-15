"""Translate human CLI output without changing structured JSON or safety answers."""
import builtins
from contextlib import contextmanager
import os
import sys

EN = {
 'ZFS Manager for Proxmox VE':'ZFS Manager for Proxmox VE',
 'Proxmox-Benachrichtigungsziele:':'Proxmox notification targets:',
 '| Versand muss mit notify-test geprueft werden':'| Delivery must be checked using notify-test',
 'WARNUNG (Poolalarm):':'WARNING (pool alert):', 'Automatische Bereinigung:':'Automatic cleanup:',
 'AUS (sicherer Standard)':'OFF (safe default)', 'AKTIV':'ENABLED', 'Bytes frei':'bytes free',
 'Keine sicher loeschbaren Snapshots':'No snapshots can be safely deleted', 'Abgebrochen':'Cancelled',
 'Test an Proxmox-Benachrichtigungssystem uebergeben. Empfang am Ziel kontrollieren!':'Test submitted to Proxmox notifications. Verify receipt at the destination!',
 'ZFS NOTFALL FEHLER:':'ZFS EMERGENCY ERROR:', 'Root erforderlich':'Root required', 'Nur root':'Root only',
 'Root-Rechte erforderlich':'Root privileges required', 'Keine Proxmox-Benachrichtigungsziele konfiguriert':'No Proxmox notification targets configured',
 'Interaktive Root-Shell erforderlich; kein stilles Loeschen':'Interactive root shell required; no silent deletion',
 'Keine Proxmox-Benachrichtigungsziele eingerichtet':'No Proxmox notification targets configured',
 'Kein Proxmox-Benachrichtigungsziel eingerichtet':'No Proxmox notification target configured',
 'Automatische Loeschung erfordert --ack-risk':'Automatic deletion requires --ack-risk',
 'Widerspruechliche Einstellungen':'Conflicting settings', 'Pool nicht vorhanden':'Pool does not exist',
 'Digest ungueltig':'Invalid digest', 'STOPP:':'STOP:', 'WARNUNG:':'WARNING:',
 'AutoSnap:':'AutoSnap:', ' Zeitpläne | ':' schedules | ', 'PRÜFEN':'REVIEW',
 'Replikation (nur Erkennung/Schutz):':'Replication (discovery/protection only):',
 ' Systemd-Units, ':' systemd units, ', ' native PVE-Aufträge':' native PVE jobs',
 ' Cron-Quellen':' cron sources', 'HINWEIS:':'NOTE:',
 'Keine Replikation wird verwaltet. Kein zusätzlicher Bereinigungstimer wird angelegt.':'Replication is not managed. No additional cleanup timer is created.',
 'Keine aktive AutoSnap-Zeitplanregel erkannt':'No active AutoSnap schedule detected',
 'Doppelte AutoSnap-Zeitpläne: ':'Duplicate AutoSnap schedules: ',
 'AutoSnap-Auftrag ohne eindeutige Art oder Aufbewahrung':'AutoSnap job has an ambiguous type or retention value',
 'Weitere Bereinigungsdienste erkannt; keine parallele Bereinigung anlegen':'Other cleanup services detected; do not create parallel cleanup',
 'PASS: Keine doppelten oder unklaren AutoSnap-Aufträge; keine Änderung nötig.':'PASS: No duplicate or ambiguous AutoSnap jobs; no change required.',
 'AutoSnap-Konflikte erkannt: Nur Cron-Regeln werden nach Auswahl deaktiviert.':'AutoSnap conflicts detected: only selected cron entries will be disabled.',
 'Vorher wird eine Sicherung erstellt. Snapshots und Replikationen bleiben unangetastet.':'A backup will be created first. Snapshots and replication remain untouched.',
 'Doppelte Aufbewahrungsart: ':'Duplicate retention type: ', ' | behalte ':' | keep ',
 ' | Benutzerregel':' | custom rule', '  0) Abbrechen (nichts ändern)':'  0) Cancel (no changes)',
 'Welche Regel behalten?':'Which rule should be kept?', 'Nicht eindeutig identifizierte AutoSnap-Aufträge:':'Ambiguous AutoSnap jobs:',
 ' | Art: ':' | type: ', ', Aufbewahrung: ':', retention: ',
 'Diesen unklaren Auftrag deaktivieren? [d=ja / a=abbrechen]: ':'Disable this ambiguous job? [d=yes / a=cancel]: ',
 'Vorgesehene Änderungen: ':'Planned changes: ', ' AutoSnap-Regel(n) in ':' AutoSnap rules in ', ' Datei(en) deaktivieren.':' files will be disabled.',
 'Jetzt mit Sicherung deaktivieren? [JA/N]: ':'Disable now with backup? [JA=yes / N=no]: ',
 'PASS: Duplikate deaktiviert; Sicherung: ':'PASS: Duplicates disabled; backup: ',
 'Keine gültige Auswahl; nichts verändert.':'Invalid choice; nothing changed.',
 'Vom Administrator abgebrochen; nichts verändert.':'Cancelled by administrator; nothing changed.',
 'Unbekannte Regel bleibt bestehen; keine Änderung.':'Unknown rule retained; no change.',
 'Nicht bestätigt; nichts verändert.':'Not confirmed; nothing changed.',
 'Keine Sicherungs-ID bei resolve angeben':'Do not specify a backup ID for resolve',
 'Keine Sicherungs-ID bei backups angeben':'Do not specify a backup ID for backups',
 'Aufruf: zfsm autosnap restore SICHERUNGS-ID':'Usage: zfsm autosnap restore BACKUP-ID',
 'PASS: Registrierte ZFS-Manager-Installation auf ':'PASS: Registered ZFS Manager installation updated to ',
 ' aktualisiert':'', 'Schon installiert; keine Änderung erforderlich':'Already installed; no change required',
 ' integriert. Proxmox: ':' integrated. Proxmox: ', ' installiert / übernommen. Sicherung: ':' installed / adopted. Backup: ',
 'PASS: PVE-Integrationsstruktur und Versionsschutz: ':'PASS: PVE integration structure and version protection: ',
 'FEHLER:':'ERROR:', 'Installation erfordert root-Rechte':'Installation requires root privileges',
 'Nicht unterstützte Hauptversion von Proxmox VE: ':'Unsupported Proxmox VE major version: ',
 'Voraussetzung fehlt: ':'Missing prerequisite: ', 'Datei fehlt oder ist Symlink: ':'Missing file or symbolic link: ',
 'Keine Sicherungen vorhanden':'No backups found', 'Sicherung erstellt:':'Backup created:',
 'Snapshot-Verbrauch':'Snapshot usage', 'frei':'free',
}

EN.update({'Originale Cron-Regeln wiederherstellen? [JA/N]: ': 'Restore original cron rules? [JA=yes / N=no]: ', ' hat nicht die geprüfte Original-Prüfsumme; Abbruch': ' does not match the verified stock checksum; stopped', 'API-Roundtrip fehlgeschlagen': 'API roundtrip failed', 'API-Route weicht von bekanntem Format ab': 'API route differs from the recognized format', 'API/Policy verändert, uninstall verweigert': 'API/policy changed; uninstall refused', 'Admin-Datei nicht root-owned': 'Admin file is not owned by root', 'Backend nicht aus einem geprüften Release': 'Backend is not from a verified release', 'Datei ist Symlink: ': 'File is a symbolic link: ', 'Deinstallation erfordert root-Rechte': 'Uninstallation requires root privileges', 'Doppelte AutoSnap-Aufträge; vor Installation prüfen: ': 'Duplicate AutoSnap jobs; review before installation: ', 'GUI-Block geändert; sichere Entfernung nicht möglich': 'GUI block changed; safe removal is not possible', 'GUI-Blockgrenzen verloren': 'GUI block boundaries lost', 'GUI-Drift-Roundtrip fehlgeschlagen': 'GUI drift roundtrip failed', 'GUI-Roundtrip fehlgeschlagen': 'GUI roundtrip failed', 'Gast-Policy nicht aus einem geprüften Release': 'Guest policy is not from a verified release', 'INTEGRATION FEHLT - automatische Pruefung/Reparatur vorgesehen: ': 'INTEGRATION MISSING - automatic check/repair scheduled: ', 'Installerzustand ist Symlink': 'Installer state is a symbolic link', 'Kein registrierter Installerzustand vorhanden': 'No registered installer state found', 'Kein reguläres File: ': 'Not a regular file: ', 'Keine bestehende Installation - zuerst installieren': 'No existing installation; install first', 'Keine registrierte Installation': 'No registered installation', 'Nodes.pm index-Route außerhalb Nodeinfo': 'Nodes.pm index route outside Nodeinfo', 'Nodes.pm passt nicht zur freigegebenen Struktur': 'Nodes.pm does not match the supported structure', 'Perl-Syntaxprüfung fehlgeschlagen: ': 'Perl syntax check failed: ', 'Proxmox GUI-Struktur unbekannt: ': 'Unknown Proxmox GUI structure: ', 'Proxmox-Dienst konnte nicht ': 'Proxmox service could not be ', 'Route existiert schon': 'Route already exists', 'Shell/System-Reihenfolge unerwartet': 'Unexpected Shell/System ordering', 'Symlink nicht erlaubt: ': 'Symbolic link not allowed: ', 'Teilintegration ohne bekannten Installerzustand': 'Partial integration without recognized installer state', 'Unbekannte API-Route vorhanden': 'Unknown API route found', 'Unbekannte API/Policy-Datei; nicht als eigene Installation erkannt': 'Unknown API/policy file; not recognized as an owned installation', 'Unbekannte Knotenmenü-Struktur': 'Unknown node menu structure', 'Unbekannte/ältere GUI-Erweiterung vorhanden; manuelle Migration erforderlich': 'Unknown/older GUI extension found; manual migration required', 'Ungültiger Installerzustand: Eigentumsnachweis fehlt': 'Invalid installer state: ownership evidence missing', 'Ungültiges Administratorkonfigurationsverzeichnis': 'Invalid administrator configuration directory', 'Unsichere Admin-Dateirechte': 'Unsafe admin file permissions', 'Vorgängerinstallation nicht eindeutig als ZFS Manager erkannt': 'Previous installation cannot be clearly identified as ZFS Manager', 'Vorhandenes API- oder Gast-Policy-Modul ohne bekannte Installation - Abbruch': 'Existing API or guest policy module without recognized installation; stopped', 'ZFS Manager schon eingebunden': 'ZFS Manager already integrated', 'ZFS-API-Route vorhanden, aber Format nicht bekannt': 'ZFS API route found but format is unknown', 'pveversion fehlt oder ist fehlerhaft: Kein Proxmox VE': 'pveversion missing or failed: not Proxmox VE', ' erledigt; Fehler bei ': ' completed; failure at ', '; bereits geloescht: ': '; already deleted: ', 'Abfrage fehlgeschlagen: ': 'Query failed: ', 'Gastdatentraeger im Rescue-Modus gesperrt': 'Guest disks are blocked in rescue mode', 'Gastzuordnung nicht lesbar': 'Guest mapping cannot be read', 'Gastzustand geaendert, keine Loeschung: ': 'Guest state changed; no deletion: ', 'Letzter Snapshot je Art bleibt geschuetzt: ': 'Last snapshot of each type remains protected: ', 'Maximal 15 Snapshots pro Bereinigung': 'Maximum 15 snapshots per cleanup', 'Nur root darf die Notfall-Konfiguration aendern': 'Only root may change emergency configuration', 'Pool nicht importiert oder unbekannt': 'Pool not imported or unknown', 'Snapshot ungueltig/geschuetzt: ': 'Snapshot invalid/protected: ', 'Snapshotname oder Poolzuordnung ungueltig': 'Invalid snapshot name or pool mapping', 'Teillöschung: ': 'Partial deletion: ', 'Unbekannte/mehrdeutige Gastzuordnung': 'Unknown/ambiguous guest mapping', 'Unbekannter Eintrag in der Notfall-Konfiguration': 'Unknown entry in emergency configuration', 'Ungueltige Dataset-Kapazitaetsdaten': 'Invalid dataset capacity data', 'Ungueltige Gastzuordnung': 'Invalid guest mapping', 'Ungueltige Liste in Notfall-Konfiguration: ': 'Invalid list in emergency configuration: ', 'Ungueltige Pool-Daten': 'Invalid pool data', 'Ungueltige Pool-Kapazitaet': 'Invalid pool capacity', 'Ungueltige Pool-Statistik': 'Invalid pool statistics', 'Ungueltige ZFS-Snapshot-Eigenschaften': 'Invalid ZFS snapshot properties', 'Ungueltige automatische Bereinigungsregel': 'Invalid automatic cleanup rule', 'Ungueltige numerische Dataset-Eigenschaft': 'Invalid numeric dataset property', 'Ungueltiger Datasetname oder Typ': 'Invalid dataset name or type', 'Ungueltiger Snapshot-Datensatz': 'Invalid snapshot record', 'Ungueltiger Zielwert (60-79%)': 'Invalid target value (60-79%)', 'Ungueltiges Dataset-Limit': 'Invalid dataset limit', 'Ungueltiges Wiederholungsintervall': 'Invalid repeat interval', 'Unsichere Notfall-Konfigurationsdatei (root:0600 erforderlich)': 'Unsafe emergency configuration file (root:0600 required)', 'Unsichere Warnzustandsdatei': 'Unsafe alert state file', 'Vorschau veraendert oder keine loeschbaren Snapshots: neue Vorschau erforderlich': 'Preview changed or no deletable snapshots; new preview required', 'Warnung konnte nicht ins Journal geschrieben werden': 'Unable to write warning to journal', 'Warnzustand ungueltig': 'Invalid alert state', 'Zu viele Datasets fuer die Kapazitaetspruefung': 'Too many datasets for capacity check', 'Zu viele Snapshots': 'Too many snapshots', '; Grund: ': '; reason: ', 'AutoSnap-Regel hat sich seit der Erkennung verändert: ': 'AutoSnap rule changed since discovery: ', 'AutoSnap-Regel hat sich verändert: ': 'AutoSnap rule changed: ', 'Binärdaten in Cron-Datei: ': 'Binary data in cron file: ', 'Cron-Datei nicht UTF-8: ': 'Cron file is not UTF-8: ', 'Cron-Datei seit Bereinigung geändert; sicherer Rückbau gestoppt: ': 'Cron file changed since cleanup; safe restore stopped: ', 'Cron-Datei zwischenzeitlich verändert: ': 'Cron file changed in the meantime: ', 'Cron-Quelle nicht automatisch änderbar: ': 'Cron source cannot be changed automatically: ', 'Datei geändert während des Rückbaus: ': 'File changed during restore: ', 'Fehlende oder verlinkte Cron-Datei: ': 'Missing or linked cron file: ', 'Keine Änderungen errechnet': 'No changes calculated', 'Nachprüfung meldet weitere Konflikte. Sicherung: ': 'Post-check reports further conflicts. Backup: ', 'Root-Crontab-Konflikt: nicht automatisch änderbar; manuelle Prüfung nötig.': 'Root crontab conflict: cannot be changed automatically; manual review required.', 'Rückbau fehlgeschlagen: ': 'Restore failed: ', 'Rückbau nicht bestätigt; nichts verändert': 'Restore not confirmed; nothing changed', 'Sicherung fehlt': 'Backup missing', 'Sicherung nicht gefunden oder verlinkt': 'Backup not found or linked', 'Sicherungsdatei ungültig': 'Invalid backup file', 'Sicherungsmanifest fehlt': 'Backup manifest missing', 'Sicherungsmanifest ungültig': 'Invalid backup manifest', 'Sicherungsverzeichnis hat unsichere Rechte': 'Backup directory has unsafe permissions', 'Sicherungsverzeichnis ist kein reguläres Verzeichnis': 'Backup directory is not a regular directory', 'Ungeeignete/zu große Cron-Datei: ': 'Unsuitable/oversized cron file: ', 'Ungültiger Sicherungsname': 'Invalid backup name', 'Unsichere Cron-Dateiquelle': 'Unsafe cron file source', 'Unsichere Eigentums-/Schreibrechte: ': 'Unsafe ownership/write permissions: ', 'Verlinktes Cron-Verzeichnis: ': 'Linked cron directory: ', 'Zeilennummer ungültig: ': 'Invalid line number: ', 'Änderung abgebrochen; Sicherung: ': 'Change cancelled; backup: ', 'Keine interaktive Konsole verfügbar. Keine Änderungen.\nInstaller direkt in einer Proxmox-Shell starten.': 'No interactive terminal available. No changes.\nStart the installer directly in a Proxmox shell.', 'GUI-Migration nicht reversibel': 'GUI migration is not reversible', 'Sicherung: ': 'Backup: ', '  Wiederherstellen: ': '  Restore: ', ' wiederhergestellt': ' restored', 'PASS: Originale Cron-Konfiguration aus ': 'PASS: Original cron configuration from '})

def english(text):
    # JSON carries API schemas/statuses unchanged, including nested string values.
    if text.lstrip().startswith(('{','[')): return text
    import re
    text=re.sub(r"GEFAHR: (\d+) Snapshots unwiderruflich loeschen\? 'JA': ",r"DANGER: permanently delete \1 snapshots? Enter 'JA' (yes): ",text)
    text=re.sub(r"Zur Bestätigung 'LOESCHEN (.*?)' eingeben: ",r"To confirm, enter 'LOESCHEN \1': ",text)
    for old,new in sorted(EN.items(),key=lambda x:-len(x[0])):
        text=text.replace(old,new)
    return text

@contextmanager
def display_language(lang):
    """Local output boundary; confirmation tokens remain exactly the same."""
    original_print=builtins.print
    original_input=builtins.input
    def translated_print(*args,**kw):
        original_print(*(english(str(x)) for x in args),**kw)
    def translated_input(prompt=''):
        return original_input(english(prompt))
    if lang=='en': builtins.print=translated_print;builtins.input=translated_input
    previous=os.environ.get('ZFSM_CLI_LANG')
    os.environ['ZFSM_CLI_LANG']=lang
    try: yield
    finally:
        builtins.print=original_print;builtins.input=original_input
        if previous is None: os.environ.pop('ZFSM_CLI_LANG',None)
        else: os.environ['ZFSM_CLI_LANG']=previous
