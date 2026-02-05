# ATBridge 统一日志系统
"""
统一的日志和错误报告模块

替代分散的 print() 和 except: pass，提供一致的日志格式和错误处理。
"""
import traceback
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import bpy


class ATBridgeLogger:
    """ATBridge 统一日志系统"""
    
    PREFIX = "[ATBridge]"
    
    @classmethod
    def info(cls, message: str) -> None:
        """输出信息日志"""
        print(f"{cls.PREFIX} {message}")
    
    @classmethod
    def debug(cls, message: str) -> None:
        """输出调试日志"""
        print(f"{cls.PREFIX} DEBUG: {message}")
    
    @classmethod
    def warning(cls, message: str) -> None:
        """输出警告日志"""
        print(f"{cls.PREFIX} WARNING: {message}")
    
    @classmethod
    def error(cls, message: str, exc: Optional[Exception] = None) -> None:
        """
        输出错误日志
        
        Args:
            message: 错误描述
            exc: 可选的异常对象，如果提供则打印堆栈
        """
        print(f"{cls.PREFIX} ERROR: {message}")
        if exc:
            traceback.print_exc()
    
    @classmethod
    def report_error(cls, operator, error: Exception, user_message: Optional[str] = None) -> None:
        """
        向 Blender UI 报告错误
        
        Args:
            operator: Blender Operator 实例
            error: 异常对象
            user_message: 显示给用户的消息（默认使用异常消息）
        """
        cls.error(str(error), error)
        if operator:
            msg = user_message or str(error)
            operator.report({'ERROR'}, msg)
    
    @classmethod
    def report_info(cls, operator, message: str) -> None:
        """
        向 Blender UI 报告信息
        
        Args:
            operator: Blender Operator 实例
            message: 显示给用户的消息
        """
        cls.info(message)
        if operator:
            operator.report({'INFO'}, message)
    
    @classmethod
    def report_warning(cls, operator, message: str) -> None:
        """
        向 Blender UI 报告警告
        
        Args:
            operator: Blender Operator 实例
            message: 显示给用户的消息
        """
        cls.warning(message)
        if operator:
            operator.report({'WARNING'}, message)
