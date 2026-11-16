# BuMaVory ZFS Manager 1.1: ZFS snapshots inside the Proxmox UI

Disclosure: I maintain this independent community project; it is not an official
Proxmox product.

I wanted pools, VM/LXC snapshots and retention in the existing Proxmox node view,
without a separate portal. BuMaVory ZFS Manager 1.1 provides grouped guest disks,
a separate dataset tab, CAP/FRAG overview, reviewed AutoSnap retention changes and
optional, confirmed cluster installation. GUI and CLI are available in German and English.

Cluster rollout uses the existing Proxmox root SSH trust and keeps each node's
settings/schedules local. Emergency cleanup is OFF by default; existing scheduled
retention still applies. Destructive snapshot operations retain previews and
protection checks. Keep independent backups and try it on a test host first.

The operator confirmed the Fix2 predecessor's cluster rollout on PVE 9.2.26 and
9.2.21; 1.1 was rebuilt and automatically checked. The QA report separates that
host evidence from fixture tests and untested scenarios. Screenshots/video are
labelled sample data using the real UI.

- [Source, screenshots and demo](https://github.com/mbuse79/zfs-manager-pve)
- [Release and full ZIP](https://github.com/mbuse79/zfs-manager-pve/releases/tag/v1.1)
- [Installation](https://github.com/mbuse79/zfs-manager-pve/blob/main/docs/INSTALL-1.1.md)

Feedback on the workflow and other PVE-9 configurations is welcome. GitHub has
forms for reproducible bugs, feature requests and compatibility reports.
