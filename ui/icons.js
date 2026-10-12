'use strict';
// Shared line icons: no external fonts or network assets are required.
window.Icons = Object.freeze({
  draw(name) {
    const paths = {
      overview:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
      wallet:'<rect x="3" y="5" width="18" height="15" rx="3"/><path d="M3 9h18m-4 4h4v4h-4a2 2 0 0 1 0-4Z"/><path d="M6 5V3h12"/>',
      repayment:'<path d="M5 8h13m-4-4 4 4-4 4M19 16H6m4 4-4-4 4-4"/>',
      chart:'<path d="M4 3v17h17M8 15v-4m5 4V6m5 9V9"/>',
      food:'<path d="M4 3v6a3 3 0 0 0 6 0V3M7 3v18M19 21V3c-4 2-5 5-5 9h5"/>',
      train:'<rect x="5" y="3" width="14" height="16" rx="4"/><path d="M5 10h14M8 19l-2 3m10-3 2 3M8 15h1m6 0h1"/>',
      bag:'<path d="M4 8h16l1 13H3L4 8Z"/><path d="M8 9V6a4 4 0 0 1 8 0v3"/>',
      home:'<path d="m3 10 9-7 9 7M5 9v12h14V9M9 21v-7h6v7"/>',
      music:'<path d="M9 17V5l11-2v12M9 8l11-2"/><ellipse cx="6" cy="18" rx="3" ry="2.5"/><ellipse cx="17" cy="16" rx="3" ry="2.5"/>',
      health:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M8 5V3h8v2m-4 6v6m-3-3h6"/>',
      chat:'<path d="M12 3c-5 0-9 3-9 7 0 2 1 4 3 5l-1 4 4-2h3c5 0 9-3 9-7S17 3 12 3Z"/><path d="M8 10h.01M12 10h.01M16 10h.01"/>',
      bank:'<path d="m3 7 9-5 9 5H3Zm1 14h16M6 10v7m6-7v7m6-7v7M3 18h18"/>',
      cash:'<rect x="2" y="5" width="20" height="14" rx="2"/><circle cx="12" cy="12" r="3"/><path d="M5 9h1m12 6h1"/>',
      more:'<circle cx="12" cy="12" r="9"/><path d="M7 12h.01M12 12h.01M17 12h.01"/>',
      arrow:'<path d="M5 19 19 5M7 5h12v12"/>',
      download:'<path d="M12 3v12m-4-4 4 4 4-4M4 16v4h16v-4"/>',
      upload:'<path d="M12 15V3m-4 4 4-4 4 4M4 16v4h16v-4"/>',
      search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>'
    };
    return `<svg class="line-icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${paths[name] || paths.more}</svg>`;
  },
  account(type) { return this.draw({'微信':'chat','支付宝':'wallet','银行卡':'bank','现金':'cash','其他':'wallet'}[type]); },
  category(category) { return this.draw({'餐饮':'food','交通':'train','购物':'bag','生活':'home','娱乐':'music','医疗':'health','还款':'repayment','其他':'more'}[category]); }
});
document.querySelectorAll('nav [data-view]').forEach(button => {
  button.querySelector('span').innerHTML = window.Icons.draw({home:'overview',accounts:'wallet',debts:'repayment',stats:'chart'}[button.dataset.view]);
});
document.querySelectorAll('.search-box>span').forEach(span => span.innerHTML = window.Icons.draw('search'));
document.querySelectorAll('.summary-icon').forEach(span => span.innerHTML = window.Icons.draw(span.classList.contains('income-icon') ? 'chart' : 'arrow'));
document.getElementById('export-btn').innerHTML = window.Icons.draw('download')+'导出备份';
document.getElementById('import-btn').innerHTML = window.Icons.draw('upload')+'导入账本';
