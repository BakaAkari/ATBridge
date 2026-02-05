# ATBridge LiveLink Operator
"""
Quixel Bridge LiveLink 操作符

启动 Socket 服务器并监听来自 Quixel Bridge 的资产导入请求。
"""
import bpy

from ..server.socket_server import QuixelSocketServer
from ..state.bridge_state import BridgeState
from ..core.import_manager import ImportManager
from ..utils.logger import ATBridgeLogger as log


class MS_Init_LiveLink(bpy.types.Operator):
    """启动 Quixel Bridge LiveLink 服务"""
    
    bl_idname = "bridge.plugin"
    bl_label = "Start Megascans LiveLink"
    bl_description = "启动 Quixel Bridge 实时连接服务"
    
    _server_thread = None
    _timer_registered = False
    
    def execute(self, context):
        """执行操作符"""
        try:
            # 重置状态
            BridgeState.reset()
            
            # 启动 Socket 服务器
            self._server_thread = QuixelSocketServer(
                importer=self._on_data_received
            )
            self._server_thread.start()
            
            # 注册定时器
            if not self._timer_registered:
                bpy.app.timers.register(self._data_monitor)
                self._timer_registered = True
            
            log.info("LiveLink 服务已启动")
            return {'FINISHED'}
            
        except Exception as e:
            log.report_error(self, e, "启动 LiveLink 失败")
            return {'CANCELLED'}
    
    def _on_data_received(self, data: bytes) -> None:
        """
        Socket 数据接收回调
        
        Args:
            data: 原始数据字节
        """
        BridgeState.set_megascans_dataset(data)
    
    def _data_monitor(self) -> float:
        """定时器回调：检测并处理新数据"""
        try:
            data = BridgeState.get_megascans_dataset()
            if data:
                # 处理导入
                manager = ImportManager()
                manager.process_dataset(data)
                
                # 处理 Alembic 延迟导入
                if manager.has_pending_alembic():
                    abc_paths, materials = manager.get_alembic_data()
                    BridgeState.set_alembic_paths(abc_paths)
                    BridgeState.set_materials(materials)
                    BridgeState.set_import_complete(True)
                
                # 清空数据
                BridgeState.set_megascans_dataset(None)
                
        except Exception as e:
            log.error("数据监控错误", e)
        
        return 1.0  # 1秒后再次调用
    
    def __del__(self):
        """析构函数：停止服务器"""
        if self._server_thread:
            self._server_thread.stop()
