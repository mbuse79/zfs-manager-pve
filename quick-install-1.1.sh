#!/usr/bin/env bash
# BuMaVory ZFS Manager 1.1. AGPL-3.0-only for project contributions.
# Version-pinned complete bundle; source and licenses accompany release v1.1.
set -Eeuo pipefail
exec python3 - "$@" <<'PYQUICK'
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.request

BASE = 'https://github.com/mbuse79/zfs-manager-pve/releases/download/v1.1/'
ZIP_URL = BASE + 'BuMaVory-ZFS-Manager-1.1.zip'
ZIP_SHA = 'fcdde5fba9bbcf29ca2a5463a586de65689a014f1f9e47bd81040720957873ed'
BOOT_URL = BASE + 'bootstrap-1.1.sh'
BOOT_SHA = '45c447c682b0ed325e5a9c0aae84c13b1af6b1422b54ce28b8df956bd0e62403'


def download(url, path, digest, limit):
    h = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=60) as response:
        if not response.url.startswith('https://'):
            raise ValueError('HTTPS redirect required / HTTPS-Weiterleitung erforderlich')
        with path.open('wb') as f:
            size = 0
            while True:
                data = response.read(1024*1024)
                if not data:
                    break
                size += len(data)
                if size > limit:
                    raise ValueError('Download too large / Download zu groß')
                h.update(data)
                f.write(data)
    if h.hexdigest() != digest:
        raise ValueError('SHA256 mismatch; no execution / SHA256 falsch; keine Ausführung')


def main(argv=None):
    parser = argparse.ArgumentParser(description='BuMaVory ZFS Manager 1.1 — complete verified ZIP / vollständige geprüfte ZIP')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check-only', action='store_true')
    group.add_argument('--download-only', action='store_true')
    parser.add_argument('--lang', choices=('de','en'), default='de')
    args = parser.parse_args(argv)
    if os.geteuid() != 0:
        raise ValueError('Root-Rechte erforderlich / root required')
    p = subprocess.run(['pveversion'], capture_output=True, text=True, check=True)
    if not re.match(r'^pve-manager/9\.\d+\.\d+/', p.stdout):
        raise ValueError('Nur PVE 9.x / PVE 9.x required')
    if args.download_only:
        fd, name = tempfile.mkstemp(prefix='BuMaVory-ZFS-Manager-1.1-', suffix='.zip')
        os.close(fd)
        path = Path(name)
        try:
            download(ZIP_URL, path, ZIP_SHA, 100*1024*1024)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        print(str(path))
        return 0
    with tempfile.TemporaryDirectory(prefix='bmv-zfsm-1.1-') as td:
        path = Path(td)/'bootstrap-1.1.sh'
        download(BOOT_URL, path, BOOT_SHA, 1024*1024)
        cmd = ['bash', str(path), ZIP_URL, ZIP_SHA, '--lang', args.lang]
        if args.check_only:
            cmd.append('--check-only')
        return subprocess.run(cmd, check=False).returncode


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError,OSError,subprocess.SubprocessError) as exc:
        print('STOP: '+str(exc), file=sys.stderr)
        raise SystemExit(1)
PYQUICK
