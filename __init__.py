# ATBridge - Quixel Bridge Toolkit for Blender
"""
ATBridge 插件入口

Blender 插件的主入口文件，负责注册和注销所有模块。
"""
import bpy
from bpy.app.handlers import persistent

# 插件元信息
bl_info = {
    "name": "ATBridge",
    "description": "Baka_Akari Quixel Bridge Toolkit",
    "author": "Baka_Akari",
    "version": (0, 4, 0),
    "blender": (4, 0, 0),
    "location": "View3D",
    "wiki_url": "https://docs.quixel.org/bridge/livelinks/blender/info_quickstart.html",
    "support": "COMMUNITY",
    "category": "3D View"
}

# 模块导入
from . import operators
from . import preferences
from . import properties
from . import tools
from . import ui
from .operators.alembic_import import MS_Init_Abc


@persistent
def load_plugin(scene):
    """文件加载后自动启动 LiveLink 服务"""
    try:
        bpy.ops.bridge.plugin()
    except Exception as e:
        print(f"[ATBridge] 自动启动失败: {e}")


def menu_func_import(self, context):
    """添加到导入菜单"""
    self.layout.operator(MS_Init_Abc.bl_idname, text="Megascans: Import Alembic")


def import_zip_button(self, context):
    """3D 视图头部添加导入按钮"""
    self.layout.operator("atb.import_zip", text="Import Fab Asset", icon='IMPORT')


def register():
    """注册插件"""
    # 1. 先注册属性组（其他模块可能依赖它）
    properties.register()
    
    # 2. 注册操作符
    operators.register()
    tools.register()
    
    # 3. 注册首选项
    preferences.register()
    
    # 4. 注册 UI 面板
    ui.register()
    
    # 5. 注册事件处理
    if load_plugin not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_plugin)
    
    # 6. 注册菜单
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.VIEW3D_HT_header.append(import_zip_button)
    
    print(f"[ATBridge] v{'.'.join(map(str, bl_info['version']))} 已加载")


def unregister():
    """注销插件"""
    # 移除菜单
    try:
        bpy.types.VIEW3D_HT_header.remove(import_zip_button)
        bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    except Exception:
        pass
    
    # 移除事件处理
    try:
        if load_plugin in bpy.app.handlers.load_post:
            bpy.app.handlers.load_post.remove(load_plugin)
    except Exception:
        pass
    
    # 注销子模块（逆序）
    ui.unregister()
    preferences.unregister()
    tools.unregister()
    operators.unregister()
    properties.unregister()
    
    print("[ATBridge] 已卸载")


if __name__ == "__main__":
    register()
