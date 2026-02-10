"""
投屏服务端
修复后的完整实现
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from phone_mirroring.config import Config
from phone_mirroring.protocols.base import BaseProtocol
from phone_mirroring.protocols.adb import ADBProtocol

# 尝试导入 RTSP 协议，如果不存在则创建空实现
try:
    from phone_mirroring.protocols.rtsp import RTSPProtocol
except ImportError:
    # 为缺失的 RTSP 协议创建占位符
    class RTSPProtocol(BaseProtocol):
        """RTSP协议占位符（尚未实现）"""
        
        def __init__(self, config: Dict[str, Any]):
            super().__init__(config)
            self.port = config.get("port", 8554)
            
        async def start(self) -> bool:
            logging.warning("RTSP protocol not implemented yet")
            return False
        
        async def stop(self) -> bool:
            return True
        
        async def send_frame(self, frame_data: bytes, metadata: Dict[str, Any]) -> bool:
            return True
        
        async def send_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
            return True
        
        async def handle_control(self, control_data: Dict[str, Any]) -> bool:
            return True

logger = logging.getLogger(__name__)

class MirroringServer:
    """手机投屏服务器"""
    
    def __init__(self, config: Optional[Config] = None):
        self.config = config if config is not None else Config()
        self.protocols: Dict[str, BaseProtocol] = {}
        self.is_running = False
        self.callbacks: Dict[str, List[Callable]] = {}
        
        # 性能统计
        self.stats = {
            "start_time": 0.0,
            "total_clients": 0,
            "total_bytes_sent": 0,
            "total_bytes_received": 0,
            "total_frames": 0,
            "errors": 0
        }
        
        # 初始化协议
        self._init_protocols()
    
    def _init_protocols(self):
        """初始化所有支持的协议"""
        # RTSP协议
        if "RTSP" in self.config.enabled_protocols:
            self.protocols["RTSP"] = RTSPProtocol({
                "port": self.config.network.port,
                "rtp_port_start": 5000
            })
        
        # ADB协议
        if "ADB" in self.config.enabled_protocols:
            adb_config = {
                "adb_port": 5555,
                "scrcpy_port": 27183,
                "device_id": "",
                "max_width": self.config.video.width,
                "max_height": self.config.video.height,
                "bitrate": self.config.video.bitrate,
                "max_fps": self.config.video.fps
            }
            self.protocols["ADB"] = ADBProtocol(adb_config)
    
    async def start(self) -> bool:
        """启动服务"""
        if self.is_running:
            logger.warning("Server is already running")
            return False
        
        try:
            self.stats["start_time"] = time.time()
            
            # 启动所有协议
            for protocol_name, protocol in self.protocols.items():
                logger.info(f"Starting {protocol_name} protocol...")
                success = await protocol.start()
                if success:
                    # 注册协议回调
                    protocol.register_callback("started", self._on_protocol_started)
                    protocol.register_callback("stopped", self._on_protocol_stopped)
                    protocol.register_callback("client_connected", self._on_client_connected)
                    protocol.register_callback("client_disconnected", self._on_client_disconnected)
                    protocol.register_callback("frame_received", self._on_frame_received)
                    logger.info(f"{protocol_name} protocol started successfully")
                else:
                    logger.error(f"Failed to start {protocol_name} protocol")
            
            self.is_running = True
            logger.info("Mirroring server started successfully")
            self.emit("server_started")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False
    
    async def stop(self) -> bool:
        """停止服务"""
        if not self.is_running:
            return True
        
        try:
            self.is_running = False
            
            # 停止所有协议
            for protocol_name, protocol in self.protocols.items():
                logger.info(f"Stopping {protocol_name} protocol...")
                await protocol.stop()
            
            logger.info("Mirroring server stopped")
            self.emit("server_stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping server: {e}")
            return False
    
    async def broadcast_frame(self, frame_data: bytes, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """广播视频帧到所有协议"""
        if not self.is_running:
            return False
        
        metadata = metadata or {}
        metadata.update({
            "timestamp": time.time(),
            "size": len(frame_data)
        })
        
        success_count = 0
        for protocol_name, protocol in self.protocols.items():
            try:
                if protocol.is_running:
                    success = await protocol.send_frame(frame_data, metadata)
                    if success:
                        success_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting frame via {protocol_name}: {e}")
        
        self.stats["total_frames"] += 1
        self.stats["total_bytes_sent"] += len(frame_data) * success_count
        
        return success_count > 0
    
    async def broadcast_audio(self, audio_data: bytes, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """广播音频数据到所有协议"""
        if not self.is_running:
            return False
        
        metadata = metadata or {}
        metadata.update({
            "timestamp": time.time(),
            "size": len(audio_data)
        })
        
        success_count = 0
        for protocol_name, protocol in self.protocols.items():
            try:
                if protocol.is_running:
                    success = await protocol.send_audio(audio_data, metadata)
                    if success:
                        success_count += 1
            except Exception as e:
                logger.error(f"Error broadcasting audio via {protocol_name}: {e}")
        
        self.stats["total_bytes_sent"] += len(audio_data) * success_count
        return success_count > 0
    
    async def handle_control(self, control_data: Dict[str, Any]) -> bool:
        """处理控制指令"""
        if not self.is_running:
            return False
        
        success_count = 0
        for protocol_name, protocol in self.protocols.items():
            try:
                if protocol.is_running:
                    success = await protocol.handle_control(control_data)
                    if success:
                        success_count += 1
            except Exception as e:
                logger.error(f"Error handling control via {protocol_name}: {e}")
        
        return success_count > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """获取服务统计信息"""
        stats = self.stats.copy()
        uptime = time.time() - stats["start_time"] if stats["start_time"] > 0 else 0.0
        stats["uptime"] = uptime
        
        # 聚合各协议统计
        protocol_stats = {}
        for protocol_name, protocol in self.protocols.items():
            if protocol.is_running:
                protocol_stats[protocol_name] = protocol.get_stats()
        
        stats["protocols"] = protocol_stats
        return stats
    
    def get_active_protocols(self) -> List[str]:
        """获取活跃的协议列表"""
        return [name for name, protocol in self.protocols.items() if protocol.is_running]
    
    def get_client_count(self) -> int:
        """获取连接的客户端总数"""
        total = 0
        for protocol in self.protocols.values():
            if protocol.is_running:
                stats = protocol.get_stats()
                total += stats.get("connected_clients", 0)
        return total
    
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
    def _on_protocol_started(self, protocol_name: str):
        """协议启动事件"""
        logger.info(f"Protocol {protocol_name} started")
    
    def _on_protocol_stopped(self, protocol_name: str):
        """协议停止事件"""
        logger.info(f"Protocol {protocol_name} stopped")
    
    def _on_client_connected(self, client_id: str, client_address: tuple):
        """客户端连接事件"""
        self.stats["total_clients"] += 1
        logger.info(f"Client connected: {client_id} from {client_address}")
        self.emit("client_connected", client_id, client_address)
    
    def _on_client_disconnected(self, client_id: str):
        """客户端断开事件"""
        logger.info(f"Client disconnected: {client_id}")
        self.emit("client_disconnected", client_id)
    
    def _on_frame_received(self, frame_data: bytes, metadata: Dict[str, Any]):
        """接收到帧事件"""
        self.stats["total_bytes_received"] += len(frame_data)
        # 转发给其他协议
        asyncio.create_task(self.broadcast_frame(frame_data, metadata))

# 便捷函数
async def create_server(config: Optional[Config] = None) -> MirroringServer:
    """创建并启动服务器"""
    server = MirroringServer(config)
    await server.start()
    return server

async def run_server(config: Optional[Config] = None):
    """运行服务器（阻塞）"""
    server = await create_server(config)
    try:
        # 保持运行
        while server.is_running:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    finally:
        await server.stop()
