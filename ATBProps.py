from bpy.props import (BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty, IntProperty,
                       StringProperty)
from bpy.types import PropertyGroup
from bpy.utils import register_class, unregister_class


class AtbPropgroup(PropertyGroup):
    my_bool: BoolProperty(
        name="Enable or Disable",
        description="A bool property",
        default=False
    ) # type: ignore

    my_int: IntProperty(
        name="Int Value",
        description="A integer property",
        default=23,
        min=10,
        max=100
    ) # type: ignore

    my_float: FloatProperty(
        name="Float Value",
        description="A float property",
        default=23.7,
        min=0.01,
        max=30.0
    ) # type: ignore

    my_float_vector: FloatVectorProperty(
        name="Float Vector Value",
        description="Something",
        default=(0.0, 0.0, 0.0),
        min=0.0,  # float
        max=0.1
    ) # type: ignore

    my_string: StringProperty(
        name="User Input",
        description=":",
        default="",
        maxlen=1024,
    ) # type: ignore

    my_enum: EnumProperty(
        name="Dropdown:",
        description="Apply Data to attribute.",
        items=[('OP1', "Option 1", ""),
               ('OP2', "Option 2", ""),
               ('OP3', "Option 3", ""),
               ]
    ) # type: ignore
    
    export_rule: EnumProperty(
        items=[
            ('UNREAL', "Unreal", "Export as Unreal Engine rules"),
            ('UNITY', "Unity", "Export as Unity Engine rules"),
        ],
        name="Export Rule",
        description="Select an option",
    ) # type: ignore
    
    physics_friction: FloatProperty(
        description="Friction",
        default=0.5,
        min=0.0, max=1.0
    ) # type: ignore
    
    physics_time_scale: FloatProperty(
        description="Simulation speed",
        default=5.0, min=0.0, max=20.0
    ) # type: ignore
    
    is_running_physics: BoolProperty(
        description="",
        default=False
    ) # type: ignore
    
    running_physics_calculation: BoolProperty(
        description="",
        default=False
    ) # type: ignore
    
    exportpath: StringProperty(
        name='Export Path',
        description='',
        # default='\\10.234.36.135\share\美术资源\Software 软件\Blender插件\【Vertex Games Tools】',
        default='',
        subtype='DIR_PATH'  # 指定为目录路径
    ) # type: ignore
    
    movetexlocation: BoolProperty(
        description="",
        default=True
    ) # type: ignore
    
    col_tex_name: StringProperty(
        name="Color Texture Name",
        description="",
        default="",
        maxlen=1024,
    )   # type: ignore
    
    opa_tex_name: StringProperty(
        name="Opacity Texture Name",
        description="",
        default="",
        maxlen=1024,
    )   # type: ignore

    rough_tex_name: StringProperty(
        name="Roughness Texture Name",
        description="",
        default="",
        maxlen=1024,
    ) # type: ignore
    
    metal_tex_name: StringProperty(
        name="Metallic Texture Name",
        description="",
        default="",
        maxlen=1024,
    ) # type: ignore
    
    ao_tex_name: StringProperty(
        name="AO Texture Name",
        description="",
        default="",
        maxlen=1024, 
    ) # type: ignore
    
    nor_tex_name: StringProperty(
        name="Normal Texture Name",
        description="",
        default="",
        maxlen=1024, 
    ) # type: ignore
    
    #     maxlen=1024,
    #     subtype='FILE_PATH'
    #     )
    # addonaddress: StringProperty(
    #     name='addonaddress',
    #     description='',
    #     default='',
    #     maxlen=1024,
    #     subtype='DIR_PATH'
    #     )

#===========================================================================================================

classes = (AtbPropgroup,
           )


def register():
    global classes
    for cls in classes:
        register_class(cls)


def unregister():
    global classes
    for cls in classes:
        unregister_class(cls)
