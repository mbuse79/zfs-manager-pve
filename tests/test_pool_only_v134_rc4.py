"""RC4: real ZFS pool alarms only; quota/refquota cannot trigger warnings."""
from pathlib import Path
from unittest.mock import patch
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import zfsm_emergency as em


def cfg():
    return {'auto_enabled':False,'auto_pools':[],'batch_count':15,
            'target_percent':78,'excluded_datasets':[],'notify_repeat_minutes':60}


def pool(level='normal'):
    return {'name':'rpool','percent':66.0 if level=='normal' else 93.0,
            'severity':level,'free':320_000_000_000,'allocated':624_000_000_000,
            'total':944_000_000_000,'health':'ONLINE'}


def test_lxc_refquota_must_never_trigger_monitor_or_notifications(tmp_path):
    calls=[]
    with patch.object(em,'ALERT_FILE',tmp_path/'alert.json'), \
         patch.object(em,'policy',return_value=cfg()), \
         patch.object(em,'pools',return_value=[pool()]), \
         patch.object(em,'dataset_report',side_effect=AssertionError('Guest quota scan forbidden')), \
         patch.object(em.zfsm_notify,'inspect_targets',return_value={'configured':False,'targets':0}), \
         patch.object(em.zfsm_notify,'send',side_effect=AssertionError('No notifications')), \
         patch.object(em,'log_alert',side_effect=lambda *a:calls.append(a)), \
         patch('os.geteuid',return_value=0):
        result=em.monitor(now=20000)
    assert calls==[]
    assert result['alerts'][0]['severity']=='normal'
    assert set(json.loads((tmp_path/'alert.json').read_text()))=={'pool:rpool'}


def test_previous_quota_alarm_is_discarded_without_recovery_spam(tmp_path):
    old={'dataset:rpool':{'level':'critical','last_error':'unconfigured'},
         'monitor:datasets':{'level':'critical','last_error':'zfs list failed'},
         'pool:rpool':{'level':'normal'}}
    path=tmp_path/'alert.json';path.write_text(json.dumps(old));path.chmod(0o600)
    logs=[];notify=[]
    with patch.object(em,'ALERT_FILE',path),patch.object(em,'policy',return_value=cfg()), \
         patch.object(em,'pools',return_value=[pool()]), \
         patch.object(em.zfsm_notify,'inspect_targets',return_value={'configured':True,'targets':1}), \
         patch.object(em.zfsm_notify,'send',side_effect=lambda *x:notify.append(x)), \
         patch.object(em,'log_alert',side_effect=lambda *x:logs.append(x)), \
         patch('os.geteuid',return_value=0):
        em.monitor(now=20000)
        info=em.status()
    assert logs==[] and notify==[]
    assert set(json.loads(path.read_text()))=={'pool:rpool'}
    assert info['notification']['last_error'] is None
    assert 'datasets' not in info and 'dataset_error' not in info


def test_real_pool_alarm_unchanged_with_no_target(tmp_path):
    path=tmp_path/'alert.json';logs=[]
    with patch.object(em,'ALERT_FILE',path),patch.object(em,'policy',return_value=cfg()), \
         patch.object(em,'pools',return_value=[pool('critical')]), \
         patch.object(em.zfsm_notify,'inspect_targets',return_value={'configured':False,'targets':0}), \
         patch.object(em,'log_alert',side_effect=lambda *x:logs.append(x)), \
         patch('os.geteuid',return_value=0):
        em.monitor(now=20000)
        state=em.status()
    assert len(logs)==1
    assert logs[0][1]=='critical'
    assert 'ADMINISTRATOR' in logs[0][0]
    assert state['notification']['last_error']=='Kein Proxmox-Benachrichtigungsziel eingerichtet'
    assert state['pools'][0]['severity']=='critical'


def test_gui_uses_only_pool_severity_and_notification_if_pool_alert():
    gui=(ROOT/'src/manager_patch.py').read_text()
    banner=gui.split('view.zfsmRenderEmergency=function()',1)[1].split('view.zfsmAutoCleanupToggle=function()',1)[0]
    assert 'datasetInfo' not in banner and 'dsWarning' not in banner and 'dsCritical' not in banner
    assert 'activePoolAlarm && !notification.configured' in banner
    assert 'activePoolAlarm && notification.last_error' in banner
    assert "p.severity==='critical'" in banner
