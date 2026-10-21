/* Bundled iOS content only. WebKit replies resolve/reject the returned Promise. */
'use strict';
window.desktopConfig = {platform: 'ios', directory: 'iPhone 本机存储'};
async function nativeRequest(action, payload = {}) {
  const bridge = window.webkit?.messageHandlers?.zzLedger;
  if (!bridge) throw new Error('请使用 iPhone 上的 zz记 App 打开账本');
  try {
    return await bridge.postMessage({action, ...payload});
  } catch (error) {
    throw new Error(error?.message || String(error) || '本地文件操作失败');
  }
}
window.DesktopAPI = Object.freeze({
  read: () => nativeRequest('read'),
  write: value => nativeRequest('write', {value}),
  import: () => nativeRequest('import'),
  export: (content, filename) => nativeRequest('export', {content, filename})
});
