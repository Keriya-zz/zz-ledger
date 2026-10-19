const fs=require('node:fs');
const [phase,backup]=process.argv.slice(2);
(async()=>{
 const targets=await(await fetch('http://127.0.0.1:9222/json')).json();
 const tab=targets.find(t=>t.type==='page'&&t.url.startsWith('https://appassets.androidplatform.net/assets/'));
 if(!tab)throw Error('zz记 WebView not found');
 const socket=new WebSocket(tab.webSocketDebuggerUrl);
 await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
 let id=0;const tasks=new Map();
 socket.onmessage=e=>{const msg=JSON.parse(e.data);const task=tasks.get(msg.id);if(task){tasks.delete(msg.id);msg.error?task.reject(msg.error):task.resolve(msg.result);}};
 const evalJS=expression=>new Promise((resolve,reject)=>{const key=++id;tasks.set(key,{resolve,reject});socket.send(JSON.stringify({id:key,method:'Runtime.evaluate',params:{expression,returnByValue:true,awaitPromise:true}}));}).then(r=>{if(r.exceptionDetails)throw Error(r.exceptionDetails.text);if(r.result.value?.error)throw Error(r.result.value.error);return r.result.value;});
 if(phase==='save'){
  const raw=await evalJS('(async()=>{await zzApp.ready;return DesktopAPI.read()})()');
  const state=JSON.parse(raw);
  if(state.entries.length || (state.transfers||[]).length || state.accounts.some(a=>a.balance!==0))throw Error('Phone ledger is no longer empty; refusing fixture write');
  fs.writeFileSync(backup,raw);
  const check=await evalJS(`(async()=>{try{const id=zzApp.snapshot().accounts[0].id;document.getElementById('add-entry').click();document.getElementById('entry-account').value=id;document.getElementById('entry-amount').value='12.34';document.getElementById('entry-category').value='餐饮';document.getElementById('entry-note').value='安卓真机验证';await document.getElementById('entry-form').onsubmit({preventDefault(){}});const saved=JSON.parse(await DesktopAPI.read());if(saved.entries.length!==1||saved.entries[0].amount!==1234||saved.accounts[0].balance!==-1234)throw Error('Native save mismatch');return {saved:true,entryId:saved.entries[0].id,amount:saved.entries[0].amount};}catch(e){return {error:e.message}}})()`);
  console.log(JSON.stringify(check));
 }else if(phase==='verify-restore'){
  const check=await evalJS(`(async()=>{try{await zzApp.ready;const raw=await DesktopAPI.read();const state=zzApp.snapshot();if(state.entries.length!==1||state.entries[0].amount!==1234||state.accounts[0].balance!==-1234)throw Error('Restart did not restore transaction');await DesktopAPI.write(${JSON.stringify(fs.readFileSync(backup,'utf8'))});const after=await DesktopAPI.read();if(after!==${JSON.stringify(fs.readFileSync(backup,'utf8'))})throw Error('Original ledger restore mismatch');location.reload();return {reopened:true,restored:true};}catch(e){return {error:e.message}}})()`);
  console.log(JSON.stringify(check));
 }else throw Error('Unknown phase');
 socket.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
