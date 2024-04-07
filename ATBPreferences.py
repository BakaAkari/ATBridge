import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty,
                       FloatProperty, IntProperty, PointerProperty,
                       StringProperty)
from bpy.types import AddonPreferences, PropertyGroup
from bpy.utils import register_class, unregister_class
import zipfile
import os

class ATB_AddonPreferences(AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout: bpy.types.UILayout
        
        props = context.scene.atbprops
        layout = self.layout
        col = layout.column(align=True)
        box = col.box()
        col = box.column(align=True)
        col.prop(props, 'addonaddress', text="Plugins Location")
        col.operator('object.atbimportaddons', text='Update Plugins')
        col.operator(ATB_DefaultSetting.bl_idname,text="Optimize Blender settings")
        
# class ATB_ImportAddons(bpy.types.Operator):
#     bl_idname = "object.atbimportaddons"
#     bl_label = "更新插件库"
    
#     def execute(self, context):
#         keys = []
#         newaddonfilepath = context.scene.atbprops.addonaddress
#         customaddonlist = [
#                             'HOps', 
#                             'MACHIN3tools', 
#                             'MESHmachine',
#                             'batch_ops', 
#                             'Boxcutter', 
#                             'Fix_Quixel_Bridge_Addon', 
#                             'GoB', 
#                             'Node Kit',
#                             'smart_fill',
#                             'sculpt_paint_wheel',
#                             'better_fbx',
#                             'VertexGame_Tools',
#                             'Gaffer',
#         ]
#         defaultaddonlist = [
#                             'space_view3d_modifier_tools',
#                             'space_view3d_spacebar_menu',
#                             'object_collection_manager',
#                             'mesh_f2',
#                             'mesh_tools',
#                             'mesh_looptools',
#                             'node_wrangler',
#         ]

#         blenderaddonpath = __file__.split('\\')
#         addonpath = '\\'.join(blenderaddonpath[:-2])
#         for root,dirs,files in os.walk(newaddonfilepath):
#             for f in files:
#                 # print(f)
#                 if f == "VertexGame_Tools.zip":
#                     with zipfile.ZipFile(onlineaddonpath) as zf:
#                         zf.extractall(addonpath)
#                 else:
#                     onlineaddonpath = os.path.join(root,f)
#                     bpy.ops.preferences.addon_install(overwrite=True, filepath=onlineaddonpath)
#         bpy.ops.script.reload()
#         alladdonlist = customaddonlist + defaultaddonlist
#         for enab in alladdonlist:
#             try:
#                 bpy.ops.preferences.addon_enable(module=enab)
#             except:
#                 print(enab)

#         return{'FINISHED'}

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
#复制指定目录里的配置文件至配置文件夹内
#已废弃
        # newaddonfilepath = context.scene.addonprops.vgtautoipdatepath
        # blenderaddonpath = __file__.split('\\')
        # # print(newaddonfilepath)
        # sourceF = '\\'.join(blenderaddonpath[:-1])+'\\config'
        # targetF = '\\'.join(blenderaddonpath[:-4])+'\\config'
        # shutil.copytree(sourceF,targetF)

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

#=====================================================================================
# 设置快捷键
        # winmankeys = bpy.data.window_managers["WinMan"].keyconfigs
        # wm = bpy.context.window_manager
        # kc = wm.keyconfigs.addon
        # for key in winmankeys:
        #     if key.name == "Blender addon":
        #         for keymap in key.keymaps:
        #             if keymap.name == "3D View":
        #                 for keyitem in keymap.keymap_items:
        #                     if keyitem.idname == "wm.call_menu_pie":
        #                         # def register():
        #                         # km = kc.keymaps.new(name="3D View")
        #                         # kc.keymaps["3D View"].keymap_items.new("wm.call_menu_pie", type = "Q", value = "PRESS", ctrl = True, shift = True)

        #                         # bpy.data.window_managers["WinMan"].keyconfigs["Blender addon"].keymaps["3D View"].keymap_items["wm.call_menu_pie"].ctrl = True
        #                         # keyitem.key_modifier = "Q"
        #                         register_keymap("wm.call_menu_pie","Q",True,True,"PRESS")
        #                         # print(keyitem.ctrl_ui)
        #                         # keyitem.is_user_modified = True
        #                     # if keyitem.idname == "wm.call_menu":
        #                     #     # km = kc.keymaps.new(name="3D View")
        #                     #     kc.keymaps["3D View"].keymap_items.new("wm.call_menu", type = "Q", value = "PRESS", ctrl = False, shift = True)

        #                         # keyitem.shift_ui = True
        #             # if keymap.name == "Object Non-modal":
        #             #     for keyitem in keymap.keymap_items:
        #             #         if keyitem.idname == "wm.call_menu_pie":
        #             #             # km = kc.keymaps.new(name="3D View")
        #             #             kc.keymaps["3D View"].keymap_items.new("wm.call_menu_pie", type = "Q")

        #                         # keyitem.type = "Q"
        #             # if keymap.name == "Image":
        #             #     for keyitem in keymap.keymap_items:
        #             #         if keyitem.idname == "wm.call_menu_pie":
        #             #             # km = kc.keymaps.new(name="3D View")
        #             #             kc.keymaps["3D View"].keymap_items.new("wm.call_menu_pie", type = "Q")

        #                         # keyitem.type = "Q"
        # # MACHIN3toolsPreferences.activate_smart_vert()

        # # def update_activate_shading_pie(self, context):
        # #     activate(self, register=self.activate_shading_pie, tool="shading_pie")


        return{'FINISHED'}


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
