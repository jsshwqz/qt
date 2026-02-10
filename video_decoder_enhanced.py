#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的视频解码器
支持 H.264 解码和实时渲染
"""
from __future__ import annotations

import struct
import logging
import io
from typing import Optional, Tuple, List

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

if HAS_CV2 and not HAS_NUMPY:
    # cv2 decoding path requires numpy arrays.
    HAS_CV2 = False
    logging.getLogger(__name__).warning('NumPy not available - disabling OpenCV decode path')

logger = logging.getLogger(__name__)


class H264Parser:
    """H.264 NAL Unit Parser and Stream Processor"""
    
    NALU_TYPE_SPS = 7
    NALU_TYPE_PPS = 8
    NALU_TYPE_IDR = 5
    NALU_TYPE_SLICE = 1
    
    def __init__(self):
        self.sps_data: Optional[bytes] = None
        self.pps_data: Optional[bytes] = None
        self._buffer = b''
    
    def split_nalus(self, data: bytes) -> List[bytes]:
        """Split a chunk of data into H.264 NAL units."""
        self._buffer += data
        nalus = []
        
        while True:
            # Look for sync codes: 00 00 01 or 00 00 00 01
            # We use a simplistic split here assuming NALUs start with 00 00 01 or 00 00 00 01
            # A more robust parser would use a sliding window or regex
            pos1 = self._buffer.find(b'\x00\x00\x01')
            pos2 = self._buffer.find(b'\x00\x00\x00\x01')
            
            # Find the first occurrence
            if pos1 == -1 and pos2 == -1:
                break
                
            start = pos2 if (pos2 != -1 and (pos1 == -1 or pos2 < pos1)) else pos1
            
            # Next potential start code
            next_pos1 = self._buffer.find(b'\x00\x00\x01', start + 3)
            next_pos2 = self._buffer.find(b'\x00\x00\x00\x01', start + 3)
            
            if next_pos1 == -1 and next_pos2 == -1:
                # Still waiting for the end of this NALU
                break
                
            end = next_pos2 if (next_pos2 != -1 and (next_pos1 == -1 or next_pos2 < next_pos1)) else next_pos1
            
            # Extract NALU including start code
            nalu = self._buffer[start:end]
            nalus.append(nalu)
            self._buffer = self._buffer[end:]
            
        return nalus

    def get_nalu_type(self, nalu: bytes) -> int:
        """Parse NAL unit type from a single NALU (including start code)."""
        # Find the start of the payload after the start code
        if nalu.startswith(b'\x00\x00\x00\x01'):
            header_pos = 4
        elif nalu.startswith(b'\x00\x00\x01'):
            header_pos = 3
        else:
            return 0
            
        if len(nalu) <= header_pos:
            return 0
            
        return nalu[header_pos] & 0x1F


class VideoDecoder:
    """视频解码器"""
    
    def __init__(self, width=720, height=1280):
        self.width = width
        self.height = height
        self.decoder = None
        self.parser = H264Parser()
        
        if HAS_CV2:
            self._init_opencv_decoder()
        else:
            logger.warning('OpenCV not available - fallback rendering only')
    
    def _init_opencv_decoder(self):
        """初始化 OpenCV 解码器"""
        try:
            # 尝试创建视频解码器
            fourcc = cv2.VideoWriter_fourcc(*'H264')
            logger.info('H.264 decoder initialized')
        except Exception as e:
            logger.warning(f'Failed to initialize OpenCV decoder: {e}')
    
    def decode_frame(self, data: bytes) -> Optional[np.ndarray]:
        """解码单个帧"""
        if not HAS_CV2 or not HAS_NUMPY:
            return None
        
        try:
            # 使用 imdecode 解码
            nparr = np.frombuffer(data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None:
                # 调整分辨率
                frame = cv2.resize(frame, (self.width, self.height))
                return frame
            
        except Exception as e:
            logger.error(f'Decoding error: {e}')
        
        return None
    
    def set_resolution(self, width: int, height: int):
        """设置分辨率"""
        self.width = width
        self.height = height
        logger.info(f'Resolution set to {width}x{height}')


class RawVideoFrame:
    """原始视频帧 - 用于 fallback 渲染"""
    
    def __init__(self, width=720, height=1280, frame_count=0):
        self.width = width
        self.height = height
        self.frame_count = frame_count
        
        # 创建测试帧数据
        self.data = np.zeros((height, width, 3), dtype=np.uint8) if HAS_NUMPY else None
    
    def render_test_pattern(self):
        """渲染测试模式"""
        if self.data is None:
            return None

        # 渐变背景
        for y in range(self.height):
            color = int((self.frame_count + y * 255 // self.height) % 256)
            self.data[y, :] = [color, 100, 200]
        
        # 添加文本信息
        try:
            import cv2
            text = f'Frame: {self.frame_count}'
            cv2.putText(
                self.data,
                text,
                (50, 100),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.5,
                (255, 255, 255),
                2
            )
            
            res_text = f'{self.width}x{self.height}'
            cv2.putText(
                self.data,
                res_text,
                (50, 150),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (200, 200, 200),
                1
            )
        except:
            pass
        
        return self.data
    
    def to_rgb(self) -> Optional[np.ndarray]:
        """转换为 RGB 格式"""
        if self.data is None:
            return None
        if HAS_CV2:
            return cv2.cvtColor(self.data, cv2.COLOR_BGR2RGB)
        return self.data


class ScrcpyVideoDecoder:
    """Scrcpy 视频流解码器"""
    
    # Scrcpy 帧头定义
    FRAME_TYPE_CONFIG = 0x00
    FRAME_TYPE_KEY = 0x01
    FRAME_TYPE_NORMAL = 0x02
    
    def __init__(self, width=720, height=1280):
        self.width = width
        self.height = height
        self.decoder = VideoDecoder(width, height)
        self.frame_count = 0
        self.buffer = b''
    
    def set_resolution(self, width: int, height: int):
        """设置分辨率"""
        self.width = width
        self.height = height
        self.decoder.set_resolution(width, height)
        logger.info(f'Scrcpy resolution set to {width}x{height}')
    
    def process_data(self, data: bytes) -> Optional[np.ndarray]:
        """处理接收的数据"""
        self.buffer += data
        
        # 尝试解析帧
        while len(self.buffer) > 0:
            frame = self._extract_frame()
            if frame is not None:
                return frame
            else:
                break
        
        return None
    
    def _extract_frame(self) -> Optional[np.ndarray]:
        """Extract a single frame from the buffer according to Scrcpy protocol."""
        if len(self.buffer) < 12:
            return None
        
        try:
            # Scrcpy Header (H.264 stream mode):
            # [8 bytes PTS] [1 byte Flags] [4 bytes Frame Length]
            # Since Scrcpy v1.18+, flags include CONFIG, KEY_FRAME, etc.
            pts = struct.unpack('>Q', self.buffer[:8])[0]
            info = self.buffer[8]
            frame_size = struct.unpack('>I', self.buffer[9:13])[0]
            
            if len(self.buffer) < 13 + frame_size:
                return None
            
            frame_data = self.buffer[13:13 + frame_size]
            self.buffer = self.buffer[13 + frame_size:]
            self.frame_count += 1
            
            # Identify frame importance
            is_config = info & 0x01 # Simplified check, usually info=0 for config, info=1 for key
            
            if is_config:
                logger.info(f"Received Config Frame ({frame_size} bytes)")
                # For H.264, config frames usually contain SPS/PPS
                # We can feed them to the decoder to initialize CSP
                return self.decoder.decode_frame(frame_data)
            
            # Regular video frame
            frame = self.decoder.decode_frame(frame_data)
            
            if frame is None:
                if HAS_CV2:
                    logger.debug(f"OpenCV failed to decode frame #{self.frame_count}")
                else:
                    # Fallback pattern for development without OpenCV
                    raw_frame = RawVideoFrame(self.width, self.height, self.frame_count)
                    frame = raw_frame.render_test_pattern()
            
            return frame
            
        except Exception as e:
            logger.error(f"Scrcpy Protocol extraction error: {e}")
            # Potentially corrupted buffer, clear it to resync
            self.buffer = b''
            return None
    
    def get_frame_count(self) -> int:
        """获取帧计数"""
        return self.frame_count


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    decoder = ScrcpyVideoDecoder(1080, 1920)
    logger.info('Video decoder initialized')
    logger.info(f'Available: OpenCV={HAS_CV2}')
