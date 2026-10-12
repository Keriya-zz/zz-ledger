"""zz记 Windows 桌面入口。账本始终保存在可执行文件所在目录。"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
from pathlib import Path
import secrets
import shutil
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

MAX_BYTES = 10 * 1024 * 1024
ASSETS = {"index.html", "style.css", "app.js", "core.js"}


def validate_ledger(data):
    from datetime import date
    def integer(value):
        return type(value) is int and abs(value) <= 999999999999
    if not isinstance(data, dict) or data.get("version") != 1 or not isinstance(data.get("accounts"), list) or not isinstance(data.get("entries"), list):
        raise ValueError("账本格式不正确")
    ids = set()
    for a in data["accounts"]:
        if not isinstance(a, dict) or not isinstance(a.get("id"), str) or not a["id"] or a["id"] in ids or not isinstance(a.get("name"), str) or not a["name"].strip() or len(a["name"]) > 30 or a.get("type") not in ("微信", "支付宝", "银行卡", "现金", "其他") or not integer(a.get("balance")):
            raise ValueError("账户数据无效")
        ids.add(a["id"])
    entries = set()
    for e in data["entries"]:
        if not isinstance(e, dict) or not isinstance(e.get("id"), str) or not e["id"] or e["id"] in entries or e.get("accountId") not in ids or e.get("kind") not in ("expense", "income") or not integer(e.get("amount")) or e["amount"] <= 0 or e.get("category") not in ("餐饮", "交通", "购物", "生活", "娱乐", "医疗", "其他") or not isinstance(e.get("note"), str) or len(e["note"]) > 200:
            raise ValueError("收支记录无效")
        if not isinstance(e.get("date"), str) or date.fromisoformat(e["date"]).isoformat() != e["date"]:
            raise ValueError("日期无效")
        entries.add(e["id"])
    return data


class LedgerStore:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "账本.json"
        self.backup = self.directory / "账本.上一版.json"
        self.lock = threading.Lock()

    def read(self):
        with self.lock:
            return self.path.read_text(encoding="utf-8") if self.path.exists() else None

    def write(self, raw):
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > MAX_BYTES:
            raise ValueError("账本文件过大")
        validate_ledger(json.loads(raw))
        with self.lock:
            temporary = self.directory / "账本.json.tmp"
            temporary.write_text(raw, encoding="utf-8")
            # 先完整落盘，再替换账本；保留前一版文件供恢复。
            with temporary.open("r+b") as handle:
                os.fsync(handle.fileno())
            if self.path.exists():
                shutil.copy2(self.path, self.backup)
            os.replace(temporary, self.path)

    def export(self, filename, content):
        if not isinstance(filename, str) or Path(filename).name != filename or any(c in filename for c in '\\/:*?"<>|') or not filename.endswith((".json", ".csv")) or not isinstance(content, str) or len(content.encode("utf-8")) > MAX_BYTES:
            raise ValueError("导出文件无效")
        folder = self.directory / "导出"
        folder.mkdir(exist_ok=True)
        destination = folder / filename
        if destination.exists():
            destination = folder / f"{destination.stem}-{secrets.token_hex(3)}{destination.suffix}"
        destination.write_text(content, encoding="utf-8", newline="")
        return str(destination)


def make_server(asset_dir, store):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def respond(self, code, body, content_type="application/json; charset=utf-8"):
            if isinstance(body, dict):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            elif isinstance(body, str):
                body = body.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def authorized(self):
            return secrets.compare_digest(self.headers.get("X-ZZ-Token", ""), token)

        def do_GET(self):
            parsed = urlsplit(self.path)
            if parsed.path == "/api/ledger":
                if not self.authorized():
                    self.respond(403, {"error": "无访问权限"}); return
                try:
                    self.respond(200, {"value": store.read()})
                except Exception as error:
                    self.respond(500, {"error": f"读取账本失败：{error}"})
                return
            name = parsed.path.lstrip("/") or "index.html"
            if name not in ASSETS:
                self.respond(404, {"error": "文件不存在"}); return
            if name == "index.html" and not secrets.compare_digest(parse_qs(parsed.query).get("token", [""])[0], token):
                self.respond(403, {"error": "请从zz记软件打开账本"}); return
            try:
                data = (asset_dir / name).read_bytes()
                if name == "index.html":
                    config = json.dumps({"token": token, "directory": str(store.directory)}, ensure_ascii=True)
                    data = data.replace(b'<script src="core.js">', f'<script>window.desktopConfig={config};</script><script src="core.js">'.encode())
                content_type = mimetypes.guess_type(name)[0] or "application/octet-stream"
                self.respond(200, data, content_type + "; charset=utf-8")
            except Exception as error:
                self.respond(500, {"error": str(error)})

        def do_POST(self):
            if not self.authorized():
                self.respond(403, {"error": "无访问权限"}); return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= MAX_BYTES * 2:
                    raise ValueError("请求大小无效")
                payload = json.loads(self.rfile.read(size))
                if self.path == "/api/ledger":
                    store.write(payload["value"])
                    self.respond(200, {"ok": True})
                elif self.path == "/api/export":
                    destination = store.export(payload["filename"], payload["content"])
                    self.respond(200, {"path": destination})
                else:
                    self.respond(404, {"error": "接口不存在"})
            except Exception as error:
                self.respond(400, {"error": f"保存失败：{error}"})

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    return server, f"http://127.0.0.1:{server.server_port}/?token={token}", token


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--smoke-test", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    executable_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    resource_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    asset_dir = resource_dir / "ui"
    data_dir = args.data_dir or executable_dir
    store = LedgerStore(data_dir)
    # 同一目录只允许一个软件实例，避免多个窗口互相覆盖账本。
    lock_file = (store.directory / ".zz记.lock").open("a+b")
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
        window = webview.create_window("zz记 · 日常账本", url, width=1280, height=900, min_size=(800, 600), background_color="#f8f7fc", text_select=True)
        if args.smoke_test:
            def smoke():
                try:
                    result = window.evaluate_js("JSON.stringify({title:document.title,accounts:state.accounts.length,desktop:!!window.desktopConfig,total:document.getElementById('total-balance').textContent})")
                    (store.directory / "smoke-result.json").write_text(result, encoding="utf-8")
                except Exception as error:
                    (store.directory / "smoke-error.txt").write_text(str(error), encoding="utf-8")
                finally:
                    window.destroy()
            window.events.loaded += smoke
        webview.start(gui="edgechromium", private_mode=True, icon=str(resource_dir / "app.ico") if (resource_dir / "app.ico").exists() else None)
    except Exception as error:
        import ctypes
        (store.directory / "启动错误.txt").write_text(str(error), encoding="utf-8")
        ctypes.windll.user32.MessageBoxW(0, f"启动失败：{error}\n请确认电脑已安装 Microsoft Edge WebView2 Runtime。", "zz记", 0x10)
        raise
    finally:
        server.shutdown()
        server.server_close()
        lock_file.close()


if __name__ == "__main__":
    main()
