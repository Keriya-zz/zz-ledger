from pathlib import Path
import shutil
ROOT=Path(__file__).resolve().parents[2]
def prepare():
    out=ROOT/'mobile/app/src/main/assets'
    shutil.copytree(ROOT/'ui',out,dirs_exist_ok=True)
    for name in ('native-api.js','mobile.css','mobile.js'): shutil.copy2(ROOT/'mobile/web'/name,out/name)
    html=(out/'index.html').read_text(encoding='utf-8')
    html=html.replace('<link rel="stylesheet" href="style.css">','<link rel="stylesheet" href="style.css"><link rel="stylesheet" href="mobile.css">')
    html=html.replace('<main>','<main><div class="mobile-brand"><strong>☾ zz记</strong><button id="mobile-backup" aria-label="导入与备份">⋮</button></div>')
    html=html.replace('  <dialog id="account-history-dialog"','  <dialog id="backup-dialog" aria-labelledby="backup-title"><div class="dialog-heading"><h2 id="backup-title">导入与备份</h2><button class="close-btn" data-close="backup-dialog" aria-label="关闭">×</button></div><p class="backup-note">账本保存在本机。导出的 JSON 可导入 Windows 版。</p><div id="backup-actions"></div><p class="backup-note">导入会替换当前账本；卸载 App 会删除本机账本。请先导出备份。</p></dialog>\n  <dialog id="account-history-dialog"')
    html=html.replace('<script src="api.js"></script>','<script src="native-api.js"></script>').replace('<script src="app.js"></script>','<script src="app.js"></script><script src="mobile.js"></script>')
    html=html.replace('width=device-width,initial-scale=1','width=device-width,initial-scale=1,viewport-fit=cover')
    html=html.replace('<meta name="theme-color"', '<meta http-equiv="Content-Security-Policy" content="default-src \'self\'; script-src \'self\'; style-src \'self\' \'unsafe-inline\'; img-src \'self\' data:; connect-src \'none\'; frame-src \'none\'; object-src \'none\'"><meta name="theme-color"')
    (out/'index.html').write_text(html,encoding='utf-8')
    app=(out/'app.js').read_text(encoding='utf-8')
    app=app.replace('已保存到本地','已保存到本机').replace('备份已保存到软件文件夹中的「导出」目录','账本备份已保存到所选位置').replace('每日明细已保存到软件文件夹中的「导出」目录','每日明细已保存到所选位置').replace('请检查软件文件夹的读写权限；如账本损坏，请先导出原始文件，再导入「账本.上一版.json」或其他有效备份恢复。','请先导出原始文件保留数据，再导入有效备份恢复。')
    (out/'app.js').write_text(app,encoding='utf-8')
    # Android never needs desktop window handlers or decorative desktop images.
    (out/'api.js').unlink(missing_ok=True)
    return out
if __name__=='__main__': print(prepare())
