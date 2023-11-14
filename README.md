<!--
 * @Author: your name
 * @Date: 2022-04-30 00:37:03
 * @LastEditTime: 2022-04-30 00:39:23
 * @LastEditors: Please set LastEditors
 * @Description: 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
 * @FilePath: \Fix_Quixel_Bridge_Addon-1\README.md
-->
警告:
3.8版本仅适用于Blender4.0, 4.0以下版本请使用旧版插件

Warning: 
Version 3.8 is only compatible with Blender 4.0. For versions below 4.0, please use the old plugin.

Chinese:

Quixel Bridge官方插件长时间不更新
一怒之下动手修改

使用方式：https://www.bilibili.com/video/BV1K14y1K73G/ 见视频

文字版：
    blender安装插件，关闭blender，bridge导出设置选择Custom Socket Export，端口号为23333，然后重启bridge，再打开blender

Tip:

    3D模型导入前，Bridge导出设置不能选择highpoly source为导出项，此项会导致输出贴图索引不完整，建议使用LOD 0

2023.11.14 Changelist:
        兼容blender 4.0新版BSDF节点
        兼容blender 4.0新版View Transform Look Setting
        修复无法导入metallic贴图的问题(旧版根据quixel tag的surface type给metallic为0或为1的值)
        修复自适应细分可以无限添加修改器的BUG

Changelist:
        添加一键EEVEE/Cycles最佳渲染参数按钮
        添加一键Cycles自适应细分功能
        添加Tiling Scale滑块

English:

Video:https://www.youtube.com/watch?v=Y-Ovx6-XvVY

1.Install the plugin using the blender script installer, then close blender

2.Open the quixel bridge, open the export settings,
    Export Target：Custom Socket 
    Socket Port：23333

3.Close Quixel Bridge

4.First open Blender, then open Quixel Bridge software

5.Click on the output button for the asset and blender will receive the correct asset

Tip：

    Before importing the 3D model, Bridge export settings cannot select highpoly source as the export item, this item will lead to incomplete output map index, it is recommended to use LOD 0

2023.11.14 Changelist:
        Compatible with Blender 4.0 new BSDF node
        Compatible with Blender 4.0 New Version View Transform Look Setting
        Fixed an issue where metallic maps could not be imported
        Fixed BUG where Adaptive Subdivision could add modifiers indefinitely

Changelist:
        Add one-click EEVEE/Cycles best rendering parameters button
        Add one-click Cycles adaptive subdivision
        Add Tiling Scale slider

