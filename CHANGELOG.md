# 更新日志 / Changelog

版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。1.0 之前，新增功能和不兼容变更都升次版本号。

## [0.5.0-beta.1] - 未发布

### 新增
- **Fab 独立浏览器（Windows）**：在 ATBridge 自带的 WebView2 窗口里登录 Fab、浏览 Megascans 并下载，不需要浏览器扩展。带下载面板（进度、取消、中断后回到商品页）、商品预览图缓存和“返回 Blender”。
- **资产收件区**：自动发现下载目录中的资产 ZIP，显示名称、格式、贴图分辨率与预览；导入记录、定位导入的对象、失败重试、按名称搜索。
- **中英界面**：跟随 Blender 界面语言；其他语言回退英文。
- 开发者：从源码启动测试 Blender，并支持同进程热重载（见 docs/DEVELOPMENT.md）。

### 改进
- 本地 ZIP 导入不再需要预先设置解压目录（留空使用 Blender 数据目录），ZIP 改名后仍能识别。
- 只显示商品图或包内真实预览，不再用基础色贴图冒充预览。
- 无法完整导入的包（如 Alembic）会在导入前明确拒绝，不再出现“导入成功但没有模型”。
- 发布包分为 Windows 完整包（含独立浏览器）和通用包。

### 修复
- Blender 5.x 下 OBJ 资产无法导入。
- 开启中文数据名称翻译时，材质构建找不到 Principled BSDF 而导入失败。
- 材质中有多个 Principled BSDF 时，贴图接到了没有输出的节点上。

### 移除
- Chrome 扩展配对方案及相关面板（原实现保留在标签 `archive/chrome-companion`）。
- 3D 视图顶部重复的“Import Fab Asset”按钮，统一到 **ATBridge → Fab 资产** 面板。

### 兼容性
- 最低支持 Blender 4.2（已在 4.2.10 LTS 与 5.2.3 LTS 测试）。

## [0.4.0] - 2026-02-05
- 完全重构插件代码。
- 整合 ATools 的功能（ATools 不再单独维护）。

## [0.2.7] - 2025-12-28
- 修复 Cycles 相关设置问题。

## [0.2.6] - 2025-12-19
- 修复导入的材质没有自动赋予选中对象。
- 修复导入后节点名称不匹配。
- 首选项界面增加翻译支持。

## [0.2.0] - 2025-07-09
- 修复首选项中 Fab ZIP 解压路径设置。
- 改进首选项界面，增加更详细的配置说明。
- 未配置路径时显示设置按钮，配置后显示导入按钮。
- 优化首选项获取逻辑，提高兼容性。

## [4.0.1]（旧版本号体系）
- 修复 Atlas、Decal 等非 Surface 3D 资产导入时法线贴图丢失。
- 重构节点连接方法，修复 Alpha 贴图错误连接到 BSDF。
- 优化一键切换中英文，修复 zh_CN 报错。
- 一键物理模拟：刚体响应距离调整为 0.001，缩短被动碰撞距离。
- 修复场景名不是默认“Scene”时时间轴工具报错。

## [4.0.0]（旧版本号体系）
- 新增一键翻译中英文（窗口右下角）。
- 新增一键模型清理：锐化边缘、缝合边缘、倒角权重等。
- 新增按集合名称重命名对象。
- 导入图像时按图像尺寸缩放平面。
- 新增快速物理工具。

[0.5.0-beta.1]: https://github.com/BakaAkari/ATBridge/compare/v0.4.0...release/0.5.0
[0.4.0]: https://github.com/BakaAkari/ATBridge/releases/tag/v0.4.0
[0.2.7]: https://github.com/BakaAkari/ATBridge/releases/tag/v0.2.7
[0.2.6]: https://github.com/BakaAkari/ATBridge/releases/tag/v0.2.6
[0.2.0]: https://github.com/BakaAkari/ATBridge/releases/tag/0.2.0
