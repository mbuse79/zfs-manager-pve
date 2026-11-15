# BuMaVory ZFS Manager v1.0.0-32 — Codeherkunft und Abgleich

**Stand:** 2026-11-09
**Status:** Technische Teilprüfung dokumentiert, **keine abschließende Urheber- oder Veröffentlichungsfreigabe**.

## 1. Quellen und Prüfumfang

- Projekt: vollständig vom Maintainer bereitgestelltes privates Git-Bundle; Ursprungs-HEAD `d6cc529` (10 erreichbare Commits). Der nachfolgende reine Dokumentations-Commit `30cbb13` wurde am 09.11.2026 vom Maintainer mittels PowerShell-Push bestätigt. Ein neuer Live-Abruf der privaten GitHub-Referenzen erfolgte bei der Analyse nicht.
- Vergleichspaket: vom Maintainer bereitgestelltes `pve-manager_9.2.25_all.deb`, SHA256 `8249415f1b2ddc9d8da4e4888c89be70f3b464f1745d9a0d1ef1b82816cae177`. Laut enthaltener Datei `usr/share/doc/pve-manager/copyright`: Copyright 2010–2026 Proxmox Server Solutions GmbH, **AGPL-3+**. Die Paket-Signatur wurde in diesem Vergleich nicht unabhängig nachgeprüft.
- Eigenes geprüftes Binärpaket: `pve-zfs-manager_1.0.0-32_all.deb`, SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`. Die 33 Python-/Perl-Quelldateien stimmten byteweise zwischen Repository und dieser DEB überein; 138 Regressionstests bestanden beim früheren Git-Audit.
- Statischer Vergleich von **83 JavaScript-/Perl-Dateien** aus dem bereitgestellten `pve-manager` mit den relevanten Projektdateien; insbesondere `pvemanagerlib.js` und `PVE/API2/Nodes.pm`. Gesucht wurden identische Zeilen- bzw. zusammenhängende Token-Sequenzen. Zusätzlich wurde die GUI/API-Patch-Reversibilität an isolierten Dateikopien erprobt.
- **Nicht Bestandteil des Vergleichskorpus:** etwa `proxmox-widget-toolkit`, die komplette ExtJS-Quelle, weitere Proxmox-Pakete oder ursprüngliche Chat-/Entwicklungsstände vor dem Git-Erstimport.

## 2. Belegte technische Berührungspunkte

| Projektdatei | Bezug zum Upstream `pve-manager` 9.2.25 | Ergebnis |
| --- | --- | --- |
| `src/patch_nav.py` (ca. Zeilen 21–25, 59–71) | Wörtlicher kurzer Suchanker aus `PVE.node.Config` / `proxmoxNodeServiceView` in `pvemanagerlib.js` (Bereich ca. Zeile 50996) | Proxmox-Struktur wird als Einfügepunkt verwendet; keine Übernahme des kompletten Upstream-Moduls nachgewiesen. |
| `src/universal.py` (ca. Zeilen 244–252) | Einfügen eigener JavaScript-Komponenten in vorhandene `pvemanagerlib.js` | Bestehende Upstream-Datei wird erst auf dem Host verändert; sie wird nicht vollständig mit der ZFS-Manager-DEB ausgeliefert. |
| `src/universal.py` (ca. Zeilen 47–53, 275–292) | Import und Registrierung eines eigenen API-Moduls in vorhandener `PVE/API2/Nodes.pm` | Integrationspunkt über Proxmox-API; keine komplette Kopie von `Nodes.pm`. |
| `src/PVE/API2/ZFSSnapshotViewer.pm` und sieben ältere Perl-Varianten | Typische `register_method`-/`proxyto`-/`permissions`-Felder ähnlich `PVE/API2/Nodes.pm` (etwa Zeilen 2858–2865) | Automatisierte Suche ergab 56 Sequenztreffer von 45–56 Tokens, konzentriert auf diese üblichen API-Felder. Allein kein Beweis einer schutzfähigen Übernahme. |
| `src/manager_patch.py` und ältere `manager_patch_*`-Varianten | Eigene ExtJS-Oberflächendefinitionen mit Proxmox-Namensräumen | Gegen die ausgewählte `pve-manager`-GUI kein exakter zusammenhängender Treffer ab 45 Tokens. Herkunft aus anderen Quellen oder bearbeitete Übernahmen dadurch **nicht ausgeschlossen**. |

In der lokalen Integrationssimulation wurden Menü und API um eigene Blöcke erweitert und anschließend **bytegenau rückgängig** gemacht. `node --check` bestand für die ergänzte GUI. Dies ist kein Browser- oder Produktivtest und kein urheberrechtlicher Reinheitsnachweis.

## 3. Urheberrechtliche Einordnung und Abgrenzung

- Proxmox VE und dessen Komponenten sind Drittsoftware. Die Rechte der Proxmox Server Solutions GmbH werden durch BuMaVory weder beansprucht noch umgeschrieben.
- Die festgestellten **kurzen Menü-Suchanker** und **üblichen API-Muster** werden aus Transparenzgründen genannt. Damit wird weder behauptet, sie seien schutzfähig und fremd lizenziert, noch, sie seien garantiert gemeinfrei.
- Ein `PVE::`-Import, eine Framework-API, ein Klassenname oder eine Host-Dateiänderung stellt allein keine Quellcodeübernahme dar. Umgekehrt erfasst der Vergleich weder semantisch umgeschriebene noch aus anderen Paketen übernommene Blöcke.
- Die `AGPL-3.0-only`-Wahl gilt für solche Projektbeiträge, für die entsprechende Lizenzrechte bestehen. `AGPL-3+` des Proxmox-Pakets ist ein getrennt dokumentierter Upstream-Lizenzhinweis, keine pauschale Lizenzierung sämtlicher ZFS-Manager-Dateien durch Proxmox.
- Die vollständige Entwicklungsherkunft **vor dem gesammelt importierten Quellcode-Commit vom 06.11.2026** ist aus dem Git-Bundle nicht nachweisbar. Von ChatGPT unterstützte Entwicklung lässt die Prüfung möglicher dritter Vorlagen nicht entfallen.

**Angabe des Maintainers (09.11.2026):** Er hat selbst keine Codefragmente aus anderen GitHub-Repositories, Webseiten oder Proxmox-Quelldateien in dieses Projekt eingefügt; die projektbezogenen Codebeiträge wurden in der gemeinsamen ChatGPT-gestützten Entwicklung erstellt. Dies dokumentiert die Erklärung des Maintainers, nicht eine unabhängig bewiesene weltweite Codeherkunft oder die Rechtefreiheit aller generierten Abschnitte.

## 4. Offene Freigabepunkte

1. Die Erklärung des Maintainers zur gemeinsamen ChatGPT-gestützten Entwicklung wurde dokumentiert. Konkrete externe Codevorlagen oder Drittbeiträge, falls später festgestellt, sind mit Herkunft/Lizenz zu ergänzen; eine vollständige unabhängige Provenienzprüfung vor Git-Erstimport ist nicht möglich.
2. Relevante *andere* Upstreamquellen (`proxmox-widget-toolkit`, ExtJS, sonstige verwendete Vorlagen) bei Anhaltspunkten vergleichen; eventuelle konkrete Übernahmen einschließlich Ursprung, Revision, Lizenz und Rechteinhaber dokumentieren.
3. Für **nachgewiesen übernommene** urheberrechtlich relevante Passagen `debian/copyright`, gegebenenfalls Dateiheader und Notices rechtlich korrekt zuordnen. Das derzeitige pauschale `Files: *` ist nur eine vorläufige Zuordnung und **nicht als abgeschlossene Klärung** zu verstehen.
4. Die in der geprüften finalen DEB **eingebetteten** Dateien `usr/share/doc/pve-zfs-manager/copyright` und `THIRD_PARTY_NOTICES.md` unterscheiden sich nach einem reinen Repository-Dokumentationspatch weiterhin von der neuen Dokumentation. Vor einem öffentlichen DEB-Release prüfen, ob **ein aktualisiertes, neu zu testendes Paket** zur korrekten Lizenzbeilage nötig wird; das ursprüngliche getestete Paket nicht heimlich ersetzen oder unter derselben Prüfsumme ausgeben.
5. Vertraulichen E-Mail-Empfang/-Antwort unabhängig testen, die historisch gelöschten Git-Dokumente redaktionell freigeben und die aktuellen Release-Assets/Quellen nach Abschluss der Rechteprüfung konsistent erstellen.

## 5. Referenzen

- `pve-manager`-Debian-Datei: `usr/share/doc/pve-manager/copyright` (lokal untersuchte Nutzerdatei, Version 9.2.25).
- Original-Repository: https://github.com/proxmox/pve-manager
- Debian Copyright Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
- GNU AGPL-3.0: https://www.gnu.org/licenses/agpl-3.0.html

*Dieser Bericht dokumentiert einen statischen technischen Teilvergleich, keine anwaltliche Urheberrechtsfreigabe.*
