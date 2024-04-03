import typing
import bpy
from bpy.types import Context
from bpy.utils import register_class, unregister_class
from . ATBFunctions import *
from mathutils import Matrix

class ATB_Panel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_ATB"
    bl_label = "Akari Tool Bag"
    bl_category = "ATB"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    @classmethod
    def poll(cls, context):
        return (context.object is not None)

    def draw(self, context):
        props = context.scene.atbprops
        wm = context.window_manager
        layout = self.layout

        object_box = layout.box()
        object_column = object_box.column()
        object_column.label(text='Object Operator')
        object_column.operator('object.rename', text='Rename Object')
        object_column.operator('object.resetorigin', text='Reset Origin')
        object_column.operator('object.cleanobject', text='Clean Object')

        image_box = layout.box()
        image_column = image_box.column()
        image_row = image_column.row()
        image_column.label(text='Image Operator')
        image_column.operator('object.reloadimage', text='Reload Images')
        image_column.operator('object.resizemesh', text='Resize Mesh')


        row = layout.row()
        physics_box = layout.box()
        physics_column = physics_box.column()
        physics_column.label(text='Quick Physics')
        physics_column.prop(wm.quick_physics,'physics_friction', text="Friction",slider=True)
        physics_column.prop(wm.quick_physics,'physics_time_scale', text="Time Scale")
        if not wm.quick_physics.running_physics_calculation:
            physics_column.operator('quick_physics.calc_physics',text = "开始模拟")
        else:
            physics_column.prop(wm.quick_physics,'running_physics_calculation', text="Cancel Calculation",icon="X")

        physics_column.operator('object.atbtestoperator',text = "测试按钮")

class Reload_Image_Operator(bpy.types.Operator):
    bl_idname = "object.reloadimage"
    bl_label = "Reload Image"
    
    def execute(self, context):
        actobj = bpy.context.active_object
        all_images = bpy.data.images
        for image in all_images:
            print(image.name)
            image.reload()

        return{'FINISHED'}

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
                    image_x = node.image.size[0]*0.001
                    image_y = node.image.size[1]*0.001

            obj.data.vertices[0].co[0] = image_x*-1
            obj.data.vertices[1].co[0] = image_x
            obj.data.vertices[2].co[0] = image_x*-1
            obj.data.vertices[3].co[0] = image_x

            obj.data.vertices[0].co[1] = image_y*-1
            obj.data.vertices[1].co[1] = image_y*-1
            obj.data.vertices[2].co[1] = image_y
            obj.data.vertices[3].co[1] = image_y
        return{'FINISHED'}

class Rename_Operator(bpy.types.Operator):
    bl_idname = "object.rename"
    bl_label = "Rename"
    
    def execute(self, context):
        obj: bpy.types.Object

        sel_objs = bpy.context.selected_objects
        act_obj = bpy.context.active_object
        collname = bpy.context.collection.name

        for i,obj in enumerate(bpy.data.collections[act_obj.users_collection[0].name].all_objects):
            if obj.type=='MESH':
                obj.name = bpy.data.collections[obj.users_collection[0].name].name+'_'+str(i+1).zfill(2)
                bpy.data.meshes[obj.to_mesh().name].name = bpy.data.collections[obj.users_collection[0].name].name+'_'+str(i+1).zfill(2)
                if len(obj.material_slots) > 1:
                    MessageBox('Have many material')
                else:
                    print(obj.material_slots)
                    if len(obj.material_slots) == 0:
                        MessageBox(obj.name + ': ' + 'Not have material')
                    else:
                        bpy.data.materials[obj.material_slots[0].name].name = bpy.data.collections[obj.users_collection[0].name].name
        return{'FINISHED'}

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

    def execute(self,context):
        selobj = bpy.context.selected_objects
        for i in selobj:
            bpy.context.view_layer.objects.active = i
            print(bpy.data.objects[i.name_full].dimensions.z)
        return{'FINISHED'}

#===========================================================================================================

class Translation(bpy.types.Operator):
    bl_idname = "object.translation"
    bl_label = "切换中英文"

    def execute(self, context):
        viewlanguage = context.preferences.view.language
        prefview = context.preferences.view
        if viewlanguage == "zh_HANS":
            context.preferences.view.language = "en_US"
        else:
            context.preferences.view.language = "zh_HANS"
            prefview.use_translate_new_dataname = False
        return{'FINISHED'}

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
        if event.type in {"ESC"} or context.scene.frame_current >= 10000 or not quick_physics.running_physics_calculation:
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
            pass # Set Start Frame Script Start
            import bpy
            bpy.data.scenes["Scene"].frame_start = bpy.data.scenes["Scene"].frame_current
            pass # Set Start Frame Script End
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
            pass # Set End Frame Script Start
            import bpy
            bpy.data.scenes["Scene"].frame_end = bpy.data.scenes["Scene"].frame_current
            pass # Set End Frame Script End
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

        if stop_playback not in frame_change:
            stop_playback(bpy.data.scenes["Scene"])
            frame_change.append(stop_playback)
        elif stop_playback in frame_change:
            start_playback(bpy.data.scenes["Scene"])
            del frame_change[-1]

        print(list(frame_change))
        return {'FINISHED'}

#===========================================================================================================
class ATBTestOperator(bpy.types.Operator):
    bl_idname = "object.atbtestoperator"
    bl_label = "ATBTestOperator"

    def execute(self, context):
        clip_data = bpy.context.window_manager.clipboard

        print(clip_data)
        return {'FINISHED'}

classes = (
    ATB_Panel,
    Reload_Image_Operator,
    Resize_Mesh_Operator,
    Rename_Operator,
    CleanObjectOperator,
    ReSetOriginOperator,
    QuickPhysics_CalcPhysics,
    QuickPhysics_AddActivePhysics,
    QuickPhysics_ApplyPhysics,
    ATBTestOperator,
    Translation,
    Setstartframe,
    Setendframe,
    StopLoop_OP,
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