import bpy
from bpy.app.handlers import persistent

from . import ATBridge
from . import ATBridgeExtend

bl_info = {
    "name": "ATBridge",
    "description": "Baka_Akari Toolkit",
    "author": "Baka_Akari",
    "version": (0, 2, 2),
    "blender": (2, 8, 0),
    "location": "View3D",
    "wiki_url": "https://docs.quixel.org/bridge/livelinks/blender/info_quickstart.html",
    "support": "COMMUNITY",
    "category": "3D View"
}

@persistent
def load_plugin(scene):
    try:
        bpy.ops.bridge.plugin()
    except Exception as e:
        print("Bridge Plugin Error::Could not start the plugin. Description: ", str(e))


def menu_func_import(self, context):
    self.layout.operator(ATBridge.MS_Init_Abc.bl_idname, text="Megascans: Import Alembic Files")

def import_zip_button(self, context):
    layout = self.layout
    layout.operator("atb.import_zip", text="Import Fab Asset", icon='FILE_NEW')


def register():
    ATBridge.register()
    ATBridgeExtend.register()
    bpy.app.handlers.load_post.append(load_plugin)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.VIEW3D_HT_header.append(import_zip_button)


def unregister():
    ATBridge.unregister()
    ATBridgeExtend.unregister()
    bpy.types.VIEW3D_HT_header.remove(import_zip_button)