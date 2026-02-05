# ATBridge 插件首选项
"""
插件首选项模块

定义插件的用户可配置选项。
"""
import bpy
from bpy.types import AddonPreferences

from ..utils.translation import get_text


# 插件 ID
ADDON_ID = "ATBridge"


class AT_AddonPreferences(AddonPreferences):
    """ATBridge 插件首选项"""
    
    bl_idname = ADDON_ID
    
    fab_assets_path: bpy.props.StringProperty(
        name="Fab Assets Path",
        description="Specify the path to extract Fab ZIP assets",
        subtype='DIR_PATH',
        default="D:\\FabAssets"
    )  # type: ignore
    
    def draw(self, context):
        """绘制首选项面板"""
        layout = self.layout
        
        # 标题
        layout.label(text=get_text("ATBridge Settings:", context))
        
        # Fab 资产配置
        box = layout.box()
        box.label(text=get_text("Fab Assets Configuration:", context), icon='PACKAGE')
        box.prop(self, "fab_assets_path", text=get_text("Extract Path", context))
        
        # 路径验证提示
        if not self.fab_assets_path:
            box.label(text="⚠ 请设置解压路径", icon='ERROR')
        elif not bpy.path.abspath(self.fab_assets_path):
            box.label(text="⚠ 路径无效", icon='ERROR')


def get_addon_preferences(context) -> AT_AddonPreferences:
    """
    获取插件首选项
    
    Args:
        context: Blender context
    
    Returns:
        插件首选项对象，或 None
    """
    try:
        addon = context.preferences.addons.get(ADDON_ID)
        if addon:
            return addon.preferences
    except Exception:
        pass
    return None
