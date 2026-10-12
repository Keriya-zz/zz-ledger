"""原子保存、上一版备份和导出文件。"""
import json
import os
from pathlib import Path
import secrets
import shutil
import threading
from .domain import validate_ledger

MAX_BYTES = 10 * 1024 * 1024

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


