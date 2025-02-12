import bpy
from bpy.utils import register_class, unregister_class
from .ATBFunctions import *
from .ATBProps import *

class AddSubdivisionOperator(bpy.types.Operator):
    bl_idname = "object.addsubd"
    bl_label = "开启自适应细分"

    def execute(self, context):
        actobj: bpy.types.Object

        actobj = bpy.context.active_object
        act_scene = bpy.context.window.scene

        hassubsurf = 0

        if len(actobj.modifiers) == 0:
            subd_mod = actobj.modifiers.new(name="Bridge Dispalcement", type="SUBSURF")
            subd_mod.subdivision_type = "SIMPLE"
            actobj.cycles.use_adaptive_subdivision = True
        else:
            for i in actobj.modifiers:
                if i.type == "SUBSURF":
                    hassubsurf = 1
            if hassubsurf == 0 and len(actobj.modifiers) != 0:
                subd_mod = actobj.modifiers.new(name="Bridge Dispalcement", type="SUBSURF")
                subd_mod.subdivision_type = "SIMPLE"
                actobj.cycles.use_adaptive_subdivision = True

        return {'FINISHED'}


class ChangeProjectionOperator(bpy.types.Operator):
    bl_idname = "object.changeprojection"
    bl_label = "Toggle map mapping"

    def execute(self, context):
        actobj = bpy.context.active_object
        actmat = actobj.active_material
        texcoordnode = None
        texmapping = None
        links = bpy.data.materials[actmat.name].node_tree.links
        for node in actmat.node_tree.nodes:
            if node.type == "TEX_COORD":
                texcoordnode = node
            if node.type == "MAPPING":
                texmapping = node
            if node.type == "TEX_IMAGE":
                if node.projection == "BOX":
                    imgprojection = 'BOX'
                    node.projection_blend = 0.25
                elif node.projection == "FLAT":
                    imgprojection = 'FLAT'

        for node in actmat.node_tree.nodes:
            if node.type == "TEX_IMAGE" and imgprojection == 'BOX':
                node.projection = "FLAT"
                links.new(texcoordnode.outputs["UV"], texmapping.inputs["Vector"])
            if node.type == "TEX_IMAGE" and imgprojection == 'FLAT':
                node.projection = "BOX"
                links.new(texcoordnode.outputs["Object"], texmapping.inputs["Vector"])
        return {'FINISHED'}
#===========================================================================================================
class Reload_Image_Operator(bpy.types.Operator):
    bl_idname = "object.reloadimage"
    bl_label = "Reload Image"

    def execute(self, context):
        actobj = bpy.context.active_object
        all_images = bpy.data.images
        for image in all_images:
            print(image.name)
            image.reload()

        return {'FINISHED'}

class ATBTestOperator(bpy.types.Operator):
    bl_idname = "object.atbtestoperator"
    bl_label = "ATBTestOperator"

    def execute(self, context):
        print("Test")
        return {'FINISHED'}
    
#===========================================================================================================


#===========================================================================================================

classes = (
    AddSubdivisionOperator,
    ChangeProjectionOperator,
    Reload_Image_Operator,
    ATBTestOperator,
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
