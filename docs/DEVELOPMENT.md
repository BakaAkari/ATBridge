# ATBridge 开发说明

面向贡献者与本地测试；用户文档见仓库根目录 README。

## 从源码运行（Windows）

使用本机 Blender 从源码启动独立测试窗口：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1
```

脚本优先使用 PATH 中的 Blender，否则读取 `.blend` 文件关联。也可加 `-BlenderPath "D:\path\to\blender.exe"` 指定版本。使用默认场景和临时首选项，不安装或更新用户插件；修改 Python 源码后点击面板中的“重载插件 · 开发模式”，或按 F3 搜索“ATBridge 重载插件”，无需重启 Blender。不要在测试窗口中手动保存首选项。

已打开的旧测试窗口可在 Python Console（Shift+F4）执行一次：

```python
import runpy; runpy.run_path(r"<仓库路径>\scripts\dev_reload.py", run_name="__main__")
```

然后 Shift+F5 返回 3D 视图。之后使用重载按钮即可。热重载保留场景、选择和插件首选项，收件区重新扫描；物理模拟或 LiveLink 活动期间拒绝重载。C# 独立浏览器更新需关闭浏览器窗口再打开，Blender 不必退出。

现在可以完全不安装浏览器扩展。3D 视图侧栏 **ATBridge → Fab 资产** 的主按钮是 **浏览 Fab 资产**，打开独立 WebView2 窗口并直达 [Quixel Megascans](https://www.fab.com/sellers/Quixel)；重复点击会唤回本次 Blender 会话启动的窗口。普通浏览器入口放在折叠的“设置与其他入口”中。首次需构建窗口程序：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-browser.ps1
```

本机开发构建使用 .NET 10 SDK；运行需要 .NET 10 Windows Desktop Runtime 和 WebView2 Runtime，本机已具备。也可加 `-SelfContained` 打包 .NET 运行时。构建输出位于 `dist/fab-browser/<构建时间>/`，`current.txt` 指向最新构建，避免更新正在运行的程序。它是 Windows 实验工具，尚未制作发行安装包。

下载完成后，Blender 后台每两秒检查所选目录及其 ATBridge 下载子目录，自动识别最近 20 个非空 ZIP。选择资产后可查看名称、格式、分辨率、大小及包内预览，点击 **导入到场景**。优先显示独立窗口缓存的 Fab 商品图；没有商品图缓存时读取包内元数据声明的真实预览，不使用基础色贴图替代，也不本地渲染。无须手动刷新，也可使用 **从电脑选择 ZIP…**。不支持的包默认隐藏，可在设置中显示并查看原因；元数据识别不保证后续模型导入一定成功。

两个导入入口共享结果反馈；导入记录保存在 Blender CONFIG/ATBridge/imports.json，最多 200 条。“曾导入过”仅表示历史，不代表当前场景仍有该资产。再次导入会创建副本，成功后可选中并查看新增对象。列表刷新保留选择，支持按名称搜索。原生模型导入同步执行，大包期间会显示忙碌光标，暂不支持中途取消。普通浏览器的自定义下载目录需在设置中匹配；独立窗口打开期间目录锁定，关闭后可更改。

独立窗口保留自己的登录数据（`%LOCALAPPDATA%/ATBridge/FabBrowser`），不读取普通浏览器的 Cookie。ZIP 写到所选下载目录的 `ATBridge/<下载编号>/` 下，完成前使用 `.partial` 后缀，不会提前出现在导入列表。每个下载有进度、取消、完成定位和中断后回来源页入口；任务记录保留在当前窗口。用户关闭窗口前会确认取消未完成下载；网页请求关闭弹窗则等待其下载结束。残留的 `.partial` 文件可自行清理。当前只接收 ZIP；它不会自动购买、领取、接受许可或导入场景。网站中的登录、验证及许可操作由用户处理。

商品图专用缓存位于 %LOCALAPPDATA%/ATBridge/Cache/Fab：images 保存最长边 512 像素的 PNG，assets 保存资产 ID 与商品页的关联记录。文件名使用哈希，不写入下载目录、ZIP 或解压缓存。上限 256 MiB，图片 90 天过期；浏览商品时，超过 7 天的缓存会重新获取。中断写入的临时缓存超过一天后清理。

独立窗口只读取当前 Fab 商品页公开的主图和包名，按 ZIP 元数据的资产 ID 精确关联，只从 media.fab.com 获取公开图片，不携带浏览器 Cookie。已下载的资产可在独立窗口重新浏览对应商品页补齐商品图；必要时展开该商品的文件列表，选择 **更多 → 补齐当前商品图**。Blender 自动发现缓存变化。“打开商品图缓存”可以查看缓存位置。

浏览器采用深色导航与可收起的下载面板：无任务时让网页占满；第一笔下载自动展开一次，主动收起后不会因后续下载重复打开。宽窗口右侧分栏，窄窗口覆盖显示。导航提供后退/前进、刷新/停止、Megascans 入口、实际来源地址；点击地址复制完整网址。支持 Alt+左右键、Ctrl+R / F5、Esc 停止加载、Ctrl+J 切换下载面板。

任务卡显示真实接收进度，未知总大小只显示已接收量。ZIP 保存成功后显示“ZIP 已保存”；商品图和资产名在元数据校验关联后补齐，缺图不阻止导入。“返回 Blender”只唤回启动此浏览器的原 Blender 进程，不自动导入；没有关联、原进程退出或 Windows 拒绝焦点切换时会说明原因。中断/取消可回来源商品页重新下载；“清除已结束记录”只清除窗口记录，不删除 ZIP。技术详情及文件路径默认折叠。

### 本轮 UI 重构实测

1. 等待当前下载结束，关闭旧 Fab 浏览器窗口；在开发测试 Blender 点击 **重载插件 · 开发模式**（或 F3 搜索 **ATBridge 重载插件**），再点 **浏览 Fab 资产**。更新原生浏览器不需要退出 Blender 或丢弃场景。
2. 确认直接进入 Quixel，空下载面板默认收起；试后退/前进、刷新、下载面板开关与窄窗口布局。
3. 下载一个 ZIP，再尝试并发下载、取消、手动收起面板；确认后续任务不抢焦点或反复展开面板。完成状态应是 **ZIP 已保存**。
4. 点 **返回 Blender**，确认回到原窗口；检查资产列表和商品图，再手动导入。多开 Blender 时尤其检查返回目标。
5. 清除结束记录后确认磁盘 ZIP 仍在；移动一个已完成 ZIP 后，其他任务和商品图仍能正常更新。

本轮为本地测试候选构建。真实 Fab 登录/下载、跨显示器 DPI 切换及用户场景下的导入体验仍需实测；这些确认后再准备对外 Beta 包。

### 界面语言

目前提供简体中文和英文。Blender 资产面板跟随 Blender 界面语言，关闭“翻译界面”时使用英文；系统默认语言按 Blender 实际解析结果处理。其他未提供翻译的语言回退英文，不会再把法语、日语等误判为中文。中文地区/脚本变体暂使用简体中文文案。

独立浏览器由 Blender 启动时接收它的界面语言；直接启动时跟随 Windows。也可用 `--language en-US` 或 `--language zh-CN` 指定语言。Blender 面板会随语言切换更新；已打开的独立浏览器保持启动时的语言，关闭后重新从 Blender 打开即可切换。Fab 官网内容由网站管理，ATBridge 不强制改写网站语言。

共享界面词条位于 `locales/fab.en.json`，原生程序构建时嵌入主程序集。商品名称、文件名、路径和底层技术错误保留原文；数量、进度与消息参数不作为翻译内容替换。自动扫描保存原始状态，显示时再按当前语言翻译，不需要为切换语言重新扫描资产。

解压目录留空时自动使用 Blender 数据目录；设置自定义解压目录仍然有效。支持包含 Megascans 元数据的 FBX / OBJ 模型或材质资产包（当前本地 ZIP 路径不支持 ABC），ZIP 改名不影响识别；不支持任意 Fab ZIP 或一个 ZIP 中多个资产的元数据。材质和贴图依赖解压后的文件，请勿删除正在使用的缓存。

Chrome 扩展伴随方案已在 0.5.0 移除，原实现见标签 `archive/chrome-companion`。

本地回归命令：

```powershell
python -m unittest discover -s tests -p 'test_*.py'
powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1 -SmokeTest
powershell -ExecutionPolicy Bypass -File .\scripts\start-dev.ps1 -LocalSmokeTest
python tests/browser_probe.py
```

Windows / Blender 5.2.3 LTS 已通过回归（2026-11-11）；原生 WebView2 本地 HTTP 夹具验证弹窗自关闭、ZIP 下载、同名文件隔离及重启后的测试 Cookie 保留。用户已在实际独立窗口完成 Fab 登录和 ZIP 下载；同一份 Historic Gemstone Mineral Sodalite Stone Hard 02 Low 包（7,452,171 字节）通过新下载列表入口在后台 Blender 成功导入：1 个网格、500 顶点、996 面，5 张 1024×1024 材质图像均已加载。测试未改动用户当前场景，未验证渲染效果或所有登录方式。后续下载中弹窗关闭的生命周期修复另经本地原生夹具验证。

## 发布

见 [RELEASING.md](RELEASING.md)。
