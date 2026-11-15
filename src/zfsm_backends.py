"""Read-only discovery of competing, unsupported snapshot schedulers."""
import re
import shutil
from pathlib import Path

ALTERNATIVES = ('sanoid','zrepl','zfs-autobackup','pyznap','znapzend','snapper')
def competing(root=Path('/'), which=shutil.which):
    """Conservative detection, never claim an unimplemented backend adapter."""
    found=set()
    for name in ALTERNATIVES:
        if which(name) or (root/'etc'/name).exists(): found.add(name)
    locations = ['etc/crontab','var/spool/cron/crontabs/root']
    for rel in ('etc/cron.d','etc/cron.hourly','etc/cron.daily','etc/cron.weekly','etc/cron.monthly',
                'etc/systemd/system','usr/lib/systemd/system','lib/systemd/system'):
        d=root/rel
        if d.is_dir(): locations.extend(str(p.relative_to(root)) for p in d.iterdir() if p.is_file())
    for rel in locations:
        p=root/rel
        if not p.is_file() or p.stat().st_size > 65536: continue
        lines='\n'.join(x for x in p.read_text(errors='replace').splitlines() if not x.lstrip().startswith('#'))
        for name in ALTERNATIVES:
            if re.search(r'(?<![\w-])'+re.escape(name)+r'(?![\w-])',lines) or name in p.name:
                found.add(name)
    return sorted(found)
