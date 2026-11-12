# ATBridge

**Browse Fab / Megascans inside Blender and import downloaded assets with their materials in one click.** Also includes a Quixel Bridge LiveLink and a set of ATools utilities.

[中文](README.md) · [Changelog](CHANGELOG.md) · [Issues](https://github.com/BakaAkari/ATBridge/issues) · GitHub: [BakaAkari/ATBridge](https://github.com/BakaAkari/ATBridge) · Gitee mirror: [baka-akari/ATBridge](https://gitee.com/baka-akari/ATBridge)

![Blender 4.2+](https://img.shields.io/badge/Blender-4.2%2B-orange) ![License LGPL-3.0](https://img.shields.io/badge/license-LGPL--3.0-blue)

> 0.5.0 is a beta release. Feedback is welcome.

## Features

| Feature | Description | Platform |
|---|---|---|
| Fab browser | Sign in to Fab, browse Megascans and download assets in ATBridge's own window, with a download panel. No browser extension required | Windows |
| Asset inbox | Finds downloaded asset ZIPs automatically and shows name, format, texture resolution and product image; import with one click | All |
| Local ZIP import | Pick an asset ZIP from disk; no extraction folder needs to be configured first | All |
| Quixel Bridge LiveLink | Receives exports from Quixel Bridge | All |
| ATools | Chinese/English UI toggle, model cleanup, rename objects by collection, images as planes, quick physics, timeline tools | All |

The interface is available in Simplified Chinese and English and follows Blender's language.

## Requirements

- Blender 4.2 or newer (tested on 4.2 LTS and 5.2 LTS)
- Fab browser: Windows 10 / 11 x64 with the Microsoft Edge WebView2 Runtime (normally preinstalled)
- macOS / Linux: everything except the built-in browser; download from Fab in your system browser, then import from the inbox or a local ZIP

## Installation

1. Download from [Releases](https://github.com/BakaAkari/ATBridge/releases) (or Gitee releases):
   - Windows: `ATBridge_<version>_windows-x64.zip` (includes the browser)
   - macOS / Linux: `ATBridge_<version>.zip`
2. In Blender open **Edit → Preferences → Add-ons**, choose **Install from Disk…** in the top-right menu and select the ZIP (do not extract it).
3. Enable **ATBridge**.

Upgrading: remove the old ATBridge from the add-on list, restart Blender, then install the new version.

## Quick start: import a Fab asset

1. Press `N` in the 3D Viewport and open **ATBridge → Fab Assets**.
2. Click **Browse Fab assets**, sign in to Fab in the window that opens, and download an asset ZIP. Sign-in is only needed once and stays in this window.
3. When the download finishes, click **Return to Blender**. The asset appears in the inbox; select it to see its preview and details.
4. Click **Import into scene**.

Without the built-in browser: download the ZIP in any browser, then select it in the inbox or use **Choose a local ZIP…**.

### Supported assets

- Fab asset ZIPs with Megascans metadata: FBX / OBJ models and materials (Surface, Decal, Atlas, …)
- Not supported yet: Alembic (ABC) packages, ZIPs without Megascans metadata, several assets in one ZIP

Unsupported packages are hidden by default; enable them under **Settings and other options** to see why.

## Quixel Bridge LiveLink

1. In Quixel Bridge open **Edit → Export Settings**, set **Export Target** to **Custom Socket Export** and **Socket Port** to **23333**.
2. Export from Bridge; the asset arrives in the current Blender scene.

Tip: don't set **Models → LODs** to **Highpoly Source**, or textures won't import correctly. On first install, close Bridge, install the add-on, restart Blender, then reopen Bridge.

## Data and privacy

| Data | Location |
|---|---|
| Browser sign-in data | `%LOCALAPPDATA%\ATBridge\FabBrowser` (your regular browser's cookies are never read) |
| Product image cache | `%LOCALAPPDATA%\ATBridge\Cache\Fab` (up to 256 MB, 90-day expiry) |
| Downloaded ZIPs | `ATBridge\` under your download folder |
| Extracted assets | Extraction folder from the add-on settings; if empty, `ATBridge/assets` in Blender's data folder |
| Import history | `ATBridge/imports.json` in Blender's config folder (up to 200 entries) |

ATBridge never buys or claims assets or accepts licenses for you; you do that yourself on the Fab website. Extracted textures are referenced by your scene, so don't delete asset folders that are in use.

## FAQ

**"Browse Fab Assets" only opened my system browser?** You installed the add-on-only package, or you're not on Windows. On Windows, install the `windows-x64` package.

**The download finished but nothing appears in the inbox?** Check that the download folder in the add-on preferences matches where files are saved. It is locked while the ATBridge browser is open. Unsupported packages are only listed when **Show unsupported ZIPs** is on.

**Import failed?** Check the reason shown in the inbox. For unsupported formats, download the FBX version on Fab. If it still fails, [open an issue](https://github.com/BakaAkari/ATBridge/issues) with your Blender version, the asset name and the error.

## Disclaimer

ATBridge is an unofficial add-on by an individual developer and is not affiliated with Epic Games, Fab or Quixel. Assets downloaded and used through ATBridge remain subject to Fab's license terms.

## Development

Running from source, hot reload and tests: [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md). Releasing: [docs/RELEASING.md](docs/RELEASING.md).

## Contact

- QQ group: 628731557
- Email: exwww2000@qq.com

## License

[LGPL-3.0](LICENSE)
