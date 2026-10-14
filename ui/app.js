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
    if (!management) return `<article class="account-row"><div class="account-row-name"><span class="account-icon ${color}">${Icons.account(a.type)}</span><h3>${escapeHtml(a.name)}</h3></div><span class="account-row-type">${escapeHtml(a.type)} · 可用余额</span><span class="account-row-value ${a.balance < 0 ? 'negative' : ''}"><small>¥</small>${money(a.balance)}</span><button class="account-row-edit" data-edit-account="${escapeHtml(a.id)}" aria-label="编辑${escapeHtml(a.name)}账户" title="编辑账户">›</button></article>`;
    return `<article class="account-card"><div class="account-top"><span class="account-icon ${color}">${Icons.account(a.type)}</span><div class="account-info"><h3>${escapeHtml(a.name)}</h3><small>${a.type} · 可用余额</small></div>${management ? '' : `<button class="account-edit" data-edit-account="${escapeHtml(a.id)}">编辑</button>`}</div><div class="account-value ${a.balance < 0 ? 'negative':''}"><small>¥</small>${money(a.balance)}</div>${management ? `<div class="account-actions"><button class="text-btn" data-account-history="${escapeHtml(a.id)}" data-history-all>交易明细</button><button class="text-btn" data-edit-account="${escapeHtml(a.id)}">编辑账户</button><button class="danger-btn" data-delete-account="${escapeHtml(a.id)}">删除</button></div>` : ''}</article>`;
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
    return `<div class="entry-row"><span class="entry-icon">${e.kind === 'income' ? Icons.draw('arrow') : Icons.category(e.category)}</span><div class="entry-content"><strong>${escapeHtml(e.note || (e.kind === 'income' ? '收入' : e.category))}</strong><small>${escapeHtml(a.name)} · ${escapeHtml(e.category)} · ${e.kind === 'income' ? '收入':'支出'}</small></div><span class="entry-money ${e.kind === 'income' ? 'income':''}">${e.kind === 'income' ? '+' : '−'} ¥ ${money(e.amount)}</span><div class="entry-actions"><button data-edit-entry="${escapeHtml(e.id)}">编辑</button><button class="danger-btn" data-delete-entry="${escapeHtml(e.id)}">删除</button></div></div>`;
  }).join('') : `<div class="empty-state"><div class="empty-symbol"><svg viewBox="0 0 80 80" aria-hidden="true"><rect x="21" y="12" width="43" height="56" rx="9"/><path d="M28 12v56M37 29h17M37 40h17M37 51h11"/><path class="spark" d="m12 28 3-7 3 7 7 3-7 3-3 7-3-7-7-3Z"/></svg></div><h2>${sum.count ? '没有匹配的记录' : '这一天，还没有记账'}</h2><p>${sum.count ? '试试其他关键词或账户。' : '一顿午餐，一次出行，记录生活里的小小开销。'}</p><button class="text-btn" data-new-entry>＋ 记下第一笔</button></div>`;
}
let editTransferId = null;
const transferAccountName = id => state.accounts.find(a=>a.id===id)?.name || '未知账户';
function transferRow(t, accountId) {
  const incoming = accountId === t.toAccountId;
  const direction = accountId ? (incoming ? '转入' : '转出') : '划转';
  return `<div class="entry-row"><span class="entry-icon">${Icons.draw('arrow')}</span><div class="entry-content"><strong>${escapeHtml(transferAccountName(t.fromAccountId))} → ${escapeHtml(transferAccountName(t.toAccountId))}</strong><small>${escapeHtml(t.date)} · ${direction}${t.note ? ' · '+escapeHtml(t.note) : ''}</small></div><span class="entry-money">${accountId ? (incoming ? '+' : '−')+' ' : ''}¥ ${money(t.amount)}</span><div class="entry-actions"><button data-edit-transfer="${escapeHtml(t.id)}">编辑</button><button class="danger-btn" data-delete-transfer="${escapeHtml(t.id)}">删除</button></div></div>`;
}
function renderTransfers() {
  const list = (state.transfers || []).filter(t=>t.date.slice(0,7)===$('transfer-month').value).sort((a,b)=>b.date.localeCompare(a.date));
  $('transfer-list').innerHTML = list.length ? list.map(t=>transferRow(t)).join('') : '<div class="empty-state"><p>所选月份暂无账户划转记录。</p><button class="text-btn" data-new-transfer>＋ 记录划转</button></div>';
}
function transferBalances() {
  $('transfer-balances').textContent = ['from','to'].map((side,i)=> {
    const account=state.accounts.find(a=>a.id===$('transfer-'+side).value);
    return account ? `${i ? '转入' : '转出'}账户当前余额 ¥ ${money(account.balance)}` : '';
  }).join(' · ');
}
function openTransfer(transferId) {
  if (state.accounts.length < 2) { toast('请先添加至少两个账户，再进行划转'); return; }
  const transfer = (state.transfers || []).find(t=>t.id===transferId);
  editTransferId = transfer?.id || null;
  $('transfer-form').reset();
  $('transfer-title').textContent = transfer ? '编辑账户划转' : '账户划转';
  $('transfer-from').innerHTML = options(transfer?.fromAccountId || state.accounts[0].id);
  $('transfer-to').innerHTML = options(transfer?.toAccountId || state.accounts[1].id);
  $('transfer-date').value = transfer?.date || today;
  $('transfer-amount').value = transfer ? (transfer.amount/100).toFixed(2) : '';
  $('transfer-note').value = transfer?.note || '';
  $('transfer-error').textContent = '';
  transferBalances();
  $('transfer-dialog').showModal();
  $('transfer-amount').focus();
}
$('transfer-from').onchange = transferBalances;
$('transfer-to').onchange = transferBalances;
$('transfer-form').onsubmit = async event => {
  event.preventDefault();
  if (saving) return;
  try {
    const input = {fromAccountId:$('transfer-from').value,toAccountId:$('transfer-to').value,amount:Ledger.cents($('transfer-amount').value),date:$('transfer-date').value,note:$('transfer-note').value.trim()};
    if (input.amount <= 0) throw new Error('划转金额必须大于零');
    if (input.fromAccountId === input.toAccountId) throw new Error('转出和转入账户不能相同');
    const next = Ledger.saveTransfer(state,input,editTransferId);
    const negative = next.accounts.find(a=>a.id===input.fromAccountId).balance < 0;
    await commit(next);
    $('transfer-month').value = input.date.slice(0,7); renderTransfers();
    $('transfer-dialog').close();
    toast(negative ? '划转已保存，转出账户余额为负数，请核对余额' : '划转已保存，双方余额已更新');
  } catch(error) { $('transfer-error').textContent = error.message; }
};
$('transfer-month').value = today.slice(0,7);
$('transfer-month').onchange = () => { if (!$('transfer-month').value) $('transfer-month').value=today.slice(0,7); renderTransfers(); };
let historyAccountId = null;
function renderAccountHistory() {
  const account = state.accounts.find(a => a.id === historyAccountId);
  if (!account) return;
  const month = $('account-history-month').value;
  const kind = $('account-history-kind').value;
  const list = [...state.entries, ...(state.transfers || []).map(t=>({...t,kind:'transfer'}))].filter(e => (e.kind === 'transfer' ? e.fromAccountId === account.id || e.toAccountId === account.id : e.accountId === account.id) && e.date.slice(0,7) === month && (kind === 'all' || e.kind === kind)).sort((a,b) => b.date.localeCompare(a.date));
  $('account-history-title').textContent = account.name + ' · 交易明细';
  const expense = list.filter(e=>e.kind === 'expense').reduce((sum,e)=>sum+e.amount,0);
  const income = list.filter(e=>e.kind === 'income').reduce((sum,e)=>sum+e.amount,0);
  $('account-history-summary').textContent = `${month} · ${list.length} 笔 · 支出 ¥ ${money(expense)} · 收入 ¥ ${money(income)} · 划转 ${list.filter(e=>e.kind==='transfer').length} 笔`;
  $('account-history-list').innerHTML = list.length ? list.map(e=>e.kind === 'transfer' ? transferRow(e,account.id) : `<div class="entry-row"><div class="entry-content"><strong>${escapeHtml(e.note || e.category)}</strong><small>${escapeHtml(e.date)} · ${escapeHtml(e.category)} · ${e.kind === 'income' ? '收入' : '支出'}</small></div><span class="entry-money ${e.kind === 'income' ? 'income' : ''}">${e.kind === 'income' ? '+' : '−'} ¥ ${money(e.amount)}</span></div>`).join('') : '<div class="empty-state"><p>该账户在所选月份没有符合条件的交易。</p></div>';
}
function openAccountHistory(accountId, all) {
  historyAccountId = accountId;
  $('account-history-month').value = all ? today.slice(0,7) : $('stats-month').value;
  $('account-history-kind').value = all ? 'all' : 'expense';
  renderAccountHistory();
  $('account-history-dialog').showModal();
}
$('account-history-month').onchange = () => {
  if (!$('account-history-month').value) $('account-history-month').value = today.slice(0,7);
  renderAccountHistory();
};
$('account-history-kind').onchange = renderAccountHistory;
function renderStats() {
  const month = $('stats-month').value;
  if (!/^\d{4}-\d{2}$/.test(month)) return;
  const list = state.entries.filter(e => e.date.slice(0,7) === month);
  const expenses = list.filter(e => e.kind === 'expense');
  const expense = expenses.reduce((s,e) => s + e.amount,0);
  const income = list.filter(e => e.kind === 'income').reduce((s,e) => s + e.amount,0);
  $('stats-summary').innerHTML = [['本月支出','¥ '+money(expense)],['本月收入','¥ '+money(income)],['收支记录',list.length+' 笔']].map(([label,value])=>`<div class="stats-metric"><span>${label}</span><strong>${value}</strong></div>`).join('');
  const accountExpenses = Ledger.accountExpenses(state, month);
  $('account-expenses').innerHTML = accountExpenses.length ? `<table class="account-expenses-table"><thead><tr><th scope="col">账户</th><th scope="col">支出金额</th><th scope="col">支出笔数</th><th scope="col">支出占比</th></tr></thead><tbody>${accountExpenses.map(a => `<tr data-expense-account="${escapeHtml(a.id)}"><th scope="row"><button class="account-expenses-name text-btn" data-account-history="${escapeHtml(a.id)}" aria-label="查看${escapeHtml(a.name)}交易明细">${escapeHtml(a.name)} ↗</button><small>${escapeHtml(a.type)}</small></th><td class="account-expenses-amount">¥ ${money(a.amount)}</td><td>${a.count} 笔</td><td>${a.share.toFixed(1)}%<div class="category-track" aria-hidden="true"><div class="category-fill" style="width:${a.share}%"></div></div></td></tr>`).join('')}</tbody></table>` : '<div class="empty-state"><p>还没有账户，添加账户并记账后即可查看支出统计。</p><button class="text-btn" data-new-account>＋ 添加账户</button></div>';
  const [year, mon] = month.split('-').map(Number);
  const days = new Date(year, mon, 0).getDate();
  const values = Array.from({length:days}, (_,i) => expenses.filter(e => Number(e.date.slice(-2)) === i+1).reduce((s,e)=>s+e.amount,0));
  const max = Math.max(1,...values);
  $('daily-chart').innerHTML = values.map((n,i) => `<button class="chart-bar" style="--height:${n ? Math.max(3, n/max*100):1}%" title="${i+1} 日：¥ ${money(n)}" aria-label="${i+1} 日支出 ${money(n)} 元，查看账单" data-chart-date="${month}-${String(i+1).padStart(2,'0')}"></button>`).join('');
  const categoryTotals = Ledger.categoryOptions(state).map(c => [c,expenses.filter(e=>e.category === c).reduce((s,e)=>s+e.amount,0)]).filter(([,n])=>n).sort((a,b)=>b[1]-a[1]);
  $('category-chart').innerHTML = categoryTotals.length ? categoryTotals.map(([c,n])=>`<div class="category-row"><div class="category-label"><span>${escapeHtml(c)}</span><span>¥ ${money(n)} <small>· ${(n/expense*100).toFixed(1)}%</small></span></div><div class="category-track"><div class="category-fill" style="width:${n/expense*100}%"></div></div></div>`).join('') : '<div class="empty-state"><div class="empty-symbol">▥</div><p>本月还没有支出记录。</p></div>';
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
  renderDaily(); renderStats(); debtUI.render(); renderTransfers();
  if ($('account-history-dialog').open) renderAccountHistory();
}
function openEntry(entryId) {
  if (!state.accounts.length) { toast('请先添加一个账户'); openAccount(); return; }
  $('entry-form').reset(); editEntryId = entryId || null;
  const e = state.entries.find(e => e.id === entryId);
  $('entry-title').textContent = e?.debtId ? '编辑还款记录' : (e ? '编辑记录' : '记一笔');
  $('entry-form').querySelector('[value=income]').disabled = Boolean(e?.debtId);
  $('entry-category').disabled = Boolean(e?.debtId);
  $('entry-account').innerHTML = options(e?.accountId,false);
  $('entry-category').innerHTML = Ledger.categoryOptions(state).map(c=>`<option value="${escapeHtml(c)}">${escapeHtml(c)}</option>`).join('') + '<option value="">＋ 自定义分类…</option>';
  $('entry-date').value = e?.date || $('selected-date').value || today;
  $('entry-amount').value = e ? (e.amount/100).toFixed(2) : '';
  $('entry-note').value = e?.note || '';
  if (e) { $('entry-category').value = e.category; $('entry-form').elements.kind.value = e.kind; }
  updateCustomCategory();
  $('entry-error').textContent = ''; $('entry-dialog').showModal(); $('entry-amount').focus();
}
function updateCustomCategory() {
  const custom = !$('entry-category').disabled && $('entry-category').value === '';
  $('custom-category-field').hidden = !custom;
  $('entry-custom-category').disabled = !custom;
  $('entry-custom-category').required = custom;
}
$('entry-category').onchange = () => {
  updateCustomCategory();
  if (!$('custom-category-field').hidden) $('entry-custom-category').focus();
};
$('entry-form').onsubmit = async event => {
  event.preventDefault();
  try {
    const amount = Ledger.cents($('entry-amount').value);
    if (amount <= 0) throw new Error('金额需要大于 0');
    const category = $('entry-category').value || $('entry-custom-category').value.trim();
    const next = Ledger.saveEntry(state,{ amount, kind:$('entry-form').elements.kind.value, accountId:$('entry-account').value, date:$('entry-date').value, category, note:$('entry-note').value.trim() },editEntryId);
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
  const text = {home:['账本总览','每一笔收支，都是生活的细节。'],accounts:['账户资产','让每一份余额，都清晰可见。'],debts:['还款安排','每一笔待还款，每一个重要日期。'],stats:['收支洞察','用清楚的记录，了解生活的节奏。']}[view];
  $('breadcrumb-view').textContent = {home:'总览',accounts:'账户管理',debts:'待还款',stats:'开销统计'}[view];
  $('page-title').textContent = text[0]; $('page-subtitle').textContent = text[1];
}
document.addEventListener('click',event=> {
  const target = event.target.closest('button'); if (!target) return;
  if (target.dataset.view) showView(target.dataset.view);
  else if (target.hasAttribute('data-new-account')) openAccount();
  else if (target.hasAttribute('data-new-transfer')) openTransfer();
  else if (target.dataset.editTransfer) openTransfer(target.dataset.editTransfer);
  else if (target.dataset.deleteTransfer) {
    const transferId = target.dataset.deleteTransfer;
    confirmAction('删除这笔划转？','删除后，转出账户将加回金额，转入账户将扣回金额，总余额保持不变。',async ()=>{ await commit(Ledger.removeTransfer(state,transferId)); toast('划转已删除，双方余额已恢复'); },'删除划转');
  }
  else if (target.hasAttribute('data-new-entry')) openEntry();
  else if (target.dataset.accountHistory) openAccountHistory(target.dataset.accountHistory, target.hasAttribute('data-history-all'));
  else if (target.dataset.editAccount) openAccount(target.dataset.editAccount);
  else if (target.dataset.editEntry) openEntry(target.dataset.editEntry);
  else if (target.dataset.deleteAccount) {
    const accountId = target.dataset.deleteAccount;
    const a = state.accounts.find(a=>a.id === accountId);
    if (state.entries.some(e=>e.accountId === accountId) || (state.transfers || []).some(t=>t.fromAccountId === accountId || t.toAccountId === accountId)) { toast('该账户有关联账单或划转，请先处理记录后再删除。'); return; }
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
    confirmAction('导入账本',`将用备份中的 ${next.accounts.length} 个账户、${next.entries.length} 笔收支、${(next.transfers || []).length} 笔划转、${(next.debts || []).length} 笔待还款替换当前账本。请先导出当前账本以备恢复。`,async ()=> {
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
