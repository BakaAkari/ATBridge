import bpy
from bpy.utils import register_class, unregister_class
from .ATBFunctions import *
from .ATBOperator3D import *


class AtbPanel3D(bpy.types.Panel):
    bl_idname = "OBJECT_PT_ATB"
    bl_label = "ATBridge Tools"
    bl_category = "Tool"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_order = 80

    
    # bl_options = {'DEFAULT_CLOSED'}
    

    @classmethod
    def poll(cls, context):
        return context.object is not None

    def draw_header(self, context):
        self.layout.label(text="", icon='DOT')

    def draw(self, context):
        wm = context.window_manager
        props = wm.atbprops
        

        layout = self.layout

        # layout.operator("object.atb3dtestoperator", text="Test Operator")

        header, render = layout.panel("render_panel", default_closed=False)
        header.label(text="Render Settings")
        if render:
            render_box = render.box()
            render_column = render_box.column()
            render_row = render_column.row()
            render_row.operator('object.optievrender', text="EEVEE Best")
            render_row.operator('object.opticyrender', text="Cycles Best")

        header, image = layout.panel("image_panel", default_closed=False)
        header.label(text="image Operator")
        if image:
            image_box = image.box()
            image_column = image_box.column()
            image_row = image_column.row()
            image_column.label(text='Image Operator')
            image_column.operator('object.reloadimage', text='Reload Images')
            image_column.operator('object.resizemesh', text='Resize Mesh')


class AtbPanelNode(bpy.types.Panel):
    bl_idname = "OBJECT_PT_FixBridgeTools"
    bl_label = "ATBridge Tools"
    bl_category = "Tool"
    bl_space_type = "NODE_EDITOR"
    bl_region_type = "UI"
    bl_order = 15

    # bl_options = {'DEFAULT_CLOSED'}
    
    def draw_header(self, context):
        self.layout.label(text="", icon='DOT')
    
    def draw(self, context):
        act_obj: bpy.types.Object
        wm = context.window_manager

        layout = self.layout
        act_obj = bpy.context.active_object
        nodes = None
        if act_obj:
            nodes = act_obj.active_material.node_tree.nodes
        else:
            return

        header, image = layout.panel("ATB_panel", default_closed=False)
        header.label(text="ATB Operator")
        if image:
            image_box = image.box()
            image_column = image_box.column()
            image_row = image_column.row()
            image_row.operator('object.changeprojection', text="切换映射方式")
            image_row.operator('object.addsubd', text="开启曲面细分")

        
        header, image = layout.panel("image_panel", default_closed=False)
        header.label(text="image Operator")
        if image:
            image_box = image.box()
            image_column = image_box.column()
            image_row = image_column.row()
            image_row.operator('object.reloadimage', text='Reload Images')
            image_row.operator('object.resizemesh', text='Resize Mesh')
            second_row = image_column.row()


        try:
            if act_obj.active_material and nodes['Tiling Scale']:
                header, bridge = layout.panel("bridge_panel", default_closed=False)
                header.label(text="Bridge Operator")
                if bridge:
                    bridge_box = bridge.box()
                    bridge_column = bridge_box.column()
                    bridge_row = bridge_column.row()
                    bridge_column.prop(nodes['Tiling Scale'].outputs['Value'], "default_value", text='Tiling Scale')
                    bridge_column.prop(nodes['Bump Strength'].outputs['Value'], "default_value", text='Bump Strength')
        except:
            pass

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
