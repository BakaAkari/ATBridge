# ATBridge UI 模块
"""
UI 面板模块

包含 3D 视图和节点编辑器的面板。
"""

from . import (
    tools_panel,
    node_panel,
    ui_callbacks,
)


def register():
    """注册所有 UI 面板"""
    tools_panel.register()
    node_panel.register()
    ui_callbacks.register()


def unregister():
    """注销所有 UI 面板"""
    ui_callbacks.unregister()
    node_panel.unregister()
    tools_panel.unregister()
