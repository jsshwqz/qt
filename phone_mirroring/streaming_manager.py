"""
流媒体管理器模块
整合屏幕捕获、视频编码和RTSP服务器
"""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable
from enum import Enum

from phone_mirroring.video_encoder import FFmpegEncoder, EncodeConfig, create_encoder
from phone_mirroring.screen_capture import ScreenCapture, CaptureConfig, create_capture
from phone_mirroring.protocols.rtsp import RTSPProtocol

logger = logging.getLogger(__name__)

class StreamSource(Enum):
    """视频流来源"""
    SCREEN = "screen"      # 桌面屏幕
    ADB = "adb"            # Android设备
    FILE = "file"          # 视频文件
    CAMERA = "camera"      # 摄像头

class StreamingManager:
    """流媒体管理器"""
    
    def __init__(self):
        self.is_running = False
        self.source_type: StreamSource = StreamSource.SCREEN
        
        # 组件
        self.screen_capture: Optional[ScreenCapture] = None
        self.video_encoder: Optional[FFmpegEncoder] = None
        self.rtsp_server: Optional[RTSPProtocol] = None
        
        # 视频缓冲区
        self.video_buffer = []
        self.buffer_lock = asyncio.Lock()
        
        # 回调
        self.on_frame_ready: Optional[Callable[[bytes, Dict], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # 统计
        self.stats = {
            'frames_captured': 0,
            'frames_encoded': 0,
            'frames_dropped': 0,
            'bytes_sent': 0,
            'start_time': 0,
            'fps': 0
        }
        
        # 任务
        self.capture_task: Optional[asyncio.Task] = None
        self.stream_task: Optional[asyncio.Task] = None
    
    async def start_screen_streaming(self, config: Optional[Dict] = None) -> bool:
        """启动桌面屏幕投屏
        
        Args:
            config: 配置字典，包含resolution, fps, bitrate等
        """
        try:
            config = config or {}
            
            # 1. 启动RTSP服务器
            logger.info("Starting RTSP server...")
            rtsp_config = {
                'port': config.get('port', 8554),
                'rtp_port_start': config.get('rtp_port_start', 5000)
            }
            self.rtsp_server = RTSPProtocol(rtsp_config)
            
            if not await self.rtsp_server.start():
                logger.error("Failed to start RTSP server")
                return False
            
            # 2. 初始化屏幕捕获
            logger.info("Initializing screen capture...")
            capture_method = config.get('capture_method', 'mss')
            self.screen_capture = create_capture(
                method=capture_method,
                fps=config.get('fps', 30)
            )
            
            if not self.screen_capture.initialize():
                logger.error("Failed to initialize screen capture")
                await self.rtsp_server.stop()
                return False
            
            # 3. 初始化视频编码器
            logger.info("Initializing video encoder...")
            encode_config = EncodeConfig(
                width=config.get('width', 1920),
                height=config.get('height', 1080),
                fps=config.get('fps', 30),
                bitrate=config.get('bitrate', 2000000),
                preset='fast',
                tune='zerolatency'
            )
            
            self.video_encoder = FFmpegEncoder(encode_config)
            
            # 设置编码器输出回调
            self.video_encoder.on_encoded_data = self._on_encoded_data
            
            if not self.video_encoder.start():
                logger.error("Failed to start video encoder")
                await self.stop()
                return False
            
            # 4. 设置RTSP视频源
            self.rtsp_server.set_video_source(self._get_video_frame)
            
            # 5. 启动捕获循环
            self.is_running = True
            self.source_type = StreamSource.SCREEN
            self.stats['start_time'] = time.time()
            
            self.capture_task = asyncio.create_task(self._capture_loop())
            self.stream_task = asyncio.create_task(self._streaming_loop())
            
            logger.info("Screen streaming started successfully")
            logger.info(f"RTSP URL: rtsp://localhost:{rtsp_config['port']}/")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start screen streaming: {e}")
            await self.stop()
            return False
    
    async def start_adb_streaming(self, adb_protocol, config: Optional[Dict] = None) -> bool:
        """启动ADB设备投屏
        
        Args:
            adb_protocol: ADBProtocol实例
            config: 配置字典
        """
        try:
            config = config or {}
            
            # 1. 启动RTSP服务器
            logger.info("Starting RTSP server for ADB...")
            rtsp_config = {
                'port': config.get('port', 8554),
                'rtp_port_start': config.get('rtp_port_start', 5000)
            }
            self.rtsp_server = RTSPProtocol(rtsp_config)
            
            if not await self.rtsp_server.start():
                logger.error("Failed to start RTSP server")
                return False
            
            # 2. 设置ADB视频帧回调
            adb_protocol.set_video_frame_callback(self._on_adb_frame)
            
            # 3. 设置RTSP视频源
            self.rtsp_server.set_video_source(self._get_video_frame)
            
            self.is_running = True
            self.source_type = StreamSource.ADB
            self.stats['start_time'] = time.time()
            
            self.stream_task = asyncio.create_task(self._streaming_loop())
            
            logger.info("ADB streaming started successfully")
            logger.info(f"RTSP URL: rtsp://localhost:{rtsp_config['port']}/")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start ADB streaming: {e}")
            await self.stop()
            return False
    
    async def stop(self) -> bool:
        """停止流媒体"""
        try:
            self.is_running = False
            
            # 停止任务
            for task in [self.capture_task, self.stream_task]:
                if task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
            
            # 停止编码器
            if self.video_encoder:
                self.video_encoder.stop()
                self.video_encoder = None
            
            # 停止屏幕捕获
            if self.screen_capture:
                self.screen_capture.stop_capture()
                self.screen_capture = None
            
            # 停止RTSP服务器
            if self.rtsp_server:
                await self.rtsp_server.stop()
                self.rtsp_server = None
            
            # 清空缓冲区
            self.video_buffer.clear()
            
            logger.info("Streaming stopped")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping streaming: {e}")
            return False
    
    async def _capture_loop(self):
        """屏幕捕获循环"""
        try:
            frame_interval = 1.0 / self.screen_capture.config.fps
            
            while self.is_running:
                loop_start = time.time()
                
                # 捕获屏幕
                frame = self.screen_capture.capture_frame()
                
                if frame is not None and self.video_encoder:
                    # 编码帧
                    success = await self.video_encoder.encode_frame_async(frame)
                    if success:
                        self.stats['frames_captured'] += 1
                
                # 控制帧率
                elapsed = time.time() - loop_start
                sleep_time = frame_interval - elapsed
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
                    
        except asyncio.CancelledError:
            logger.info("Capture loop cancelled")
        except Exception as e:
            logger.error(f"Capture loop error: {e}")
            if self.on_error:
                self.on_error(e)
    
    async def _streaming_loop(self):
        """流媒体发送循环"""
        try:
            while self.is_running:
                await asyncio.sleep(1)
                
                # 更新统计
                uptime = time.time() - self.stats['start_time']
                if uptime > 0:
                    self.stats['fps'] = self.stats['frames_captured'] / uptime
                    
        except asyncio.CancelledError:
            logger.info("Streaming loop cancelled")
        except Exception as e:
            logger.error(f"Streaming loop error: {e}")
    
    def _on_encoded_data(self, data: bytes):
        """编码数据回调"""
        if data:
            # 添加到缓冲区
            self.video_buffer.append(data)
            
            # 限制缓冲区大小
            if len(self.video_buffer) > 30:
                self.video_buffer.pop(0)
                self.stats['frames_dropped'] += 1
            
            self.stats['frames_encoded'] += 1
    
    def _on_adb_frame(self, frame_data: bytes, metadata: Dict):
        """ADB视频帧回调"""
        self.video_buffer.append(frame_data)
        self.stats['frames_captured'] += 1
        
        # 通知RTSP服务器有新帧
        if self.rtsp_server:
            asyncio.create_task(
                self.rtsp_server.send_frame(frame_data, metadata)
            )
    
    def _get_video_frame(self) -> Optional[bytes]:
        """获取视频帧（供RTSP服务器调用）"""
        if self.video_buffer:
            return self.video_buffer.pop(0)
        return None
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        uptime = time.time() - self.stats['start_time'] if self.stats['start_time'] > 0 else 0
        
        stats = {
            'is_running': self.is_running,
            'source_type': self.source_type.value,
            'uptime': uptime,
            'fps': self.stats['fps'],
            'frames_captured': self.stats['frames_captured'],
            'frames_encoded': self.stats['frames_encoded'],
            'frames_dropped': self.stats['frames_dropped']
        }
        
        # 添加RTSP服务器状态
        if self.rtsp_server:
            stats['rtsp'] = self.rtsp_server.get_session_info()
        
        return stats
    
    def set_quality(self, quality: str):
        """设置视频质量
        
        Args:
            quality: 'low', 'medium', 'high', 'ultra'
        """
        quality_settings = {
            'low': {'bitrate': 1000000, 'fps': 15, 'preset': 'ultrafast'},
            'medium': {'bitrate': 2000000, 'fps': 30, 'preset': 'fast'},
            'high': {'bitrate': 4000000, 'fps': 30, 'preset': 'medium'},
            'ultra': {'bitrate': 8000000, 'fps': 60, 'preset': 'slow'}
        }
        
        settings = quality_settings.get(quality, quality_settings['medium'])
        
        if self.video_encoder:
            self.video_encoder.reconfigure(**settings)
        
        if self.screen_capture:
            self.screen_capture.set_fps(settings['fps'])
        
        logger.info(f"Quality set to {quality}: {settings}")


# 便捷函数
async def start_screen_mirror(config: Optional[Dict] = None) -> StreamingManager:
    """快速启动屏幕投屏
    
    Args:
        config: 配置字典
        
    Returns:
        StreamingManager实例
    """
    manager = StreamingManager()
    success = await manager.start_screen_streaming(config)
    
    if not success:
        raise RuntimeError("Failed to start screen mirroring")
    
    return manager

async def start_adb_mirror(adb_protocol, config: Optional[Dict] = None) -> StreamingManager:
    """快速启动ADB设备投屏
    
    Args:
        adb_protocol: ADBProtocol实例
        config: 配置字典
        
    Returns:
        StreamingManager实例
    """
    manager = StreamingManager()
    success = await manager.start_adb_streaming(adb_protocol, config)
    
    if not success:
        raise RuntimeError("Failed to start ADB mirroring")
    
    return manager
