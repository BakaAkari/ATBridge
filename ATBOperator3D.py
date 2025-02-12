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
