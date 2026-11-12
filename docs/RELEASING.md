# 发布流程

发版只在**发布机**（MacBook）上进行，令牌也只放在那里。开发机只通过 SSH 推送代码，不保存任何 GitHub / Gitee 令牌。

## 约定

- 版本号：语义化版本。`bl_info["version"]` 只写 `(主, 次, 修订)`，预发布后缀只出现在标签和包名里。
- 标签：`vX.Y.Z` 或 `vX.Y.Z-beta.N`；带 `-` 的标签自动作为预发布，不标记为最新版本。
- 分支：`main` 始终等于最近一次正式发布；每个版本在 `release/X.Y.Z` 上准备与修复 Beta；新功能走 `feat/*`，修复走 `fix/*`。
- 远程：`origin` = GitHub（主仓库，Issues 以这里为准），`gitee` = Gitee 镜像。两边推送相同的分支和标签。
- 发行说明：`docs/release-notes/<标签>.md`，随代码提交，GitHub 与 Gitee 共用。

## 发布机一次性准备（macOS）

1. SSH：GitHub 使用 `~/.ssh/id_ed25519_github`，Gitee 使用 `~/.ssh/id_ed25519_gitee`（`~/.ssh/config` 中已配置），两把公钥分别加到对应账户。
2. GitHub CLI：`gh auth login`（选择 GitHub.com → SSH → 浏览器登录）。不要在 shell 配置里导出 `GITHUB_TOKEN`，它会覆盖 gh 的登录。
3. Gitee 令牌：在 https://gitee.com/profile/personal_access_tokens 生成（权限只勾 `projects`），写入发布机的 `~/.zshrc`：`export GITEE_TOKEN=...`，或 macOS 钥匙串后再导出。不要写进仓库。
4. .NET 10 SDK（用于交叉编译 Windows 浏览器，不需要 sudo）：
   ```bash
   curl -sSL https://dot.net/v1/dotnet-install.sh | bash -s -- --channel 10.0
   export PATH="$HOME/.dotnet:$PATH"
   ```
5. 仓库远程：`origin = git@github.com:BakaAkari/ATBridge.git`，`gitee = git@gitee.com:baka-akari/ATBridge.git`。

## 发布前检查（在 Windows 开发机上）

1. `python -m unittest discover -s tests -p "test_*.py"` 全部通过。
2. Blender 冒烟测试，最低支持版本和最新 LTS 各跑一次：
   ```powershell
   .\scripts\start-dev.ps1 -BlenderPath "<blender.exe>" -LocalSmokeTest
   .\scripts\start-dev.ps1 -BlenderPath "<blender.exe>" -SmokeTest
   ```
3. 实际走一遍：独立浏览器登录 Fab → 下载 → 返回 Blender → 导入，以及从旧版本升级安装。
4. 更新 `CHANGELOG.md`（写上日期）、`bl_info` 的 `version` / `blender`，写 `docs/release-notes/<标签>.md`。提交并推送 `release/X.Y.Z` 到两个远程。

## 发版（在 MacBook 上）

```bash
git checkout release/0.5.0 && git pull
git tag -a v0.5.0-beta.2 -m "ATBridge v0.5.0-beta.2"
git push origin release/0.5.0 v0.5.0-beta.2
git push gitee  release/0.5.0 v0.5.0-beta.2

python3 scripts/package.py --suffix beta.2      # 正式版不加 --suffix
python3 scripts/publish.py v0.5.0-beta.2        # 创建 GitHub 与 Gitee 发行版并上传附件
```

`package.py` 输出到 `dist/release/<标签>/`：通用包、含自包含 .NET 浏览器的 Windows 包（`windows-x64`）和 `SHA256SUMS.txt`。包内只有插件运行所需的文件。打包结果与平台无关，Windows 上也可以运行（`python scripts/package.py`）用于自测。

`publish.py` 可重复运行：已存在的发行版会复用，已上传的附件会跳过；只发一边用 `--only github` 或 `--only gitee`。

正式版：`release/X.Y.Z` 合入 `main`，在 `main` 上打 `vX.Y.Z`，两个远程都推送 `main` 和标签，再运行上面的打包和发布。

## 发布后

- 从两个发布页各下载一次安装包，核对 `SHA256SUMS.txt`。
- 在干净的 Blender 中从磁盘安装 Windows 包，确认插件能启用、独立浏览器能打开。
