# ATBridge 资产解析器
"""
资产 JSON 解析模块

负责将 Megascans/Fab 格式的 JSON 数据解析为结构化的 Python 数据类。
"""
import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..config import BridgeConfig
from ..utils.logger import ATBridgeLogger as log


@dataclass
class TextureInfo:
    """贴图信息"""
    format: str
    type: str
    path: str


@dataclass
class MeshInfo:
    """模型信息"""
    format: str
    path: str


@dataclass
class AssetData:
    """
    解析后的资产数据结构
    
    包含导入资产所需的所有元数据和文件路径。
    """
    id: str
    name: str
    type: str
    path: Optional[str]
    
    # 贴图和模型
    textures: List[TextureInfo] = field(default_factory=list)
    meshes: List[MeshInfo] = field(default_factory=list)
    texture_types: List[str] = field(default_factory=list)
    
    # 资产属性
    is_metal: bool = False
    is_high_poly: bool = False
    is_scatter: bool = False
    is_billboard: bool = False
    apply_to_selection: bool = False
    
    # LOD 信息
    active_lod: Optional[str] = None
    min_lod: Optional[str] = None
    
    # 工作流
    pbr_workflow: str = 'metalness'
    
    # 分类
    category: str = ''
    categories: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    
    @property
    def material_name(self) -> str:
        """生成材质名称"""
        return f"{self.name}_{self.id}"
    
    def has_texture(self, tex_type: str) -> bool:
        """检查是否有指定类型的贴图"""
        return tex_type in self.texture_types
    
    def get_texture_path(self, tex_type: str) -> Optional[str]:
        """获取指定类型贴图的路径"""
        for tex in self.textures:
            if tex.type == tex_type:
                path = tex.path
                # 处理网络路径
                if path.startswith('\\\\'):
                    return path
                return path.replace('\\', '/')
        return None


class AssetParser:
    """资产 JSON 解析器"""
    
    @classmethod
    def parse_json(cls, json_str: str) -> List[AssetData]:
        """
        解析 JSON 字符串为资产数据列表
        
        Args:
            json_str: Megascans 格式的 JSON 字符串
        
        Returns:
            解析后的 AssetData 列表
        """
        try:
            json_array = json.loads(json_str)
            assets = [cls._parse_single_asset(js) for js in json_array]
            log.info(f"解析到 {len(assets)} 个资产")
            return assets
        except json.JSONDecodeError as e:
            log.error(f"JSON 解析失败: {e}")
            return []
    
    @classmethod
    def _parse_single_asset(cls, data: dict) -> AssetData:
        """解析单个资产"""
        # 解析贴图和模型
        textures, texture_types = cls._parse_textures(data)
        meshes = cls._parse_meshes(data)
        
        # 构建 AssetData
        asset = AssetData(
            id=data.get('id', ''),
            name=cls._build_asset_name(data),
            type=data.get('type', ''),
            path=data.get('path'),
            textures=textures,
            meshes=meshes,
            texture_types=texture_types,
            is_metal=data.get('category') == 'Metal',
            is_high_poly=data.get('activeLOD') == 'high',
            active_lod=data.get('activeLOD'),
            min_lod=data.get('minLOD'),
            pbr_workflow=data.get('pbrWorkflow', 'metalness'),
            category=data.get('category', ''),
            categories=data.get('categories', []),
            tags=data.get('tags', []),
            apply_to_selection=data.get('applyToSelection', False),
        )
        
        # 特殊资产检测
        asset.is_scatter = cls._check_scatter(data)
        asset.is_billboard = cls._check_billboard(asset)
        
        log.debug(f"解析资产: {asset.name} (类型: {asset.type}, 贴图: {len(textures)}, 模型: {len(meshes)})")
        
        return asset
    
    @classmethod
    def _parse_textures(cls, data: dict) -> Tuple[List[TextureInfo], List[str]]:
        """解析贴图列表"""
        textures = []
        texture_types = []
        
        # 支持 'components' 键
        components = data.get('components', [])
        
        for comp in components:
            try:
                tex_type = comp.get('type', 'unknown').lower()
                tex_format = comp.get('format', '')
                tex_path = comp.get('path', '')
                
                if not tex_path:
                    continue
                
                # 标准化类型名
                tex_type = BridgeConfig.TEXTURE_TYPE_ALIASES.get(tex_type, tex_type)
                
                textures.append(TextureInfo(
                    format=tex_format,
                    type=tex_type,
                    path=tex_path
                ))
                
                if tex_type not in texture_types:
                    texture_types.append(tex_type)
                    
            except Exception as e:
                log.warning(f"解析贴图失败: {e}, 数据: {comp}")
        
        return textures, texture_types
    
    @classmethod
    def _parse_meshes(cls, data: dict) -> List[MeshInfo]:
        """解析模型列表"""
        meshes = []
        
        for mesh in data.get('meshList', []):
            try:
                mesh_format = mesh.get('format', '')
                mesh_path = mesh.get('path', '')
                
                if not mesh_path:
                    continue
                
                meshes.append(MeshInfo(
                    format=mesh_format,
                    path=mesh_path
                ))
            except Exception as e:
                log.warning(f"解析模型失败: {e}, 数据: {mesh}")
        
        return meshes
    
    @classmethod
    def _build_asset_name(cls, data: dict) -> str:
        """构建资产名称"""
        # 尝试多个可能的名称字段
        name = (data.get('name') or 
                data.get('displayName') or 
                data.get('title') or
                os.path.basename(data.get('path', 'Unknown')))
        
        name = name.replace(' ', '_')
        
        # 截断过长名称
        parts = name.split('_')
        if len(parts) > 2:
            name = '_'.join(parts[:-1])
        
        return name
    
    @staticmethod
    def _check_scatter(data: dict) -> bool:
        """检测是否为散布资产"""
        cats = data.get('categories', [])
        tags = data.get('tags', [])
        return ('scatter' in cats or 
                'scatter' in tags or 
                'cmb_asset' in cats or 
                'cmb_asset' in tags)
    
    @staticmethod
    def _check_billboard(asset: AssetData) -> bool:
        """检测是否为 Billboard"""
        if asset.type == BridgeConfig.ASSET_TYPE_3DPLANT:
            if asset.active_lod and asset.active_lod == asset.min_lod:
                return True
        return False
