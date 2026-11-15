"""Compact RC9 UI and an actual RC8 fixture upgrade, without host writes."""
from pathlib import Path
import hashlib
import importlib.util
import json
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from universal import Installer,JS_INSERT,VERSION,sha
import manager_patch
from test_repair_drift_v112 import SRC_GUI,SRC_NODES


def config_script(extra):
    return """const assert=require('assert');const document={cookie:'PVELangCookie=en',querySelectorAll:()=>[]};
const Ext={String:{htmlEncode:String},create:(_n,c)=>c};const caps={nodes:{'Sys.Audit':true,'Sys.Modify':true}};
const me={items:[]},nodename='fixture';const safeZFSValue=String,zfsBytes=String;
"""+manager_patch.BLOCK+"\nconst config=me.items[0];\n"+extra


def test_layout_sections_and_exactly_two_tabs():
    code=config_script("""
assert.deepEqual(config.items.filter(x=>x.xtype==='fieldset').map(x=>x.itemId),
 ['zfsm-pool-section','zfsm-technical-details','zfsm-snapshot-audit','zfsm-retention-section','zfsm-service-details']);
for(const id of ['zfsm-technical-details','zfsm-snapshot-audit','zfsm-service-details']){
 assert.equal(config.items.find(x=>x.itemId===id).collapsed,true);
}
const tabs=config.items.find(x=>x.itemId==='zfs-snapshot-tabs');assert.equal(tabs.items.length,2);
assert.equal(tabs.items[0].title,'VMs / LXC');assert.equal(tabs.items[1].title,'ZFS-Datasets');
const pools=config.items.find(x=>x.itemId==='zfsm-pool-section');
assert(!JSON.stringify(pools).includes('zfsm-emergency-button'),'No immediate cleanup control in primary pool section');
""")
    subprocess.run(['node'],input=code,check=True,capture_output=True,text=True)


def test_cap_thresholds_and_separate_fragmentation():
    code=config_script("""
const grid=config.items.find(x=>x.itemId==='zfsm-pool-section').items.find(x=>x.itemId==='zfs-ro-pools');
const cap=grid.columns.find(x=>x.text==='CAP'),frag=grid.columns.find(x=>x.dataIndex==='frag');
assert.equal(cap.dataIndex,'alloc');assert.equal(frag.dataIndex,'frag');
for(const [value,color] of [[69,'#3db982'],[70,'#d4ad30'],[79,'#d4ad30'],[80,'#e24b4b']]){
 const html=cap.renderer(value,null,{get:()=>100});assert(html.includes(color));assert(html.includes('role="meter"'));
}
assert.equal(cap.renderer(0,null,{get:()=>0}),'—');
""")
    subprocess.run(['node'],input=code,check=True,capture_output=True,text=True)


def test_protected_runtime_files_identical_to_rc8():
    expected=json.loads((ROOT/'tests/fixtures/rc8-protected-sha256.json').read_text())
    for name,digest in expected.items():
        raw=(ROOT/'src'/name).read_bytes()
        if name=='PVE/API2/ZFSSnapshotViewer.pm':
            start=raw.index(b'# BEGIN ZFSM OPTIONAL CLUSTER DEPLOYMENT\n')
            marker=b'# END ZFSM OPTIONAL CLUSTER DEPLOYMENT\n'
            end=raw.index(marker,start)+len(marker)
            raw=raw[:start]+raw[end:]
        assert hashlib.sha256(raw).hexdigest()==digest,name


def test_rc8_upgrade_keeps_configuration_and_proxmox_surroundings(tmp_path):
    import previous_patch
    spec=importlib.util.spec_from_file_location('old_rc8_gui',ROOT/'tests/fixtures/manager_patch_v134rc8.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    i=Installer(root=tmp_path,source=ROOT/'src',test_version='pve-manager/9.2.26/mock',dry_system=True)
    for path,txt in ((i.gui,SRC_GUI),(i.nodes,SRC_NODES)):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(txt)
    i.install()
    old=previous_patch.HELPERS+module.BLOCK
    old_gui=i.gui.read_text().replace(JS_INSERT,old)
    i.gui.write_text(old_gui)
    state=i.state();state['version']='1.0.0-34-rc8-dynamic-compat-installer';state['installed_hashes']['gui']=sha(old_gui.encode());i.save_state(state)
    custom=i.admindir/'emergency.json';custom.write_text('{"auto_enabled":true,"auto_pools":["tank"]}')
    i.yearly.write_text('# individually disabled yearly schedule\n')
    paths=[custom,i.yearly,i.secret,i.admin,i.api,i.policy,i.nodes]
    before={p:p.read_bytes() for p in paths}
    i.install()
    assert i.state()['version']==VERSION
    assert before=={p:p.read_bytes() for p in paths}
    new_gui=i.gui.read_text()
    assert new_gui.count(JS_INSERT)==1
    assert new_gui.replace(JS_INSERT,old)==old_gui
    assert i.state().get('last_repair_backup')
