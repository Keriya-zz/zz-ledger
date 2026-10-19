from pathlib import Path
import urllib.request, hashlib, zipfile, concurrent.futures
base=Path(__file__).resolve().parents[2]/'.qa/android-tools';base.mkdir(parents=True,exist_ok=True)
items=[('build-tools_r35_windows.zip','af059bb67cf7786f45ee0db85e2d24985df1b4b6','build-tools'),('platform-35_r02.zip','0bb560a90a7a2cbd0dd8348224d518b638fe7949','platform'),('platform-tools_r37.0.1-win.zip','e03e78b1d80b396f1c3358e31251cb31740e1110','platform-tools')]
def get(item):
    name,sha,folder=item;p=base/name
    if not p.exists(): urllib.request.urlretrieve('https://dl.google.com/android/repository/'+name,p)
    if hashlib.sha1(p.read_bytes()).hexdigest()!=sha: raise RuntimeError('SDK checksum mismatch: '+name)
    with zipfile.ZipFile(p) as z: z.extractall(base/folder)
    print('Ready:',folder,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(get,items))
