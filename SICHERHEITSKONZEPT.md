# RC9 – Sicherheitskonzept und Bedienvertrag

| Ziel | VM/LXC | Normales Host-Dateisystem | `rpool`, ROOT, aktives Root |
| --- | --- | --- | --- |
| Snapshot erstellen | Direkt, automatisch benannt | Direkt, automatisch benannt | Direkt mit Hinweis |
| Snapshot löschen | Vorschau + **eine** Checkbox | Vorschau + erste Checkbox + **zweite rote Warnung/Checkbox** | Dieselben zwei Warnungen, Host-API, Clone/Hold-Prüfung |
| Rollback | Vorschau + **eine** Checkbox, Gast aus | Zwei Warnungen, nur bei nicht gemountetem Dateisystem | Zwei Warnungen und signierte Offline-Vorbereitung; keine Live-Ausführung |
| Adminpflicht | Ja | Ja | Ja |
| Texteingaben | Nein | Nein | Nein |

Zusätzlich: 5-Minuten-HMAC-Vorschau, CSRF/RBAC, Token-Sperre, exakte Grenzen der Snapshot-Reihe, ZFS native Dryrun, keine rekursive `-R`/`-r`-Zerstörung von Kind-Datasets und signierter 24h-Rescue-Plan.

**Wichtige technische Einschränkung:** Ein `zfs rollback rpool@...` setzt ausschließlich das Dataset `rpool` zurück, nicht automatisch `rpool/ROOT/pve-1` oder andere Unter-Datasets. OpenZFS erfordert für ein vollständiges rekursives Recovery eine *individuelle* Prüfung und Rücksetzung der betroffenen Kinder. Der ZFS Manager darf dies nicht verschweigen und führt keine verdeckte Mehrdataset-Rücksetzung aus.

**Nicht getestet auf echter Hardware:** Die Offline-Rettung benötigt ZFS im Rescue-OS, korrekt importierten Pool und einen extern geprüften Backup-/Boot-Wiederherstellungsweg. Bis zu diesem Test ist RC9 keine Finalversion.
