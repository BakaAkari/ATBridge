# ATBridge Plugin

## Introduction
#### [中文]
ATBridge是集成了ATB功能的Quixel Bridge桥接插件, 内置了一些常用功能
#### [English]
ATBridge is a plugin for Quixel Bridge that integrates a set of convenient tools for personal use.

## Features
#### [中文]
- Quixel Bridge资产导入
- Fab ZIP文件导入功能
- 一键翻译中英文功能
- 一键模型清理功能
- 物理模拟工具
- 集合重命名功能

#### [English]
- Quixel Bridge asset import
- Fab ZIP file import functionality
- One-click Chinese/English translation
- One-click model cleanup
- Physics simulation tools
- Collection renaming functionality

## Fab ZIP File Import Configuration
#### [中文]
**首次使用前必须配置解压路径：**
1. 打开 Blender 首选项：`编辑` > `首选项` > `插件`
2. 搜索并找到 "ATBridge" 插件
3. 展开插件设置，在 "Fab Assets Configuration" 部分设置 "Extract Path"
4. 选择一个用于解压Fab ZIP文件的文件夹路径
5. 设置完成后，3D视图区域顶部将显示 "Import Fab Asset" 按钮

**使用方法：**
1. 确保已配置解压路径
2. 点击3D视图顶部的 "Import Fab Asset" 按钮
3. 选择要导入的Fab ZIP文件
4. 插件会自动解压并导入资产到Blender

#### [English]
**Extraction path must be configured before first use:**
1. Open Blender Preferences: `Edit` > `Preferences` > `Add-ons`
2. Search for and find the "ATBridge" addon
3. Expand addon settings, set "Extract Path" in the "Fab Assets Configuration" section
4. Choose a folder path for extracting Fab ZIP files
5. After configuration, "Import Fab Asset" button will appear in the 3D viewport header

**Usage:**
1. Ensure extraction path is configured
2. Click the "Import Fab Asset" button in the 3D viewport header
3. Select the Fab ZIP file to import
4. The plugin will automatically extract and import assets into Blender

## Change Log
### Version 0.2.0 (Latest)

#### [中文]
- 🔧 修复首选项中fab zip文件解压路径设置功能
- ✨ 改进首选项界面，增加更详细的配置说明
- ✨ 添加智能UI切换：未配置路径时显示设置按钮，已配置时显示导入按钮
- 🔧 优化首选项获取逻辑，提高兼容性
- ✨ 增加首选项快捷访问功能

#### [English]
- 🔧 Fixed fab zip file extraction path setting in preferences
- ✨ Improved preferences interface with detailed configuration instructions
- ✨ Added smart UI switching: shows setup button when unconfigured, import button when configured
- 🔧 Optimized preferences retrieval logic for better compatibility
- ✨ Added quick access to preferences functionality

### Version 4.0.1

#### [中文]
- 修复Atlas, Decal等非Surface, 3D Assets资产导入, Normal map丢失问题
- 重构link.new的方法, 解决Alpha贴图连接BSDF错误的问题
- 优化一键切换中英文功能, 修复zh_CN报错问题
- 优化一键物理模拟功能, 调整刚体响应距离为0.001, 缩短被动碰撞距离
- 修复Scene name不是默认"Scene"的情况下, Timeline Tools失效报错的问题
#### [English]
- Repair Atlas, Decal and other non-Surface, 3D Assets assets import, Normal map loss problem.
- Refactor the link.new method to fix the issue with Alpha maps incorrectly connecting to BSDF.
- Optimize the one-click toggle between English and Chinese, fix the zh_CN error issue.
- Optimize the one-click physics simulation feature, set the rigid body response distance to 0.001, reduce the passive collision distance.
- Fixed the issue where Timeline Tools would fail and give an error if the Scene name wasn't set to the default "Scene".

### Version 4.0.0

#### [中文]
- 新增了一键翻译中英文功能，位于窗口右下角
- 新增了一键模型清理功能，包括但不限于锐化边缘、缝合边缘和倒角权重
- 增加了一键根据集合名称重命名对象的功能，强制以Collection名称重命名内含Object以在一定程度上规范文件目录
- 增加导入图像, 根据图像尺寸正确缩放Plane长宽
- 添加Quick Physics工具
#### [English]
- Added a one-click feature to translate between Chinese and English, located at the bottom right of the window, and it only provides the translation results.
- Added a one-click model cleanup feature that includes, but is not limited to, sharpening edges, stitching edges, and chamfer weights.
- Added a feature to rename objects with a single click based on the collection name, enforcing a standardized file structure by renaming contained objects after the collection.
- Add images, scale the plane to the correct size based on the image dimensions.
- Add the Quick Physics tool.

## Installation
#### [中文]
- 使用Blender插件安装界面直接安装
- 首次安装前建议关闭Quixel Bridge, 安装好插件后重启Blender再开启Quixel Bridge
#### [English]
- Install directly using the Blender plugin interface.
- Before the initial setup, it's recommended to close Quixel Bridge. After installing the plugin, restart Blender and then reopen Quixel Bridge.

## Usage
#### [中文]
- Quixel Bridge设置: Edit > Export Settings > Export Target设置为Custom Socket Export, Socket Port设置为23333
- Tips: Export Settings > Models > LODs设置不要设置为Highpoly Source, 该设置无法正确导入贴图
#### [English]
- In Quixel Bridge, go to Edit > Export Settings, set Export Target to Custom Socket Export, and set the Socket Port to 23333
- Tips: In the Export Settings under Models, don't set LODs to Highpoly Source as it won't import textures correctly

## Contact
- QQ群: 628731557
- Email: exwww2000@qq.com

![Image text](https://gitee.com/baka-akari/images_lib/raw/master/%E5%8A%A8%E7%94%BB%2025.gif)
![Image text](https://gitee.com/baka-akari/images_lib/raw/master/%E5%8A%A8%E7%94%BB%2027.gif)
![Image text](https://gitee.com/baka-akari/images_lib/raw/master/%E5%8A%A8%E7%94%BB%2026.gif)
