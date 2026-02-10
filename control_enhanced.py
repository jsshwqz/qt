#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
触摸控制和坐标转换模块
处理设备屏幕与窗口坐标的映射
"""

import struct
import logging
import socket
from typing import Tuple, Optional

logger = logging.getLogger(__name__)


class CoordinateTransformer:
    """坐标转换器"""
    
    def __init__(self, device_width: int, device_height: int,
                 window_width: int, window_height: int):
        """
        初始化坐标转换器
        
        Args:
            device_width: 设备屏幕宽度
            device_height: 设备屏幕高度
            window_width: 窗口显示宽度
            window_height: 窗口显示高度
        """
        self.device_width = device_width
        self.device_height = device_height
        self.window_width = window_width
        self.window_height = window_height
        
        # 计算缩放因子
        self.scale_x = device_width / window_width if window_width > 0 else 1
        self.scale_y = device_height / window_height if window_height > 0 else 1
        
        logger.info(f'Coordinate transformer initialized: '
                   f'Device={device_width}x{device_height}, '
                   f'Window={window_width}x{window_height}, '
                   f'Scale=({self.scale_x:.2f}, {self.scale_y:.2f})')
    
    def window_to_device(self, window_x: int, window_y: int) -> Tuple[int, int]:
        """
        将窗口坐标转换为设备坐标
        
        Args:
            window_x: 窗口X坐标
            window_y: 窗口Y坐标
        
        Returns:
            (device_x, device_y)
        """
        device_x = int(window_x * self.scale_x)
        device_y = int(window_y * self.scale_y)
        
        # 限制在有效范围内
        device_x = max(0, min(device_x, self.device_width - 1))
        device_y = max(0, min(device_y, self.device_height - 1))
        
        return device_x, device_y
    
    def device_to_window(self, device_x: int, device_y: int) -> Tuple[int, int]:
        """
        将设备坐标转换为窗口坐标
        
        Args:
            device_x: 设备X坐标
            device_y: 设备Y坐标
        
        Returns:
            (window_x, window_y)
        """
        window_x = int(device_x / self.scale_x)
        window_y = int(device_y / self.scale_y)
        
        return window_x, window_y
    
    def set_window_size(self, width: int, height: int):
        """更新窗口大小并重新计算缩放因子"""
        self.window_width = width
        self.window_height = height
        
        self.scale_x = self.device_width / width if width > 0 else 1
        self.scale_y = self.device_height / height if height > 0 else 1
        
        logger.info(f'Window size updated to {width}x{height}, '
                   f'Scale=({self.scale_x:.2f}, {self.scale_y:.2f})')


class TouchEvent:
    """触摸事件"""
    
    # 事件类型
    ACTION_DOWN = 0
    ACTION_MOVE = 1
    ACTION_UP = 2
    
    def __init__(self, action: int, x: int, y: int, pressure: int = 1):
        """
        创建触摸事件
        
        Args:
            action: 动作类型 (DOWN/MOVE/UP)
            x: X坐标
            y: Y坐标
            pressure: 压力值 (0-255)
        """
        self.action = action
        self.x = x
        self.y = y
        self.pressure = max(0, min(pressure, 255))
    
    def to_bytes(self) -> bytes:
        """转换为字节"""
        return struct.pack('>BHHBx', self.action, self.x, self.y, self.pressure)
    
    @staticmethod
    def from_bytes(data: bytes) -> Optional['TouchEvent']:
        """从字节解析"""
        try:
            if len(data) < 7:
                return None
            action, x, y, pressure = struct.unpack('>BHHBx', data[:7])
            return TouchEvent(action, x, y, pressure)
        except struct.error:
            return None
    
    def __repr__(self):
        action_name = {
            self.ACTION_DOWN: 'DOWN',
            self.ACTION_MOVE: 'MOVE',
            self.ACTION_UP: 'UP'
        }.get(self.action, 'UNKNOWN')
        return f'TouchEvent({action_name}, {self.x}, {self.y}, pressure={self.pressure})'


class KeyEvent:
    """按键事件"""
    
    # Android key codes (常用)
    KEYCODE_HOME = 3
    KEYCODE_BACK = 4
    KEYCODE_CALL = 5
    KEYCODE_ENDCALL = 6
    KEYCODE_0 = 7
    KEYCODE_1 = 8
    KEYCODE_POWER = 26
    KEYCODE_VOLUME_UP = 24
    KEYCODE_VOLUME_DOWN = 25
    KEYCODE_MENU = 82
    KEYCODE_SEARCH = 84
    KEYCODE_ENTER = 66
    KEYCODE_DEL = 67
    KEYCODE_SPACE = 62
    
    # 事件类型
    ACTION_DOWN = 0
    ACTION_UP = 1
    
    def __init__(self, keycode: int, action: int = ACTION_DOWN):
        """
        创建按键事件
        
        Args:
            keycode: Android key code
            action: 动作 (DOWN/UP)
        """
        self.keycode = keycode
        self.action = action
    
    def to_bytes(self) -> bytes:
        """转换为字节"""
        return struct.pack('>BIB', self.action, self.keycode, 0)
    
    def __repr__(self):
        action_name = 'DOWN' if self.action == self.ACTION_DOWN else 'UP'
        return f'KeyEvent({self.keycode}, {action_name})'


class MotionEvent:
    """运动事件（手势）"""
    
    # 手势类型
    GESTURE_TAP = 0
    GESTURE_LONG_PRESS = 1
    GESTURE_DRAG = 2
    GESTURE_PINCH = 3
    
    def __init__(self, gesture_type: int, x: int, y: int, duration_ms: int = 100):
        """
        创建运动事件
        
        Args:
            gesture_type: 手势类型
            x: X坐标
            y: Y坐标
            duration_ms: 持续时间（毫秒）
        """
        self.gesture_type = gesture_type
        self.x = x
        self.y = y
        self.duration_ms = duration_ms
    
    def to_bytes(self) -> bytes:
        """转换为字节"""
        return struct.pack('>BHHi', self.gesture_type, self.x, self.y, self.duration_ms)
    
    def __repr__(self):
        gesture_name = {
            self.GESTURE_TAP: 'TAP',
            self.GESTURE_LONG_PRESS: 'LONG_PRESS',
            self.GESTURE_DRAG: 'DRAG',
            self.GESTURE_PINCH: 'PINCH'
        }.get(self.gesture_type, 'UNKNOWN')
        return f'MotionEvent({gesture_name}, {self.x}, {self.y}, {self.duration_ms}ms)'


class ControlSocket:
    """控制 Socket - 用于发送控制命令"""
    
    def __init__(self, host: str = '127.0.0.1', port: int = 27184):
        """
        初始化控制 Socket
        
        Args:
            host: 目标主机
            port: 目标端口
        """
        self.host = host
        self.port = port
        self.socket: Optional[socket.socket] = None
        self.connected = False
    
    def connect(self) -> bool:
        """连接到设备"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5.0)
            self.socket.connect((self.host, self.port))
            self.connected = True
            logger.info(f'Control socket connected to {self.host}:{self.port}')
            return True
        except Exception as e:
            logger.error(f'Failed to connect control socket: {e}')
            self.connected = False
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                logger.error(f'Error closing socket: {e}')
            self.connected = False
            logger.info('Control socket disconnected')
    
    def send_touch_event(self, event: TouchEvent) -> bool:
        """发送触摸事件"""
        if not self.connected or not self.socket:
            return False
        
        try:
            self.socket.sendall(event.to_bytes())
            return True
        except Exception as e:
            logger.error(f'Failed to send touch event: {e}')
            return False
    
    def send_key_event(self, event: KeyEvent) -> bool:
        """发送按键事件"""
        if not self.connected or not self.socket:
            return False
        
        try:
            self.socket.sendall(event.to_bytes())
            return True
        except Exception as e:
            logger.error(f'Failed to send key event: {e}')
            return False
    
    def send_motion_event(self, event: MotionEvent) -> bool:
        """发送运动事件"""
        if not self.connected or not self.socket:
            return False
        
        try:
            self.socket.sendall(event.to_bytes())
            return True
        except Exception as e:
            logger.error(f'Failed to send motion event: {e}')
            return False
    
    def send_tap(self, x: int, y: int) -> bool:
        """发送点击事件"""
        # 按下
        if not self.send_touch_event(TouchEvent(TouchEvent.ACTION_DOWN, x, y)):
            return False
        
        # 抬起
        return self.send_touch_event(TouchEvent(TouchEvent.ACTION_UP, x, y))
    
    def send_swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 500) -> bool:
        """发送滑动事件"""
        # 按下
        if not self.send_touch_event(TouchEvent(TouchEvent.ACTION_DOWN, x1, y1)):
            return False
        
        # 移动（可以分多步）
        steps = max(5, duration_ms // 50)
        for i in range(1, steps):
            x = int(x1 + (x2 - x1) * i / steps)
            y = int(y1 + (y2 - y1) * i / steps)
            if not self.send_touch_event(TouchEvent(TouchEvent.ACTION_MOVE, x, y)):
                return False
            # 模拟延迟
            import time
            time.sleep(duration_ms / (steps * 1000))
        
        # 抬起
        return self.send_touch_event(TouchEvent(TouchEvent.ACTION_UP, x2, y2))


if __name__ == '__main__':
    # 测试代码
    logging.basicConfig(level=logging.DEBUG)
    
    # 测试坐标转换
    transformer = CoordinateTransformer(1080, 1920, 540, 960)
    
    # 窗口坐标 (270, 480) -> 设备坐标 (540, 960)
    device_x, device_y = transformer.window_to_device(270, 480)
    print(f"Window (270, 480) -> Device ({device_x}, {device_y})")
    
    # 测试触摸事件
    event = TouchEvent(TouchEvent.ACTION_DOWN, 540, 960)
    print(f"Touch event: {event}")
    print(f"Bytes: {event.to_bytes().hex()}")
    
    # 测试按键事件
    key_event = KeyEvent(KeyEvent.KEYCODE_HOME)
    print(f"Key event: {key_event}")
