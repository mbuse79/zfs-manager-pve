// Chromium smoke test of the actual GUI block with ExtJS component mocks.
// No PVE host, no API writes. This does not replace real ExtJS/PVE testing.
const fs=require('fs'),{chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 const block=fs.readFileSync(process.argv[2],'utf8');
 const results=[];
 for(const lang of ['de','en']){
  const page=await browser.newPage();
  await page.route('http://rc8.test/**',route=>route.fulfill({body:'<html><body><div id="out"></div></body></html>',contentType:'text/html'}));
  await page.goto('http://rc8.test/');
  const result=await page.evaluate(({block,lang})=>{
   document.cookie='PVELangCookie='+lang;
   window.Proxmox={defaultLang:lang,Utils:{API2Request(){throw Error('API forbidden in this test')}}};
   const encode=x=>String(x).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
   window.safeZFSValue=encode;
   let config;
   window.caps={nodes:{'Sys.Audit':true,'Sys.Modify':true}};window.me={items:[]};window.nodename='fixture';
   window.zfsBytes=x=>String(x);
   window.Ext={String:{htmlEncode:encode},ClassManager:{get(){return false}},
    create(name,c){return c;},define(name,c){config=c;},apply:Object.assign,Utils:{},isArray:Array.isArray};
   new Function(block)();
   config=config||me.items[0];
   if(!config)throw Error('GUI definition missing');
   const labels=[],ids=[];
   function visit(x){if(!x||typeof x!=='object')return;if(x.itemId)ids.push(x.itemId);
    for(const k of ['text','title','boxLabel','html'])if(typeof x[k]==='string')labels.push(x[k]);
    for(const k of ['items','columns','buttons','tbar','bbar'])if(x[k])for(const a of Array.isArray(x[k])?x[k]:[x[k]])visit(a);
   }
   visit(config);
   if(new Set(ids).size!==ids.length)throw Error('Duplicate component IDs');
   const outputs={};
   const view={down(id){return {destroyed:false,update(html){outputs[id]=html;}}}};
   const state={readySnapshots:true,pools:[{name:'tank',size:100,alloc:75,free:25}],
    snapshots:[{dataset:'tank/test',snapshot:'zfs-auto-snap_hourly-2026-11-13-1200',used:42,creation:1700000000},
               {dataset:'tank/test',snapshot:'zfs-auto-snap_hourly-2026-11-13-1300',used:43,creation:1700003600}],
    retention:[{label:'hourly',keep:24,file:'/etc/cron.hourly/zfs-auto-snapshot'}]};
   const render=block.slice(block.indexOf('var renderCapacity = function'),block.indexOf('// The row widgets'));
   new Function('view','state',block+'\n'+render+'\nrenderCapacity();renderRetention(state.retention);')(view,state);
   if(!outputs['#zfs-ro-retention'].includes('/etc/cron.hourly/zfs-auto-snapshot'))throw Error('Cron source missing');
   if(!outputs['#zfs-ro-retention'].includes('>2</td>'))throw Error('Observed count missing');
   document.querySelector('#out').innerHTML=labels.join('<br>')+'<hr>'+outputs['#zfs-capacity-audit']+outputs['#zfs-ro-retention'];
   return {lang,labels:labels.length,ids:ids.length,text:document.body.innerText};
  },{block,lang});
  if(lang==='de'&&!result.text.includes('Aufbewahrung'))throw Error('German content missing');
  if(lang==='en'&&!result.text.includes('Retention'))throw Error('English content missing');
  results.push(result);
  await page.screenshot({path:process.argv[3]+'/gui-'+lang+'.png',fullPage:true});
  await page.close();
 }
 console.log(JSON.stringify(results,null,2));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
