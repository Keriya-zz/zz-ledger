# zz记 iOS 0.1.0 · 个人使用开发版

面向 iOS 16 及以上的 iPhone。沿用原项目的移动端设计、以整数分计金额的记账逻辑和 version 1 JSON 备份格式；使用 Swift、UIKit 和 WKWebView 提供本机文件保存、系统文件选择器与安全区域适配。所有界面资源随 App 打包，记账无需联网。

**当前交付是 iOS 源码工程，尚未完成 iOS SDK 编译、签名或真机验证，不包含可直接安装的 IPA。** 开发机器只有 Command Line Tools，没有完整 Xcode。下列桌面测试与浏览器测试不能替代真机验收。

## 安装到自己的 iPhone

1. 在 Mac 的 App Store 安装 **Xcode**，打开一次并按提示安装 iOS 开发组件。需要使用支持你手机系统版本的 Xcode。
2. 保持整个项目文件夹完整，双击 `ios/ZZLedger.xcodeproj`。不需要安装 CocoaPods、Node.js 或其他 App 框架。
3. 在 **Xcode → Settings → Apple Accounts** 登录自己的 Apple 账户。
4. 选中项目中的 **ZZLedger** target，打开 **Signing & Capabilities**，勾选 **Automatically manage signing**，在 **Team** 选择自己的 **Personal Team**。
5. 如果提示 Bundle Identifier 被占用，把 `com.keriya.zzledger.ios` 改为你自己的唯一标识，例如 `com.yourname.zzledger.personal`。以后更新应保持这个标识和 Team 不变。
6. 用数据线连接、解锁 iPhone，并点击手机上的“信任”。按 Xcode 提示在 iPhone **设置 → 隐私与安全性 → 开发者模式**中启用开发者模式，按提示重启。
7. 在 Xcode 顶部运行设备中选择自己的 iPhone，点击 **▶ Run**。首次构建会自动生成手机界面资源，然后编译、签名并安装。
8. 首次打开如提示信任开发者，按系统指引到 **设置 → 通用 → VPN 与设备管理**确认自己的开发者账户。

个人设备测试可以使用免费的 Apple 账户。免费 Personal Team 的描述文件在签发后 **7 天**过期，届时需连接 Mac，用同一 Team 和 Bundle Identifier 重新运行安装；不要为了续签先删除 App，删除会清除本机账本。详见 [Apple 个人开发账户说明](https://developer.apple.com/help/account/basics/about-your-developer-account/)和[在设备上运行 App](https://developer.apple.com/documentation/xcode/running-your-app-on-simulated-or-physical-devices)。

如果 Xcode 提示缺少 Web 资源，在项目根目录运行 `python3 ios/scripts/prepare_assets.py` 后重新构建。构建阶段也会自动执行该脚本。若使用命令行构建，需要让 `DEVELOPER_DIR` 指向完整 Xcode。

## 使用与转移账本

- **总览**：总余额、当日/月支出、每日账单、搜索和 CSV 导出。
- **记一笔**：收入、支出、自定义分类、日期、备注；支持编辑、删除和余额同步更新。
- **账户**：账户管理、交易明细、账户间划转。划转不计入收支。
- **待还款**：登记欠款、部分还款、全部还款与历史记录。
- **统计**：月度收支、每日开销、分类和账户支出。
- **右上角 ⋮**：导入 JSON 账本或导出备份，可通过系统“文件”保存到“我的 iPhone”或已启用的文件提供商。

把电脑或 Android 导出的 JSON 备份放到 iPhone 的“文件”中，在 App 里选择导入，核对数量后点“替换并导入”。导入会替换本机账本，不会合并。含划转记录的备份应使用支持划转的其他端版本读取。

App 没有账户登录或自动跨设备同步。选择 iCloud Drive 存放导出的备份，仅代表保存了一个文件，不会自动同步正在使用的账本。

## 数据保存

- 本机账本位于 App 沙盒的 `Library/Application Support/ZZLedger/ledger.json`。
- 每次修改先校验，再在串行队列写入；原子替换成功后界面才更新。失败会保留原状态并提示。
- 保存前保留 `ledger.previous.json`。恢复结构损坏的文件时另保留 `ledger.recovered-original.json`，不覆盖有效的上一版。
- 本机账本使用 iOS 文件保护；短时间切到后台时申请时间完成正在进行的文件操作。
- 导入和保存上限为 10 MB；取消文件选择或取消导入确认都不会改动当前账本。
- 自动上一版保存在 App 私有目录，不能直接从“文件”浏览。日常恢复应使用自己导出的备份；必要时开发者可从 Xcode 下载 App 容器取出自动备份。
- 卸载会删除本地数据，请先导出备份。App 初次运行只创建零余额默认账户，不包含个人账本或测试数据。

## 验证与尚待完成的项目

本次已完成：

- 共享 JavaScript 记账、还款、划转、分类及账户统计测试。
- iOS Promise 桥接测试：请求内容、原生失败、取消导出、取消导入及等待磁盘确认。
- Foundation 存储与资源路径的 7 组测试：首次启动、重启读取、上一版备份、失败保护、损坏文件恢复、大小/编码限制、导出文件名及资源路径限制。
- 原有 Python 16 项测试（Python 3.12）。
- 375×667、393×852 和 852×393 浏览器测试：真实共享界面配合模拟的 WebKit 桥，覆盖记账、编辑/删除、划转、还款、重复提交、保存失败回滚、原生导入确认、导出和横向溢出检查。
- Swift 源码语法检查、Xcode 工程及 plist 结构检查。

仍需安装 Xcode 后完成：完整 iOS 编译；模拟器与 iPhone 上的 WKWebView、系统文件选择器、键盘、旋转、锁屏保存、前后台切换、重启持久化和签名安装。仓库附带的 GitHub Actions 构建工作流尚未在远端运行。

## 开发与测试命令

以下命令从项目根目录运行。

```sh
python3 ios/scripts/prepare_assets.py
node core.test.cjs
node tests/debts.test.cjs
node tests/transfers.test.cjs
node tests/categories.test.cjs
node tests/account-expenses.test.cjs
node tests/ios_bridge.test.cjs
swift test --package-path ios
```

如果只有 Command Line Tools、没有 XCTest，可执行 `python3 ios/scripts/test_core.py`，它使用同一组测试方法验证 Foundation 部分。这不编译 iOS App。

```sh
# 需要 Python 3.10+ 与 Chrome；只使用隔离样例账本
CHROME_BIN='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
  python3 tests/ui_regression.py --ios --preview-view home

# 需要完整 Xcode；无需签名的模拟器构建
DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer \
  xcodebuild -project ios/ZZLedger.xcodeproj -scheme ZZLedger \
  -configuration Debug -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath ios/build CODE_SIGNING_ALLOWED=NO build
```

`ios/scripts/create_project.py` 可重新生成初始工程和沿用 Android 图形的图标。通常只需打开已提供的工程；重新生成会覆盖手工修改的工程设置。共享网页由 `ui/`、`mobile/web/` 和 `ios/web/` 生成到 `ios/ZZLedger/Web/`，不要直接修改生成资源。
