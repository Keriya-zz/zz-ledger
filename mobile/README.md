# zz记 Android 0.1.0 · 离线测试版

采用 A「古典账页」视觉：暖白背景、灰紫点缀、衬线金额和底部四栏导航。

## 安装与使用

安装包：`output/zzledger-0.1.0-android.apk`。适用于 Android 8.0（API 26）及以上；请保持 Android System WebView 更新。将 APK 传到手机打开，根据系统提示允许此次安装来源。

- 右下角「记一笔」：收入/支出、自定义分类、日期、备注，支持编辑与删除。
- 「账户」：添加/编辑账户、逐笔交易明细、账户间划转。
- 「待还款」：登记待还、部分/全部还款及还款记录。
- 「统计」：按月查看每日、分类和账户支出；划转不计入收支。
- 首页右上角「⋮」：导入与备份。导出时使用系统文件选择器保存 JSON；可在支持划转的 Windows 版导入。导入先校验并显示数量，确认后替换本机账本，不自动合并。

账本保存在 App 私有目录，支持离线使用。卸载 App 会删除其本地数据，请先导出备份。此版本没有登录、网络权限或云同步，不会实际执行银行转账。APK 不包含个人账本。

## 当前验证范围

已通过：共享金额计算与划转/还款测试、390×844 和 360×800 手机浏览器交互、保存失败回滚、重复提交保护、导入校验/确认/恢复、导出桥接模拟、APK 编译及 v2/v3 签名校验。另在 Xiaomi 15（Android 16）真机验证了安装、记录保存与重启持久化、系统文件选择器导出 JSON、重新导入该 JSON，以及测试后恢复原始账本。

尚未全面覆盖：不同品牌手机上的系统文件选择器、键盘与返回手势适配。导入个人账本前，建议先导出当前手机账本留作备份。

这是采用本地开发密钥签署的首版测试 APK，不是应用商店正式发布包。后续本地更新需保留 `.qa/android-test.keystore` 并保持应用 ID；不要将密钥提交到 GitHub。

## 构建

Windows + JDK 17+ + Python 3.9+：从项目根目录运行：

```powershell
python mobile/scripts/download_tools.py
python mobile/scripts/build_apk.py
```

工具从 Google 官方地址下载到 `.qa/android-tools` 并按官方仓库 SHA-1 校验。已有 SDK 可设置 `ZZ_ANDROID_BUILD_TOOLS` 和 `ZZ_ANDROID_PLATFORM`，分别指向含 aapt2 的目录与含 android.jar 的平台目录。构建使用 aapt2、javac、D8、zipalign 和 apksigner；无 Gradle 或大型 UI 框架依赖。APK 生成在 `mobile/output/`。

`web/` 为移动端样式、UI 适配和原生接口；`app/src/main/java/` 为本地 WebView 外壳。`prepare_assets.py` 复制共享的 `ui/core.js`、记账交互与页面，再应用手机布局及存储适配；生成资源不提交，Windows 源文件不受影响。

原生侧只加载打包的 HTTPS 虚拟域资源，禁止远程页面和跨域请求。保存使用 Android AtomicFile，另保留上一版账本。导入采用系统文档选择器并限制 10 MB；导出由用户选择位置。

## 页面回归

```powershell
$env:CHROME_BIN='你的 Chrome.exe 完整路径'
python tests/ui_regression.py --mobile --preview-view home --reference-a-fixture
```

测试使用独立样例账本，通过 CDP 手机视口运行；原生存储桥接由隔离测试服务模拟，不等同于真机测试。
