# BuMaVory ZFS Manager 1.1.1

AutoSnap kann jetzt je VM/LXC ausgeschlossen und wieder eingeschaltet werden. Gast- und Dataset-Zeilen zeigen ihren Zustand dezent grün, rot oder gelb. Aktionsschaltflächen sind einheitlich ausgerichtet. Die Dataset-Standardansicht blendet bekannte ZRM-/zrepl-Replikationsbereiche aus; „Alle Datasets anzeigen“ zeigt sie wieder.

„Alle Snapshots löschen“ umfasst die aktuell zugeordneten ZFS-Datenträger eines gestoppten Gastes und verlangt Vorschau und Bestätigung. Schutzprüfungen bleiben erhalten. Neue oder verschobene Gast-Datenträger erfordern eine erneute Prüfung des AutoSnap-Ausschlusses. Einschalten aktiviert alle sechs Intervalle ausdrücklich.

ZFSM prüft täglich auf stabile Releases. Updates werden erst nach erfolgreicher Vorprüfung und ausdrücklicher Bestätigung installiert. Bereits installierte Testversionen können über **ZFSM-Updates → Jetzt prüfen** auf 1.1.1 aktualisiert werden.

Installation: [INSTALL-1.1.1.md](https://github.com/mbuse79/zfs-manager-pve/blob/v1.1.1/docs/INSTALL-1.1.1.md). Vollständiges ZIP einschließlich Abhängigkeiten, Quellen und Lizenzen verwenden. Prüfsummen stehen in SHA256SUMS. Vorhandene Version-1.1-Downloads bleiben unverändert.

Automatisierte Prüfungen und isolierte ExtJS-Browsertests prüfen die Funktionen. Der Betreiber hat die RC9-Migration auf PVE 9.1.1 erfolgreich ausgeführt und spätere Oberflächenstände gezeigt. Das endgültige 1.1.1-Paket und ein vollständiger Web-Update-Lauf wurden noch nicht auf einem echten PVE neu getestet.

English: per-guest AutoSnap controls, confirmed deletion of all guest snapshots, subtle status colours, aligned actions, focused dataset inventory and daily stable update checks with explicitly confirmed installation. Existing schedules and safety checks remain in effect. Use the complete verified ZIP and the versioned installation guide.
