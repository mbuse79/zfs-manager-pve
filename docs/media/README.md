# Bilder und Demo / Screenshots and demo

Die Bilder und der Film zeigen den tatsächlichen **Version-1.1-ExtJS-Panelcode**
mit klar gekennzeichneten Beispiel-/Testdaten. Keine Verbindung zu realen PVE-Hosts,
keine echte Installation, keine Löschung und kein Rollback. Die sichtbare Umgebung
ist ein isolierter Browser-Harness, nicht eine vollständige PVE-Websitzung.

- `overview-de.png`, `overview-en.png`: Pool- und Snapshot-Übersicht.
- `cluster-de.png`, `cluster-en.png`: bewusste Auswahl von Clusterknoten.
- `zfsm-1.1-demo-en.mp4`: rund zwei Minuten Oberflächenrundgang, englische Bildtexte,
  ohne Ton. Das Video endet vor einer Installationsbestätigung.
- `zfsm-1.1-demo.de.srt`, `zfsm-1.1-demo.en.srt`: separate Untertitel.

In einer Vorstellung als „Demo mit Testdaten“ kennzeichnen. Die realen
Praxistestnachweise stehen separat in `RELEASE-QA.md`; das Video ersetzt sie nicht.
Keine Proxmox-/ExtJS-Laufzeitdateien werden mit diesem Medienordner verteilt.

English: These are captures of the actual 1.1 panel code using labelled sample data
in an isolated browser harness, not a live Proxmox-host session. No real installation,
deletion or rollback occurs. The silent video is an interface tour, not host-test
evidence. Keep this context when sharing. See RELEASE-QA.md for actual evidence.

## Aufzeichnung reproduzieren

`tools/record-promo.cjs` verwendet die vorhandenen API-Fixtures aus
`tests/browser_rc9.cjs`, ersetzt Gastnamen durch neutrale Beispiele und lädt
keine externen APIs. Benötigt werden Playwright, Chromium, dessen FFmpeg-Unterstützung
sowie lokal bereitgestellte ExtJS-/Widget-Toolkit-Dateien aus den Proxmox-Paketen.
Die jeweiligen Drittanbieter-Lizenzen gelten weiterhin.

```bash
PYTHONPATH=src python3 - <<'PY'
from pathlib import Path
import manager_patch, previous_patch
Path('/tmp/zfsm-promo-ui.js').write_text(previous_patch.HELPERS + manager_patch.BLOCK)
PY
node tools/record-promo.cjs "$ZFSM_EXTJS_ROOT" "$ZFSM_TOOLKIT_ROOT" /tmp/zfsm-promo /tmp/zfsm-promo-ui.js --video
```

Die beiden Variablen zeigen auf die entsprechenden lokalen JavaScript-Verzeichnisse.
Ohne `--video` entstehen nur die Screenshots. Die erzeugten JSON-Nachweise melden
Browserfehler und bestätigen, dass kein Installationsaufruf erfolgte. Das Video
kann anschließend mit lokalem FFmpeg als H.264/MP4 für übliche Player exportiert werden.
