# ATBridge Blender 4.x 兼容层
"""
Blender 4.x API 兼容层

集中管理 Blender 4.x 特定的 API 差异，避免在代码中分散处理版本判断。
本模块仅支持 Blender 4.0+，不再包含旧版本兼容代码。
"""
from typing import Dict


class BlenderCompat:
    """Blender 4.x API 兼容层"""
    
    # ============================================
    # 节点类型
    # ============================================
    
    @staticmethod
    def get_mix_node_type() -> str:
        """获取混合节点类型 (4.0+ 使用 ShaderNodeMix)"""
        return 'ShaderNodeMix'
    
    @staticmethod
    def get_separate_color_node_type() -> str:
        """获取分离颜色节点类型 (4.0+ 使用 ShaderNodeSeparateColor)"""
        return 'ShaderNodeSeparateColor'
    
    @staticmethod
    def get_combine_color_node_type() -> str:
        """获取合并颜色节点类型 (4.0+ 使用 ShaderNodeCombineColor)"""
        return 'ShaderNodeCombineColor'
    
    # ============================================
    # BSDF 输入名映射
    # ============================================
    
    # Blender 4.0+ Principled BSDF 输入名称
    BSDF_INPUT_MAPPING: Dict[str, str] = {
        'base color': 'Base Color',
        'albedo': 'Base Color',
        'metallic': 'Metallic',
        'roughness': 'Roughness',
        'alpha': 'Alpha',
        'normal': 'Normal',
        'emission': 'Emission Color',
        'emission_strength': 'Emission Strength',
        'transmission': 'Transmission Weight',
        'ior': 'IOR',
        'subsurface': 'Subsurface Weight',
        'anisotropic': 'Anisotropic',
        'sheen': 'Sheen Weight',
        'clearcoat': 'Coat Weight',
    }
    
    @classmethod
    def get_bsdf_input_name(cls, input_type: str) -> str:
        """
        获取 Principled BSDF 节点输入名称
        
        Args:
            input_type: 输入类型的通用名称
        
        Returns:
            Blender 4.x 中对应的输入槽名称
        """
        key = input_type.lower().replace('_', ' ')
        return cls.BSDF_INPUT_MAPPING.get(key, input_type.title())
    
    # ============================================
    # Mix 节点配置
    # ============================================
    
    @staticmethod
    def get_mix_node_inputs() -> Dict[str, str]:
        """
        获取 Mix 节点的输入槽名称
        
        Returns:
            包含 factor, a, b 键的字典
        """
        return {
            'factor': 'Factor',
            'a': 'A',
            'b': 'B',
        }
    
    @staticmethod
    def configure_mix_node(node, blend_type: str = 'MULTIPLY', 
                           data_type: str = 'RGBA', factor: float = 1.0) -> None:
        """
        配置 Mix 节点
        
        Args:
            node: ShaderNodeMix 节点
            blend_type: 混合类型 (MULTIPLY, ADD, etc.)
            data_type: 数据类型 (RGBA, FLOAT, VECTOR)
            factor: 混合因子
        """
        node.data_type = data_type
        node.blend_type = blend_type
        node.inputs['Factor'].default_value = factor
    
    # ============================================
    # OBJ/FBX 导入参数
    # ============================================
    
    @staticmethod
    def get_obj_import_params() -> Dict:
        """
        获取 OBJ 导入参数
        
        Returns:
            适用于 bpy.ops.import_scene.obj 的参数字典
        """
        return {
            'use_split_objects': True,
            'use_split_groups': True,
            'global_clamp_size': 1.0,
        }
    
    @staticmethod
    def get_fbx_import_params() -> Dict:
        """
        获取 FBX 导入参数
        
        Returns:
            适用于 bpy.ops.import_scene.fbx 的参数字典
        """
        return {
            # 使用默认参数即可
        }
    
    # ============================================
    # 材质设置
    # ============================================
    
    @staticmethod
    def get_displacement_method() -> str:
        """获取材质位移方法"""
        return 'BOTH'
    
    @staticmethod
    def get_blend_method_hashed() -> str:
        """获取透明混合方法"""
        return 'HASHED'
