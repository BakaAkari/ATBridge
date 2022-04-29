![images](https://github.com/BakaAkari/Images_lib/blob/main/baka-akari-untitled.jpg)
Chinese:
Quixel Bridge官方插件长时间不更新
一怒之下动手修改

使用方式：https://weibo.com/5361597303/LiGi5wKUJ 见视频

文字版：
    blender安装插件，关闭blender，bridge导出设置选择Custom Socket Export，端口号为23333，然后重启bridge，再打开blender

修正了节点连BSDF插槽错位的问题

解除了默认只在CYCLES渲染器下才导入置换贴图的限制

增加surface对象，贴图映射方式从UV方式改为方形投射，免除UV步骤

Tip:

    3D模型导入前，Bridge导出设置不能选择highpoly source为导出项，此项会导致输出贴图索引不完整，建议使用LOD 0


English:
1.Install the plugin using the blender script installer, then close blender

2.Open the quixel bridge, open the export settings,
    Export Target：Custom Socket 
    Socket Port：23333

3.Close Quixel Bridge

4.First open Blender, then open Quixel Bridge software

5.Click on the output button for the asset and blender will receive the correct asset

Tip：

    Before importing the 3D model, Bridge export settings cannot select highpoly source as the export item, this item will lead to incomplete output map index, it is recommended to use LOD 0
