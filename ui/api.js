'use strict';
// 文件接口与原生窗口桥接；界面不再使用阻塞的 XMLHttpRequest。
window.DesktopAPI = Object.freeze({
  async request(endpoint, payload) {
    const response = await fetch(endpoint, {
      method: payload === undefined ? 'GET' : 'POST',
      headers: {'X-ZZ-Token': window.desktopConfig.token, 'Content-Type': 'application/json'},
      body: payload === undefined ? undefined : JSON.stringify(payload),
      cache: 'no-store'
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || '账本文件读写失败');
    return result;
  },
  async read() { return (await this.request('/api/ledger')).value; },
  async write(value) { await this.request('/api/ledger', {value}); },
  async export(content, filename) { return this.request('/api/export', {content, filename}); }
});

async function nativeControl(action) {
  if (action === 'close' && window.zzApp?.isSaving?.()) {
    document.getElementById('save-status').textContent = '正在保存，请稍后关闭';
    return;
  }
  if (!window.pywebview?.api) return;
  const result = await window.pywebview.api[action]();
  if (action === 'toggle_maximize') {
    const button = document.getElementById('window-maximize');
    button.setAttribute('aria-label', result.maximized ? '还原窗口' : '最大化');
    button.title = result.maximized ? '还原窗口' : '最大化';
  }
}
document.getElementById('window-minimize').onclick = () => nativeControl('minimize');
document.getElementById('window-maximize').onclick = () => nativeControl('toggle_maximize');
document.getElementById('window-close').onclick = () => nativeControl('close');
document.getElementById('title-drag').ondblclick = () => nativeControl('toggle_maximize');
