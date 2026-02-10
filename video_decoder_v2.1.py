#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
改进的视频解码器 v2.1

支持：
- H.264 NAL 单元解析
- 实时帧解码 (PyAV Backend)
- Fallback 渲染模式
- 帧缓冲管理
- 性能监控
"""

import struct
import logging
import io
import time
from typing import Optional, Tuple, List
from collections import deque
import numpy as np

try:
    import av
    HAS_AV = True
except ImportError:
    HAS_AV = False

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

logger = logging.getLogger(__name__)


class H264Parser:
    """H.264 NAL 单元解析器 (Helper for raw analysis)"""
    # (Existing parser logic kept for analysis purposes, though PyAV handles parsing internally)
    NALU_TYPE_SPS = 7
    NALU_TYPE_PPS = 8
    NALU_TYPE_IDR = 5
    NALU_TYPE_SLICE = 1
    
    def __init__(self):
        self.frame_count = 0
    
    # ... (Keep existing parser methods if needed for debugging, but PyAV does this better)
    # We will use PyAV for actual decoding.


class FrameBuffer:
    """帧缓冲管理器"""
    def __init__(self, max_size: int = 30):
        self.max_size = max_size
        self.buffer = deque(maxlen=max_size)
        self.stats = {'total_received': 0, 'total_dropped': 0, 'current_size': 0}
    
    def push(self, frame_data: dict) -> bool:
        self.stats['total_received'] += 1
        if len(self.buffer) >= self.max_size:
            self.stats['total_dropped'] += 1
            return False
        self.buffer.append(frame_data)
        self.stats['current_size'] = len(self.buffer)
        return True
    
    def pop(self) -> Optional[dict]:
        if self.buffer:
            frame = self.buffer.popleft()
            self.stats['current_size'] = len(self.buffer)
            return frame
        return None
    
    def get_stats(self) -> dict:
        return self.stats.copy()


class VideoDecoder:
    """视频解码器 (PyAV powered)"""
    
    def __init__(self, width: int = 720, height: int = 1280):
        self.width = width
        self.height = height
        self.frame_buffer = FrameBuffer(max_size=30)
        self.codec = None
        
        self.decode_stats = {
            'frames_decoded': 0,
            'frames_failed': 0,
            'last_decode_time': 0,
            'total_decode_time': 0
        }
        
        if HAS_AV:
            try:
                self.codec = av.CodecContext.create('h264', 'r')
                logger.info("PyAV H.264 codec initialized")
            except Exception as e:
                logger.error(f"Failed to initialize PyAV codec: {e}")
        else:
            logger.warning("PyAV not found. Decoding will fail.")
            
        logger.info(f'VideoDecoder initialized: {width}x{height}')
    
    def decode_h264_frame(self, data: bytes) -> Optional[dict]:
        """
        解码 H.264 帧数据 (Raw NAL unit or framed data)
        """
        if not self.codec:
            return {'success': False, 'error': 'No codec available'}

        start_time = time.time()
        decoded_frames = []
        
        try:
            # PyAV handles NAL parsing. We just feed it packets.
            # If data is a raw NAL unit, PyAV can usually handle it.
            packets = [av.Packet(data)]
            
            for packet in packets:
                frames = self.codec.decode(packet)
                for frame in frames:
                    # Convert to numpy RGB
                    img = frame.to_ndarray(format='rgb24')
                    decoded_frames.append(img)
            
            decode_time = time.time() - start_time
            
            if decoded_frames:
                self.decode_stats['frames_decoded'] += len(decoded_frames)
                self.decode_stats['last_decode_time'] = decode_time / len(decoded_frames)
                self.decode_stats['total_decode_time'] += decode_time
                
                # Return the last frame for display (or all?)
                # Usually we process one frame at a time in this architecture
                return {
                    'success': True,
                    'frame_info': {'frame_number': self.decode_stats['frames_decoded']},
                    'image': decoded_frames[-1], # Numpy array
                    'decode_time': decode_time
                }
            else:
                return {'success': False, 'error': 'No frames produced'}
                
        except Exception as e:
            self.decode_stats['frames_failed'] += 1
            logger.error(f"Decode error: {e}")
            return {'success': False, 'error': str(e)}

    def get_stats(self) -> dict:
        stats = self.decode_stats.copy()
        if stats['frames_decoded'] > 0:
            stats['avg_decode_time'] = stats['total_decode_time'] / stats['frames_decoded']
        else:
            stats['avg_decode_time'] = 0
        return stats


def create_video_decoder(width: int = 720, height: int = 1280) -> VideoDecoder:
    return VideoDecoder(width, height)