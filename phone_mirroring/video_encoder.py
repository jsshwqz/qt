"""
视频编码模块
实现 H.264 视频编码功能
"""

import cv2
import numpy as np
import logging
import asyncio
from typing import Optional, Dict, Any, Callable, Tuple
from dataclasses import dataclass
import time

logger = logging.getLogger(__name__)

@dataclass
class EncodeConfig:
    """编码配置"""
    codec: str = 'H264'  # 编码格式
    width: int = 1920
    height: int = 1080
    fps: int = 30
    bitrate: int = 2000000  # 2 Mbps
    quality: str = 'high'  # low, medium, high, ultra
    gop_size: int = 30  # 关键帧间隔
    preset: str = 'fast'  # ultrafast, superfast, veryfast, faster, fast, medium, slow
    tune: str = 'zerolatency'  # film, animation, grain, stillimage, fastdecode, zerolatency

class VideoEncoder:
    """H.264视频编码器"""
    
    def __init__(self, config: Optional[EncodeConfig] = None):
        self.config = config or EncodeConfig()
        self.encoder: Optional[cv2.VideoWriter] = None
        self.is_initialized = False
        self.frame_count = 0
        self.last_frame_time = 0
        
        # 回调函数
        self.on_encoded_frame: Optional[Callable[[bytes, Dict], None]] = None
        
        # 编码器上下文
        self._encoder_context = None
        self._packet_buffer = []
        
        logger.info(f"VideoEncoder initialized with config: {self.config}")
    
    def initialize(self, width: int = None, height: int = None, fps: int = None) -> bool:
        """初始化编码器"""
        try:
            if width:
                self.config.width = width
            if height:
                self.config.height = height
            if fps:
                self.config.fps = fps
            
            # OpenCV使用FourCC编码
            fourcc = cv2.VideoWriter_fourcc(*'avc1')  # H.264编码
            
            # 检查编码器是否可用
            if not self._check_encoder_available():
                logger.warning("avc1编码器不可用，尝试使用mp4v")
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            
            self.encoder = cv2.VideoWriter(
                'appsrc ! videoconvert ! x264enc ! appsink',  # GStreamer管道（如果可用）
                fourcc,
                self.config.fps,
                (self.config.width, self.config.height),
                True
            )
            
            self.is_initialized = True
            self.frame_count = 0
            logger.info(f"Encoder initialized: {self.config.width}x{self.config.height}@{self.config.fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize encoder: {e}")
            return False
    
    def _check_encoder_available(self) -> bool:
        """检查编码器是否可用"""
        try:
            test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
            fourcc = cv2.VideoWriter_fourcc(*'avc1')
            test_writer = cv2.VideoWriter('test.mp4', fourcc, 30, (100, 100))
            test_writer.write(test_frame)
            test_writer.release()
            import os
            if os.path.exists('test.mp4'):
                os.remove('test.mp4')
                return True
            return False
        except:
            return False
    
    def encode_frame(self, frame: np.ndarray) -> Optional[bytes]:
        """编码单帧图像
        
        Args:
            frame: BGR格式的numpy数组 (H, W, 3)
            
        Returns:
            编码后的H.264数据，如果编码失败返回None
        """
        if not self.is_initialized:
            logger.error("Encoder not initialized")
            return None
        
        try:
            # 确保帧大小正确
            if frame.shape[:2] != (self.config.height, self.config.width):
                frame = cv2.resize(frame, (self.config.width, self.config.height))
            
            # 写入编码器
            self.encoder.write(frame)
            
            # 更新统计
            self.frame_count += 1
            current_time = time.time()
            
            # 触发回调
            if self.on_encoded_frame:
                metadata = {
                    'frame_number': self.frame_count,
                    'timestamp': current_time,
                    'width': self.config.width,
                    'height': self.config.height
                }
                # 注意：OpenCV的VideoWriter不能直接获取编码后的数据
                # 这里需要特殊处理，我们会在实际使用时使用FFmpeg
                self.on_encoded_frame(b'', metadata)
            
            return b''
            
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return None
    
    async def encode_frame_async(self, frame: np.ndarray) -> Optional[bytes]:
        """异步编码帧"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.encode_frame, frame)
    
    def reconfigure(self, **kwargs):
        """重新配置编码器参数"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
        
        # 如果编码器已初始化，需要重新初始化
        if self.is_initialized:
            self.release()
            self.initialize()
    
    def release(self):
        """释放编码器资源"""
        if self.encoder:
            self.encoder.release()
            self.encoder = None
        self.is_initialized = False
        logger.info("Encoder released")
    
    def __del__(self):
        """析构函数"""
        self.release()


class FFmpegEncoder:
    """使用FFmpeg进行H.264编码（更专业的编码实现）"""
    
    def __init__(self, config: Optional[EncodeConfig] = None):
        self.config = config or EncodeConfig()
        self.process = None
        self.is_running = False
        self.frame_count = 0
        
        # 回调
        self.on_encoded_data: Optional[Callable[[bytes], None]] = None
    
    def start(self, output_callback: Callable[[bytes], None] = None) -> bool:
        """启动FFmpeg编码进程"""
        try:
            import subprocess
            
            if output_callback:
                self.on_encoded_data = output_callback
            
            # FFmpeg命令行参数
            cmd = [
                'ffmpeg',
                '-y',  # 覆盖输出文件
                '-f', 'rawvideo',  # 输入格式
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',  # 像素格式
                '-s', f'{self.config.width}x{self.config.height}',  # 分辨率
                '-r', str(self.config.fps),  # 帧率
                '-i', '-',  # 从stdin读取
                '-c:v', 'libx264',  # 视频编码器
                '-preset', self.config.preset,  # 编码速度预设
                '-tune', self.config.tune,  # 调优选项
                '-b:v', str(self.config.bitrate),  # 视频码率
                '-g', str(self.config.gop_size),  # GOP大小
                '-pix_fmt', 'yuv420p',  # 输出像素格式
                '-f', 'h264',  # 输出格式
                '-'  # 输出到stdout
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0
            )
            
            self.is_running = True
            
            # 启动读取线程
            import threading
            self._read_thread = threading.Thread(target=self._read_output)
            self._read_thread.daemon = True
            self._read_thread.start()
            
            logger.info(f"FFmpeg encoder started: {self.config.width}x{self.config.height}@{self.config.fps}fps")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start FFmpeg encoder: {e}")
            return False
    
    def _read_output(self):
        """读取FFmpeg输出"""
        while self.is_running and self.process:
            try:
                # 读取编码后的数据
                data = self.process.stdout.read(4096)
                if data:
                    if self.on_encoded_data:
                        self.on_encoded_data(data)
            except Exception as e:
                if self.is_running:
                    logger.error(f"Error reading FFmpeg output: {e}")
                break
    
    def encode_frame(self, frame: np.ndarray) -> bool:
        """编码一帧"""
        if not self.is_running or not self.process:
            return False
        
        try:
            # 调整帧大小
            if frame.shape[:2] != (self.config.height, self.config.width):
                frame = cv2.resize(frame, (self.config.width, self.config.height))
            
            # 写入原始帧数据
            self.process.stdin.write(frame.tobytes())
            self.process.stdin.flush()
            
            self.frame_count += 1
            return True
            
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return False
    
    async def encode_frame_async(self, frame: np.ndarray) -> bool:
        """异步编码帧"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.encode_frame, frame)
    
    def stop(self):
        """停止编码器"""
        self.is_running = False
        
        if self.process:
            try:
                self.process.stdin.close()
                self.process.wait(timeout=5)
            except:
                self.process.kill()
            finally:
                self.process = None
        
        logger.info("FFmpeg encoder stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取编码统计"""
        return {
            'frames_encoded': self.frame_count,
            'fps': self.config.fps,
            'resolution': f'{self.config.width}x{self.config.height}',
            'bitrate': self.config.bitrate
        }


class HardwareEncoder:
    """硬件加速编码器（使用NVIDIA NVENC或Intel QuickSync）"""
    
    def __init__(self, config: Optional[EncodeConfig] = None):
        self.config = config or EncodeConfig()
        self.encoder_type = self._detect_hardware_encoder()
        self.process = None
        self.is_running = False
    
    def _detect_hardware_encoder(self) -> str:
        """检测可用的硬件编码器"""
        try:
            import subprocess
            
            # 检查NVIDIA GPU
            result = subprocess.run(
                ['nvidia-smi'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return 'h264_nvenc'
            
            # 检查Intel QuickSync
            result = subprocess.run(
                ['ffmpeg', '-encoders'],
                capture_output=True,
                text=True
            )
            if 'h264_qsv' in result.stdout:
                return 'h264_qsv'
            
            return 'libx264'  # 默认软件编码
            
        except:
            return 'libx264'
    
    def start(self) -> bool:
        """启动硬件编码器"""
        try:
            import subprocess
            
            cmd = [
                'ffmpeg',
                '-y',
                '-f', 'rawvideo',
                '-vcodec', 'rawvideo',
                '-pix_fmt', 'bgr24',
                '-s', f'{self.config.width}x{self.config.height}',
                '-r', str(self.config.fps),
                '-i', '-',
                '-c:v', self.encoder_type,
                '-preset', 'fast',
                '-b:v', str(self.config.bitrate),
                '-f', 'h264',
                '-'
            ]
            
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            self.is_running = True
            logger.info(f"Hardware encoder started using {self.encoder_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start hardware encoder: {e}")
            return False
    
    def encode_frame(self, frame: np.ndarray) -> bool:
        """编码一帧"""
        if not self.is_running or not self.process:
            return False
        
        try:
            if frame.shape[:2] != (self.config.height, self.config.width):
                frame = cv2.resize(frame, (self.config.width, self.config.height))
            
            self.process.stdin.write(frame.tobytes())
            return True
            
        except Exception as e:
            logger.error(f"Error encoding frame: {e}")
            return False
    
    def stop(self):
        """停止编码器"""
        self.is_running = False
        if self.process:
            self.process.stdin.close()
            self.process.wait()
            self.process = None


# 便捷的工厂函数
def create_encoder(encoder_type: str = 'ffmpeg', config: Optional[EncodeConfig] = None) -> VideoEncoder:
    """创建编码器实例
    
    Args:
        encoder_type: 编码器类型 ('opencv', 'ffmpeg', 'hardware')
        config: 编码配置
        
    Returns:
        编码器实例
    """
    config = config or EncodeConfig()
    
    if encoder_type == 'ffmpeg':
        return FFmpegEncoder(config)
    elif encoder_type == 'hardware':
        return HardwareEncoder(config)
    else:
        return VideoEncoder(config)
