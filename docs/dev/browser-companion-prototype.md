> 历史归档：旧版 Blender 扩展连接面板及其测试入口已移除。以下记录用于追溯，不是现行操作指南；当前流程请见 README。

# 当前免扩展交互

2026-11-11：新主入口为“浏览 Fab 资产”，下载自动识别，手动导入；目录、普通浏览器和旧扩展开关收进设置。独立窗口提供每项下载进度与取消、完成定位和失败回来源页。完整现行使用方式见 [README](../README.md)。以下保留原型迭代与旧扩展机制，旧按钮名称以 README 为准。

# Fab browser companion prototype

## Windows extension-free experiment (2026-11-11)

The extension is now optional. `ui/fab_panel.py` offers the system Fab website, a separate experimental Windows WebView2 browser, recent downloads and direct ZIP selection. See the Windows section in the repository README for build/run instructions. The old extension panel remains available and collapsed by default; the historical flow below still describes that implementation.

`browser/` is an independent .NET 10 WinForms process, not Python packages injected into Blender. It uses a dedicated WebView2 user-data directory under LOCALAPPDATA/ATBridge/FabBrowser, with host objects and web messages disabled. It does not export browser cookies or call undocumented Fab APIs. Official website UI handles authentication and asset selection. Downloads are ZIP-only, isolated by a random folder, and published with the ZIP suffix only after WebView2 reports completion. Blender does not trust a ZIP merely because it is listed; normal ZIP validation and asset metadata parsing run on explicit import.

Verified on this Windows machine: native WebView2 renders the Fab homepage; an actual native local fixture exercises window.open/window.close, completed download notification, unchanged downloaded bytes, duplicate filenames and test-cookie persistence between two helper processes. Blender 5.2.3 regression imports a renamed uppercase ZIP with unrelated JSON, automatically creates an unset extraction directory and isolates repeated extraction folders. The user then confirmed actual Fab sign-in and ZIP download in this independent window. The same downloaded Historic Gemstone Mineral Sodalite Stone Hard 02 Low ZIP (7,452,171 bytes, asset ujyjbi0) was imported through the new recent-list operators in a separate factory-startup Blender process: one mesh, 500 vertices, 996 polygons and five loaded 1024x1024 material images. Existing user scenes were not modified; rendering and all sign-in methods were not tested. No user-agent spoofing or verification bypass is implemented.

Independent review found and verified fixes for early Refresh, page-requested popup closure and rejected metadata conversion cache cleanup. A further slow-download fixture reproduced a popup closing while its download was active. Page-requested closure now waits for active downloads to reach a terminal state; explicit user/owner closure still cancels. The independent reproduction then downloaded all 524,408 bytes, published the final ZIP, closed the popup and exited successfully. This lifecycle fix was tested locally after the user-confirmed live download, rather than claiming a second full Fab download.

The recent list is manually refreshed, limited to 20 entries, and scans only the chosen directory and ATBridge/<job>/ directories. Incomplete .partial files are hidden. There is no automatic scene import, arbitrary native JavaScript bridge, localhost pairing server, or browser extension involved in this new route. Imported image paths depend on the retained extraction cache.

This is an opt-in development prototype, not an official Fab integration. Blender package version and compatibility claims are unchanged. The tested Blender runtime is 5.2.0 LTS on macOS; the existing Blender 2.8+ compatibility/CI work is separate.

## Components and scope

- `companion/blender_ui.py`: View3D → ATBridge → Fab Companion. Explicit Start/Stop, pairing-code copy, search/next-page, ownership + FBX files, download, cancel, manual import.
- `companion/bridge.py`: Python standard-library HTTP server bound only to `127.0.0.1:28481`. No installation, daemon registration, native messaging manifest, or system service. It runs only after Start, and stops on Stop/add-on unload/process exit.
- `companion/extension/`: unpacked Manifest V3 extension. A dedicated extension tab remains open and polls Blender; a signed-in Fab tab must also remain open. Closing the extension tab stops new work; pending Blender jobs can be cancelled manually and expire after 15 minutes.
- `fab-client.mjs`: fixed search / owned-state / FBX files / download-info requests executed in the Fab tab's isolated world. Account login occurs in the official website. No cookie permission, browser database access, cookie export, borrowed OAuth client, purchase, acquisition, or EULA acceptance.

The prototype only imports Megascans-compatible FBX ZIPs with `id/maps/models` JSON. A Fab FBX listing is not proof that its package has this metadata. Unsupported packages return an import error. Other file types, full owned-library pagination, thumbnails, batch jobs, resume, native Asset Browser integration, and rendering validation are outside this slice. Search is public catalog search; ownership is checked when loading files and again before download.

## Before installing

**Do not install automatically. Explain and get the user's go-ahead first.**

Load `companion/extension` via Chrome → Extensions → Developer mode → Load unpacked. Chrome must be 102+. Permissions:

- `scripting` plus `https://www.fab.com/*`: run the packaged request function only on Fab.
- `downloads`: start, check, and cancel extension-created downloads. Chrome exposes broader download API capability, though this prototype queries only IDs it creates.
- `http://127.0.0.1/*`: Chrome host permissions cannot restrict by port; implementation uses only 28481.

No Native Messaging host is required or registered. The extension is an additional installation beyond the Blender ZIP. It is not bundled into an automatic installer.

## Manual acceptance flow after installation approval

1. Use a disposable Blender scene with this source checkout enabled. Set “Browser download folder” to Chrome's actual download directory (default `~/Downloads`). Set the existing Fab Assets Path if desired; otherwise ATBridge uses Blender's DATAFILES/ATBridge directory.
2. Start browser connection. Copy the temporary pairing code. Open the extension via its toolbar action, paste the code and Connect. The code stays in the extension page's memory only; Stop changes it. Clipboard is changed only when Copy is clicked.
3. Log into Fab in a browser tab. Login is handled by the user, including MFA. Keep both Fab and extension tabs open.
4. Search in Blender; select an asset; check ownership / FBX files; select a quality ZIP by filename and displayed size. The extension rechecks acquired state before obtaining a fresh download link.
5. Download stores `Chrome download folder/ATBridge/<job-id>/<original-name>.zip`. Server quickly acknowledges the exact file under the configured directory and enters `transferring`; a background worker checks metadata size (max 1 GiB), validates ZIP paths/CRC and expansion limits (4 GiB / 10000 entries), hashes and atomically copies into `<cache>/companion-inbox/<job-id>/`. A SHA-256 records identity, not authenticity against a publisher checksum.
The extension acknowledgment means transfer was accepted, not that validation finished. Blender exposes Import only after background validation succeeds. A late transport error cannot replace an in-progress transfer. Cancelled transfer output is discarded. Starting another download clears the previous import-ready selection.

6. Click Import downloaded asset in the intended scene. No automatic scene changes occur at download completion. For the verified Nordic Forest Cluster Rock Small low ZIP, expect exactly one mesh, 1599 vertices / 3123 polygons, with four 1K maps. The original FBX may leave unused materials/image placeholders; those are not purged globally.
7. Cancel a running job. A late result must not become ready/importable. Disconnect/reconnect the extension; stop/restart Blender connection; previous pairing code must fail.
8. Session expiry: a 401 yields AUTH_REQUIRED. Log in on the official site, then retry manually. A 403 yields ACCESS_DENIED (may be permission or browser verification, not necessarily expired login); no automatic bypass. 429 stops the request. Already-expired download URLs refresh at most once; mid-download failures require a new download job.
9. Stop the Blender connection, close the extension connection tab, disable/remove the unpacked extension when finished. Cache/download files remain for user cleanup; no account logout is forced.

The installed Chrome extension completed a live search → owned file lookup → download → Blender handoff → import test on 2026-11-11 after user approval and manual loading. See the live result below. Traycer's logged-in Electron browser is not evidence of Chrome `scripting`, `downloads`, CORS/local-network permissions, or extension lifecycle correctness.

## Tests without installation

From repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py'
node tests/test_fab_client.mjs
node tests/test_companion_controller.mjs
blender --background --factory-startup --python-exit-code 1 --python tests/blender_companion_smoke.py
```

To test the already-owned real low ZIP without redistributing it:

```sh
blender --background --factory-startup --python-exit-code 1 --python tests/blender_companion_smoke.py -- /absolute/path/nordic_forest_cluster_rock_small_xjijdiz_low.zip
```

The Blender smoke uses a temporary download/cache directory and an HTTP client standing in for Chrome. It drives actual panel operators, handoff, ZIP import, one-mesh assertion, active material images, auth-error UI state and shutdown. This is not a real Chrome browser test. Node tests use mocked HTTP/Chrome responses; no credentials are required. The independently written controller test also passed: pairing, search-result handoff, completed-download path handoff, disconnect while download creation is unresolved followed by cancellation of the late download, and AUTH_REQUIRED propagation. No real Chrome installation was used.

Live checks on 2026-11-11: logged-in Fab search returns the target among 12 results; file metadata lists the low ZIP (3801396 bytes); download-info HTTP 200 provides a parseable future expiry. An explicit same-origin request with `credentials: omit` returns JSON 401 without logging out the user. Previous live UI download is reused for Blender regression. Unauthenticated-request testing simulates absent session; actual session timeout and re-login lifecycle still require installed-extension acceptance.

## Connection boundaries

Random 256-bit pairing code, extension-only Origin validation, exact Host header, and first authenticated extension-origin pinning. No arbitrary URL fetch or arbitrary destination path supplied by Blender. Signed CDN URLs remain in browser execution and normal browser download history; they are not written to Blender results or logs. Origin is not authentication against local processes: possession of the code grants local job access. The prototype trusts the paired installed extension and the local machine, and has not undergone a production security audit.

Chrome documentation: [scripting](https://developer.chrome.com/docs/extensions/reference/api/scripting), [downloads](https://developer.chrome.com/docs/extensions/reference/api/downloads). Fab `/i/` endpoints are undocumented dependencies and may change.

## Review closure (2026-11-11)

Independent review closed all three findings: slow handoff now acknowledges before background verification, new downloads invalidate the old ready asset, and late old-connection poll failures cannot stop a new session. Final root rerun passed six Python bridge tests, both Node suites, and the Blender 5.2 smoke with the real user-owned low ZIP. Expected rejected import attempts after failed/cancelled replacement downloads are asserted. The later installed Chrome integration passed the single-asset happy path described below. No commit or push performed.

## Installed Chrome live result (2026-11-11)

User loaded the unpacked extension, then authorized continuation. Actual Chrome `scripting` and `downloads`, the installed extension connection page, and a separate Blender 5.2.0 background process completed the flow. The test driver invoked the actual Blender operators; this was not a manual Blender panel usability test.

- Search returned 12 items including the owned Nordic Forest Cluster Rock Small.
- Ownership/file selection succeeded, low ZIP size 3801396 bytes.
- Chrome UI showed completed download; actual extension delivered its file path to the loopback bridge.
- Background validation completed and the actual importer produced exactly one mesh (1599 vertices, 3123 polygons), with four loaded 1024×1024 maps.
- The test process exited 0 and shut the bridge down; its temporary pairing file was removed. Extension remains installed, with its connection page disconnected. No system host registered and no user's existing scene modified.

The first live attempt returned UNSUPPORTED at download, without enough detail to identify whether metadata or CDN validation rejected it. Added bounded diagnostics (changed metadata or hostname only; no signed URL), refreshed the extension page, and retried successfully without relaxing validation. The original cause remains unconfirmed: this is one successful happy path, not a reliability guarantee. Real timed session expiry/re-login and manual Blender panel ergonomics remain unverified; absent-session HTTP401 and simulated error/lifecycle tests passed earlier.

## 2026-11-11：安装引导与便捷配对（扩展 0.2.0）

Blender 新增安装指南、打开扩展目录、商店入口配置、两分钟配对窗口及确认/拒绝操作。当前 CHROME_STORE_ID 留空，显示“测试版：尚未上架”；不会打开虚构商店地址。用户在扩展请求连接后，两边核对六位码，再在 Blender 允许；票据一次性兑换内存中的会话令牌，不需要复制长码。原手动码备用流程保留。

授权仍按运行会话生效，不长期保存信任设备。停止服务或重新配对撤销旧令牌并取消当前任务。取消待审批请求使用绑定来源与票据的 /pair/cancel；取消请求完成前连接按钮保持禁用。重配对与已授权请求分发共用锁，旧会话不能领取新任务。

真实 Chrome 连接页完成请求与确认码显示；测试驱动核对同一码后调用真实 Blender approve 操作，随后 Fab 搜索返回 12 项。Blender 5.2 后台测试退出 0，服务已关闭。这证明真实扩展/HTTP/Blender 操作链路；不冒充手动点击 Blender 面板按钮的验证。最终取消重试竞态修复通过独立实际 Bridge+controller 延迟探针和回归验证；未再重复完整下载。

验证：Python 10 项、Node Fab client 与 controller 两套、Blender background smoke；独立审阅关闭撤销分发和取消重试问题，无阻断发现。Chrome 商店签名安装、Windows/Linux、历史 Blender 版本、Fab 自然到期重登录仍未覆盖。

商店材料见 `docs/chrome-web-store/README.md`。本地执行 `python3 scripts/package_companion.py` 生成 0.2.0 ZIP+SHA256，未上传、未提交审核。截图为实际 connect.html 初始状态的 1280×800 本地无头渲染，不包含账户或配对秘密；真实 Chrome 配对另有上述验证，截图不代表已上架。
