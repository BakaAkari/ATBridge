import typing
import bpy
from bpy.types import Context
from bpy.utils import register_class, unregister_class
from .ATBFunctions import *
from .ATBProps import *
from mathutils import Matrix

import os
import PIL
from bpy.types import Node, Operator, NodeTree
from bpy.props import StringProperty, EnumProperty, IntProperty

# from PIL import Image


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


# class EVDisplacementOperator(bpy.types.Operator):
#     bl_idname = "object.evdisplacement"
#     bl_label = "实验性:创建eevee视差"

#     def execute(self, context):
#         actobj = bpy.context.active_object
#         actmat = actobj.active_material

#         vectorgroup = bpy.data.node_groups.new('Vector Group', 'ShaderNodeTree')
#         group_inputs = vectorgroup.nodes.new('NodeGroupInput')
#         group_inputs.location = (-350,0)
#         vectorgroup.inputs.new('NodeSocketFloat','in_to_greater')

#         # create group outputs
#         group_outputs = vectorgroup.nodes.new('NodeGroupOutput')
#         group_outputs.location = (300,0)
#         vectorgroup.outputs.new('NodeSocketVector','out_result')

#         nodegroup = actmat.node_tree.nodes.new('ShaderNodeGroup', 'Parallex Vector')
#         nodegroup.node_tree = vectorgroup
#         nodegroup.location = (-1300, 0)
#         return {'FINISHED'}

# MS_Init_ImportProcess is the main asset import class.
# This class is invoked whenever a new asset is set from Bridge.

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

#===========================================================================================================
class MergeBridgeTexOperator(bpy.types.Operator):
    bl_idname = "object.mergebridgetex"
    bl_label = "Merge Bridge Tex"

    def execute(self, context):
        actmat = bpy.context.active_object.active_material
        actnodetree = bpy.data.materials[actmat.name].node_tree

        ColNodeList = []
        ORMNodeList = []
        NrmNodeList = []
        DisNodeList = []

        for node in actnodetree.nodes:
            if node.type == "TEX_IMAGE":
                # 获取Albedo节点和贴图
                if node.name == "Color Tex Node":
                    colornode = node
                    ColNodeList.append(colornode)
                    parts = colornode.image.name.split('_')
                    BID = parts[0]

                # 获取AO节点和贴图
                if node.name == "AO Tex Node":
                    aonode = node
                    ORMNodeList.append(aonode)

                # 获取Roughness节点和贴图
                if node.name == "Roughness Tex Node":
                    roughnessnode = node
                    ORMNodeList.append(roughnessnode)

                # 获取Metalness节点和贴图
                if node.name == "Metalness Tex Node":
                    metalnessnode = node
                    ORMNodeList.append(metalnessnode)

                # 获取Normal节点和贴图
                if node.name == "Normal Tex Node":
                    normalnode = node
                    NrmNodeList.append(normalnode)

                # 获取Opacity节点和贴图
                if node.name == "Opacity Tex Node":
                    opacitynode = node
                    ColNodeList.append(opacitynode)

                # 获取Displacement节点和贴图
                if node.name == "Displacement Tex Node":
                    displacementnode = node
                    DisNodeList.append(displacementnode)
                    
        if ColNodeList:
            PILMergeCol(BID, ColNodeList)
            NewTexPath = PILMergeORM(BID, ORMNodeList)
            OrganizeImages(BID, NrmNodeList, DisNodeList)
            OpenSysDir(NewTexPath)
        else:
            messagebox(message="Not Bridge Material", title="WARNING", icon='INFO')
        return {'FINISHED'}

#===========================================================================================================
class ATBTestOperator(bpy.types.Operator):
    bl_idname = "object.atbtestoperator"
    bl_label = "ATBTestOperator"

    def execute(self, context):
        print("Test")
        return {'FINISHED'}
    
#===========================================================================================================


#===========================================================================================================

classes = (
    # FixBridgeToolsPanel,
    AddSubdivisionOperator,
    ChangeProjectionOperator,
    Reload_Image_Operator,
    MergeBridgeTexOperator,
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
