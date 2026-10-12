'use strict';
window.zzApp = {};
window.zzApp.ready = (async function initialize() {
const $ = id => document.getElementById(id);
if (!window.desktopConfig) {
  document.body.innerHTML = '<main style="margin:40px;width:auto"><h1>zz记 · 日常账本</h1><p>请双击 zz记.exe 启动软件，此文件仅用于桌面软件的内部界面。</p></main>';
  throw new Error('zz记仅支持桌面软件入口');
}
const escapeHtml = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const money = n => (n / 100).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const localDate = (d = new Date()) => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
const today = localDate();
const storage = window.DesktopAPI;
let state, editEntryId = null, editAccountId = null, confirmCallback = null, toastTimer;
let storageBlocked = false, saving = false, saved = null;
window.zzApp.snapshot = () => JSON.parse(JSON.stringify(state));
window.zzApp.isSaving = () => saving;
try {
  saved = await storage.read();
  state = saved ? Ledger.validate(JSON.parse(saved)) : Ledger.initial();
} catch (error) {
  storageBlocked = true;
  state = Ledger.initial();
}
const debtUI = window.createDebtUI({getState:()=>state, commit, money, today, toast, confirmAction, options, openAccount, escapeHtml});
function toast(message) {
  clearTimeout(toastTimer); $('toast').textContent = message; $('toast').hidden = false;
  toastTimer = setTimeout(() => $('toast').hidden = true, 4200);
}
async function commit(next, recovery = false) {
  Ledger.validate(next);
  if (storageBlocked && !recovery) throw new Error('本地账本无法读取，请导入有效备份后再保存。');
  if (saving) throw new Error('上一笔正在保存，请稍后再试。');
  saving = true;
  document.body.classList.add('is-saving');
  $('save-status').textContent = '正在保存…';
  try {
    await storage.write(JSON.stringify(next));
    state = next;
    if (recovery) storageBlocked = false;
    render();
    $('save-status').textContent = '已保存到本地';
  } catch (error) {
    $('save-status').textContent = '保存失败，请重试';
    throw error;
  } finally {
    saving = false;
    document.body.classList.remove('is-saving');
  }
}
function confirmAction(title, message, callback, label = '确定') {
  $('confirm-title').textContent = title; $('confirm-message').textContent = message;
  $('confirm-action').textContent = label; confirmCallback = callback;
  $('confirm-dialog').showModal();
}
$('confirm-action').onclick = async () => {
  const callback = confirmCallback; confirmCallback = null; $('confirm-dialog').close();
  try { await callback?.(); } catch(error) { toast(error.message); }
};
document.querySelectorAll('[data-close]').forEach(b => b.onclick = () => $(b.dataset.close).close());
const icons = { '微信':['微','wechat'], '支付宝':['支','alipay'], '银行卡':['▤','bank'], '现金':['¥','cash'], '其他':['◇','other'] };
const categoryIcons = {'餐饮':'♨','交通':'↗','购物':'▢','生活':'⌂','娱乐':'♫','医疗':'✚','还款':'↗','其他':'◇'};
function accountCards(management) {
  if (!state.accounts.length) return '<div class="empty-state"><div class="empty-symbol">◇</div><p>还没有账户，添加一个开始记账吧。</p><button class="text-btn" data-new-account>＋ 添加账户</button></div>';
  return state.accounts.map(a => {
    const [symbol, color] = icons[a.type];
    return `<article class="account-card"><div class="account-top"><span class="account-icon ${color}">${Icons.account(a.type)}</span><div class="account-info"><h3>${escapeHtml(a.name)}</h3><small>${a.type} · 可用余额</small></div>${management ? '' : `<button class="account-edit" data-edit-account="${escapeHtml(a.id)}">编辑</button>`}</div><div class="account-value ${a.balance < 0 ? 'negative':''}"><small>¥</small>${money(a.balance)}</div>${management ? `<div class="account-actions"><button class="text-btn" data-edit-account="${escapeHtml(a.id)}">编辑账户</button><button class="danger-btn" data-delete-account="${escapeHtml(a.id)}">删除</button></div>` : ''}</article>`;
  }).join('');
}
function options(selected, all) {
  return (all ? '<option value="">全部账户</option>' : '') + state.accounts.map(a => `<option value="${escapeHtml(a.id)}" ${a.id === selected ? 'selected':''}>${escapeHtml(a.name)}</option>`).join('');
}
function selectedEntries() {
  const query = $('search').value.trim().toLowerCase();
  return state.entries.filter(e => e.date === $('selected-date').value && (!$('filter-account').value || e.accountId === $('filter-account').value) && (!query || `${e.note} ${e.category}`.toLowerCase().includes(query)));
}
function renderDaily() {
  const sum = Ledger.totals(state, $('selected-date').value);
  $('day-expense').textContent = '¥ ' + money(sum.expense);
  $('day-income').textContent = '¥ ' + money(sum.income);
  $('day-count').textContent = `${sum.count} 笔记录`;
  const list = selectedEntries();
  $('entry-list').innerHTML = list.length ? list.map(e => {
    const a = state.accounts.find(a => a.id === e.accountId);
    return `<div class="entry-row"><span class="entry-icon">${e.kind === 'income' ? Icons.draw('arrow') : Icons.category(e.category)}</span><div class="entry-content"><strong>${escapeHtml(e.note || (e.kind === 'income' ? '收入' : e.category))}</strong><small>${escapeHtml(a.name)} · ${e.category} · ${e.kind === 'income' ? '收入':'支出'}</small></div><span class="entry-money ${e.kind === 'income' ? 'income':''}">${e.kind === 'income' ? '+' : '−'} ¥ ${money(e.amount)}</span><div class="entry-actions"><button data-edit-entry="${escapeHtml(e.id)}">编辑</button><button class="danger-btn" data-delete-entry="${escapeHtml(e.id)}">删除</button></div></div>`;
  }).join('') : `<div class="empty-state"><div class="empty-symbol"><svg viewBox="0 0 80 80" aria-hidden="true"><rect x="21" y="12" width="43" height="56" rx="9"/><path d="M28 12v56M37 29h17M37 40h17M37 51h11"/><path class="spark" d="m12 28 3-7 3 7 7 3-7 3-3 7-3-7-7-3Z"/></svg></div><h2>${sum.count ? '没有匹配的记录' : '这一天，还没有记账'}</h2><p>${sum.count ? '试试其他关键词或账户。' : '一顿午餐，一次出行，记录生活里的小小开销。'}</p><button class="text-btn" data-new-entry>＋ 记下第一笔</button></div>`;
}
function renderStats() {
  const month = $('stats-month').value;
  if (!/^\d{4}-\d{2}$/.test(month)) return;
  const list = state.entries.filter(e => e.date.slice(0,7) === month);
  const expenses = list.filter(e => e.kind === 'expense');
  const expense = expenses.reduce((s,e) => s + e.amount,0);
  const income = list.filter(e => e.kind === 'income').reduce((s,e) => s + e.amount,0);
  $('stats-summary').innerHTML = [['本月支出','¥ '+money(expense)],['本月收入','¥ '+money(income)],['收支记录',list.length+' 笔']].map(([label,value])=>`<div class="stats-metric"><span>${label}</span><strong>${value}</strong></div>`).join('');
  const [year, mon] = month.split('-').map(Number);
  const days = new Date(year, mon, 0).getDate();
  const values = Array.from({length:days}, (_,i) => expenses.filter(e => Number(e.date.slice(-2)) === i+1).reduce((s,e)=>s+e.amount,0));
  const max = Math.max(1,...values);
  $('daily-chart').innerHTML = values.map((n,i) => `<button class="chart-bar" style="--height:${n ? Math.max(3, n/max*100):1}%" title="${i+1} 日：¥ ${money(n)}" aria-label="${i+1} 日支出 ${money(n)} 元，查看账单" data-chart-date="${month}-${String(i+1).padStart(2,'0')}"></button>`).join('');
  const categoryTotals = Ledger.categories.map(c => [c,expenses.filter(e=>e.category === c).reduce((s,e)=>s+e.amount,0)]).filter(([,n])=>n).sort((a,b)=>b[1]-a[1]);
  $('category-chart').innerHTML = categoryTotals.length ? categoryTotals.map(([c,n])=>`<div class="category-row"><div class="category-label"><span>${c}</span><span>¥ ${money(n)} <small>· ${(n/expense*100).toFixed(1)}%</small></span></div><div class="category-track"><div class="category-fill" style="width:${n/expense*100}%"></div></div></div>`).join('') : '<div class="empty-state"><div class="empty-symbol">▥</div><p>本月还没有支出记录。</p></div>';
}
function render() {
  $('total-balance').innerHTML = '<span class="currency">¥</span>' + money(state.accounts.reduce((s,a)=>s+a.balance,0));
  $('account-count').textContent = `${state.accounts.length} 个账户的余额合计`;
  $('home-account-count').textContent = state.accounts.length;
  const day = Ledger.totals(state,today);
  $('today-expense').textContent = '¥ ' + money(day.expense);
  $('today-count').textContent = `今日已记录 ${day.count} 笔收支`;
  $('month-expense').textContent = '¥ ' + money(state.entries.filter(e=>e.kind === 'expense' && e.date.slice(0,7) === today.slice(0,7)).reduce((s,e)=>s+e.amount,0));
  $('month-caption').textContent = `${Number(today.slice(5,7))} 月累计支出`;
  $('account-cards').innerHTML = accountCards(false);
  $('manage-cards').innerHTML = accountCards(true);
  $('filter-account').innerHTML = options($('filter-account').value,true);
  renderDaily(); renderStats(); debtUI.render();
}
function openEntry(entryId) {
  if (!state.accounts.length) { toast('请先添加一个账户'); openAccount(); return; }
  $('entry-form').reset(); editEntryId = entryId || null;
  const e = state.entries.find(e => e.id === entryId);
  $('entry-title').textContent = e?.debtId ? '编辑还款记录' : (e ? '编辑记录' : '记一笔');
  $('entry-form').querySelector('[value=income]').disabled = Boolean(e?.debtId);
  $('entry-category').disabled = Boolean(e?.debtId);
  $('entry-account').innerHTML = options(e?.accountId,false);
  $('entry-category').innerHTML = Ledger.categories.map(c=>`<option>${c}</option>`).join('');
  $('entry-date').value = e?.date || $('selected-date').value || today;
  $('entry-amount').value = e ? (e.amount/100).toFixed(2) : '';
  $('entry-note').value = e?.note || '';
  if (e) { $('entry-category').value = e.category; $('entry-form').elements.kind.value = e.kind; }
  $('entry-error').textContent = ''; $('entry-dialog').showModal(); $('entry-amount').focus();
}
$('entry-form').onsubmit = async event => {
  event.preventDefault();
  try {
    const amount = Ledger.cents($('entry-amount').value);
    if (amount <= 0) throw new Error('金额需要大于 0');
    const next = Ledger.saveEntry(state,{ amount, kind:$('entry-form').elements.kind.value, accountId:$('entry-account').value, date:$('entry-date').value, category:$('entry-category').value, note:$('entry-note').value.trim() },editEntryId);
    const negative = next.accounts.find(a=>a.id === $('entry-account').value).balance < 0;
    await commit(next); $('entry-dialog').close(); toast(negative ? '记录已保存，该账户余额已为负数，请核对余额。' : '记录已保存，账户余额已更新');
  } catch(error) { $('entry-error').textContent = error.message; }
};
function openAccount(accountId) {
  editAccountId = accountId || null;
  const a = state.accounts.find(a => a.id === accountId);
  $('account-title').textContent = a ? '编辑账户' : '添加账户';
  $('account-name').value = a?.name || '';
  $('account-type').value = a?.type || '银行卡';
  $('account-balance').value = a ? (a.balance/100).toFixed(2) : '0.00';
  $('account-error').textContent = ''; $('account-dialog').showModal(); $('account-name').focus();
}
$('account-form').onsubmit = async event => {
  event.preventDefault();
  try {
    const name = $('account-name').value.trim();
    if (!name) throw new Error('请输入账户名称');
    if (state.accounts.some(a => a.name === name && a.id !== editAccountId)) throw new Error('已有同名账户，请使用不同名称');
    const raw = $('account-balance').value.trim();
    const balance = raw.startsWith('-') ? -Ledger.cents(raw.slice(1)) : Ledger.cents(raw);
    const a = { id: editAccountId || Ledger.id(), name, type:$('account-type').value, balance };
    const next = JSON.parse(JSON.stringify(state));
    if (editAccountId) next.accounts[next.accounts.findIndex(a=>a.id === editAccountId)] = a;
    else next.accounts.push(a);
    await commit(next); $('account-dialog').close(); toast('账户已保存');
  } catch(error) { $('account-error').textContent = error.message; }
};
function showView(view) {
  ['home','accounts','debts','stats'].forEach(v=>$(v+'-view').hidden = v !== view);
  document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view === view));
  const text = {home:['把生活，记得清楚','每一笔收支，都是生活的细节。'],accounts:['账户资产','让每一份余额，都清晰可见。'],debts:['还款安排','每一笔待还款，每一个重要日期。'],stats:['收支洞察','用清楚的记录，了解生活的节奏。']}[view];
  $('breadcrumb-view').textContent = {home:'总览',accounts:'账户管理',debts:'待还款',stats:'开销统计'}[view];
  $('page-title').textContent = text[0]; $('page-subtitle').textContent = text[1];
}
document.addEventListener('click',event=> {
  const target = event.target.closest('button'); if (!target) return;
  if (target.dataset.view) showView(target.dataset.view);
  else if (target.hasAttribute('data-new-account')) openAccount();
  else if (target.hasAttribute('data-new-entry')) openEntry();
  else if (target.dataset.editAccount) openAccount(target.dataset.editAccount);
  else if (target.dataset.editEntry) openEntry(target.dataset.editEntry);
  else if (target.dataset.deleteAccount) {
    const accountId = target.dataset.deleteAccount;
    const a = state.accounts.find(a=>a.id === accountId);
    if (state.entries.some(e=>e.accountId === accountId)) { toast('该账户有关联账单，请先处理账单后再删除。'); return; }
    confirmAction('删除账户',`删除「${a.name}」后，总余额将减少该账户的余额 ¥ ${money(a.balance)}。`,async ()=>{await commit({...state,accounts:state.accounts.filter(a=>a.id !== accountId)});toast('账户已删除');},'删除账户');
  } else if (target.dataset.deleteEntry) {
    const entryId = target.dataset.deleteEntry;
    confirmAction('删除这笔记录？',state.entries.find(e=>e.id === entryId)?.debtId ? '删除后，会恢复付款账户余额，并增加关联明细的剩余待还金额。' : '删除后，会撤销这笔收支对账户余额的影响。',async ()=>{await commit(Ledger.removeEntry(state,entryId));toast('记录已删除，余额已恢复');},'删除记录');
  } else if (target.dataset.chartDate) { $('selected-date').value = target.dataset.chartDate; renderDaily(); showView('home'); $('selected-date').scrollIntoView({block:'center'}); }
});
$('add-entry').onclick = () => openEntry();
$('add-account').onclick = $('accounts-add').onclick = () => openAccount();
$('manage-link').onclick = () => showView('accounts');
$('selected-date').value = today; $('stats-month').value = today.slice(0,7);
$('selected-date').onchange = () => { if (!$('selected-date').value) $('selected-date').value = today; renderDaily(); };
$('stats-month').onchange = () => { if (!$('stats-month').value) $('stats-month').value = today.slice(0,7); renderStats(); };
$('search').oninput = renderDaily; $('filter-account').onchange = renderDaily;
function moveDay(delta) { const date = new Date($('selected-date').value+'T12:00:00'); date.setDate(date.getDate()+delta); $('selected-date').value = localDate(date); renderDaily(); }
$('prev-day').onclick = () => moveDay(-1); $('next-day').onclick = () => moveDay(1);
$('go-today').onclick = () => { $('selected-date').value = today; renderDaily(); };
async function download(content, filename) {
  await storage.export(content, filename);
}
$('export-btn').onclick = async () => {
  if (storageBlocked) {
    try { const raw = await storage.read(); if (raw) { await download(raw,`zz记-原始账本-${today}.json`,'application/json'); toast('已导出原始账本，请妥善保管'); return; } } catch(error) { toast(error.message); return; }
  }
  try { await download(JSON.stringify(state,null,2),`zz记-账本备份-${today}.json`,'application/json'); toast('备份已保存到软件文件夹中的「导出」目录'); }
  catch(error) { toast(error.message); }
};
$('import-btn').onclick = () => $('import-file').click();
$('import-file').onchange = async event => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (file.size > 10*1024*1024) throw new Error('备份文件过大，最大支持 10 MB');
    const next = Ledger.validate(JSON.parse(await file.text()));
    confirmAction('导入账本',`将用备份中的 ${next.accounts.length} 个账户、${next.entries.length} 笔记录、${(next.debts || []).length} 笔待还款替换当前账本。请先导出当前账本以备恢复。`,async ()=> {
      await commit(next, true); toast('账本已导入');
    },'替换并导入');
  } catch(error) { toast(error instanceof SyntaxError ? '文件不是有效的 JSON 账本' : error.message); }
  event.target.value = '';
};
$('csv-btn').onclick = async () => {
  const list = selectedEntries();
  if (!list.length) { toast('当前日期与筛选条件下没有可导出的记录'); return; }
  const cell = v => { const s = String(v); return '"' + (/^[=+\-@\t\r]/.test(s) ? "'"+s : s).replace(/"/g,'""') + '"'; };
  const rows = [['日期','类型','账户','分类','金额（元）','备注'],...list.map(e=>[e.date,e.kind === 'expense' ? '支出':'收入',state.accounts.find(a=>a.id === e.accountId).name,e.category,(e.amount/100).toFixed(2),e.note])];
  try { await download('\uFEFF'+rows.map(row=>row.map(cell).join(',')).join('\r\n'),`zz记-每日明细-${$('selected-date').value}.csv`,'text/csv;charset=utf-8'); toast('每日明细已保存到软件文件夹中的「导出」目录'); }
  catch(error) { toast(error.message); }
};
$('today-label').textContent = new Date().toLocaleDateString('zh-CN',{year:'numeric',month:'long',day:'numeric',weekday:'long'});
render();
{
  $('save-status').textContent = storageBlocked ? '账本读取失败' : '已保存到本地';
  const footer = document.querySelector('footer span');
  footer.textContent = '账本保存在软件文件夹的「账本.json」· 导出文件在「导出」目录';
  footer.title = window.desktopConfig.directory;
  // 首次运行即创建文件，之后每次保存都有原子替换与上一版备份。
  if (!storageBlocked) {
    try { if (!saved) await commit(state); }
    catch(error) { storageBlocked = true; toast(error.message); }
  }
}
if (storageBlocked) confirmAction('本地账本读取失败','已有文件没有被覆盖。请检查软件文件夹的读写权限；如账本损坏，请先导出原始文件，再导入「账本.上一版.json」或其他有效备份恢复。',()=>{},'我知道了');

})();
window.zzApp.ready.catch(error => {
  console.error(error);
  const status = document.getElementById('save-status');
  if (status) status.textContent = '启动失败，请重新打开软件';
});
