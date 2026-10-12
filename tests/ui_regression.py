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
parser.add_argument('--preview-view', choices=('home','accounts','debts','stats'), default='debts')
parser.add_argument('--preview-dialog', choices=('repayment','entry','debt','account'), default=None)
args = parser.parse_args()
if not os.environ.get("CHROME_BIN"):
    raise SystemExit("请将 CHROME_BIN 环境变量设为本机 Chrome 可执行文件的路径。")
assets = root / '.qa/design-assets'
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
    $('add-account').click(); $('account-name').value='测试现金'; $('account-type').value='现金'; $('account-balance').value='200.00';
    await submit('account-form'); check(snapshot().accounts.length === 4,'账户添加');
    const cash=snapshot().accounts[3].id;
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
    document.body.dataset.qaResult='PASS';
    $('toast').hidden=true;
  } catch(error) {document.body.dataset.qaResult='FAIL: '+error.message;}
});
</script>'''
preview_actions = f"document.querySelector('[data-view=\"{args.preview_view}\"]').click();"
if args.preview_dialog:
    selector = {'repayment':'[data-repay-debt]', 'entry':'#add-entry', 'debt':'[data-new-debt]', 'account':'#add-account'}[args.preview_dialog]
    preview_actions += f"document.querySelector('{selector}').click();"
preview_actions += "check(document.querySelector('main').scrollWidth <= document.querySelector('main').clientWidth, '内容区横向溢出');"
script=script.replace("document.body.dataset.qaResult='PASS';", preview_actions+" document.body.dataset.qaResult='PASS';")
p=assets/'index.html';p.write_text(p.read_text(encoding='utf-8').replace('</body>',script+'</body>'),encoding='utf-8')
server,url,_=make_server(assets,store)
thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
try:
    for width,height,label in ((1440,1100,'design-desktop'),(900,900,'design-compact')):
        store.write(json.dumps(data,ensure_ascii=False))
        command=[os.environ['CHROME_BIN'],'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',f'--user-data-dir={root / ".qa" / (label+"-profile")}',f'--window-size={width},{height}','--virtual-time-budget=6000',f'--screenshot={root / ".qa" / (label+".png")}', '--dump-dom',url]
        result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
        rendered=result.stdout.decode('utf-8',errors='replace')
        (root/'.qa'/f'{label}.html').write_text(rendered,encoding='utf-8')
        if 'data-qa-result="PASS"' not in rendered: raise RuntimeError('浏览器回归失败：'+rendered[-2000:])
        print(label+': PASS (async save, double submit, edit/delete, failure rollback, export, layout)')
finally:
    server.shutdown();server.server_close()
