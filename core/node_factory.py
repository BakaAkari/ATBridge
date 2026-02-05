# ATBridge 节点工厂
"""
材质节点创建工厂

封装 Blender 节点创建逻辑，提供简洁的 API。
"""
import bpy
from typing import Tuple, Optional

from ..compat.blender_compat import BlenderCompat
from ..config import BridgeConfig


class NodeFactory:
    """材质节点工厂"""
    
    def __init__(self, node_tree: bpy.types.NodeTree):
        """
        初始化节点工厂
        
        Args:
            node_tree: 材质的节点树
        """
        self.node_tree = node_tree
        self.nodes = node_tree.nodes
        self.links = node_tree.links
    
    # ============================================
    # 基础节点创建
    # ============================================
    
    def create_node(self, node_type: str, location: Tuple[float, float]) -> bpy.types.Node:
        """
        创建通用节点
        
        Args:
            node_type: 节点类型（如 'ShaderNodeTexImage'）
            location: 节点位置 (x, y)
        
        Returns:
            创建的节点
        """
        node = self.nodes.new(node_type)
        node.location = location
        return node
    
    # ============================================
    # 贴图节点
    # ============================================
    
    def create_texture_node(self, image_path: str, location: Tuple[float, float],
                            colorspace: str = None,
                            projection: str = None) -> bpy.types.ShaderNodeTexImage:
        """
        创建贴图节点
        
        Args:
            image_path: 图像文件路径
            location: 节点位置
            colorspace: 颜色空间（默认 sRGB）
            projection: 投影方式（FLAT/BOX 等）
        
        Returns:
            贴图节点
        """
        node = self.create_node('ShaderNodeTexImage', location)
        node.image = bpy.data.images.load(image_path)
        node.image.colorspace_settings.name = colorspace or BridgeConfig.COLORSPACE_SRGB
        node.show_texture = True
        
        if projection:
            node.projection = projection
        
        return node
    
    # ============================================
    # 混合节点
    # ============================================
    
    def create_mix_node(self, location: Tuple[float, float], 
                        blend_type: str = 'MULTIPLY') -> bpy.types.Node:
        """
        创建颜色混合节点
        
        Args:
            location: 节点位置
            blend_type: 混合类型
        
        Returns:
            Mix 节点
        """
        node_type = BlenderCompat.get_mix_node_type()
        node = self.create_node(node_type, location)
        BlenderCompat.configure_mix_node(node, blend_type=blend_type)
        return node
    
    # ============================================
    # 法线/凹凸节点
    # ============================================
    
    def create_normal_map_node(self, location: Tuple[float, float]) -> bpy.types.Node:
        """创建法线贴图节点"""
        return self.create_node('ShaderNodeNormalMap', location)
    
    def create_bump_node(self, location: Tuple[float, float], 
                         strength: float = None) -> bpy.types.Node:
        """创建凹凸节点"""
        node = self.create_node('ShaderNodeBump', location)
        node.inputs[0].default_value = strength or BridgeConfig.BUMP_STRENGTH
        return node
    
    # ============================================
    # 置换节点
    # ============================================
    
    def create_displacement_node(self, location: Tuple[float, float]) -> bpy.types.Node:
        """创建置换节点"""
        node = self.create_node('ShaderNodeDisplacement', location)
        node.inputs[2].default_value = BridgeConfig.DISPLACEMENT_SCALE  # Scale
        node.inputs[1].default_value = BridgeConfig.DISPLACEMENT_MIDLEVEL  # Midlevel
        return node
    
    def create_separate_color_node(self, location: Tuple[float, float]) -> bpy.types.Node:
        """创建分离颜色节点"""
        node_type = BlenderCompat.get_separate_color_node_type()
        return self.create_node(node_type, location)
    
    # ============================================
    # UV Mapping 节点
    # ============================================
    
    def create_mapping_setup(self, location: Tuple[float, float]) -> Tuple[bpy.types.Node, ...]:
        """
        创建 UV Mapping 节点组
        
        Args:
            location: 主 Mapping 节点的位置
        
        Returns:
            (mapping_node, tex_coord_node, scale_value_node, reroute_node)
        """
        # Mapping 节点
        mapping = self.create_node('ShaderNodeMapping', location)
        mapping.vector_type = 'TEXTURE'
        
        # Texture Coordinate 节点
        tex_coord = self.create_node('ShaderNodeTexCoord', 
                                     (location[0] - 200, location[1]))
        
        # 缩放值节点
        scale_value = self.create_node('ShaderNodeValue', 
                                       (location[0] - 200, location[1] - 250))
        scale_value.name = 'Tiling Scale'
        scale_value.outputs[0].default_value = BridgeConfig.TILING_SCALE
        
        # Reroute 节点
        reroute = self.create_node('NodeReroute', 
                                   (location[0] + 750, location[1]))
        
        # 连接节点
        self.link(tex_coord.outputs['UV'], mapping.inputs['Vector'])
        self.link(scale_value.outputs['Value'], mapping.inputs['Scale'])
        self.link(mapping.outputs[0], reroute.inputs[0])
        
        return mapping, tex_coord, scale_value, reroute
    
    # ============================================
    # 其他工具节点
    # ============================================
    
    def create_invert_node(self, location: Tuple[float, float]) -> bpy.types.Node:
        """创建反转节点"""
        return self.create_node('ShaderNodeInvert', location)
    
    def create_value_node(self, location: Tuple[float, float], 
                          value: float = 1.0, 
                          name: str = None) -> bpy.types.Node:
        """创建数值节点"""
        node = self.create_node('ShaderNodeValue', location)
        node.outputs[0].default_value = value
        if name:
            node.name = name
        return node
    
    # ============================================
    # 连接工具
    # ============================================
    
    def link(self, from_socket, to_socket) -> None:
        """
        创建节点连接
        
        Args:
            from_socket: 输出插槽
            to_socket: 输入插槽
        """
        self.links.new(to_socket, from_socket)
