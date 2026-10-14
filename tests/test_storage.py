import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from desktop import LedgerStore, make_server


def sample(balance=10000):
    return {"version": 1, "accounts": [{"id": "wx", "name": "微信", "type": "微信", "balance": balance}], "entries": []}


class DesktopTests(unittest.TestCase):
    def test_persist_and_previous_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LedgerStore(directory)
            self.assertIsNone(store.read())
            store.write(json.dumps(sample(), ensure_ascii=False))
            store.write(json.dumps(sample(8701), ensure_ascii=False))
            self.assertEqual(json.loads(LedgerStore(directory).read())["accounts"][0]["balance"], 8701)
            self.assertEqual(json.loads(store.backup.read_text(encoding="utf-8"))["accounts"][0]["balance"], 10000)
            invalid = sample(); invalid["accounts"][0]["balance"] = "wrong"
            with self.assertRaises(ValueError):
                store.write(json.dumps(invalid))
            self.assertEqual(json.loads(store.read())["accounts"][0]["balance"], 8701)
            self.assertFalse((Path(directory) / "账本.json.tmp").exists())

    def test_corrupt_file_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LedgerStore(directory)
            store.path.write_text("corrupt", encoding="utf-8")
            self.assertEqual(store.read(), "corrupt")
            store.write(json.dumps(sample()))
            self.assertEqual(store.backup.read_text(encoding="utf-8"), "corrupt")

    def test_export_rejects_traversal_and_preserves_repeated_exports(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LedgerStore(directory)
            first = store.export("备份.json", "{}")
            second = store.export("备份.json", "{\"version\":1}")
            self.assertNotEqual(first, second)
            self.assertEqual(Path(first).read_text(encoding="utf-8"), "{}")
            for filename in ("../outside.json", "..\\outside.json", "bad.exe"):
                with self.assertRaises(ValueError): store.export(filename, "{}")

    def test_http_storage_and_access_control(self):
        with tempfile.TemporaryDirectory() as directory:
            store = LedgerStore(directory)
            server, url, token = make_server(Path(__file__).resolve().parent.parent / "ui", store)
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            base = url.split("/?")[0]
            try:
                with self.assertRaises(HTTPError) as result: urlopen(base + "/api/ledger")
                self.assertEqual(result.exception.code, 403)
                result.exception.close()
                with self.assertRaises(HTTPError) as denied: urlopen(base + "/")
                denied.exception.close()
                self.assertIn(b"window.desktopConfig", urlopen(url).read())
                image = urlopen(base + "/assets/sidebar-engraving.png")
                self.assertTrue(image.headers.get('Content-Type').startswith('image/png'))
                self.assertEqual(image.read(8), b'\x89PNG\r\n\x1a\n')
                image.close()
                raw = json.dumps(sample())
                request = Request(base+"/api/ledger", data=json.dumps({"value": raw}).encode(), headers={"X-ZZ-Token":token,"Content-Type":"application/json"})
                self.assertEqual(urlopen(request).status,200)
                request = Request(base+"/api/ledger",headers={"X-ZZ-Token":token})
                self.assertEqual(json.loads(json.loads(urlopen(request).read())["value"]),sample())
            finally:
                server.shutdown(); server.server_close(); thread.join()


if __name__ == "__main__": unittest.main()

