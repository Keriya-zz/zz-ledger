'use strict';
// 待还款页面单独管理展示与表单，金额与关联账单规则位于 core.js。
window.createDebtUI = function ({getState, commit, money, today, toast, confirmAction, options, openAccount, escapeHtml}) {
  const $ = id => document.getElementById(id);
  let editId = null, repayId = null;
  const details = () => Ledger.debtDetails(getState());
  function status(d) {
    if (!d.remaining) return ['settled','已还清'];
    if (d.dueDate && d.dueDate < today) return ['overdue','已逾期'];
    if (d.dueDate === today) return ['today','今日到期'];
    if (!d.dueDate) return ['pending','未设日期'];
    return ['pending','待还款'];
  }
  function render() {
    const all = details();
    const pending = all.filter(d=>d.remaining > 0);
    const sum = pending.reduce((n,d)=>n+d.remaining,0);
    const overdue = pending.filter(d=>d.dueDate && d.dueDate < today);
    const monthly = pending.filter(d=>d.dueDate.slice(0,7) === today.slice(0,7));
    $('home-debt-total').textContent = '¥ ' + money(sum);
    $('home-debt-count').textContent = `${pending.length} 笔待还${overdue.length ? ' · '+overdue.length+' 笔逾期' : ''}`;
    $('debt-nav-count').textContent = pending.length;
    $('debt-summary').innerHTML = [['待还总额','¥ '+money(sum),`${pending.length} 笔未还清`],['本月应还','¥ '+money(monthly.reduce((n,d)=>n+d.remaining,0)),'按设定还款日期统计'],['已逾期待还','¥ '+money(overdue.reduce((n,d)=>n+d.remaining,0)),`${overdue.length} 笔超过还款日期`]].map(([label,value,note])=>`<article class="stats-metric"><span>${label}</span><strong>${value}</strong><small>${note}</small></article>`).join('');
    const filter = $('debt-filter').value;
    const query = $('debt-search').value.trim().toLowerCase();
    const list = all.filter(d=>(filter === 'all' || (filter === 'pending' && d.remaining > 0) || (filter === 'settled' && d.remaining === 0) || (filter === 'overdue' && d.remaining > 0 && d.dueDate && d.dueDate < today)) && (!query || `${d.name} ${d.creditor} ${d.note}`.toLowerCase().includes(query))).sort((a,b)=>(a.remaining === 0)-(b.remaining === 0) || (a.dueDate || '9999-12-31').localeCompare(b.dueDate || '9999-12-31'));
    $('debt-list-count').textContent = `${list.length} 笔明细`;
    $('debt-list').innerHTML = list.length ? list.map(d=> {
      const [kind,label] = status(d);
      const percentage = Math.min(100,d.paid/d.amount*100);
      return `<article class="debt-card"><div class="debt-card-top"><div class="debt-identity"><span class="debt-symbol">${Icons.draw('repayment')}</span><div><h3>${escapeHtml(d.name)}</h3><p>${escapeHtml(d.creditor || '未填写还款对象')}</p></div></div><span class="debt-badge ${kind}">${label}</span></div><div class="debt-amount"><small>剩余待还</small><strong>¥ ${money(d.remaining)}</strong></div><div class="debt-progress"><span style="width:${percentage}%"></span></div><div class="debt-numbers"><span>已还 ¥ ${money(d.paid)}</span><span>应还总额 ¥ ${money(d.amount)}</span></div><div class="debt-due"><span>还款日期</span><b>${d.dueDate || '未设置'}</b></div>${d.note ? `<p class="debt-note">${escapeHtml(d.note)}</p>` : ''}<div class="debt-actions">${d.remaining ? `<button class="primary-btn" data-repay-debt="${escapeHtml(d.id)}">记录还款</button>` : '<span class="debt-settled">✓ 已全部还清</span>'}<button class="text-btn" data-history-debt="${escapeHtml(d.id)}">还款记录</button><button class="text-btn" data-edit-debt="${escapeHtml(d.id)}">编辑</button><button class="danger-btn" data-delete-debt="${escapeHtml(d.id)}">删除</button></div></article>`;
    }).join('') : `<div class="empty-state debt-empty"><div class="empty-symbol">◇</div><h2>${all.length ? '没有符合条件的待还款' : '暂无待还款'}</h2>${all.length ? '<p>请调整筛选条件。</p>' : ''}<button class="text-btn" data-new-debt>＋ 添加待还款</button></div>`;
  }
  function openDebt(id) {
    editId = id || null;
    const d = details().find(d=>d.id === id);
    $('debt-title').textContent = d ? '编辑待还款' : '添加待还款';
    $('debt-name').value = d?.name || '';
    $('debt-creditor').value = d?.creditor || '';
    $('debt-amount').value = d ? (d.amount/100).toFixed(2) : '';
    $('debt-due').value = d?.dueDate || '';
    $('debt-note').value = d?.note || '';
    $('debt-error').textContent = '';
    $('debt-dialog').showModal(); $('debt-name').focus();
  }
  function openRepayment(id) {
    if (!getState().accounts.length) { toast('请先添加一个付款账户'); openAccount(); return; }
    const d = details().find(d=>d.id === id);
    if (!d?.remaining) { toast('这笔待还款已经还清'); return; }
    repayId = id;
    $('repay-description').textContent = `${d.name} · 剩余 ¥ ${money(d.remaining)}`;
    $('repay-account').innerHTML = options(null,false);
    $('repay-amount').value = (d.remaining/100).toFixed(2);
    $('repay-date').value = today;
    $('repay-note').value = '';
    $('repay-error').textContent = '';
    $('repay-dialog').showModal(); $('repay-amount').focus();
  }
  function history(id) {
    const d = details().find(d=>d.id === id);
    $('debt-history-title').textContent = d.name+' · 还款记录';
    const state = getState();
    const entries = state.entries.filter(e=>e.debtId === id).sort((a,b)=>b.date.localeCompare(a.date));
    $('debt-history-list').innerHTML = entries.length ? entries.map(e=>`<div class="entry-row"><div class="entry-content"><strong>¥ ${money(e.amount)}</strong><small>${e.date} · ${escapeHtml(state.accounts.find(a=>a.id === e.accountId).name)}</small><p class="hint">${escapeHtml(e.note)}</p></div><button class="text-btn" data-edit-entry="${escapeHtml(e.id)}">编辑账单</button><button class="danger-btn" data-delete-entry="${escapeHtml(e.id)}">撤销还款</button></div>`).join('') : '<div class="empty-state"><p>还没有实际还款记录。</p></div>';
    $('debt-history-dialog').showModal();
  }
  $('debt-form').onsubmit = async event => {
    event.preventDefault();
    try {
      const next = Ledger.saveDebt(getState(),{name:$('debt-name').value.trim(),creditor:$('debt-creditor').value.trim(),amount:Ledger.cents($('debt-amount').value),dueDate:$('debt-due').value,note:$('debt-note').value.trim()},editId);
      await commit(next); $('debt-dialog').close(); toast('待还款已保存');
    } catch(error) { $('debt-error').textContent = error.message; }
  };
  $('repay-form').onsubmit = async event => {
    event.preventDefault();
    try {
      const next = Ledger.repayDebt(getState(),repayId,{amount:Ledger.cents($('repay-amount').value),accountId:$('repay-account').value,date:$('repay-date').value,note:$('repay-note').value.trim()});
      const negative = next.accounts.find(a=>a.id === $('repay-account').value).balance < 0;
      await commit(next); $('repay-dialog').close(); toast(negative ? '还款已记录，付款账户余额为负，请核对。' : '还款已记录，待还金额与账户余额已更新');
    } catch(error) { $('repay-error').textContent = error.message; }
  };
  document.addEventListener('click',event=> {
    const target = event.target.closest('button'); if (!target) return;
    if (target.hasAttribute('data-new-debt')) openDebt();
    else if (target.dataset.editDebt) openDebt(target.dataset.editDebt);
    else if (target.dataset.repayDebt) openRepayment(target.dataset.repayDebt);
    else if (target.dataset.historyDebt) history(target.dataset.historyDebt);
    else if (target.dataset.deleteDebt) {
      const id = target.dataset.deleteDebt;
      if (getState().entries.some(e=>e.debtId === id)) { toast('这笔明细已有还款记录，请先处理关联账单后再删除。'); return; }
      confirmAction('删除待还款？','仅删除这笔待还款安排，不会改变账户余额。',async ()=>{await commit(Ledger.removeDebt(getState(),id));toast('待还款已删除');},'删除明细');
    } else if (target.dataset.editEntry || target.dataset.deleteEntry) $('debt-history-dialog').close();
  });
  $('debt-search').oninput = render;
  $('debt-filter').onchange = render;
  return {render};
};
