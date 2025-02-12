import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty

from . import ATBOperator3D, ATBPreferences, ATBProps, ATBFunctions, ATBPanel, ATBOperatorNode, ATBridge
from .ATBProps import AtbPropgroup

bl_info = {
    "name": "ATBridge",
    "description": "Akari Toolkit integrates the optimized Quixel Bridge plugin suite.",
    "author": "Akari",
    "version": (0, 1, 7),
    "blender": (4, 3, 0),
    "location": "View3D",
    "warning": "Multiple functions are in beta",  # used for warning icon and text in addons panel
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


def register():
    ATBPreferences.register()
    ATBOperator3D.register()
    ATBOperatorNode.register()
    ATBProps.register()
    ATBPanel.register()
    ATBridge.register()
    
    bpy.app.handlers.load_post.append(load_plugin)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)


def unregister():
    ATBPreferences.unregister()
    ATBOperator3D.unregister()
    ATBOperatorNode.unregister()
    ATBProps.unregister()
    ATBPanel.unregister()
    ATBridge.unregister()
