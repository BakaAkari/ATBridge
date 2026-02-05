# ATBridge 工具属性组
"""
工具属性组模块

包含物理模拟、碰撞体等属性组定义。
"""
import bpy
from bpy.props import (
    BoolProperty,
    FloatProperty,
    IntProperty,
    EnumProperty,
    PointerProperty,
    CollectionProperty,
)
from bpy.types import PropertyGroup
from bpy.utils import register_class, unregister_class

from ..config import PhysicsSettings


class CustomColliderItem(PropertyGroup):
    """自定义碰撞体列表项"""
    obj: PointerProperty(
        name="Object",
        type=bpy.types.Object,
        description="碰撞体对象"
    )


class ToolProperties(PropertyGroup):
    """工具属性组"""
    
    # 物理模拟状态
    running_physics_calculation: BoolProperty(
        name="Running Physics",
        description="物理计算是否正在运行",
        default=False
    )
    
    # 物理参数
    physics_collision_shape: EnumProperty(
        name="Collision Shape",
        description="碰撞形状",
        items=PhysicsSettings.COLLISION_SHAPES,
        default='CONVEX_HULL'
    )
    
    physics_collision_margin: FloatProperty(
        name="Collision Margin",
        description="碰撞边距",
        default=PhysicsSettings.DEFAULT_COLLISION_MARGIN,
        min=0.0,
        max=1.0,
        step=0.01
    )
    
    physics_friction: FloatProperty(
        name="Friction",
        description="摩擦力",
        default=PhysicsSettings.DEFAULT_FRICTION,
        min=0.0,
        max=1.0,
        step=0.1
    )
    
    physics_time_scale: FloatProperty(
        name="Time Scale",
        description="时间缩放",
        default=PhysicsSettings.DEFAULT_TIME_SCALE,
        min=0.01,
        max=10.0,
        step=0.1
    )
    
    physics_solver_iterations: IntProperty(
        name="Solver Iterations",
        description="求解器迭代次数",
        default=PhysicsSettings.DEFAULT_SOLVER_ITERATIONS,
        min=1,
        max=100
    )
    
    physics_restitution: FloatProperty(
        name="Restitution",
        description="弹性系数",
        default=PhysicsSettings.DEFAULT_RESTITUTION,
        min=0.0,
        max=1.0,
        step=0.1
    )
    
    physics_split_impulse: BoolProperty(
        name="Split Impulse",
        description="分离冲量",
        default=True
    )
    
    # 自定义碰撞体
    physics_use_custom_colliders: BoolProperty(
        name="Use Custom Colliders",
        description="使用自定义碰撞体列表",
        default=False
    )
    
    physics_custom_colliders: CollectionProperty(
        type=CustomColliderItem,
        name="Custom Colliders",
        description="自定义碰撞体列表"
    )
    
    physics_custom_collider_index: IntProperty(
        name="Active Collider Index",
        description="当前选中的碰撞体索引",
        default=0
    )


classes = (
    CustomColliderItem,
    ToolProperties,
)


def register():
    for cls in classes:
        register_class(cls)
    
    # 注册到 WindowManager
    bpy.types.WindowManager.atb_props = PointerProperty(type=ToolProperties)


def unregister():
    # 从 WindowManager 移除
    if hasattr(bpy.types.WindowManager, 'atb_props'):
        del bpy.types.WindowManager.atb_props
    
    for cls in reversed(classes):
        unregister_class(cls)
