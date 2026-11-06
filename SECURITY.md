# Security policy / Sicherheit

## Scope

v1.0.0-32 is a technical final build. The RC1 was tested on Proxmox VE 9.2.25. This is independent community software, not an official Proxmox product. No support or compatibility guarantee applies to other untested versions.

## Reporting a vulnerability

**Do not post exploits, credentials or sensitive system details in public GitHub issues.** A private reporting channel and real maintainer contact have **not yet been configured**. Before making this repository public, enable GitHub private vulnerability reporting (if available) and publish a valid security contact.

## Operational risks

- Snapshot deletion and rollback can lead to permanent data loss.
- Operations spanning multiple datasets/disks are not atomic.
- Keep independent off-host backups and test recovery.
- Restrict management access to authorized Proxmox administrators. Do not expose the Proxmox management interface directly to the public internet.
- Verify distribution origin and release hashes before installing packages with root privileges.

## Deutsch

Sicherheitslücken nicht mit Exploit-Details in öffentlichen Issues melden. Vor der öffentlichen Freigabe müssen ein vertraulicher Meldeweg und ein echter Ansprechpartner eingerichtet werden. Destruktive Snapshot-Aktionen nur mit unabhängigen Sicherungen und auf geprüften Systemen durchführen.
