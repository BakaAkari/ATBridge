# ATBridge 插件首选项
"""
插件首选项模块

定义插件的用户可配置选项。
"""
import bpy
from bpy.types import AddonPreferences

from ..utils.translation import get_text
from ..utils.fab_files import downloads_directory


# 插件 ID
ADDON_ID = "ATBridge"


class AT_AddonPreferences(AddonPreferences):
    """ATBridge 插件首选项"""
    
    bl_idname = ADDON_ID
    
    fab_assets_path: bpy.props.StringProperty(
        name="Fab Assets Path",
        description="Specify the path to extract Fab ZIP assets",
        subtype='DIR_PATH',
        default=""
    )  # type: ignore

    fab_downloads_path: bpy.props.StringProperty(
        name="Download folder", subtype='DIR_PATH', default=str(downloads_directory()),
        description="Your browser's download folder. The ATBridge browser uses an ATBridge subfolder here."
    )
    
    def draw(self, context):
        """绘制首选项面板"""
        layout = self.layout
        
        # 标题
        layout.label(text=get_text("ATBridge Settings:", context))
        
        # Fab 资产配置
        box = layout.box()
        box.label(text=get_text("Fab Assets Configuration:", context), icon='PACKAGE')
        box.prop(self, "fab_assets_path", text=get_text("Extract Path", context))
        box.prop(self, "fab_downloads_path", text=get_text("下载目录", context))
        
        # 路径验证提示
        if not self.fab_assets_path:
            box.label(text=get_text("留空使用 Blender 数据目录，无需首次配置", context), icon='INFO')
        elif not bpy.path.abspath(self.fab_assets_path):
            box.label(text=get_text("⚠ 路径无效", context), icon='ERROR')


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
