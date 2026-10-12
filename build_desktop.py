"""在项目的独立虚拟环境中运行，生成单文件 Windows EXE。"""
from pathlib import Path
import shutil
import subprocess
import sys
from PIL import Image, ImageDraw

root = Path(__file__).resolve().parent
image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(image)
draw.rounded_rectangle((8, 8, 248, 248), radius=56, fill="#ab8bd5")
draw.rounded_rectangle((62, 48, 195, 212), radius=16, fill="#faf7ff")
draw.rounded_rectangle((51, 48, 72, 212), radius=9, fill="#7855ac")
for y in (89, 125, 161):
    draw.ellipse((91, y-5, 101, y+5), fill="#b69ada")
    draw.rounded_rectangle((115, y-4, 170, y+4), radius=4, fill="#c8b0e5")
image.save(root / "app.ico", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
command = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile", "--windowed", "--name", "zz记", "--icon", str(root / "app.ico"), "--exclude-module", "tkinter"]
for filename in ("index.html", "style.css", "app.js", "core.js"):
    command.extend(["--add-data", f"{root / 'ui' / filename};ui"])
command.extend(["--add-data", f"{root / 'app.ico'};."])
command.append(str(root / "desktop.py"))
subprocess.run(command, cwd=root, check=True)
shutil.copy2(root / "dist" / "zz记.exe", root / "zz记.exe")
print(f"完成：{root / 'zz记.exe'}")
