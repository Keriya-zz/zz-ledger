"""Regenerate a dependency-free Xcode project and icons matching the Android vector."""
from pathlib import Path
import hashlib
import json
import struct
import zlib

IOS = Path(__file__).resolve().parents[1]


def ident(name):
    return hashlib.sha256(name.encode()).hexdigest()[:24].upper()


def create_project():
    objects = []
    def add(name, value):
        objects.append(f'{ident(name)} = {{ {value} }};')
        return ident(name)
    def refs(names):
        return '(' + ', '.join(ident(n) for n in names) + ',)'
    sources = ['AppDelegate.swift', 'LedgerViewController.swift', 'LocalSchemeHandler.swift',
               'Core/LedgerStore.swift', 'Core/BundledResource.swift']
    resources = [('Web', 'folder'), ('Assets.xcassets', 'folder.assetcatalog'),
                 ('PrivacyInfo.xcprivacy', 'text.xml')]
    for path in sources:
        add(path, f'isa = PBXFileReference; lastKnownFileType = sourcecode.swift; path = "{path}"; sourceTree = "<group>";')
        add('build-' + path, f'isa = PBXBuildFile; fileRef = {ident(path)};')
    for path, kind in resources:
        add(path, f'isa = PBXFileReference; lastKnownFileType = {kind}; path = "{path}"; sourceTree = "<group>";')
        add('build-' + path, f'isa = PBXBuildFile; fileRef = {ident(path)};')
    add('Info.plist', 'isa = PBXFileReference; lastKnownFileType = text.plist.xml; path = Info.plist; sourceTree = "<group>";')
    add('app', 'isa = PBXFileReference; explicitFileType = wrapper.application; path = ZZLedger.app; sourceTree = BUILT_PRODUCTS_DIR;')
    add('group-app', f'isa = PBXGroup; path = ZZLedger; sourceTree = "<group>"; children = {refs(sources + [p for p, _ in resources] + ["Info.plist"])};')
    add('products', f'isa = PBXGroup; name = Products; sourceTree = "<group>"; children = {refs(["app"])};')
    add('root', f'isa = PBXGroup; sourceTree = "<group>"; children = {refs(["group-app", "products"])};')
    add('sources', f'isa = PBXSourcesBuildPhase; buildActionMask = 2147483647; files = {refs(["build-" + p for p in sources])}; runOnlyForDeploymentPostprocessing = 0;')
    add('resources', f'isa = PBXResourcesBuildPhase; buildActionMask = 2147483647; files = {refs(["build-" + p for p, _ in resources])}; runOnlyForDeploymentPostprocessing = 0;')
    add('frameworks', 'isa = PBXFrameworksBuildPhase; buildActionMask = 2147483647; files = (); runOnlyForDeploymentPostprocessing = 0;')
    command = '/usr/bin/python3 "$SRCROOT/scripts/prepare_assets.py"\n'
    add('prepare', 'isa = PBXShellScriptBuildPhase; alwaysOutOfDate = 1; buildActionMask = 2147483647; files = (); inputPaths = (); name = "Prepare bundled UI"; outputPaths = ("$(SRCROOT)/ZZLedger/Web/index.html",); runOnlyForDeploymentPostprocessing = 0; shellPath = /bin/sh; shellScript = ' + json.dumps(command) + ';')
    for name in ['Debug', 'Release']:
        common = 'CLANG_ENABLE_MODULES = YES; CLANG_ENABLE_OBJC_ARC = YES; SDKROOT = iphoneos; IPHONEOS_DEPLOYMENT_TARGET = 16.0; SWIFT_VERSION = 5.0; ENABLE_USER_SCRIPT_SANDBOXING = NO;'
        mode = 'SWIFT_OPTIMIZATION_LEVEL = "-Onone"; DEBUG_INFORMATION_FORMAT = dwarf; SWIFT_ACTIVE_COMPILATION_CONDITIONS = DEBUG; ONLY_ACTIVE_ARCH = YES;' if name == 'Debug' else 'SWIFT_OPTIMIZATION_LEVEL = "-O"; DEBUG_INFORMATION_FORMAT = "dwarf-with-dsym"; SWIFT_COMPILATION_MODE = wholemodule;'
        add('project-' + name, f'isa = XCBuildConfiguration; name = {name}; buildSettings = {{ {common} {mode} }};')
        add('target-' + name, f'''isa = XCBuildConfiguration; name = {name}; buildSettings = {{
            PRODUCT_NAME = "$(TARGET_NAME)"; PRODUCT_BUNDLE_IDENTIFIER = com.keriya.zzledger.ios;
            INFOPLIST_FILE = ZZLedger/Info.plist; GENERATE_INFOPLIST_FILE = NO;
            MARKETING_VERSION = 0.1.0; CURRENT_PROJECT_VERSION = 1;
            CODE_SIGN_STYLE = Automatic; TARGETED_DEVICE_FAMILY = 1;
            SUPPORTED_PLATFORMS = "iphoneos iphonesimulator"; SUPPORTS_MACCATALYST = NO;
            ASSETCATALOG_COMPILER_APPICON_NAME = AppIcon;
            LD_RUNPATH_SEARCH_PATHS = "$(inherited) @executable_path/Frameworks";
        }};''')
    for prefix in ['project', 'target']:
        add(prefix + '-configs', f'isa = XCConfigurationList; buildConfigurations = {refs([prefix + "-Debug", prefix + "-Release"])}; defaultConfigurationIsVisible = 0; defaultConfigurationName = Release;')
    add('target', f'''isa = PBXNativeTarget; name = ZZLedger; productName = ZZLedger;
        productType = "com.apple.product-type.application"; productReference = {ident('app')};
        buildConfigurationList = {ident('target-configs')};
        buildPhases = {refs(['prepare', 'sources', 'frameworks', 'resources'])}; buildRules = (); dependencies = ();''')
    add('project', f'''isa = PBXProject; attributes = {{ LastUpgradeCheck = 1600; TargetAttributes = {{ {ident('target')} = {{ CreatedOnToolsVersion = 16.0; }}; }}; }};
        buildConfigurationList = {ident('project-configs')}; compatibilityVersion = "Xcode 14.0";
        developmentRegion = "zh-Hans"; knownRegions = ("zh-Hans", en, Base,);
        mainGroup = {ident('root')}; productRefGroup = {ident('products')};
        projectDirPath = ""; projectRoot = ""; targets = {refs(['target'])};''')
    project = IOS / 'ZZLedger.xcodeproj'
    project.mkdir(exist_ok=True)
    (project / 'project.pbxproj').write_text('// !$*UTF8*$!\n{ archiveVersion = 1; classes = {}; objectVersion = 56; objects = {\n' + '\n'.join(objects) + '\n}; rootObject = ' + ident('project') + '; }\n')
    scheme = project / 'xcshareddata/xcschemes'
    scheme.mkdir(parents=True, exist_ok=True)
    reference = f'<BuildableReference BuildableIdentifier="primary" BlueprintIdentifier="{ident("target")}" BuildableName="ZZLedger.app" BlueprintName="ZZLedger" ReferencedContainer="container:ZZLedger.xcodeproj"/>'
    (scheme / 'ZZLedger.xcscheme').write_text(f'''<?xml version="1.0" encoding="UTF-8"?>
<Scheme LastUpgradeVersion="1600" version="1.3">
  <BuildAction parallelizeBuildables="YES" buildImplicitDependencies="YES"><BuildActionEntries><BuildActionEntry buildForTesting="YES" buildForRunning="YES" buildForProfiling="YES" buildForArchiving="YES" buildForAnalyzing="YES">{reference}</BuildActionEntry></BuildActionEntries></BuildAction>
  <TestAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" shouldUseLaunchSchemeArgsEnv="YES"><Testables/></TestAction>
  <LaunchAction buildConfiguration="Debug" selectedDebuggerIdentifier="Xcode.DebuggerFoundation.Debugger.LLDB" selectedLauncherIdentifier="Xcode.IDEFoundation.Launcher.LLDB" launchStyle="0" useCustomWorkingDirectory="NO" ignoresPersistentStateOnLaunch="NO" debugDocumentVersioning="YES" allowLocationSimulation="YES"><BuildableProductRunnable runnableDebuggingMode="0">{reference}</BuildableProductRunnable></LaunchAction>
  <ProfileAction buildConfiguration="Release" shouldUseLaunchSchemeArgsEnv="YES" useCustomWorkingDirectory="NO" debugDocumentVersioning="YES"><BuildableProductRunnable runnableDebuggingMode="0">{reference}</BuildableProductRunnable></ProfileAction>
  <AnalyzeAction buildConfiguration="Debug"/>
  <ArchiveAction buildConfiguration="Release" revealArchiveInOrganizer="YES"/>
</Scheme>
''')


def create_icons():
    # Rasterize the existing Android vector paths, not a new branding design.
    polygon = [(42, 39), (69, 39), (69, 44), (50, 67), (70, 67), (70, 73),
               (41, 73), (41, 68), (60, 45), (42, 45)]
    def inside(x, y):
        result = False
        for i, (ax, ay) in enumerate(polygon):
            bx, by = polygon[i - 1]
            if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                result = not result
        return result
    def png(size):
        pixels = bytearray()
        for row in range(size):
            pixels.append(0)
            y = (row + .5) * 108 / size
            for col in range(size):
                x = (col + .5) * 108 / size
                color = (48, 33, 57)
                if 25 <= x < 83 and 24 <= y < 85: color = (239, 231, 244)
                if 25 <= x < 34 and 24 <= y < 85: color = (146, 122, 165)
                if inside(x, y): color = (80, 53, 94)
                pixels.extend(color)
        def chunk(kind, data):
            return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data) & 0xffffffff)
        return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(pixels, 9)) + chunk(b'IEND', b'')
    assets = IOS / 'ZZLedger/Assets.xcassets'
    out = assets / 'AppIcon.appiconset'
    out.mkdir(parents=True, exist_ok=True)
    (assets / 'Contents.json').write_text(json.dumps({'info': {'author': 'xcode', 'version': 1}}, indent=2) + '\n')
    images = []
    for points, scales, idiom in [(20, [2, 3], 'iphone'), (29, [2, 3], 'iphone'),
                                  (40, [2, 3], 'iphone'), (60, [2, 3], 'iphone'),
                                  (1024, [1], 'ios-marketing')]:
        for scale in scales:
            filename = f'icon-{points}@{scale}x.png'
            (out / filename).write_bytes(png(points * scale))
            images.append({'size': f'{points}x{points}', 'idiom': idiom, 'filename': filename, 'scale': f'{scale}x'})
    (out / 'Contents.json').write_text(json.dumps({'images': images, 'info': {'author': 'xcode', 'version': 1}}, indent=2) + '\n')


if __name__ == '__main__':
    create_project()
    create_icons()
    print(IOS / 'ZZLedger.xcodeproj')
