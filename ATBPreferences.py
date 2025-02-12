import bpy
from bpy.types import AddonPreferences, PropertyGroup
from bpy.utils import register_class, unregister_class

class ATB_AddonPreferences(AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout: bpy.types.UILayout
        
        wm = context.window_manager
        props = wm.atbprops
        layout = self.layout
        col = layout.column(align=True)
        box = col.box()
        col = box.column(align=True)
        col.operator('object.atbinstallpil', text='Install PIL')
        col.operator(ATB_DefaultSetting.bl_idname, text="Optimize Blender settings")

class ATB_DefaultSetting(bpy.types.Operator):
    bl_idname = "object.vgtdefaultsetting"
    bl_label = "导入初始设置(会覆盖现有设置)"
    addon_keymaps = []

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        #=====================================================================================
        #设置machin3tools默认配置
        if 'MACHIN3tools' in bpy.context.preferences.addons:
            addonpre = bpy.context.preferences.addons['MACHIN3tools'].preferences
            addonpre.activate_smart_vert = True
            addonpre.activate_smart_edge = True
            addonpre.activate_smart_face = True
            addonpre.activate_clean_up = True
            addonpre.activate_edge_constraint = True
            addonpre.activate_extrude = True
            addonpre.activate_focus = True
            addonpre.activate_mirror = True
            addonpre.activate_align = True
            addonpre.activate_group = True
            addonpre.activate_smart_drive = True
            addonpre.activate_assetbrowser_tools = True
            addonpre.activate_filebrowser_tools = True
            addonpre.activate_render = True
            addonpre.activate_smooth = True
            addonpre.activate_clipping_toggle = True
            addonpre.activate_surface_slide = True
            addonpre.activate_material_picker = True
            addonpre.activate_apply = True
            addonpre.activate_select = True
            addonpre.activate_mesh_cut = True
            addonpre.activate_thread = True
            addonpre.activate_unity = True
            addonpre.activate_customize = True

            addonpre.activate_modes_pie = True
            addonpre.activate_save_pie = True
            addonpre.activate_shading_pie = True
            addonpre.activate_views_pie = True
            addonpre.activate_align_pie = True
            addonpre.activate_cursor_pie = True
            addonpre.activate_transform_pie = True
            addonpre.activate_snapping_pie = True
            addonpre.activate_collections_pie = True
            addonpre.activate_workspace_pie = True
            addonpre.activate_tools_pie = True
        else:
            print("MACHIN3tools missing")
        #=====================================================================================
        # 设置cycles渲染设备
        cyclespref = bpy.context.preferences.addons['cycles'].preferences
        cyclespref.compute_device_type = 'OPTIX'

        #修改默认配置选项至可用状态
        prefview = context.preferences.view
        prefsys = context.preferences.system
        prefinp = context.preferences.inputs
        prefedit = context.preferences.edit
        #界面设置
        prefview.show_developer_ui = True
        prefview.show_tooltips_python = True
        prefview.show_statusbar_memory = True
        prefview.show_statusbar_stats = True
        prefview.show_statusbar_vram = True
        #视图设置
        prefview.show_object_info = False
        prefview.show_view_name = False
        prefsys.viewport_aa = "32"
        prefsys.anisotropic_filter = "FILTER_16"
        #视图切换设置
        prefinp.use_mouse_depth_navigate = True

        context.preferences.view.language = "zh_HANS"
        prefview.use_translate_new_dataname = False
        #系统设置
        prefedit.undo_steps = 256

        #=====================================================================================
        #存储用户设置
        bpy.ops.preferences.associate_blend()
        bpy.ops.wm.save_userpref()

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)


#=====================================================================================


classes = (ATB_AddonPreferences, ATB_DefaultSetting)


def register():
    global classes
    for cls in classes:
        register_class(cls)


def unregister():
    global classes
    for cls in classes:
        unregister_class(cls)
