# Quality assurance – v1.0.0-32

## Live checks reported by the test host owner
- The exact final `pve-zfs-manager_1.0.0-32_all.deb` (SHA256 `af34d257abccf23bbd7635edfa16cf77b468f6a2e0ba399d3c88e5a39e73c7c2`) was installed as an APT upgrade from `1.0.0-32~rc1` on `pve-test` / Proxmox VE 9.2.25 on 2026-11-07.
- `zfsm version`, `status`, `check`, `services` and the GUI were confirmed working by the test host owner.
- Snapshot selection, multi-disk handling, batch deletion and translations were confirmed in preceding `1.0.0-27`–`1.0.0-31` releases.

## Source checks
- On 2026-11-09, 138/138 Python regression tests passed on source from the uploaded Git bundle (`main` at `d6cc529`).
- All 33 Python/Perl source files match the exact tested final .deb byte-for-byte.
- Complete reachable Git history was integrity-checked; heuristic text-only secret scanning found no confirmed credentials.

## Limits
- Proxmox VE 9.2.25 is the only live environment validated for this final release; no blanket support claim for all PVE 9.x hosts.
- Not all dark-mode, destructive and recovery error paths were exhaustively tested; maintain independent backups.
- Legal rights/provenance review is incomplete; **do not publish or switch repository visibility to Public until resolved**. See `LICENSING-REVIEW.md`.
- Maintainer reported a successful email function test on 2026-11-09; separate external delivery-and-reply evidence was not inspected.
