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
    bl_label = "ATBridge Tools"
    bl_idname = "ATB_PT_tools_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = UIConstants.PANEL_CATEGORY
    bl_order = UIConstants.PANEL_ORDER_TOOLS
    
    def draw(self, context):
        layout = self.layout
        
        # 网格操作区
        box = layout.box()
        box.label(text=get_text("Tools"), icon='MESH_DATA')
        
        col = box.column(align=True)
        col.operator("atb.mesh_rename_by_collection", text=get_text("Rename"), icon='SORTALPHA')
        col.operator("atb.mesh_clean_attributes", text=get_text("Clean Attributes"), icon='BRUSH_DATA')
        col.operator("atb.mesh_resize_to_texture", text=get_text("Resize to Texture"), icon='TEXTURE')
        
        col.separator()
        col.operator("atb.image_reload_all", text=get_text("Reload Images"), icon='FILE_REFRESH')
        col.operator("atb.collection_sort", text=get_text("Sort Collection"), icon='SORTALPHA')
        
        # 物理模拟区
        self.draw_physics_section(context, layout)
    
    def draw_physics_section(self, context, layout):
        """绘制物理模拟区"""
        wm = context.window_manager
        
        if not hasattr(wm, 'atb_props') or wm.atb_props is None:
            layout.label(text="Properties not initialized", icon='ERROR')
            return
            
        atb_props = wm.atb_props
        
        box = layout.box()
        box.label(text=get_text("Physics"), icon='PHYSICS')
        
        # 物理参数
        col = box.column(align=True)
        col.prop(atb_props, "physics_collision_shape", text=get_text("Collision Shape"))
        col.prop(atb_props, "physics_collision_margin", text=get_text("Collision Margin"))
        col.prop(atb_props, "physics_friction", text=get_text("Friction"))
        col.prop(atb_props, "physics_time_scale", text=get_text("Time Scale"))
        col.prop(atb_props, "physics_solver_iterations", text=get_text("Solver Iterations"))
        col.prop(atb_props, "physics_restitution", text=get_text("Restitution"))
        col.prop(atb_props, "physics_split_impulse", text=get_text("Split Impulse"))
        
        col.separator()
        
        # 自定义碰撞体
        col.prop(atb_props, "physics_use_custom_colliders", text=get_text("Use Custom Colliders"))
        
        if atb_props.physics_use_custom_colliders:
            row = col.row()
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
        
        col.separator()
        
        # 物理操作按钮
        if atb_props.running_physics_calculation:
            # 模拟运行中：显示禁用的提示标签
            col.alert = True
            col.enabled = False
            col.label(text="模拟中... 按 ESC 应用结果", icon='TIME')
        else:
            # 未运行：显示可点击的计算按钮
            col.operator("atb.physics_calculate", text=get_text("Calculate"), icon='PLAY')


classes = (
    AT_UL_CustomColliderList,
    ATB_PT_ToolsPanel,
)


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
