// Real Proxmox-shipped ExtJS 7; Proxmox API responses are isolated fixtures.
const fs=require('fs'),path=require('path'),assert=require('assert'),{chromium}=require('playwright');
(async()=>{
 const extRoot=path.resolve(process.argv[2]),script=fs.readFileSync(process.argv[3],'utf8'),out=process.argv[4];
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const results=[],toolkit=process.argv[5]&&path.resolve(process.argv[5]),clusterMode=process.argv[6]==='cluster',guestMode=process.argv[6]==='guest',updateMode=process.argv[6]==='updates',lightMode=process.argv[7]==='light';
 for(const lang of ['de','en']){
  const page=await browser.newPage({viewport:{width:1640,height:1080}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('http://rc9.test/**',async route=>{
   const pathname=new URL(route.request().url()).pathname;
   if(pathname.startsWith('/toolkit/')&&toolkit){
    const f=path.join(toolkit,pathname.slice(9));return fs.existsSync(f)?route.fulfill({path:f,contentType:f.endsWith('.css')?'text/css':undefined}):route.fulfill({status:404,body:''});
   }
   if(pathname.startsWith('/extjs/')){
    const f=path.join(extRoot,pathname.slice(7));
    if(!f.startsWith(extRoot)||!fs.existsSync(f))return route.fulfill({status:404,body:''});
    return route.fulfill({path:f,contentType:f.endsWith('.js')?'application/javascript':f.endsWith('.css')?'text/css':undefined});
   }
   let html='<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/extjs/theme-crisp/resources/theme-crisp-all.css"><link rel="stylesheet" href="/toolkit/css/ext6-pmx.css"><link rel="stylesheet" href="/toolkit/themes/theme-proxmox-dark.css"><script src="/extjs/ext-all.js"></script><style>body{margin:0;background:#202020;font-family:Arial}header{height:38px;background:#242424;color:white;padding:10px 18px;box-sizing:border-box}#app{margin:8px 12px}.x-fieldset-header-text{font-weight:bold}</style></head><body><header>RC9 · ExtJS-7-Browsertest · API-Fixtures · keine Hostverbindung</header><div id="app"></div></body></html>';
   if(lightMode)html=html.replace('<link rel="stylesheet" href="/toolkit/themes/theme-proxmox-dark.css">','').replace('background:#202020','background:#f3f3f3');
   return route.fulfill({contentType:'text/html',body:html});
  });
  await page.goto('http://rc9.test/');
  await page.waitForFunction(()=>window.Ext&&Ext.isReady);
  await page.evaluate(({script,lang,clusterMode,guestMode,updateMode})=>{
   document.cookie='PVELangCookie='+lang;window.calls=[];
   const now=Math.floor(Date.now()/1000),guests=[],datasets=[],snapshots=[];
   [['vm',103,'RaspberryMatic',1],['vm',108,'Windows-11',3],['lxc',701,'zmb-member',2],['lxc',704,'zmb-admin',1]].forEach(([kind,id,name,count])=>{
    for(let i=0;i<count;i++){
     const ds='rpool/data/'+(kind==='vm'?'vm-':'subvol-')+id+'-disk-'+i;
     guests.push({guest:kind,vmid:id,display_name:name,drive:'disk'+i,dataset:ds,disk_count:count,can_create:1,can_delete:1,can_rollback:1,autosnap_excluded:(id===108 || (id===701 && i===0))?1:0});
     datasets.push({name:ds,type:kind==='vm'?'volume':'filesystem'});
     ['hourly','daily'].forEach((label,j)=>snapshots.push({dataset:ds,snapshot:'zfs-auto-snap_'+label+'-sample',used:1024*(i+1),creation:now-j*86400}));
    }
   });
   const pools=[{name:'rpool',health:'ONLINE',size:944*1024**3,alloc:628*1024**3,free:316*1024**3,frag:66},{name:'rpool_2',health:'ONLINE',size:1900*1024**3,alloc:755*1024**3,free:1145*1024**3,frag:12}];
   const ret=['frequent','hourly','daily','weekly','monthly','yearly'].map((label,i)=>({label,keep:[9,24,7,3,3,2][i],file:'/etc/'+(i===0?'cron.d/zfs-auto-snapshot':i===5?'cron.d/pve-zfs-manager-yearly':'cron.'+label+'/zfs-auto-snapshot')}));
   const hostDatasets=[{name:'rpool',type:'filesystem'},...['included','excluded','partial'].map(state=>({name:'rpool/host-'+state,type:'filesystem'}))];
   for(const name of ['manual-a','manual-b'])snapshots.push({dataset:'rpool/host-excluded',snapshot:name,used:1024,creation:now});
   const updateJobs={};let currentUpdate='1.1',checkedAt=now,updateAvailable=true;
   const fixtures={'disks/list':[{devpath:'/dev/nvme0n1',model:'Test NVMe',size:1024**4,health:'PASSED',wearout:99}],
    'disks/zfs':pools,'pool-scan':pools.map(p=>({name:p.name,state:'ONLINE',scan:'Not available',errors:'No known data errors'})),
    'pool-topology':pools.map(p=>({name:p.name,kind:'pool',status:'ONLINE',children:[]})),
    'emergency-status':{pools:pools.map(p=>({name:p.name,percent:100*p.alloc/p.size,severity:'normal'})),policy:{auto_enabled:false},notification:{configured:false,targets:0}},
    'datasets':datasets.concat(hostDatasets),
    'dataset-autosnap-status':datasets.concat(hostDatasets).map(d=>({dataset:d.name,autosnap_excluded:d.name.endsWith('excluded')?1:0,autosnap_partial:d.name.endsWith('partial')?1:0})),
    'update-status':{installed_version:'1.1',latest_version:'2.0',available:true,checked_at:now,error:null},'snapshots':snapshots,'retention':ret,'guest-access':guests,'admin-status':{admin:1},
    'host-inventory':{autosnap:{ready:true,schedule_count:6},replication:{systemd_units:[],native_pve_jobs:0},monitoring:{checkzfs_package:'absent'},warnings:[]}};
   window.Proxmox={defaultLang:lang,NodeName:'fixture-coordinator',UserName:(clusterMode||updateMode)?'root@pam':'observer@pve',Utils:{API2Request(opts){
    calls.push({url:opts.url,method:opts.method,params:opts.params});
    if(opts.url.endsWith('/update-status')){
     setTimeout(()=>opts.success({result:{data:{installed_version:currentUpdate,latest_version:'2.0',available:updateAvailable,checked_at:checkedAt,error:null}}}),0);return;
    }
    if(updateMode&&/\/update-(check|prepare|install|job)$/.test(opts.url)){
     const route=opts.url.split('/').pop();let data;
     if(route==='update-job')data=updateJobs[opts.params.job];
     else{
      if(opts.method!=='POST')throw Error('Update mutation must be POST');
      const op=route.slice(7),id=(op==='check'?'c':op==='prepare'?'a':'b').repeat(32);
      if(op==='install'){
       if(opts.params.plan!=='a'.repeat(32)||opts.params.confirm!==1)throw Error('Unconfirmed update');
       currentUpdate='2.0';updateAvailable=false;
      }
      updateJobs[id]={job:id,kind:op,status:op==='prepare'?'prepared':op==='install'?'installed':'complete',ready:op==='prepare',
       installed_version:op==='prepare'?'1.1':currentUpdate,version:'2.0',log:'Fixture package precheck; no real host'};
      data={job:id,upid:'fixture-update-'+op};
     }
     if(!data)throw Error('Unknown update job');
     setTimeout(()=>opts.success({result:{data}}),0);return;
    }
    if(clusterMode&&opts.url.includes('/cluster-')){
     if(!opts.url.startsWith('/nodes/fixture-coordinator/'))throw Error('Cluster request used selected remote node instead of coordinator');
     const route=opts.url.split('/').pop();let data;
     if(route==='cluster-status')data={release:{version:'1.1'},nodes:[{name:'node-a',online:true},{name:'node-b',online:false}]};
     else if(route==='cluster-preview'){
      if(opts.method!=='POST'||opts.params.nodes!=='node-a')throw Error('Unexpected cluster preview selection');
      data={job:'a'.repeat(32),upid:'fixture-preview'};
     }else if(route==='cluster-install'){
      if(opts.method!=='POST'||opts.params.confirm!==1||opts.params.plan!=='a'.repeat(32))throw Error('Unconfirmed cluster install');
      data={job:'b'.repeat(32),upid:'fixture-install'};
     }else if(route==='cluster-job'){
      const install=opts.params.job==='b'.repeat(32);
      data={kind:install?'install':'preview',status:'complete',ready:true,release:{version:'1.1'},
       results:[{node:'node-a',status:install?'installed':'ready',log:'<img src=x onerror=alert(1)> fixture escaped'}]};
     }else throw Error('Unexpected cluster route');
     setTimeout(()=>opts.success({result:{data}}),0);return;
    }
    if(guestMode && /\/guest-(autosnap|delete-all)(-preview)?$/.test(opts.url)){
     const preview=opts.url.endsWith('-preview'),deleting=opts.url.includes('delete-all');
     const disks=guests.filter(g=>g.guest===opts.params.guest && String(g.vmid)===String(opts.params.vmid));
     if(!disks.length)throw Error('Missing explicit guest identity');
     let data;
     if(preview){
      if(opts.method!=='GET')throw Error('Preview mutated');
      data={token:'fixture-token',targets:disks.map(g=>({dataset:g.dataset,snapshot:'fixture-snap',previous:'fixture property state'}))};
     }else{
      if(opts.method!=='POST'||opts.params.token!=='fixture-token'||opts.params.critical_ack!==1)throw Error('Unconfirmed guest action');
      if(opts.params.confirm!==(deleting?'GUEST-DELETE-ALL':'GUEST-AUTOSNAP')+':'+opts.params.guest+':'+opts.params.vmid)throw Error('Wrong confirmation');
      if(!deleting)disks.forEach(g=>g.autosnap_excluded=opts.params.excluded);
      data={finished:disks.map(g=>g.dataset),non_atomic:1};
     }
     setTimeout(()=>opts.success({result:{data}}),0);return;
    }
    if(opts.method!=='GET')throw Error('Mutation attempted');
    const key=opts.url.includes('/disks/')?opts.url.split('/').slice(-2).join('/'):opts.url.split('/').pop();
    setTimeout(()=>{try{opts.success({result:{data:fixtures[key]}});if(opts.callback)opts.callback();}catch(e){window.fixtureError=e.stack;throw e;}},0);
   }}};
   const me={items:[]},caps={nodes:{'Sys.Audit':true,'Sys.Modify':true}};
   new Function('me','caps','nodename',script)(me,caps,'pve4');
   window.plugin=Ext.create('Ext.panel.Panel',Object.assign(me.items[0],{renderTo:'app',width:1600}));
  },{script,lang,clusterMode,guestMode,updateMode});
  await page.waitForFunction(()=>window.plugin&&plugin.zfsReadOnly&&!plugin.zfsReadOnly.refreshing);
  const proof=await page.evaluate(async()=>{
   const p=plugin,technical=p.down('#zfsm-technical-details'),audit=p.down('#zfsm-snapshot-audit'),services=p.down('#zfsm-service-details');
   const details=p.getDockedItems('toolbar')[0].items.last();
   details.handler(details);if(technical.collapsed)throw Error('Details button failed');details.handler(details);
   if(!technical.collapsed||!audit.collapsed||!services.collapsed)throw Error('Details must start collapsed');
   if(p.down('#zfs-snapshot-tabs').items.length!==2)throw Error('Exactly two snapshot tabs required');
   const tree=p.down('#zfs-guest-snapshot-tree');
   if(tree.getRootNode().childNodes.length!==4)throw Error('Fixture guests missing');
   if(tree.getRootNode().childNodes.some(n=>n.isExpanded()))throw Error('Guests must start collapsed');
   const autoSnapColors={};
   for(const [id,state] of [[103,'included'],[108,'excluded'],[701,'partial']]){
    const rec=tree.getRootNode().childNodes.find(g=>g.get('guestId')===String(id));
    const row=tree.getView().getNode(rec),cell=row&&row.querySelector('.x-grid-cell');
    const color=cell&&getComputedStyle(cell).backgroundColor;
    if(!row||!(row.classList.contains('zfsm-autosnap-'+state)||row.querySelector('.zfsm-autosnap-'+state)))throw Error('Missing AutoSnap row status: '+state);
    const rgba=color.match(/[0-9.]+/g).map(Number);
    if(rgba.length!==4||rgba[3]<=0||rgba[3]>.13)throw Error('AutoSnap tint is missing or too strong: '+color);
    if(state==='included'&&rgba[1]<=rgba[0])throw Error('Included guest is not green');
    if(state==='excluded'&&rgba[0]<=rgba[1])throw Error('Excluded guest is not red');
    autoSnapColors[state]=color;
   }
   const actionAlignment=[];
   for(const panelWidth of [1180,1600]){
    p.setWidth(panelWidth);p.updateLayout();
    const column=tree.columns.find(c=>c.xtype==='widgetcolumn');
    let reference;
    for(const rec of tree.getRootNode().childNodes){
     const widget=column.getWidget(rec),cell=tree.getView().getNode(rec).querySelector('.x-grid-cell:last-child');
     const boxes=['guest-create','guest-autosnap','guest-delete-all'].map(id=>{
      const button=widget.down('#'+id),el=button.getEl().dom,box=el.getBoundingClientRect();
      const text=el.querySelector('.x-btn-inner');
      if(text&&text.scrollWidth>text.clientWidth+1)throw Error('Guest action text clipped: '+id);
      return {left:box.left,width:box.width,right:box.right};
     });
     if(reference&&boxes.some((b,i)=>Math.abs(b.left-reference[i].left)>.5||Math.abs(b.width-reference[i].width)>.5))throw Error('Guest actions do not align across AutoSnap states');
     if(boxes[2].right>cell.getBoundingClientRect().right+1)throw Error('Guest action exceeds its column');
     reference=boxes;
    }
    actionAlignment.push({panelWidth,aligned:true,labelsFit:true});
   }
   const tabs=p.down('#zfs-snapshot-tabs'),datasets=p.down('#zfs-ro-snapshots');
   tabs.setActiveTab(1);p.updateLayout();
   const datasetColors={};
   for(const state of ['included','excluded','partial']){
    const rec=datasets.getRootNode().childNodes.find(d=>d.get('dataset')==='rpool/host-'+state);
    const row=datasets.getView().getNode(rec),cell=row.querySelector('.x-grid-cell');
    if(!(row.classList.contains('zfsm-autosnap-'+state)||row.querySelector('.zfsm-autosnap-'+state)))throw Error('Dataset status missing: '+state);
    datasetColors[state]=getComputedStyle(cell).backgroundColor;
   }
   const excluded=datasets.getRootNode().childNodes.find(d=>d.get('dataset')==='rpool/host-excluded');excluded.expand();
   const column=datasets.columns.find(c=>c.xtype==='widgetcolumn');let snapshotButtons;
   for(const rec of excluded.childNodes){
    const widget=column.getWidget(rec),boxes=['zfs-row-delete','zfs-row-delete-exact','zfs-row-rollback'].map(id=>{
     const el=widget.down('#'+id).getEl().dom,text=el.querySelector('.x-btn-inner');
     if(text&&text.scrollWidth>text.clientWidth+1)throw Error('Dataset action label clipped: '+id);
     return el.getBoundingClientRect();
    });
    if(snapshotButtons&&boxes.some((b,i)=>Math.abs(b.left-snapshotButtons[i].left)>.5||b.width!==snapshotButtons[i].width))throw Error('Dataset actions not aligned');
    const last=boxes[2],cell=datasets.getView().getNode(rec).querySelector('.x-grid-cell:last-child');
    if(last.right>cell.getBoundingClientRect().right+1)throw Error('Dataset actions overflow');
    snapshotButtons=boxes;
   }
   excluded.collapse();tabs.setActiveTab(0);p.updateLayout();
   const first=tree.getRootNode().firstChild;first.expand();
   const group=first.firstChild;group.set('batchMarked',true);
   const check=tree.columns[0];check.fireEvent('checkchange',check,tree.getStore().indexOf(group),true);
   if(group.isExpanded())throw Error('Checkbox unexpectedly expanded snapshot group');
   p.down('#zfsm-guest-filter').setValue('Windows');
   if(tree.getRootNode().childNodes.length!==1)throw Error('Guest filter failed');
   p.down('#zfsm-guest-filter').setValue('');
   if(!tree.getRootNode().firstChild.isExpanded())throw Error('Filter lost prior expansion');
   if(!tree.getRootNode().firstChild.firstChild.get('batchMarked'))throw Error('Filter lost snapshot selection');
   const save=p.down('#zfs-retention-save'),keep=p.down('#zfs-retention-keep');
   const original=Ext.Msg.show,dialogs=[];Ext.Msg.show=function(opts){dialogs.push(opts);return this;};
   keep.setValue(10);save.handler(save);keep.setValue(9);Ext.Msg.show=original;
   if(dialogs.length!==1)throw Error('Retention button did not open the mandatory preview');
   technical.expand();services.expand();
   p.zfsRefreshReadOnly();
   await new Promise(resolve=>setTimeout(resolve,80));
   if(technical.collapsed||services.collapsed)throw Error('Refresh collapsed details');
   if(!tree.getRootNode().firstChild.firstChild.get('batchMarked'))throw Error('Refresh lost snapshot selection');
   technical.collapse();services.collapse();
   const nodes=p.query('[itemId]'),ids=nodes.map(n=>n.itemId);
   // Widget IDs intentionally repeat per row; section IDs must be unique.
   const sectionIds=ids.filter(id=>id.startsWith('zfsm-')||id.startsWith('zfs-ro-'));
   if(new Set(sectionIds).size!==sectionIds.length)throw Error('Duplicate section IDs');
   if(p.down('#zfs-ro-retention').getEl().dom.querySelectorAll('tbody tr')[1].children[2].textContent.trim()!=='7')throw Error('Observed total missing');
   tree.getRootNode().firstChild.collapse();
   return {datasetColors,actionAlignment,autoSnapColors,lang:document.cookie,ext:Ext.getVersion().toString(),tabs:2,guests:tree.getRootNode().childNodes.length,technicalCollapsed:technical.collapsed,filterPreservesExpansion:true,refreshPreservesSections:true,refreshPreservesSelection:true,checkboxDoesNotExpand:true,retentionPreviewRequired:true,detailsButtonWorks:true,apiWrites:calls.filter(c=>c.method!=='GET').length,fixtureError:window.fixtureError||null};
  });
  assert.equal(proof.fixtureError,null);assert.equal(errors.length,0,errors.join('\n'));
  await page.evaluate(()=>{plugin.down('#zfs-snapshot-tabs').setActiveTab(1);const tree=plugin.down('#zfs-ro-snapshots');tree.getRootNode().childNodes.find(d=>d.get('dataset')==='rpool/host-excluded').expand();plugin.updateLayout();});
  await page.screenshot({path:out+'/datasets-'+lang+'.png',fullPage:true});
  await page.evaluate(()=>{plugin.down('#zfs-ro-snapshots').getRootNode().childNodes.find(d=>d.get('dataset')==='rpool/host-excluded').collapse();plugin.down('#zfs-snapshot-tabs').setActiveTab(0);plugin.updateLayout();});
  if(clusterMode){
   proof.cluster=await page.evaluate(async()=>{
    const wait=async fn=>{for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setTimeout(r,20));}throw Error('Cluster dialog timeout');};
    const button=plugin.down('#zfsm-cluster-open');if(button.hidden)throw Error('Root cluster control hidden');button.handler();
    await wait(()=>Ext.ComponentQuery.query('window').some(w=>w.down('#cluster-nodes')));
    const win=Ext.ComponentQuery.query('window').find(w=>w.down('#cluster-nodes')),grid=win.down('#cluster-nodes');
    await wait(()=>grid.getStore().getCount()===2);
    const selection=grid.getSelectionModel();
    if(selection.getSelection().length)throw Error('Nodes selected automatically');
    selection.select(grid.getStore().getAt(1));if(selection.getSelection().length)throw Error('Offline node selectable');
    selection.select(grid.getStore().first());
    const check=win.down('#cluster-check'),install=win.down('#cluster-install'),ack=win.down('#cluster-ack');
    if(!install.disabled||!ack.disabled)throw Error('Installation enabled before preview');
    check.handler();await wait(()=>!ack.disabled);
    if(calls.some(c=>c.url.endsWith('cluster-install')))throw Error('Preview installed a package');
    if(!install.disabled)throw Error('Installation enabled without checkbox');
    if(win.down('#cluster-report').getEl().dom.querySelector('img'))throw Error('Backend text was not escaped');
    ack.setValue(true);if(install.disabled)throw Error('Checkbox did not enable installation');
    const oldConfirm=Ext.Msg.confirm;let confirmations=0;
    Ext.Msg.confirm=(title,text,cb)=>{confirmations++;cb('yes');};install.handler();Ext.Msg.confirm=oldConfirm;
    await wait(()=>calls.some(c=>c.url.endsWith('cluster-job')&&c.params.job==='b'.repeat(32))&&!check.disabled);
    if(confirmations!==1||!install.disabled)throw Error('Missing confirmation or install control not reset');
    const writes=calls.filter(c=>c.method==='POST');
    if(writes.length!==2)throw Error('Unexpected mutation request count');
    return {explicitSelection:true,offlineBlocked:true,previewRequired:true,checkboxRequired:true,
      confirmationRequired:true,coordinatorRouting:true,backendHtmlEscaped:true,fixtureOnly:true};
   });
   assert.equal(errors.length,0,errors.join('\n'));
  }
  if(guestMode){
   await page.screenshot({path:out+'/autosnap-status-'+lang+'.png',fullPage:true});
   proof.guestControls=await page.evaluate(async()=>{
    const p=plugin,tree=p.down('#zfs-guest-snapshot-tree');
    const wait=async fn=>{for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setTimeout(r,20));}throw Error('Guest control timeout');};
    const getGuest=kind=>tree.getRootNode().childNodes.find(g=>g.get('guestType')===kind);
    let confirms=0;const oldConfirm=Ext.Msg.confirm;
    Ext.Msg.confirm=(title,text,callback)=>{confirms++;callback('yes');};
    for(const kind of ['vm','lxc']){
     for(const action of ['autosnap','autosnap','delete-all']){
      const rec=getGuest(kind),before=calls.filter(c=>c.method==='POST').length;
      const column=tree.columns.find(c=>c.xtype==='widgetcolumn');
      const widget=column.getWidget(rec),button=widget.down(action==='autosnap'?'#guest-autosnap':'#guest-delete-all');
      if(button.hidden||button.disabled)throw Error('Guest action unavailable');
      button.handler(button);
      await wait(()=>Ext.ComponentQuery.query('window').some(w=>w.down('#ack')));
      const win=Ext.ComponentQuery.query('window').find(w=>w.down('#ack'));
      const execute=win.getDockedItems('toolbar[dock="bottom"]')[0].items.last();
      execute.handler();
      if(calls.filter(c=>c.method==='POST').length!==before)throw Error('Unchecked action wrote');
      win.down('#ack').setValue(true);execute.handler();
      await wait(()=>!p.zfsReadOnly.saving&&!p.zfsReadOnly.refreshing);
      if(calls.filter(c=>c.method==='POST').length!==before+1)throw Error('Missing confirmed write');
      if(!getGuest(kind).get('autosnapExcluded')&&action==='autosnap'&&before%3===0)throw Error('Exclusion status not refreshed');
      if(tree.getRootNode().childNodes.some(g=>g.isExpanded()))throw Error('Action expanded guest');
     }
    }
    if(confirms!==6)throw Error('Second confirmations missing');
    Ext.Msg.confirm=oldConfirm;
    p.zfsReadOnly.isAdmin=false;
    const count=calls.length;p.zfsmGuestWide('delete-all',getGuest('vm'));
    if(calls.length!==count)throw Error('Read-only session enabled action');
    p.zfsReadOnly.isAdmin=true;
    return {vmAndLxc:true,excludeAndEnable:true,deleteAll:true,checkboxRequired:true,secondConfirmation:true,refreshPreservesCollapse:true,fixtureOnly:true};
   });
   assert.equal(errors.length,0,errors.join('\n'));
  }
  if(updateMode){
   proof.updates=await page.evaluate(async()=>{
    const wait=async fn=>{for(let i=0;i<100;i++){if(fn())return;await new Promise(r=>setTimeout(r,20));}throw Error('Update dialog timeout');};
    const button=plugin.down('#zfsm-update-open');button.handler(button);
    const win=Ext.ComponentQuery.query('window').find(w=>w.down('#update-check'));
    const check=win.down('#update-check'),install=win.down('#update-install'),ack=win.down('#update-ack');
    await wait(()=>!install.disabled);
    if(calls.some(c=>c.url.endsWith('/update-check')||c.url.endsWith('/update-prepare')||c.url.endsWith('/update-install')))throw Error('Opening update status mutated host');
    check.handler();await wait(()=>!check.disabled&&!install.disabled);
    if(calls.some(c=>c.url.endsWith('/update-install')))throw Error('Checking installed an update');
    install.handler();await wait(()=>!ack.disabled);
    if(!install.disabled)throw Error('Update installation enabled without acknowledgment');
    install.handler();if(calls.some(c=>c.url.endsWith('/update-install')))throw Error('Unchecked update installed');
    ack.setValue(true);if(install.disabled)throw Error('Confirmation did not enable update');
    const oldAlert=Ext.Msg.alert;Ext.Msg.alert=()=>{};install.handler();
    await wait(()=>calls.some(c=>c.url.endsWith('/update-job')&&c.params.job==='b'.repeat(32))&&!check.disabled);
    Ext.Msg.alert=oldAlert;win.close();
    if(calls.filter(c=>c.url.endsWith('/update-install')).length!==1)throw Error('Repeated update installation');
    Proxmox.UserName='observer@pve';button.handler(button);
    const readOnly=Ext.ComponentQuery.query('window').find(w=>w.down('#update-check'));
    const before=calls.filter(c=>c.method==='POST').length;
    if(!readOnly.down('#update-check').disabled)throw Error('Observer can start update');
    readOnly.down('#update-check').handler();if(calls.filter(c=>c.method==='POST').length!==before)throw Error('Observer update executed');readOnly.close();
    return {cachedStatusReadOnly:true,checkDoesNotInstall:true,precheckRequired:true,checkboxRequired:true,singleConfirmedInstall:true,observerBlocked:true,fixtureOnly:true};
   });
   assert.equal(errors.length,0,errors.join('\n'));
  }
  await page.screenshot({path:out+'/rc9-'+lang+'.png',fullPage:true});
  results.push(proof);await page.close();
 }
 await browser.close();console.log(JSON.stringify(results,null,2));
})().catch(e=>{console.error(e);process.exit(1)});
