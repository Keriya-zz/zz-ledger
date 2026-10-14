const assert = require('node:assert/strict');
const L = require('../ui/core.js');
const initial = L.initial();
const input = {amount:500,kind:'expense',accountId:initial.accounts[0].id,date:'2026-10-14',category:'  学习  ',note:''};
const original = JSON.stringify(initial);
let state = L.saveEntry(initial,input);
assert.equal(JSON.stringify(initial),original,'添加分类不能修改原账本');
assert.equal(state.entries[0].category,'学习');
assert.deepEqual(state.customCategories,['学习']);
state = L.saveEntry(state,{...input,category:'学习'});
assert.deepEqual(state.customCategories,['学习'],'重复使用分类不产生重复项');
for (const entry of [...state.entries]) state = L.removeEntry(state,entry.id);
assert.ok(L.categoryOptions(state).includes('学习'),'删除最后一笔账单后分类仍可复用');
assert.deepEqual(L.validate(JSON.parse(JSON.stringify(state))),state,'备份保留分类');
const legacyCustom = L.initial();
legacyCustom.entries.push({...input,id:'legacy-custom',accountId:legacyCustom.accounts[0].id,category:'宠物'});
assert.ok(L.categoryOptions(L.validate(legacyCustom)).includes('宠物'),'可从历史账单恢复自定义选项');
for (const category of ['', '  ', 'x'.repeat(21), '坏\n名称', null]) {
  assert.throws(()=>L.saveEntry(initial,{...input,category}));
}
for (const customCategories of [null, {}, ['学习','学习'], [''], [' x '], [20]]) {
  assert.throws(()=>L.validate({...initial,customCategories}));
}
const debtState = L.saveDebt(initial,{name:'借款',creditor:'朋友',amount:1000,dueDate:'',note:''});
const repaid = L.repayDebt(debtState,debtState.debts[0].id,{amount:500,accountId:initial.accounts[0].id,date:'2026-10-14',note:''});
assert.throws(()=>L.saveEntry(repaid,{...input,category:'学习'},repaid.entries[0].id),'关联还款不能改成自定义分类');
console.log('PASS: 自定义分类、去重、删除后复用、备份兼容、名称校验及还款关联保护。');
