"""
屏幕捕获模块
支持 Windows 平台桌面屏幕捕获
"""

import numpy as np
import cv2
import logging
import asyncio
import threading
import time
from typing import Optional, Dict, Any, Callable, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class CaptureMethod(Enum):
    """捕获方法枚举"""
    PIL = "pil"           # Pillow库
    MSS = "mss"           # MSS库（推荐，性能更好）
    D3D = "d3d"           # Direct3D（Windows专属，高性能）
    OPENCV = "opencv"     # OpenCV

@dataclass
class CaptureConfig:
    """屏幕捕获配置"""
    method: CaptureMethod = CaptureMethod.MSS
    fps: int = 30
    region: Optional[Tuple[int, int, int, int]] = None  # (left, top, width, height)
    scale: float = 1.0  # 缩放比例
    quality: int = 95   # 图像质量（JPEG压缩）

class ScreenCapture:
    """屏幕捕获器"""
    
    def __init__(self, config: Optional[CaptureConfig] = None):
        self.config = config or CaptureConfig()
        self.is_capturing = False
        self.capture_thread: Optional[threading.Thread] = None
        self.last_frame: Optional[np.ndarray] = None
        self.frame_count = 0
        
        # 回调函数
        self.on_frame_captured: Optional[Callable[[np.ndarray, Dict], None]] = None
        self.on_error: Optional[Callable[[Exception], None]] = None
        
        # 捕获器实例
        self._capture_impl = None
        self._frame_buffer = []
        self._buffer_lock = threading.Lock()
        
        # 性能统计
        self._last_capture_time = 0
        self._capture_times = []
        
        logger.info(f"ScreenCapture initialized with method: {self.config.method.value}")
    
    def initialize(self) -> bool:
        """初始化捕获器"""
        try:
            if self.config.method == CaptureMethod.MSS:
                return self._init_mss()
            elif self.config.method == CaptureMethod.PIL:
                return self._init_pil()
            elif self.config.method == CaptureMethod.D3D:
                return self._init_d3d()
            elif self.config.method == CaptureMethod.OPENCV:
                return self._init_opencv()
            else:
                logger.error(f"Unknown capture method: {self.config.method}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize screen capture: {e}")
            if self.on_error:
                self.on_error(e)
            return False
    
    def _init_mss(self) -> bool:
        """初始化MSS捕获器"""
        try:
            import mss
            import mss.tools
            
            self._capture_impl = mss.mss()
            
            # 获取屏幕尺寸
            monitor = self._capture_impl.monitors[1]  # 主显示器
            logger.info(f"MSS initialized. Screen size: {monitor['width']}x{monitor['height']}")
            
            return True
            
        except ImportError:
            logger.error("MSS library not installed. Install with: pip install mss")
            return False
    
    def _init_pil(self) -> bool:
        """初始化PIL捕获器"""
        try:
            from PIL import ImageGrab
            self._capture_impl = ImageGrab
            logger.info("PIL ImageGrab initialized")
            return True
            
        except ImportError:
            logger.error("PIL not installed")
            return False
    
    def _init_d3d(self) -> bool:
        """初始化Direct3D捕获器（Windows高性能）"""
        try:
            import d3dshot
            self._capture_impl = d3dshot.create(capture_output="numpy")
            logger.info("Direct3D capture initialized")
            return True
            
        except ImportError:
            logger.warning("d3dshot not installed, falling back to MSS")
            return self._init_mss()
        except Exception as e:
            logger.error(f"Failed to initialize D3D capture: {e}")
            return self._init_mss()
    
    def _init_opencv(self) -> bool:
        """初始化OpenCV捕获器"""
        # OpenCV不支持直接屏幕捕获，使用MSS作为后端
        logger.warning("OpenCV method not directly supported, using MSS backend")
        return self._init_mss()
    
    def capture_frame(self) -> Optional[np.ndarray]:
        """捕获单帧
        
        Returns:
            BGR格式的numpy数组，捕获失败返回None
        """
        try:
            start_time = time.time()
            
            if self.config.method == CaptureMethod.MSS:
                frame = self._capture_mss()
            elif self.config.method == CaptureMethod.PIL:
                frame = self._capture_pil()
            elif self.config.method == CaptureMethod.D3D:
                frame = self._capture_d3d()
            else:
                frame = self._capture_mss()
            
            if frame is None:
                return None
            
            # 应用缩放
            if self.config.scale != 1.0:
                new_width = int(frame.shape[1] * self.config.scale)
                new_height = int(frame.shape[0] * self.config.scale)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # 更新统计
            self.frame_count += 1
            capture_time = time.time() - start_time
            self._capture_times.append(capture_time)
            if len(self._capture_times) > 100:
                self._capture_times.pop(0)
            
            self.last_frame = frame
            
            # 触发回调
            if self.on_frame_captured:
                metadata = {
                    'frame_number': self.frame_count,
                    'capture_time': capture_time,
                    'timestamp': time.time(),
                    'resolution': f"{frame.shape[1]}x{frame.shape[0]}"
                }
                self.on_frame_captured(frame, metadata)
            
            return frame
            
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            if self.on_error:
                self.on_error(e)
            return None
    
    def _capture_mss(self) -> Optional[np.ndarray]:
        """使用MSS捕获屏幕"""
        try:
            if self.config.region:
                left, top, width, height = self.config.region
                monitor = {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height
                }
            else:
                monitor = self._capture_impl.monitors[1]  # 主显示器
            
            # 捕获屏幕
            screenshot = self._capture_impl.grab(monitor)
            
            # 转换为numpy数组 (BGR格式)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            
            return frame
            
        except Exception as e:
            logger.error(f"MSS capture error: {e}")
            return None
    
    def _capture_pil(self) -> Optional[np.ndarray]:
        """使用PIL捕获屏幕"""
        try:
            if self.config.region:
                screenshot = self._capture_impl.grab(bbox=self.config.region)
            else:
                screenshot = self._capture_impl.grab()
            
            # 转换为numpy数组
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            return frame
            
        except Exception as e:
            logger.error(f"PIL capture error: {e}")
            return None
    
    def _capture_d3d(self) -> Optional[np.ndarray]:
        """使用Direct3D捕获屏幕"""
        try:
            frame = self._capture_impl.screenshot()
            if frame is not None:
                # D3DShot默认返回RGB格式
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame
            
        except Exception as e:
            logger.error(f"D3D capture error: {e}")
            return None
    
    async def capture_frame_async(self) -> Optional[np.ndarray]:
        """异步捕获单帧"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.capture_frame)
    
    def start_capture(self, callback: Callable[[np.ndarray, Dict], None] = None):
        """开始连续捕获"""
        if self.is_capturing:
            logger.warning("Capture already running")
            return
        
        if not self.initialize():
            logger.error("Failed to initialize capture")
            return
        
        if callback:
            self.on_frame_captured = callback
        
        self.is_capturing = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        
        logger.info(f"Screen capture started at {self.config.fps} FPS")
    
    def _capture_loop(self):
        """捕获循环"""
        frame_interval = 1.0 / self.config.fps
        
        while self.is_capturing:
            loop_start = time.time()
            
            frame = self.capture_frame()
            if frame is None:
                continue
            
            # 控制帧率
            elapsed = time.time() - loop_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    def stop_capture(self):
        """停止捕获"""
        self.is_capturing = False
        
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
            self.capture_thread = None
        
        # 释放资源
        if self._capture_impl:
            if hasattr(self._capture_impl, 'close'):
                self._capture_impl.close()
            self._capture_impl = None
        
        logger.info("Screen capture stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取捕获统计信息"""
        avg_time = sum(self._capture_times) / len(self._capture_times) if self._capture_times else 0
        
        return {
            'frames_captured': self.frame_count,
            'is_capturing': self.is_capturing,
            'average_capture_time': avg_time,
            'effective_fps': 1.0 / avg_time if avg_time > 0 else 0,
            'method': self.config.method.value
        }
    
    def set_region(self, left: int, top: int, width: int, height: int):
        """设置捕获区域"""
        self.config.region = (left, top, width, height)
        logger.info(f"Capture region set to: {left}, {top}, {width}, {height}")
    
    def set_fps(self, fps: int):
        """设置帧率"""
        self.config.fps = fps
        logger.info(f"Capture FPS set to: {fps}")
    
    def __del__(self):
        """析构函数"""
        self.stop_capture()


class WindowCapture:
    """特定窗口捕获器"""
    
    def __init__(self, window_title: str = None, window_handle: int = None):
        self.window_title = window_title
        self.window_handle = window_handle
        self.is_capturing = False
    
    def find_window(self, title: str) -> bool:
        """根据标题查找窗口"""
        try:
            import win32gui
            
            def callback(hwnd, extra):
                if win32gui.IsWindowVisible(hwnd):
                    text = win32gui.GetWindowText(hwnd)
                    if title.lower() in text.lower():
                        extra.append(hwnd)
                return True
            
            windows = []
            win32gui.EnumWindows(callback, windows)
            
            if windows:
                self.window_handle = windows[0]
                self.window_title = win32gui.GetWindowText(self.window_handle)
                logger.info(f"Found window: {self.window_title} (handle: {self.window_handle})")
                return True
            
            return False
            
        except ImportError:
            logger.error("win32gui not available")
            return False
    
    def capture_window(self) -> Optional[np.ndarray]:
        """捕获特定窗口"""
        try:
            import win32gui
            import win32ui
            import win32con
            from PIL import Image
            
            if not self.window_handle:
                if self.window_title and not self.find_window(self.window_title):
                    return None
                else:
                    return None
            
            # 获取窗口DC
            hwndDC = win32gui.GetWindowDC(self.window_handle)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # 获取窗口尺寸
            left, top, right, bottom = win32gui.GetWindowRect(self.window_handle)
            width = right - left
            height = bottom - top
            
            # 创建位图
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # 复制屏幕内容
            saveDC.BitBlt((0, 0), (width, height), mfcDC, (0, 0), win32con.SRCCOPY)
            
            # 转换为numpy数组
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            im = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1)
            
            # 清理资源
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(self.window_handle, hwndDC)
            
            # 转换为OpenCV格式
            frame = np.array(im)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            
            return frame
            
        except Exception as e:
            logger.error(f"Window capture error: {e}")
            return None


# 便捷的工厂函数
def create_capture(method: str = 'mss', **kwargs) -> ScreenCapture:
    """创建屏幕捕获器
    
    Args:
        method: 捕获方法 ('mss', 'pil', 'd3d', 'opencv')
        **kwargs: 其他配置参数
        
    Returns:
        ScreenCapture实例
    """
    method_map = {
        'mss': CaptureMethod.MSS,
        'pil': CaptureMethod.PIL,
        'd3d': CaptureMethod.D3D,
        'd3dshot': CaptureMethod.D3D,
        'opencv': CaptureMethod.OPENCV
    }
    
    capture_method = method_map.get(method.lower(), CaptureMethod.MSS)
    config = CaptureConfig(method=capture_method, **kwargs)
    
    return ScreenCapture(config)
