"""
投屏客户端
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Any, Callable
from .config import Config
from .protocols.base import BaseProtocol

logger = logging.getLogger(__name__)

class MirroringClient:
    """手机投屏客户端"""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.protocol: Optional[BaseProtocol] = None
        self.protocol_name = ""
        self.is_connected = False
        self.callbacks = {}
        
        # 性能统计
        self.stats = {
            "connected_time": 0,
            "total_bytes_received": 0,
            "total_frames": 0,
            "latency": 0,
            "errors": 0
        }
    
    async def connect(self, protocol: str, server_address: str, **kwargs) -> bool:
        """连接到投屏服务器"""
        if self.is_connected:
            logger.warning("Already connected")
            return False
        
        # 初始化协议
        self.protocol_name = protocol
        self.protocol = self._create_protocol(protocol, server_address, **kwargs)
        
        if not self.protocol:
            logger.error(f"Failed to create {protocol} protocol")
            return False
        
        try:
            # 注册回调
            self.protocol.register_callback("started", self._on_connected)
            self.protocol.register_callback("stopped", self._on_disconnected)
            self.protocol.register_callback("client_connected", self._on_client_event)
            self.protocol.register_callback("client_disconnected", self._on_client_event)
            self.protocol.register_callback("frame_received", self._on_frame_received)
            self.protocol.register_callback("control", self._on_control)
            
            # 启动协议
            success = await self.protocol.start()
            if success:
                logger.info(f"Connected via {protocol} protocol")
                return True
            else:
                logger.error(f"Failed to start {protocol} protocol")
                return False
                
        except Exception as e:
            logger.error(f"Error connecting: {e}")
            self.stats["errors"] += 1
            return False
    
    async def disconnect(self) -> bool:
        """断开连接"""
        if not self.is_connected:
            return True
        
        try:
            if self.protocol:
                await self.protocol.stop()
                self.protocol = None
            
            self.is_connected = False
            logger.info("Disconnected from server")
            return True
            
        except Exception as e:
            logger.error(f"Error disconnecting: {e}")
            return False
    
    def _create_protocol(self, protocol: str, server_address: str, **kwargs) -> Optional[BaseProtocol]:
        """创建协议实例"""
        # 这里应该根据协议类型创建相应的客户端协议
        # 由于当前实现都是服务端协议，这里需要扩展
        
        if protocol == "RTSP":
            from .protocols.rtsp import RTSPProtocol
            return RTSPClientProtocol(server_address, **kwargs)
        elif protocol == "WebRTC":
            from .protocols.webrtc import WebRTCProtocol
            return WebRTCClientProtocol(server_address, **kwargs)
        elif protocol == "ADB":
            from .protocols.adb import ADBProtocol
            return ADBClientProtocol(server_address, **kwargs)
        else:
            logger.error(f"Unknown protocol: {protocol}")
            return None
    
    async def send_control(self, control_data: Dict[str, Any]) -> bool:
        """发送控制指令"""
        if not self.is_connected or not self.protocol:
            return False
        
        try:
            return await self.protocol.handle_control(control_data)
        except Exception as e:
            logger.error(f"Error sending control: {e}")
            self.stats["errors"] += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """获取客户端统计信息"""
        stats = self.stats.copy()
        
        if self.stats["connected_time"] > 0:
            stats["connection_duration"] = time.time() - self.stats["connected_time"]
        
        if self.protocol and self.is_connected:
            protocol_stats = self.protocol.get_stats()
            stats["protocol"] = protocol_stats
        
        return stats
    
    def register_callback(self, event: str, callback: Callable):
        """注册回调函数"""
        if event not in self.callbacks:
            self.callbacks[event] = []
        self.callbacks[event].append(callback)
    
    def emit(self, event: str, *args, **kwargs):
        """触发回调"""
        callbacks = self.callbacks.get(event, [])
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    # 事件处理器
    def _on_connected(self):
        """连接成功事件"""
        self.is_connected = True
        self.stats["connected_time"] = time.time()
        logger.info("Connected to mirroring server")
        self.emit("connected")
    
    def _on_disconnected(self):
        """断开连接事件"""
        self.is_connected = False
        logger.info("Disconnected from mirroring server")
        self.emit("disconnected")
    
    def _on_client_event(self, *args):
        """客户端事件"""
        self.emit("client_event", *args)
    
    def _on_frame_received(self, frame_data: bytes, metadata: Dict[str, Any]):
        """接收帧事件"""
        self.stats["total_bytes_received"] += len(frame_data)
        self.stats["total_frames"] += 1
        
        # 计算延迟
        if "timestamp" in metadata:
            self.stats["latency"] = (time.time() - metadata["timestamp"]) * 1000  # ms
        
        self.emit("frame_received", frame_data, metadata)
    
    def _on_control(self, control_data: Dict[str, Any]):
        """控制事件"""
        self.emit("control", control_data)

# 客户端协议实现（扩展示例）
class RTSPClientProtocol(BaseProtocol):
    """RTSP客户端协议"""
    
    def __init__(self, server_address: str, **kwargs):
        super().__init__({"host": server_address, **kwargs})
        self.server_address = server_address
        self.client_socket = None
    
    async def start(self) -> bool:
        """启动RTSP客户端"""
        try:
            # 这里应该实现RTSP客户端逻辑
            # 包括RTSP握手、RTP接收等
            self.is_running = True
            self.stats["start_time"] = time.time()
            return True
        except Exception as e:
            logger.error(f"Failed to start RTSP client: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止RTSP客户端"""
        self.is_running = False
        if self.client_socket:
            self.client_socket.close()
        return True
    
    async def send_frame(self, frame_data: bytes, metadata: Dict[str, Any]) -> bool:
        """RTSP客户端通常不发送帧"""
        return True
    
    async def send_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        """RTSP客户端通常不发送音频"""
        return True
    
    async def handle_control(self, control_data: Dict[str, Any]) -> bool:
        """处理控制指令"""
        # 实现RTSP控制逻辑
        return True

class WebRTCClientProtocol(BaseProtocol):
    """WebRTC客户端协议"""
    
    def __init__(self, server_address: str, **kwargs):
        super().__init__({"server": server_address, **kwargs})
        self.server_address = server_address
    
    async def start(self) -> bool:
        """启动WebRTC客户端"""
        try:
            # 实现WebRTC客户端逻辑
            # 包括信令交换、P2P连接建立等
            self.is_running = True
            self.stats["start_time"] = time.time()
            return True
        except Exception as e:
            logger.error(f"Failed to start WebRTC client: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止WebRTC客户端"""
        self.is_running = False
        return True
    
    async def send_frame(self, frame_data: bytes, metadata: Dict[str, Any]) -> bool:
        return True
    
    async def send_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        return True
    
    async def handle_control(self, control_data: Dict[str, Any]) -> bool:
        return True

class ADBClientProtocol(BaseProtocol):
    """ADB客户端协议"""
    
    def __init__(self, server_address: str, **kwargs):
        super().__init__({"host": server_address, **kwargs})
        self.server_address = server_address
    
    async def start(self) -> bool:
        """启动ADB客户端"""
        try:
            # 实现ADB客户端逻辑
            self.is_running = True
            self.stats["start_time"] = time.time()
            return True
        except Exception as e:
            logger.error(f"Failed to start ADB client: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止ADB客户端"""
        self.is_running = False
        return True
    
    async def send_frame(self, frame_data: bytes, metadata: Dict[str, Any]) -> bool:
        return True
    
    async def send_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        return True
    
    async def handle_control(self, control_data: Dict[str, Any]) -> bool:
        return True

# 便捷函数
async def connect_to_server(protocol: str, server_address: str, 
                           config: Config = None) -> MirroringClient:
    """连接到投屏服务器"""
    client = MirroringClient(config)
    success = await client.connect(protocol, server_address)
    if success:
        return client
    else:
        raise ConnectionError(f"Failed to connect via {protocol}")