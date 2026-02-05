# ATBridge UI 回调函数
"""
UI 回调函数模块

包含添加到 Blender 标准 UI 的回调函数。
"""
import bpy
from bpy.utils import register_class, unregister_class


def translation_ui_function(self, context):
    """状态栏语言切换按钮"""
    layout = self.layout
    layout.operator("atb.ui_toggle_language", text="", icon='WORLD')


def frame_ui_function(self, context):
    """时间线帧控制按钮"""
    layout = self.layout
    row = layout.row(align=True)
    row.operator("atb.frame_set_start", text="[", icon='NONE')
    row.operator("atb.frame_set_end", text="]", icon='NONE')
    row.operator("atb.frame_toggle_loop", text="", icon='FILE_REFRESH')


def reload_image_ui_function(self, context):
    """节点编辑器重载图像按钮"""
    layout = self.layout
    layout.operator("atb.image_reload_all", text="", icon='FILE_REFRESH')


def register():
    """注册 UI 回调"""
    try:
        bpy.types.STATUSBAR_HT_header.append(translation_ui_function)
        bpy.types.DOPESHEET_HT_header.append(frame_ui_function)
        bpy.types.NODE_HT_header.append(reload_image_ui_function)
        print("ATBridge: UI callbacks registered")
    except Exception as e:
        print(f"ATBridge: Error registering UI callbacks: {e}")


def unregister():
    """注销 UI 回调"""
    try:
        bpy.types.STATUSBAR_HT_header.remove(translation_ui_function)
        bpy.types.DOPESHEET_HT_header.remove(frame_ui_function)
        bpy.types.NODE_HT_header.remove(reload_image_ui_function)
    except Exception as e:
        print(f"ATBridge: Error unregistering UI callbacks: {e}")
