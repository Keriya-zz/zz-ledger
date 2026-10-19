/* Android edition: local files only; Windows keeps its existing storage adapter. */
'use strict';
window.desktopConfig = {platform:'android',directory:'App 私有存储'};
const pending = new Map();
let requestId = 0;
window.zzNativeReply = (id, result) => {
  const task=pending.get(id); if (!task) return;
  pending.delete(id);
  if (result.error) task.reject(new Error(result.error)); else task.resolve(result.value);
};
function nativeRequest(action, payload) {
  if (!window.ZZNative) return Promise.reject(new Error('请使用安卓 App 打开账本'));
  return new Promise((resolve,reject)=> {
    const id=String(++requestId); pending.set(id,{resolve,reject});
    try { window.ZZNative.request(id,action,JSON.stringify(payload || {})); }
    catch(error) { pending.delete(id); reject(error); }
  });
}
window.DesktopAPI = Object.freeze({
  read:()=>nativeRequest('read'),
  write:value=>nativeRequest('write',{value}),
  export:(content,filename)=>nativeRequest('export',{content,filename})
});
