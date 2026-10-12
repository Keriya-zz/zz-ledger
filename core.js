(function (root, factory) {
  const api = factory();
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Ledger = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  const categories = ['餐饮', '交通', '购物', '生活', '娱乐', '医疗', '其他'];
  const id = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  function cents(value) {
    const s = String(value).trim();
    if (!/^\d+(\.\d{1,2})?$/.test(s)) throw new Error('请输入有效金额，最多两位小数');
    const [a, b = ''] = s.split('.');
    const n = Number(a) * 100 + Number(b.padEnd(2, '0'));
    if (!Number.isSafeInteger(n) || n > 999999999999) throw new Error('金额过大');
    return n;
  }
  function initial() {
    return { version: 1, accounts: [
      { id: id(), name: '微信', type: '微信', balance: 0 },
      { id: id(), name: '支付宝', type: '支付宝', balance: 0 },
      { id: id(), name: '银行卡', type: '银行卡', balance: 0 }
    ], entries: [] };
  }
  function validDate(s) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
    const d = new Date(s + 'T12:00:00Z');
    return Number.isFinite(d.getTime()) && d.toISOString().slice(0, 10) === s;
  }
  function validate(data) {
    if (!data || data.version !== 1 || !Array.isArray(data.accounts) || !Array.isArray(data.entries)) throw new Error('账本格式不正确');
    const ids = new Set();
    for (const a of data.accounts) {
      if (!a || typeof a.id !== 'string' || !a.id || ids.has(a.id) || typeof a.name !== 'string' || !a.name.trim() || a.name.length > 30 || !['微信','支付宝','银行卡','现金','其他'].includes(a.type) || !Number.isSafeInteger(a.balance) || Math.abs(a.balance) > 999999999999) throw new Error('账户数据无效');
      ids.add(a.id);
    }
    const entryIds = new Set();
    for (const e of data.entries) {
      if (!e || typeof e.id !== 'string' || !e.id || entryIds.has(e.id) || !ids.has(e.accountId) || !['expense','income'].includes(e.kind) || !Number.isSafeInteger(e.amount) || e.amount <= 0 || e.amount > 999999999999 || !validDate(e.date) || !categories.includes(e.category) || typeof e.note !== 'string' || e.note.length > 200) throw new Error('收支记录无效');
      entryIds.add(e.id);
    }
    return data;
  }
  function saveEntry(data, input, editId) {
    const next = JSON.parse(JSON.stringify(data));
    if (editId) {
      const old = next.entries.find(e => e.id === editId);
      if (!old) throw new Error('记录不存在');
      next.accounts.find(a => a.id === old.accountId).balance -= old.kind === 'expense' ? -old.amount : old.amount;
      next.entries = next.entries.filter(e => e.id !== editId);
    }
    const entry = { id: editId || id(), ...input };
    const account = next.accounts.find(a => a.id === entry.accountId);
    if (!account) throw new Error('请选择有效账户');
    account.balance += entry.kind === 'expense' ? -entry.amount : entry.amount;
    next.entries.unshift(entry);
    return validate(next);
  }
  function removeEntry(data, entryId) {
    const next = JSON.parse(JSON.stringify(data));
    const entry = next.entries.find(e => e.id === entryId);
    if (!entry) throw new Error('记录不存在');
    next.accounts.find(a => a.id === entry.accountId).balance -= entry.kind === 'expense' ? -entry.amount : entry.amount;
    next.entries = next.entries.filter(e => e.id !== entryId);
    return validate(next);
  }
  function totals(data, date) {
    const list = data.entries.filter(e => e.date === date);
    return { expense: list.filter(e => e.kind === 'expense').reduce((n,e) => n + e.amount, 0), income: list.filter(e => e.kind === 'income').reduce((n,e) => n + e.amount, 0), count: list.length };
  }
  return { categories, id, cents, initial, validate, saveEntry, removeEntry, totals, validDate };
});
