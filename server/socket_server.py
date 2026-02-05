# ATBridge Socket 服务器
"""
Quixel Bridge 通信服务器模块

监听 TCP 端口接收来自 Quixel Bridge 的资产数据。
"""
import socket
import threading
from typing import Callable, Optional

from ..config import BridgeConfig
from ..utils.logger import ATBridgeLogger as log


class QuixelSocketServer(threading.Thread):
    """
    Quixel Bridge Socket 服务器
    
    在独立线程中监听 TCP 端口，接收资产数据后调用回调函数。
    """
    
    def __init__(self, host: str = None, port: int = None, 
                 importer: Callable[[bytes], None] = None):
        """
        初始化 Socket 服务器
        
        Args:
            host: 监听地址（默认 localhost）
            port: 监听端口（默认 23333）
            importer: 数据接收回调函数
        """
        super().__init__()
        self.host = host or BridgeConfig.HOST
        self.port = port or BridgeConfig.PORT
        self.importer = importer
        self.daemon = True  # 设为守护线程，随主线程退出
        self.running = True
        self.server: Optional[socket.socket] = None
    
    def run(self) -> None:
        """服务器主循环"""
        log.info(f"Socket 服务器启动于 {self.host}:{self.port}")
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
                self.server = server
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind((self.host, self.port))
                server.listen(5)
                
                while self.running:
                    self._handle_connection(server)
                    
        except OSError as e:
            if self.running:  # 非主动停止的错误
                log.error(f"Socket 服务器错误: {e}")
        except Exception as e:
            log.error("Socket 服务器意外错误", e)
        finally:
            log.info("Socket 服务器已停止")
    
    def _handle_connection(self, server: socket.socket) -> None:
        """处理客户端连接"""
        try:
            client, addr = server.accept()
            log.debug(f"收到连接: {addr}")
            
            with client:
                data = self._receive_all(client)
                
                if data and self.importer:
                    log.info(f"收到数据: {len(data)} 字节")
                    self.importer(data)
                    
        except OSError:
            # 服务器被关闭时的正常情况
            pass
        except Exception as e:
            log.error(f"处理连接错误: {e}")
    
    def _receive_all(self, client: socket.socket) -> bytes:
        """接收所有数据"""
        data = b''
        while True:
            chunk = client.recv(BridgeConfig.BUFFER_SIZE)
            if not chunk:
                break
            data += chunk
        return data
    
    def stop(self) -> None:
        """停止服务器"""
        log.info("正在停止 Socket 服务器...")
        self.running = False
        
        # 发送空连接以解除 accept() 阻塞
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((self.host, self.port))
        except Exception:
            pass
