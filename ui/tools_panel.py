# ATBridge 工具面板
"""
3D 视图侧边栏工具面板

包含网格操作、物理模拟等工具的 UI 面板。
"""
import bpy
from bpy.types import Panel, UIList
from bpy.utils import register_class, unregister_class

from ..config import UIConstants
from ..utils.translation import get_text


class AT_UL_CustomColliderList(UIList):
    """自定义碰撞体列表 UI"""
    bl_idname = "ATB_UL_custom_collider_list"
    
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            if item.obj:
                layout.label(text=item.obj.name, icon='MESH_CUBE')
            else:
                layout.label(text="[Missing Object]", icon='ERROR')
        elif self.layout_type == 'GRID':
            layout.alignment = 'CENTER'
            layout.label(text="", icon='MESH_CUBE')


class ATB_PT_ToolsPanel(Panel):
    """ATBridge 工具面板"""
    bl_label = "Tools"
    bl_idname = "ATB_PT_tools_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UIConstants.PANEL_CATEGORY
    bl_order = UIConstants.PANEL_ORDER_TOOLS
    bl_options = {'DEFAULT_CLOSED'}
    
    def draw(self, context):
        layout = self.layout
        
        layout.label(text=get_text('网格处理'), icon='MESH_DATA')
        # Avoid squeezing the longer labels when the N-panel is narrow.
        columns = 2 if context.region.width / context.preferences.system.ui_scale >= 360 else 1
        grid = layout.grid_flow(columns=columns, even_columns=True, align=True)
        grid.operator('atb.mesh_rename_by_collection', text=get_text('Rename'), icon='SORTALPHA')
        grid.operator('atb.mesh_clean_attributes', text=get_text('Clean Attributes'), icon='BRUSH_DATA')
        row = layout.row()
        row.operator('atb.mesh_resize_to_texture', text=get_text('Resize to Texture'), icon='TEXTURE')
        layout.separator()
        layout.label(text=get_text('场景维护'), icon='OUTLINER_COLLECTION')
        grid = layout.grid_flow(columns=columns, even_columns=True, align=True)
        grid.operator('atb.image_reload_all', text=get_text('Reload Images'), icon='FILE_REFRESH')
        grid.operator('atb.collection_sort', text=get_text('Sort Collection'), icon='SORTALPHA')


class ATB_PT_PhysicsPanel(Panel):
    bl_label = 'Physics Simulation'
    bl_idname = 'ATB_PT_physics_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UIConstants.PANEL_CATEGORY
    bl_order = UIConstants.PANEL_ORDER_TOOLS + 1
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        atb_props = getattr(context.window_manager, 'atb_props', None)
        if atb_props is None:
            layout.label(text="Properties not initialized", icon='ERROR')
            return
        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column(align=True)
        col.enabled = not atb_props.running_physics_calculation
        col.prop(atb_props, "physics_collision_shape", text=get_text("Collision Shape"))
        col.prop(atb_props, "physics_collision_margin", text=get_text("Collision Margin"))
        col.separator()
        col.prop(atb_props, "physics_friction", text=get_text("Friction"))
        col.prop(atb_props, "physics_restitution", text=get_text("Restitution"))
        layout.separator()
        row = layout.row()
        row.scale_y = 1.4
        if atb_props.running_physics_calculation:
            row.enabled = False
            row.label(text=get_text('模拟中 · 按 ESC 应用结果'), icon='TIME')
        else:
            row.operator('atb.physics_calculate', text=get_text('开始模拟'), icon='PLAY')


class ATB_PT_PhysicsColliders(Panel):
    bl_label = 'Custom Colliders'
    bl_idname = 'ATB_PT_physics_colliders'
    bl_parent_id = 'ATB_PT_physics_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UIConstants.PANEL_CATEGORY
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 0

    def draw(self, context):
        layout = self.layout
        atb_props = context.window_manager.atb_props
        layout.enabled = not atb_props.running_physics_calculation
        layout.prop(atb_props, 'physics_use_custom_colliders', text=get_text('Use Custom Colliders'))
        if atb_props.physics_use_custom_colliders:
            row = layout.row()
            row.template_list(
                "ATB_UL_custom_collider_list", "",
                atb_props, "physics_custom_colliders",
                atb_props, "physics_custom_collider_index",
                rows=3
            )
            
            col2 = row.column(align=True)
            col2.operator("atb.physics_get_custom_colliders", icon='ADD', text="")
            col2.operator("atb.physics_remove_custom_collider", icon='REMOVE', text="")
            col2.operator("atb.physics_clear_custom_colliders", icon='X', text="")


class ATB_PT_PhysicsAdvanced(Panel):
    bl_label = 'Simulation Settings'
    bl_idname = 'ATB_PT_physics_advanced'
    bl_parent_id = 'ATB_PT_physics_panel'
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UIConstants.PANEL_CATEGORY
    bl_options = {'DEFAULT_CLOSED'}
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        atb_props = context.window_manager.atb_props
        layout.enabled = not atb_props.running_physics_calculation
        layout.use_property_split = True
        layout.use_property_decorate = False
        col = layout.column(align=True)
        col.prop(atb_props, 'physics_time_scale', text=get_text('Time Scale'))
        col.prop(atb_props, 'physics_solver_iterations', text=get_text('Solver Iterations'))
        col.prop(atb_props, 'physics_split_impulse', text=get_text('Split Impulse'))


classes = (
    AT_UL_CustomColliderList,
    ATB_PT_ToolsPanel,
    ATB_PT_PhysicsPanel,
    ATB_PT_PhysicsColliders,
    ATB_PT_PhysicsAdvanced,
)


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
