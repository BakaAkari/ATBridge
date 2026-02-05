# ATBridge 几何体导入器
"""
几何体导入模块

负责导入 FBX、OBJ、Alembic 等格式的 3D 模型。
"""
import bpy
from typing import List, Tuple

from ..compat.blender_compat import BlenderCompat
from ..utils.logger import ATBridgeLogger as log
from .asset_parser import MeshInfo


class GeometryImporter:
    """几何体导入器"""
    
    @classmethod
    def import_meshes(cls, meshes: List[MeshInfo]) -> Tuple[List[bpy.types.Object], List[str]]:
        """
        导入模型列表
        
        Args:
            meshes: 模型信息列表
        
        Returns:
            Tuple[imported_objects, alembic_paths]:
                - imported_objects: 成功导入的对象列表
                - alembic_paths: Alembic 文件路径（需延迟导入）
        """
        imported_objects: List[bpy.types.Object] = []
        alembic_paths: List[str] = []
        
        for mesh in meshes:
            mesh_format = mesh.format.lower()
            
            if mesh_format == 'fbx':
                objs = cls._import_fbx(mesh.path)
                imported_objects.extend(objs)
                
            elif mesh_format == 'obj':
                objs = cls._import_obj(mesh.path)
                imported_objects.extend(objs)
                
            elif mesh_format == 'abc':
                alembic_paths.append(mesh.path)
        
        log.info(f"导入了 {len(imported_objects)} 个对象, {len(alembic_paths)} 个 Alembic 待处理")
        return imported_objects, alembic_paths
    
    @classmethod
    def _import_fbx(cls, filepath: str) -> List[bpy.types.Object]:
        """
        导入 FBX 文件
        
        Args:
            filepath: FBX 文件路径
        
        Returns:
            导入的对象列表
        """
        try:
            params = BlenderCompat.get_fbx_import_params()
            bpy.ops.import_scene.fbx(filepath=filepath, **params)
            selected = cls._get_selected_objects()
            log.debug(f"FBX 导入成功: {filepath} ({len(selected)} 个对象)")
            return selected
        except Exception as e:
            log.error(f"FBX 导入失败: {filepath}", e)
            return []
    
    @classmethod
    def _import_obj(cls, filepath: str) -> List[bpy.types.Object]:
        """
        导入 OBJ 文件
        
        Args:
            filepath: OBJ 文件路径
        
        Returns:
            导入的对象列表
        """
        try:
            params = BlenderCompat.get_obj_import_params()
            bpy.ops.import_scene.obj(filepath=filepath, **params)
            selected = cls._get_selected_objects()
            log.debug(f"OBJ 导入成功: {filepath} ({len(selected)} 个对象)")
            return selected
        except Exception as e:
            log.error(f"OBJ 导入失败: {filepath}", e)
            return []
    
    @classmethod
    def import_alembic(cls, filepath: str) -> List[bpy.types.Object]:
        """
        导入 Alembic 文件
        
        Args:
            filepath: Alembic 文件路径
        
        Returns:
            导入的对象列表
        """
        try:
            bpy.ops.wm.alembic_import(filepath=filepath, as_background_job=False)
            selected = cls._get_selected_objects()
            log.debug(f"Alembic 导入成功: {filepath} ({len(selected)} 个对象)")
            return selected
        except Exception as e:
            log.error(f"Alembic 导入失败: {filepath}", e)
            return []
    
    @staticmethod
    def _get_selected_objects() -> List[bpy.types.Object]:
        """获取当前选中的对象"""
        return [o for o in bpy.context.scene.objects if o.select_get()]
