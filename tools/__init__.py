# ATBridge Tools 模块
"""
工具操作符模块

包含从 ATools 合并的各种工具操作符。
"""

from . import (
    mesh_operators,
    node_operators,
    physics_operators,
    frame_operators,
    collection_operators,
)


def register():
    """注册所有工具操作符"""
    mesh_operators.register()
    node_operators.register()
    physics_operators.register()
    frame_operators.register()
    collection_operators.register()


def unregister():
    """注销所有工具操作符"""
    collection_operators.unregister()
    frame_operators.unregister()
    physics_operators.unregister()
    node_operators.unregister()
    mesh_operators.unregister()
