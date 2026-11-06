# Third-party components and attribution review

The application integrates into an existing Proxmox VE host and relies on system dependencies including:

- Proxmox Virtual Environment — upstream project; **not** owned by BuMaVory. https://www.proxmox.com/
- OpenZFS / `zfsutils-linux` — host dependency. https://openzfs.org/
- `zfs-auto-snapshot` — host dependency; check its installed Debian copyright file.
- Perl, Python and Debian/system libraries — host dependencies.

This list is informational, **not a completed third-party code audit**. The installer integrates with existing Proxmox GUI and API files. Before distributing source or packages publicly, audit any bundled/adapted upstream snippets, preserve their licensing notices, and check license compatibility.
