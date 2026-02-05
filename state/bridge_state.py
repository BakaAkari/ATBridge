# ATBridge 状态管理器
"""
线程安全的全局状态管理模块

用于在 Socket 服务器线程和 Blender 主线程之间共享数据。
"""
import threading
from typing import Optional, List, TYPE_CHECKING

if TYPE_CHECKING:
    import bpy


class BridgeState:
    """
    线程安全的全局状态管理器
    
    使用类属性存储状态，通过 threading.Lock 保证线程安全。
    所有方法都是类方法，可直接调用无需实例化。
    """
    
    _lock = threading.Lock()
    _megascans_dataset: Optional[bytes] = None
    _alembic_paths: List[List[str]] = []
    _materials: List = []  # List[bpy.types.Material]
    _import_complete: bool = False
    
    @classmethod
    def get_megascans_dataset(cls) -> Optional[bytes]:
        """
        获取待处理的 Megascans 数据
        
        Returns:
            原始数据字节，或 None
        """
        with cls._lock:
            return cls._megascans_dataset
    
    @classmethod
    def set_megascans_dataset(cls, value: Optional[bytes]) -> None:
        """
        设置 Megascans 数据
        
        Args:
            value: 原始数据字节，或 None 清空
        """
        with cls._lock:
            cls._megascans_dataset = value
    
    @classmethod
    def get_alembic_paths(cls) -> List[List[str]]:
        """获取待导入的 Alembic 路径列表"""
        with cls._lock:
            return cls._alembic_paths.copy()
    
    @classmethod
    def set_alembic_paths(cls, value: List[List[str]]) -> None:
        """设置 Alembic 路径列表"""
        with cls._lock:
            cls._alembic_paths = value
    
    @classmethod
    def append_alembic_paths(cls, paths: List[str]) -> None:
        """追加 Alembic 路径"""
        with cls._lock:
            cls._alembic_paths.append(paths)
    
    @classmethod
    def get_materials(cls) -> List:
        """获取材质列表"""
        with cls._lock:
            return cls._materials.copy()
    
    @classmethod
    def set_materials(cls, value: List) -> None:
        """设置材质列表"""
        with cls._lock:
            cls._materials = value
    
    @classmethod
    def append_material(cls, material) -> None:
        """追加材质"""
        with cls._lock:
            cls._materials.append(material)
    
    @classmethod
    def get_import_complete(cls) -> bool:
        """获取导入完成标志"""
        with cls._lock:
            return cls._import_complete
    
    @classmethod
    def set_import_complete(cls, value: bool) -> None:
        """设置导入完成标志"""
        with cls._lock:
            cls._import_complete = value
    
    @classmethod
    def reset(cls) -> None:
        """重置所有状态"""
        with cls._lock:
            cls._megascans_dataset = None
            cls._alembic_paths = []
            cls._materials = []
            cls._import_complete = False
    
    @classmethod
    def has_pending_data(cls) -> bool:
        """检查是否有待处理的数据"""
        with cls._lock:
            return cls._megascans_dataset is not None
    
    @classmethod
    def has_pending_alembic(cls) -> bool:
        """检查是否有待导入的 Alembic"""
        with cls._lock:
            return len(cls._alembic_paths) > 0 and cls._import_complete
