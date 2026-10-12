"""窗口生命周期与软件启动配置。"""
import argparse
import json
from pathlib import Path
import sys
import threading
from .storage import LedgerStore
from .server import make_server
from .window import WindowControls

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    executable_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
    resource_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    asset_dir = resource_dir / "ui"
    data_dir = args.data_dir or executable_dir
    if args.smoke_test and not args.data_dir:
        parser.error("启动验证必须指定独立的 --data-dir")
    store = LedgerStore(data_dir)
    # 同一目录只允许一个软件实例，避免多个窗口互相覆盖账本。
    lock_path = store.directory / ".zz记.lock"
    lock_file = lock_path.open("r+b" if lock_path.exists() else "w+b")
    import msvcrt
    lock_file.seek(0)
    lock_file.write(b"0")
    lock_file.flush()
    lock_file.seek(0)
    try:
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, "此文件夹的zz记已在运行，请使用已打开的窗口。", "zz记", 0x40)
        return
    server, url, _ = make_server(asset_dir, store)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        import webview
        controls = WindowControls()
        window = webview.create_window("zz记 · 日常账本", url, width=1320, height=920, min_size=(860, 640), background_color="#f7f5fc", text_select=True, frameless=True, easy_drag=False, shadow=True, js_api=controls)
        controls.bind(window)
        if args.smoke_test:
            def smoke():
                try:
                    completed = threading.Event()
                    received = []
                    def on_result(result):
                        received.append(result)
                        completed.set()
                    window.evaluate_js("window.zzApp.ready.then(() => ({title:document.title,accounts:window.zzApp.snapshot().accounts.length,desktop:!!window.desktopConfig,total:document.getElementById('total-balance').textContent,titlebar:!!document.getElementById('window-close'),titlebarColor:getComputedStyle(document.querySelector('.window-titlebar')).backgroundColor,overflow:document.documentElement.scrollWidth > innerWidth}))", callback=on_result)
                    if not completed.wait(15):
                        raise RuntimeError('异步界面初始化超时')
                    details = received[0]
                    details["frameless"] = window.frameless
                    details["native_border"] = str(window.native.FormBorderStyle)
                    controls.toggle_maximize()
                    controls.toggle_maximize()
                    controls.minimize()
                    window.restore()
                    details["window_controls"] = "passed"
                    (store.directory / "smoke-result.json").write_text(json.dumps(details, ensure_ascii=False), encoding="utf-8")
                except Exception as error:
                    (store.directory / "smoke-error.txt").write_text(str(error), encoding="utf-8")
                finally:
                    window.destroy()
            window.events.loaded += smoke
        webview.start(gui="edgechromium", private_mode=True, icon=str(resource_dir / "app.ico") if (resource_dir / "app.ico").exists() else None)
    except Exception as error:
        import ctypes
        (store.directory / "启动错误.txt").write_text(str(error), encoding="utf-8")
        if not args.smoke_test:
            ctypes.windll.user32.MessageBoxW(0, f"启动失败：{error}\n请确认电脑已安装 Microsoft Edge WebView2 Runtime。", "zz记", 0x10)
        raise
    finally:
        server.shutdown()
        server.server_close()
        lock_file.close()


