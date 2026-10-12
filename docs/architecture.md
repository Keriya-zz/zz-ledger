# zz记架构与技术流程

软件沿用 Python + pywebview + WebView2，界面使用原生 HTML、CSS、JavaScript。用户运行 EXE 无需安装 Node.js；Node.js 仅用于验证金额与记账逻辑。

## 模块职责

| 模块 | 职责 |
| --- | --- |
| `desktop.py` | 薄启动入口 |
| `zzledger/application.py` | 参数、资源目录、单实例锁、窗口与服务生命周期 |
| `zzledger/window.py` | 最小化、最大化、还原、关闭 |
| `zzledger/domain.py` | 账本格式与数据校验 |
| `zzledger/storage.py` | 原子写入、上一版备份、导出 |
| `zzledger/server.py` | 仅本机可访问的界面资源与带令牌的文件接口 |
| `ui/core.js` | 以整数分为单位的收支计算及账本状态转换 |
| `ui/api.js` | 异步文件请求和原生窗口桥接 |
| `ui/app.js` | 页面渲染、事件与提交状态 |
| `ui/debts.js` | 待还款明细、状态筛选及还款表单 |
| `ui/styles/` | 基础变量、布局、组件、窗口及视觉细节 |
| `ui/icons.js` | 共用矢量线条图标，不依赖在线字体或图片 |

## 一笔记录如何保存

```mermaid
flowchart LR
  A[输入金额与账户] --> B[core.js 生成新状态]
  B --> C[api.js 异步请求]
  C --> D[本机接口校验令牌]
  D --> E[domain.py 校验账本]
  E --> F[storage.py 写入临时文件]
  F --> G[保留上一版并原子替换账本]
  G --> H[保存成功后更新页面]
```

每次金额变更先生成新状态，写入成功后才替换页面中的状态。请求期间阻止重复提交，保存失败显示错误并保留原账本。同步 XMLHttpRequest 已移除，磁盘请求不会阻塞界面线程。

标题栏使用浅紫色自定义界面，原生窗口启用无边框模式。只有标题栏的中间区域可拖动；窗口按钮通过 pywebview 调用原生控制。页面内容独立滚动，标题栏和侧边栏保持固定。

样式由 `tokens.css`、`layout.css`、`components.css`、`debts.css` 四层管理，旧的叠加主题已移除。暖白和灰紫构成基础色，金额使用深色文字，仅总额卡片使用深灰紫；细边框与间距建立层次。详细色彩、排版、间距及交互规则见[设计规范](design-system.md)。还款明细在大窗口显示三列，普通桌面显示两列，窄窗口显示一列。

## 数据与兼容性

继续使用 version 1 的 JSON 账本格式，金额以整数分存储。程序启动后读取 EXE 同目录的 `账本.json`，写入时保留 `账本.上一版.json`。升级替换 EXE 即可，账本文件无需迁移。界面资源随软件打包，未恢复独立网页版。

待还款保存在可选 `debts` 数组中，旧账本缺少此字段时按空列表显示。每笔明细记录应还总额；实际还款是分类为「还款」、带 `debtId` 的支出账单。剩余金额由应还总额减去关联账单金额计算，避免重复维护两个金额。编辑、撤销账单会同时更新账户余额和待还状态；JS 与 Python 均校验关联和超额还款。待还款不从首页账户总余额中扣减。

## 验证与打包

```powershell
node core.test.cjs
node tests/debts.test.cjs
python -m unittest discover -s tests
.\.desktop-venv\Scripts\python.exe build_desktop.py
```

打包脚本整体收集 `ui/`，新增样式或界面模块时无需逐个修改资源列表。软件支持内部启动验证参数，必须配合独立数据目录，避免测试写入日常账本：

```powershell
.\zz记.exe --smoke-test --data-dir "E:\codex\记账\.qa\smoke-test"
```

`tests/ui_regression.py` 使用隔离示例账本验证异步提交、重复提交、跨账户编辑、删除、保存失败回滚及导出，并生成宽屏和小窗口截图。运行前将 `CHROME_BIN` 环境变量设为本机 Chrome 可执行文件路径：

```powershell
$env:CHROME_BIN = '你的Chrome可执行文件完整路径'
python tests/ui_regression.py
```

测试文件与截图生成到 `.qa/`，不会使用日常账本。
