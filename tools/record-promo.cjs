// Record the real 1.1 ExtJS panel against labelled, isolated sample data.
// No Proxmox hosts or production APIs are contacted. No install/delete is performed.
const fs=require('fs'),path=require('path'),assert=require('assert'),{chromium}=require('playwright');
(async()=>{
 const extRoot=path.resolve(process.argv[2]),toolkit=path.resolve(process.argv[3]),out=path.resolve(process.argv[4]),script=fs.readFileSync(process.argv[5],'utf8');
 const video=process.argv.includes('--video');fs.mkdirSync(out,{recursive:true});
 const harness=fs.readFileSync(path.join(__dirname,'../tests/browser_rc9.cjs'),'utf8');
 let init=harness.split('  await page.evaluate(({script,lang,clusterMode})=>{')[1].split('  },{script,lang,clusterMode});')[0];
 assert(init.includes('window.Proxmox'));
 const guestsStart=init.indexOf("[['vm',"),guestsEnd=init.indexOf('.forEach(([kind,id,name,count])=>{',guestsStart);
 assert(guestsStart>=0&&guestsEnd>guestsStart);
 init=init.slice(0,guestsStart)+"[['vm',101,'webserver-demo',1],['vm',102,'database-demo',3],['ct',201,'app-container-demo',2],['ct',202,'fileserver-demo',1]]"+init.slice(guestsEnd);
 for(const [a,b] of [["'fixture-coordinator'","'demo-node-a'"],["'node-a'","'demo-node-b'"],["'node-b'","'demo-node-c'"],['/nodes/fixture-coordinator/','/nodes/demo-node-a/'],['<img src=x onerror=alert(1)> fixture escaped','Example preflight verified. Demo data; no host connected.']])init=init.split(a).join(b);
 init=init.replace(/new Function\('me','caps','nodename',script\)\(me,caps,'[^']+'\);/,"new Function('me','caps','nodename',script)(me,caps,'demo-node-a');");
 init=init.replace('944*1024**3','512*1024**3').replace('628*1024**3','256*1024**3').replace('316*1024**3','256*1024**3').replace('frag:66','frag:18');
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 for(const lang of ['de','en']){
  const context=await browser.newContext({viewport:{width:1640,height:1080},...(video&&lang==='en'?{recordVideo:{dir:out,size:{width:1640,height:1080}}}:{})});
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',async route=>{
   const url=new URL(route.request().url());if(url.hostname!=='demo.zfsm.invalid')throw Error('Unexpected external request: '+url.hostname);
   const pathname=url.pathname;
   for(const [prefix,root] of [['/extjs/',extRoot],['/toolkit/',toolkit]]){
    if(pathname.startsWith(prefix)){
     const f=path.resolve(root,pathname.slice(prefix.length));
     if(!f.startsWith(root+path.sep)||!fs.existsSync(f))return route.fulfill({status:404,body:''});
     return route.fulfill({path:f,contentType:f.endsWith('.js')?'application/javascript':f.endsWith('.css')?'text/css':undefined});
    }
   }
   const demo=lang==='de'?'DEMO · Testdaten · Keine Hostverbindung':'DEMO · Sample data · No hosts connected';
   return route.fulfill({contentType:'text/html',body:`<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/extjs/theme-crisp/resources/theme-crisp-all.css"><link rel="stylesheet" href="/toolkit/css/ext6-pmx.css"><link rel="stylesheet" href="/toolkit/themes/theme-proxmox-dark.css"><script src="/extjs/ext-all.js"></script><style>body{margin:0;background:#202020;font-family:Arial}header{position:sticky;top:0;z-index:20000;height:48px;background:#142c38;color:#eef7fc;display:flex;align-items:center;justify-content:space-between;padding:0 22px;box-sizing:border-box;font-size:16px}header small{color:#b9dce8;font-size:13px}#app{margin:10px 12px 95px}.x-fieldset-header-text{font-weight:bold}#caption{position:fixed;bottom:0;left:0;right:0;z-index:20000;background:#142c38;color:#fff;padding:15px 24px;min-height:64px;box-sizing:border-box;font-size:18px;line-height:1.4;border-top:2px solid #3896bf}</style></head><body><header><b>BuMaVory ZFS Manager 1.1</b><small>${demo}</small></header><div id="app"></div><div id="caption"></div></body></html>`});
  });
  await page.goto('http://demo.zfsm.invalid/');await page.waitForFunction(()=>window.Ext&&Ext.isReady);
  await page.evaluate(({init,script,lang})=>{new Function('script','lang','clusterMode',init)(script,lang,true);},{init,script,lang});
  await page.waitForFunction(()=>window.plugin&&!plugin.zfsReadOnly.refreshing);
  const caption=async(de,en)=>page.evaluate(text=>{document.getElementById('caption').textContent=text;},lang==='de'?de:en);
  const still=async name=>{await page.evaluate(()=>{document.getElementById('caption').style.display='none';document.getElementById('app').style.marginBottom='10px';});await page.screenshot({path:path.join(out,name),fullPage:true});await page.evaluate(()=>{document.getElementById('caption').style.display='';document.getElementById('app').style.marginBottom='95px';});};
  await caption('ZFS direkt in der vorhandenen Proxmox-Oberfläche verwalten.','Manage ZFS in the existing Proxmox interface.');
  await still(`overview-${lang}.png`);
  if(video&&lang==='en')await page.waitForTimeout(12000);
  await page.evaluate(()=>{plugin.down('#zfsm-technical-details').expand();});
  await caption('Poolbelegung, Fragmentierung und technische Details getrennt betrachten.','Pool capacity, fragmentation and technical details stay separate.');
  if(video&&lang==='en')await page.waitForTimeout(16000);
  await page.evaluate(()=>{plugin.down('#zfsm-technical-details').collapse();const tree=plugin.down('#zfs-guest-snapshot-tree');tree.getRootNode().childNodes.forEach(n=>n.expand());tree.getEl().dom.scrollIntoView({block:'center'});});
  await caption('VM-/LXC-Datenträger und Snapshots gemeinsam überblicken.','Inspect VM/LXC disks and snapshots in one grouped view.');
  if(video&&lang==='en')await page.waitForTimeout(16000);
  await page.evaluate(()=>{plugin.down('#zfsm-guest-filter').setValue('webserver');});
  if(video&&lang==='en')await page.waitForTimeout(6000);
  await page.evaluate(()=>{plugin.down('#zfsm-guest-filter').setValue('');plugin.down('#zfs-snapshot-tabs').setActiveTab(1);});
  await caption('Zwei getrennte Ansichten: VMs/LXC und ZFS-Datasets.','Two views: VMs/LXC and ZFS datasets.');
  if(video&&lang==='en')await page.waitForTimeout(14000);
  await page.evaluate(()=>{plugin.down('#zfs-snapshot-tabs').setActiveTab(0);plugin.down('#zfs-ro-retention').getEl().dom.scrollIntoView({block:'center'});});
  await caption('Aufbewahrung je Dataset; beobachtete Gesamtzahl separat. Änderungen benötigen eine Vorschau.','Retention per dataset, observed totals separately. Changes require review.');
  if(video&&lang==='en')await page.waitForTimeout(18000);
  await page.evaluate(()=>window.scrollTo(0,0));
  await page.evaluate(()=>plugin.down('#zfsm-cluster-open').handler());
  await page.waitForFunction(()=>Ext.ComponentQuery.query('window').some(w=>w.down('#cluster-nodes')&&w.down('#cluster-nodes').getStore().getCount()===2));
  await page.evaluate(()=>{const w=Ext.ComponentQuery.query('window').find(w=>w.down('#cluster-nodes'));w.down('#cluster-nodes').getSelectionModel().select(0);});
  await caption('Clusterinstallation nur nach bewusster Knotenauswahl und Prüfung. Offline-Knoten sind gesperrt.','Cluster rollout is opt-in: select nodes and preflight. Offline nodes are blocked.');
  await still(`cluster-${lang}.png`);
  if(video&&lang==='en')await page.waitForTimeout(14000);
  await page.evaluate(()=>{const w=Ext.ComponentQuery.query('window').find(w=>w.down('#cluster-nodes'));w.down('#cluster-check').handler();});
  await page.waitForFunction(()=>Ext.ComponentQuery.query('window').some(w=>w.down('#cluster-ack')&&!w.down('#cluster-ack').disabled));
  await caption('Demo-Vorprüfung: Keine echte Installation. Häkchen und Bestätigung wären zusätzlich erforderlich.','Demo preflight only. Installation would require the approval checkbox and confirmation.');
  if(video&&lang==='en')await page.waitForTimeout(14000);
  await page.evaluate(()=>{Ext.ComponentQuery.query('window').find(w=>w.down('#cluster-nodes')).close();});
  await caption('Quellcode und Installation: github.com/mbuse79/zfs-manager-pve · Unabhängiges Community-Projekt.','Source and installation: github.com/mbuse79/zfs-manager-pve · Independent community project.');
  if(video&&lang==='en')await page.waitForTimeout(10000);
  assert(!page.isClosed());assert.deepEqual(errors,[]);
  const calls=await page.evaluate(()=>window.calls);
  assert(!calls.some(c=>c.url.endsWith('cluster-install')));
  assert(calls.filter(c=>c.method==='POST').every(c=>c.url.endsWith('cluster-preview')));
  fs.writeFileSync(path.join(out,`demo-proof-${lang}.json`),JSON.stringify({lang,realHostsContacted:0,actualInstalls:0,errors,apiFixtureCalls:calls.length},null,2));
  const recording=page.video();await context.close();
  if(recording){fs.renameSync(await recording.path(),path.join(out,'zfsm-1.1-demo-en.webm'));}
 }
 await browser.close();
 console.log('Demo screens/recording complete; isolated sample data only.');
})().catch(e=>{console.error(e.stack);process.exit(1);});
