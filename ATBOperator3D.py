import os
import bpy
from bpy.utils import register_class, unregister_class
from .ATBFunctions import *
from mathutils import Matrix

class OptiEVRenderOperator(bpy.types.Operator):
    bl_idname = "object.optievrender"
    bl_label = "最优EV设置"

    def execute(self, context):
        actobj: bpy.types.Object

        actobj = bpy.context.active_object
        actmat = actobj.active_material
        act_scene = bpy.context.window.scene
        # 设置eevee参数
        bpy.context.scene.render.engine = 'BLENDER_EEVEE_NEXT'
        # 设置渲染参数
        bpy.data.scenes[act_scene.name].eevee.taa_samples = 0
        bpy.data.scenes[act_scene.name].eevee.taa_render_samples = 512
        #AO
        bpy.context.scene.eevee.use_gtao = True
        bpy.context.scene.eevee.gtao_quality = 1
        #光线追踪
        bpy.context.scene.eevee.use_raytracing = True
        #体积
        bpy.context.scene.eevee.volumetric_tile_size = '4'
        bpy.context.scene.eevee.volumetric_sample_distribution = 1
        bpy.context.scene.eevee.use_volumetric_shadows = True
        bpy.context.scene.eevee.volumetric_shadow_samples = 64
        #阴影
        bpy.context.scene.eevee.shadow_ray_count = 3
        #高品质法线
        bpy.context.scene.render.use_high_quality_normals = True
        #色彩管理
        bpy.context.scene.view_settings.look = 'AgX - High Contrast'
        bpy.context.scene.render.image_settings.compression = 0

        return {'FINISHED'}


class OptiCYRenderOperator(bpy.types.Operator):
    bl_idname = "object.opticyrender"
    bl_label = "最优CY设置"

    def execute(self, context):
        actobj: bpy.types.Object

        actobj = bpy.context.active_object
        actmat = actobj.active_material
        act_scene = bpy.context.window.scene
        # 设置cycles参数
        bpy.context.scene.render.engine = 'CYCLES'
        bpy.data.scenes[act_scene.name].cycles.feature_set = 'EXPERIMENTAL'
        bpy.data.scenes["Scene"].cycles.device = 'GPU'
        # 设置渲染参数
        bpy.context.scene.cycles.preview_adaptive_threshold = 0.01
        bpy.context.scene.cycles.use_preview_denoising = True
        bpy.context.scene.cycles.tile_size = 512
        bpy.context.scene.view_settings.look = 'AgX - High Contrast'
        bpy.context.scene.render.image_settings.compression = 0

        return {'FINISHED'}

class Resize_Mesh_Operator(bpy.types.Operator):
    bl_idname = "object.resizemesh"
    bl_label = "Resize Size Mesh"

    def execute(self, context):
        sel_objs = bpy.context.selected_objects
        for obj in sel_objs:
            mat_nodes = obj.active_material.node_tree.nodes
            for node in mat_nodes:
                if node.type == 'TEX_IMAGE':
                    print(node.image.size[0])
                    image_x = node.image.size[0] * 0.001
                    image_y = node.image.size[1] * 0.001

            obj.data.vertices[0].co[0] = image_x * -1
            obj.data.vertices[1].co[0] = image_x
            obj.data.vertices[2].co[0] = image_x * -1
            obj.data.vertices[3].co[0] = image_x

            obj.data.vertices[0].co[1] = image_y * -1
            obj.data.vertices[1].co[1] = image_y * -1
            obj.data.vertices[2].co[1] = image_y
            obj.data.vertices[3].co[1] = image_y
        return {'FINISHED'}


class Rename_Operator(bpy.types.Operator):
    bl_idname = "object.rename"
    bl_label = "Rename"

    def execute(self, context):
        obj: bpy.types.Object

        sel_objs = bpy.context.selected_objects
        act_obj = bpy.context.active_object
        collname = bpy.context.collection.name

        for i, obj in enumerate(bpy.data.collections[act_obj.users_collection[0].name].all_objects):
            if obj.type == 'MESH':
                obj.name = bpy.data.collections[obj.users_collection[0].name].name + '_' + str(i + 1).zfill(2)
                bpy.data.meshes[obj.to_mesh().name].name = bpy.data.collections[
                                                               obj.users_collection[0].name].name + '_' + str(
                    i + 1).zfill(2)
                if len(obj.material_slots) > 1:
                    messagebox('Have many material', title="WARNING", icon='INFO')
                else:
                    print(obj.material_slots)
                    if len(obj.material_slots) == 0:
                        messagebox(obj.name + ': ' + 'Not have material', title="WARNING", icon='INFO')
                    else:
                        bpy.data.materials[obj.material_slots[0].name].name = bpy.data.collections[
                            obj.users_collection[0].name].name
        return {'FINISHED'}


class CleanObjectOperator(bpy.types.Operator):
    bl_idname = "object.cleanobject"
    bl_label = "初始化模型信息"

    def execute(self, context):
        selection = bpy.context.selected_objects
        for o in selection:
            try:
                bpy.context.view_layer.objects.active = o
                bpy.ops.object.editmode_toggle()
                bpy.ops.mesh.select_all(action='SELECT')
                bpy.ops.mesh.mark_sharp(clear=True)
                bpy.ops.mesh.mark_seam(clear=True)
                bpy.ops.transform.edge_crease(value=-1)
                bpy.ops.transform.edge_bevelweight(value=-1)
                bpy.ops.object.editmode_toggle()
                bpy.ops.mesh.customdata_custom_splitnormals_clear()

            except:
                print("Object has no custom split normals: " + o.name + ", skipping")
        return {'FINISHED'}


class ReSetOriginOperator(bpy.types.Operator):
    bl_idname = "object.resetorigin"
    bl_label = "Reset Origin"

    def execute(self, context):
        selobj = bpy.context.selected_objects
        for i in selobj:
            bpy.context.view_layer.objects.active = i
            print(bpy.data.objects[i.name_full].dimensions.z)
        return {'FINISHED'}


#===========================================================================================================

class Translation(bpy.types.Operator):
    bl_idname = "object.translation"
    bl_label = "切换中英文"

    def execute(self, context):
        viewlanguage = context.preferences.view.language
        prefview = context.preferences.view
        if viewlanguage != "en_US":
            context.preferences.view.language = "en_US"
        else:
            try:
                context.preferences.view.language = "zh_CN"
            except:
                context.preferences.view.language = "zh_HANS"
            prefview.use_translate_new_dataname = False
        return {'FINISHED'}


#===========================================================================================================
class ExportFBX(bpy.types.Operator):
    bl_idname = "object.exportfbx"
    bl_label = "导出FBX"

    def execute(self, context):
        wm = context.window_manager
        props = wm.atbprops
        exportpath = props.exportpath
        absexportpath = bpy.path.abspath(exportpath)
        # 获取当前选中的对象
        selected_objs = [obj for obj in bpy.context.selected_objects if obj.type == 'MESH']

        if selected_objs is None:
            print("没有选中的对象！")
            return

        # 逐个导出选中的对象为FBX文件
        for obj in selected_objs:
            # 获取对象名称作为文件名
            file_name = obj.name + ".fbx"
            output_path = os.path.join(absexportpath, file_name)

            # 确保路径的格式和目录存在
            output_path = os.path.normpath(output_path)  # 规范路径格式

            # 确保目录存在
            output_dir_path = os.path.dirname(output_path)
            if not os.path.exists(output_dir_path):
                os.makedirs(output_dir_path)

            # # 选择当前对象
            # bpy.ops.object.select_all(action='DESELECT')  # 取消选择所有对象
            # obj.select_set(True)  # 选择当前对象

            # 检查对象是否包含关联子项，并将符合条件的子项加入导出列表
            objects_to_export = [obj]  # 主对象
            if obj.children:  # 检查是否有子项
                for child in obj.children:
                    # 判断子项是否为关联子项且类型为 "MESH"
                    if child.parent == obj and child.type == 'MESH':
                        objects_to_export.append(child)

            # 选择所有需要导出的对象
            bpy.ops.object.select_all(action='DESELECT')  # 取消选择所有对象
            for obj_to_export in objects_to_export:
                obj_to_export.select_set(True)  # 选择当前对象或子项

            # 导出当前对象为FBX文件
            if props.export_rule == 'UNREAL':
                bpy.ops.export_scene.fbx(filepath=output_path, use_selection=True, bake_space_transform=False, axis_forward='-Z', axis_up='Y')
            elif props.export_rule == 'UNITY':
                bpy.ops.export_scene.fbx(filepath=output_path, use_selection=True, bake_space_transform=True, axis_forward='-X', axis_up='Y')
            print(f"导出成功: {output_path}")

        return {'FINISHED'}


#===========================================================================================================
class QuickPhysics_CalcPhysics(bpy.types.Operator):
    bl_idname = "quick_physics.calc_physics"
    bl_label = "Calculate Physics"
    bl_description = ""
    bl_options = {"REGISTER"}

    def __init__(self):
        fps = 0
        frame_start = 0
        frame_end = 0
        frame_current = 0
        world_enabled = True
        use_split_impulse = True
        world_time_scale = 1.0

    @classmethod
    def poll(cls, context):
        return True

    def add_passive_bodies(self, context, add):
        quick_physics = context.window_manager.quick_physics
        active_object = context.active_object

        for obj in context.visible_objects:
            if not obj.select_get() and obj.type == "MESH":
                context.view_layer.objects.active = obj
                if add and obj.rigid_body == None:
                    bpy.ops.rigidbody.object_add()
                    obj.rigid_body.friction = quick_physics.physics_friction
                    obj.rigid_body.use_margin = True
                    obj.rigid_body.collision_margin = 0.0001
                    obj.rigid_body.type = "PASSIVE"
                    obj.rigid_body.collision_shape = "MESH"
                elif not add and obj.rigid_body != None:
                    bpy.ops.rigidbody.object_remove()

        context.view_layer.objects.active = canvas = active_object

    def invoke(self, context, event):

        mesh_objects = 0
        for obj in context.selected_objects:
            if obj.type == "MESH":
                mesh_objects += 1
                break
        if mesh_objects == 0:
            self.report({'WARNING'}, 'No Objects for Physics selected.')
            return {"CANCELLED"}

        wm = context.window_manager
        quick_physics = context.window_manager.quick_physics
        wm.modal_handler_add(self)
        quick_physics.running_physics_calculation = True

        if context.scene.rigidbody_world == None:
            bpy.ops.rigidbody.world_add()

        self.fps = context.scene.render.fps
        self.frame_start = context.scene.frame_start
        self.frame_end = context.scene.frame_end
        self.frame_current = context.scene.frame_current
        self.world_enabled = context.scene.rigidbody_world.enabled
        self.use_split_impulse = context.scene.rigidbody_world.use_split_impulse
        self.world_time_scale = context.scene.rigidbody_world.time_scale

        context.scene.rigidbody_world.time_scale = quick_physics.physics_time_scale
        context.scene.render.fps = 24
        context.scene.frame_start = 0
        context.scene.frame_end = 10000
        context.scene.frame_current = 0
        context.scene.rigidbody_world.enabled = True
        context.scene.rigidbody_world.use_split_impulse = True

        self.add_passive_bodies(context, True)

        bpy.ops.object.as_add_active_physics()

        bpy.ops.screen.animation_play()

        tot = context.scene.frame_end
        wm.progress_begin(0, tot)
        return {"RUNNING_MODAL"}

    def exit_modal(self, context, wm):
        quick_physics = context.window_manager.quick_physics
        quick_physics.running_physics_calculation = False
        bpy.ops.screen.animation_play()
        bpy.ops.object.as_apply_physics()
        # bpy.ops.screen.animation_cancel()

        context.scene.render.fps = self.fps
        context.scene.frame_start = self.frame_start
        context.scene.frame_end = self.frame_end
        context.scene.frame_current = self.frame_current
        context.scene.rigidbody_world.enabled = self.world_enabled
        context.scene.rigidbody_world.use_split_impulse = self.use_split_impulse
        context.scene.rigidbody_world.time_scale = self.world_time_scale

        self.add_passive_bodies(context, False)
        wm.progress_end()
        bpy.ops.ed.undo_push(message="Calc Physics")

    def modal(self, context, event):
        wm = context.window_manager
        quick_physics = context.window_manager.quick_physics
        if event.type in {
            "ESC"} or context.scene.frame_current >= 10000 or not quick_physics.running_physics_calculation:
            self.exit_modal(context, wm)
            return {"CANCELLED"}
        wm.progress_update(context.scene.frame_current)
        return {"PASS_THROUGH"}


class QuickPhysics_AddActivePhysics(bpy.types.Operator):
    bl_idname = "object.as_add_active_physics"
    bl_label = "Add physics to Assets"
    bl_description = "Sets up Assets as rigidbody objects."

    def execute(self, context):
        quick_physics = context.window_manager.quick_physics
        active_object = context.active_object
        for obj in context.selected_objects:
            if obj.type == "MESH":
                context.view_layer.objects.active = obj
                bpy.ops.rigidbody.object_add()
                obj.rigid_body.friction = quick_physics.physics_friction
        context.view_layer.objects.active = active_object

        return {'FINISHED'}


class QuickPhysics_ApplyPhysics(bpy.types.Operator):
    bl_idname = "object.as_apply_physics"
    bl_label = "Apply physics to Assets"
    bl_description = "Applies physics to assets and removes rigidbodies."

    def execute(self, context):
        active_object = context.active_object

        obj_transformation = []
        context.view_layer.update()

        for obj in context.selected_objects:
            obj_transformation.append({"obj": obj, "matrix_world": Matrix(obj.matrix_world)})

        for data in obj_transformation:
            obj = bpy.data.objects[data["obj"].name]

            context.view_layer.objects.active = obj
            bpy.ops.object.visual_transform_apply()
            bpy.ops.rigidbody.object_remove()

            obj.matrix_world = data["matrix_world"]

        context.view_layer.objects.active = active_object

        return {'FINISHED'}


#===========================================================================================================

class Setstartframe(bpy.types.Operator):
    bl_idname = "object.setstartframe"
    bl_label = "SetStartFrame"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        try:
            pass  # Set Start Frame Script Start
            import bpy
            actscene = bpy.context.scene
            bpy.data.scenes[actscene.name].frame_start = bpy.data.scenes[actscene.name].frame_current
            pass  # Set Start Frame Script End
        except Exception as exc:
            print(str(exc) + " | Error in execute function of SetStartFrame")
        return {"FINISHED"}

    def invoke(self, context, event):
        try:
            pass
        except Exception as exc:
            print(str(exc) + " | Error in invoke function of SetStartFrame")
        return self.execute(context)


class Setendframe(bpy.types.Operator):
    bl_idname = "object.setendframe"
    bl_label = "SetEndFrame"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        try:
            pass  # Set End Frame Script Start
            import bpy
            actscene = bpy.context.scene
            bpy.data.scenes[actscene.name].frame_end = bpy.data.scenes[actscene.name].frame_current
            pass  # Set End Frame Script End
        except Exception as exc:
            print(str(exc) + " | Error in execute function of SetEndFrame")
        return {"FINISHED"}

    def invoke(self, context, event):
        try:
            pass
        except Exception as exc:
            print(str(exc) + " | Error in invoke function of SetEndFrame")
        return self.execute(context)


class StopLoop_OP(bpy.types.Operator):
    bl_idname = "object.stoploop"
    bl_label = "StopLoop"

    def execute(self, context):
        frame_change = bpy.app.handlers.frame_change_pre
        actscene = bpy.context.scene

        if stop_playback not in frame_change:
            stop_playback(bpy.data.scenes[actscene.name])
            frame_change.append(stop_playback)
        elif stop_playback in frame_change:
            start_playback(bpy.data.scenes[actscene.name])
            del frame_change[-1]

        print(list(frame_change))
        return {'FINISHED'}
#===========================================================================================================
class ATB3DTestOperator(bpy.types.Operator):
    bl_idname = "object.atb3dtestoperator"
    bl_label = "ATBTestOperator"

    def execute(self, context):
        actmat = bpy.context.active_object.active_material
        return {'FINISHED'}



#===========================================================================================================
classes = (
    OptiEVRenderOperator,
    OptiCYRenderOperator,
    Resize_Mesh_Operator,
    Rename_Operator,
    CleanObjectOperator,
    ReSetOriginOperator,
    QuickPhysics_CalcPhysics,
    QuickPhysics_AddActivePhysics,
    QuickPhysics_ApplyPhysics,
    Translation,
    Setstartframe,
    Setendframe,
    StopLoop_OP,
    ExportFBX,
    ATB3DTestOperator,
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
