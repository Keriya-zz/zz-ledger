'use strict';
const mobile$=id=>document.getElementById(id);
document.querySelector('main').append(mobile$('add-entry'));
const sidebarBottom=document.querySelector('.sidebar-bottom');
mobile$('backup-actions').append(sidebarBottom);
mobile$('mobile-backup').onclick=()=>mobile$('backup-dialog').showModal();
const labels={home:'总览',accounts:'账户',debts:'待还款',stats:'统计'};
document.querySelectorAll('nav [data-view]').forEach(button=> {
  const icon=button.querySelector('span');
  const badge=button.querySelector('b');
  button.replaceChildren(icon,document.createTextNode(labels[button.dataset.view]));
  if (badge) button.append(badge);
  button.setAttribute('aria-label',labels[button.dataset.view]);
});
const teaser=document.querySelector('.debt-teaser');
document.querySelector('.balance-pane').insertBefore(teaser,document.querySelector('.ledger-panel'));
window.zzMobileBack=()=> {
  if (window.zzApp?.isSaving()) return;
  const dialogs=[...document.querySelectorAll('dialog[open]')];
  if (dialogs.length) { dialogs[dialogs.length-1].close(); return; }
  if (mobile$('home-view').hidden) { document.querySelector('nav [data-view=home]').click(); return; }
  window.ZZNative?.finishApp();
};
document.addEventListener('click',event=> {
  const nav=event.target.closest('nav [data-view]');
  if (nav) document.querySelector('main').scrollTo({top:0});
});
// The same category select remains the source of truth for custom categories.
const grid=document.createElement('div');grid.className='mobile-category-grid';grid.setAttribute('aria-label','常用分类');
const category=mobile$('entry-category');category.closest('label').append(grid);
function categoryButtons() {
  grid.replaceChildren();
  [...category.options].filter(o=>o.value!== '还款').slice(0,7).concat([{value:'',textContent:'自定义'}]).forEach(option=>{
    const button=document.createElement('button');button.type='button';
    button.innerHTML=Icons.category(option.value);const caption=document.createElement('span');caption.textContent=option.textContent;button.append(caption);
    button.classList.toggle('selected',option.value===category.value);
    button.disabled=category.disabled;
    button.onclick=()=>{category.value=option.value;category.onchange();categoryButtons();};grid.append(button);
  });
}
new MutationObserver(()=> { if (mobile$('entry-dialog').open) categoryButtons(); }).observe(mobile$('entry-dialog'),{attributes:true,attributeFilter:['open']});
category.addEventListener('change',categoryButtons);
window.zzApp.ready.then(()=> {
  mobile$('save-status').textContent='已保存到本机';
  document.querySelector('footer span').textContent='离线记账 · 数据保存在本机';
});

function updateMobileState() {
  document.body.classList.toggle('mobile-home',!mobile$('home-view').hidden);
  document.body.classList.toggle('mobile-modal',Boolean(document.querySelector('dialog[open]')));
}
new MutationObserver(updateMobileState).observe(document.querySelector('main'),{subtree:true,attributes:true,attributeFilter:['hidden']});
document.querySelectorAll('dialog').forEach(dialog=>new MutationObserver(updateMobileState).observe(dialog,{attributes:true,attributeFilter:['open']}));
updateMobileState();
