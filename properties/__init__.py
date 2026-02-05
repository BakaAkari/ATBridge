# ATBridge 属性模块
"""
属性组模块

包含工具属性等 PropertyGroup 定义。
"""

from . import tool_properties


def register():
    tool_properties.register()


def unregister():
    tool_properties.unregister()
