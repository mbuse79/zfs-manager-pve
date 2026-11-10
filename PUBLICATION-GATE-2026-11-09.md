# BuMaVory ZFS Manager 1.0.0-32 — Publikationssperren und Abschlussstand

**Nachtrag 10.11.2026:** Die veralteten eingebetteten Unterlagen betreffen die historische Referenz-DEB `1.0.0-32`. Die separate Paketrevision `1.0.0-32+docs2` wurde am 09.11.2026 mit bestätigter SHA256 auf `pve-test` installiert und CLI/GUI-geprüft. Eine rechtliche Freigabe und die Live-Prüfung der GitHub-Historie sind davon getrennt. Die nachfolgenden Abschnitte dokumentieren teils den historischen Prüfstand.


**Erstellt:** 09.11.2026 · **Repository bleibt privat** · **Keine Änderung an Programmcode oder geprüfter DEB.**

## Verifizierte technische Grundlagen

- Vom Maintainer mit PowerShell-Ausgabe bestätigter privater `main`-Push: `59d58e3` (`docs: document Proxmox code provenance and third-party licensing`). Diese Prüfung verwendet das ursprünglich überlassene Git-Bundle (`d6cc529`) und die beiden bestätigten Dokumentationspatches zur Rekonstruktion des Stands; kein unabhängiger Abruf des privaten Commits `59d58e3`.
- Technisches Referenzartefakt: `pve-zfs-manager_1.0.0-32_all.deb`, SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`; Debian-Control-Maintainer **korrekt** `BuMaVory Project <bumavory@buse.rocks>`.
- Paket am 07.11.2026 laut Maintainer erfolgreich auf PVE 9.2.25 installiert und GUI/CLI geprüft. 138/138 Python-Regressionstests aus früherer Prüfung; 33/33 Python-/Perl-Quellen bytegleich mit geprüftem Paket.
- Git-Integrität und erreichbare Historie geprüft (ursprünglicher Export: zehn Commits, ein Branch); heuristischer Suchlauf ohne bestätigten Secret-Fund. Historisch gelöschte Dateien bleiben in erreichbaren alten Commits, veröffentlichungsgeeignete Inhalte müssen redaktionell geprüft werden.
- Technischer Vergleich mit dem vom Nutzer überlassenen Paket `pve-manager_9.2.25_all.deb` (83 JS-/Perl-Dateien) fand nur kurze wörtliche Einfügeanker und generische API-Muster; kein langer identischer GUI-Implementierungsblock. Weitere Proxmox-Pakete (`proxmox-widget-toolkit`, ExtJS etc.), abgeleitete/umgeschriebene Vorlagen und die Historie **vor dem Erstimport** sind dadurch nicht vollständig geprüft.
- E-Mail-Funktionstest für `bumavory@buse.rocks` am 09.11.2026 vom Maintainer als erfolgreich gemeldet; ein unabhängiger technischer Mitschnitt oder ein externer Absender-/Antwortnachweis wurde nicht eingesehen.

## Entscheidende neue Feststellung: Paketdokumentation ist inkonsistent

Die **tatsächliche** installierte Datei `usr/share/doc/pve-zfs-manager/LICENSING-REVIEW.md` innerhalb der geprüften DEB sagt noch, die Paketmetadaten enthielten `contact@example.invalid` und eine finale Live-Installation fehle. **Beides ist falsch:** Das Control-Feld enthält die bestätigte Maintainer-Adresse und der Live-Test fand statt. Die DEB enthält außerdem ältere Versionen von `THIRD_PARTY_NOTICES.md`, `SECURITY.md`, `RELEASE-QA.md`, `README.md` und ein historisches PDF. Die im Repository korrigierten Dokumente ersetzen die eingebetteten DEB-Dateien nicht.

**Folge:** Das ursprüngliche, lauffähige Paket bleibt unberührt und als Referenz archiviert. Für einen widerspruchsfreien öffentlichen Binärdownload ist ein **separat zu erstellendes Dokumentations-/Metadaten-Update-Paket** mit eigenem SHA256 erforderlich. Dessen Runtime-Dateien müssen gegenüber der getesteten DEB bytegleich nachgewiesen werden, dazu Paketstruktur, Lizenzbeilagen und ein begrenzter Live-Pakettest. Vor Abschluss der Herkunftsklärung wird kein öffentlicher Release erzeugt. **Ein bisheriger 138/138-Test ersetzt nicht die Überprüfung der geänderten Paketdatei.**

## Copyright und Codeherkunft

- Die AGPLv3-Lizenzwahl ist für Anteile festgelegt, für die BuMaVory die Lizenzrechte besitzt. `debian/copyright` enthält derzeit den pauschalen Eintrag `Files: * / Copyright: 2026 BuMaVory ZFS Manager contributors`; dieser ist nach dem Debian-Format grundsätzlich zulässig, behauptet aber **keine nachgewiesene ausschließliche Rechteinhaberschaft über fremde Textteile**.
- Der vollständige AGPLv3-Lizenztext selbst nennt **Copyright 2007 Free Software Foundation, Inc.** und enthält eine eigenständige Erlaubnis zur unveränderten Vervielfältigung des Lizenzdokuments. Diese bereits enthaltene Angabe darf nicht als BuMaVory-Urheberschaft dargestellt werden.
- Der Maintainer berichtete, dass das Projekt mit Unterstützung von ChatGPT entwickelt wurde. Laut OpenAI-Nutzungsbedingungen stehen Output-Rechte im Verhältnis zwischen Nutzer und OpenAI grundsätzlich dem Nutzer zu, soweit rechtlich zulässig; das belegt weder urheberrechtliche Schutzfähigkeit jedes erzeugten Absatzes noch das Fehlen fremder Codeanteile. Fremde Quelltextvorlagen sind gesondert zu dokumentieren, soweit bekannt.
- Die kurzen Proxmox-Anker werden in `CODE-PROVENANCE-REVIEW.md` offengelegt. Eine dokumentierte fremde Implementierung oder ein nachweisbar entfernter fremder Copyright-Hinweis wurde im begrenzten Vergleich **nicht** identifiziert. Dies ist keine weltweite Plagiats- oder rechtsverbindliche Herkunftsprüfung.
- Bei tatsächlichen fremden Quelltextanteilen sind Rechteinhaber, Quelle, Versionsstand, Lizenz und Notices **konkret** zu ergänzen, statt willkürlich Personen/Firmen als Urheber des gesamten Projekts zu nennen.

## Freigabegatter

1. **Offen / Entscheidung des Maintainers:** Herkunftserklärung über eigene/mit ChatGPT entwickelte Teile und etwaige bewusst eingebrachte Vorlagen; falls externe Codevorlagen genutzt wurden, passende Rechte-/Copyright-Nachweise ergänzen. Ohne diese Erklärung kann die urheberrechtliche Freigabe nicht automatisch erfolgen.
2. **Offen / technische Restprüfung:** Wenn erforderlich `proxmox-widget-toolkit`, relevante ExtJS-Bestandteile und andere tatsächliche Vorlagen des GUI-Codes gegen die enthaltenen Implementierungen vergleichen. Der bisherige Vergleich umfasste nur `pve-manager` 9.2.25.
3. **Erledigt / Paketrevision:** `+docs2` mit eigener Prüfsumme, unverändertem Laufzeitcode und erfolgreichem Proxmox-Livetest. Ein bereits existierender Tag `v1.0.0-32` darf nicht überschrieben werden.
4. **Offen / History redaction:** Historische interne Dokumente vor `Public` redaktionell akzeptieren; keine vorschnelle Git-History-Umschreibung. Nur bei nachgewiesenen Geheimnissen zuerst die betroffenen Zugangsdaten erneuern und anschließend eine begründete History-Bereinigung planen.
5. **Offen / GitHub:** Privates Security-Reporting beim öffentlichen Start soweit verfügbar aktivieren, Release-Assets, Source-Stand, Dokumentation und SHA256 synchronisieren, anschließend bewusst öffentliche Sichtbarkeit freigeben.

**Nicht erneut offen:** Maintainer-Adresse im Control-Feld, Installation der exakt geprüften DEB vom 07.11.2026, die bestandenen 138 Regressionstests oder der vom Maintainer gemeldete E-Mail-Funktionstest.

## Referenzen

- Debian Copyright Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
- Proxmox Entwickler und Lizenzen: https://proxmox.com/en/about/open-source/developers
- OpenAI EU Terms: https://openai.com/de-DE/policies/eu-terms-of-use/
- GitHub Sichtbarkeit: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility

*Technische und redaktionelle Prüfung, keine anwaltliche Urheberrechtsfreigabe.*
