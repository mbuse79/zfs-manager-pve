"""Read-only per-node panel with auto discovery, grouped ZFS snapshots and retention display (0.5.1-test)."""
from previous_patch import HELPERS

START = '        // BEGIN PVE-ZFS-MANAGER-READONLY-v1.0.0-rc9\n'
END = '        // END PVE-ZFS-MANAGER-READONLY-v1.0.0-rc9\n'

BLOCK = START + r'''        // This panel is added only to PVE.node.Config. No monkeypatching.
        // Use the same language bundle loaded by Proxmox for this session.
        var zfsLanguage = (function () {
            // Proxmox selects the active GUI language via PVELangCookie,
            // otherwise uses the datacenter default exposed in Proxmox.defaultLang.
            var cookieLang = document.cookie.match(/(?:^|;\s*)PVELangCookie=([a-zA-Z_\-]+)/);
            if (cookieLang) { return cookieLang[1].replace('_', '-').toLowerCase(); }
            var scripts = document.querySelectorAll('script[src*="pve-lang-"]');
            for (var i = 0; i < scripts.length; i++) {
                var matched = String(scripts[i].src || '').match(/pve-lang-([a-zA-Z_\-]+)\.js/);
                if (matched) { return matched[1].replace('_', '-').toLowerCase(); }
            }
            return String((typeof Proxmox !== 'undefined' && Proxmox.defaultLang) || 'en')
                .replace('_', '-').toLowerCase();
        }());
        var zfsLocale = zfsLanguage.indexOf('de') === 0 ? 'de-DE' : 'en-US';
        var zfsTDe = {
            'Not available': 'Keine Angabe',
            'Storage and snapshot audit': 'Speicher- und Snapshot-Auswertung',
            'Pool capacity': 'Pool-Auslastung',
            'Snapshot used (sum)': 'Snapshot-Verbrauch (Summe)',
            'Top datasets by snapshot use': 'Datasets mit höchstem Snapshot-Verbrauch',
            'Snapshots': 'Snapshots',
            'Oldest': 'Ältester',
            'Retention overview': 'Aufbewahrungsübersicht',
            'Current keep': 'Aktuelle Aufbewahrung',
            'Observed': 'Vorhanden',
            'Above keep': 'Über Aufbewahrungswert',
            'Not configured': 'Nicht konfiguriert',
            'Disabled': 'Deaktiviert',
            'Warning': 'Warnung',
            'Critical': 'Kritisch',
            'Normal': 'Normal',
            'Snapshot used is not the same as space freed by deletion. No snapshots are changed.': 'Snapshot-Verbrauch entspricht nicht dem bei Löschung freigegebenen Speicher. Es werden keine Snapshots verändert.',
            'Numbers above keep are only a planning hint, not a deletion forecast.': 'Werte über der Aufbewahrung sind nur Planungshinweise, keine Löschprognose.',
            'Current observed snapshots for this interval: ': 'Aktuell vorhandene Snapshots dieses Intervalls: ',
            'Datasets with snapshots: ': 'Datasets mit Snapshots: ',
            'This changes the schedule, not existing snapshots immediately.': 'Dies ändert den Zeitplan, nicht unmittelbar bestehende Snapshots.',
            'No snapshots found': 'Keine Snapshots gefunden',
            'Free': 'Frei',
            'High pool occupancy': 'Hohe Pool-Auslastung',
            'Days': 'Tage',
            'Host snapshots will be permanently deleted.': 'Host-Snapshots werden endgültig gelöscht.',
            'Host rollback overwrites the current data.': 'Host-Rollback überschreibt den aktuellen Datenstand.',
            'Affected snapshots: ': 'Betroffene Snapshots: ',
            'Only this dataset; child datasets remain unchanged.': 'Nur dieses Dataset; untergeordnete Datasets bleiben unverändert.',
            'ZFS preview:': 'ZFS-Vorschau:',
            'Offline required': 'Offline erforderlich',
            'Only a signed offline request is saved here. The actual rollback runs exclusively in the rescue system.': 'Hier wird nur ein signierter Offline-Auftrag gespeichert. Der eigentliche Rollback erfolgt ausschließlich über das Rescue-System.',
            'Host snapshot deletion – preview': 'Host-Snapshot-Löschung – Vorschau',
            'Host rollback – preview': 'Host-Rollback – Vorschau',
            'CRITICAL HOST DELETION': 'KRITISCHE HOST-LÖSCHUNG',
            'CRITICAL HOST ROLLBACK': 'KRITISCHER HOST-ROLLBACK',
            'This operation can impair host recoverability.': 'Diese Aktion kann die Wiederherstellbarkeit des Hosts beeinträchtigen.',
            'Permanently delete host snapshots': 'Host-Snapshots endgültig löschen',
            'Prepare offline recovery request': 'Offline-Recovery-Auftrag vorbereiten',
            'Start host rollback permanently': 'Host-Rollback endgültig starten',
            'OFFLINE RECOVERY PREPARED': 'OFFLINE-RECOVERY VORBEREITET',
            'No rollback executed. Rescue system required. ': 'Kein Rollback ausgeführt. Rescue-System erforderlich. ',
            'Signed request: ': 'Signierter Auftrag: ',
            'See Proxmox host log': 'Siehe Proxmox-Host-Protokoll',
            'Offline request failed: ': 'Offline-Auftrag fehlgeschlagen: ',
            'Host preview failed: ': 'Host-Vorschau fehlgeschlagen: ',
            'Host rollback: additional critical warning; root or active mounts require offline recovery': 'Host-Rollback: zusätzliche rote Warnung; für Root/aktive Mounts nur Offline-Recovery',
            'Unknown': 'Unbekannt',
            'No known data errors': 'Keine bekannten Datenfehler',
            'Single-disk rollback': 'Einzelplatten-Rollback',
            'Only this disk:': 'Nur diese Festplatte:',
            'Snapshot:': 'Snapshot:',
            'Newer snapshots:': 'Neuere Snapshots:',
            'All other disks remain unchanged.': 'Alle anderen Festplatten bleiben unverändert.',
            'Data loss possible. Continue?': 'Datenverlust möglich. Fortfahren?',
            'disks': 'Datenträger',
            'guests found. ': 'Gäste erkannt. ',
            'Expanded rows and scroll position are preserved on refresh.': 'Aufklappzustand und Scrollposition bleiben beim Aktualisieren erhalten.',
            'ZFS Datasets': 'ZFS-Datasets',
            'Browse datasets and snapshots. Manage individual datasets.': 'Datasets und Snapshots durchsuchen. Einzelne Datasets verwalten.',
            'Actions': 'Aktionen',
            'VMs / LXC': 'VMs / LXC',
            " . ": " zurückgesetzt. ",
            " dataset rows displayed.": " Dataset-Zeilen angezeigt.",
            " datasets. ": " Datasets. ",
            " days": " Tage",
            " entries loaded.": " Einträge geladen.",
            " hr": " Std",
            " min": " Min",
            " newer snapshots will be DELETED by ZFS rollback -r. ": " neuere Snapshots werden durch ZFS rollback -r GELÖSCHT. ",
            " now?": " erstellen?",
            " per dataset? ": " pro Dataset ändern? ",
            " retention rules loaded.": " Aufbewahrungsregeln geladen.",
            " snapshots across ": " Snapshots auf ",
            " snapshots enter DELETE exactly:": " Snapshots exakt LÖSCHEN eingeben:",
            "15 minutes": "15 Minuten",
            "<br><b>Selected snapshot is preserved.</b><br><br>": "<br><b>Gewählter Snapshot bleibt bestehen.</b><br><br>",
            "<br><b>Snapshots permanently affected: ": "<br><b>Unwiderruflich betroffene Snapshots: ",
            "<br><b>Target:</b> ": "<br><b>Ziel:</b> ",
            "<br><br><b>Newer snapshots to delete:</b><br>": "<br><br><b>Zu löschende neuere Snapshots:</b><br>",
            "<br><br>The container must be stopped. The live data state will NOT be rolled back.": "<br><br>Der Gast muss gestoppt sein. Der aktive Datenstand wird dabei NICHT zurückgesetzt.",
            "<h3>Automatic Snapshot Retention</h3>": "<h3>Automatische Snapshot-Aufbewahrung</h3>",
            "<h3>Disks</h3>": "<h3>Festplatten</h3>",
            "<h3>ZFS Datasets and Snapshots</h3>": "<h3>ZFS-Datasets und Snapshots</h3>",
            "<h3>ZFS Pools</h3>": "<h3>ZFS-Pools</h3>",
            "<h4>Scrub and error status</h4>": "<h4>Scrub- und Fehlerstatus</h4>",
            "<p>Automatic detection every 60 seconds. Edit retention; ": "<p>Automatische Erkennung alle 60 Sekunden. Aufbewahrung bearbeiten; ",
            "<p>Changes apply per dataset. Nothing is deleted immediately. ": "<p>Änderungen gelten je Dataset. Es wird nicht sofort gelöscht. ",
            "<p>Click a dataset row to expand its snapshots. ": "<p>Auf eine Dataset-Zeile klicken, um Snapshots auszuklappen. ",
            "<p>Current zfs-auto-snapshot values, per dataset. ": "<p>Aktuelle Werte von zfs-auto-snapshot, je Dataset. ",
            "<p>The PVE status is not a complete SMART diagnosis.</p>": "<p>Der PVE-Zustand ersetzt keine vollständige SMART-Diagnose.</p>",
            "A reduction can delete older snapshots during later cron runs.</p>": "Bei späteren Cron-Läufen kann eine Verringerung ältere Snapshots entfernen.</p>",
            "API error: ": "API-Fehler: ",
            "Action completed. Refreshing snapshots.": "Aktion abgeschlossen. Snapshots werden aktualisiert.",
            "Action does not match the selected row.": "Aktion passt nicht zur ausgewählten Zeile.",
            "Action failed: ": "Aktion fehlgeschlagen: ",
            "Actions": "Aktionen",
            "Administrator required": "Nur Administratoren dürfen diese Einstellung ändern.",
            "Protected preview": "Geschützte Vorschau",
            "Protected dataset - read-only review. No live delete or rollback is allowed.": "Geschütztes Dataset – nur Sicherheitsvorschau. Keine Live-Löschung oder Live-Wiederherstellung.",
            "Actions are next to the dataset and snapshot rows. ": "Aktionen stehen direkt an den Dataset- und Snapshot-Zeilen. ",
            "Age": "Alter",
            "All data changes since the selected snapshot will be lost. ": "Alle Datenänderungen seit dem gewählten Snapshot gehen verloren. ",
            "Cancel": "Abbrechen",
            "Change snapshot retention": "Snapshot-Aufbewahrung ändern",
            "Changes are confirmed by type and take effect at the next scheduled run.</p>": "Änderungen werden je Typ bestätigt und erst beim nächsten Zeitplanlauf wirksam.</p>",
            "Continue to confirmation": "Weiter zur Bestätigung",
            "Count": "Anzahl",
            "Create": "Erstellen",
            "Create host dataset snapshot": "Host-Dataset-Snapshot erstellen",
            "Snapshot creation requires an authorized dataset and administrator rights": "Snapshot-Erstellung erfordert ein freigegebenes Dataset und Administratorrechte",
            "Create crash-consistent snapshot for mapped Proxmox guest disk": "Online-Snapshot für eindeutig zugeordneten Gast-Datenträger erstellen",
            "Created": "Erstellt",
            "Cron file": "Cron-Datei",
            "DELETE": "LÖSCHEN",
            "Delete snapshots": "Snapshots löschen",
            "Execute rollback": "Rollback ausführen",
            "I have reviewed the affected snapshots and confirm permanent deletion.": "Ich habe die betroffenen Snapshots geprüft und bestätige die endgültige Löschung.",
            "I have reviewed the consequences and confirm rollback with data loss.": "Ich habe die Auswirkungen geprüft und bestätige den Rollback mit Datenverlust.",
            "Daily": "Täglich",
            "Datasets without snapshots are also shown.</p>": "Auch Datasets ohne Snapshots werden aufgeführt.</p>",
            "Delete": "Löschen",
            "Delete only this snapshot": "Nur diesen Snapshot löschen",
            "Only this": "Nur diesen",
            "Select": "Auswählen",
            "Batch delete": "Auswahl löschen",
            "Partial group: only existing targets will be removed.": "Unvollständige Gruppe: Nur tatsächlich vorhandene Snapshots werden entfernt.",
            "Missing on these disks": "Auf diesen Datenträgern nicht vorhanden",
            "Exact targets to delete": "Genau diese Snapshots werden gelöscht",
            "Confirm incomplete snapshot group": "Unvollständige Snapshot-Gruppe bestätigen",
            "I understand missing snapshots will be skipped, and only listed existing snapshots deleted.": "Ich bestätige, dass fehlende Snapshots ausgelassen werden und nur die angezeigten vorhandenen Snapshots gelöscht werden.",
            "Incomplete snapshot group": "Unvollständige Snapshot-Gruppe",
            "Selected disks for this VM/LXC. Actions affect selected disks only.": "Ausgewählte Datenträger für diese VM/LXC. Aktionen betreffen nur die ausgewählten Datenträger.",
            "The VM/LXC must be stopped for a consistent grouped snapshot.": "Für einen gemeinsamen konsistenten Snapshot muss die VM/LXC gestoppt sein.",
            "The VM/LXC must be stopped. Deletion removes the selected and all newer snapshots per disk. Rollback discards changes after the target snapshot.": "Die VM/LXC muss gestoppt sein. Die Bereichslöschung entfernt den ausgewählten und alle neueren Snapshots je Datenträger. Rollback verwirft Änderungen seit dem Zielstand.",
            "Enter an existing snapshot name": "Vorhandenen Snapshot-Namen eingeben",
            "Open preview": "Vorschau öffnen",
            "Save selected disks together?": "Ausgewählte Datenträger gemeinsam sichern?",
            "newer snapshots": "neuere Snapshots",
            "Jointly delete": "Gemeinsam löschen",
            "Grouped rollback": "Gemeinsamer Rollback",
            "Data loss possible; this operation is not atomic. Continue?": "Datenverlust möglich; diese Aktion ist nicht atomar. Fortfahren?",
            "Action failed": "Aktion fehlgeschlagen",
            "Batch preview blocked: ": "Sammelvorschau gesperrt: ",
            "Snapshot": "Snapshot",
            "Preview": "Vorschau",
            "The current data will be overwritten.": "Aktuelle Daten werden überschrieben.",
            "Selected and newer snapshots will be deleted.": "Ausgewählte und neuere Snapshots werden gelöscht.",
            "Multiple disks are processed sequentially, not atomically.": "Mehrere Datenträger werden nacheinander bearbeitet, nicht atomar.",

            "Grouped snapshot": "Gemeinsamer Snapshot",
            "Create snapshot": "Snapshot erstellen",
            "Create a grouped snapshot for ": "Gemeinsamen Snapshot für ",
            " disks?": " Datenträger erstellen?",
            "Incomplete": "unvollständig",
            "Single disk": "Einzelplatte",
            "Affected disks": "Betroffene Datenträger",
            "Incomplete group: missing targets will be skipped.": "Unvollständige Gruppe: Fehlende Ziele werden übersprungen.",
            "Only selected existing snapshots will be deleted.": "Nur ausgewählte, vorhandene Snapshots werden gelöscht.",
            "Show details": "Details anzeigen",
            "Hide details": "Details ausblenden",
            "Critical host dataset": "Kritisches Host-Dataset",
            "Permanently delete selected host snapshots?": "Ausgewählte Host-Snapshots endgültig löschen?",
            "Selected snapshots": "Ausgewählte Snapshots",
            "Select snapshots by checkbox before deleting.": "Vor dem Löschen Snapshots über die Kästchen auswählen.",
            "Reclaimable space cannot be determined exactly before deletion.": "Tatsächlich freigebbarer Speicher ist vor dem Löschen nicht exakt bestimmbar.",
            "Non-atomic operation: a failure may leave partial deletions.": "Nicht atomare Aktion: Bei Fehlern sind Teillöschungen möglich.",
            "Delete only marked snapshots. Newer unselected snapshots remain.": "Nur markierte Snapshots löschen. Nicht ausgewählte neuere Snapshots bleiben erhalten.",
            "Newer snapshots remain": "Neuere Snapshots bleiben erhalten",
            "Disabled": "Deaktiviert",
            "Schedule disabled. Existing snapshots were preserved.": "Zeitplan deaktiviert. Vorhandene Snapshots bleiben erhalten.",
            "No new snapshots will be created for this interval. Existing snapshots will remain.": "Für dieses Intervall werden keine neuen Snapshots erstellt. Vorhandene Snapshots bleiben erhalten.",
            "Delete all snapshots from selection": "Alle Snapshots ab Auswahl löschen",
            "Delete selected snapshot and ALL newer snapshots; preview required": "Ausgewählten und ALLE neueren Snapshots löschen; Vorschau erforderlich",
            "CRITICAL ACTION - second confirmation": "KRITISCHE AKTION - zweite Sicherheitsbestätigung",
            "DANGER: irreversible snapshot deletion": "GEFAHR: Snapshots werden unwiderruflich gelöscht",
            "DANGER: rollback overwrites current data": "GEFAHR: Rollback überschreibt aktuelle Daten",
            "I understand this critical action and confirm again.": "Ich habe die kritischen Folgen verstanden und bestätige diese Aktion erneut.",
            "Permanently delete snapshots": "Snapshots endgültig löschen",
            "Confirm critical rollback": "Kritischen Rollback endgültig bestätigen",
            "Host snapshot may consume capacity; system datasets can be important. Create for ": "Ein Snapshot benötigt Speicherplatz. System-Datasets können kritisch sein. Snapshot erstellen für ",
            "No text input is required.": "Eine Texteingabe ist nicht erforderlich.",
            "This operation affects": "Diese Aktion betrifft",
            "snapshots; restoring them may be impossible.": "Snapshots; die Wiederherstellung kann unmöglich sein.",
            "The current guest data will be replaced by the snapshot state.": "Der aktuelle Datenstand des Gastes wird durch den Snapshot-Stand ersetzt.",
            "Deletion preview failed: ": "Löschvorschau fehlgeschlagen: ",
            "Device": "Gerät",
            "Errors": "Fehler",
            "External backup required.": "Externe Datensicherung erforderlich.",
            "Filter datasets / snapshots": "Dataset / Snapshot filtern",
            "Fragmentation": "Fragmentierung",
            "Free": "Frei",
            "Hourly": "Stündlich",
            "Incomplete deletion preview.": "Unvollständige Löschvorschau.",
            "Incomplete preview.": "Unvollständige Vorschau.",
            "Invalid retention value.": "Ungültiger Aufbewahrungswert.",
            "Keep": "Behalten",
            "Keep per dataset": "Behalten je Dataset",
            "Last scrub / scan": "Letzter Scrub / Scan",
            "Latest snapshot": "Neuester Snapshot",
            "Loading disks ...": "Festplatten werden geladen …",
            "Loading pools ...": "Pools werden geladen …",
            "Loading retention rules ...": "Aufbewahrungsregeln werden geladen …",
            "Loading snapshots ...": "Snapshots werden geladen …",
            "Model": "Modell",
            "Monthly": "Monatlich",
            "Yearly": "Jährlich",
            "Newer snapshots will be permanently deleted!": "Die neuere Snapshots werden unwiderruflich gelöscht!",
            "No": "Nein",
            "No SMART support": "Keine SMART-Unterstützung",
            "No snapshots": "Keine Snapshots",
            "None": "Keine",
            "OK": "OK",
            "Older snapshots may be deleted during future automatic runs.": "Bei den nächsten automatischen Läufen können dadurch ältere Snapshots gelöscht werden.",
            "Online creation is allowed for verified guest disks; delete and rollback require a stopped guest and a preview.": "Online-Erstellung erlaubt; Löschen und Rollback nur bei gestopptem Gast und nach Vorschau.",
            "Only approved guest datasets can be deleted": "Löschen ist nur für freigegebene Gast-Datasets erlaubt",
            "Only approved guest datasets can be rolled back": "Rollback ist nur für freigegebene Gast-Datasets erlaubt",
            "Please select a disk first.": "Bitte zuerst eine Festplatte auswählen.",
            "Preview failed: ": "Vorschau fehlgeschlagen: ",
            "ROLLBACK - all newer snapshots": "ROLLBACK – alle neuere Snapshots",
            "ROLLBACK PREVIEW - data loss!": "ROLLBACK-VORSCHAU – Datenverlust!",
            "Refresh": "Aktualisieren",
            "Retention ": "Aufbewahrung ",
            "Retention saved. The schedule is unchanged.": "Aufbewahrung gespeichert. Der Zeitplan bleibt unverändert.",
            "Rollback preview for this snapshot (LXC must be stopped)": "Rollback-Vorschau für genau diesen Snapshot (LXC muss gestoppt sein)",
            "SMART / Wear": "SMART / Verschleiß",
            "SMART data unavailable: ": "SMART-Daten nicht verfügbar: ",
            "SMART details for selected disk": "SMART-Details zur markierten Festplatte",
            "Save": "Speichern",
            "Saving failed: ": "Speichern fehlgeschlagen: ",
            "Action is not permitted for this dataset or user.": "Diese Aktion ist für das Dataset oder den Benutzer nicht freigegeben.",
            "Size": "Größe",
            "Proxmox Guest": "Proxmox-Gast",
            "Guest may be RUNNING. Snapshot is crash-consistent, not necessarily application-consistent. Create snapshot for ": "Der Gast darf laufen. Der Snapshot ist crash-konsistent, nicht automatisch anwendungskonsistent. Jetzt Snapshot für ",
            "To confirm enter ROLLBACK exactly. ": "Zum Bestätigen exakt ROLLBACK eingeben. ",
            "To delete all ": "Zum Löschen aller ",
            "Total": "Gesamt",
            "Type": "Typ",
            "Unavailable": "Nicht verfügbar",
            "Unexpected response format": "Unerwartetes Antwortformat",
            "Unknown error": "Unbekannter Fehler",
            " to ": " auf ",
            "Used": "Verwendet",
            "Virtual disk - no SMART": "Virtuelle Disk – kein SMART",
            "WARNING - delete entire snapshot history from this point onward": "ACHTUNG – gesamte Snapshot-Historie ab diesem Zeitpunkt löschen",
            "WARNING: Proxmox Guest will be rolled back to ": "ACHTUNG: Der Proxmox-Gast wird auf ",
            "Guest destructive actions require administrator permission, stopped guest and a user-bound preview; ensure a verified backup.": "Löschen und Rollback sind bis zu einer geprüften externen Sicherung und kurzzeitigen Root-Freigabe gesperrt.",
            "ZFS dry run (no changes):": "ZFS-Trockenlauf (keine Änderungen):",
            " newer snapshots will be removed by a bounded delete before rollback. ": " neuere Snapshots werden vor dem Rollback in einem begrenzten Bereich gelöscht. ",
            "Weekly": "Wöchentlich",
            "Yes": "Ja",
            "create guest snapshots online; delete and rollback only when the guest is stopped.</p>": "Snapshots für Gast-Datenträger online erstellen; Löschen und Rollback nur bei gestopptem Gast.</p>",
            "e.g. rpool/data or hourly": "z. B. rpool/data oder hourly",
            'Advanced: selected disks': 'Erweitert: einzelne Laufwerke',
            'VM / LXC / Snapshot / Disks': 'VM / LXC / Snapshot / Datenträger',
            'Disks': 'Datenträger',
            'Action': 'Aktion',
            'Delete': 'Löschen',
            'Loading guest data ...': 'Gastdaten werden geladen ...',
            'Show all datasets (including VM/LXC)': 'Alle Datasets anzeigen (einschließlich VM/LXC)',
            'Selected disks for this VM/LXC. Actions affect selected disks only.': 'Ausgewählte Laufwerke dieser VM/LXC. Aktionen betreffen nur markierte Laufwerke.',
            'I confirm this action.': 'Ich bestätige diese Aktion.',
            'Execute': 'Ausführen',
            'Proceed to second safety warning': 'Zur zweiten Sicherheitswarnung',
            'I have reviewed all affected snapshots and consequences.': 'Ich habe alle betroffenen Snapshots und Auswirkungen geprüft.',
            'VM / LXC – Snapshot management': 'VM / LXC – Snapshot-Verwaltung',
            'Guests, their disks and snapshots. Manage individual disks or the whole VM/LXC.': 'Gaeste mit ihren Datentraegern und Snapshots. Pro Festplatte oder gesamte VM (Rollback) arbeiten.',
            'Single-disk rollback not permitted: guest must be stopped and unprotected.': 'Einzelplatten-Rollback nicht freigegeben: Gast muss gestoppt und ungeschützt sein.',
            'Single-disk preview is invalid.': 'Vorschau der Einzelplatte ungültig.',
            'Single-disk rollback completed.': 'Einzelplatten-Rollback abgeschlossen.',
            'Rollback failed': 'Rollback fehlgeschlagen',
            'Preview failed': 'Vorschau fehlgeschlagen',
            'Administrator privileges required.': 'Administratorberechtigung erforderlich.',
            'Select a VM or LXC in the tree first.': 'Bitte zuerst VM oder LXC im Baum markieren.',
            'Select a guest.': 'Bitte einen Gast markieren.',
            'Not all disks are permitted for this action.': 'Nicht alle Datentraeger fuer diese Aktion freigegeben.',
            'Grouped snapshot created.': 'Gemeinsamer Snapshot erstellt.',
            'Preview incomplete.': 'Vorschau unvollstaendig.',
            'Action completed.': 'Aktion abgeschlossen.',
            'No disks selected.': 'Keine Laufwerke gewählt.',
            'Enter a valid existing snapshot name.': 'Gültigen vorhandenen Snapshot-Namen eingeben.',
            'Preview incomplete.': 'Vorschau unvollständig.',
            'Host safety preview incomplete': 'Host-Sicherheitsvorschau unvollständig',
};
        var zfsL = function (text) {
            if (zfsLanguage.indexOf('de') === 0) { return zfsTDe[text] || text; }
            // Our own English strings are canonical; only the German dictionary translates them.
            return text;
        };
        // Translate API values at the display boundary. Older installations may
        // still return legacy German fallback text; normalize both directions.
        // Preserve real zpool scan descriptions and unknown statuses verbatim.
        var zfsPoolStatusValue = function (value) {
            var raw = String(value == null ? '' : value).trim();
            var canonical = raw;
            if (!raw || raw === 'Keine Angabe' || raw === 'Not available' || raw === 'No information') {
                canonical = 'Not available';
            } else if (raw === 'Unbekannt' || raw === 'Unknown') {
                canonical = 'Unknown';
            } else if (raw === 'Keine bekannten Datenfehler' || raw === 'No known data errors') {
                canonical = 'No known data errors';
            }
            return safeZFSValue(zfsL(canonical));
        };
        var zfsmRetentionLabel = function(label) {
            var labels = {frequent:'15 minutes',hourly:'Hourly',daily:'Daily',
                          weekly:'Weekly',monthly:'Monthly',yearly:'Yearly'};
            return zfsL(labels[label] || String(label || ''));
        };
        // Read-only audit: derived from existing authenticated API payloads.
        // ZFS snapshot 'used' is NOT a prediction of reclaimable space.
        var zfsmCapacityReport = function (pools, snapshots, retention, nowSeconds) {
            var byDs = {}, perLabel = {}, labels = ['frequent','hourly','daily','weekly','monthly','yearly'];
            labels.forEach(function(label){perLabel[label]={count:0,ds:{}};});
            (snapshots || []).forEach(function(item){
                var dataset = String(item.dataset || ''), snap = String(item.snapshot || '');
                if (!dataset || !snap) {return;}
                var u=Number(item.used), t=Number(item.creation);
                if (!isFinite(u) || u<0) {u=0;}
                if (!isFinite(t) || t<0) {t=0;}
                if (!byDs[dataset]) {byDs[dataset]={dataset:dataset,count:0,used:0,oldest:0};}
                var row=byDs[dataset];row.count++;row.used+=u;
                if (t && (!row.oldest || row.oldest>t)) {row.oldest=t;}
                var m=/^zfs-auto-snap_(frequent|hourly|daily|weekly|monthly|yearly)-/.exec(snap);
                if (m) { var g=perLabel[m[1]];g.count++;g.ds[dataset]=(g.ds[dataset]||0)+1; }
            });
            var ranked=Object.keys(byDs).map(function(key){return byDs[key];}).sort(function(a,b){
                return (b.used-a.used)||(b.count-a.count)||(a.dataset<b.dataset?-1:a.dataset>b.dataset?1:0);
            });
            var policies=(retention||[]).map(function(item){
                var label=String(item.label||''), g=perLabel[label]||{count:0,ds:{}}, keep=Number(item.keep);
                var enabled=Number.isInteger(keep) && keep>0;
                var over=enabled?Object.keys(g.ds).reduce(function(sum,key){return sum+Math.max(0,g.ds[key]-keep);},0):null;
                return {label:label,keep:Number.isInteger(keep)?keep:null,
                    count:g.count,datasets:Object.keys(g.ds).length,aboveKeep:over};
            });
            var poolStats=(pools||[]).map(function(item){
                var size=Number(item.size),used=Number(item.alloc),free=Number(item.free);
                var cap=size>0&&isFinite(used)?100*used/size:0;
                return {name:String(item.name||''),capacity:cap,free:isFinite(free)&&free>0?free:0,
                    level:cap>=80?'critical':cap>=70?'warning':'normal'};
            });
            return {pools:poolStats,topDatasets:ranked.slice(0,8),datasets:ranked.length,
                snapshots:(snapshots||[]).length,policies:policies,generatedAt:nowSeconds||0};
        };
        var safeZFSDate = function (seconds) {
            var stamp = Number(seconds);
            if (!isFinite(stamp) || stamp <= 0) { return '—'; }
            try { return Ext.String.htmlEncode(new Date(stamp * 1000).toLocaleString(zfsLocale)); }
            catch (err) { return Ext.String.htmlEncode(new Date(stamp * 1000).toISOString().replace('T', ' ').slice(0, 19)); }
        };
        var zfsDialog = function (title, message, ok) {
            var safeTitle = title || 'ZFS Manager';
            var body = ok
                ? '<i class="fa fa-check-circle" style="color:#28b57a;font-size:18px;margin-right:10px"></i>' +
                    Ext.String.htmlEncode(String(message))
                : Ext.String.htmlEncode(String(message));
            Ext.Msg.show({title:safeTitle, message:body, buttons:Ext.Msg.OK,
                buttonText:{ok:zfsL('OK')}, icon: ok ? '' : Ext.Msg.ERROR});
        };
        var zfsSuccess = function (title, msg) {
            // Centered, non-modal, no button, closes automatically in five seconds.
            var content = '<i class="fa fa-check-circle" style="color:#28b57a;font-size:20px;margin-right:12px"></i>' +
                Ext.String.htmlEncode(String(msg));
            var popup = Ext.create('Ext.window.Window', {
                title:title || 'ZFS Manager', width:480, minHeight:100,
                bodyPadding:18, html:content, modal:false, closable:false,
                resizable:false, draggable:false, shadow:true,
                focusOnToFront:false,
            });
            popup.show();
            popup.center();
            Ext.defer(function () { if (!popup.destroyed) { popup.close(); } }, 5000);
        };
        var zfsError = function (title, msg) { zfsDialog(title, msg, false); };
        var zfsConfirm = function (title, msg, cb) {
            Ext.Msg.show({title:title, message:msg, buttons:Ext.Msg.YESNO,
                icon:Ext.Msg.QUESTION,
                buttonText:{yes:zfsL('Yes'),no:zfsL('No')}, fn:cb});
        };
        // High-risk actions require a SECOND independent opt-in after preview.
        // No dataset/snapshot names or command words are ever entered by hand.
        var zfsCriticalWarning = function (title, summaryHtml, confirmLabel, execute) {
            var dangerWindow = Ext.create('Ext.window.Window', {
                title:zfsL('CRITICAL ACTION - second confirmation'), width:690, height:345,
                modal:true, closable:true, layout:{type:'vbox',align:'stretch'},
                items:[
                    {xtype:'component', flex:1, scrollable:true, padding:18,
                     html:'<div role="alert" style="background:#fff1e6;border:3px solid #c62828;' +
                         'color:#801313;border-radius:6px;padding:18px;font-weight:600">' +
                         '<i class="fa fa-exclamation-triangle"></i> ' +
                         '<strong>'+safeZFSValue(title)+'</strong><br><br>' + summaryHtml + '</div>'},
                    {xtype:'checkbox',itemId:'zfs-final-ack',margin:'8 16 12 16',
                     boxLabel:zfsL('I understand this critical action and confirm again.'),
                     checked:false,listeners:{change:function(box,checked){
                        var win=box.up('window');
                        var btn=win && win.down('#zfs-critical-execute');
                        if (btn) {btn.setDisabled(!checked);}
                     }}}
                ],
                buttons:[
                    {text:zfsL('Cancel'),handler:function(){dangerWindow.close();}},
                    {text:confirmLabel,itemId:'zfs-critical-execute',disabled:true,
                     iconCls:'fa fa-exclamation-triangle',ui:'default',
                     style:{backgroundColor:'#b71c1c',borderColor:'#8c1515',color:'#ffffff',fontWeight:'bold'},
                     handler:function(btn){
                        var win=btn.up('window');
                        var ack=win && win.down('#zfs-final-ack');
                        if (!ack || ack.getValue() !== true) {return;}
                        btn.setDisabled(true);
                        win.close();
                        execute();
                     }}
                ],
            });
            dangerWindow.show();
        };
        if (caps.nodes['Sys.Audit']) {
            me.items.push({
                xtype: 'panel',
                title: 'ZFS Manager',
                iconCls: 'fa fa-database',
                itemId: 'zfsmanager-readonly',
                bodyPadding: 14,
                scrollable: true,
                layout: { type: 'vbox', align: 'stretch' },
                defaults: { margin: '0 0 9 0' },
                tbar: [{
                    text: zfsL("Refresh"), iconCls: 'fa fa-refresh',
                    handler: function (btn) {
                        var panel = btn.up('panel');
                        if (panel && panel.zfsRefreshReadOnly) { panel.zfsRefreshReadOnly(); }
                    },
                }],
                items: [
                    { xtype: 'component', html: '<h2>ZFS Manager</h2>' },
                    { xtype: 'component', html: zfsL("<h3>Disks</h3>") +
                        zfsL("<p>The PVE status is not a complete SMART diagnosis.</p>") },
                    {
                        xtype: 'grid', itemId: 'zfs-ro-disks', height: 95,
                        store: Ext.create('Ext.data.Store', {
                            fields: ['devpath', 'model', 'size', 'health', 'wearout'], data: [],
                        }),
                        columns: [
                            { text: zfsL("Device"), dataIndex: 'devpath', flex: 1, renderer: safeZFSValue },
                            { text: zfsL("Model"), dataIndex: 'model', flex: 2, renderer: safeZFSValue },
                            { text: zfsL("Size"), dataIndex: 'size', width: 100, renderer: zfsBytes },
                            { text: 'Status', dataIndex: 'health', width: 110, renderer: safeZFSValue },
                            { text: zfsL("SMART / Wear"), dataIndex: 'wearout', width: 230,
                              renderer: function (v, meta, record) {
                                  var model = String(record.get('model') || '');
                                  if (/QEMU|VMware|VBOX|Virtual/i.test(model)) {
                                      return zfsL("Virtual disk - no SMART");
                                  }
                                  if (v === null || v === undefined || String(v) === 'N/A') {
                                      return zfsL("Unavailable");
                                  }
                                  return safeZFSValue(v);
                              } },
                        ],
                    },
                    { xtype: 'button', text: zfsL("SMART details for selected disk"),
                      handler: function (btn) {
                          var v = btn.up('panel'); var grid = v.down('#zfs-ro-disks');
                          var record = grid && grid.getSelection && grid.getSelection()[0];
                          var disk = record && record.get('devpath');
                          if (!disk) { zfsError('ZFS Manager',zfsL("Please select a disk first.")); return; }
                          Proxmox.Utils.API2Request({
                              url:'/nodes/'+encodeURIComponent(nodename)+'/disks/smart',
                              method:'GET',params:{disk:disk},
                              success:function (res) {
                                  var data = res && res.result && res.result.data;
                                  Ext.Msg.show({title:'SMART '+safeZFSValue(disk),
                                      message:'<pre style="white-space:pre-wrap">'+
                                          safeZFSValue(JSON.stringify(data,null,2))+'</pre>',
                                      buttons:Ext.Msg.OK,buttonText:{ok:zfsL('OK')},icon:Ext.Msg.INFO});
                              },
                              failure:function (res) {
                                  zfsError('ZFS Manager',
                                      zfsL("SMART data unavailable: ")+
                                      safeZFSValue(res && res.htmlStatus || zfsL("No SMART support")));
                              },
                          });
                      } },
                    { xtype: 'component', itemId: 'zfs-ro-disks-status', html: zfsL("Loading disks ...") },
                    { xtype: 'component', html: zfsL("<h3>ZFS Pools</h3>") },
                    {
                        xtype: 'grid', disableSelection: true, itemId: 'zfs-ro-pools', height: 90,
                        store: Ext.create('Ext.data.Store', {
                            fields: ['name', 'health', 'size', 'alloc', 'free', 'frag'], data: [],
                        }),
                        columns: [
                            { text: 'Pool', dataIndex: 'name', flex: 1, renderer: safeZFSValue },
                            { text: 'Status', dataIndex: 'health', width: 125, renderer: safeZFSValue },
                            { text: zfsL("Total"), dataIndex: 'size', width: 110, renderer: zfsBytes },
                            { text: zfsL("Used"), dataIndex: 'alloc', width: 110, renderer: zfsBytes },
                            { text: zfsL("Free"), dataIndex: 'free', width: 110, renderer: zfsBytes },
                            { text: zfsL("Fragmentation"), dataIndex: 'frag', width: 130,
                              renderer: function (v) {
                                  return v === null || v === undefined ? '—' : safeZFSValue(v) + '%';
                              } },
                            { text: 'CAP', dataIndex: 'alloc', width: 82,
                              renderer: function (v, meta, record) {
                                  var alloc = Number(v);
                                  var size = Number(record.get('size'));
                                  if (!isFinite(alloc) || !isFinite(size) || size <= 0 || alloc < 0) {
                                      return '—';
                                  }
                                  // zpool list CAP is an integer; truncate rather than round.
                                  var cap = Math.max(0, Math.floor(100 * alloc / size));
                                  var color = cap >= 80 ? '#e24b4b' : (cap >= 70 ? '#d4ad30' : '#3db982');
                                  return '<span style="color:' + color + ';font-weight:700">' + cap + ' %</span>';
                              } },
                        ],
                    },
                    { xtype: 'component', itemId: 'zfs-ro-pools-status', html: zfsL("Loading pools ...") },
                    { xtype: 'component', html: zfsL("<h4>Scrub and error status</h4>") },
                    { xtype: 'grid', disableSelection: true, itemId: 'zfs-ro-scan', height: 110,
                      store: Ext.create('Ext.data.Store', {
                          fields:['name','state','scan','errors'], data: [],
                      }),
                      columns:[
                          {text:zfsL('Pool'),dataIndex:'name',width:150,renderer:safeZFSValue},
                          {text:zfsL('Status'),dataIndex:'state',width:140,renderer:zfsPoolStatusValue},
                          {text:zfsL("Last scrub / scan"),dataIndex:'scan',flex:2,renderer:zfsPoolStatusValue},
                          {text:zfsL("Errors"),dataIndex:'errors',flex:2,renderer:zfsPoolStatusValue},
                      ],
                    },

                    { xtype:'tabpanel', itemId:'zfs-snapshot-tabs', deferredRender:false, plain:true,
                      items:[
                        { xtype:'panel', title:zfsL('VMs / LXC'), border:false, bodyPadding:8, layout:'anchor', items:[
                    { xtype:'toolbar', items:[
                        {xtype:'button',text:zfsL('Advanced: selected disks'),handler:function(b){b.up('#zfsmanager-readonly').zfsGroupAction('create');}},
                        {xtype:'button',text:zfsL('Batch delete'),iconCls:'fa fa-scissors',handler:function(b){b.up('#zfsmanager-readonly').zfsmRunBatch('guest');}}
                    ]},
                    { xtype: 'component', cls:'zfsm-section-head', html: '<h3>' + zfsL('VM / LXC – Snapshot management') + '</h3><p>' + zfsL('Guests, their disks and snapshots. Manage individual disks or the whole VM/LXC.') + '</p>' },
                    {
                        xtype:'treepanel', itemId:'zfs-guest-snapshot-tree',
                        rootVisible:false, height:390, useArrows:true,
                        // One click on a snapshot row opens its individual disks.
                        // Keep native arrow clicks and action buttons independent.
                        viewConfig: {
                            toggleOnDblClick: false,
                            listeners: {
                                cellclick: function(treeView, cell, cellIndex, record, row, index, event) {
                                    if (!record || cellIndex !== 1 || (record.get('kind') !== 'guest' && record.get('kind') !== 'group-snapshot')) { return; }
                                    if (event && event.getTarget && event.getTarget(
                                        '.x-tree-expander, .x-btn, .x-btn-wrap, .x-btn-inner, .x-action-col-icon, button, input, a'
                                    )) { return; }
                                    if (record.isExpanded()) { record.collapse(); }
                                    else { record.expand(); }
                                }
                            }
                        },
                        listeners:{
                            itemexpand:function(node){var panel=this.up('#zfsmanager-readonly');if(!panel||!panel.zfsReadOnly)return;
                                var st=panel.zfsReadOnly,key=String(node.get('guestType')||'')+':'+String(node.get('guestId')||'');
                                if(node.get('kind')==='guest'){st.expandedGuests[key]=true;}
                                else if(node.get('kind')==='group-snapshot'&&node.parentNode){
                                  key=String(node.parentNode.get('guestType'))+':'+String(node.parentNode.get('guestId'));
                                  st.expandedGuestSnapshots[key+'@'+node.get('snapshot')]=true;}
                            },
                            itemcollapse:function(node){var panel=this.up('#zfsmanager-readonly');if(!panel||!panel.zfsReadOnly)return;
                                var st=panel.zfsReadOnly,key=String(node.get('guestType')||'')+':'+String(node.get('guestId')||'');
                                if(node.get('kind')==='guest'){st.expandedGuests[key]=false;}
                                else if(node.get('kind')==='group-snapshot'&&node.parentNode){
                                  key=String(node.parentNode.get('guestType'))+':'+String(node.parentNode.get('guestId'));
                                  st.expandedGuestSnapshots[key+'@'+node.get('snapshot')]=false;}
                            }
                        },
                        store:Ext.create('Ext.data.TreeStore', {
                            fields:['label','dataset','snapshot','kind','complete','guestId','snapCount','batchMarked'],
                            root:{expanded:true,children:[]}
                        }),
                        columns:[
                            {xtype:'checkcolumn',text:zfsL('Select'),width:72,dataIndex:'batchMarked',
                                listeners:{checkchange:function(col,rowIndex,checked){
                                    var tree=col.up('treepanel'), rec=tree.getStore().getAt(rowIndex);
                                    if(!rec || rec.get('kind')!=='group-snapshot'){
                                        if(rec)rec.set('batchMarked',rec.get('kind')==='snapshot' && !!(rec.parentNode && rec.parentNode.get('batchMarked')));
                                        return;
                                    }
                                    var owner=tree.up('#zfsmanager-readonly');
                                    var key=String(rec.parentNode.get('guestType'))+':'+String(rec.parentNode.get('guestId'))+'@'+String(rec.get('snapshot'));
                                    if(checked)owner.zfsmBatchGuest[key]={snapshot:rec.get('snapshot'),guestId:rec.parentNode.get('guestId'),guestType:rec.parentNode.get('guestType')};
                                    else delete owner.zfsmBatchGuest[key];
                                    // The group checkbox is the sole batch-selection authority.
                                    // Update children in place, without expanding/collapsing their parent.
                                    rec.eachChild(function(child){
                                        if (child.get('batchMarked') !== checked) child.set('batchMarked', checked);
                                    });
                                }}},
                            {xtype:'treecolumn',text:zfsL('VM / LXC / Snapshot / Disks'),dataIndex:'label',flex:3,
                                renderer:safeZFSValue},
                            {text:zfsL('Disks'),dataIndex:'complete',width:125,renderer:safeZFSValue},
                            {text:zfsL('Snapshots'),dataIndex:'snapCount',width:90,
                                renderer:function(v,meta,rec){return rec.get('kind')==='guest'?safeZFSValue(String(v||0)):'—';}},
                            {xtype:'widgetcolumn',text:zfsL('Action'),width:365,widget:{
                                xtype:'container',layout:{type:'hbox',align:'middle'},
                                items:[
                                    {xtype:'button',itemId:'guest-create',text:zfsL('Create'),iconCls:'fa fa-plus',ui:'default-toolbar',margin:'0 4 0 0',
                                        handler:function(b){
                                            var holder=b.up('container');
                                            var node=holder && holder.getWidgetRecord && holder.getWidgetRecord();
                                            var panel=b.up('#zfsmanager-readonly');
                                            if(node && panel && node.get('kind')==='guest') {
                                                panel.zfsGroupAction('create',{guest:node,direct:true});
                                            }
                                        }},
                                    {xtype:'button',itemId:'guest-delete',text:zfsL('Delete'),iconCls:'fa fa-trash',ui:'default-toolbar',margin:'0 4 0 0',
                                        handler:function(b){
                                            var holder=b.up('container');
                                            var node=holder && holder.getWidgetRecord && holder.getWidgetRecord();
                                            var panel=b.up('#zfsmanager-readonly');
                                            if(node && panel) {if(node.get('kind')==='group-snapshot'){panel.zfsGroupAction('delete',{snapshot:node.get('snapshot'),guest:node.parentNode,direct:true});}else if(node.get('kind')==='snapshot'){panel.zfsTestAction('delete',node);}}
                                        }},
                                    {xtype:'button',itemId:'guest-delete-exact',text:zfsL('Only this'),tooltip:zfsL('Delete only this snapshot'),
                                        iconCls:'fa fa-scissors',ui:'default-toolbar',margin:'0 4 0 0',
                                        handler:function(b){
                                            var holder=b.up('container');
                                            var node=holder && holder.getWidgetRecord && holder.getWidgetRecord();
                                            var panel=b.up('#zfsmanager-readonly');
                                            if(node && panel && node.get('kind')==='group-snapshot'){
                                                panel.zfsGroupAction('deleteExact',{snapshot:node.get('snapshot'),guest:node.parentNode,direct:true});
                                            }
                                        }},
                                    {xtype:'button',itemId:'guest-rollback',text:zfsL('Rollback'),iconCls:'fa fa-undo',ui:'default-toolbar',
                                        handler:function(b){
                                            var holder=b.up('container');
                                            var node=holder && holder.getWidgetRecord && holder.getWidgetRecord();
                                            var panel=b.up('#zfsmanager-readonly');
                                            if(node && panel) {if(node.get('kind')==='group-snapshot'){panel.zfsGroupAction('rollback',{snapshot:node.get('snapshot'),guest:node.parentNode,direct:true});}else if(node.get('kind')==='snapshot'){panel.zfsSingleDiskRollback(node);}}
                                        }}
                                ]},
                                onWidgetAttach:function(col,widget,rec){
                                    var kind=rec.get('kind'),ds=rec.get('dataset'),snap=rec.get('snapshot');
                                    var panel=col.up('#zfsmanager-readonly');
                                    var access=panel && panel.zfsReadOnly && panel.zfsReadOnly.guestAccess || {};
                                    var a=access[ds] || {};
                                    var admin=panel && panel.zfsReadOnly && panel.zfsReadOnly.isAdmin;
                                    widget.down('#guest-create').setHidden(kind!=='guest');
                                    widget.down('#guest-create').setDisabled(!admin);
                                    widget.down('#guest-delete').setHidden(kind!=='snapshot' && kind!=='group-snapshot');
                                    widget.down('#guest-delete-exact').setHidden(kind!=='group-snapshot');
                                    widget.down('#guest-delete-exact').setDisabled(!admin || !rec.get('allDisks'));
                                    widget.down('#guest-delete').setDisabled(!admin || (kind==='group-snapshot' ? !rec.get('allDisks') : !a.can_delete));
                                    widget.down('#guest-rollback').setHidden(kind!=='snapshot' && kind!=='group-snapshot');
                                    widget.down('#guest-rollback').setDisabled(!admin || (kind==='group-snapshot' ? !rec.get('allDisks') : !a.can_delete));
                                }
                            }
                        ]
                    },
                    {xtype:'component',itemId:'zfs-guest-status',html:zfsL('Loading guest data ...')},
                        ] },
                        { xtype:'panel', title:zfsL('ZFS-Datasets'), border:false, bodyPadding:8, layout:'anchor', items:[
                    { xtype: 'component', cls:'zfsm-section-head', html:zfsL('<h3>ZFS Datasets and Snapshots</h3>') },
                    { xtype:'checkbox', itemId:'zfs-show-all-datasets', boxLabel:zfsL('Show all datasets (including VM/LXC)'), checked:false,
                      listeners:{change:function(field){var owner=field.up('#zfsmanager-readonly');if(owner&&owner.zfsRenderTree){owner.zfsRenderTree();}}} },
                    {
                        xtype: 'textfield', itemId: 'zfs-ro-snapshot-filter',
                        fieldLabel: zfsL("Filter datasets / snapshots"), labelWidth: 190,
                        emptyText: zfsL("e.g. rpool/data or hourly"),
                        listeners: {
                            change: function (field) {
                                var panel = field.up('panel');
                                if (panel && panel.zfsRenderTree) { panel.zfsRenderTree(); }
                            },
                        },
                    },
                    {xtype:'toolbar',items:[{xtype:'button',text:zfsL('Batch delete'),iconCls:'fa fa-scissors',
                      handler:function(b){b.up('#zfsmanager-readonly').zfsmRunBatch('dataset');}}]},
                    {
                        xtype: 'treepanel', itemId: 'zfs-ro-snapshots',
                        disableSelection: true, height: 390, rootVisible: false, useArrows: true,
                        // ExtJS TreeView normally expands on double-click. Use the
                        // single cellclick event instead, independent of selection.
                        viewConfig: {
                            toggleOnDblClick: false,
                            listeners: {
                                cellclick: function (treeView, cell, cellIndex, record, row, index, event) {
                                    if (!record || record.get('snapshot')) { return; }
                                    // Do not interfere with native arrow toggle or any action control.
                                    if (event && event.getTarget && event.getTarget(
                                        '.x-tree-expander, .x-btn, .x-btn-wrap, .x-btn-inner, .x-action-col-icon, button, input, a'
                                    )) { return; }
                                    if (record.isExpanded()) { record.collapse(); }
                                    else { record.expand(); }
                                },
                            },
                        },
                        store: Ext.create('Ext.data.TreeStore', {
                            root: { expanded: true, children: [] },
                        }),
                        columns: [
                            {xtype:'checkcolumn',text:zfsL('Select'),width:72,dataIndex:'batchMarked',
                              listeners:{checkchange:function(col,rowIndex,checked){
                                var tree=col.up('treepanel'),rec=tree.getStore().getAt(rowIndex);
                                if(!rec || !rec.get('snapshot')){if(rec)rec.set('batchMarked',false);return;}
                                var owner=tree.up('#zfsmanager-readonly');
                                var key=String(rec.get('dataset'))+'@'+String(rec.get('snapshot'));
                                if(checked)owner.zfsmBatchDataset[key]={dataset:rec.get('dataset'),snapshot:rec.get('snapshot')};
                                else delete owner.zfsmBatchDataset[key];
                              }}},
                            { xtype: 'treecolumn', text: zfsL('Dataset / Snapshot'), dataIndex: 'label',
                              flex: 2, renderer: safeZFSValue },
                            { text: zfsL("Latest snapshot"), dataIndex: 'latestName',
                              flex: 2, renderer: function(v) { var raw=String(v == null ? '' : v).trim(); return safeZFSValue(!raw || raw === 'Keine Angabe' || raw === 'No information' || raw === 'Not available' ? zfsL('Not available') : v); } },
                            { text: zfsL("Created"), dataIndex: 'creation', width: 170,
                              renderer: function (v) {
                                  var n = Number(v);
                                  return isFinite(n) && n > 0
                                      ? safeZFSDate(n) : '—';
                              } },
                            { text: zfsL("Age"), dataIndex: 'creation', width: 100,
                              renderer: function (v) {
                                  var seconds = Math.max(0, Math.floor(Date.now() / 1000 - Number(v || 0)));
                                  if (!Number(v)) { return '—'; }
                                  if (seconds < 3600) { return Math.floor(seconds / 60) + zfsL(" min"); }
                                  if (seconds < 86400) { return Math.floor(seconds / 3600) + zfsL(" hr"); }
                                  return Math.floor(seconds / 86400) + zfsL(" days");
                              } },
                            { text: zfsL("Count"), dataIndex: 'count', width: 78, renderer: function(v){ return safeZFSValue(v === undefined || v === null ? '' : String(v)); } },
                            { text: zfsL("Used"), dataIndex: 'used', width: 105, renderer: zfsBytes, tooltip:zfsL('Reclaimable space cannot be determined exactly before deletion.') },
                            {
                                xtype: 'widgetcolumn', text: zfsL("Actions"), width: 340,
                                sortable: false, menuDisabled: true,
                                widget: {
                                    xtype: 'container', layout: { type: 'hbox', align: 'middle' },
                                    items: [
                                        {
                                            xtype: 'button', itemId: 'zfs-row-create', text: zfsL("Create"),
                                            iconCls: 'fa fa-plus', ui: 'default-toolbar',
                                            handler: function (btn) {
                                                var widget = btn.up('container');
                                                var tree = widget && widget.zfsTree;
                                                var owner = tree && tree.zfsOwnerView;
                                                if (owner && widget && widget.zfsRowRecord) {
                                                    owner.zfsTestAction('create', widget.zfsRowRecord);
                                                }
                                            },
                                        },
                                        {
                                            xtype: 'button', itemId: 'zfs-row-delete', text: zfsL("Delete"),
                                            iconCls: 'fa fa-trash', ui: 'default-toolbar', margin: '0 4 0 0',
                                            handler: function (btn) {
                                                var widget = btn.up('container');
                                                var tree = widget && widget.zfsTree;
                                                var owner = tree && tree.zfsOwnerView;
                                                if (owner && widget && widget.zfsRowRecord) {
                                                    owner.zfsTestAction('delete', widget.zfsRowRecord);
                                                }
                                            },
                                        },
                                        {
                                            xtype: 'button', itemId: 'zfs-row-delete-exact', text: zfsL('Only this'),
                                            iconCls: 'fa fa-scissors', ui: 'default-toolbar', margin: '0 4 0 0',
                                            handler: function (btn) {
                                                var widget = btn.up('container');
                                                var tree = widget && widget.zfsTree;
                                                var owner = tree && tree.zfsOwnerView;
                                                if (owner && widget && widget.zfsRowRecord) {
                                                    owner.zfsDatasetExactDelete(widget.zfsRowRecord);
                                                }
                                            },
                                        },
                                        {
                                            xtype: 'button', itemId: 'zfs-row-protected',
                                            text: zfsL('Protected preview'), iconCls: 'fa fa-lock',
                                            ui: 'default-toolbar', margin: '0 4 0 0',
                                            handler: function (btn) {
                                                var widget = btn.up('container');
                                                var tree = widget && widget.zfsTree;
                                                var owner = tree && tree.zfsOwnerView;
                                                var row = widget && widget.zfsRowRecord;
                                                if (!owner || !row || !owner.zfsReadOnly.isAdmin) { return; }
                                                var ds = String(row.get('dataset') || '');
                                                var snap = String(row.get('snapshot') || '');
                                                var base = '/nodes/' + encodeURIComponent(nodename) + '/zfsmanager-ro/';
                                                Proxmox.Utils.API2Request({
                                                    url:base+'protected-snapshot-review',method:'GET',
                                                    params:{dataset:ds,snapshot:snap},
                                                    success:function(res) {
                                                        var plan = res && res.result && res.result.data;
                                                        if (!plan || !Ext.isArray(plan.newer)) { return; }
                                                        var lines = Ext.Array.map(plan.newer, safeZFSValue).join('<br>');
                                                        Ext.Msg.show({title:zfsL('Protected preview'),
                                                            message:'<b>'+safeZFSValue(ds+'@'+snap)+'</b><br><br>'+
                                                              zfsL('Protected dataset - read-only review. No live delete or rollback is allowed.')+
                                                              '<br><br>'+safeZFSValue(String(plan.newer_count))+zfsL(' newer snapshots:')+'<br>'+lines,
                                                            buttons:Ext.Msg.OK,icon:Ext.Msg.WARNING});
                                                    },
                                                    failure:function(res) { zfsError('ZFS Manager',
                                                        zfsL('Preview failed: ')+safeZFSValue(res && res.htmlStatus || 'Unknown error')); }
                                                });
                                            },
                                        },
                                        {
                                            xtype: 'button', itemId: 'zfs-row-rollback', text: 'Rollback',
                                            iconCls: 'fa fa-undo', ui: 'default-toolbar',
                                            handler: function (btn) {
                                                var widget = btn.up('container');
                                                var tree = widget && widget.zfsTree;
                                                var owner = tree && tree.zfsOwnerView;
                                                if (owner && widget && widget.zfsRowRecord) {
                                                    owner.zfsTestAction('rollback', widget.zfsRowRecord);
                                                }
                                            },
                                        },
                                    ],
                                },
                                onWidgetAttach: function (column, widget, record) {
                                    // Column widgets are recycled by ExtJS. Update every button
                                    // from the currently bound row to avoid stale actions.
                                    widget.zfsRowRecord = record;
                                    widget.zfsTree = column.up('treepanel');
                                    var ds = String(record.get('dataset') || '');
                                    var snap = String(record.get('snapshot') || '');
                                    var access = (column.up('treepanel').zfsOwnerView.zfsReadOnly.guestAccess || {})[ds];
                                    var isAdmin = !!column.up('treepanel').zfsOwnerView.zfsReadOnly.isAdmin;
                                    var canWrite = !!caps.nodes['Sys.Modify'] && isAdmin && access && !access.protected;
                                    // Any inventoried filesystem/volume may take a snapshot,
                                    // subject to backend checks. Guest disks still use guest policy.
                                    var datasetType = String(record.get('datasetType') || '');
                                    var standalone = !access && (datasetType === 'filesystem' || datasetType === 'volume') &&
                                        !/(?:^|\/)(?:vm|subvol)-[0-9]+-disk-[0-9]+(?:-[A-Za-z0-9_.-]+)?$/.test(ds);
                                    var canCreate = !!caps.nodes['Sys.Modify'] && isAdmin && !snap &&
                                        (access ? !!access.can_create : standalone);
                                    var testDataset = !!access;
                                    var createBtn = widget.down('#zfs-row-create');
                                    var deleteBtn = widget.down('#zfs-row-delete');
                                    var exactBtn = widget.down('#zfs-row-delete-exact');
                                    var rollbackBtn = widget.down('#zfs-row-rollback');
                                    var protectedBtn = widget.down('#zfs-row-protected');
                                    if (protectedBtn) {
                                        protectedBtn.setHidden(true); // RC9: real host actions occupy their own buttons.
                                    }
                                    if (createBtn) {
                                        createBtn.setHidden(!!snap);
                                        createBtn.setDisabled(!canCreate);
                                        createBtn.setTooltip(canCreate
                                            ? (access ? zfsL("Create crash-consistent snapshot for mapped Proxmox guest disk")
                                                      : zfsL('Create host dataset snapshot'))
                                            : zfsL("Snapshot creation requires an authorized dataset and administrator rights"));
                                    }
                                    if (deleteBtn) {
                                        deleteBtn.setHidden(!snap);
                                        deleteBtn.setDisabled(!isAdmin || !caps.nodes['Sys.Modify'] ||
                                            !(access ? (canWrite && access.can_delete) : standalone));
                                        deleteBtn.setTooltip(access ? zfsL("Delete selected snapshot and ALL newer snapshots; preview required")
                                            : zfsL('CRITICAL ACTION - second confirmation'));
                                    }
                                    if (exactBtn) {
                                        exactBtn.setHidden(!snap);
                                        exactBtn.setDisabled(!isAdmin || !caps.nodes['Sys.Modify'] ||
                                            !(access ? (canWrite && access.can_delete) : standalone));
                                        exactBtn.setTooltip(zfsL('Delete only this snapshot') + ' - ' + zfsL('Newer snapshots remain'));
                                    }
                                    if (rollbackBtn) {
                                        rollbackBtn.setHidden(!snap);
                                        rollbackBtn.setDisabled(!isAdmin || !caps.nodes['Sys.Modify'] ||
                                            !(access ? (canWrite && access.can_rollback) : standalone));
                                        rollbackBtn.setTooltip(access
                                            ? zfsL("Rollback preview for this snapshot (LXC must be stopped)")
                                            : zfsL('Host rollback: additional critical warning; root or active mounts require offline recovery'));
                                    }
                                },
                            },
                        ],
                    },
                    { xtype: 'component', itemId: 'zfs-ro-snapshots-status', html: zfsL("Loading snapshots ...") },
                        ] }
                      ]
                    },

                    { xtype: 'component', html: '<h3>' + zfsL('Storage and snapshot audit') + '</h3>' +
                        '<p>' + zfsL('Snapshot used is not the same as space freed by deletion. No snapshots are changed.') + '</p>' },
                    { xtype: 'component', itemId: 'zfs-capacity-audit',
                      html: '<div class="zfs-audit-pending">—</div>' },
                    { xtype: 'component', html: zfsL("<h3>Automatic Snapshot Retention</h3>") +
                        zfsL("<p>Current zfs-auto-snapshot values, per dataset. ") +
                        zfsL("Changes are confirmed by type and take effect at the next scheduled run.</p>") },
                    // Six fixed retention rows require no nested ExtJS grid scroller.
                    // A simple themed table grows with its content; scrolling belongs to the outer panel.
                    { xtype: 'component', itemId: 'zfs-ro-retention',
                      html: '<div class="zfs-retention-pending"></div>' },
                    {
                        xtype: 'container', layout: { type: 'hbox', align: 'middle' },
                        hidden: !caps.nodes['Sys.Modify'],
                        items: [
                            {
                                xtype: 'combobox', itemId: 'zfs-retention-label', disabled:true, fieldLabel: zfsL("Type"),
                                labelWidth: 45, width: 245, editable: false, queryMode: 'local',
                                forceSelection: true, displayField: 'name', valueField: 'id',
                                store: Ext.create('Ext.data.Store', {
                                    fields: ['id', 'name'], data: [
                                        { id: 'frequent', name: zfsL("15 minutes") },
                                        { id: 'hourly', name: zfsL("Hourly") },
                                        { id: 'daily', name: zfsL("Daily") },
                                        { id: 'weekly', name: zfsL("Weekly") },
                                        { id: 'monthly', name: zfsL("Monthly") },
                                        { id: 'yearly', name: zfsL("Yearly") },
                                    ],
                                }),
                                value: 'frequent',
                                listeners: {
                                    change: function (field, value) {
                                        var panel = field.up('panel');
                                        if (panel && panel.zfsReadOnly) {
                                            var row = panel.zfsReadOnly.retention.find(function (r) {
                                                return r.label === value;
                                            });
                                            var count = panel.down('#zfs-retention-keep');
                                            if (row && count) { count.setValue(row.keep); }
                                        }
                                    },
                                },
                            },
                            { xtype: 'numberfield', itemId: 'zfs-retention-keep', disabled:true,
                              fieldLabel: zfsL("Keep"), labelWidth: 70, width: 205,
                              minValue: 0, maxValue: 999, allowDecimals: false,
                              allowBlank: false, hideTrigger: true, keyNavEnabled: false,
                              mouseWheelEnabled: false, value: 9, margin: '0 10 0 12' },
                            { xtype: 'button', itemId: 'zfs-retention-save', text: zfsL("Save"), disabled:true, iconCls: 'fa fa-save',
                              handler: function (btn) {
                                  var view = btn.up('panel');
                                  if (!view || !view.zfsReadOnly || view.zfsReadOnly.saving) { return; }
                                  if (!view.zfsReadOnly.isAdmin) { zfsError('ZFS Manager',zfsL('Administrator required')); return; }
                                  var typeField = view.down('#zfs-retention-label');
                                  var keepField = view.down('#zfs-retention-keep');
                                  if (!typeField || !keepField || !keepField.isValid()) { return; }
                                  var label = String(typeField.getValue() || '');
                                  var keep = Number(keepField.getValue());
                                  var row = view.zfsReadOnly.retention.find(function (item) {
                                      return item.label === label;
                                  });
                                  if (!row || !Number.isInteger(keep) || keep < 0 || keep > 999) {
                                      zfsError('ZFS Manager', zfsL("Invalid retention value.")); return;
                                  }
                                  if (row.keep === keep) { return; }
                                  var before = Number(row.keep);
                                  var footprint=zfsmCapacityReport(view.zfsReadOnly.pools,
                                      view.zfsReadOnly.snapshots,view.zfsReadOnly.retention,Math.floor(Date.now()/1000));
                                  var observed=footprint.policies.find(function(p){return p.label===label;});
                                  zfsConfirm(zfsL("Change snapshot retention"),
                                      zfsL('Current observed snapshots for this interval: ') +
                                      (view.zfsReadOnly.readySnapshots && observed?observed.count:'—') + '. ' +
                                      zfsL('This changes the schedule, not existing snapshots immediately.') + '<br>' +
                                      zfsL("Retention ") + Ext.String.htmlEncode(zfsmRetentionLabel(label)) +
                                      ': ' + before + zfsL(' to ') + keep + zfsL(" per dataset? ") +
                                      (keep === 0
                                          ? zfsL("No new snapshots will be created for this interval. Existing snapshots will remain.")
                                          : zfsL("Older snapshots may be deleted during future automatic runs.")),
                                      function (answer) {
                                          if (answer !== 'yes' || view.destroyed) { return; }
                                          view.zfsReadOnly.saving = true;
                                          btn.setDisabled(true);
                                          Proxmox.Utils.API2Request({
                                              url: '/nodes/' + encodeURIComponent(nodename) +
                                                  '/zfsmanager-ro/retention-update',
                                              method: 'POST',
                                              params: {
                                                  label: label, keep: keep, expected_keep: before,
                                                  confirm: 'RETENTION:' + label + ':' + before + ':' + keep,
                                              },
                                              success: function () {
                                                  if (!view.destroyed) {
                                                      zfsSuccess('ZFS Manager',
                                                          (keep === 0
                                                              ? zfsL("Schedule disabled. Existing snapshots were preserved.")
                                                              : zfsL("Retention saved. The schedule is unchanged.")));
                                                      view.zfsRefreshReadOnly();
                                                  }
                                              },
                                              failure: function (response) {
                                                  if (!view.destroyed) {
                                                      zfsError('ZFS Manager',
                                                          zfsL("Saving failed: ") +
                                                          safeZFSValue(response && response.htmlStatus || zfsL("Unknown error")));
                                                  }
                                              },
                                              callback: function () {
                                                  view.zfsReadOnly.saving = false;
                                                  if (!view.destroyed) { btn.setDisabled(false); }
                                              },
                                          });
                                      });
                              },
                            },
                        ],
                    },
                    { xtype: 'component', html: zfsL("<p>Changes apply per dataset. Nothing is deleted immediately. ") +
                        zfsL("A reduction can delete older snapshots during later cron runs.</p>") },
                    { xtype: 'component', itemId: 'zfs-ro-retention-status',
                      html: zfsL("Loading retention rules ...") },
                ],
                listeners: {
                    afterrender: function (view) {
                        view.zfsmBatchGuest={};view.zfsmBatchDataset={};
                        view.zfsmRunBatch=function(kind){
                            var items=Object.keys(kind==='guest'?view.zfsmBatchGuest:view.zfsmBatchDataset).map(function(k){
                                return (kind==='guest'?view.zfsmBatchGuest:view.zfsmBatchDataset)[k];
                            });
                            if(!items.length){zfsError('ZFS Manager',zfsL('Select snapshots by checkbox before deleting.'));return;}
                            var first=items[0],guest=kind==='guest',snapshots=items.map(function(i){return String(i.snapshot);});
                            if(guest && items.some(function(i){return i.guestId!==first.guestId || i.guestType!==first.guestType;})){
                                zfsError('ZFS Manager',zfsL('Select snapshots from one VM/LXC only.'));return;
                            }
                            if(!guest && items.some(function(i){return i.dataset!==first.dataset;})){
                                zfsError('ZFS Manager',zfsL('Select snapshots from one dataset only.'));return;
                            }
                            var params={snapshots:Ext.encode(snapshots),allow_partial:1};
                            var scope='host';
                            if(guest){
                                var drives=Object.keys(view.zfsReadOnly.guestAccess||{}).filter(function(ds){var a=view.zfsReadOnly.guestAccess[ds];return String(a.vmid)===String(first.guestId) && String(a.guest)===String(first.guestType);});
                                params.selection=Ext.encode(drives);
                                scope='guest';
                            } else {
                                params.dataset=String(first.dataset);
                                if(view.zfsReadOnly.guestAccess[params.dataset]){
                                    scope='guest';params.selection=Ext.encode([params.dataset]);delete params.dataset;
                                }
                            }
                            var base='/nodes/'+encodeURIComponent(nodename)+'/zfsmanager-ro/'+scope+'-snapshot-batch-exact';
                            Proxmox.Utils.API2Request({url:base+'-preview',method:'GET',params:params,success:function(r){
                                var plan=r&&r.result&&r.result.data;
                                if(!plan || !plan.token || plan.newer_preserved!==1){zfsError('ZFS Manager',zfsL('Preview incomplete.'));return;}
                                var missing=(plan.missing_targets||[]),targets=(plan.targets||[]);
                                if(!targets.length){zfsError('ZFS Manager',zfsL('Preview incomplete.'));return;}
                                var diskSet={};
                                targets.forEach(function(t){diskSet[t.dataset]=true;});
                                var summary=zfsL('Selected snapshots')+': '+snapshots.length+'<br>'+
                                    zfsL('Affected disks')+': '+Object.keys(diskSet).length+'<br>'+
                                    (missing.length?zfsL('Incomplete group: missing targets will be skipped.')+'<br>':'')+
                                    zfsL('Only selected existing snapshots will be deleted.');
                                var detailed=zfsL('Exact targets to delete')+':\n'+
                                    targets.map(function(t){return t.dataset+'@'+t.snapshot;}).join('\n')+
                                    (missing.length?'\n\n'+zfsL('Missing on these disks')+':\n'+missing.join('\n'):'');
                                var submitBatch=function(){
                                    if(view.zfsReadOnly.saving)return;
                                    view.zfsReadOnly.saving=true;
                                    var post=Ext.apply({},params);
                                    post.token=plan.token;post.confirm='DELETE-BATCH-EXACT';
                                    if(scope==='host'||missing.length)post.critical_ack=1;
                                    Proxmox.Utils.API2Request({url:base,method:'POST',params:post,
                                        success:function(){view.zfsReadOnly.saving=false;view.zfsmBatchGuest={};view.zfsmBatchDataset={};view.zfsRefreshReadOnly();},
                                        failure:function(e){view.zfsReadOnly.saving=false;zfsError('ZFS Manager',safe(e&&e.htmlStatus||zfsL('Unknown error')));}
                                    });
                                };
                                var win=Ext.create('Ext.window.Window',{
                                    title:zfsL('Batch delete'),modal:true,resizable:false,width:470,
                                    bodyPadding:12,layout:{type:'vbox',align:'stretch'},
                                    items:[{xtype:'component',html:summary},
                                        {xtype:'button',text:zfsL('Show details'),margin:'10 0 0 0',
                                            handler:function(btn){
                                                var detail=win.down('#zfsm-batch-details');
                                                detail.setHidden(!detail.isHidden());
                                                btn.setText(zfsL(detail.isHidden()?'Show details':'Hide details'));
                                                win.updateLayout();
                                            }},
                                        {xtype:'textarea',itemId:'zfsm-batch-details',hidden:true,
                                            readOnly:true,value:detailed,height:155,margin:'6 0 0 0'}],
                                    buttons:[{text:zfsL('Cancel'),handler:function(){win.close();}},
                                        {text:zfsL('Delete'),handler:function(){
                                            if(scope==='host'){
                                                Ext.Msg.confirm(zfsL('Critical host dataset'),
                                                    zfsL('Permanently delete selected host snapshots?'),
                                                    function(choice){if(choice==='yes'){win.close();submitBatch();}});
                                            }else{win.close();submitBatch();}
                                        }}]
                                });
                                win.show();
                            },failure:function(e){zfsError('ZFS Manager',zfsL('Batch preview blocked: ')+safe(e&&e.htmlStatus||zfsL('Preview failed')));}});
                        };
                        view.zfsReadOnly = {
                            pools: [], disks: [],
                            datasets: [], snapshots: [], retention: [], scan: [],
                            readyDatasets: false, readySnapshots: false, refreshing: false, saving: false,
                        };
                        var state = view.zfsReadOnly;
                        state.guestAccess = {};
                        state.isAdmin = false;
                        state.expandedDatasets = {};
                        state.expandedGuests = {};
                        state.expandedGuestSnapshots = {};
                        var safe = function (s) { return safeZFSValue(s); };
                        var gridLoad = function (id, rows) {
                            var item = view.down('#' + id);
                            if (item && !item.destroyed) { item.getStore().loadData(rows); }
                        };
                        var renderCapacity = function () {
                            var component=view.down('#zfs-capacity-audit');
                            if (!component || component.destroyed) {return;}
                            var audit=zfsmCapacityReport(state.pools,state.snapshots,state.retention,
                                Math.floor(Date.now()/1000));
                            var enc=function(v){return Ext.String.htmlEncode(String(v==null?'':v));};
                            var cell='style="padding:4px 8px;border-bottom:1px solid rgba(128,128,128,.16);text-align:left"';
                            var html='<div style="font-size:12px">';
                            html+='<b>'+enc(zfsL('Pool capacity'))+'</b><div style="display:flex;gap:14px;flex-wrap:wrap;margin:6px 0 12px">';
                            audit.pools.forEach(function(p){
                                var color=p.level==='critical'?'#dc4646':p.level==='warning'?'#dca62e':'#32a66c';
                                html+='<span>'+enc(p.name)+': <strong style="color:'+color+'">'+p.capacity.toFixed(1)+'%</strong> ('+
                                    enc(zfsL('Free'))+' '+enc(zfsBytes(p.free))+')</span>';
                            });
                            html+='</div><b>'+enc(zfsL('Top datasets by snapshot use'))+'</b>';
                            html+='<table style="width:100%;border-collapse:collapse;margin:6px 0 14px"><thead><tr>'+
                                '<th '+cell+'>Dataset</th><th '+cell+'>'+enc(zfsL('Snapshots'))+'</th>'+
                                '<th '+cell+'>'+enc(zfsL('Snapshot used (sum)'))+'</th><th '+cell+'>'+enc(zfsL('Oldest'))+'</th></tr></thead><tbody>';
                            if (!audit.topDatasets.length) {html+='<tr><td '+cell+' colspan="4">'+enc(zfsL('No snapshots found'))+'</td></tr>';}
                            audit.topDatasets.forEach(function(r){
                                var age=r.oldest?Math.max(0,Math.floor((audit.generatedAt-r.oldest)/86400))+' '+zfsL('Days'):'—';
                                html+='<tr><td '+cell+'>'+enc(r.dataset)+'</td><td '+cell+'>'+r.count+'</td><td '+cell+'>'+
                                    enc(zfsBytes(r.used))+'</td><td '+cell+'>'+enc(age)+'</td></tr>';
                            });
                            html+='</tbody></table><b>'+enc(zfsL('Retention overview'))+'</b>';
                            html+='<table style="width:100%;border-collapse:collapse;margin:6px 0 4px"><thead><tr>'+
                                '<th '+cell+'>'+enc(zfsL('Type'))+'</th><th '+cell+'>'+enc(zfsL('Current keep'))+'</th>'+
                                '<th '+cell+'>'+enc(zfsL('Observed'))+'</th><th '+cell+'>'+enc(zfsL('Above keep'))+'</th></tr></thead><tbody>';
                            audit.policies.forEach(function(r){
                                var count=r.keep===null?zfsL('Not configured'):r.keep===0?zfsL('Disabled'):r.keep;
                                html+='<tr><td '+cell+'>'+enc(zfsmRetentionLabel(r.label))+'</td><td '+cell+'>'+enc(count)+'</td><td '+cell+'>'+r.count+
                                    '</td><td '+cell+'>'+(r.aboveKeep===null?'—':r.aboveKeep)+'</td></tr>';
                            });
                            html+='</tbody></table><div style="opacity:.75">'+enc(zfsL('Numbers above keep are only a planning hint, not a deletion forecast.'))+'</div></div>';
                            component.update(html);
                        };
                        var renderRetention = function (rows) {
                            var panel = view.down('#zfs-ro-retention');
                            if (!panel || panel.destroyed) { return; }
                            var enc = function (value) {
                                return Ext.String.htmlEncode(String(value === null || value === undefined ? '' : value));
                            };
                            var cell = 'style="padding:5px 8px;border-bottom:1px solid rgba(128,128,128,.16);text-align:left;"';
                            var html = '<table style="width:100%;table-layout:fixed;border-collapse:collapse;">' +
                                '<colgroup><col style="width:20%"><col style="width:20%"><col style="width:60%"></colgroup>' +
                                '<thead><tr><th ' + cell + '>' + enc(zfsL("Type")) + '</th><th ' + cell + '>' +
                                enc(zfsL("Keep per dataset")) + '</th><th ' + cell + '>' + enc(zfsL("Cron file")) + '</th></tr></thead><tbody>';
                            rows.forEach(function (record) {
                                var count = Number(record.keep);
                                var shown = count === 0 ? '0 (' + zfsL("Disabled") + ')' : String(count);
                                html += '<tr><td ' + cell + '>' + enc(zfsmRetentionLabel(record.label)) + '</td><td ' + cell + '>' +
                                    enc(shown) + '</td><td ' + cell + '>' + enc(record.file) + '</td></tr>';
                            });
                            panel.update(html + '</tbody></table>');
                        };
                        // The row widgets call the owner of this particular tree.
                        // Never operate on whichever row happens to be selected.
                        var zfsTree = view.down('#zfs-ro-snapshots');
                        if (zfsTree) { zfsTree.zfsOwnerView = view; }
                        view.zfsRenderTree = function () {
                            var tree = view.down('#zfs-ro-snapshots');
                            if (!tree || tree.destroyed) { return; }
                            var filter = view.down('#zfs-ro-snapshot-filter');
                            var search = filter ? String(filter.getValue() || '').toLowerCase().trim() : '';
                            // Preserve user expansion choices through the 60-second refresh.
                            var previousRoot = tree.getRootNode();
                            if (previousRoot) {
                                previousRoot.eachChild(function (node) {
                                    state.expandedDatasets[String(node.get('dataset'))] = node.isExpanded();
                                });
                            }
                            var mapping = {};
                            var datasetTypes = {};
                            Ext.Array.each(state.datasets, function (ds) {
                                if (ds.name) {
                                    mapping[String(ds.name)] = [];
                                    datasetTypes[String(ds.name)] = String(ds.type || '');
                                }
                            });
                            Ext.Array.each(state.pools, function (pool) {
                                if (pool.name && !mapping[String(pool.name)]) { mapping[String(pool.name)] = []; }
                            });
                            Ext.Array.each(state.snapshots, function (snap) {
                                if (!snap.dataset || !snap.snapshot) { return; }
                                var name = String(snap.dataset);
                                if (!mapping[name]) { mapping[name] = []; }
                                mapping[name].push(snap);
                            });
                            var children = [];
                            var showAllField=view.down('#zfs-show-all-datasets');
                            var showAll=!!(showAllField && showAllField.getValue());
                            Object.keys(mapping).sort().forEach(function (dataset) {
                                if (!showAll && state.guestAccess && state.guestAccess[dataset]) { return; }
                                var sorted = mapping[dataset].slice().sort(function (a, b) {
                                    return Number(b.creation || 0) - Number(a.creation || 0);
                                });
                                var matching = !search || dataset.toLowerCase().indexOf(search) >= 0;
                                var shown = sorted.filter(function (snap) {
                                    return matching || String(snap.snapshot).toLowerCase().indexOf(search) >= 0;
                                });
                                if (search && !matching && !shown.length) { return; }
                                var latest = sorted.length ? sorted[0] : null;
                                var used = sorted.reduce(function (total, snap) {
                                    return total + (Number(snap.used) || 0);
                                }, 0);
                                children.push({
                                    dataset: dataset, datasetType: datasetTypes[dataset] || '', snapshot: null, label: dataset, latestName: latest ? String(latest.snapshot) : zfsL("No snapshots"),
                                    creation: latest ? latest.creation : 0,
                                    count: sorted.length, used: used, leaf: false,
                                    expanded: !!search || state.expandedDatasets[dataset] === true,
                                    children: shown.map(function (snap) {
                                        return {
                                            dataset: dataset, datasetType: datasetTypes[dataset] || '',
                                            snapshot: String(snap.snapshot),
                                            label: String(snap.snapshot), latestName: '',
                                            creation: snap.creation, count: '', used: snap.used, batchMarked:!!view.zfsmBatchDataset[dataset+'@'+snap.snapshot],
                                            leaf: true,
                                        };
                                    }),
                                });
                            });
                            tree.getStore().setRoot({ expanded: true, children: children });
                            var info = view.down('#zfs-ro-snapshots-status');
                            if (info) {
                                info.update(state.snapshots.length + zfsL(" snapshots across ") +
                                    Object.keys(mapping).length + zfsL(" datasets. ") +
                                    children.length + zfsL(" dataset rows displayed."));
                            }
                        };
                        // A disk rollback uses the existing guarded group endpoint with a
                        // one-element selection. It must not invoke the old whole-guest API.
                        // Dataset tree exact deletion uses the same guest endpoint as the VM/LXC tree.
                        // Host datasets must use a separately guarded, double-confirmed route.
                        view.zfsDatasetExactDelete = function(record) {
                            if(!record || !record.get || state.saving || !state.isAdmin || !caps.nodes['Sys.Modify'])return;
                            var ds=String(record.get('dataset')||'');
                            var snap=String(record.get('snapshot')||'');
                            if(!/^[A-Za-z0-9_.:-]{1,128}$/.test(snap))return;
                            var access=state.guestAccess[ds];
                            var datasetType=String(record.get('datasetType')||'');
                            var standalone=!access && (datasetType==='filesystem'||datasetType==='volume') &&
                                !/(?:^|\/)(?:vm|subvol)-[0-9]+-disk-[0-9]+(?:-[A-Za-z0-9_.-]+)?$/.test(ds);
                            if(access && (access.protected || !access.can_delete))return;
                            if(!access && !standalone)return;
                            var guest=!!access;
                            var selection=Ext.encode([ds]);
                            var route=guest?'guest-group-delete-exact':'host-snapshot-delete-exact';
                            var base='/nodes/'+encodeURIComponent(nodename)+'/zfsmanager-ro/'+route;
                            var params=guest?{selection:selection,snapshot:snap}:{dataset:ds,snapshot:snap};
                            Proxmox.Utils.API2Request({url:base+'-preview',method:'GET',params:params,
                                success:function(r){
                                    var plan=r&&r.result&&r.result.data;
                                    if(!plan || !plan.token || plan.newer_preserved!==1 ||
                                        String(plan.snapshot)!==snap || String(plan.dataset)!==ds){
                                        zfsError('ZFS Manager',zfsL('Preview incomplete.'));return;
                                    }
                                    var text='<b>'+safe(ds+'@'+snap)+'</b><br>'+zfsL('Newer snapshots remain')+
                                        '<br><b>'+zfsL('DANGER: irreversible snapshot deletion')+'</b>';
                                    // First confirmation: show the exact affected snapshot and dry run.
                                    Ext.Msg.confirm(zfsL('Delete only this snapshot'),text,function(answer){
                                        if(answer!=='yes')return;
                                        var doPost=function(){
                                            if(state.saving)return;
                                            state.saving=true;
                                            var data=Ext.apply({},params);
                                            data.token=plan.token;
                                            data.confirm=(guest?'DELETE-EXACT:':'HOST-DELETE-EXACT:')+snap;
                                            if(!guest)data.critical_ack=1;
                                            Proxmox.Utils.API2Request({url:base,method:'POST',params:data,
                                                success:function(){state.saving=false;zfsSuccess('ZFS Manager',zfsL('Action completed.'));view.zfsRefreshReadOnly();},
                                                failure:function(e){state.saving=false;zfsError('ZFS Manager',safe(e&&e.htmlStatus||zfsL('Unknown error')));}
                                            });
                                        };
                                        if(guest){doPost();return;}
                                        // Host/root datasets always require a second independent warning.
                                        Ext.Msg.confirm(zfsL('CRITICAL ACTION - second confirmation'),
                                            text+'<br>'+zfsL('I understand this critical action and confirm again.'),
                                            function(ack){if(ack==='yes')doPost();});
                                    });
                                },failure:function(e){zfsError('ZFS Manager',safe(e&&e.htmlStatus||zfsL('Preview failed')));}
                            });
                        };
                        view.zfsSingleDiskRollback = function(record) {
                            if(!record || record.get('kind')!=='snapshot')return;
                            var ds=String(record.get('dataset')||'');
                            var snap=String(record.get('snapshot')||'');
                            var a=state.guestAccess[ds];
                            if(!state.isAdmin || !caps.nodes['Sys.Modify'] || !a || !a.can_delete){
                                zfsError('ZFS Manager',zfsL('Single-disk rollback not permitted: guest must be stopped and unprotected.'));return;
                            }
                            if(!/^[A-Za-z0-9_.:-]{1,128}$/.test(snap))return;
                            var base='/nodes/'+encodeURIComponent(nodename)+'/zfsmanager-ro/guest-group-rollback';
                            var chosen=Ext.encode([ds]);
                            Proxmox.Utils.API2Request({url:base+'-preview',method:'GET',
                                params:{selection:chosen,snapshot:snap},
                                success:function(r){
                                    var plan=r&&r.result&&r.result.data;
                                    if(!plan || !plan.token || !Ext.isArray(plan.disks) || plan.disks.length!==1 || String(plan.disks[0].dataset)!==ds){
                                        zfsError('ZFS Manager',zfsL('Single-disk preview is invalid.'));return;
                                    }
                                    Ext.Msg.confirm(zfsL('Single-disk rollback'),
                                        '<b>'+zfsL('Only this disk:')+'</b> '+safe(ds)+'<br><b>'+zfsL('Snapshot:')+'</b> '+safe(snap)+
                                        '<br>'+zfsL('Newer snapshots:')+' '+Number(plan.disks[0].newer_count||0)+
                                        '<br><b>'+zfsL('All other disks remain unchanged.')+'</b><br>'+zfsL('Data loss possible. Continue?'),
                                        function(answer){
                                            if(answer!=='yes' || state.saving)return;
                                            state.saving=true;
                                            Proxmox.Utils.API2Request({url:base,method:'POST',
                                                params:{selection:chosen,snapshot:snap,token:plan.token,confirm:'GROUP-ROLLBACK:'+snap},
                                                success:function(){state.saving=false;zfsSuccess('ZFS Manager',zfsL('Single-disk rollback completed.'));view.zfsRefreshReadOnly();},
                                                failure:function(res){state.saving=false;zfsError('ZFS Manager',safe(res&&res.htmlStatus||zfsL('Rollback failed')));}
                                            });
                                        });
                                },failure:function(res){zfsError('ZFS Manager',safe(res&&res.htmlStatus||zfsL('Preview failed')));}
                            });
                        };
                        view.zfsGroupAction = function(action, options) {
                            options=options||{};
                            if (!state.isAdmin || !caps.nodes['Sys.Modify']) {
                                zfsError('ZFS Manager',zfsL('Administrator privileges required.'));return;
                            }
                            var tree=view.down('#zfs-guest-snapshot-tree');
                            var rec=options.guest || (tree && tree.getSelectionModel().getSelection()[0]);
                            if(!rec) {zfsError('ZFS Manager',zfsL('Select a VM or LXC in the tree first.'));return;}
                            while (rec && rec.get('kind')!=='guest') {rec=rec.parentNode;}
                            if (!rec) {zfsError('ZFS Manager',zfsL('Select a guest.'));return;}
                            var guestId=String(rec.get('guestId')||'');
                            var guestType=String(rec.get('guestType')||'');
                            // Resolve disks independently from tree layout; also works with zero snapshots.
                            var drives=Object.keys(state.guestAccess||{}).filter(function(ds){
                                var a=state.guestAccess[ds];
                                return String(a.vmid||'')===guestId && String(a.guest||'')===guestType;
                            }).sort().map(function(ds){
                                return {get:function(k){return k==='dataset'?ds:
                                    k==='label'?String(state.guestAccess[ds].drive||'Disk')+' – '+ds:null;}};
                            });
                            if(!drives.length) {return;}
                            var checks=Ext.Array.map(drives,function(d){
                                var a=state.guestAccess[d.get('dataset')]||{};
                                return {xtype:'checkbox',boxLabel:Ext.String.htmlEncode(String(d.get('label'))),
                                    inputValue:d.get('dataset'),checked:true,disabled:!!a.protected};
                            });
                            var title={create:zfsL('Grouped snapshot'),delete:zfsL('Jointly delete'),rollback:zfsL('Rollback')}[action];
                            // Simple path: use every eligible disk. Advanced path keeps selective checkbox dialog.
                            if(options.direct){
                                var selected=Ext.Array.map(Ext.Array.filter(drives,function(d){
                                    var a=state.guestAccess[d.get('dataset')]||{};
                                    return !a.protected && (action==='create' ? a.can_create :
                                        (action==='delete' || action==='deleteExact') ? a.can_delete : a.can_rollback);
                                }),function(d){return d.get('dataset');});
                                if(selected.length!==drives.length){
                                    zfsError('ZFS Manager',zfsL('Not all disks are permitted for this action.'));return;
                                }
                                if(action==='create'){
                                    Ext.Msg.confirm(zfsL('Create snapshot'),zfsL('Create a grouped snapshot for ') + selected.length + zfsL(' disks?'),function(choice){
                                        if(choice!=='yes')return;
                                        if(state.saving)return;state.saving=true;
                                        Proxmox.Utils.API2Request({url:'/nodes/'+encodeURIComponent(nodename)+'/zfsmanager-ro/guest-group-create',method:'POST',
                                            params:{selection:Ext.encode(selected),confirm:'CREATE-GROUP'},
                                            success:function(){state.saving=false;zfsSuccess('ZFS Manager',zfsL('Grouped snapshot created.'));view.zfsRefreshReadOnly();},
                                            failure:function(r){state.saving=false;zfsError('ZFS Manager',safe(r&&r.htmlStatus||zfsL('Unknown error')));}
                                        });
                                    });return;
                                }
                                var snapName=String(options.snapshot||'');
                                if(!/^[A-Za-z0-9_.:-]{1,128}$/.test(snapName))return;
                                var base='/nodes/'+encodeURIComponent(nodename)+'/zfsmanager-ro/';
                                var endpoint=action==='delete'?'guest-group-delete':action==='deleteExact'?'guest-group-delete-exact':'guest-group-rollback';
                                Proxmox.Utils.API2Request({url:base+endpoint+'-preview',method:'GET',
                                    params:{selection:Ext.encode(selected),snapshot:snapName},
                                    success:function(r){
                                        var plan=r&&r.result&&r.result.data;
                                        if(!plan||!plan.token||!Ext.isArray(plan.disks)){
                                            zfsError('ZFS Manager',zfsL('Preview incomplete.'));return;
                                        }
                                        var details=Ext.Array.map(plan.disks,function(d){
                                            return safe(d.dataset)+(action==='deleteExact' ? ' – '+zfsL('Newer snapshots remain') : ' – '+Number(d.newer_count||0)+' '+zfsL('newer snapshots'));
                                        }).join('<br>');
                                        Ext.Msg.confirm((action==='deleteExact'?zfsL('Delete only this snapshot'):action==='delete'?zfsL('Jointly delete'):zfsL('Grouped rollback')),
                                            '<b>'+safe(snapName)+'</b><br>'+details+'<br><b>'+zfsL('Data loss possible; this operation is not atomic. Continue?')+'</b>',function(choice){
                                            if(choice!=='yes'||state.saving)return;state.saving=true;
                                            Proxmox.Utils.API2Request({url:base+endpoint,method:'POST',
                                                params:{selection:Ext.encode(selected),snapshot:snapName,token:plan.token,
                                                    confirm:(action==='deleteExact'?'DELETE-EXACT:':action==='delete'?'GROUP-DELETE:':'GROUP-ROLLBACK:')+snapName},
                                                success:function(){state.saving=false;zfsSuccess('ZFS Manager',zfsL('Action completed.'));view.zfsRefreshReadOnly();},
                                                failure:function(e){state.saving=false;zfsError('ZFS Manager',safe(e&&e.htmlStatus||zfsL('Action failed')));}
                                            });
                                        });
                                    },failure:function(r){zfsError('ZFS Manager',safe(r&&r.htmlStatus||zfsL('Preview failed')));}
                                });return;
                            }
                            var win=Ext.create('Ext.window.Window',{
                                title:title,modal:true,width:650,layout:'anchor',bodyPadding:14,
                                items:[
                                    {xtype:'component',html:zfsL('Selected disks for this VM/LXC. Actions affect selected disks only.')},
                                    {xtype:'checkboxgroup',itemId:'drives',columns:1,vertical:true,items:checks},
                                    {xtype:'textfield',itemId:'snapname',fieldLabel:'Snapshot',labelWidth:110,
                                        hidden:action==='create',emptyText:zfsL('Enter an existing snapshot name')},
                                    {xtype:'component',html:action==='create' ? zfsL('The VM/LXC must be stopped for a consistent grouped snapshot.') :
                                        zfsL('The VM/LXC must be stopped. Deletion removes the selected and all newer snapshots per disk. Rollback discards changes after the target snapshot.')}
                                ],
                                buttons:[{text:zfsL('Cancel'),handler:function(){win.close();}},
                                    {text:action==='create'?zfsL('Create'):zfsL('Open preview'),handler:function(){
                                        var boxes=win.down('#drives').query('checkbox');
                                        var selection=Ext.Array.map(Ext.Array.filter(boxes,function(c){return c.checked && !c.disabled;}),function(c){return c.inputValue;});
                                        if(!selection.length){zfsError('ZFS Manager',zfsL('No disks selected.'));return;}
                                        var snapshot=action==='create'?'':String(win.down('#snapname').getValue()||'').trim();
                                        if(action!=='create' && !/^[A-Za-z0-9_.:-]{1,128}$/.test(snapshot)) {
                                            zfsError('ZFS Manager',zfsL('Enter a valid existing snapshot name.'));return;
                                        }
                                        win.close();
                                        var base='/nodes/'+encodeURIComponent(nodename)+'/zfsmanager-ro/';
                                        var encoded=Ext.encode(selection);
                                        var endpoint=action==='create'?'guest-group-create':
                                            action==='delete'?'guest-group-delete':action==='deleteExact'?'guest-group-delete-exact':'guest-group-rollback';
                                        var submit=function(token){
                                            if(state.saving){return;}
                                            state.saving=true;
                                            Proxmox.Utils.API2Request({url:base+endpoint,method:'POST',
                                                params:action==='create'?{selection:encoded,confirm:'CREATE-GROUP'}:
                                                    {selection:encoded,snapshot:snapshot,token:token,
                                                        confirm:(action==='delete'?'GROUP-DELETE:':'GROUP-ROLLBACK:')+snapshot},
                                                success:function(){state.saving=false;zfsSuccess('ZFS Manager',zfsL('Action completed.'));view.zfsRefreshReadOnly();},
                                                failure:function(r){state.saving=false;zfsError('ZFS Manager',safe(r&&r.htmlStatus||zfsL('Unknown error')));}
                                            });
                                        };
                                        if(action==='create'){
                                            Ext.Msg.confirm(title,selection.length+' '+zfsL('Save selected disks together?'),function(v){if(v==='yes')submit(null);});
                                            return;
                                        }
                                        Proxmox.Utils.API2Request({url:base+endpoint+'-preview',method:'GET',
                                            params:{selection:encoded,snapshot:snapshot},
                                            success:function(r){
                                                var plan=r&&r.result&&r.result.data;
                                                if(!plan||!plan.token||!Ext.isArray(plan.disks)) {
                                                    zfsError('ZFS Manager',zfsL('Preview incomplete.'));return;
                                                }
                                                var affected=Ext.Array.map(plan.disks,function(p){
                                                    return safe(p.dataset)+' – '+Number(p.newer_count||0)+' '+zfsL('newer snapshots');
                                                }).join('<br>');
                                                var dlg=Ext.create('Ext.window.Window',{
                                                    title:title+' – '+zfsL('Preview'),modal:true,width:680,height:390,
                                                    layout:{type:'vbox',align:'stretch'},
                                                    items:[{xtype:'component',flex:1,scrollable:true,padding:15,
                                                        html:'<b>Snapshot:</b> '+safe(snapshot)+'<br><br>'+affected+
                                                            '<br><br><b>'+ (action==='rollback'?zfsL('The current data will be overwritten.'):zfsL('Selected and newer snapshots will be deleted.'))+'</b><br>'+ 
                                                            zfsL('Multiple disks are processed sequentially, not atomically.')},
                                                        {xtype:'checkbox',itemId:'ack',margin:'0 14 10 14',boxLabel:zfsL('I confirm this action.')}],
                                                    buttons:[{text:zfsL('Cancel'),handler:function(){dlg.close();}},
                                                        {text:zfsL('Execute'),handler:function(){if(!dlg.down('#ack').checked)return;dlg.close();submit(plan.token);}}]
                                                });dlg.show();
                                            },failure:function(r){zfsError('ZFS Manager',safe(r&&r.htmlStatus||zfsL('Preview failed')));}
                                        });
                                    }}]
                            });win.show();
                        };
                        view.zfsRenderGuests = function () {
                            var tree=view.down('#zfs-guest-snapshot-tree');
                            if (!tree || tree.destroyed) {return;}
                            var oldRoot=tree.getRootNode();
                            if(oldRoot){oldRoot.eachChild(function(g){
                                var key=String(g.get('guestType')||'')+':'+String(g.get('guestId')||'');
                                state.expandedGuests[key]=g.isExpanded();
                                g.eachChild(function(sn){
                                    if(sn.get('kind')==='group-snapshot'){
                                        state.expandedGuestSnapshots[key+'@'+String(sn.get('snapshot')||'')]=sn.isExpanded();
                                    }
                                });
                            });}
                            var byGuest={};
                            Object.keys(state.guestAccess || {}).forEach(function(ds){
                                var a=state.guestAccess[ds];
                                var k=String(a.guest||'')+':'+String(a.vmid||'');
                                if(!a.guest || !a.vmid) {return;}
                                if(!byGuest[k]) {byGuest[k]={kind:a.guest,id:a.vmid,name:a.display_name||'',disks:[]};}
                                byGuest[k].disks.push(a);
                            });
                            var snapshotIndex={};
                            (state.snapshots||[]).forEach(function(snap){
                                if(!snapshotIndex[snap.dataset]) {snapshotIndex[snap.dataset]=[];}
                                snapshotIndex[snap.dataset].push(snap);
                            });
                            var treeScroll=tree.getView() && tree.getView().getScrollY ? tree.getView().getScrollY() : 0;
                            var roots=[];
                            Object.keys(byGuest).sort().forEach(function(k){
                                var g=byGuest[k], disks=g.disks.sort(function(a,b){
                                    return String(a.drive).localeCompare(String(b.drive));
                                });
                                var names={};
                                disks.forEach(function(d){
                                    (snapshotIndex[d.dataset]||[]).forEach(function(sn){
                                        names[sn.snapshot]=(names[sn.snapshot]||0)+1;
                                    });
                                });
                                // Each snapshot is a parent; its children are the actual disk snapshots.
                                // This permits a single-disk operation without touching other disks.
                                var groups=Object.keys(names).map(function(n){
                                    var members=[],created=0;
                                    disks.forEach(function(d){
                                        (snapshotIndex[d.dataset]||[]).forEach(function(sn){
                                            if(String(sn.snapshot)!==n)return;
                                            created=Math.max(created,Number(sn.creation||0));
                                            members.push({kind:'snapshot',dataset:d.dataset,snapshot:n,
                                                label:String(d.drive||'Disk')+' – '+d.dataset,
                                                complete:zfsL('Single disk'),leaf:true,allDisks:false,batchMarked:false});
                                        });
                                    });
                                    var all=members.length===disks.length && disks.every(function(d){
                                        return !d.other_disks && Number(d.disk_count||disks.length)===disks.length;
                                    });
                                    members.forEach(function(m){m.batchMarked=!!view.zfsmBatchGuest[k+'@'+n];});
                                    return {kind:'group-snapshot',batchMarked:!!view.zfsmBatchGuest[k+'@'+n],snapshot:n,dataset:null,
                                        label:n+(all?'':' – '+zfsL('Incomplete')),complete:members.length+' / '+disks.length,
                                        allDisks:all,created:created,expanded:state.expandedGuestSnapshots[k+'@'+n]===true,children:members};
                                }).sort(function(a,b){return b.created-a.created || a.snapshot.localeCompare(b.snapshot);});
                                roots.push({kind:'guest',dataset:null,snapshot:null,
                                    label:(g.kind==='vm'?'VM ':'LXC ')+g.id+(g.name?' – '+g.name:''),guestId:String(g.id),guestType:String(g.kind),
                                    complete:disks.length+' '+zfsL('disks'),snapCount:groups.length,
                                    expanded:state.expandedGuests[k]===true,
                                    children:groups});
                            });
                            tree.getStore().setRoot({expanded:true,children:roots});
                            if(tree.getView() && tree.getView().setScrollY){tree.getView().setScrollY(treeScroll);}
                            var info=view.down('#zfs-guest-status');
                            if(info){info.update(roots.length+' '+zfsL('guests found. ')+
                                zfsL('Expanded rows and scroll position are preserved on refresh.'));}
                        };
                        view.zfsTestAction = function (action, chosen) {
                            if (!chosen || !chosen.get || !caps.nodes['Sys.Modify']) { return; }
                            // Explicit row identity prevents acting on stale selections.
                            var ds = chosen.get('dataset');
                            var snap = chosen.get('snapshot');
                            if ((action === 'create' && snap) ||
                                (action !== 'create' && !snap)) {
                                zfsError('ZFS Manager', zfsL("Action does not match the selected row."));
                                return;
                            }
                            var access = state.guestAccess[ds];
                            var datasetType = String(chosen.get('datasetType') || '');
                            var standalone = !access && (datasetType === 'filesystem' || datasetType === 'volume') &&
                                !/(?:^|\/)(?:vm|subvol)-[0-9]+-disk-[0-9]+(?:-[A-Za-z0-9_.-]+)?$/.test(ds);
                            if (!state.isAdmin ||
                                (action === 'create' && !(access ? access.can_create : standalone)) ||
                                (action !== 'create' && !(access ? !access.protected : standalone)) ||
                                (action === 'delete' && access && !access.can_delete) ||
                                (action === 'rollback' && access && !access.can_rollback)) {
                                zfsError('ZFS Manager', zfsL("Action is not permitted for this dataset or user."));
                                return;
                            }
                            var base = '/nodes/' + encodeURIComponent(nodename) + '/zfsmanager-ro/';
                            var post = function (path, params) {
                                if (state.saving) { return; }
                                state.saving = true;
                                Proxmox.Utils.API2Request({
                                    url: base + path, method: 'POST', params: params,
                                    success: function () {
                                        if (!view.destroyed) {
                                            zfsSuccess('ZFS Manager', zfsL("Action completed. Refreshing snapshots."));
                                            view.zfsRefreshReadOnly();
                                        }
                                    },
                                    failure: function (res) {
                                        if (!view.destroyed) {
                                            zfsError('ZFS Manager', zfsL("Action failed: ") +
                                                safe(res && res.htmlStatus || zfsL("Unknown error")));
                                        }
                                    },
                                    callback: function () { state.saving = false; },
                                });
                            };
                            // IMPORTANT: host actions use their own admin-only routes and
                            // always require the second red warning. Guest actions NEVER do.
                            if (!access && action !== 'create') {
                                var isDeletion = action === 'delete';
                                var previewPath = isDeletion ? 'host-snapshot-delete-preview' : 'host-rollback-preview';
                                var postPath = isDeletion ? 'host-snapshot-delete' : 'host-rollback';
                                Proxmox.Utils.API2Request({
                                    url:base+previewPath, method:'GET', params:{dataset:ds,snapshot:snap},
                                    success:function(res) {
                                        var plan=res && res.result && res.result.data;
                                        if (!plan || !plan.token || !Ext.isArray(plan.delete_list)) {
                                            zfsError('ZFS Manager',zfsL('Host safety preview incomplete'));return;
                                        }
                                        var list=Ext.Array.map(plan.delete_list,function(n){return safe(n);}).join('<br>');
                                        var needsOffline = !isDeletion && Number(plan.requires_offline)===1;
                                        var message = '<div style="color:#8b1111;background:#fff0e5;border:2px solid #c62828;padding:12px;font-weight:bold">' +
                                            (isDeletion ? zfsL('Host snapshots will be permanently deleted.') :
                                             zfsL('Host rollback overwrites the current data.')) + '</div><br>' +
                                            '<b>Dataset:</b> '+safe(ds)+'<br><b>Snapshot:</b> '+safe(snap)+
                                            '<br><b>'+zfsL('Affected snapshots: ')+Number(plan.delete_count)+'</b><br>'+list+
                                            '<br><br>'+zfsL('Only this dataset; child datasets remain unchanged.')+
                                            '<br><br>'+zfsL('ZFS preview:')+'<pre>'+safe(plan.dry_run || '-')+'</pre>';
                                        if (needsOffline) {
                                            message += '<br><div style="color:#901919;border:2px solid #a52727;padding:12px">' +
                                                safe(plan.reason || zfsL('Offline required')) +
                                                '<br><b>'+zfsL('Only a signed offline request is saved here. The actual rollback runs exclusively in the rescue system.')+'</b></div>';
                                        }
                                        var hostDialog=Ext.create('Ext.window.Window',{
                                            title:isDeletion?zfsL('Host snapshot deletion – preview'):zfsL('Host rollback – preview'),
                                            width:730,height:470,modal:true,layout:{type:'vbox',align:'stretch'},
                                            items:[
                                                {xtype:'component',flex:1,scrollable:true,padding:15,html:message},
                                                {xtype:'checkbox',itemId:'zfs-host-first-ack',checked:false,
                                                 margin:'8 16 12 16',
                                                 boxLabel:zfsL('I have reviewed all affected snapshots and consequences.'),
                                                 listeners:{change:function(box,value){
                                                    var b=box.up('window').down('#zfs-host-first-confirm');
                                                    if(b){b.setDisabled(!value);}
                                                 }}}
                                            ],
                                            buttons:[
                                                {text:zfsL('Cancel'),handler:function(){hostDialog.close();}},
                                                {text:zfsL('Proceed to second safety warning'),disabled:true,
                                                 itemId:'zfs-host-first-confirm',handler:function(btn){
                                                    var ack=btn.up('window').down('#zfs-host-first-ack');
                                                    if(!ack || !ack.getValue()){return;}
                                                    hostDialog.close();
                                                    zfsCriticalWarning(isDeletion?zfsL('CRITICAL HOST DELETION'):zfsL('CRITICAL HOST ROLLBACK'),
                                                        message+'<br><b>'+zfsL('This operation can impair host recoverability.')+'</b>',
                                                        isDeletion?zfsL('Permanently delete host snapshots'):
                                                            (needsOffline?zfsL('Prepare offline recovery request'):zfsL('Start host rollback permanently')),
                                                        function(){
                                                            var args={dataset:ds,snapshot:snap,token:plan.token,
                                                                confirm:(isDeletion?'HOST-DELETE:':'HOST-ROLLBACK:')+snap,
                                                                critical_ack:1};
                                                            if (needsOffline) {
                                                                Proxmox.Utils.API2Request({
                                                                    url:base+'host-rollback-stage',method:'POST',params:args,
                                                                    success:function(response){
                                                                        var result=response && response.result && response.result.data;
                                                                        zfsDialog(zfsL('OFFLINE RECOVERY PREPARED'),
                                                                            zfsL('No rollback executed. Rescue system required. ')+
                                                                            zfsL('Signed request: ')+
                                                                            (result && result.pending_file || zfsL('See Proxmox host log')),true);
                                                                    },
                                                                    failure:function(response){zfsError('ZFS Manager',
                                                                        zfsL('Offline request failed: ')+safe(response && response.htmlStatus || zfsL('Unknown error')));}
                                                                });
                                                            } else {post(postPath,args);}
                                                        });
                                                 }}
                                            ]
                                        });
                                        hostDialog.show();
                                    },
                                    failure:function(res){zfsError('ZFS Manager',
                                        zfsL('Host preview failed: ')+safe(res && res.htmlStatus || zfsL('Unknown error')));}
                                });
                                return;
                            }
                            if (action === 'create') {
                                if (access) {
                                    // Keep all existing guest policy checks and API paths.
                                    zfsConfirm(zfsL("Proxmox Guest"),
                                        zfsL("Guest may be RUNNING. Snapshot is crash-consistent, not necessarily application-consistent. Create snapshot for ") + safe(ds) + zfsL(" now?"),
                                        function (yes) {
                                            if (yes === 'yes') { post('guest-snapshot-create',
                                                {dataset: ds, confirm:'CREATE-TEST-SNAPSHOT'}); }
                                        });
                                } else {
                                    // The selected row supplies the exact dataset to the
                                    // server; no textual confirmations or typed names.
                                    zfsConfirm(zfsL('Create host dataset snapshot'),
                                        '<span style="color:#a76000;font-weight:bold">' +
                                        zfsL('Host snapshot may consume capacity; system datasets can be important. Create for ') +
                                        '</span><b>' + safe(ds) + '</b>?<br>' +
                                        zfsL('No text input is required.'),
                                        function (answer) {
                                            if (answer === 'yes') {
                                                post('dataset-snapshot-create',
                                                    {dataset:ds, confirm:'CREATE-DATASET:' + ds});
                                            }
                                        });
                                }
                            } else if (action === 'delete') {
                                Proxmox.Utils.API2Request({
                                    url: base + 'guest-snapshot-delete-preview', method: 'GET',
                                    params: {dataset:ds,snapshot:snap},
                                    success: function (res) {
                                        var plan = res && res.result && res.result.data;
                                        if (!plan || !plan.token || !Ext.isArray(plan.delete_list) ||
                                            !plan.delete_list.length || !plan.delete_count) {
                                            zfsError('ZFS Manager',zfsL("Incomplete deletion preview.")); return;
                                        }
                                        var list = Ext.Array.map(plan.delete_list, function (name) {
                                            return '&lt;'+ safe(name) +'&gt;';
                                        }).join('<br>');
                                        // Full scrollable list, not a truncated number in a yes/no dialog.
                                        var dialog = Ext.create('Ext.window.Window', {
                                            title: zfsL("WARNING - delete entire snapshot history from this point onward"),
                                            width: 720, height: 450, modal: true,
                                            layout: {type:'vbox',align:'stretch'},
                                            items: [
                                                {xtype:'component', flex:1, scrollable:true, padding:14,
                                                    html:'<div style="color:#ad281b;background:#fff1e6;border-left:5px solid #c62828;padding:9px;font-weight:bold">' + zfsL('DANGER: irreversible snapshot deletion') + '</div><br><b>Dataset:</b> '+safe(ds)+'<br><b>Start:</b> '+safe(snap)+
                                                    zfsL("<br><b>Snapshots permanently affected: ")+Number(plan.delete_count)+
                                                    '</b><br><br>'+list+
                                                    zfsL("<br><br>The container must be stopped. The live data state will NOT be rolled back.") +
                                                    '<br><br><b>' + zfsL("ZFS dry run (no changes):") + '</b><pre>' + safe(plan.dry_run || '-') + '</pre>'},
                                                {xtype:'checkbox', itemId:'zfs-ack-delete', margin:'8 14 12 14',
                                                    boxLabel:zfsL("I have reviewed the affected snapshots and confirm permanent deletion."),
                                                    checked:false, listeners:{change:function(box, checked){
                                                        var win = box.up('window');
                                                        var actionBtn = win && win.down('#zfs-delete-confirm');
                                                        if (actionBtn) { actionBtn.setDisabled(!checked); }
                                                    }}}
                                            ],
                                            buttons: [{text:zfsL("Cancel"),handler:function(){dialog.close();}},
                                                {text:zfsL("Delete snapshots"),itemId:'zfs-delete-confirm',disabled:true,
                                                 handler:function(btn){
                                                    var win=btn.up('window');
                                                    var consent=win && win.down('#zfs-ack-delete');
                                                    if (!consent || consent.getValue() !== true) { return; }
                                                    btn.setDisabled(true);
                                                    win.close();
                                                    // Guests always need only this ONE preview + checkbox.
                                                    post('guest-snapshot-delete',{
                                                        dataset:ds,snapshot:snap,token:plan.token,
                                                        confirm:'DELETE-RANGE:'+snap,critical_ack:0
                                                    });
                                                }}],
                                        });
                                        dialog.show();
                                    },
                                    failure: function(res) {
                                        zfsError('ZFS Manager',zfsL("Deletion preview failed: ")+
                                            safe(res && res.htmlStatus || zfsL("Unknown error")));
                                    },
                                });
                            } else if (action === 'rollback') {
                                Proxmox.Utils.API2Request({
                                    url: base + 'guest-rollback-preview', method:'GET',
                                    params:{dataset:ds,snapshot:snap},
                                    success:function (res) {
                                        var plan = res && res.result && res.result.data;
                                        if (!plan || !plan.token || !Ext.isArray(plan.newer)) {
                                            zfsError('ZFS Manager',zfsL("Incomplete preview.")); return;
                                        }
                                        var allNames = Ext.Array.map(plan.newer, function(n) {
                                            return safe(n);
                                        }).join('<br>');
                                        var diskText = Ext.isArray(plan.disks) ? Ext.Array.map(plan.disks, function(d){return safe(d.dataset) + ' (' + Number(d.newer_count) + ' newer)';}).join('<br>') : safe(ds);
                                        var warning = zfsL("WARNING: Proxmox Guest will be rolled back to ") + safe(snap) +
                                            zfsL(" . ") + Number(plan.newer_count) +
                                            zfsL(" newer snapshots will be removed by a bounded delete before rollback. ") +
                                            zfsL("All data changes since the selected snapshot will be lost. ") +
                                            zfsL("External backup required.");
                                        var dlg = Ext.create('Ext.window.Window', {
                                            title:zfsL("ROLLBACK PREVIEW - data loss!"), modal:true,
                                            width:720,height:450,layout:{type:'vbox',align:'stretch'},
                                            items:[
                                                {xtype:'component',flex:1,scrollable:true,padding:14,
                                                    html:'<div style="color:#ad281b;background:#fff1e6;border-left:5px solid #c62828;padding:9px;font-weight:bold">' + zfsL('DANGER: rollback overwrites current data') + '</div><br><b>Dataset:</b> '+safe(ds)+zfsL("<br><b>Target:</b> ")+safe(snap)+
                                                        zfsL("<br><b>Selected snapshot is preserved.</b><br><br>")+
                                                        warning + '<br><br><b>Guest disks (' + Number(plan.disk_count || 1) + '):</b><br>' + diskText + zfsL("<br><br><b>Newer snapshots to delete:</b><br>") +
                                                        (allNames || zfsL("None")) +
                                                        '<br><br><b>' + zfsL("ZFS dry run (no changes):") +
                                                        '</b><pre>' + safe(plan.dry_run || '-') + '</pre>'},
                                                {xtype:'checkbox',itemId:'zfs-ack-rollback',margin:'8 14 12 14',
                                                    boxLabel:zfsL("I have reviewed the consequences and confirm rollback with data loss."),
                                                    checked:false,listeners:{change:function(box,checked){
                                                        var win=box.up('window');
                                                        var actionBtn=win && win.down('#zfs-rollback-confirm');
                                                        if (actionBtn) { actionBtn.setDisabled(!checked); }
                                                    }}}
                                            ],
                                            buttons:[{text:zfsL("Cancel"),handler:function(){dlg.close();}},
                                                {text:zfsL("Execute rollback"),itemId:'zfs-rollback-confirm',disabled:true,
                                                 handler:function(btn){
                                                    var win=btn.up('window');
                                                    var consent=win && win.down('#zfs-ack-rollback');
                                                    if (!consent || consent.getValue() !== true) { return; }
                                                    btn.setDisabled(true);
                                                    win.close();
                                                    // No second warning for VM/LXC rollback.
                                                    post('guest-rollback',{
                                                        dataset:ds,snapshot:snap,token:plan.token,
                                                        confirm:'ROLLBACK:'+snap,critical_ack:0
                                                    });
                                                }}],
                                        });
                                        dlg.show();
                                    },
                                    failure:function (res) {
                                        zfsError('ZFS Manager',zfsL("Preview failed: ")+
                                            safe(res && res.htmlStatus || zfsL("Unknown error")));
                                    },
                                });
                            }
                        };
                        view.zfsRefreshReadOnly = function () {
                            if (view.destroyed || state.refreshing) { return; }
                            state.refreshing = true;
                            var routes = [
                                ['disks/list', 'disks'],
                                ['disks/zfs', 'pools'],
                                ['zfsmanager-ro/pool-scan', 'scan'],
                                ['zfsmanager-ro/datasets', 'datasets'],
                                ['zfsmanager-ro/snapshots', 'snapshots'],
                                ['zfsmanager-ro/retention', 'retention'],
                                ['zfsmanager-ro/guest-access', 'guestAccess'],
                                ['zfsmanager-ro/admin-status', 'adminStatus'],
                            ];
                            var pending = routes.length;
                            Ext.Array.each(routes, function (route) {
                                var key = route[1];
                                Proxmox.Utils.API2Request({
                                    url: '/nodes/' + encodeURIComponent(nodename) + '/' + route[0],
                                    method: 'GET',
                                    timeout: 30000,
                                    success: function (response) {
                                        if (view.destroyed) { return; }
                                        var data = response && response.result && response.result.data;
                                        if (key === 'adminStatus') {
                                            if (!data || typeof data.admin !== 'number') { error('Invalid admin status'); return; }
                                            state.isAdmin = data.admin === 1;
                                            ['zfs-retention-label','zfs-retention-keep'].forEach(function(id){
                                                var f = view.down('#'+id); if (f) { f.setDisabled(!state.isAdmin); }
                                            });
                                            var save = view.down('#zfs-retention-save');
                                            if (save) { save.setDisabled(!state.isAdmin); }
                                            view.zfsRenderTree(); finish(); return;
                                        }
                                        if (!Ext.isArray(data)) {
                                            error(zfsL("Unexpected response format")); return;
                                        }
                                        if (key === 'guestAccess') {
                                            var mapped = {};
                                            data.forEach(function(g){ if (g.dataset) { mapped[String(g.dataset)] = g; } });
                                            state.guestAccess = mapped;
                                            view.zfsRenderTree(); view.zfsRenderGuests(); finish(); return;
                                        }
                                        state[key] = data;
                                        if (key === 'snapshots') {state.readySnapshots=true;}
                                        if (key === 'pools' || key === 'snapshots' || key === 'retention') {renderCapacity();}
                                        if (key === 'disks' || key === 'pools') {
                                            gridLoad('zfs-ro-' + key, data);
                                            var gridStatus = view.down('#zfs-ro-' + key + '-status');
                                            if (gridStatus) { gridStatus.update(data.length + zfsL(" entries loaded.")); }
                                        }
                                        if (key === 'retention') {
                                            renderRetention(data);
                                            var labelField = view.down('#zfs-retention-label');
                                            var keepField = view.down('#zfs-retention-keep');
                                            if (labelField && keepField && !state.saving) {
                                                var selected = labelField.getValue();
                                                var selectedRow = data.find(function (r) { return r.label === selected; });
                                                if (selectedRow) { keepField.setValue(selectedRow.keep); }
                                            }
                                            var rstatus = view.down('#zfs-ro-retention-status');
                                            if (rstatus) { rstatus.update(data.length + zfsL(" retention rules loaded.")); }
                                        }
                                        if (key === 'scan') { gridLoad('zfs-ro-scan', data); }
                                        if (key === 'datasets' || key === 'snapshots' || key === 'pools') {
                                            view.zfsRenderTree(); view.zfsRenderGuests();
                                        }
                                        finish();
                                    },
                                    failure: function (response) {
                                        if (view.destroyed) { return; }
                                        error(response && (response.htmlStatus || response.statusText) || zfsL("Unknown error"));
                                    },
                                });
                                function error(message) {
                                    var status = view.down('#zfs-ro-' +
                                        (key === 'disks' ? 'disks' : key === 'pools' || key === 'scan' ? 'pools' :
                                         key === 'retention' ? 'retention' : 'snapshots') + '-status');
                                    if (status && !status.destroyed) { status.update(zfsL("API error: ") + safe(message)); }
                                    finish();
                                }
                                function finish() {
                                    pending--;
                                    if (pending === 0) { state.refreshing = false; }
                                }
                            });
                        };
                        view.zfsRefreshReadOnly();
                        view.zfsRefreshTimer = Ext.TaskManager.start({
                            run: function () {
                                if (!view.destroyed && view.zfsRefreshReadOnly) { view.zfsRefreshReadOnly(); }
                            },
                            interval: 60000,
                        });
                    },
                    destroy: function (view) {
                        if (view.zfsRefreshTimer) { Ext.TaskManager.stop(view.zfsRefreshTimer); }
                    },
                },
            });
        }
''' + END
