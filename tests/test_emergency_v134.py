"""ZFS emergency 1.0.0-34: pure selector and fail-closed behaviour."""
from contextlib import nullcontext
from pathlib import Path
from unittest.mock import patch
import json
import pytest
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import zfsm_emergency as em


def snap(ds,kind,when, *, refs=0, clones='-'):
    label=f'zfs-auto-snap_{kind}-{when:06d}'
    return {'name':ds+'@'+label,'dataset':ds,'snapshot':label,'label':kind,
            'creation':when,'userrefs':refs,'clones':clones,
            'blocked':bool(refs) or clones not in ('-','', 'none')}


def test_thresholds_exact():
    table=['a\t100\t79\t21\tONLINE','b\t100\t80\t20\tONLINE',
           'c\t100\t89\t11\tONLINE','d\t100\t90\t10\tONLINE',
           'e\t100\t95\t5\tONLINE']
    with patch.object(em,'command',return_value='\n'.join(table)):
        assert [p['severity'] for p in em.pools()] == [
            'normal','warning','warning','critical','emergency']


def test_last_snapshot_survives_even_if_five_years_old():
    ds='tank/data'
    one=snap(ds,'yearly',100)
    other=[snap(ds,'hourly',100+i) for i in range(18)]
    selected=em.choose([one,*other],'tank',15,guests={})
    assert len(selected)==15
    assert one['name'] not in {x['name'] for x in selected}
    assert max(other,key=lambda x:x['creation'])['name'] not in {x['name'] for x in selected}
    assert selected[0]['creation']==100


def test_singles_all_protected():
    rows=[snap('tank/data',kind,100) for kind in em.LABELS]
    assert em.choose(rows,'tank',15,guests={})==[]


def test_manual_replication_and_root_protected():
    a=[snap('tank/production', 'daily',i) for i in range(5)]
    b=[snap('tank/pve4-replikation/production', 'daily',i) for i in range(5)]
    c=[snap('tank/ROOT/pve-1','daily',i) for i in range(5)]
    d=[snap('tank','daily',i) for i in range(5)]
    manual={'name':'tank/production@my-backup','dataset':'tank/production',
            'snapshot':'my-backup','label':None,'creation':0,'userrefs':0,'clones':'-',
            'blocked':False}
    chosen=em.choose(a+b+c+d+[manual],'tank',15,guests={})
    assert len(chosen)==4
    assert all(x['dataset']=='tank/production' for x in chosen)


def test_holds_and_clones_blocked():
    rows=[snap('tank/data','daily',i,refs=1 if i==1 else 0,clones='pool/clone' if i==2 else '-') for i in range(1,5)]
    assert [x['creation'] for x in em.choose(rows,'tank',15,guests={})]==[3]
    # The only oldest eligible candidate is after adding an additional snapshot.
    rows.append(snap('tank/data','daily',5))
    assert [x['creation'] for x in em.choose(rows,'tank',15,guests={})]==[3,4]


def test_guest_group_only_if_complete_and_stopped():
    a='tank/data/vm-204-disk-0';b='tank/data/vm-204-disk-1'
    owned={ds:{'guest':'vm','vmid':204,'state':'stopped','can_delete':True,'protected':False,'other_disks':0} for ds in (a,b)}
    rows=[snap(ds,'hourly',n) for ds in (a,b) for n in (1,2)]
    chosen=em.choose(rows,'tank',15,guests=owned)
    assert {x['name'] for x in chosen}=={snap(a,'hourly',1)['name'],snap(b,'hourly',1)['name']}
    owned[b]['state']='running'
    assert em.choose(rows,'tank',15,guests=owned)==[]
    owned[b]['state']='stopped'
    assert em.choose(rows[:-1],'tank',15,guests=owned)==[]


def test_count_bounded_and_no_clean_when_snapshot_changed():
    with pytest.raises(em.EmergencyError):em.choose([], 'tank', 16)
    with patch.object(em,'deletion_lock',return_value=nullcontext()),patch.object(em,'make_plan',return_value={
        'digest':'deadbeef','targets':['tank/data@snapshot']}):
        with pytest.raises(em.EmergencyError):em.apply('tank',15,'something-else',runner=lambda x:pytest.fail('ZFS write must not execute'))


def test_read_only_default_and_config_security(tmp_path):
    assert not em.policy(tmp_path/'no-file')['auto_enabled']
    cfg=tmp_path/'bad.json';cfg.write_text('{"auto_enabled":true}')
    cfg.chmod(0o644)
    with pytest.raises(em.EmergencyError):em.policy(cfg)
    cfg.write_text('{"auto_enabled":false,"auto_pools":["tank"],"unexpected":1}')
    cfg.chmod(0o600)
    if cfg.stat().st_uid==0:
        with pytest.raises(em.EmergencyError):em.policy(cfg)


def test_api_permissions_hmac_and_ui_persistent_warning():
    api=(ROOT/'src/PVE/API2/ZFSSnapshotViewer.pm').read_text()
    js=(ROOT/'src/manager_patch.py').read_text()
    for route in ('emergency-status','emergency-preview','emergency-cleanup'):
        assert f"path=>'{route}'" in api
    assert "_require_zfsmgr_admin($x->{node})" in api
    assert "_verify_preview($plan,'EMERGENCY-34'" in api
    assert "confirm} eq 'EMERGENCY-DELETE'" in api
    assert "itemId:'zfsm-emergency-alert'" in js
    assert 'Administrator action required' in js
    assert 'view.zfsmEmergencyPreview=function()' in js
    assert 'critical_ack:1' in js
    assert 'timeout:240000' in js


def test_cli_includes_emergency():
    import zfsm_cli
    assert 'emergency' in zfsm_cli.HELP_COMMANDS
    assert zfsm_cli.VERSION=='1.0.0-34~rc10+fix1'


def test_apply_cannot_delete_last_snapshot_even_between_writes():
    ds='tank/data'; rows=[snap(ds,'daily',x) for x in (10,20,30)]
    deleted=[]; calls=[]
    def runner(args):
        calls.append(args[:])
        if args[2:4]!=['-n','-v']:
            deleted.append(args[-1]);rows[:]=[x for x in rows if x['name']!=args[-1]]
        return ''
    plan={'digest':'a'*64,'targets':[rows[0]['name'],rows[1]['name']]}
    with patch.object(em,'deletion_lock',return_value=nullcontext()), \
         patch.object(em,'make_plan',return_value=plan), \
         patch.object(em,'snapshot_inventory',side_effect=lambda _:rows[:]), \
         patch.object(em,'policy',return_value={'excluded_datasets':[]}), \
         patch.object(em,'owned_disks',return_value=({},{})):
        result=em.apply('tank',15,plan['digest'],runner=runner)
    assert result['deleted_count']==2
    assert len(rows)==1 and rows[0]['creation']==30
    assert len([x for x in calls if '-n' in x])==2
    assert len([x for x in calls if '-n' not in x])==2


def test_monitor_alerts_critical_without_auto_deleting(tmp_path):
    state=tmp_path/'alerts.json';reported=[]
    config={'auto_enabled':False,'auto_pools':[],'batch_count':15,'target_percent':78,
            'excluded_datasets':[],'notify_repeat_minutes':60}
    info={'name':'tank','severity':'critical','percent':92,'free':8,'allocated':92,'total':100,'health':'ONLINE'}
    with patch.object(em,'ALERT_FILE',state),patch.object(em,'policy',return_value=config), \
         patch.object(em,'pools',return_value=[info]),patch.object(em,'dataset_report',return_value={'checked':0,'total_alerts':0,'issues':[],'truncated':False}),patch.object(em,'log_alert',side_effect=lambda msg,level:reported.append((msg,level))), \
         patch('os.geteuid',return_value=0),patch.object(em,'make_plan',side_effect=AssertionError('automatic cleanup must be disabled')):
        result=em.monitor(now=10000)
    assert result['alerts'][0]['severity']=='critical'
    assert len(reported)==1 and reported[0][1]=='critical'
    assert 'ADMINISTRATOR' in reported[0][0]
    assert state.is_file()
