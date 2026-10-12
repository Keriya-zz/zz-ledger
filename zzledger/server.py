"""仅监听本机的界面资源与文件接口。"""
import json
import mimetypes
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from .storage import MAX_BYTES

def make_server(asset_dir, store):
    token = secrets.token_urlsafe(32)
    assets = {p.relative_to(asset_dir).as_posix() for p in asset_dir.rglob("*") if p.is_file() and p.suffix in (".html", ".js", ".css", ".svg")}

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
            if name not in assets:
                self.respond(404, {"error": "文件不存在"}); return
            if name == "index.html" and not secrets.compare_digest(parse_qs(parsed.query).get("token", [""])[0], token):
                self.respond(403, {"error": "请从zz记软件打开账本"}); return
            try:
                data = (asset_dir / name).read_bytes()
                if name == "index.html":
                    config = json.dumps({"token": token, "directory": str(store.directory)}, ensure_ascii=True)
                    data = data.replace(b'<!--DESKTOP_CONFIG-->', f'<script>window.desktopConfig={config};</script>'.encode())
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


