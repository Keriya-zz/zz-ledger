"""Render and exercise our own application with isolated sample data."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import json
import shutil
import subprocess
import os
import argparse
import threading
from zzledger.storage import LedgerStore
from zzledger.server import make_server

root = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument('--mobile', action='store_true')
parser.add_argument('--ios', action='store_true', help='Exercise the iOS assets with a mocked WebKit bridge')
parser.add_argument('--preview-view', choices=('home','accounts','debts','stats'), default='debts')
parser.add_argument('--preview-dialog', choices=('repayment','entry','debt','account','account-history','transfer'), default=None)
parser.add_argument('--preview-custom-category', action='store_true')
parser.add_argument('--reference-a-fixture', action='store_true', help='Only change isolated preview data to the six-account concept A example')
args = parser.parse_args()
if args.ios:
    args.mobile = True
if not os.environ.get("CHROME_BIN"):
    raise SystemExit("请将 CHROME_BIN 环境变量设为本机 Chrome 可执行文件的路径。")
assets = root / '.qa/design-assets'
if args.mobile:
    sys.path.insert(0,str(root/('ios/scripts' if args.ios else 'mobile/scripts')))
    from prepare_assets import prepare
    shutil.copytree(prepare(),assets,dirs_exist_ok=True)
    page=assets/'index.html'
    import re
    text=page.read_text(encoding='utf-8')
    text=re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]+>', '', text)
    mock='''<script>window.ZZNative={request:async(id,action,payload)=>{try{const args=JSON.parse(payload); const response=await fetch('/api/'+(action==='export'?'export':'ledger'),{method:action==='read'?'GET':'POST',headers:{'X-ZZ-Token':window.desktopConfig.token,'Content-Type':'application/json'},body:action==='read'?undefined:JSON.stringify(action==='export'?{content:args.content,filename:args.filename}:{value:args.value})}); const result=await response.json();window.zzNativeReply(id,response.ok?{value:result.value}:{error:result.error});}catch(e){window.zzNativeReply(id,{error:e.message});}}};</script>'''
    if args.ios:
        mock='''<script>window.webkit={messageHandlers:{zzLedger:{postMessage:async args=>{if(args.action==='import')return window.qaImportContent ?? null;const response=await fetch('/api/'+(args.action==='export'?'export':'ledger'),{method:args.action==='read'?'GET':'POST',headers:{'X-ZZ-Token':window.desktopConfig.token,'Content-Type':'application/json'},body:args.action==='read'?undefined:JSON.stringify(args.action==='export'?{content:args.content,filename:args.filename}:{value:args.value})});const result=await response.json();if(!response.ok)throw new Error(result.error);return result.value ?? null;}}}};</script>'''
    text=text.replace('<script src="native-api.js">',mock+'<script src="native-api.js">')
    page.write_text(text,encoding='utf-8')
    api=assets/'native-api.js';api.write_text(api.read_text(encoding='utf-8-sig').replace("window.desktopConfig = {platform:'android',directory:'App 私有存储'};","window.desktopConfig = {...window.desktopConfig,platform:'android',directory:'App 私有存储'};"),encoding='utf-8')
    if args.ios:
        api.write_text(api.read_text(encoding='utf-8').replace("window.desktopConfig = {platform: 'ios', directory: 'iPhone 本机存储'};", "window.desktopConfig = {...window.desktopConfig, platform: 'ios', directory: 'iPhone 本机存储'};"),encoding='utf-8')
else:
    shutil.copytree(root/'ui', assets, dirs_exist_ok=True)
store = LedgerStore(root/'.qa/design-data')
data = {"version":1,"accounts":[
    {"id":"wx","name":"微信","type":"微信","balance":128640},
    {"id":"alipay","name":"支付宝","type":"支付宝","balance":215800},
    {"id":"bank","name":"生活储蓄卡","type":"银行卡","balance":680000}],"entries":[
    {"id":"lunch","accountId":"wx","kind":"expense","amount":2800,"date":"2026-10-12","category":"餐饮","note":"一顿好好吃的午餐"},
    {"id":"metro","accountId":"alipay","kind":"expense","amount":600,"date":"2026-10-12","category":"交通","note":"下班地铁"}]}
store.write(json.dumps(data,ensure_ascii=False))
script = r'''
<script>
window.zzApp.ready.then(async () => {
  const $ = id => document.getElementById(id);
  const check = (ok, message) => {if (!ok) throw new Error(message);};
  const submit = id => $(id).onsubmit({preventDefault(){}});
  const snapshot = () => window.zzApp.snapshot();
  try {
    const previousMonth=$('stats-month').value;
    $('stats-month').value='2026-10'; $('stats-month').onchange();
    check($('account-expenses').querySelectorAll('tbody tr').length===3,'所有账户支出统计');
    check($('account-expenses').querySelector('[data-expense-account="wx"] .account-expenses-amount').textContent==='¥ 28.00','账户月支出金额');
    document.querySelector('#account-expenses [data-account-history="wx"]').click();
    check($('account-history-dialog').open && $('account-history-month').value==='2026-10','账户明细继承月份');
    check($('account-history-list').querySelectorAll('.entry-row').length===1 && $('account-history-list').textContent.includes('28.00') && !$('account-history-list').textContent.includes('地铁'),'明细仅包含当前账户');
    $('account-history-kind').value='income'; $('account-history-kind').onchange();
    check(!$('account-history-list').querySelector('.entry-row'),'收入筛选与空状态');
    $('account-history-kind').value='all'; $('account-history-kind').onchange();
    check($('account-history-list').querySelectorAll('.entry-row').length===1,'全部收支筛选');
    $('account-history-month').value='2026-09'; $('account-history-month').onchange();
    check(!$('account-history-list').querySelector('.entry-row'),'明细月份筛选');
    $('account-history-dialog').querySelector('[data-close]').click();
    $('stats-month').value='2026-09'; $('stats-month').onchange();
    check([...$('account-expenses').querySelectorAll('.account-expenses-amount')].every(el=>el.textContent==='¥ 0.00'),'切换无支出月份');
    $('stats-month').value=previousMonth; $('stats-month').onchange();
    $('add-account').click(); $('account-name').value='测试现金'; $('account-type').value='现金'; $('account-balance').value='200.00';
    await submit('account-form'); check(snapshot().accounts.length === 4,'账户添加');
    const cash=snapshot().accounts[3].id;
    const beforeImport=JSON.stringify(snapshot());
    if (window.desktopConfig.platform==='ios') {
      window.qaImportContent=null;
      await $('import-btn').onclick();
      check(!$('confirm-dialog').open && JSON.stringify(snapshot())===beforeImport,'iOS 取消选择不改变账本');
      window.qaImportContent='{bad';
      await $('import-btn').onclick();
      check(!$('confirm-dialog').open && $('toast').textContent.includes('JSON'),'iOS 原生导入拒绝损坏 JSON');
      window.qaImportContent=JSON.stringify({...snapshot(),entries:[{id:'broken'}]});
      await $('import-btn').onclick();
      check(!$('confirm-dialog').open && JSON.stringify(snapshot())===beforeImport,'iOS 原生导入校验领域数据');
      window.qaImportContent=beforeImport;
      await $('import-btn').onclick();
      check($('confirm-dialog').open,'iOS 原生导入要求确认');
      $('confirm-dialog').querySelector('[data-close]').click();
      check(JSON.stringify(snapshot())===beforeImport,'iOS 取消确认保持原账本');
      await $('import-btn').onclick(); await $('confirm-action').onclick();
      check(JSON.stringify(snapshot())===beforeImport,'iOS 原生导入成功');
    }
    await $('import-file').onchange({target:{files:[new File(['{bad'], 'bad.json')],value:'bad'}});
    check(JSON.stringify(snapshot())===beforeImport && !$('confirm-dialog').open,'无效导入不改变账本');
    await $('import-file').onchange({target:{files:[new File([beforeImport], 'backup.json')],value:'backup'}});
    check($('confirm-dialog').open,'导入前需确认');
    $('confirm-dialog').querySelector('[data-close]').click();
    check(JSON.stringify(snapshot())===beforeImport,'取消导入保留账本');
    await $('import-file').onchange({target:{files:[new File([beforeImport], 'backup.json')],value:'backup'}});
    await $('confirm-action').onclick();
    check(JSON.stringify(snapshot())===beforeImport,'导入恢复兼容账本');
    const beforeTransfer=JSON.stringify(snapshot());
    document.querySelector('[data-new-transfer]').click();
    $('transfer-from').value='wx'; $('transfer-to').value='wx'; $('transfer-amount').value='10.01';
    await submit('transfer-form');
    check($('transfer-error').textContent.includes('不能相同') && JSON.stringify(snapshot())===beforeTransfer,'同账户划转被拒绝');
    $('transfer-to').value=cash; $('transfer-note').value='<img src=x>';
    const transferFetch=window.fetch;
    window.fetch=async (...args)=>args[0]==='/api/ledger' && args[1]?.method==='POST' ? new Response(JSON.stringify({error:'模拟划转保存失败'}),{status:500,headers:{'Content-Type':'application/json'}}) : transferFetch(...args);
    await submit('transfer-form');
    check(JSON.stringify(snapshot())===beforeTransfer && $('transfer-error').textContent.includes('保存失败'),'划转保存失败两边余额不变');
    window.fetch=transferFetch;
    await Promise.all([submit('transfer-form'),submit('transfer-form')]);
    check(snapshot().transfers.length===1 && snapshot().accounts[0].balance===127639 && snapshot().accounts[3].balance===21001,'划转双余额更新及重复提交保护');
    const transferId=snapshot().transfers[0].id;
    check($('transfer-list').textContent.includes('<img src=x>') && !$('transfer-list').querySelector('img'),'划转备注安全显示');
    check(JSON.parse(await window.DesktopAPI.read()).transfers.length===1,'划转保存可重新读取');
    document.querySelector('#manage-cards [data-account-history="'+cash+'"]').click();
    $('account-history-kind').value='transfer'; $('account-history-kind').onchange();
    check($('account-history-list').textContent.includes('转入') && $('account-history-list').textContent.includes('+ ¥ 10.01'),'转入账户明细');
    $('account-history-dialog').close();
    document.querySelector('#manage-cards [data-account-history="wx"]').click();
    $('account-history-kind').value='transfer'; $('account-history-kind').onchange();
    check($('account-history-list').textContent.includes('转出') && $('account-history-list').textContent.includes('− ¥ 10.01'),'转出账户明细');
    $('account-history-dialog').close();
    document.querySelector('[data-delete-account="'+cash+'"]').click();
    check(!$('confirm-dialog').open && $('toast').textContent.includes('划转'),'禁止删除划转关联账户');
    document.querySelector('#transfer-list [data-edit-transfer]').click();
    $('transfer-from').value=cash; $('transfer-to').value='alipay'; $('transfer-amount').value='20.00';
    await submit('transfer-form');
    check(snapshot().accounts[0].balance===128640 && snapshot().accounts[3].balance===18000 && snapshot().accounts[1].balance===217800,'编辑划转恢复原双方并调整新双方');
    document.querySelector('#transfer-list [data-delete-transfer]').click(); await $('confirm-action').onclick();
    check(snapshot().transfers.length===0 && snapshot().accounts[3].balance===20000 && snapshot().accounts[1].balance===215800,'删除划转恢复双方余额');

    $('add-entry').click(); $('entry-account').value=cash; $('entry-amount').value='5.00';
    $('entry-category').value=''; $('entry-category').onchange();
    check(!$('custom-category-field').hidden && $('entry-custom-category').required,'自定义分类输入');
    $('entry-custom-category').value='   '; await submit('entry-form');
    check($('entry-error').textContent.includes('分类名称') && snapshot().entries.length===2,'空分类不能保存');
    const realFetch=window.fetch;
    window.fetch=async (...args)=>args[0]==='/api/ledger' && args[1]?.method==='POST' ? new Response(JSON.stringify({error:'模拟写入失败'}),{status:500,headers:{'Content-Type':'application/json'}}) : realFetch(...args);
    $('entry-custom-category').value='学习'; await submit('entry-form');
    check(!snapshot().customCategories && snapshot().entries.length===2,'分类保存失败回滚');
    window.fetch=realFetch;
    const customName='<img src=x>';
    $('entry-custom-category').value=customName; await submit('entry-form');
    const customId=snapshot().entries[0].id;
    check(snapshot().customCategories.includes(customName) && snapshot().entries[0].category===customName,'自定义分类落盘');
    document.querySelector('#account-expenses [data-account-history="'+cash+'"]').click();
    check($('account-history-list').textContent.includes(customName) && !$('account-history-list').querySelector('img'),'交易明细文本转义');
    $('account-history-dialog').close();
    check($('entry-list').textContent.includes(customName) && !$('entry-list').querySelector('img'),'分类列表转义');
    check($('category-chart').textContent.includes(customName) && !$('category-chart').querySelector('img'),'自定义分类统计与转义');
    const persisted=JSON.parse(await window.DesktopAPI.read());
    check(persisted.customCategories.includes(customName),'重新读取保留分类');
    document.querySelector('[data-edit-entry="'+customId+'"]').click();
    check($('entry-category').value===customName && $('custom-category-field').hidden,'编辑自定义分类回显');
    $('entry-dialog').close();
    document.querySelector('[data-delete-entry="'+customId+'"]').click(); await $('confirm-action').onclick();
    $('add-entry').click();
    check([...$('entry-category').options].some(o=>o.value===customName),'删除后仍可复用自定义分类');
    $('entry-dialog').close();
    $('add-entry').click(); $('entry-account').value=cash; $('entry-amount').value='12.99'; $('entry-note').value='<img src=x onerror=alert(1)>';
    await Promise.all([submit('entry-form'),submit('entry-form')]);
    check(snapshot().entries.length === 3 && snapshot().accounts[3].balance === 18701,'异步重复提交保护');
    check(!$('entry-list').querySelector('img'),'备注安全转义');
    const entry=snapshot().entries[0].id;
    document.querySelector('[data-edit-entry="'+entry+'"]').click(); $('entry-amount').value='20.00'; $('entry-account').value='wx';
    await submit('entry-form'); check(snapshot().accounts[3].balance === 20000 && snapshot().accounts[0].balance === 126640,'跨账户编辑恢复余额');
    document.querySelector('[data-delete-entry="'+entry+'"]').click(); await $('confirm-action').onclick();
    check(snapshot().entries.length === 2 && snapshot().accounts[0].balance === 128640,'删除余额恢复');
    const originalFetch=window.fetch;
    window.fetch=async (...args)=>args[0]==='/api/ledger' && args[1]?.method==='POST' ? new Response(JSON.stringify({error:'模拟写入失败'}),{status:500,headers:{'Content-Type':'application/json'}}) : originalFetch(...args);
    $('add-entry').click(); $('entry-account').value=cash; $('entry-amount').value='10.00'; await submit('entry-form');
    check(snapshot().accounts[3].balance === 20000 && snapshot().entries.length === 2 && $('entry-error').textContent.includes('模拟写入失败'),'保存失败不能修改内存账本');
    window.fetch=originalFetch; $('entry-dialog').close();
    document.querySelector('[data-view="accounts"]').click(); document.querySelector('[data-delete-account="'+cash+'"]').click(); await $('confirm-action').onclick();
    document.querySelector('[data-view="home"]').click();
    await $('export-btn').onclick();
    document.querySelector('[data-view="debts"]').click();
    async function addDebt(name, amount, due) {
      document.querySelector('[data-new-debt]').click();
      $('debt-name').value=name; $('debt-creditor').value='示例还款对象'; $('debt-amount').value=amount; $('debt-due').value=due;
      await submit('debt-form');
      return snapshot().debts[snapshot().debts.length-1].id;
    }
    const testDebt=await addDebt('测试信用卡','60.00','2026-10-10');
    check(snapshot().accounts[0].balance===128640,'登记待还款不影响余额');
    check($('home-debt-total').textContent==='¥ 60.00' && $('debt-list').querySelector('.overdue'),'待还总额与逾期状态');
    document.querySelector('[data-repay-debt="'+testDebt+'"]').click(); $('repay-account').value='wx'; $('repay-amount').value='20.00';
    await Promise.all([submit('repay-form'),submit('repay-form')]);
    check(snapshot().entries.length===3 && snapshot().accounts[0].balance===126640,'部分还款与防重复提交');
    check($('home-debt-total').textContent==='¥ 40.00','部分还款摘要');
    document.querySelector('[data-repay-debt="'+testDebt+'"]').click(); $('repay-amount').value='40.01'; await submit('repay-form');
    check($('repay-error').textContent.includes('超过') && snapshot().entries.length===3,'阻止超额还款'); $('repay-dialog').close();
    document.querySelector('[data-history-debt="'+testDebt+'"]').click(); $('debt-history-list').querySelector('[data-edit-entry]').click();
    check($('entry-category').disabled && $('entry-form').querySelector('[value=income]').disabled,'还款账单关联保护');
    $('entry-amount').value='30.00'; $('entry-account').value='alipay'; await submit('entry-form');
    check(snapshot().accounts[0].balance===128640 && snapshot().accounts[1].balance===212800 && $('home-debt-total').textContent==='¥ 30.00','还款跨账户编辑');
    document.querySelector('[data-history-debt="'+testDebt+'"]').click(); $('debt-history-list').querySelector('[data-delete-entry]').click(); await $('confirm-action').onclick();
    check(snapshot().accounts[1].balance===215800 && $('home-debt-total').textContent==='¥ 60.00','撤销还款恢复账户与待还');
    document.querySelector('[data-repay-debt="'+testDebt+'"]').click(); $('repay-account').value='wx'; await submit('repay-form');
    check($('home-debt-total').textContent==='¥ 0.00','全额还款');
    $('debt-filter').value='settled'; $('debt-filter').onchange(); check($('debt-list').querySelector('.settled'),'已还清筛选');
    document.querySelector('[data-history-debt="'+testDebt+'"]').click(); $('debt-history-list').querySelector('[data-delete-entry]').click(); await $('confirm-action').onclick();
    $('debt-filter').value='all'; $('debt-filter').onchange(); document.querySelector('[data-delete-debt="'+testDebt+'"]').click(); await $('confirm-action').onclick();
    check(snapshot().debts.length===0 && snapshot().accounts[0].balance===128640,'待还款删除与恢复');
    $('debt-filter').value='pending';
    const card=await addDebt('10 月信用卡账单','650.00','2026-10-15');
    await addDebt('花呗待还','180.00','2026-10-10');
    await addDebt('朋友借款','1200.00','');
    document.querySelector('[data-repay-debt="'+card+'"]').click(); $('repay-account').value='wx'; $('repay-amount').value='100.00'; await submit('repay-form');
    check(document.documentElement.scrollWidth<=innerWidth,'横向溢出');
    await new Promise(resolve=>setTimeout(resolve,50));
    check(snapshot().accounts.length===3,'账户删除');
    if (window.referenceAFixture) {
      document.querySelector('[data-view="accounts"]').click();
      const targetBalances=[['微信','201.19'],['支付宝','30.10'],['招商4345','246.96']];
      for (let i=0;i<3;i++) {
        const id=snapshot().accounts[i].id;
        document.querySelector('[data-edit-account="'+id+'"]').click();
        $('account-name').value=targetBalances[i][0]; $('account-balance').value=targetBalances[i][1];
        await submit('account-form');
      }
      for (const [name,type,amount] of [['招商5055','银行卡','255.74'],['币安','其他','100.72'],['校园卡','其他','32.87']]) {
        $('accounts-add').click(); $('account-name').value=name; $('account-type').value=type; $('account-balance').value=amount;
        await submit('account-form');
      }
      check(snapshot().accounts.length===6,'六账户示例');
      document.querySelector('[data-view="home"]').click();
      check($('account-cards').querySelectorAll('.account-row').length===6,'首页账户列表渲染');
      $('account-cards').querySelector('[data-edit-account]').click();
      check($('account-dialog').open && $('account-name').value==='微信','列表编辑入口');
      $('account-dialog').close();
    }
    document.body.dataset.qaResult='PASS';
    $('toast').hidden=true;
  } catch(error) {document.body.dataset.qaResult='FAIL: '+error.message;}
});
</script>'''
preview_actions = f"document.querySelector('[data-view=\"{args.preview_view}\"]').click();"
if args.preview_view == 'home':
    preview_actions += "$('selected-date').value='2026-10-12'; $('selected-date').onchange();"
    preview_actions += "check($('entry-list').querySelectorAll('.entry-row').length===2, '首页每日开销明细');"
    preview_actions += "check($('entry-list').closest('.balance-pane') && getComputedStyle($('add-entry')).borderRadius==='4px', '每日开销位置与按钮圆角');"
if args.preview_dialog:
    selector = {'repayment':'[data-repay-debt]', 'entry':'#add-entry', 'debt':'[data-new-debt]', 'account':'#add-account', 'account-history':'#account-expenses [data-account-history]', 'transfer':'[data-new-transfer]'}[args.preview_dialog]
    preview_actions += f"document.querySelector('{selector}').click();"
if args.preview_custom_category:
    if args.preview_dialog != 'entry': parser.error('--preview-custom-category requires --preview-dialog entry')
    preview_actions += "$('entry-category').value=''; $('entry-category').onchange(); $('entry-custom-category').value='学习'; $('entry-amount').value='25.00';"
preview_actions += "check(document.querySelector('main').scrollWidth <= document.querySelector('main').clientWidth, '内容区横向溢出');"
if args.mobile and not args.preview_dialog:
    preview_actions += "check($('add-entry').getBoundingClientRect().width>0 && $('add-entry').getBoundingClientRect().bottom<=innerHeight,'手机记账入口可见');"
preview_actions += "await document.fonts.ready; await new Promise(resolve => setTimeout(resolve,220));"
script=script.replace("document.body.dataset.qaResult='PASS';", preview_actions+" document.body.dataset.qaResult='PASS';")
fixture_config = '<script>window.referenceAFixture='+('true' if args.reference_a_fixture else 'false')+';</script>'
p=assets/'index.html';p.write_text(p.read_text(encoding='utf-8').replace('</body>',fixture_config+script+'</body>'),encoding='utf-8')
server,url,_=make_server(assets,store)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
    sizes = ((375,667,'ios-compact'),(393,852,'ios-iphone'),(852,393,'ios-landscape')) if args.ios else (((390,844,'mobile-desktop'),(360,800,'mobile-compact')) if args.mobile else ((1440,1100,'design-desktop'),(900,900,'design-compact')))
    for width,height,label in sizes:
        store.write(json.dumps(data,ensure_ascii=False))
        command=[os.environ['CHROME_BIN'],'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',f'--user-data-dir={root / ".qa" / (label+"-profile")}',f'--window-size={width},{height}','--virtual-time-budget=6000',f'--screenshot={root / ".qa" / (label+".png")}', '--dump-dom',url]
        if args.mobile:
            command=['node',str(root/'tests/render_mobile.cjs'),url,str(width),str(height),str(root/'.qa'/(label+'-cdp-profile')),str(root/'.qa'/(label+'.png')),str(root/'.qa'/(label+'.html'))]
            subprocess.run(command,check=True,timeout=40)
            rendered=(root/'.qa'/(label+'.html')).read_text(encoding='utf-8')
        else:
            result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
            rendered=result.stdout.decode('utf-8',errors='replace')
        (root/'.qa'/f'{label}.html').write_text(rendered,encoding='utf-8')
        if 'data-qa-result="PASS"' not in rendered: raise RuntimeError('浏览器回归失败：'+str(__import__('re').findall(r'data-qa-result="([^"]*)"',rendered))+rendered[-300:])
        print(label+': PASS (async save, double submit, edit/delete, failure rollback, export, layout)')
finally:
    server.shutdown();server.server_close()
