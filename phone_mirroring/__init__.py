"""
WiFi手机投屏系统 - 统一入口
支持多种投屏协议：RTSP、ADB
"""

from .server import MirroringServer
from .client import MirroringClient
from .config import Config, Presets
from .protocols.rtsp import RTSPProtocol
from .protocols.adb import ADBProtocol
from .app_main import MirroringApp

__version__ = "1.0.0"
__all__ = [
    "MirroringServer",
    "MirroringClient",
    "RTSPProtocol",
    "ADBProtocol",
    "MirroringApp",
    "Config",
    "Presets"
]
