# ATBridge preferences module
from .addon_prefs import AT_AddonPreferences, get_addon_preferences

# 注册列表
classes = (
    AT_AddonPreferences,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
