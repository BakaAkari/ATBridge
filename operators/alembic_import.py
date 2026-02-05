# ATBridge Alembic 导入操作符
"""
Alembic 延迟导入操作符

处理 LiveLink 过程中收集的 Alembic 文件路径，进行批量导入。
"""
import bpy

from ..state.bridge_state import BridgeState
from ..core.geometry_importer import GeometryImporter
from ..utils.logger import ATBridgeLogger as log


class MS_Init_Abc(bpy.types.Operator):
    """导入 Alembic 资产"""
    
    bl_idname = "atbridge.import_alembic"
    bl_label = "Import Alembic Assets"
    bl_description = "导入待处理的 Alembic 文件"
    
    def execute(self, context):
        """执行操作符"""
        try:
            if not BridgeState.get_import_complete():
                log.warning("没有待导入的 Alembic 文件")
                return {'CANCELLED'}
            
            abc_paths_list = BridgeState.get_alembic_paths()
            materials = BridgeState.get_materials()
            
            if not abc_paths_list or not materials:
                log.warning("Alembic 数据不完整")
                return {'CANCELLED'}
            
            old_materials = []
            
            # 遍历每个资产的 Alembic 路径列表
            for idx, abc_paths in enumerate(abc_paths_list):
                material = materials[idx] if idx < len(materials) else None
                
                for abc_path in abc_paths:
                    # 导入 Alembic
                    objects = GeometryImporter.import_alembic(abc_path)
                    
                    # 替换材质
                    for obj in objects:
                        if obj.type == 'MESH':
                            if obj.active_material:
                                old_materials.append(obj.active_material)
                            if material:
                                obj.active_material = material
            
            # 清理旧材质
            for mat in old_materials:
                try:
                    if mat and mat.users == 0:
                        bpy.data.materials.remove(mat)
                except Exception:
                    pass
            
            # 重置状态
            BridgeState.set_alembic_paths([])
            BridgeState.set_materials([])
            BridgeState.set_import_complete(False)
            
            log.info("Alembic 导入完成")
            return {'FINISHED'}
            
        except Exception as e:
            log.report_error(self, e, "Alembic 导入失败")
            return {'CANCELLED'}
