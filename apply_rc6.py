from pathlib import Path
p=Path(__file__).parent

def replace(path, old, new, count=1):
    f=p/path
    s=f.read_text()
    assert s.count(old)==count,(f,old[:100],s.count(old))
    f.write_text(s.replace(old,new,count))

replace('src/zfsm_cli.py',"VERSION='1.0.0-34~rc5'", "VERSION='1.0.0-34~rc6'")
replace('src/zfsm_cli.py'," 'emergency':'Warnstufen, Notfallvorschau und geschuetzte Snapshot-Bereinigung',", " 'emergency':'Warnstufen, Notfallvorschau und geschuetzte Snapshot-Bereinigung',\n 'inventory':'Bestehende AutoSnap- und ZFS-Dienste sicher erkennen (nur lesend)',")
replace('src/zfsm_cli.py'," 'emergency':'Capacity alerts, emergency preview and guarded cleanup',", " 'emergency':'Capacity alerts, emergency preview and guarded cleanup',\n 'inventory':'Read-only audit of existing AutoSnap and ZFS services',")
replace('src/zfsm_cli.py',"'capacity','emergency')", "'capacity','emergency','inventory')")
replace('src/zfsm_cli.py',"parser.add_argument('--json',action='store_true',help='JSON for zfsm capacity only')", "parser.add_argument('--json',action='store_true',help='JSON for zfsm capacity/inventory')")
replace('src/zfsm_cli.py',"if (args.force and args.command!='repair') or (args.json and args.command!='capacity'):", "if (args.force and args.command!='repair') or (args.json and args.command not in ('capacity','inventory')):")
replace('src/zfsm_cli.py',"    if args.command=='capacity':\n", "    if args.command=='inventory':\n        from zfsm_host_audit import discover, main as audit_main\n        return audit_main(['--json'] if args.json else [])\n    if args.command=='capacity':\n")
replace('src/universal.py',"VERSION = '1.0.0-34-rc5-dynamic-compat-installer'", "VERSION = '1.0.0-34-rc6-dynamic-compat-installer'")
old="""            for f in ('/etc/cron.d/zfs-auto-snapshot','/etc/cron.hourly/zfs-auto-snapshot', '/etc/cron.daily/zfs-auto-snapshot','/etc/cron.weekly/zfs-auto-snapshot','/etc/cron.monthly/zfs-auto-snapshot'):
                if not self.path(f).is_file(): raise InstallError('Cron-Regel fehlt: '+f)
"""
new="""            # Detect existing schedules, including administrator-defined paths.
            # Never create a second timer or overwrite a pre-existing policy.
            from zfsm_host_audit import discover
            audit=discover()
            if not audit['autosnap']['schedules']:
                raise InstallError('AutoSnap vorhanden, aber kein Zeitplan gefunden; manuell prüfen')
            if audit['autosnap']['duplicate_labels']:
                raise InstallError('Doppelte AutoSnap-Aufträge; vor Installation prüfen: '+
                                   ', '.join(audit['autosnap']['duplicate_labels']))
"""
replace('src/universal.py',old,new)
replace('build_deb.sh',"# Experimental 1.0.0-34 RC5", "# Experimental 1.0.0-34 RC6")
replace('build_deb.sh',"PACKAGE_VERSION='1.0.0-34~rc5'", "PACKAGE_VERSION='1.0.0-34~rc6'")
replace('install-local.sh',"1.0.0-34 RC5", "1.0.0-34 RC6")
replace('install-local.sh',"1.0.0-34~rc5", "1.0.0-34~rc6",2)
replace('install-local.sh',"/tmp/zfsm-autosnap-rc5.", "/tmp/zfsm-autosnap-rc6.")
# Inspect and classify existing services prior to Apt/dpkg. Keep audit strictly read-only.
replace('install-local.sh',"step 'Pflichtkomponente AutoSnap prüfen'", """step 'Vorhandene ZFS-Dienste und Zeitpläne erkennen (nur lesend)'
AUDITOR="$TMP/pkg/usr/lib/pve-zfs-manager/zfsm_host_audit.py"
[[ -f "$AUDITOR" && ! -L "$AUDITOR" ]] || die 'Host-Inventur im DEB fehlt.'
python3 "$AUDITOR" --json > "$TMP/inventory-before.json" || die 'Host-Inventur fehlgeschlagen, keine Aenderungen.'
python3 - "$TMP/inventory-before.json" <<'PYINVENTORY'
import json,sys
with open(sys.argv[1],encoding='utf-8') as fh: report=json.load(fh)
a=report['autosnap'];r=report['replication']
print('AutoSnap: %s | %d vorhandene Zeitpläne' % (a['package'],a['schedule_count']))
print('Externe Replikation: %d Systemd-Units, %d native PVE-Aufträge – nur Erkennung' %
      (len(r['systemd_units']),r['native_pve_jobs']))
for warning in report['warnings'][:12]: print('HINWEIS:',warning)
PYINVENTORY

step 'Pflichtkomponente AutoSnap prüfen'""")
old="""for file in "${CRON_FILES[@]}"; do
  [[ -f "$file" ]] || die "AutoSnap-Cron-Regel fehlt: $file. Keine automatische Änderung einer Admin-Konfiguration."
done
step 'Vorhandene AutoSnap-Regeln respektieren'
echo 'PASS: AutoSnap und Zeitpläne vorhanden. Keine Cron-Datei wird vom RC5-Installer überschrieben.'
"""
new="""# Re-scan after optional APT installation. Custom existing schedules are adopted;
# never install duplicate timers or silently overwrite administrators' cron jobs.
python3 "$AUDITOR" --json > "$TMP/inventory-after.json" || die 'Host-Inventur nach AutoSnap-Installation fehlgeschlagen.'
python3 - "$TMP/inventory-after.json" <<'PYVERIFY'
import json,sys
with open(sys.argv[1],encoding='utf-8') as fh: d=json.load(fh)
a=d['autosnap']
if a['package'] != 'installed' or not a['binary'] or not a['schedules']:
    print('STOPP: AutoSnap-Paket oder Zeitplan fehlt; keine automatische Änderung einer Admin-Konfiguration.',file=sys.stderr)
    sys.exit(1)
if a['duplicate_labels']:
    print('STOPP: Doppelte AutoSnap-Labels: '+', '.join(a['duplicate_labels']),file=sys.stderr)
    sys.exit(1)
if any(s['keep'] is None or s['label']=='unknown' for s in a['schedules']):
    print('STOPP: Vorhandene AutoSnap-Regel nicht eindeutig; manuell prüfen.',file=sys.stderr)
    sys.exit(1)
print('PASS: AutoSnap Zeitpläne übernommen, keine zusätzliche Bereinigung erstellt.')
PYVERIFY
step 'Vorhandene AutoSnap-Regeln respektieren'
"""
replace('install-local.sh',old,new)
# CLI code and frontend provenance docs
f=p/'build_deb.sh';s=f.read_text();needle='cp "$HERE/POOLALARME-34-RC4-DE.md" "$HERE/AUTOSNAP-34-RC5-DE.md" "$BUILD/usr/share/doc/pve-zfs-manager/"';assert needle in s;s=s.replace(needle,needle+'\ncp "$HERE/HOSTPRUEFUNG-34-RC6-DE.md" "$BUILD/usr/share/doc/pve-zfs-manager/"');f.write_text(s)
print('source/installer version and audit integration updated')
