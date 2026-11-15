# RC8 Installerfix 1 – 13.11.2026

Der erste RC8-Einstieg hat Neuinstallationen bestanden, blockierte jedoch das
gewünschte RC7→RC8-Upgrade: APT --no-upgrade überspringt auch den ausdrücklich
angegebenen, bereits installierten Manager. Dadurch fehlte dessen Inst-Zeile
im streng geprüften Simulationsplan.

Diese Ursache wurde neu mit dem echten APT-Solver und einer privaten dpkg-
Statusdatei reproduziert. Kein Paket wurde dabei auf dem Runner installiert.
Die Simulation verwendet jetzt --no-remove und --no-install-recommends ohne
--no-upgrade. Der Plan muss weiterhin exakt den Manager und ausschließlich
fehlende mitgelieferte Abhängigkeiten enthalten. Andere Installationen,
Konfigurationen oder Entfernungen bleiben verboten. Die tatsächliche Ausführung
installiert weiterhin nur die geprüften lokalen DEBs mittels dpkg.

Keine PVE-Minor-/Patch-Rückfrage: PVE 9.x bleibt zulässig, reale unbekannte
GUI/API-Strukturen werden weiterhin abgewiesen. Keine pauschale Behauptung,
dass jede unbekannte Proxmox-Struktur bereits getestet ist.

Unverändert bleiben das bereits auf der Test-PVE installierte DEB, alle
Laufzeitquellen, Snapshot-/Gastschutz und Bootstrap. Es wurde bewusst kein
neues DEB mit derselben Version erzeugt. Geändert sind nur der äußere Installer,
seine Regressionen und diese Ergänzung. Das ursprüngliche ZIP bleibt erhalten.

DEB SHA256:
904bed03e98bea41f13fb704d393dba229fe46c592ad554fcbfb77a9d13c12ce
Bootstrap SHA256:
26a4384fcf9199dee2236fb269e0f101aae30d58dbb490d61da517b3dfc7d69b

Neuer Lauf: 234 bestanden, 9 übersprungen, 5 abgewählt im normalen Benutzerlauf;
18 bestanden im separaten fakeroot-Lauf (4 überlappend).
Gesamt: 248 unterschiedliche Tests erfolgreich. Warnung im ZIP-Negativtest
wegen absichtlich doppeltem Namen bleibt erwartet. Logs unter qa/installerfix1-*.
Der neue APT-Solver-Test ergänzt die zuvor ausschließlich gemockte Prozessprüfung.
Das erste RC8-Paket hatte hierfür eine Testlücke; der neue Nachweis korrigiert sie.

Für pve4 das neue Installerfix1-ZIP mit seiner NEUEN Prüfsumme verwenden.
Zuerst --check-only, erst nach Erfolg die Installation starten. Der alte
Bootstrap kann unverändert benutzt werden. Auf der Test-PVE muss das bereits
installierte identische RC8-DEB wegen dieses äußeren Installerfixes nicht ersetzt
werden. Echte Bestätigung des pve4-Upgrades weiterhin offen, keine Veröffentlichung.
