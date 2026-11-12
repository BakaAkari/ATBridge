# 发布流程

## 约定

- 版本号：语义化版本。`bl_info["version"]` 只写 `(主, 次, 修订)`，预发布后缀只出现在标签和包名里。
- 标签：`vX.Y.Z` 或 `vX.Y.Z-beta.N`。
- 分支：`main` 始终等于最近一次正式发布；每个版本在 `release/X.Y.Z` 上准备与修复 Beta；新功能走 `feat/*`，修复走 `fix/*`。
- 远程：`origin` = GitHub（主仓库，Issues 和 Release 以这里为准），`gitee` = Gitee 镜像。两边推送相同的 `main` 和标签。

## 发布前检查

1. `python -m unittest discover -s tests -p "test_*.py"` 全部通过。
2. Blender 冒烟测试，最低支持版本和最新 LTS 各跑一次：
   ```powershell
   .\scripts\start-dev.ps1 -BlenderPath "<blender.exe>" -LocalSmokeTest
   .\scripts\start-dev.ps1 -BlenderPath "<blender.exe>" -SmokeTest
   ```
3. 实际走一遍：独立浏览器登录 Fab → 下载 → 返回 Blender → 导入，以及从旧版本升级安装。
4. 更新 `CHANGELOG.md`（把“未发布”改成日期），确认 `bl_info` 的 `version` 和 `blender`。

## 打包

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\package.ps1 -Suffix beta.1   # 正式版不加 -Suffix
```

输出到 `dist/release/<标签>/`：

- `ATBridge_<标签>.zip`：通用包（不含独立浏览器）
- `ATBridge_<标签>_windows-x64.zip`：Windows 完整包（含自包含 .NET 的独立浏览器，用户不用另装 .NET）
- `SHA256SUMS.txt`

需要 .NET 10 SDK。包内只有插件运行所需的文件，不含 tests、scripts、docs、browser 源码和缓存。打包后在干净的 Blender 里从磁盘安装两个包，各检查一次。

## 发布

```bash
git tag -a v0.5.0-beta.1 -m "ATBridge v0.5.0-beta.1"
git push origin release/0.5.0 v0.5.0-beta.1
git push gitee release/0.5.0 v0.5.0-beta.1
```

- GitHub：在 Releases 页面用这个标签新建发布；Beta 勾选 **Set as a pre-release**；正文用 CHANGELOG 对应段落；上传三个文件。
- Gitee：在发行版页面用同一个标签新建发行版，上传同样的三个文件。
- 正式版：`release/X.Y.Z` 合入 `main`，打 `vX.Y.Z`，两个远程都推送 `main` 和标签。

## 凭据

- 推送使用本机 SSH 密钥，GitHub 与 Gitee 账户里都已添加公钥。
- 如需脚本自动创建 Release：GitHub 用 `gh auth login`（由仓库所有者本人登录）；Gitee 用私人令牌，放在环境变量 `GITEE_TOKEN` 中。令牌不写入仓库，也不发到聊天里。
