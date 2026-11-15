from pathlib import Path
base=Path('/mnt/data/zfsm_rc7_build')
p=base/'src/zfsm_host_audit.py'
s=p.read_text()
s=s.replace("MAX_FILE_BYTES = 64 * 1024\n", """MAX_FILE_BYTES = 64 * 1024
# Cron scripts routinely check that AutoSnap exists before invoking it.
# That guard is not a schedule and must not count as an 'unknown' rule.
PROBE_RE = re.compile(r'(?i)\\b(?:which|command\\s+-v|type\\s+-[a-z]+|test\\s+-x)\\s+(?:/usr/sbin/)?zfs-auto-snapshot\\b')


def autosnap_invocation(line):
    if not AUTOSNAP_RE.search(line):
        return False
    # A normal invocation with --label is never dismissed by a preceding
    # 'which' guard on the same cron.d line.
    if LABEL_RE.search(line) or KEEP_RE.search(line):
        return True
    if PROBE_RE.search(line):
        return False
    return True  # Unknown real command: require manual review rather than guessing.


def active_entries(text):
    return [(n, line.strip()) for n, line in enumerate(text.splitlines(), 1)
            if line.strip() and not line.lstrip().startswith('#')]
""")
s=s.replace('            for ln in active_lines(load_text(f)):', '            for lineno, ln in active_entries(load_text(f)):')
s=s.replace('                if not AUTOSNAP_RE.search(ln): continue\n', '                if not autosnap_invocation(ln): continue\n')
s=s.replace("'source':path_label(f), 'standard':", "'source':path_label(f), 'line':lineno, 'standard':")
s=s.replace('        for ln in active_lines(load_text(f)):', '        for lineno, ln in active_entries(load_text(f)):')
s=s.replace('            if not AUTOSNAP_RE.search(ln): continue\n', '            if not autosnap_invocation(ln): continue\n')
s=s.replace("'source':path_label(f),'standard':False", "'source':path_label(f),'line':lineno,'standard':False")
s=s.replace('    for ln in active_lines(root_crontab):', '    for lineno, ln in active_entries(root_crontab):')
s=s.replace('        if not AUTOSNAP_RE.search(ln):continue', '        if not autosnap_invocation(ln):continue')
s=s.replace("'source':'root crontab','standard':False", "'source':'root crontab','line':lineno,'standard':False")
s=s.replace("duplicate_labels = sorted(k for k,v in count.items() if v > 1)","duplicate_labels = sorted(k for k,v in count.items() if k!='unknown' and v > 1)")
p.write_text(s)
# version references source and test expectations, excluding historical fixtures:
for file in [base/'src/universal.py',base/'src/zfsm_cli.py',base/'build_deb.sh',base/'install-local.sh'] + list((base/'tests').glob('test_*.py')):
    txt=file.read_text()
    txt=txt.replace('1.0.0-34~rc6','1.0.0-34~rc7').replace('1.0.0-34-rc6-dynamic-compat-installer','1.0.0-34-rc7-dynamic-compat-installer')
    file.write_text(txt)
