# ATBridge 材质构建器
"""
材质节点图构建模块

负责根据资产数据创建完整的 PBR 材质节点图。
"""
import bpy
from typing import Optional

from .asset_parser import AssetData
from .node_factory import NodeFactory
from ..compat.blender_compat import BlenderCompat
from ..config import BridgeConfig
from ..utils.logger import ATBridgeLogger as log


class MaterialBuilder:
    """材质构建器"""
    
    # 贴图节点 Y 轴间距
    TEXTURE_Y_SPACING = 260
    TEXTURE_BASE_Y = 460
    
    def __init__(self, asset: AssetData):
        """
        初始化材质构建器
        
        Args:
            asset: 解析后的资产数据
        """
        self.asset = asset
        self.mat: Optional[bpy.types.Material] = None
        self.factory: Optional[NodeFactory] = None
        self.bsdf_node: Optional[bpy.types.Node] = None
        self.output_node: Optional[bpy.types.Node] = None
        self.reroute: Optional[bpy.types.Node] = None
        self.tex_count = 0
    
    def build(self) -> bpy.types.Material:
        """
        构建完整材质
        
        Returns:
            创建的材质
        """
        log.info(f"构建材质: {self.asset.material_name}")
        
        self._create_material()
        self._setup_mapping()
        self._setup_textures()
        
        log.debug(f"材质构建完成, 贴图节点数: {self.tex_count}")
        return self.mat
    
    def _create_material(self) -> None:
        """创建或获取材质"""
        name = self.asset.material_name
        self.mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        self.mat.use_nodes = True
        
        self.factory = NodeFactory(self.mat.node_tree)
        self.bsdf_node = self.mat.node_tree.nodes.get('Principled BSDF')
        self.output_node = self.mat.node_tree.nodes.get('Material Output')
    
    def _setup_mapping(self) -> None:
        """设置 UV Mapping（非 3D/3DPlant 资产）"""
        if self.asset.type not in [BridgeConfig.ASSET_TYPE_3D, 
                                   BridgeConfig.ASSET_TYPE_3DPLANT]:
            _, _, _, self.reroute = self.factory.create_mapping_setup((-1950, 0))
    
    def _setup_textures(self) -> None:
        """设置所有贴图"""
        # Albedo + AO
        if self.asset.has_texture('albedo'):
            self._setup_albedo_ao()
        
        # Metalness
        if self.asset.has_texture('metalness'):
            self._create_connected_texture('metalness', 'Metallic', 
                                          BridgeConfig.COLORSPACE_NON_COLOR)
        
        # Roughness
        if self.asset.has_texture('roughness'):
            self._create_connected_texture('roughness', 'Roughness',
                                          BridgeConfig.COLORSPACE_NON_COLOR)
        elif self.asset.has_texture('gloss'):
            self._setup_gloss()
        
        # Opacity
        if self.asset.has_texture('opacity'):
            self._create_connected_texture('opacity', 'Alpha',
                                          BridgeConfig.COLORSPACE_NON_COLOR)
            self.mat.blend_method = BlenderCompat.get_blend_method_hashed()
        
        # Transmission
        if self.asset.has_texture('transmission'):
            self._create_connected_texture('transmission', 'Transmission Weight',
                                          BridgeConfig.COLORSPACE_NON_COLOR)
        
        # Normal
        if self.asset.has_texture('normal'):
            self._setup_normal()
        elif self.asset.has_texture('bump'):
            self._setup_bump()
        
        # Displacement
        if self.asset.has_texture('displacement'):
            self._setup_displacement()
    
    def _setup_albedo_ao(self) -> None:
        """设置 Albedo (+ AO 混合)"""
        if self.asset.has_texture('ao'):
            # 创建 Multiply 混合节点
            mix_node = self.factory.create_mix_node((-250, 320), 'MULTIPLY')
            
            # 创建 Albedo 和 AO 贴图
            color_node = self._create_texture_node('albedo', (-640, 460), 
                                                   BridgeConfig.COLORSPACE_SRGB)
            color_node.name = "Color Tex Node"
            
            ao_node = self._create_texture_node('ao', (-640, 200),
                                               BridgeConfig.COLORSPACE_NON_COLOR)
            ao_node.name = "AO Tex Node"
            
            # 连接到混合节点
            inputs = BlenderCompat.get_mix_node_inputs()
            self.factory.link(color_node.outputs['Color'], 
                             mix_node.inputs[inputs['a']])
            self.factory.link(ao_node.outputs['Color'], 
                             mix_node.inputs[inputs['b']])
            
            # 连接到 BSDF
            self._connect_to_bsdf(mix_node.outputs[2], 'Base Color')
            self.tex_count += 2
        else:
            # 仅 Albedo
            node = self._create_texture_node('albedo', 
                                            (-640, self._get_tex_y()),
                                            BridgeConfig.COLORSPACE_SRGB)
            node.name = "Color Tex Node"
            self._connect_to_bsdf(node.outputs['Color'], 'Base Color')
            self.tex_count += 1
    
    def _setup_gloss(self) -> None:
        """设置 Gloss 贴图（反转为 Roughness）"""
        gloss_node = self._create_texture_node('gloss',
                                              (-640, self._get_tex_y()),
                                              BridgeConfig.COLORSPACE_NON_COLOR)
        gloss_node.name = "Gloss Tex Node"
        
        invert_node = self.factory.create_invert_node((-250, self._get_tex_y() + 60))
        
        self.factory.link(gloss_node.outputs['Color'], invert_node.inputs[1])
        self._connect_to_bsdf(invert_node.outputs[0], 'Roughness')
        self.tex_count += 1
    
    def _setup_normal(self) -> None:
        """设置法线贴图"""
        tex_node = self._create_texture_node('normal',
                                            (-640, self._get_tex_y()),
                                            BridgeConfig.COLORSPACE_NON_COLOR)
        tex_node.name = "Normal Tex Node"
        
        normal_node = self.factory.create_normal_map_node((-250, -250))
        
        self.factory.link(tex_node.outputs['Color'], normal_node.inputs['Color'])
        self._connect_to_bsdf(normal_node.outputs['Normal'], 'Normal')
        self.tex_count += 1
    
    def _setup_bump(self) -> None:
        """设置凹凸贴图"""
        tex_node = self._create_texture_node('bump',
                                            (-640, self._get_tex_y()),
                                            BridgeConfig.COLORSPACE_NON_COLOR)
        tex_node.name = "Bump Tex Node"
        
        bump_node = self.factory.create_bump_node((-250, -250))
        
        self.factory.link(tex_node.outputs['Color'], bump_node.inputs[2])
        self._connect_to_bsdf(bump_node.outputs['Normal'], 'Normal')
        self.tex_count += 1
    
    def _setup_displacement(self) -> None:
        """设置置换贴图"""
        tex_node = self._create_texture_node('displacement',
                                            (-640, self._get_tex_y()),
                                            BridgeConfig.COLORSPACE_NON_COLOR)
        tex_node.name = "Displacement Tex Node"
        
        # 分离颜色节点（提取 R 通道）
        sep_node = self.factory.create_separate_color_node((-250, -550))
        
        # 置换节点
        disp_node = self.factory.create_displacement_node((10, -400))
        
        # 置换强度控制
        strength_node = self.factory.create_value_node((-250, -650), 
                                                       BridgeConfig.DISPLACEMENT_SCALE,
                                                       'Bump Strength')
        
        # 连接
        self.factory.link(tex_node.outputs['Color'], sep_node.inputs[0])
        self.factory.link(sep_node.outputs[0], disp_node.inputs[0])
        self.factory.link(strength_node.outputs[0], disp_node.inputs['Scale'])
        self.factory.link(disp_node.outputs[0], self.output_node.inputs[2])
        
        # 设置材质位移方法
        self.mat.displacement_method = BlenderCompat.get_displacement_method()
        self.tex_count += 1
    
    def _create_texture_node(self, tex_type: str, location: tuple, 
                             colorspace: str) -> bpy.types.Node:
        """
        创建贴图节点并连接到 Mapping
        
        Args:
            tex_type: 贴图类型
            location: 节点位置
            colorspace: 颜色空间
        
        Returns:
            创建的贴图节点
        """
        path = self.asset.get_texture_path(tex_type)
        if not path:
            log.warning(f"找不到贴图: {tex_type}")
            return None
        
        # 确定投影方式
        projection = None
        if self.asset.type == BridgeConfig.ASSET_TYPE_SURFACE:
            projection = 'FLAT'
        
        node = self.factory.create_texture_node(path, location, colorspace, projection)
        
        # 连接到 Mapping Reroute
        if self.reroute:
            self.factory.link(self.reroute.outputs[0], node.inputs['Vector'])
        
        return node
    
    def _create_connected_texture(self, tex_type: str, bsdf_input: str,
                                  colorspace: str) -> bpy.types.Node:
        """
        创建贴图并直接连接到 BSDF
        
        Args:
            tex_type: 贴图类型
            bsdf_input: BSDF 输入名称
            colorspace: 颜色空间
        
        Returns:
            创建的贴图节点
        """
        node = self._create_texture_node(tex_type, 
                                        (-640, self._get_tex_y()), 
                                        colorspace)
        if node:
            node.name = f"{tex_type.title()} Tex Node"
            self._connect_to_bsdf(node.outputs['Color'], bsdf_input)
            self.tex_count += 1
        return node
    
    def _connect_to_bsdf(self, from_socket, input_name: str) -> None:
        """连接到 BSDF 节点"""
        bsdf_input = BlenderCompat.get_bsdf_input_name(input_name)
        if bsdf_input in self.bsdf_node.inputs:
            self.factory.link(from_socket, self.bsdf_node.inputs[bsdf_input])
        else:
            log.warning(f"BSDF 节点没有输入: {bsdf_input}")
    
    def _get_tex_y(self) -> float:
        """获取下一个贴图节点的 Y 坐标"""
        return self.TEXTURE_BASE_Y - (self.tex_count * self.TEXTURE_Y_SPACING)
