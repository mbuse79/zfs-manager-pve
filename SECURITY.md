# Security policy / Sicherheit

## Scope

v1.0.0-32 is a technical final build. The exact final Debian package was installed and GUI/CLI-tested on Proxmox VE 9.2.25 on 2026-11-07. This is independent community software, not an official Proxmox product. No support or compatibility guarantee applies to other untested versions.

## Reporting a vulnerability

**Do not post exploits, credentials or sensitive system details in public GitHub issues.** Contact the maintainers privately at **[bumavory@buse.rocks](mailto:bumavory@buse.rocks)**. The maintainer reported a successful email function test on 2026-11-09; separate external sender/response evidence has not been reviewed in this audit. GitHub private vulnerability reporting should also be enabled before public launch, if available.

## Operational risks

- Snapshot deletion and rollback can lead to permanent data loss.
- Operations spanning multiple datasets/disks are not atomic.
- Keep independent off-host backups and test recovery.
- Restrict management access to authorized Proxmox administrators. Do not expose the Proxmox management interface directly to the public internet.
- Verify distribution origin and release hashes before installing packages with root privileges.

## Deutsch

Sicherheitslücken nicht mit Exploit-Details in öffentlichen Issues melden. Meldungen bitte vertraulich an **bumavory@buse.rocks** senden. Der Maintainer meldete am 09.11.2026 einen erfolgreichen E-Mail-Funktionstest; ein separater externer Zustell- und Antwortnachweis wurde bei dieser Prüfung nicht eingesehen. Destruktive Snapshot-Aktionen nur mit unabhängigen Sicherungen und auf geprüften Systemen durchführen.
