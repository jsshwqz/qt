#!/usr/bin/env python3
"""
主应用集成模块
整合所有组件，提供统一的启动接口
"""

import sys
import asyncio
import logging
from typing import Optional, Dict, Any, Callable
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from phone_mirroring.server import MirroringServer
from phone_mirroring.config import Config, Presets
from phone_mirroring.streaming_manager import StreamingManager
from phone_mirroring.protocols.adb import ADBProtocol
from phone_mirroring.error_handling import ErrorHandler

logger = logging.getLogger(__name__)

class MirroringApp:
    """投屏应用主类"""
    
    def __init__(self):
        self.server: Optional[MirroringServer] = None
        self.streaming_manager: Optional[StreamingManager] = None
        self.adb_protocol: Optional[ADBProtocol] = None
        self.config: Config = Config()
        self.error_handler = ErrorHandler()
        
        # 回调
        self.on_server_started: Optional[Callable] = None
        self.on_server_stopped: Optional[Callable] = None
        self.on_frame_captured: Optional[Callable] = None
        self.on_client_connected: Optional[Callable] = None
        self.on_client_disconnected: Optional[Callable] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
    
    def setup(self, config: Optional[Config] = None, preset: str = None):
        """配置应用
        
        Args:
            config: 自定义配置
            preset: 预设配置名称 ('high_quality', 'low_latency', 'mobile_optimized')
        """
        if config:
            self.config = config
        elif preset:
            if preset == 'high_quality':
                self.config = Presets.high_quality()
            elif preset == 'low_latency':
                self.config = Presets.low_latency()
            elif preset == 'mobile_optimized':
                self.config = Presets.mobile_optimized()
        
        logger.info(f"App configured with preset: {preset or 'default'}")
    
    async def start_server_mode(self) -> bool:
        """启动服务器模式"""
        try:
            logger.info("🚀 启动服务器模式...")
            
            self.server = MirroringServer(self.config)
            
            # 注册回调
            if self.on_client_connected:
                self.server.register_callback("client_connected", self.on_client_connected)
            if self.on_client_disconnected:
                self.server.register_callback("client_disconnected", self.on_client_disconnected)
            
            success = await self.server.start()
            
            if success:
                logger.info("✅ 服务器启动成功")
                if self.on_server_started:
                    self.on_server_started()
                return True
            else:
                logger.error("❌ 服务器启动失败")
                return False
                
        except Exception as e:
            logger.error(f"启动服务器失败: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    async def start_screen_mirroring(self, config: Optional[Dict] = None) -> bool:
        """启动屏幕投屏模式"""
        try:
            logger.info("🚀 启动屏幕投屏...")
            
            stream_config = config or {
                'port': self.config.network.port,
                'width': self.config.video.width,
                'height': self.config.video.height,
                'fps': self.config.video.fps,
                'bitrate': self.config.video.bitrate
            }
            
            self.streaming_manager = StreamingManager()
            success = await self.streaming_manager.start_screen_streaming(stream_config)
            
            if success:
                logger.info("✅ 屏幕投屏已启动")
                logger.info(f"📡 RTSP地址: rtsp://localhost:{stream_config['port']}/")
                return True
            else:
                logger.error("❌ 屏幕投屏启动失败")
                return False
                
        except Exception as e:
            logger.error(f"启动屏幕投屏失败: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    async def start_adb_mirroring(self, device_id: Optional[str] = None) -> bool:
        """启动ADB投屏模式"""
        try:
            logger.info("🚀 启动ADB投屏...")
            
            # 创建ADB协议
            adb_config = {
                'adb_port': 5555,
                'device_id': device_id or '',
                'max_width': self.config.video.width,
                'max_height': self.config.video.height,
                'bitrate': self.config.video.bitrate,
                'max_fps': self.config.video.fps
            }
            
            self.adb_protocol = ADBProtocol(adb_config)
            
            if not await self.adb_protocol.start():
                logger.error("❌ ADB连接失败")
                return False
            
            logger.info(f"✅ ADB已连接: {self.adb_protocol.active_device}")
            
            # 启动RTSP流
            stream_config = {
                'port': self.config.network.port
            }
            
            self.streaming_manager = StreamingManager()
            success = await self.streaming_manager.start_adb_streaming(
                self.adb_protocol, 
                stream_config
            )
            
            if success:
                logger.info("✅ ADB投屏已启动")
                logger.info(f"📡 RTSP地址: rtsp://localhost:{stream_config['port']}/")
                return True
            else:
                logger.error("❌ ADB投屏流启动失败")
                await self.adb_protocol.stop()
                return False
                
        except Exception as e:
            logger.error(f"启动ADB投屏失败: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    async def stop(self):
        """停止所有服务"""
        logger.info("🛑 正在停止所有服务...")
        
        # 停止流管理器
        if self.streaming_manager:
            await self.streaming_manager.stop()
            self.streaming_manager = None
        
        # 停止ADB
        if self.adb_protocol:
            await self.adb_protocol.stop()
            self.adb_protocol = None
        
        # 停止服务器
        if self.server:
            await self.server.stop()
            self.server = None
        
        if self.on_server_stopped:
            self.on_server_stopped()
        
        logger.info("✅ 所有服务已停止")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取运行统计"""
        stats = {
            'server_running': self.server.is_running if self.server else False,
            'streaming_active': self.streaming_manager.is_running if self.streaming_manager else False
        }
        
        if self.server:
            stats['server'] = self.server.get_stats()
        
        if self.streaming_manager:
            stats['streaming'] = self.streaming_manager.get_stats()
        
        if self.adb_protocol:
            stats['adb'] = self.adb_protocol.get_device_info()
        
        return stats
    
    async def handle_control(self, control_data: Dict[str, Any]) -> bool:
        """处理控制指令"""
        if self.server:
            return await self.server.handle_control(control_data)
        
        if self.adb_protocol:
            return await self.adb_protocol.handle_control(control_data)
        
        return False
    
    def set_video_quality(self, quality: str):
        """设置视频质量"""
        if self.streaming_manager:
            self.streaming_manager.set_quality(quality)
        
        # 更新配置
        quality_map = {
            'low': {'width': 1280, 'height': 720, 'fps': 15, 'bitrate': 1000000},
            'medium': {'width': 1920, 'height': 1080, 'fps': 30, 'bitrate': 2000000},
            'high': {'width': 1920, 'height': 1080, 'fps': 30, 'bitrate': 4000000},
            'ultra': {'width': 2560, 'height': 1440, 'fps': 60, 'bitrate': 8000000}
        }
        
        settings = quality_map.get(quality, quality_map['medium'])
        self.config.video.width = settings['width']
        self.config.video.height = settings['height']
        self.config.video.fps = settings['fps']
        self.config.video.bitrate = settings['bitrate']
        
        logger.info(f"Video quality set to {quality}")


# 便捷函数
async def quick_start_screen_mirroring(
    port: int = 8554,
    quality: str = 'medium'
) -> MirroringApp:
    """快速启动屏幕投屏
    
    Args:
        port: RTSP服务器端口
        quality: 视频质量 ('low', 'medium', 'high', 'ultra')
        
    Returns:
        MirroringApp实例
    """
    app = MirroringApp()
    app.setup(preset=quality)
    app.config.network.port = port
    
    success = await app.start_screen_mirroring()
    if not success:
        raise RuntimeError("Failed to start screen mirroring")
    
    return app

async def quick_start_adb_mirroring(
    device_id: Optional[str] = None,
    port: int = 8554
) -> MirroringApp:
    """快速启动ADB投屏
    
    Args:
        device_id: 设备ID
        port: RTSP服务器端口
        
    Returns:
        MirroringApp实例
    """
    app = MirroringApp()
    
    success = await app.start_adb_mirroring(device_id)
    if not success:
        raise RuntimeError("Failed to start ADB mirroring")
    
    return app

async def quick_start_server(
    config: Optional[Config] = None,
    port: int = 8554
) -> MirroringApp:
    """快速启动完整服务器
    
    Args:
        config: 自定义配置
        port: 服务器端口
        
    Returns:
        MirroringApp实例
    """
    app = MirroringApp()
    
    if config:
        app.setup(config=config)
    
    app.config.network.port = port
    
    success = await app.start_server_mode()
    if not success:
        raise RuntimeError("Failed to start server")
    
    return app


# 主函数
async def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WiFi手机投屏系统')
    parser.add_argument('mode', choices=['screen', 'adb', 'server'], 
                       help='运行模式')
    parser.add_argument('--port', type=int, default=8554,
                       help='RTSP服务器端口 (默认: 8554)')
    parser.add_argument('--quality', choices=['low', 'medium', 'high', 'ultra'],
                       default='medium', help='视频质量')
    parser.add_argument('--device', type=str, default=None,
                       help='ADB设备ID (仅ADB模式)')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    app = MirroringApp()
    
    try:
        if args.mode == 'screen':
            await app.start_screen_mirroring({
                'port': args.port,
                'quality': args.quality
            })
        elif args.mode == 'adb':
            await app.start_adb_mirroring(args.device)
        elif args.mode == 'server':
            await app.start_server_mode()
        
        # 保持运行
        logger.info("按 Ctrl+C 停止")
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("\n正在停止...")
        await app.stop()

if __name__ == "__main__":
    asyncio.run(main())
