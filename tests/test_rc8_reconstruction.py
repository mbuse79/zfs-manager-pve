"""RC8 safety boundaries: pure fixtures, no production host access."""
import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from unittest.mock import patch
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
spec=importlib.util.spec_from_file_location('driver',ROOT/'install_driver.py')
driver=importlib.util.module_from_spec(spec);spec.loader.exec_module(driver)

@pytest.mark.parametrize('plan',[
 'Inst unzip (6)\nInst pve-zfs-manager (1)\nInst pve-manager (9)',
 'Inst unzip (6)\nInst pve-zfs-manager (1)\nRemv important',
 'Inst unzip (6)',
 'Inst unzip (6)\nInst pve-zfs-manager (1)\nConf foreign (1)',
 'Inst unzip (6)\nInst unzip (6)\nInst pve-zfs-manager (1)',
])
def test_apt_plan_rejects_additional_changes(plan):
    with pytest.raises(RuntimeError):driver.plan_changes(plan,['unzip','pve-zfs-manager'])

def test_exact_plan_allowed():
    driver.plan_changes('Inst unzip (6)\nInst pve-zfs-manager [1.0.0-34~rc7] (1.0.0-34~rc9)\nConf unzip (6)\nConf pve-zfs-manager (1.0.0-34~rc9)',['unzip','pve-zfs-manager'])

@pytest.mark.parametrize('name',driver.ALTERNATIVES)
def test_unsupported_backend_stops_parallel_scheduler(tmp_path,name):
    unit=tmp_path/'etc/systemd/system/custom-snapshot.service';unit.parent.mkdir(parents=True)
    unit.write_text('[Service]\nExecStart=/opt/'+name+' --secret PRIVATE\n')
    assert driver.competing(tmp_path,which=lambda _:None)==[name]

def test_manifest_before_driver_including_tampered_extra_and_missing(tmp_path):
    package=tmp_path/'package';package.mkdir()
    script=ROOT/'install-local.sh'
    (package/'install-local.sh').write_bytes(script.read_bytes())
    (package/'install_driver.py').write_text("raise SystemExit('DRIVER EXECUTED')\n")
    def manifest():
        (package/'SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in sorted(package.iterdir()) if p.name!='SHA256SUMS'))
    def run():return subprocess.run(['bash',str(package/'install-local.sh'),'--check-only'],capture_output=True,text=True)
    manifest()
    assert 'DRIVER EXECUTED' in run().stderr
    (package/'install_driver.py').write_text("raise SystemExit('TAMPERED DRIVER EXECUTED')")
    assert 'SHA256 mismatch' in run().stderr
    manifest();(package/'unexpected').write_text('extra')
    assert 'Incomplete manifest' in run().stderr
    (package/'unexpected').unlink();(package/'install_driver.py').unlink()
    assert 'Incomplete manifest' in run().stderr

def test_no_pool_is_valid_but_command_error_is_not():
    import zfsm_emergency as em
    with patch.object(em,'command',return_value=''):assert em.pools()==[]
    with patch.object(em,'command',side_effect=em.EmergencyError('query failed')):
        with pytest.raises(em.EmergencyError):em.pools()

def test_rc7_upgrade_preserves_policies_secrets_cron_and_api(tmp_path):
    from universal import Installer,JS_INSERT,VERSION,sha
    from test_repair_drift_v112 import SRC_GUI,SRC_NODES
    import previous_patch
    spec=importlib.util.spec_from_file_location('rc7gui',ROOT/'tests/fixtures/manager_patch_v134rc7.py')
    rc7=importlib.util.module_from_spec(spec);spec.loader.exec_module(rc7)
    i=Installer(root=tmp_path,source=ROOT/'src',test_version='pve-manager/9.2.26/mock',dry_system=True)
    for p,txt in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(txt)
    i.install()
    old=i.gui.read_text().replace(JS_INSERT,previous_patch.HELPERS+rc7.BLOCK)
    i.gui.write_text(old);state=i.state();state['version']='1.0.0-34-rc7-dynamic-compat-installer';state['installed_hashes']['gui']=sha(old.encode());i.save_state(state)
    i.yearly.write_text('custom yearly schedule preserved\n')
    cfg=i.admindir/'emergency.json';cfg.write_text('{"auto_enabled": true}')
    paths=[i.secret,i.admin,i.yearly,i.api,i.policy,i.nodes,cfg]
    before={p:p.read_bytes() for p in paths}
    i.install()
    assert i.state()['version']==VERSION
    assert i.gui.read_text().count(JS_INSERT)==1
    assert before=={p:p.read_bytes() for p in paths}
    assert i.state().get('last_repair_backup')

@pytest.mark.parametrize('version',['9.0.0','9.1.0','9.2.26','9.99.999'])
def test_pve9_no_minor_confirmation(tmp_path,version):
    from universal import Installer
    from test_repair_drift_v112 import SRC_GUI,SRC_NODES
    i=Installer(root=tmp_path,source=ROOT/'src',test_version='pve-manager/'+version+'/mock',dry_system=True)
    for p,txt in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(txt)
    i.precheck()


def test_gui_static_translation_keys_and_no_duplicates():
    import manager_patch
    dictionary,body=manager_patch.BLOCK.split('var zfsL = function',1)
    keys=[]
    for k in re.findall(r'''^\s*(['"].*?['"]):\s*['"].*?['"],?\s*$''',dictionary,re.M):
        keys.append(ast.literal_eval(k))
    uses=[ast.literal_eval(k) for k in re.findall(r'''zfsL\((['"](?:\\.|[^\\])*?['"])\)''',body)]
    assert len(keys)==len(set(keys))
    assert not set(uses)-set(keys)
    capacity=body.split('var renderCapacity = function',1)[1].split('var renderRetention',1)[0]
    assert "zfsL('Pool capacity')" not in capacity
    assert "zfsL('Retention overview')" not in capacity
    retention=body.split('var renderRetention = function',1)[1].split('// The row widgets',1)[0]
    assert 'Observed total' in retention and 'record.file' in retention


def test_cli_english_json_boundary_and_confirmation_tokens():
    from cli_locale import english
    assert english('Automatische Bereinigung: AUS (sicherer Standard)')=='Automatic cleanup: OFF (safe default)'
    raw='{"message":"Automatische Bereinigung:","status":"PRÜFEN"}'
    assert english(raw)==raw
    assert "'LOESCHEN tank'" in english("Zur Bestätigung 'LOESCHEN tank' eingeben: ")

@pytest.mark.parametrize('existing,missing,check_only',[
 ('1.0.0-34~rc7',[],True),('1.0.0-34~rc7',[],False),
 (None,['unzip','zfs-auto-snapshot'],True),(None,['unzip','zfs-auto-snapshot'],False),
])
def test_driver_upgrade_and_fresh_install_exact_archives(tmp_path,monkeypatch,existing,missing,check_only):
    import zfsm_host_audit
    monkeypatch.setattr(driver,'HERE',tmp_path)
    dep=tmp_path/'dependencies';dep.mkdir()
    for n in missing:(dep/(n+'_test_all.deb')).touch()
    (tmp_path/('pve-zfs-manager_'+driver.VERSION+'_all.deb')).touch()
    state={'pve-zfs-manager':existing,**{n:None if n in missing else '1' for n in ['unzip','zfs-auto-snapshot']}}
    audit={'autosnap':{'duplicate_labels':[],'schedules':[],'binary':not missing},'other_cleanup_units':[],'other_cleanup_cron':[]}
    calls=[]
    def run(argv,**kw):
        calls.append(argv)
        if argv[:2]==['dpkg','-i']:
            state['pve-zfs-manager']=driver.VERSION
            for n in missing:state[n]='1'
        return subprocess.CompletedProcess(argv,0,'','')
    def output(argv):
        calls.append(argv)
        if argv==['pveversion']:return 'pve-manager/9.99.999/mock'
        if argv==['dpkg','--print-architecture']:return 'amd64'
        if argv[0]=='dpkg-deb':
            name=Path(argv[-2]).name.split('_')[0]
            return name if argv[-1]=='Package' else driver.VERSION if argv[-1]=='Version' else 'all'
        if argv[0]=='apt-get':
            assert '--no-upgrade' not in argv, 'The explicit RC7 to RC8 upgrade must remain possible'
            return '\n'.join('Inst '+n+' (1)\nConf '+n+' (1)' for n in [*missing,'pve-zfs-manager'])
        raise AssertionError(argv)
    monkeypatch.setattr(driver,'run',run);monkeypatch.setattr(driver,'output',output)
    monkeypatch.setattr(driver,'installed',state.get);monkeypatch.setattr(driver.os,'geteuid',lambda:0)
    monkeypatch.setattr(driver,'competing',lambda:[]);monkeypatch.setattr(zfsm_host_audit,'discover',lambda:audit)
    assert driver.main(['--check-only'] if check_only else [])==0
    installs=[x for x in calls if x[:2]==['dpkg','-i']]
    assert len(installs)==(0 if check_only else 1)
    if installs:
        assert installs[0][2:]==[str(dep/(n+'_test_all.deb')) for n in missing]+[str(tmp_path/('pve-zfs-manager_'+driver.VERSION+'_all.deb'))]
    assert not any(x[0]=='apt-get' and '--simulate' not in x for x in calls)

@pytest.mark.parametrize('kind',['traversal','symlink','duplicate','hash','extra'])
def test_bootstrap_rejects_unsafe_zip_before_code(tmp_path,monkeypatch,kind):
    import io,stat,urllib.request,zipfile
    buf=io.BytesIO()
    with zipfile.ZipFile(buf,'w') as z:
        if kind=='traversal':z.writestr('../escape','bad')
        elif kind=='symlink':
            i=zipfile.ZipInfo('link');i.external_attr=(stat.S_IFLNK|0o777)<<16;z.writestr(i,'/etc/passwd')
        elif kind=='duplicate':z.writestr('same','a');z.writestr('same','b')
        else:
            z.writestr('SHA256SUMS','0'*64+'  install-local.sh\n');z.writestr('install-local.sh','echo BAD')
            if kind=='extra':z.writestr('extra','bad')
    data=buf.getvalue()
    class Response(io.BytesIO):url='https://test.invalid/package.zip'
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**kw:Response(data))
    monkeypatch.setattr(sys,'argv',['-',Response.url,hashlib.sha256(data).hexdigest()])
    monkeypatch.setattr(subprocess,'run',lambda *a,**kw:pytest.fail('Contained code executed'))
    code=(ROOT/'bootstrap-rc8.sh').read_text().split("<<'PYBOOT'\n",1)[1].rsplit('\nPYBOOT',1)[0]
    with pytest.raises(ValueError):exec(compile(code,'bootstrap-rc8.sh','exec'),{'__name__':'test'})

@pytest.mark.parametrize('current',['1.0.0-34~rc9','1.0.0-35'])
def test_same_or_newer_manager_never_reinstalled(tmp_path,monkeypatch,current):
    monkeypatch.setattr(driver.os,'geteuid',lambda:0)
    monkeypatch.setattr(driver,'HERE',tmp_path)
    def output(argv):
        if argv==['pveversion']:return 'pve-manager/9.2.26/mock'
        if argv[-1]=='Package':return 'pve-zfs-manager'
        if argv[-1]=='Version':return driver.VERSION
        raise AssertionError(argv)
    monkeypatch.setattr(driver,'output',output)
    monkeypatch.setattr(driver,'installed',lambda _:current)
    monkeypatch.setattr(driver,'run',lambda *a,**kw:pytest.fail('No package action allowed'))
    assert driver.main([])==0

@pytest.mark.parametrize('major',['8','10'])
def test_other_pve_major_stops_before_package_code(monkeypatch,major):
    monkeypatch.setattr(driver.os,'geteuid',lambda:0)
    monkeypatch.setattr(driver,'output',lambda argv:'pve-manager/'+major+'.1.0/mock' if argv==['pveversion'] else pytest.fail('Package accessed'))
    with pytest.raises(RuntimeError):driver.main(['--check-only'])


def test_verified_bootstrap_succeeds_without_unzip(monkeypatch):
    import io,urllib.request,zipfile
    buf=io.BytesIO();payload=b'echo example'
    with zipfile.ZipFile(buf,'w') as z:
        z.writestr('install-local.sh',payload)
        z.writestr('SHA256SUMS',hashlib.sha256(payload).hexdigest()+'  install-local.sh\n')
    data=buf.getvalue()
    class Response(io.BytesIO):url='https://test.invalid/package.zip'
    monkeypatch.setattr(urllib.request,'urlopen',lambda *a,**kw:Response(data))
    monkeypatch.setattr(sys,'argv',['-',Response.url,hashlib.sha256(data).hexdigest(),'--check-only'])
    calls=[]
    def run(argv):
        calls.append(argv)
        assert argv[0]=='bash' and argv[-1]=='--check-only'
        assert Path(argv[1]).read_bytes()==payload
        return subprocess.CompletedProcess(argv,0)
    monkeypatch.setattr(subprocess,'run',run)
    code=(ROOT/'bootstrap-rc8.sh').read_text().split("<<'PYBOOT'\n",1)[1].rsplit('\nPYBOOT',1)[0]
    with pytest.raises(SystemExit) as end:exec(compile(code,'bootstrap','exec'),{})
    assert end.value.code==0 and len(calls)==1


def test_custom_yearly_schedule_does_not_get_parallel_job(tmp_path):
    from universal import Installer
    from test_repair_drift_v112 import SRC_GUI,SRC_NODES
    cron=tmp_path/'etc/cron.d/custom-yearly';cron.parent.mkdir(parents=True)
    text='1 1 1 1 * root /usr/sbin/zfs-auto-snapshot --label=yearly --keep=9 //\n';cron.write_text(text)
    i=Installer(root=tmp_path,source=ROOT/'src',test_version='pve-manager/9.2.26/mock',dry_system=True)
    for p,txt in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
        p.parent.mkdir(parents=True,exist_ok=True);p.write_text(txt)
    i.install()
    assert cron.read_text()==text
    assert not i.yearly.exists()
