# ATBridge 全局配置
"""
ATBridge 插件配置常量模块

所有硬编码值都应在此定义，便于集中管理和修改。
"""

class BridgeConfig:
    """ATBridge 全局配置"""
    
    # 网络配置
    HOST = 'localhost'
    PORT = 23333
    BUFFER_SIZE = 8192
    RECONNECT_DELAY = 3
    
    # 材质默认值
    DEFAULT_IOR = 1.45
    DISPLACEMENT_SCALE = 0.1
    DISPLACEMENT_MIDLEVEL = 0.5
    BUMP_STRENGTH = 0.1
    TILING_SCALE = 1.0
    
    # 颜色空间
    COLORSPACE_SRGB = "sRGB"
    COLORSPACE_NON_COLOR = "Non-Color"
    COLORSPACE_LINEAR = "Linear"
    
    # 资产类型
    ASSET_TYPE_3D = "3d"
    ASSET_TYPE_3DPLANT = "3dplant"
    ASSET_TYPE_SURFACE = "surface"
    ASSET_TYPE_ATLAS = "atlas"
    
    # 贴图类型别名映射 (统一为标准名称)
    TEXTURE_TYPE_ALIASES = {
        'diffuse': 'albedo',
        'basecolor': 'albedo',
        'col': 'albedo',
        'color': 'albedo',
    }


class PhysicsSettings:
    """物理模拟设置常量"""
    
    # 默认物理参数
    DEFAULT_FRICTION = 0.5
    DEFAULT_TIME_SCALE = 1.0
    DEFAULT_COLLISION_MARGIN = 0.04
    DEFAULT_SOLVER_ITERATIONS = 10
    DEFAULT_RESTITUTION = 0.0
    DEFAULT_FPS = 60
    
    # 模拟限制
    MAX_SIMULATION_FRAMES = 10000
    
    # 碰撞形状选项
    COLLISION_SHAPES = [
        ('MESH', "Mesh", "Mesh collision shape"),
        ('CONVEX_HULL', "Convex Hull", "Convex Hull collision shape"),
        ('BOX', "Box", "Box collision shape"),
        ('SPHERE', "Sphere", "Sphere collision shape"),
        ('CAPSULE', "Capsule", "Capsule collision shape"),
        ('CYLINDER', "Cylinder", "Cylinder collision shape"),
    ]


class MaterialNodes:
    """材质节点类型常量"""
    
    # 节点类型
    TEX_IMAGE = 'TEX_IMAGE'
    TEX_COORD = 'TEX_COORD'
    MAPPING = 'MAPPING'
    SUBSURF = 'SUBSURF'
    
    # 投影模式
    PROJECTION_BOX = 'BOX'
    PROJECTION_FLAT = 'FLAT'
    DEFAULT_PROJECTION_BLEND = 1.0
    
    # 修改器名称
    BRIDGE_DISPLACEMENT = "ATB_Subdivision"


class UIConstants:
    """UI 常量"""
    
    # 面板类别
    PANEL_CATEGORY = "ATBridge"
    
    # 面板排序
    PANEL_ORDER_MAIN = 0
    PANEL_ORDER_NODE = 1
    PANEL_ORDER_TOOLS = 2
