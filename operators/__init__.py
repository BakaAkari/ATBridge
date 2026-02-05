# ATBridge operators module
from .bridge_livelink import MS_Init_LiveLink
from .alembic_import import MS_Init_Abc
from .fab_import import ATB_OT_import_zip

# 注册列表
classes = (
    MS_Init_LiveLink,
    MS_Init_Abc,
    ATB_OT_import_zip,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in classes:
        unregister_class(cls)
