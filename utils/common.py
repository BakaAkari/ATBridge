# ATBridge 通用工具函数
"""
通用工具模块

包含错误处理、验证函数等通用工具。
"""
import bpy


class ATError(Exception):
    """ATBridge 基础异常类"""
    pass


class ATFileError(ATError):
    """文件相关异常"""
    pass


class ATOperationError(ATError):
    """操作相关异常"""
    pass


def safe_execute(func, *args, **kwargs):
    """
    安全执行函数，捕获异常并返回结果
    
    返回: (success: bool, result_or_error)
    """
    try:
        result = func(*args, **kwargs)
        return True, result
    except Exception as e:
        return False, str(e)


def show_message_box(message="", title="Message", icon='INFO'):
    """显示消息对话框"""
    def draw(self, context):
        self.layout.label(text=message)
    
    bpy.context.window_manager.popup_menu(draw, title=title, icon=icon)


def open_directory(path):
    """在系统文件浏览器中打开目录"""
    import os
    import subprocess
    import platform

    if not os.path.exists(path):
        raise ATFileError(f"目录不存在: {path}")

    system = platform.system()
    if system == "Windows":
        os.startfile(path)
    elif system == "Darwin":  # macOS
        subprocess.Popen(["open", path])
    else:  # Linux
        subprocess.Popen(["xdg-open", path])


def validate_object_selection(context, min_count=1, max_count=None, obj_type=None):
    """
    验证对象选择
    
    Args:
        context: Blender context
        min_count: 最小选择数量
        max_count: 最大选择数量 (None=不限制)
        obj_type: 对象类型过滤 (如 'MESH', 'CURVE' 等)
        
    Returns:
        list: 符合条件的选中对象列表
        
    Raises:
        ATOperationError: 验证失败时抛出
    """
    selected = context.selected_objects
    
    if obj_type:
        selected = [obj for obj in selected if obj.type == obj_type]
        type_name = obj_type.lower()
    else:
        type_name = "对象"
    
    if len(selected) < min_count:
        if min_count == 1:
            raise ATOperationError(f"请至少选择一个{type_name}")
        else:
            raise ATOperationError(f"请至少选择 {min_count} 个{type_name}")
    
    if max_count and len(selected) > max_count:
        raise ATOperationError(f"选择的{type_name}数量超过限制 ({max_count})")
    
    return selected


def get_active_material_nodes(obj):
    """
    安全获取活动材质的节点
    
    Args:
        obj: Blender对象
        
    Returns:
        材质节点列表
        
    Raises:
        ATOperationError: 无法获取节点时抛出
    """
    if not obj:
        raise ATOperationError("对象为空")
    
    if not obj.active_material:
        raise ATOperationError(f"对象 '{obj.name}' 没有活动材质")
    
    mat = obj.active_material
    if not mat.use_nodes:
        raise ATOperationError(f"材质 '{mat.name}' 未启用节点")
    
    if not mat.node_tree:
        raise ATOperationError(f"材质 '{mat.name}' 没有节点树")
    
    return mat.node_tree.nodes
