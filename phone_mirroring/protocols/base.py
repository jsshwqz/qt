"""
基础协议接口
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Callable, Tuple
import threading
import time
import logging

logger = logging.getLogger(__name__)

class BaseProtocol(ABC):
    """协议基类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_running = False
        self.stats = {
            "connected_clients": 0,
            "bytes_sent": 0,
            "bytes_received": 0,
            "frames_sent": 0,
            "errors": 0,
            "start_time": 0,
            "last_activity": 0
        }
        self.callbacks = {}
        self._lock = threading.Lock()
    
    @abstractmethod
    async def start(self) -> bool:
        """启动协议服务"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """停止协议服务"""
        pass
    
    @abstractmethod
    async def send_frame(self, frame_data: bytes, metadata: Dict[str, Any]) -> bool:
        """发送视频帧"""
        pass
    
    @abstractmethod
    async def send_audio(self, audio_data: bytes, metadata: Dict[str, Any]) -> bool:
        """发送音频数据"""
        pass
    
    @abstractmethod
    async def handle_control(self, control_data: Dict[str, Any]) -> bool:
        """处理控制指令"""
        pass
    
    def register_callback(self, event: str, callback: Callable):
        """注册回调函数"""
        with self._lock:
            if event not in self.callbacks:
                self.callbacks[event] = []
            self.callbacks[event].append(callback)
    
    def unregister_callback(self, event: str, callback: Callable):
        """注销回调函数"""
        with self._lock:
            if event in self.callbacks:
                try:
                    self.callbacks[event].remove(callback)
                except ValueError:
                    pass
    
    def emit(self, event: str, *args, **kwargs):
        """触发回调"""
        with self._lock:
            callbacks = self.callbacks.get(event, [])
        
        for callback in callbacks:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback error for {event}: {e}")
    
    def update_stats(self, **kwargs):
        """更新统计信息"""
        now = time.time()
        self.stats["last_activity"] = now
        
        for key, value in kwargs.items():
            if key in self.stats:
                if isinstance(value, int) or isinstance(value, float):
                    self.stats[key] += value
                else:
                    self.stats[key] = value
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = self.stats.copy()
        if stats["start_time"] > 0:
            stats["uptime"] = time.time() - stats["start_time"]
        return stats
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats.update({
            "bytes_sent": 0,
            "bytes_received": 0,
            "frames_sent": 0,
            "errors": 0,
            "start_time": time.time() if self.is_running else 0
        })