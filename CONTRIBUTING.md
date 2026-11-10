# Contributing / Mitarbeit

Thanks for your interest in BuMaVory ZFS Manager.

This repository is public as of 2026-11-10. Contributions may be proposed through pull requests and are subject to maintainer review; acceptance is not guaranteed. Contribute only work you have the right to license and attribute. The project applies `AGPL-3.0-only` to contributions for which the necessary rights exist; third-party provenance review is ongoing.

Before a future pull request:

1. Document what was changed and why.
2. Run the repository's existing automated tests and JavaScript syntax checks.
3. Validate changes on a **disposable** Proxmox VE test environment; do not test destructive operations on production data.
4. Provide a clear read-only preview for new snapshot write operations, preserve explicit confirmation, and document rollback limits.
5. Remove all personal data, internal IPs, real credentials, keys and test-server details from submissions.

Do not claim a feature is compatible with an untested Proxmox version. Please keep the existing GUI navigation and localization behavior intact.
