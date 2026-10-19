"""Build the iPhone bundle from the same UI and ledger logic as Android/Windows."""
from pathlib import Path
import importlib.util
import shutil

ROOT = Path(__file__).resolve().parents[2]


def prepare():
    spec = importlib.util.spec_from_file_location('mobile_assets', ROOT / 'mobile/scripts/prepare_assets.py')
    mobile = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mobile)
    out = mobile.prepare(ROOT / 'ios/ZZLedger/Web')
    for name in ('native-api.js', 'ios.css'):
        shutil.copy2(ROOT / 'ios/web' / name, out / name)
    page = out / 'index.html'
    html = page.read_text(encoding='utf-8')
    html = html.replace('<link rel="stylesheet" href="mobile.css">',
                        '<link rel="stylesheet" href="mobile.css"><link rel="stylesheet" href="ios.css">')
    html = html.replace('导出的 JSON 可导入 Windows 版。', '导出的 JSON 可导入 Windows、Android 或 iOS 版。')
    # No desktop chrome or image needs to be fetched by the iPhone web view.
    import re
    html = re.sub(r'<div class="sidebar-illustration".*?</div>', '', html)
    page.write_text(html, encoding='utf-8')
    shutil.rmtree(out / 'assets', ignore_errors=True)
    return out


if __name__ == '__main__':
    print(prepare())
