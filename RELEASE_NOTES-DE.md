# BuMaVory ZFS Manager 1.1

1.1 veröffentlicht den vom Betreiber bestätigten RC10-Fix2-Funktionsstand mit
Einheitlichkeit von Paket, CLI, GUI und Cluster-Verteilung. Bewusste Knotenauswahl,
Vorprüfung, bestätigte Installation und vorhandene Root-SSH-Vertrauensbeziehungen.
Keine automatische Verteilung oder Konfigurationssynchronisierung.

Der Betreiber bestätigte den Fix2-Praxistest auf PVE 9.2.26 und 9.2.21. Das genaue
1.1-DEB wird neu gebaut und automatisiert geprüft, nicht erneut auf realen Hosts
installiert. Reale Offline-Rettung, Abbruch während dpkg und parallele reale
Steuerknoten bleiben ungeprüft. Siehe RELEASE-QA.md und docs/INSTALL-1.1.md.

Vollständige ZIP verwenden, damit die geprüfte Cluster-Verteilungskopie registriert
wird. Bestehende Sicherheitsregeln, Konfigurationen und Zeitpläne bleiben erhalten.
