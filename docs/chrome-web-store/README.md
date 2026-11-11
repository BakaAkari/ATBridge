# Chrome 商店发布材料（未提交）

当前准备版本：0.2.0。未注册或修改开发者账号、未上传包、未提交审核。

- `listing.zh-CN.txt`：可复制的中文商店说明。
- `reviewer-notes.txt`：单一用途、权限用途、数据流与审核步骤。
- `privacy.html`：隐私政策草案，发布前确认联系方式并部署为公开 HTTPS 页面。
- `assets/`：图标、宣传图和实际连接页截图。
- `../../companion/install.html`：测试版用户安装指南。

从仓库根执行 `python3 scripts/package_companion.py`，在 `dist/` 生成扩展 ZIP 及 SHA256。ZIP 根目录包含 manifest，仅打包扩展运行所需文件，不包含账户、资产、测试或 Blender 代码。不执行上传或安装。

## 上架前仍需处理

1. 维护者确认商店开发者身份、隐私联系渠道与上述数据披露；取得公开隐私政策 URL。
2. 发布包含本次 companion 实现的配套 Blender 插件包。当前公开旧版本不能用作审核依赖。
3. 上传扩展草稿取得真实扩展 ID 后，写入 `companion/distribution.py` 的 CHROME_STORE_ID；仅在商店链接可访问时随 Blender 正式版启用。当前为空，明确显示测试版，不伪造商店链接。
4. 实测商店签名安装、不同 Chrome 配置、Windows/Linux、自然会话过期与重新登录。当前验证不能宣传成全版本全平台支持。
5. 审阅所有材料和权限后再另行授权提交审核。商店审核结果及 Fab 接口持续可用性均未保证。

普通用户正式流程：Blender 内打开商店 → 用户确认添加扩展 → 打开扩展请求连接 → Blender 核对确认码并允许。预览版保持会话级授权，关闭扩展页面或重启 Blender 后重新配对，不长期记忆设备。

## 资料依据

2026-11-11 核对：
- https://developer.chrome.com/docs/webstore/cws-dashboard-listing
- https://developer.chrome.com/docs/webstore/cws-dashboard-privacy
- https://developer.chrome.com/docs/webstore/images
- https://developer.chrome.com/docs/extensions/how-to/distribute/install-extensions

当前官方要求 store icon 和至少一张截图；440×280 宣传图为可选。以提交时控制台要求为准。

## 图像来源

`connect1280x800.png` 为实际扩展 connect.html 的初始状态，以本机 Chrome 无头渲染 1280×800 捕获，无账户或配对信息。不是虚构连接成功的宣传画。`icon128.png` 和运行包内图标为本项目生成的几何桥形图标；`promo440x280.png` 为可选预览版宣传图。未使用 Fab/Epic/Blender 标志。截图不验证商店安装，实际 Chrome 配对见 browser-companion-prototype.md。
