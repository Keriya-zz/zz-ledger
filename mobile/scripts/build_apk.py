"""Build a local signed test APK with official Android SDK tools and JDK 17+."""
from pathlib import Path
import os, re, shutil, subprocess, zipfile, sys
from prepare_assets import prepare
ROOT=Path(__file__).resolve().parents[2]
def run(args):
    print('>',Path(str(args[0])).name,flush=True)
    subprocess.run([os.path.relpath(a,ROOT) if isinstance(a,Path) and a.is_relative_to(ROOT) else str(a) for a in args],check=True,cwd=ROOT)
def main():
    assets=prepare()
    java=shutil.which('java')
    if not java: raise SystemExit('JDK 17+ is required')
    info=subprocess.run([java,'-XshowSettings:properties','-version'],capture_output=True).stderr.decode(errors='replace')
    home=Path(re.search(r'java.home = (.+)',info).group(1).strip())
    tools=Path(os.environ.get('ZZ_ANDROID_BUILD_TOOLS',ROOT/'.qa/android-tools/build-tools/android-15'))
    platform=Path(os.environ.get('ZZ_ANDROID_PLATFORM',ROOT/'.qa/android-tools/platform/android-35'))
    android=platform/'android.jar'
    if not android.exists() or not (tools/'aapt2.exe').exists(): raise SystemExit('Run mobile/scripts/download_tools.py first, or set ZZ_ANDROID_BUILD_TOOLS / ZZ_ANDROID_PLATFORM')
    build=ROOT/'mobile/build';build.mkdir(exist_ok=True)
    generated=build/'generated';generated.mkdir(exist_ok=True)
    classes=build/'classes';classes.mkdir(exist_ok=True)
    dex=build/'dex';dex.mkdir(exist_ok=True)
    src=ROOT/'mobile/app/src/main'
    run([tools/'aapt2.exe','compile','--dir',src/'res','-o',build/'resources.zip'])
    manifest=build/'AndroidManifest.xml'
    text=(src/'AndroidManifest.xml').read_text(encoding='utf-8-sig')
    if '--debug' in sys.argv: text=text.replace('<application ', '<application android:debuggable="true" ')
    manifest.write_text(text,encoding='utf-8')
    run([tools/'aapt2.exe','link','-I',android,'--manifest',manifest,'--java',generated,'--min-sdk-version','26','--target-sdk-version','35','-A',assets,'-o',build/'unsigned.apk',build/'resources.zip'])
    sources=list((src/'java').rglob('*.java'))+list(generated.rglob('*.java'))
    for source in sources: source.write_text(source.read_text(encoding='utf-8-sig'),encoding='utf-8')
    run([home/'bin/javac.exe','-encoding','UTF-8','-source','8','-target','8','-classpath',android,'-d',classes,*sources])
    run([home/'bin/java.exe','-cp',tools/'lib/d8.jar','com.android.tools.r8.D8','--lib',android,'--min-api','26','--output',dex,*classes.rglob('*.class')])
    with zipfile.ZipFile(build/'unsigned.apk','a',compression=zipfile.ZIP_DEFLATED) as apk:
        for file in dex.glob('*.dex'): apk.write(file,file.name)
    run([tools/'zipalign.exe','-f','-p','4',build/'unsigned.apk',build/'aligned.apk'])
    key=ROOT/'.qa/android-test.keystore'
    if not key.exists(): run([home/'bin/keytool.exe','-genkeypair','-keystore',key,'-storepass','android','-keypass','android','-alias','androiddebugkey','-keyalg','RSA','-keysize','2048','-validity','10000','-dname','CN=zzLedger Development,O=zzLedger,C=CN'])
    out=ROOT/'mobile/output';out.mkdir(exist_ok=True)
    apk=out/('zzledger-0.1.0-debug.apk' if '--debug' in sys.argv else 'zzledger-0.1.0-android.apk')
    run([home/'bin/java.exe','-jar',tools/'lib/apksigner.jar','sign','--ks',key,'--ks-pass','pass:android','--key-pass','pass:android','--out',apk,build/'aligned.apk'])
    run([home/'bin/java.exe','-jar',tools/'lib/apksigner.jar','verify','--verbose',apk])
    print('APK:',apk)
if __name__=='__main__':main()
