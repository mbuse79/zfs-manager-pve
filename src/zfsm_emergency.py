#!/usr/bin/env python3
"""BuMaVory ZFS emergency guard and capacity notifier.

No deletion is automatic unless the administrator opts in for a named pool.
Only zfs-auto-snapshot labels are eligible; never prune the final snapshot
of a label on any dataset. Unknown ownership and replica destinations fail
closed. Operations re-check inventories and use exact `zfs destroy` targets.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import socket

import zfsm_notify

LABELS = ('frequent', 'hourly', 'daily', 'weekly', 'monthly', 'yearly')
AUTO = re.compile(r'^zfs-auto-snap_(frequent|hourly|daily|weekly|monthly|yearly)-[A-Za-z0-9_.:-]+$')
SAFE = re.compile(r'^[A-Za-z0-9_.:~-]+(?:/[A-Za-z0-9_.:~-]+)*$')
SNAP = re.compile(r'^[A-Za-z0-9_.:-]{1,128}$')
GUEST = re.compile(r'^(vm|subvol)-(\d+)-disk-\d+(?:-[A-Za-z0-9_.-]+)?$')
REPLICA = re.compile(r'(replik|replic|zsync|backup|smoketest|pbs)', re.I)
CONFIG = Path('/etc/pve-zfs-manager/emergency.json')
ALERT_FILE = Path('/var/lib/pve-zfs-manager/emergency-alerts.json')
LOCK = Path('/run/lock/pve-zfs-manager-emergency.lock')
GUEST_POLICY = Path('/usr/local/libexec/pve-zfs-manager/guest_policy.py')
LIMIT = 15
MAX_SNAPSHOTS = 10000
MAX_DATASETS = 10000
MIN_DATASET_FREE = 1024**3

class EmergencyError(ValueError):
    pass


def command(args, *, timeout=30):
    cp = subprocess.run(args, text=True, capture_output=True, timeout=timeout, check=False)
    if cp.returncode or len(cp.stdout.encode('utf-8')) > 8_000_000:
        raise EmergencyError(f"Abfrage fehlgeschlagen: {args[0]} (Exit {cp.returncode}): {cp.stderr[:240]}")
    return cp.stdout


def pools():
    raw = command(['/usr/sbin/zpool', 'list', '-H', '-p', '-o', 'name,size,alloc,free,health'])
    data = []
    for line in raw.splitlines():
        cols = line.split('\t')
        if len(cols) != 5:
            raise EmergencyError('Ungueltige Pool-Statistik')
        name, size, allocated, free, health = cols
        if not SAFE.fullmatch(name) or '/' in name or not all(x.isascii() and x.isdigit() for x in (size,allocated,free)):
            raise EmergencyError('Ungueltige Pool-Daten')
        total, used, available = int(size), int(allocated), int(free)
        if total <= 0 or used > total or available > total:
            raise EmergencyError('Ungueltige Pool-Kapazitaet')
        percent = round(100 * used / total, 2)
        data.append({'name':name,'percent':percent,'allocated':used,'free':available,'total':total,'health':health,
                     'severity':'emergency' if used*100 >= total*95 else
                        'critical' if used*100 >= total*90 else
                        'warning' if used*100 >= total*80 else 'normal'})
    return data


def policy(path=CONFIG):
    default = {'auto_enabled':False,'auto_pools':[],'batch_count':15,'target_percent':78,
               'excluded_datasets':[],'notify_repeat_minutes':60}
    if not path.exists():
        return default
    stat = path.lstat()
    if not path.is_file() or path.is_symlink() or stat.st_uid != 0 or stat.st_mode & 0o077 or stat.st_size > 16384:
        raise EmergencyError('Unsichere Notfall-Konfigurationsdatei (root:0600 erforderlich)')
    raw = json.loads(path.read_text('utf-8'))
    if not isinstance(raw,dict) or set(raw)-set(default):
        raise EmergencyError('Unbekannter Eintrag in der Notfall-Konfiguration')
    cfg = dict(default, **raw)
    if type(cfg['auto_enabled']) is not bool or type(cfg['batch_count']) is not int or not 1 <= cfg['batch_count'] <= 15:
        raise EmergencyError('Ungueltige automatische Bereinigungsregel')
    if type(cfg['target_percent']) is not int or not 60 <= cfg['target_percent'] <= 79:
        raise EmergencyError('Ungueltiger Zielwert (60-79%)')
    if type(cfg['notify_repeat_minutes']) is not int or not 5 <= cfg['notify_repeat_minutes'] <= 1440:
        raise EmergencyError('Ungueltiges Wiederholungsintervall')
    for key in ('auto_pools','excluded_datasets'):
        if not isinstance(cfg[key],list) or len(cfg[key]) > 200 or any(not isinstance(x,str) or not SAFE.fullmatch(x) for x in cfg[key]):
            raise EmergencyError('Ungueltige Liste in Notfall-Konfiguration: '+key)
    return cfg


def save_policy(cfg, path=CONFIG):
    if os.geteuid() != 0:
        raise EmergencyError('Nur root darf die Notfall-Konfiguration aendern')
    # Validate the configuration before writing it.
    path.parent.mkdir(parents=True,exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.zfsm-emergency-',dir=str(path.parent))
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as out:
            json.dump(cfg,out,sort_keys=True);out.write('\n');out.flush();os.fsync(out.fileno())
        os.chmod(name,0o600)
        policy(Path(name))
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def dataset_report():
    """Read-only per-dataset quota/refquota and effective headroom monitoring.

    Dataset available bytes may be limited by its ancestors; do not present
    it as the physical pool free space. Quota/refquota are independent limits.
    """
    raw=command(['/usr/sbin/zfs','list','-H','-p','-t','filesystem,volume',
                 '-o','name,type,used,referenced,avail,quota,refquota'])
    issues=[];checked=0
    for line in raw.splitlines():
        cols=line.split('\t')
        if len(cols)!=7:
            raise EmergencyError('Ungueltige Dataset-Kapazitaetsdaten')
        name,kind,used,referenced,available,quota,refquota=cols
        if not SAFE.fullmatch(name) or kind not in ('filesystem','volume'):
            raise EmergencyError('Ungueltiger Datasetname oder Typ')
        for item in (used,referenced,available):
            if not item.isascii() or not item.isdigit():
                raise EmergencyError('Ungueltige numerische Dataset-Eigenschaft')
        limits=[]
        for label,value,consumed in (('quota',quota,int(used)),('refquota',refquota,int(referenced))):
            if value in ('none','-','0'):
                continue
            if not value.isascii() or not value.isdigit() or int(value)<0:
                raise EmergencyError('Ungueltiges Dataset-Limit')
            cap=int(value)
            if cap>0:
                pct=round(100*consumed/cap,2)
                if pct>=80:
                    sev='emergency' if pct>=95 else 'critical' if pct>=90 else 'warning'
                    limits.append((pct,{'dataset':name,'pool':name.split('/')[0],
                        'severity':sev,'percent':pct,'metric':label,'used':consumed,
                        'limit':cap,'available':int(available)}))
        if limits:
            issues.append(max(limits,key=lambda v:v[0])[1])
        elif '/' in name and int(used)>=MIN_DATASET_FREE and int(available)<MIN_DATASET_FREE:
            free=int(available)
            severity='emergency' if free<64*1024**2 else 'critical' if free<256*1024**2 else 'warning'
            issues.append({'dataset':name,'pool':name.split('/')[0],
                'severity':severity,'percent':None,'metric':'available',
                'used':int(used),'limit':None,'available':free})
        checked+=1
        if checked>MAX_DATASETS:
            raise EmergencyError('Zu viele Datasets fuer die Kapazitaetspruefung')
    rank={'emergency':3,'critical':2,'warning':1}
    issues.sort(key=lambda item:(-rank[item['severity']],-(item['percent'] or 0),item['dataset']))
    grouped=defaultdict(list)
    for item in issues:
        grouped[item['pool']].append(item)
    per_pool={name:{'severity':max((v['severity'] for v in group),key=lambda x:rank[x]),
                    'count':len(group),'samples':group[:5]}
              for name,group in grouped.items()}
    return {'checked':checked,'total_alerts':len(issues),'issues':issues[:50],
            'per_pool':per_pool,'truncated':len(issues)>50}


def read_alert_state(path=None):
    path=ALERT_FILE if path is None else path
    if not path.exists():return {}
    st=path.lstat()
    if not path.is_file() or path.is_symlink() or st.st_uid!=0 or st.st_mode & 0o077 or st.st_size>65536:
        raise EmergencyError('Unsichere Warnzustandsdatei')
    value=json.loads(path.read_text('utf-8'))
    if not isinstance(value,dict):raise EmergencyError('Warnzustand ungueltig')
    return value


def notification_state(active_pools=()):
    """Show delivery failures only for an active ZFS pool alarm.

    Older versions stored quota/refquota alerts as dataset:<pool> and
    monitor:datasets. They must not be displayed as pool emergencies.
    """
    info=zfsm_notify.inspect_targets()
    try:
        states=read_alert_state()
        relevant={'pool:'+name for name in active_pools}
        errors=[v.get('last_error') for key,v in states.items()
                if key in relevant and isinstance(v,dict) and v.get('last_error')]
        info['last_error']=errors[0] if errors else None
    except (EmergencyError,OSError,ValueError) as exc:
        info['last_error']='Warnzustand nicht lesbar: '+str(exc) if active_pools else None
    return info


def status():
    # Guest quotas/refquotas are guest sizing policies, NOT physical ZFS pool
    # capacity alerts. No dataset scan and no snapshot deletion in this path.
    capacity=pools()
    active={p['name'] for p in capacity if p['severity']!='normal'}
    return {'schema':3,'pools':capacity,
            'notification':notification_state(active),'policy':policy(),
            'auto_cleanup_default':'disabled',
            'thresholds':{'warning':80,'critical':90,'emergency':95}}


def parse_snapshots(text, pool):
    out=[]
    for line in text.splitlines():
        cols=line.split('\t')
        if len(cols)!=4 or '@' not in cols[0]:
            raise EmergencyError('Ungueltiger Snapshot-Datensatz')
        name, created, refs, clones=cols
        ds,snap=name.split('@',1)
        if not SAFE.fullmatch(ds) or not SNAP.fullmatch(snap) or not (ds == pool or ds.startswith(pool+'/')):
            raise EmergencyError('Snapshotname oder Poolzuordnung ungueltig')
        if not created.isascii() or not created.isdigit() or not refs.isascii() or not refs.isdigit():
            raise EmergencyError('Ungueltige ZFS-Snapshot-Eigenschaften')
        label=AUTO.fullmatch(snap)
        out.append({'name':name,'dataset':ds,'snapshot':snap,'label':label.group(1) if label else None,
                    'creation':int(created),'userrefs':int(refs),'clones':clones,
                    'blocked':int(refs)>0 or clones not in ('-','', 'none')})
        if len(out)>MAX_SNAPSHOTS:raise EmergencyError('Zu viele Snapshots')
    return out


def excluded_dataset(dataset, pool, exclusions=(), *, rescue_system=False):
    if dataset == pool: return True  # conservative: top-level pool root
    parts=dataset.split('/')[1:]
    if any(REPLICA.search(part) for part in parts): return True
    if any(part.lower() in (('boot','efi','grub') if rescue_system else ('root','boot','efi','grub')) for part in parts): return True
    if any(dataset == e or dataset.startswith(e+'/') for e in exclusions): return True
    return False


def owned_disks():
    """Guest-policy resolver is fail-closed; do not guess ownership from names."""
    raw=command(['/usr/bin/python3',str(GUEST_POLICY),'list'],timeout=28)
    rows=json.loads(raw)
    if not isinstance(rows,list):raise EmergencyError('Gastzuordnung nicht lesbar')
    groups=defaultdict(dict)
    by_ds={}
    for row in rows:
        if not isinstance(row,dict) or row.get('guest') not in ('lxc','vm') or type(row.get('vmid')) is not int:
            raise EmergencyError('Ungueltige Gastzuordnung')
        ds=row.get('dataset')
        if not isinstance(ds,str) or not SAFE.fullmatch(ds) or ds in by_ds:
            raise EmergencyError('Unbekannte/mehrdeutige Gastzuordnung')
        key=(row['guest'],row['vmid'])
        groups[key][ds]=row
        by_ds[ds]=row
    return groups,by_ds


def choose(snapshots, pool, count=15, *, guests=None, excluded=(), rescue_system=False):
    """Pure selector. Count describes physical ZFS snapshots, not guest groups."""
    if type(count) is not int or not 1 <= count <= LIMIT:
        raise EmergencyError('Maximal 15 Snapshots pro Bereinigung')
    if guests is None:guests={}
    by_dataset=defaultdict(list)
    for s in snapshots:by_dataset[s['dataset']].append(s)
    # Reserve one *latest* snapshot for each label per dataset, regardless of age.
    reserved=set()
    for ds, rows in by_dataset.items():
        for label in LABELS:
            same=[s for s in rows if s['label']==label]
            if same:
                newest=max(same,key=lambda s:(s['creation'],s['name']))
                reserved.add(newest['name'])
    eligible=[]
    for s in snapshots:
        if not s['label'] or s['blocked'] or s['name'] in reserved or excluded_dataset(s['dataset'],pool,excluded,rescue_system=rescue_system):
            continue
        member=GUEST.fullmatch(s['dataset'].rsplit('/',1)[-1])
        if member:
            row=guests.get(s['dataset'])
            if row is None or row.get('state') != 'stopped' or row.get('protected') or not row.get('can_delete'):
                continue
        eligible.append(s)
    # Group all disks of the *same live guest* at each snapshot name;
    # skipping incomplete groups prevents a partial logical restore point.
    guest_by_id=defaultdict(set)
    for ds,row in guests.items():
        guest_by_id[(row['guest'],row['vmid'])].add(ds)
    buckets=defaultdict(list)
    for s in eligible:
        row=guests.get(s['dataset'])
        key=('guest',row['guest'],row['vmid'],s['snapshot']) if row else ('host',s['name'])
        buckets[key].append(s)
    candidates=[]
    for key,rows in buckets.items():
        if key[0]=='guest':
            disk_set=guest_by_id[(key[1],key[2])]
            if set(s['dataset'] for s in rows) != disk_set:
                continue
            # Guest snapshots on non-ZFS or detached disks are never pruned.
            if any(guests[ds].get('other_disks') for ds in disk_set):continue
        candidates.append(rows)
    candidates.sort(key=lambda rows:(min(s['creation'] for s in rows), rows[0]['name']))
    result=[]
    for group in candidates:
        if len(result)+len(group)>count:continue
        result.extend(sorted(group,key=lambda s:s['name']))
        if len(result)==count:break
    return result


def snapshot_inventory(pool):
    if pool not in [p['name'] for p in pools()]:
        raise EmergencyError('Pool nicht importiert oder unbekannt')
    raw=command(['/usr/sbin/zfs','list','-H','-p','-t','snapshot','-o',
                 'name,creation,userrefs,clones','-r',pool])
    return parse_snapshots(raw,pool)


def make_plan(pool, count=15, *, rescue=False, rescue_system=False):
    cfg=policy() if not rescue else {'excluded_datasets':[]}
    _,guests=owned_disks() if not rescue else ({},{})
    snap=snapshot_inventory(pool)
    selected=choose(snap,pool,count,guests=guests,excluded=cfg['excluded_datasets'],rescue_system=rescue_system)
    targets=[x['name'] for x in selected]
    digest=hashlib.sha256(json.dumps({'pool':pool,'count':count,'targets':targets},sort_keys=True).encode()).hexdigest()
    return {'pool':pool,'requested_count':count,'delete_count':len(targets),'targets':targets,
            'digest':digest,'note':'Kein garantierter Platzgewinn; jede Snapshot-Art bleibt pro Dataset vertreten.',
            'excluded_manual_and_replication':True,'protected_minimum_per_dataset_type':1}


@contextmanager
def deletion_lock():
    if os.geteuid()!=0:raise EmergencyError('Root erforderlich')
    fd=os.open(LOCK,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600)
    try:
        fcntl.flock(fd,fcntl.LOCK_EX)
        yield
    finally:os.close(fd)


def apply(pool,count,digest,*,runner=command,rescue=False,rescue_system=False):
    """Exact per-target deletion, revalidates frozen plan under process lock."""
    with deletion_lock():
        plan=make_plan(pool,count,rescue=rescue,rescue_system=rescue_system)
        if plan['digest']!=digest or not plan['targets']:
            raise EmergencyError('Vorschau veraendert oder keine loeschbaren Snapshots: neue Vorschau erforderlich')
        # All dry-runs BEFORE first write; errors stop without changing any snapshot.
        for item in plan['targets']:
            runner(['/usr/sbin/zfs','destroy','-n','-v',item])
        deleted=[]
        for item in plan['targets']:
            # Re-read actual ZFS properties before each mutation, including after
            # an earlier member of a multi-disk snapshot group was removed.
            inventory=snapshot_inventory(pool)
            row=next((x for x in inventory if x['name']==item),None)
            exclusions=[] if rescue else policy()['excluded_datasets']
            if not row or not row['label'] or row['blocked'] or excluded_dataset(row['dataset'],pool,exclusions,rescue_system=rescue_system):
                raise EmergencyError('Snapshot ungueltig/geschuetzt: '+item+'; bereits geloescht: '+','.join(deleted))
            siblings=[x for x in inventory if x['dataset']==row['dataset'] and x['label']==row['label']]
            newest=max(siblings,key=lambda x:(x['creation'],x['name']))
            if len(siblings)<2 or newest['name']==item:
                raise EmergencyError('Letzter Snapshot je Art bleibt geschuetzt: '+item)
            guest_name=GUEST.fullmatch(row['dataset'].rsplit('/',1)[-1])
            if guest_name and rescue:
                raise EmergencyError('Gastdatentraeger im Rescue-Modus gesperrt')
            if guest_name:
                _,current_owners=owned_disks()
                owner=current_owners.get(row['dataset'])
                if not owner or owner.get('state')!='stopped' or owner.get('protected') or not owner.get('can_delete'):
                    raise EmergencyError('Gastzustand geaendert, keine Loeschung: '+item)
            # Holds/clones/races are further guarded by native ZFS itself.
            try:runner(['/usr/sbin/zfs','destroy',item])
            except EmergencyError as exc:
                raise EmergencyError(f'Teillöschung: {len(deleted)} erledigt; Fehler bei {item}: {exc}') from exc
            deleted.append(item)
        return {'pool':pool,'deleted':deleted,'deleted_count':len(deleted)}


def log_alert(message, severity):
    priority='daemon.crit' if severity in ('critical','emergency') else 'daemon.warning'
    cp=subprocess.run(['/usr/bin/logger','-p',priority,'-t','zfsm-emergency',message],check=False)
    if cp.returncode:raise EmergencyError('Warnung konnte nicht ins Journal geschrieben werden')


def monitor(*, run_auto=True, now=None):
    """Timer tick: journal+native Proxmox alarms; repeat unresolved issues.

    A failed notification is NOT recorded as successfully delivered, so
    another attempt occurs on the next timer tick. Live cleanup is independent.
    """
    if os.geteuid()!=0:raise EmergencyError('Root erforderlich')
    cfg=policy();t=int(time.time() if now is None else now)
    state=read_alert_state();current={}
    all_pools=pools()
    targets=zfsm_notify.inspect_targets()
    # Pool-only monitoring: never use VM/LXC quota/refquota or replica
    # quotas for warnings, journal entries, or Proxmox notifications.

    def record(key,level,title,message,legacy_key=None):
        old=state.get(key,state.get(legacy_key,{}))
        if not isinstance(old,dict):old={}
        old=dict(old)
        previous=old.get('level','normal')
        period=cfg['notify_repeat_minutes']*60
        changed=level!=previous
        active=level!='normal'
        recovery=not active and previous not in (None,'normal')
        last_journal=int(old.get('last_journal',old.get('last_notification',0)))
        if (active and (changed or t-last_journal>=period)) or recovery:
            log_alert(message,level if active else 'warning')
            old['last_journal']=t
        if targets['configured'] and (active or recovery):
            # On transport failure, retry every timer run (and keep GUI warning).
            last_success=int(old.get('last_delivered',0))
            last_level=old.get('last_delivered_level')
            should_send=changed or last_level!=level or t-last_success>=period
            if should_send:
                try:
                    zfsm_notify.send('error' if level in ('critical','emergency') else 'warning' if active else 'info',
                                     title[:150],message[:1500])
                    old['last_delivered']=t
                    old['last_delivered_level']=level
                    old.pop('last_error',None)
                except zfsm_notify.NotifyError as exc:
                    old['last_error']=str(exc)
                    log_alert('Proxmox-Benachrichtigungsversand fehlgeschlagen: '+str(exc),'critical')
        elif active and not targets['configured']:
            old['last_error']='Kein Proxmox-Benachrichtigungsziel eingerichtet'
        if level=='normal' and not recovery:
            old.pop('last_error',None)
        old['level']=level
        current[key]=old

    host=socket.gethostname()
    for p in all_pools:
        name=p['name'];level=p['severity']
        if level=='normal':
            msg=f'OK ZFS-Pool {name} auf {host}: {p["percent"]}% belegt.'
        else:
            msg=f'{level.upper()} ZFS-Pool {name} auf {host}: {p["percent"]}% belegt, {p["free"]} Bytes frei. ADMINISTRATOR-EINGRIFF ERFORDERLICH'
        record('pool:'+name,level,'ZFS Manager: Pool '+name+' '+level.upper(),msg,legacy_key=name)
        if run_auto and cfg['auto_enabled'] and name in cfg['auto_pools'] and p['percent']>=80:
            try:
                plan=make_plan(name,cfg['batch_count'])
                if plan['delete_count']:
                    done=apply(name,cfg['batch_count'],plan['digest'])
                    log_alert(f'Automatische Bereinigung {name}: {done["deleted_count"]} Snapshots geloescht; Auslastung erneut pruefen','warning')
                else:
                    log_alert(f'Kein sicher loeschbarer Snapshot in {name}; Administrator muss handeln','critical')
            except (EmergencyError,OSError,subprocess.TimeoutExpired) as exc:
                log_alert(f'Automatische Bereinigung {name} NICHT abgeschlossen: {exc}','critical')

    # Legacy dataset:* and monitor:datasets entries are intentionally omitted
    # from the new state file, without sending false recovery notifications.
    # Only per-pool alerts are persisted and repeated.

    ALERT_FILE.parent.mkdir(parents=True,exist_ok=True)
    fd,path=tempfile.mkstemp(prefix='.zfsm-alerts-',dir=str(ALERT_FILE.parent))
    try:
        with os.fdopen(fd,'w') as f:
            json.dump(current,f,sort_keys=True);f.flush();os.fsync(f.fileno())
        os.chmod(path,0o600);os.replace(path,ALERT_FILE)
    finally:
        if os.path.exists(path):os.unlink(path)
    return {'alerts':[{k:v for k,v in p.items() if k in ('name','percent','severity')} for p in all_pools],
            'notification':targets}


def main(argv=None):
    import argparse
    cli=argparse.ArgumentParser(prog='zfsm emergency')
    sub=cli.add_subparsers(dest='cmd',required=True)
    sub.add_parser('status').add_argument('--json',action='store_true')
    for action in ('preview','cleanup','cleanup-api','rescue-preview','rescue-cleanup'):
        p=sub.add_parser(action)
        p.add_argument('--pool',required=True);p.add_argument('--count',type=int,default=15)
        if action=='cleanup-api':p.add_argument('--digest',required=True)
        if action in ('rescue-preview','rescue-cleanup'):p.add_argument('--include-system',action='store_true')
    c=sub.add_parser('config');c.add_argument('--enable-auto-pool');c.add_argument('--disable-auto',action='store_true');c.add_argument('--ack-risk',action='store_true')
    sub.add_parser('monitor')
    sub.add_parser('notify-check')
    sub.add_parser('notify-test')
    args=cli.parse_args(argv)
    try:
        if args.cmd=='status':
            data=status()
            if args.json:print(json.dumps(data,ensure_ascii=False))
            else:
                for p in data['pools']:
                    level=p['severity'].upper() if os.environ.get('ZFSM_CLI_LANG')=='en' else {'normal':'NORMAL','warning':'WARNUNG','critical':'KRITISCH','emergency':'NOTFALL'}.get(p['severity'],p['severity'])
                    print(f"{p['name']}: {p['percent']}% – {level}, {p['free']} Bytes frei")
                print('Proxmox-Benachrichtigungsziele:',data['notification']['targets'],
                      '| Versand muss mit notify-test geprueft werden')
                if data['notification'].get('last_error'):print('WARNUNG (Poolalarm):',data['notification']['last_error'])
                print('Automatische Bereinigung:', 'AKTIV' if data['policy']['auto_enabled'] else 'AUS (sicherer Standard)')
            return 0
        if args.cmd in ('preview','rescue-preview'):
            print(json.dumps(make_plan(args.pool,args.count,rescue=args.cmd=='rescue-preview',
                                       rescue_system=getattr(args,'include_system',False)),ensure_ascii=False,indent=2));return 0
        if args.cmd in ('cleanup','rescue-cleanup'):
            if os.geteuid()!=0 or not sys.stdin.isatty():
                raise EmergencyError('Interaktive Root-Shell erforderlich; kein stilles Loeschen')
            rescue=args.cmd=='rescue-cleanup'
            system=getattr(args,'include_system',False)
            plan=make_plan(args.pool,args.count,rescue=rescue,rescue_system=system)
            print(json.dumps(plan,ensure_ascii=False,indent=2))
            if not plan['delete_count']:
                print('Keine sicher loeschbaren Snapshots');return 0
            if input(f"GEFAHR: {plan['delete_count']} Snapshots unwiderruflich loeschen? 'JA': ").strip()!='JA':
                print('Abgebrochen');return 2
            if input(f"Zur Bestätigung 'LOESCHEN {args.pool}' eingeben: ").strip()!=f'LOESCHEN {args.pool}':
                print('Abgebrochen');return 2
            print(json.dumps(apply(args.pool,args.count,plan['digest'],rescue=rescue,rescue_system=system),ensure_ascii=False,indent=2));return 0
        if args.cmd=='cleanup-api':
            if os.geteuid()!=0:raise EmergencyError('Nur root')
            if not re.fullmatch('[a-f0-9]{64}',args.digest):raise EmergencyError('Digest ungueltig')
            print(json.dumps(apply(args.pool,args.count,args.digest),ensure_ascii=False));return 0
        if args.cmd=='config':
            cfg=policy()
            if args.enable_auto_pool and args.disable_auto:
                raise EmergencyError('Widerspruechliche Einstellungen')
            if args.enable_auto_pool:
                if not args.ack_risk:raise EmergencyError('Automatische Loeschung erfordert --ack-risk')
                if args.enable_auto_pool not in [p['name'] for p in pools()]:
                    raise EmergencyError('Pool nicht vorhanden')
                cfg['auto_enabled']=True
                cfg['auto_pools']=sorted(set(cfg['auto_pools']+[args.enable_auto_pool]))
                save_policy(cfg)
            if args.disable_auto:
                cfg['auto_enabled']=False;save_policy(cfg)
            print(json.dumps(cfg,ensure_ascii=False,indent=2));return 0
        if args.cmd=='notify-check':
            info=zfsm_notify.inspect_targets();print(json.dumps(info,ensure_ascii=False,indent=2))
            return 0 if info['configured'] else 1
        if args.cmd=='notify-test':
            if os.geteuid()!=0:raise EmergencyError('Root erforderlich')
            info=zfsm_notify.inspect_targets()
            if not info['configured']:raise EmergencyError('Keine Proxmox-Benachrichtigungsziele konfiguriert')
            zfsm_notify.send('warning','ZFS Manager Testnachricht',
                'Dies ist ein Test der Benachrichtigung auf '+socket.gethostname()+'. Keine ZFS-Aktion wurde ausgefuehrt.')
            print('Test an Proxmox-Benachrichtigungssystem uebergeben. Empfang am Ziel kontrollieren!')
            return 0
        if args.cmd=='monitor':
            print(json.dumps(monitor(),ensure_ascii=False));return 0
    except (EmergencyError,zfsm_notify.NotifyError,OSError,ValueError,subprocess.TimeoutExpired) as exc:
        print('ZFS NOTFALL FEHLER: '+str(exc),file=sys.stderr)
        return 1
    return 2


if __name__=='__main__':sys.exit(main())
