// Dedicated Chrome instance for testing our own Android web assets at real phone viewports.
const fs=require('node:fs'),cp=require('node:child_process'),path=require('node:path');
const [url,width,height,profileBase,png,html]=process.argv.slice(2);
const profile=profileBase+'-'+process.pid;
(async()=>{
 fs.mkdirSync(profile,{recursive:true}); const active=path.join(profile,'DevToolsActivePort');if(fs.existsSync(active))fs.unlinkSync(active);
 const chrome=cp.spawn(process.env.CHROME_BIN,['--headless','--disable-gpu','--disable-extensions','--disable-background-networking','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--remote-allow-origins=*','--user-data-dir='+profile,'about:blank'],{stdio:'ignore',windowsHide:true});
 let ws;
 try {
  for(let i=0;i<100&&!fs.existsSync(active);i++)await new Promise(r=>setTimeout(r,100));
  const port=fs.readFileSync(active,'utf8').split('\n')[0];
  const tabs=await(await fetch('http://127.0.0.1:'+port+'/json')).json();
  const tab=tabs.find(t=>t.type==='page' && t.url==='about:blank');if(!tab)throw new Error('Test page not found');
  ws=new WebSocket(tab.webSocketDebuggerUrl);await new Promise((r,j)=>{ws.onopen=r;ws.onerror=j;setTimeout(()=>j(new Error('WebSocket timeout')),5000).unref();});
  let id=0;const waiting=new Map();ws.onmessage=e=>{const m=JSON.parse(e.data);if(waiting.has(m.id)){const t=waiting.get(m.id);waiting.delete(m.id);m.error?t.reject(m.error):t.resolve(m.result);}};
  const call=(method,params={})=>new Promise((resolve,reject)=>{const key=++id;const timer=setTimeout(()=>{waiting.delete(key);reject(new Error('CDP timeout: '+method));},8000);waiting.set(key,{resolve:v=>{clearTimeout(timer);resolve(v);},reject:e=>{clearTimeout(timer);reject(e);}});ws.send(JSON.stringify({id:key,method,params}));});
  await call('Page.enable');await call('Emulation.setDeviceMetricsOverride',{width:+width,height:+height,deviceScaleFactor:1,mobile:true});
  await call('Page.navigate',{url});
  for(let i=0;i<150;i++){
   const result=await call('Runtime.evaluate',{expression:'document.body?.dataset.qaResult || ""',returnByValue:true});
   if(result.result.value)break;
   await new Promise(r=>setTimeout(r,100));
  }
  const dom=await call('Runtime.evaluate',{expression:'document.documentElement.outerHTML',returnByValue:true});fs.writeFileSync(html,dom.result.value);
  const shot=await call('Page.captureScreenshot',{format:'png'});fs.writeFileSync(png,Buffer.from(shot.data,'base64'));
  ws.send(JSON.stringify({id:++id,method:'Browser.close'}));
 }finally {if(ws)ws.close();chrome.kill();}
})().catch(e=>{console.error(e);process.exitCode=1;});
