# ATBridge 节点操作符
"""
节点操作符模块

包含节点编辑器相关操作：细分、投影切换、UE PBR节点组导入、图像重载。
"""
import bpy
import os
from bpy.utils import register_class, unregister_class

from ..config import MaterialNodes
from ..utils.common import ATOperationError, get_active_material_nodes


class NodeSubdivisionOperator(bpy.types.Operator):
    """添加自适应细分修改器"""
    bl_idname = "atb.node_add_subdivision"
    bl_label = "开启自适应细分"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            actobj = context.active_object
            
            if not actobj:
                self.report({'ERROR'}, "没有选中的对象")
                return {'CANCELLED'}
            
            if actobj.type != 'MESH':
                self.report({'ERROR'}, "选中的对象不是网格对象")
                return {'CANCELLED'}

            # 检查是否已经有曲面细分修改器
            has_subsurf = any(mod.type == MaterialNodes.SUBSURF for mod in actobj.modifiers)
            
            if not has_subsurf:
                subd_mod = actobj.modifiers.new(name=MaterialNodes.BRIDGE_DISPLACEMENT, type=MaterialNodes.SUBSURF)
                subd_mod.subdivision_type = "SIMPLE"
                actobj.cycles.use_adaptive_subdivision = True
                self.report({'INFO'}, "已添加自适应细分修改器")
            else:
                self.report({'INFO'}, "对象已有曲面细分修改器")

            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"添加细分修改器失败: {str(e)}")
            return {'CANCELLED'}


class NodeProjectionOperator(bpy.types.Operator):
    """切换材质投影模式"""
    bl_idname = "atb.node_toggle_projection"
    bl_label = "Toggle map mapping"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            actobj = context.active_object
            
            if not actobj or not actobj.active_material:
                self.report({'ERROR'}, "对象没有活动材质")
                return {'CANCELLED'}
            
            # 获取材质节点
            nodes = get_active_material_nodes(actobj)
            links = actobj.active_material.node_tree.links
            
            # 查找节点
            texcoord_node = None
            mapping_node = None
            current_projection = None
            
            for node in nodes:
                if node.type == MaterialNodes.TEX_COORD:
                    texcoord_node = node
                elif node.type == MaterialNodes.MAPPING:
                    mapping_node = node
                elif node.type == MaterialNodes.TEX_IMAGE:
                    current_projection = node.projection
                    if current_projection == MaterialNodes.PROJECTION_BOX:
                        node.projection_blend = MaterialNodes.DEFAULT_PROJECTION_BLEND
            
            if not texcoord_node or not mapping_node:
                self.report({'ERROR'}, "材质缺少必要的节点（纹理坐标或映射节点）")
                return {'CANCELLED'}

            # 切换投影模式
            for node in nodes:
                if node.type == MaterialNodes.TEX_IMAGE:
                    if current_projection == MaterialNodes.PROJECTION_BOX:
                        node.projection = MaterialNodes.PROJECTION_FLAT
                        links.new(texcoord_node.outputs["UV"], mapping_node.inputs["Vector"])
                        self.report({'INFO'}, "已切换到平面投影")
                    elif current_projection == MaterialNodes.PROJECTION_FLAT:
                        node.projection = MaterialNodes.PROJECTION_BOX
                        links.new(texcoord_node.outputs["Object"], mapping_node.inputs["Vector"])
                        self.report({'INFO'}, "已切换到盒式投影")
                        
            return {'FINISHED'}
            
        except ATOperationError as e:
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"切换投影模式失败: {str(e)}")
            return {'CANCELLED'}


class CreateUEPBRNodeGroupOperator(bpy.types.Operator):
    """从assets.blend文件中link UE Shader节点组"""
    bl_idname = "atb.node_create_ue_pbr_group"
    bl_label = "Create UE PBR Node Group"
    bl_description = "从assets.blend文件中链接Unreal Engine规则的PBR材质节点组"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            # 检查是否已存在UE Shader节点组
            existing_group = bpy.data.node_groups.get("UE Shader")
            if existing_group:
                self.report({'INFO'}, "节点组 'UE Shader' 已存在，可直接使用")
                return {'FINISHED'}
            
            # 获取插件目录路径
            addon_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
            assets_path = os.path.join(addon_dir, "assets", "ue_shader.blend")
            
            # 检查assets.blend文件是否存在
            if not os.path.exists(assets_path):
                self.report({'ERROR'}, f"找不到assets.blend文件: {assets_path}")
                return {'CANCELLED'}
            
            # 从assets.blend文件中link UE Shader节点组
            with bpy.data.libraries.load(assets_path, link=True) as (data_from, data_to):
                if "UE Shader" in data_from.node_groups:
                    data_to.node_groups = ["UE Shader"]
                else:
                    self.report({'ERROR'}, "assets.blend文件中未找到'UE Shader'节点组")
                    return {'CANCELLED'}
            
            # 验证节点组是否成功加载
            if bpy.data.node_groups.get("UE Shader"):
                self.report({'INFO'}, "成功加载 UE Shader 节点组")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, "加载节点组失败")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"加载节点组失败: {str(e)}")
            return {'CANCELLED'}


class ImageReloadOperator(bpy.types.Operator):
    """重新加载所有图像"""
    bl_idname = "atb.image_reload_all"
    bl_label = "Reload Image"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        try:
            all_images = bpy.data.images
            reloaded_count = 0
            failed_images = []
            
            for image in all_images:
                try:
                    if image.filepath:  # 只重载有文件路径的图像
                        image.reload()
                        reloaded_count += 1
                        print(f"重载图像: {image.name}")
                except Exception as e:
                    failed_images.append(f"{image.name}: {str(e)}")
            
            # 报告结果
            if reloaded_count > 0:
                self.report({'INFO'}, f"成功重载 {reloaded_count} 个图像")
            
            if failed_images:
                error_msg = "重载失败的图像:\n" + "\n".join(failed_images[:3])
                if len(failed_images) > 3:
                    error_msg += f"\n... 还有 {len(failed_images) - 3} 个图像失败"
                self.report({'WARNING'}, error_msg)
            
            if reloaded_count == 0 and not failed_images:
                self.report({'INFO'}, "没有找到需要重载的图像")

            return {'FINISHED'}
            
        except Exception as e:
            self.report({'ERROR'}, f"重载图像失败: {str(e)}")
            return {'CANCELLED'}


classes = (
    NodeSubdivisionOperator,
    NodeProjectionOperator,
    CreateUEPBRNodeGroupOperator,
    ImageReloadOperator,
)


def register():
    for cls in classes:
        register_class(cls)


def unregister():
    for cls in reversed(classes):
        unregister_class(cls)
