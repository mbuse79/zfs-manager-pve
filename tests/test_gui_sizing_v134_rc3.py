"""Desktop UI regression checks; no ZFS writes, no Proxmox runtime."""
from pathlib import Path
import subprocess
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
import manager_patch


def _fn(name):
    raw=manager_patch.BLOCK
    start=raw.index('view.'+name+' = function () {')
    end=raw.index('\n                        };',start)+len('\n                        };')
    return raw[start:end]


def test_disk_table_grows_with_drive_count_and_limits_scrolling():
    source=manager_patch.BLOCK
    assert "itemId: 'zfs-ro-disks', height: 126" in source
    assert 'Math.min(540,Math.max(126,48+data.length*24))' in source
    assert 'diskGrid.setHeight(diskHeight)' in source
    assert 'gridLoad(\'zfs-ro-\' + key, data)' in source
    assert 48+6*24==192
    assert min(540,max(126,48+40*24))==540


def test_topology_defaults_closed_and_resizes_opened_pool_without_losing_state():
    node=shutil.which('node')
    assert node, 'Node ist für GUI-Prüfung erforderlich'
    scripts=_fn('zfsmResizePoolTree')+'\n'+_fn('zfsRenderPoolTopology')
    harness=r'''
const assert=require('assert');
function makeNode(obj){
  const result={...obj,children:(obj.children||[]).map(makeNode)};
  result.get=(key)=>result[key];
  result.isExpanded=()=>!!result.expanded;
  result.eachChild=(fn)=>result.children.forEach(fn);
  return result;
}
const tree={height:110,destroyed:false,root:makeNode({expanded:true,children:[]}),
  getRootNode(){return this.root;},
  getHeight(){return this.height;},
  setHeight(h){this.height=h;},
  getStore(){return {setRoot:(obj)=>this.root=makeNode(obj)}}};
const status={update(s){this.content=s}};
const view={down(id){return id==='#zfs-ro-pool-topology'?tree:status}};
const state={expandedPoolMembers:{},poolTopology:[
  {name:'rpool',kind:'pool',status:'ONLINE',system_pool:true,children:[
    {name:'mirror-0',kind:'vdev',children:[
      {name:'nvme0',kind:'disk',children:[]},
      {name:'nvme1',kind:'disk',children:[]}
    ]}]},
  {name:'tank',kind:'pool',children:[{name:'mirror-0',kind:'vdev',children:[]}]}
]};
const Ext={isArray:Array.isArray};
const zfsL=(x)=>x;
'''
    js=harness+'\n'+scripts+r'''
view.zfsRenderPoolTopology();
assert.equal(tree.root.children.length,2);
assert.equal(tree.root.children[0].expanded,false,'Pools müssen zu Beginn geschlossen sein');
assert.equal(tree.root.children[1].expanded,false);
assert.equal(tree.root.children[0].children[0].expanded,true,'VDEV beim Öffnen sichtbar');
assert.equal(tree.height,110,'Geschlossene Liste soll kompakt sein');
tree.root.children[0].expanded=true;
view.zfsmResizePoolTree();
assert.equal(tree.height,166,'Ausgeklappter Mirror muss alle fünf Zeilen zeigen');
view.zfsRenderPoolTopology();
assert.equal(tree.root.children[0].expanded,true,'Manuell geöffnet bei Reload erhalten');
assert.equal(tree.height,166);
tree.root.children[0].expanded=false;
view.zfsRenderPoolTopology();
assert.equal(tree.root.children[0].expanded,false,'Manuell geschlossen bei Reload erhalten');
assert.equal(tree.height,110);
'''
    p=subprocess.run([node,'-e',js],capture_output=True,text=True,timeout=15)
    assert p.returncode==0,p.stderr
