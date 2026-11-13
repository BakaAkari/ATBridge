# ATBridge

**在 Blender 里浏览 Fab / Megascans，下载后一键导入带材质的模型。** 同时提供 Quixel Bridge LiveLink 和一组常用的 ATools 工具。

[English](README.en.md) · [更新日志](CHANGELOG.md) · [问题反馈](https://github.com/BakaAkari/ATBridge/issues) · GitHub: [BakaAkari/ATBridge](https://github.com/BakaAkari/ATBridge) · Gitee 镜像: [baka-akari/ATBridge](https://gitee.com/baka-akari/ATBridge)

![Blender 4.2+](https://img.shields.io/badge/Blender-4.2%2B-orange) ![License LGPL-3.0](https://img.shields.io/badge/license-LGPL--3.0-blue)

> 0.5.0 目前为 Beta 版本。欢迎试用并反馈问题。

## 功能

| 功能 | 说明 | 平台 |
|---|---|---|
| Fab 独立浏览器 | 在 ATBridge 自带的窗口里登录 Fab、浏览 Megascans、下载资产；带下载面板，不需要安装浏览器扩展 | Windows |
| 资产收件区 | 自动发现下载好的资产 ZIP，显示名称、格式、贴图分辨率和商品预览图，一键导入到场景 | 全平台 |
| 本地 ZIP 导入 | 也可以从电脑上手动选择资产 ZIP 导入，不需要预先设置解压目录 | 全平台 |
| Quixel Bridge LiveLink | 接收 Quixel Bridge 的导出 | 全平台 |
| ATools 工具 | 一键切换中英文界面、模型清理、按集合重命名对象、导入图像为平面、快速物理模拟、时间轴工具 | 全平台 |

界面支持简体中文和英文，跟随 Blender 的界面语言。

## 系统要求

- Blender 4.2 或更高版本（已在 4.2 LTS 和 5.2 LTS 上测试）
- Fab 独立浏览器：Windows 10 / 11 x64，需要 Microsoft Edge WebView2 运行库（Windows 一般自带）
- macOS / Linux：除独立浏览器外的功能均可用；在系统浏览器里下载 Fab 资产后，用收件区或本地 ZIP 导入

## 安装

1. 在 [Releases](https://github.com/BakaAkari/ATBridge/releases)（或 Gitee 发行版）下载安装包：
   - Windows：`ATBridge_<版本>_windows-x64.zip`（包含独立浏览器）
   - macOS / Linux：`ATBridge_<版本>.zip`
2. Blender 中打开 **编辑 → 偏好设置 → 插件**，点右上角下拉菜单里的 **从磁盘安装…**，选择下载的 ZIP（不用解压）。
3. 勾选启用 **ATBridge**。

从旧版本升级：先在插件列表里移除旧版 ATBridge，重启 Blender，再安装新版本。

## 快速开始：导入 Fab 资产

1. 在 3D 视图按 `N` 打开侧栏，进入 **ATBridge → Fab 资产**。
2. 点 **浏览 Fab 资产**，在打开的窗口里登录 Fab，找到资产后下载 ZIP。首次使用需要登录，登录信息只保存在这个窗口里。
3. 下载完成后点 **返回 Blender**。资产会自动出现在收件区列表中，选中后可以查看预览和资产信息。
4. 点 **导入到场景**。

不用独立窗口也可以：在任意浏览器里下载 ZIP，然后在收件区选择，或点 **从电脑选择 ZIP…**。

### 支持的资产

支持含 Megascans 元数据的 Fab 资产 ZIP，格式可以是 FBX、OBJ 或 glTF：

| 类型 | 导入结果 |
| --- | --- |
| 3D 资产 | 模型和材质 |
| 植物 | 每个变体一个模型，沿 X 轴排开；叶片按不透明度镂空并透光 |
| 表面、贴花、图集、瑕疵 | 有选中物体时替换它的当前材质槽，否则新建一个按真实扫描尺寸的平面 |
| 笔刷 | 图像纹理和纹理绘制笔刷 |

- 模型只导入最高精度的 LOD0。LOD 用于游戏引擎，Blender 渲染用不到。
- 同一资产有多种分辨率时，默认最高使用 4K 贴图。
- 重新导入到已有材质时，你自己加的节点和连线会保留。

暂不支持：

- **Megascans 树木**（如 European Beech）：Fab 只提供 Unreal Engine 格式（`.uasset`），许可也限定在 UE 中使用，无法在 Blender 中导入。可以用 Blender 自带的 Sapling Tree Gen 或几何节点生成树干，再用 Megascans 的树皮表面和叶片图集制作材质。
- 只提供 Alembic（ABC）、USD 或 .blend 的包。
- 没有 Megascans 元数据的普通 ZIP，以及一个 ZIP 里有多个资产。

不支持的包默认不显示，可以在 **设置与其他入口** 里勾选 **显示不支持的 ZIP** 查看原因。

## Quixel Bridge LiveLink

1. 在 Quixel Bridge 中打开 **Edit → Export Settings**，**Export Target** 设为 **Custom Socket Export**，**Socket Port** 设为 **23333**。
2. 在 Bridge 里点导出，资产会进入当前 Blender 场景。

提示：**Models → LODs** 不要设为 **Highpoly Source**，否则贴图无法正确导入。首次安装建议先关闭 Bridge，装好插件并重启 Blender 后再打开 Bridge。

## 数据与隐私

| 数据 | 位置 |
|---|---|
| 独立浏览器的登录数据 | `%LOCALAPPDATA%\ATBridge\FabBrowser`（不读取你平时浏览器的 Cookie） |
| 商品预览图缓存 | `%LOCALAPPDATA%\ATBridge\Cache\Fab`（上限 256 MB，90 天过期） |
| 下载的 ZIP | 你设置的下载目录下的 `ATBridge\` 子目录 |
| 解压后的资产 | 插件设置里的解压目录；留空时使用 Blender 数据目录下的 `ATBridge/assets` |
| 导入记录 | Blender 配置目录下的 `ATBridge/imports.json`（最多 200 条） |

ATBridge 不会替你购买、领取资产或接受许可，这些操作都由你在 Fab 网站上自己完成。解压后的贴图被场景引用，请不要删除正在使用的资产目录。

## 常见问题

**点“浏览 Fab 资产”只打开了系统浏览器？** 你安装的是不含独立浏览器的通用包，或者当前系统不是 Windows。在 Windows 上请改装 `windows-x64` 安装包。

**下载完成了，但收件区里没有出现？** 确认下载目录设置和实际下载位置一致（插件偏好设置 → 下载目录）。独立窗口打开期间，下载目录会被锁定。如果包不受支持，需要勾选“显示不支持的 ZIP”才能看到它和原因。

**导入失败？** 先看收件区显示的原因。如果是不支持的格式，请在 Fab 下载 FBX 版本。仍然失败的话，请附上 Blender 版本、资产名称和报错信息[提交问题](https://github.com/BakaAkari/ATBridge/issues)。

## 声明

ATBridge 是个人开发的非官方插件，与 Epic Games、Fab、Quixel 没有关联。通过 ATBridge 下载和使用的资产，仍需遵守 Fab 的许可条款。

## 参与开发

从源码运行、热重载和测试见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)，发布流程见 [docs/RELEASING.md](docs/RELEASING.md)。

## 联系方式

- QQ 群：628731557
- 邮箱：exwww2000@qq.com

## 许可证

[LGPL-3.0](LICENSE)
