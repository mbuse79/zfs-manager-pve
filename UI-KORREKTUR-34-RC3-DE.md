# BuMaVory ZFS Manager 1.0.0-34 RC3 – GUI-Korrektur

Die Laufwerksliste besitzt keine feste 95-Pixel-Höhe mehr. Sie wächst mit der Anzahl vorhandener Laufwerke und wird ab maximal 540 Pixel innerhalb der Liste scrollbar.

Die ZFS-Pooltopologie startet standardmäßig mit geschlossenen Pool-Einträgen. Nach dem manuellen Öffnen bleiben die untergeordneten vdevs standardmäßig ausgeklappt, sodass die Festplatten sichtbar werden. Der manuelle Zustand bleibt während der 60-Sekunden-Aktualisierung erhalten. Die Topologie passt ihre Höhe ebenfalls an sichtbare Zeilen an (max. 540 Pixel).

Dies ist eine Oberflächenkorrektur. Die automatische Snapshot-Bereinigung bleibt standardmäßig deaktiviert. Warnüberwachung und Benachrichtigung der RC2 sind unverändert enthalten.

Empfohlene Prüfung nach Installation: Seite mit Strg+F5 aktualisieren und Poolzeilen auf-/zuklappen; keine Löschungen für diese GUI-Prüfung durchführen.
