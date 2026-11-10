# BuMaVory ZFS Manager v1.0.0-32 — Lizenz- und Codeherkunftsprüfung

**Update 10.11.2026:** Die historische, tatsächlich getestete `1.0.0-32` bleibt unverändert. Die exakte `1.0.0-32+docs2` wurde am 09.11.2026 auf `pve-test` (PVE 9.2.25) mit erfolgreicher CLI-/GUI-Prüfung installiert; das ist keine eigenständige Rechtefreigabe. `LICENSE` ist unveränderter FSF-Lizenztext; `debian/copyright` enthält dafür einen gesonderten Hinweis. Details siehe `PACKAGE-STATUS.md`.


Stand: 2026-11-09  
Lizenzwahl: **AGPL-3.0-only für eigenständig entwickelte Projektbestandteile**  
Veröffentlichungsstatus: **Repository und `v1.0.0-32` am 10.11.2026 veröffentlicht. Die technische Codeherkunfts- und Lizenzprüfung ist im dokumentierten Umfang durchgeführt; keine konkrete unzulässige Fremdcodeübernahme nachgewiesen. Keine unabhängige rechtliche Vollprüfung.**

## Bestätigte Punkte

- **Lizenzwahl:** Der Maintainer hat `AGPL-3.0-only` gewählt; der vollständige AGPLv3-Lizenztext liegt als `LICENSE` im vorbereiteten Quellarchiv und im Debian-Paket vor.
- **Paketmetadaten:** Die geprüfte DEB `pve-zfs-manager_1.0.0-32_all.deb` enthält `Maintainer: BuMaVory Project <bumavory@buse.rocks>` und Version `1.0.0-32`. SHA256: `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`.
- **Praxistest am 2026-11-07:** Der Maintainer hat die DEB über Nextcloud mit passender SHA256-Prüfung heruntergeladen und auf `pve-test` per APT von `1.0.0-32~rc1` auf `1.0.0-32` aktualisiert. `zfsm version`, `status`, `check` und `services` waren erfolgreich auf Proxmox VE 9.2.25; die grafische Oberfläche wurde ebenfalls vom Maintainer als funktionierend bestätigt.
- **Sicherheitskontakt:** `SECURITY.md` nennt `bumavory@buse.rocks` für vertrauliche Meldungen. Der Maintainer meldete am 09.11.2026 einen erfolgreichen E-Mail-Funktionstest; ein separater externer Zustell-/Antwortnachweis wurde nicht eingesehen.

## Konkret geprüfte Quelldateien

Grundlage des historischen Ausgangsaudits: ein lokal überlassenes Quellarchiv `BuMaVory-ZFS-Manager-1.0.0-32-AGPL-Source.tar.gz`. Inzwischen wurden das öffentliche `main` und der Release-Tag `v1.0.0-32` über GitHub geprüft. Die vollständige Codeherkunft vor dem ersten Git-Import ist dadurch nicht nachgewiesen.

Im Verzeichnis `src/` befinden sich **25 Python- und 8 Perl-Dateien**. In ihren ersten 25 Zeilen waren keine expliziten Copyright-/SPDX-Kopfzeilen erkennbar. Dies beweist keine Fremdurheberschaft, zeigt aber fehlende dateibezogene Rechte- und Lizenzzuordnung.

Im technischen Codeherkunfts- und Lizenzabgleich betrachtete Bestandteile (zusätzliche Prüfung nur bei konkreten Anhaltspunkten):

| Datei/Familie | Warum prüfen? | Stand |
| --- | --- | --- |
| `src/manager_patch.py`, `src/previous_patch.py`, `src/patch_nav.py` und Versionsvarianten `manager_patch_*.py` | GUI-Integrationscode mit Proxmox-Menüankern und ExtJS-Strukturen. | Im definierten `pve-manager`-Korpus verglichen; kein längerer identischer GUI-Implementierungsblock gefunden. Andere mögliche Vorlagen nicht systematisch untersucht. |
| `src/PVE/API2/ZFSSnapshotViewer.pm` und ältere Varianten | API-Registrierungsfelder und Proxmox-Schnittstellen. | Technisch verglichen; nur kurze konventionelle API-Muster festgestellt. |
| `src/universal.py` | Einbau der projektspezifischen Ergänzungen in bereits vorhandene Proxmox-Dateien auf dem Host. | Integrationspunkte untersucht; keine vollständigen fremden Hostdateien im Paket festgestellt. |
| `src/libexec/guest_policy*.py`, `src/zfsm_cli.py`, `src/zfsm_capacity.py`, `src/adminctl.py`, `src/offline_recovery.py` | Eigenständige Projektbestandteile; Maintainer-Erklärung zur Entstehung ist dokumentiert. | In den technischen Quellenabgleich einbezogen; Lizenzköpfe können bei zukünftiger Pflege vereinheitlicht werden. |
| `debian/copyright` | Lizenzwahl für eigene Beiträge und gesonderter Vermerk zum unveränderten FSF-Lizenztext. | Vorhanden; ergänzen, wenn tatsächliche Drittanteile mit nachweisbaren Rechten festgestellt werden. |

**Abgrenzung:** Der Import einer Proxmox-Bibliothek, ein Aufruf der öffentlichen API oder das Patchen einer auf dem Host installierten Datei ist für sich genommen **noch kein Nachweis, dass fremder Quelltext mit dem Paket ausgeliefert wird**. Umgekehrt belegt ein automatischer Scan nicht, dass kein fremder Quelltext enthalten ist. Für übernommene Abschnitte müssen die jeweiligen Urheberrechtsvermerke und Lizenzbedingungen erhalten bleiben.

## Zusätzlicher Upstream-Abgleich vom 09.11.2026

- Das vom Maintainer bereitgestellte Originalpaket `pve-manager_9.2.25_all.deb` wurde extrahiert und in den 83 einschlägigen JavaScript-/Perl-Dateien mit dem ZFS-Manager-Code verglichen. Original-Copyright laut Paket: **2010–2026 Proxmox Server Solutions GmbH**, **AGPL-3+**.
- **Belegte kurze Berührungspunkte:** ein wörtlicher Menü-Suchanker in `src/patch_nav.py` zu `pvemanagerlib.js`; typische API-Registrierungsfelder in `src/PVE/API2/ZFSSnapshotViewer*.pm` zu `PVE/API2/Nodes.pm`; `src/universal.py` bindet eigene Ergänzungen in diese vorhandenen Hostdateien ein.
- **Kein längerer wortgleicher GUI-Funktionsblock** ab 45 Tokens aus dem untersuchten `pve-manager`-Korpus wurde in der Projekt-GUI nachgewiesen. Das ist nur ein abgegrenzter **technischer Teilvergleich**, nicht der Nachweis vollständiger unabhängiger Autorschaft oder die Prüfung aller Frameworks.
- Die oben genannten Funde und verbleibenden Grenzen sind in [`CODE-PROVENANCE-REVIEW.md`](CODE-PROVENANCE-REVIEW.md) dokumentiert und in [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md) als vorläufige Quellenhinweise aufgenommen. Nicht nachgewiesene Dritturheber werden **nicht** pauschal zu Rechteinhabern eigener Implementierungen erklärt.
- **Paket-Metadaten (historischer Befund):** Die ursprüngliche `1.0.0-32`-DEB enthielt teilweise veraltete Dokumente, obwohl das Debian-Control-Maintainerfeld korrekt war. Die separate `1.0.0-32+docs2`-Revision korrigierte diese Beilagen und wurde am 09.11.2026 auf PVE 9.2.25 praktisch getestet. Das veröffentlichte Paket entspricht SHA256 `3fa2e7a8777e0c58b80cfadcafdd9b4eabc5da883c35e5e1672b9c3417d2251d`; dies ist kein unabhängiges vollständiges Herkunfts- oder Rechtsgutachten.
- Der Maintainer hat den Dokumentations-Commit **`30cbb13`** auf `main` erfolgreich gepusht (PowerShell-Ausgabe vom 09.11.2026). Dies ist **keine** vollständige erneute Live-Abfrage des privaten GitHub-Repositorys.

## Abschlussstand und mögliche Folgearbeiten (10.11.2026)

1. **Technische Prüfung durchgeführt:** Die Herkunftserklärung des Maintainers, der Vergleich der 33 projektbezogenen Python-/Perl-Dateien mit 83 relevanten `pve-manager`-Dateien und die festgestellten kurzen Integrationsmuster sind dokumentiert. In diesem begrenzten Prüfumfang wurde keine konkrete unzulässige Fremdcodeübernahme festgestellt.
2. **Keine pauschale Rechtsgarantie:** Nicht Bestandteil der Untersuchung waren ein vollständiger Vergleich mit ExtJS, `proxmox-widget-toolkit`, allen denkbaren weiteren Vorlagen und eine unabhängige Prüfung jeder Entwicklungsstufe vor dem Git-Erstimport. Daraus folgt nicht automatisch ein offener konkreter Rechtsverstoß.
3. **Lizenznachweise bei Bedarf ergänzen:** Für später eindeutig nachgewiesene fremde Passagen konkrete Quellen, Rechteinhaber und Lizenzen in `debian/copyright`, Dateiheadern und `THIRD_PARTY_NOTICES.md` aufnehmen. Ein vollständiges externes Rechtsgutachten wurde nicht beauftragt oder erbracht.
4. **Sicherheitskontakt und Veröffentlichung:** `bumavory@buse.rocks` wurde vom Maintainer am 09.11.2026 erfolgreich getestet; GitHub Private Vulnerability Reporting ist laut API-Prüfung vom 10.11.2026 aktiviert. Das Repository und `v1.0.0-32` sind öffentlich; die Git-Historie wurde vor Veröffentlichung um drei bekannte interne Berichte bereinigt. Externe Kopien oder Caches können davon unberührt bleiben.
5. **Artefakte unverändert:** Das bereits geprüfte `1.0.0-32+docs2`-Paket samt SHA256, das Release-Quellarchiv und der Tag `v1.0.0-32` werden durch diese nachträgliche Dokumentationskorrektur nicht ersetzt.

## Keine erneute Pflichtprüfung

Die Punkte „Maintainer-Adresse im DEB ersetzen“, „neue Final-DEB bauen“ und „auf PVE 9.2.25 installieren“ sind **bereits erledigt**. Sie dürfen nicht weiterhin als offen dargestellt werden, solange das veröffentlichte Artefakt der oben genannten SHA256 entspricht.

## Quellen

- Proxmox: https://proxmox.com/en/about/open-source/developers
- GNU AGPL-3.0: https://www.gnu.org/licenses/agpl-3.0.html
- Debian Copyright Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/

*Technische Dokumentationsprüfung, keine anwaltliche Marken- oder Urheberrechtsfreigabe.*
