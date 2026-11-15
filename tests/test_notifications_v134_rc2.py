"""Offline, non-destructive tests for ZFS Manager 1.0.0-34 RC2."""
from pathlib import Path
from unittest.mock import patch, Mock
import json
import sys
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import zfsm_emergency as em
import zfsm_notify as notify


def empty_report():
    return {'checked':3,'total_alerts':0,'issues':[],'truncated':False}


def info(name='tank',level='critical'):
    return {'name':name,'severity':level,'percent':90 if level=='critical' else 80,
            'free':10,'allocated':90,'total':100,'health':'ONLINE'}


def config():
    return {'auto_enabled':False,'auto_pools':[],'batch_count':15,'target_percent':78,
            'excluded_datasets':[],'notify_repeat_minutes':60}


def test_dataset_quota_refquota_and_low_available():
    # Pure string fixture; no ZFS calls or writes occur.
    sample='\n'.join([
        'tank\tfilesystem\t0\t0\t10000000000\tnone\tnone',
        'tank/normal\tfilesystem\t20\t20\t10000000000\t100\tnone',
        'tank/quota\tfilesystem\t900\t800\t100\t1000\tnone',
        'tank/ref\tvolume\t550\t950\t90\tnone\t1000',
        'tank/headroom\tfilesystem\t2147483648\t2100000000\t40000000\tnone\tnone',
    ])
    with patch.object(em,'command',return_value=sample):
        result=em.dataset_report()
    assert result['checked']==5
    assert result['total_alerts']==3
    by={r['dataset']:r for r in result['issues']}
    assert by['tank/quota']['severity']=='critical'
    assert by['tank/ref']['severity']=='emergency'
    assert by['tank/headroom']['metric']=='available'
    assert by['tank/headroom']['severity']=='emergency'
    assert 'tank/normal' not in by


def test_dataset_limits_80_and_last_quota_not_snapshot_deleted():
    sample='tank/lxc\tfilesystem\t80\t70\t20\t100\t100'
    with patch.object(em,'command',return_value=sample):
        r=em.dataset_report()
    assert r['total_alerts']==1 and r['issues'][0]['severity']=='warning'
    assert r['issues'][0]['metric']=='quota'


@pytest.mark.parametrize('line',[
    'tank/lxc\tfilesystem\ta\t70\t20\t100\tnone',
    'tank/lxc\tfilesystem\t3\t3\t-\tnone\tnone',
    'tank/lxc\tfilesystem\t3\t3\t7\t1b\tnone',
])
def test_bad_dataset_inventory_fails_closed(line):
    with patch.object(em,'command',return_value=line):
        with pytest.raises(em.EmergencyError):em.dataset_report()


def test_target_config_inspection_only_public(tmp_path):
    f=tmp_path/'notifications.cfg'
    f.write_text('''sendmail: mail-to-root
\tmailto-user root@pam
smtp: outside
webhook: phone
matcher: default-matcher
''')
    assert notify.inspect_targets(f)['targets']==3
    assert not notify.inspect_targets(tmp_path/'does-not-exist')['configured']


def test_notification_native_api_no_shell_and_payload_is_stdin():
    seen={}
    def runner(args,**kwargs):
        seen.update(args=args,kwargs=kwargs)
        return Mock(returncode=0)
    assert notify.send('error','Alarm rpool','Keine Snapshots loeschen',runner=runner)
    assert seen['args'][:3]==['/usr/bin/perl','-MJSON::PP','-MPVE::Notify']
    assert 'Keine Snapshots loeschen' not in ' '.join(seen['args'])
    assert json.loads(seen['kwargs']['input'])['message']=='Keine Snapshots loeschen'
    assert seen['kwargs']['timeout']<=30


def test_notification_does_not_log_sensitive_errors():
    def runner(args,**kwargs):return Mock(returncode=7,stderr='secret=https://private.example')
    with pytest.raises(notify.NotifyError) as err:
        notify.send('warning','Test','Benachrichtigung',runner=runner)
    assert 'private.example' not in str(err.value)


def test_monitor_critical_is_repeated_but_not_each_five_minutes(tmp_path):
    state=tmp_path/'alerts.json';logged=[];notified=[]
    with patch.object(em,'ALERT_FILE',state),patch.object(em,'policy',return_value=config()), \
         patch.object(em,'pools',return_value=[info()]),patch.object(em,'dataset_report',return_value=empty_report()), \
         patch.object(em.zfsm_notify,'inspect_targets',return_value={'configured':True,'targets':1}), \
         patch.object(em.zfsm_notify,'send',side_effect=lambda *a: notified.append(a)), \
         patch.object(em,'log_alert',side_effect=lambda *a: logged.append(a)),patch('os.geteuid',return_value=0), \
         patch.object(em,'make_plan',side_effect=AssertionError('cleanup must stay disabled')):
        em.monitor(now=10000)
        em.monitor(now=10300)
        em.monitor(now=13700)
    assert len(notified)==2
    assert len(logged)==2
    assert notified[0][0]=='error'
    assert state.exists()
    assert json.loads(state.read_text())['pool:tank']['last_delivered']==13700


def test_monitor_notify_failure_retries_next_tick(tmp_path):
    state=tmp_path/'alerts.json';attempts=[]
    def sender(*args):
        attempts.append(1)
        if len(attempts)==1:raise notify.NotifyError('Testversand fehlgeschlagen')
    with patch.object(em,'ALERT_FILE',state),patch.object(em,'policy',return_value=config()), \
         patch.object(em,'pools',return_value=[info()]),patch.object(em,'dataset_report',return_value=empty_report()), \
         patch.object(em.zfsm_notify,'inspect_targets',return_value={'configured':True,'targets':1}), \
         patch.object(em.zfsm_notify,'send',side_effect=sender),patch.object(em,'log_alert'), \
         patch('os.geteuid',return_value=0):
        em.monitor(now=10000)
        first=json.loads(state.read_text())['pool:tank']
        assert 'last_delivered' not in first and first['last_error']
        em.monitor(now=10300)
        last=json.loads(state.read_text())['pool:tank']
    assert len(attempts)==2
    assert 'last_error' not in last
    assert last['last_delivered']==10300


def test_dataset_quotas_not_alarm_pool_or_send_notifications(tmp_path):
    ds={'checked':3,'total_alerts':3,'issues':[
        {'dataset':'tank/a','pool':'tank','severity':'critical','metric':'quota','percent':91,'available':20},
        {'dataset':'tank/b','pool':'tank','severity':'warning','metric':'refquota','percent':82,'available':50},
        {'dataset':'tank/c','pool':'tank','severity':'warning','metric':'quota','percent':83,'available':40}],
        'truncated':False}
    sent=[]
    with patch.object(em,'ALERT_FILE',tmp_path/'alert.json'),patch.object(em,'policy',return_value=config()), \
         patch.object(em,'pools',return_value=[info(level='normal')]),patch.object(em,'dataset_report',return_value=ds), \
         patch.object(em.zfsm_notify,'inspect_targets',return_value={'configured':True,'targets':1}), \
         patch.object(em.zfsm_notify,'send',side_effect=lambda *a: sent.append(a)),patch.object(em,'log_alert'), \
         patch('os.geteuid',return_value=0):
        em.monitor(now=10000)
    assert sent==[]
    state=json.loads((tmp_path/'alert.json').read_text())
    assert set(state)=={'pool:tank'}
    assert state['pool:tank']['level']=='normal'


def test_monitor_no_target_journal_warning_without_cleanup(tmp_path):
    logs=[]
    with patch.object(em,'ALERT_FILE',tmp_path/'alert.json'),patch.object(em,'policy',return_value=config()), \
         patch.object(em,'pools',return_value=[info()]),patch.object(em,'dataset_report',return_value=empty_report()), \
         patch.object(em.zfsm_notify,'inspect_targets',return_value={'configured':False,'targets':0}), \
         patch.object(em.zfsm_notify,'send',side_effect=AssertionError('no targets')), \
         patch.object(em,'log_alert',side_effect=lambda *a: logs.append(a)),patch('os.geteuid',return_value=0):
        em.monitor(now=10000)
    assert len(logs)==1
    assert json.loads((tmp_path/'alert.json').read_text())['pool:tank']['last_error']


def test_web_gui_shows_dataset_and_notification_warnings():
    js=(ROOT/'src/manager_patch.py').read_text()
    banner=js.split('view.zfsmRenderEmergency=function()',1)[1].split('view.zfsmAutoCleanupToggle=function()',1)[0]
    assert 'Dataset limits critical' not in banner
    assert 'Dataset limits warning' not in banner
    assert 'dataset_error' not in banner
    assert 'activePoolAlarm && !notification.configured' in banner
    assert 'Proxmox notification not configured' in js
    assert 'Notification delivery failed' in js
    assert 'zfsL(\'Administrator action required\')' in js


def test_dataset_50_row_display_limit_does_not_hide_other_pool_alerts():
    rows=[f'tank/a{i:03}\tfilesystem\t99\t99\t1\t100\tnone' for i in range(75)]
    rows.append('tank2/z\tfilesystem\t90\t90\t10\t100\tnone')
    with patch.object(em,'command',return_value='\n'.join(rows)):
        report=em.dataset_report()
    assert report['truncated'] is True
    assert len(report['issues'])==50
    assert report['per_pool']['tank']['count']==75
    assert report['per_pool']['tank2']['count']==1


def test_dataset_scan_is_not_used_by_pool_monitor(tmp_path):
    msgs=[]
    with patch.object(em,'ALERT_FILE',tmp_path/'alert.json'),patch.object(em,'policy',return_value=config()), \
         patch.object(em,'pools',return_value=[info(level='normal')]), \
         patch.object(em,'dataset_report',side_effect=em.EmergencyError('zfs list fehlgeschlagen')), \
         patch.object(em.zfsm_notify,'inspect_targets',return_value={'configured':True,'targets':1}), \
         patch.object(em.zfsm_notify,'send',side_effect=lambda *a:msgs.append(a)), \
         patch.object(em,'log_alert'),patch('os.geteuid',return_value=0):
        em.monitor(now=10000)
    assert msgs==[]  # No irrelevant guest-volume alerts or scan failures
    assert set(json.loads((tmp_path/'alert.json').read_text()))=={'pool:tank'}


def test_native_notify_perl_call_with_local_stub(tmp_path):
    """Execute Perl syntax with an isolated mock PVE::Notify, never real delivery."""
    import os, shutil, subprocess
    if not shutil.which('perl'):
        pytest.skip('Perl unavailable in CI environment')
    module=tmp_path/'PVE';module.mkdir()
    (module/'Notify.pm').write_text('''package PVE::Notify;
use strict; use warnings;
sub common_template_data {return {hostname => 'test-host'}}
sub notify {my ($level,$template,$data,$fields)=@_;
    die 'wrong level' unless $level eq 'warning';
    die 'wrong template' unless $template eq 'simple';
    die 'wrong message' unless $data->{message} eq 'Mock hello';
    print 'MOCK-OK';return 1;
}
1;
''')
    env=os.environ.copy();env['PERL5LIB']=str(tmp_path)
    cp=subprocess.run(['/usr/bin/perl','-MJSON::PP','-MPVE::Notify','-e',notify.PERL],
        input=json.dumps({'level':'warning','title':'Test','message':'Mock hello'}),
        env=env,text=True,capture_output=True,timeout=8)
    assert cp.returncode==0,cp.stderr
    assert cp.stdout=='MOCK-OK'
