# ATBridge 导入管理器
"""
资产导入流程管理模块

整合解析、导入、材质构建等流程，替代原有的 MS_Init_ImportProcess 类。
"""
import bpy
from typing import List, Optional, Tuple

from .asset_parser import AssetParser, AssetData
from .geometry_importer import GeometryImporter
from .material_builder import MaterialBuilder
from ..config import BridgeConfig
from ..utils.logger import ATBridgeLogger as log


class ImportManager:
    """资产导入管理器"""
    
    def __init__(self):
        """初始化导入管理器"""
        self.alembic_paths: List[List[str]] = []
        self.alembic_materials: List[bpy.types.Material] = []
    
    def process_dataset(self, json_data) -> bool:
        """
        处理完整的资产数据集
        
        Args:
            json_data: Megascans JSON 格式字符串或 bytes
        
        Returns:
            成功导入返回 True
        """
        try:
            # 处理 bytes 输入
            if isinstance(json_data, bytes):
                json_str = json_data.decode('utf-8')
            else:
                json_str = json_data
            
            # 解析资产
            assets = AssetParser.parse_json(json_str)
            if not assets:
                log.warning("没有解析到任何资产")
                return False
            
            # 逐个导入
            for asset in assets:
                self._import_single_asset(asset)
            
            log.info(f"成功导入 {len(assets)} 个资产")
            return True
            
        except Exception as e:
            log.error("资产导入失败", e)
            return False
    
    def _import_single_asset(self, asset: AssetData) -> None:
        """
        导入单个资产
        
        Args:
            asset: 解析后的资产数据
        """
        log.info(f"正在导入: {asset.name} (类型: {asset.type})")
        
        # 导入几何体
        objects, abc_paths = GeometryImporter.import_meshes(asset.meshes)
        
        # 构建材质
        builder = MaterialBuilder(asset)
        material = builder.build()
        
        # 赋予材质
        self._apply_material(objects, material, asset.type)
        
        # 处理特殊资产类型
        if asset.is_scatter and len(objects) > 1:
            self._setup_parent(asset, objects, 'Scatter')
        elif asset.type == BridgeConfig.ASSET_TYPE_3DPLANT and len(objects) > 1:
            self._setup_parent(asset, objects, 'Plant')
        
        # 记录 Alembic 数据（延迟导入）
        if abc_paths:
            self.alembic_paths.append(abc_paths)
            self.alembic_materials.append(material)
        
        log.info(f"导入完成: {asset.name}")
    
    def _apply_material(self, objects: List[bpy.types.Object], 
                       material: bpy.types.Material,
                       asset_type: str) -> None:
        """
        为对象应用材质
        
        Args:
            objects: 对象列表
            material: 材质
            asset_type: 资产类型
        """
        for obj in objects:
            if obj.type == 'MESH':
                obj.active_material = material
        
        # Surface/Atlas 类型需要为当前激活对象也设置材质
        if asset_type in [BridgeConfig.ASSET_TYPE_SURFACE, 
                          BridgeConfig.ASSET_TYPE_ATLAS]:
            act_obj = bpy.context.active_object
            if act_obj and act_obj.type == 'MESH':
                act_obj.active_material = material
    
    def _setup_parent(self, asset: AssetData, 
                     objects: List[bpy.types.Object],
                     parent_type: str) -> None:
        """
        创建空对象作为父级
        
        Args:
            asset: 资产数据
            objects: 子对象列表
            parent_type: 父对象类型描述
        """
        bpy.ops.object.empty_add(type='ARROWS')
        parent = bpy.context.active_object
        parent.name = f"{asset.id}_{asset.name}"
        
        for obj in objects:
            obj.parent = parent
        
        log.debug(f"创建 {parent_type} 父对象: {parent.name}")
    
    def get_alembic_data(self) -> Tuple[List[List[str]], List[bpy.types.Material]]:
        """
        获取待导入的 Alembic 数据
        
        Returns:
            (alembic_paths, materials) 元组
        """
        return self.alembic_paths, self.alembic_materials
    
    def has_pending_alembic(self) -> bool:
        """检查是否有待导入的 Alembic"""
        return len(self.alembic_paths) > 0
