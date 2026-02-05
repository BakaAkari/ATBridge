# ATBridge 节点编辑器面板
"""
节点编辑器面板

包含节点操作工具的 UI 面板。
"""
import bpy
from bpy.types import Panel
from bpy.utils import register_class, unregister_class

from ..config import UIConstants
from ..utils.translation import get_text


class ATB_PT_NodePanel(Panel):
    """ATBridge 节点编辑器面板"""
    bl_label = "ATBridge Node Tools"
    bl_idname = "ATB_PT_node_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = UIConstants.PANEL_CATEGORY
    bl_order = UIConstants.PANEL_ORDER_NODE
    
    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ShaderNodeTree'
    
    def draw(self, context):
        layout = self.layout
        
        # 节点工具区
        box = layout.box()
        box.label(text=get_text("Node Tools"), icon='NODETREE')
        
        col = box.column(align=True)
        col.operator("atb.node_create_ue_pbr_group", text=get_text("Import UE PBR"), icon='IMPORT')
        col.operator("atb.node_toggle_projection", text=get_text("Toggle Projection"), icon='MOD_UVPROJECT')
        col.operator("atb.node_add_subdivision", text=get_text("Add Subdivision"), icon='MOD_SUBSURF')
        
        col.separator()
        col.operator("atb.image_reload_all", text=get_text("Reload Images"), icon='FILE_REFRESH')


classes = (
    ATB_PT_NodePanel,
)


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
