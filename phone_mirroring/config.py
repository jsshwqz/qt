"""
配置管理模块
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import os

@dataclass
class VideoConfig:
    """视频配置"""
    width: int = 1920
    height: int = 1080
    fps: int = 30
    bitrate: int = 2000000  # 2Mbps
    codec: str = "H264"
    quality: str = "high"  # low, medium, high, ultra

@dataclass
class AudioConfig:
    """音频配置"""
    enabled: bool = True
    bitrate: int = 128000  # 128kbps
    codec: str = "AAC"
    sample_rate: int = 44100
    channels: int = 2

@dataclass
class NetworkConfig:
    """网络配置"""
    host: str = "0.0.0.0"
    port: int = 8080
    max_connections: int = 10
    buffer_size: int = 65536
    timeout: int = 30
    keepalive: bool = True

@dataclass
class ControlConfig:
    """控制配置"""
    enable_touch: bool = True
    enable_keyboard: bool = True
    enable_mouse: bool = True
    enable_clipboard: bool = False
    latency_threshold: int = 100  # ms

@dataclass
class Config:
    """主配置类"""
    video: VideoConfig = field(default_factory=VideoConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    control: ControlConfig = field(default_factory=ControlConfig)
    
    # 协议配置
    enabled_protocols: List[str] = field(default_factory=lambda: ["RTSP", "WebRTC", "ADB"])
    
    # 录制配置
    recording: Dict = field(default_factory=dict)
    
    # 安全配置
    security: Dict = field(default_factory=lambda: {
        "require_password": False,
        "password": "",
        "allow_lan": True,
        "ssl_cert": "",
        "ssl_key": ""
    })
    
    # 调试配置
    debug: Dict = field(default_factory=lambda: {
        "log_level": "INFO",
        "log_file": "",
        "stats_enabled": False,
        "stats_interval": 5000  # ms
    })

    def load_from_file(self, file_path: str):
        """从文件加载配置"""
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._update_from_dict(data)
    
    def save_to_file(self, file_path: str):
        """保存配置到文件"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "video": {
                "width": self.video.width,
                "height": self.video.height,
                "fps": self.video.fps,
                "bitrate": self.video.bitrate,
                "codec": self.video.codec,
                "quality": self.video.quality
            },
            "audio": {
                "enabled": self.audio.enabled,
                "bitrate": self.audio.bitrate,
                "codec": self.audio.codec,
                "sample_rate": self.audio.sample_rate,
                "channels": self.audio.channels
            },
            "network": {
                "host": self.network.host,
                "port": self.network.port,
                "max_connections": self.network.max_connections,
                "buffer_size": self.network.buffer_size,
                "timeout": self.network.timeout,
                "keepalive": self.network.keepalive
            },
            "control": {
                "enable_touch": self.control.enable_touch,
                "enable_keyboard": self.control.enable_keyboard,
                "enable_mouse": self.control.enable_mouse,
                "enable_clipboard": self.control.enable_clipboard,
                "latency_threshold": self.control.latency_threshold
            },
            "enabled_protocols": self.enabled_protocols,
            "recording": self.recording,
            "security": self.security,
            "debug": self.debug
        }
    
    def _update_from_dict(self, data: Dict):
        """从字典更新配置"""
        if "video" in data:
            for k, v in data["video"].items():
                if hasattr(self.video, k):
                    setattr(self.video, k, v)
        
        if "audio" in data:
            for k, v in data["audio"].items():
                if hasattr(self.audio, k):
                    setattr(self.audio, k, v)
        
        if "network" in data:
            for k, v in data["network"].items():
                if hasattr(self.network, k):
                    setattr(self.network, k, v)
        
        if "control" in data:
            for k, v in data["control"].items():
                if hasattr(self.control, k):
                    setattr(self.control, k, v)
        
        for key in ["enabled_protocols", "recording", "security", "debug"]:
            if key in data:
                setattr(self, key, data[key])

# 预设配置
class Presets:
    """预设配置"""
    
    @staticmethod
    def high_quality() -> Config:
        """高质量配置"""
        config = Config()
        config.video.width = 1920
        config.video.height = 1080
        config.video.fps = 60
        config.video.bitrate = 5000000
        config.video.quality = "ultra"
        config.audio.bitrate = 320000
        return config
    
    @staticmethod
    def low_latency() -> Config:
        """低延迟配置"""
        config = Config()
        config.video.fps = 30
        config.video.bitrate = 1000000
        config.control.latency_threshold = 50
        config.network.buffer_size = 32768
        return config
    
    @staticmethod
    def mobile_optimized() -> Config:
        """移动优化配置"""
        config = Config()
        config.video.width = 1280
        config.video.height = 720
        config.video.fps = 30
        config.video.bitrate = 1500000
        config.network.buffer_size = 16384
        return config