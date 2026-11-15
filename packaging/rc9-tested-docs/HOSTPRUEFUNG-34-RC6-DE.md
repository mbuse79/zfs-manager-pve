# BuMaVory ZFS Manager 1.0.0-34 RC6 – Hostprüfung und AutoSnap-Übernahme

**Testversion, kein öffentlicher Release.** Proxmox VE 9.x, auf PVE4 wurde bisher nur RC5 live bestätigt. RC6 wird zunächst nur offline getestet; destruktive Funktionen nicht ungeprüft verwenden.

## Zweck

Der ZFS Manager soll nicht mehrere Bereinigungssysteme parallel anlegen. Vor einer Installation untersucht der lokale Installer ausschließlich lesend:

- vorhandene `zfs-auto-snapshot`-Pakete und Cron-Aufträge einschließlich eigener Cron-Dateien und `root`-Crontab;
- doppelte Zeitpläne mit identischem `--label`;
- vorhandene systemd-Dienste und -Timer einschließlich manuell gestarteter `bashclub-zsync`-Programme;
- CheckZFS und andere Snapshot-Bereinigungsprogramme;
- native Proxmox-Replikationsaufträge über `pvesr list`.

Es werden nur Dienstenamen und Cron-Dateiquellen ausgegeben, **keine** `ExecStart`-Argumente, Zugangsdaten oder Replikationskonfigurationen. Eine erkannte systemd-Unit ist nicht automatisch ein nachweislich erfolgreicher Dienstlauf.

## Vorhandenes übernehmen

- AutoSnap ist **Pflichtpaket**. Bereits vorhandenes AutoSnap wird nicht erneut installiert und vorhandene Einstellungen werden nicht überschrieben.
- Fehlt das Paket, wird im ZIP-Installer mit einer APT-Simulation geprüft und anschließend nur die AutoSnap-Installation ohne allgemeines Upgrade durchgeführt.
- Bereits erkannte AutoSnap-Cron-Aufträge werden übernommen; der Installer erzeugt keine zweite AutoSnap-Planung. Bewusst deaktivierte Zeitpläne bleiben deaktiviert.
- Bei doppelt geplanten Arten oder unbekannten AutoSnap-Aufträgen stoppt der Installer vor der ZFS-Manager-DEB-Installation, um Konflikte zu verhindern.
- Fehlt der Paketstatus, aber eine manuell installierte AutoSnap-Binärdatei oder Cron-Regel ist vorhanden, stoppt der Installer **vor APT**, statt diese Installation zu überschreiben.
- Die bestehenden Aufbewahrungsregeln bleiben im ZFS Manager bearbeitbar, soweit sie dem geprüften unterstützten Format entsprechen.
- `checkzfs`, `zsync`, `sanoid`, `syncoid`, `zrepl` und native PVE-Replikation sind **keine** ZFS-Manager-Pflichtkomponenten. Sie werden nur erkannt. Der ZFS Manager erstellt, stoppt oder verändert **keine Replikationsjobs**. Deren Verwaltung ist Aufgabe des zukünftigen unabhängigen BuMaVory ZFS Replication Managers.
- Snapshot-Notfallbereinigung behält sämtliche Schutzregeln. Die automatische Löschung ist standardmäßig **AUS**.

## Diagnostik nach Installation

```sh
zfsm inventory
zfsm inventory --json
zfsm version
zfsm status
zfsm emergency status
```

In der Weboberfläche steht unter der vorhandenen AutoSnap-Aufbewahrung zusätzlich **„Vorhandene Dienste (nur Erkennung)“**. Die Anzeige ist rein lesend und keine Replikationsverwaltung.

## Grenzen

Die Erkennung wertet Paketstatus, Cron-Quellen, systemd-Unit-Dateien und native PVE-Replikationslisten aus. Undokumentierte Skripte, die ausschließlich unter fremden Verzeichnissen oder in nicht erkannten Supervisors laufen, können unentdeckt bleiben. Fehlende `zsync`-Pakete sind kein Beweis für fehlende zsync-Dienste.

Bei unbekannter, doppelter oder nicht zuverlässig ermittelbarer Bereinigungsplanung keine zweite automatische Bereinigung hinzufügen. Eine echte automatische Löschung wird in dieser Version nicht standardmäßig aktiviert.

## Teststand

Die Python-/Perl-/JavaScript-bezogenen Offline-Regressionen einschließlich isoliertem RC5-auf-RC6-Upgrade werden vor Ausgabe des Testpakets durchgeführt. Ein Proxmox-Livetest auf PVE4 ist erforderlich, bevor die Version als stabil gelten kann.
