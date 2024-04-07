# ATBridge Plugin

## Introduction
#### [中文]
ATBridge是集成了ATB功能的Quixel Bridge桥接插件, 内置了一些常用功能
#### [English]
ATBridge is a plugin for Quixel Bridge that integrates a set of convenient tools for personal use.

## Change Log
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
