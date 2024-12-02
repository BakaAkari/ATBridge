import typing
import bpy
from bpy.types import Context
from bpy.utils import register_class, unregister_class
from .ATBFunctions import *
from mathutils import Matrix
# from PIL import Image
from .ATBOperator3D import *


class AtbPanel3D(bpy.types.Panel):
    bl_idname = "OBJECT_PT_ATB"
    bl_label = "Akari Tool Bag"
    bl_category = "Tool"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 999

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw_header(self, context):
        self.layout.label(text="", icon="TRIA_RIGHT")

    def draw(self, context):
        props = context.scene.atbprops
        wm = context.window_manager

        layout = self.layout
        
        header, render = layout.panel("render_panel", default_closed=True)
        header.label(text="Render Settings")
        if render:
            render_box = layout.box()
            render_column = render_box.column()
            render_column.label(text='Render Settings')
            render_row = render_column.row()
            render_row.operator('object.optievrender', text="EEVEE Best")
            render_row.operator('object.opticyrender', text="Cycles Best")

        header, export = layout.panel("export_panel", default_closed=True)
        header.label(text="Export Operator")
        if export:
            export_box = export.box()
            export_column = export_box.column()
            export_column.label(text='Export Operator')
            export_column.prop(props, 'exportpath', text="Export Location")
            export_column.operator('object.exportfbx', text='Export Object')

        header, object = layout.panel("object_panel", default_closed=True)
        header.label(text="object Operator")
        if object:
            object_box = object.box()
            object_column = object_box.column()
            object_column.label(text='Object Operator')
            object_column.operator('object.rename', text='Rename Object')
            # object_column.operator('object.resetorigin', text='Reset Origin')
            object_column.operator('object.cleanobject', text='Clean Object')

        header, image = layout.panel("image_panel", default_closed=True)
        header.label(text="image Operator")
        if image:
            image_box = image.box()
            image_column = image_box.column()
            image_row = image_column.row()
            image_column.label(text='Image Operator')
            image_column.operator('object.reloadimage', text='Reload Images')
            image_column.operator('object.resizemesh', text='Resize Mesh')

        header, physics = layout.panel("physics_panel", default_closed=True)
        header.label(text="Quick Physics")
        if physics:
            row = physics.row()
            physics_box = layout.box()
            physics_column = physics_box.column()
            physics_column.label(text='Quick Physics')
            physics_column.prop(wm.quick_physics, 'physics_friction', text="Friction", slider=True)
            physics_column.prop(wm.quick_physics, 'physics_time_scale', text="Time Scale")
            if not wm.quick_physics.running_physics_calculation:
                physics_column.operator('quick_physics.calc_physics', text="开始模拟")
            else:
                physics_column.prop(wm.quick_physics, 'running_physics_calculation', text="Cancel Calculation", icon="X")

class AtbPanelNode(bpy.types.Panel):
    bl_idname = "OBJECT_PT_FixBridgeTools"
    bl_label = "Fix Bridge Tools"
    bl_category = "Tool"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_order = 15

    # bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        act_obj: bpy.types.Object

        layout = self.layout
        act_obj = bpy.context.active_object
        nodes = None
        if act_obj.active_material:
            nodes = act_obj.active_material.node_tree.nodes

        layout.operator('object.changeprojection', text="切换映射方式")
        layout.operator('object.addsubd', text="开启曲面细分")

        # 创建节点参数控制滑竿
        try:
            if act_obj.active_material and nodes['Tiling Scale']:
                layout.prop(nodes['Tiling Scale'].outputs['Value'], "default_value", text='Tiling Scale')
        except:
            pass
        try:
            if act_obj.active_material and nodes['Bump Strength']:
                layout.prop(nodes['Bump Strength'].outputs['Value'], "default_value", text='Bump Strength')
        except:
            pass
        layout.operator('object.atbtestoperator', text="测试按钮")

classes = (
    AtbPanel3D,
    AtbPanelNode
)


def register():
    global classes
    for cls in classes:
        register_class(cls)


def unregister():
    global classes
    for cls in classes:
        unregister_class(cls)


if __name__ == "__main__":
    try:
        unregister()
    except:
        pass
    register()
