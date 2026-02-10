"""
屏幕控制和交互模块
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable, List, Tuple
from dataclasses import dataclass
from enum import Enum
import json

logger = logging.getLogger(__name__)

class ControlAction(Enum):
    """控制动作类型"""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    LONG_PRESS = "long_press"
    SWIPE = "swipe"
    SCROLL = "scroll"
    PINCH = "pinch"
    ROTATE = "rotate"
    KEY = "key"
    TEXT = "text"
    GESTURE = "gesture"
    HOME = "home"
    BACK = "back"
    MENU = "menu"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    POWER = "power"
    SCREENSHOT = "screenshot"
    RECORD = "record"

@dataclass
class TouchEvent:
    """触摸事件"""
    x: float
    y: float
    pressure: float = 1.0
    timestamp: float = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()

@dataclass
class KeyEvent:
    """按键事件"""
    key_code: int
    meta_state: int = 0
    repeat_count: int = 0
    timestamp: float = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()

@dataclass
class GestureEvent:
    """手势事件"""
    points: List[Tuple[float, float]]
    action: ControlAction
    duration: int = 300
    timestamp: float = 0
    
    def __post_init__(self):
        if self.timestamp == 0:
            self.timestamp = time.time()

class ControlManager:
    """控制管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.is_enabled = config.get("enabled", True)
        self.enable_touch = config.get("enable_touch", True)
        self.enable_keyboard = config.get("enable_keyboard", True)
        self.enable_mouse = config.get("enable_mouse", True)
        self.enable_gestures = config.get("enable_gestures", True)
        self.enable_clipboard = config.get("enable_clipboard", False)
        
        # 延迟和坐标映射
        self.latency_threshold = config.get("latency_threshold", 100)  # ms
        self.coordinate_mapping = config.get("coordinate_mapping", {
            "screen_width": 1920,
            "screen_height": 1080,
            "touch_width": 1920,
            "touch_height": 1080
        })
        
        # 手势识别
        self.gesture_detector = GestureDetector(config.get("gesture_config", {}))
        
        # 回调函数
        self.control_callbacks: List[Callable] = []
        
        # 统计信息
        self.stats = {
            "total_controls": 0,
            "touch_events": 0,
            "key_events": 0,
            "gesture_events": 0,
            "errors": 0,
            "last_activity": 0
        }
    
    def register_callback(self, callback: Callable):
        """注册控制回调"""
        self.control_callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable):
        """注销控制回调"""
        if callback in self.control_callbacks:
            self.control_callbacks.remove(callback)
    
    async def handle_touch(self, event: TouchEvent) -> bool:
        """处理触摸事件"""
        if not self.is_enabled or not self.enable_touch:
            return False
        
        try:
            # 坐标映射
            mapped_x, mapped_y = self._map_coordinates(event.x, event.y)
            
            control_data = {
                "type": "touch",
                "action": ControlAction.CLICK.value,
                "x": mapped_x,
                "y": mapped_y,
                "pressure": event.pressure,
                "timestamp": event.timestamp
            }
            
            return await self._execute_control(control_data)
            
        except Exception as e:
            logger.error(f"Error handling touch: {e}")
            self.stats["errors"] += 1
            return False
    
    async def handle_click(self, x: float, y: float, button: int = 0) -> bool:
        """处理点击事件"""
        if not self.is_enabled or not self.enable_mouse:
            return False
        
        control_data = {
            "type": "mouse",
            "action": ControlAction.CLICK.value,
            "x": x,
            "y": y,
            "button": button,
            "timestamp": time.time()
        }
        
        return await self._execute_control(control_data)
    
    async def handle_double_click(self, x: float, y: float) -> bool:
        """处理双击事件"""
        if not self.is_enabled or not self.enable_mouse:
            return False
        
        control_data = {
            "type": "mouse",
            "action": ControlAction.DOUBLE_CLICK.value,
            "x": x,
            "y": y,
            "timestamp": time.time()
        }
        
        return await self._execute_control(control_data)
    
    async def handle_long_press(self, x: float, y: float, duration: int = 1000) -> bool:
        """处理长按事件"""
        if not self.is_enabled or not self.enable_touch:
            return False
        
        control_data = {
            "type": "touch",
            "action": ControlAction.LONG_PRESS.value,
            "x": x,
            "y": y,
            "duration": duration,
            "timestamp": time.time()
        }
        
        return await self._execute_control(control_data)
    
    async def handle_swipe(self, x1: float, y1: float, x2: float, y2: float, 
                          duration: int = 300) -> bool:
        """处理滑动事件"""
        if not self.is_enabled or not self.enable_touch:
            return False
        
        # 映射坐标
        mx1, my1 = self._map_coordinates(x1, y1)
        mx2, my2 = self._map_coordinates(x2, y2)
        
        control_data = {
            "type": "gesture",
            "action": ControlAction.SWIPE.value,
            "x1": mx1,
            "y1": my1,
            "x2": mx2,
            "y2": my2,
            "duration": duration,
            "timestamp": time.time()
        }
        
        return await self._execute_control(control_data)
    
    async def handle_scroll(self, x: float, y: float, delta_x: float, delta_y: float) -> bool:
        """处理滚动事件"""
        if not self.is_enabled or not self.enable_mouse:
            return False
        
        control_data = {
            "type": "mouse",
            "action": ControlAction.SCROLL.value,
            "x": x,
            "y": y,
            "delta_x": delta_x,
            "delta_y": delta_y,
            "timestamp": time.time()
        }
        
        return await self._execute_control(control_data)
    
    async def handle_key(self, key_code: int, meta_state: int = 0, 
                        repeat_count: int = 0) -> bool:
        """处理按键事件"""
        if not self.is_enabled or not self.enable_keyboard:
            return False
        
        key_event = KeyEvent(key_code, meta_state, repeat_count)
        
        control_data = {
            "type": "keyboard",
            "action": ControlAction.KEY.value,
            "key_code": key_code,
            "meta_state": meta_state,
            "repeat_count": repeat_count,
            "timestamp": key_event.timestamp
        }
        
        return await self._execute_control(control_data)
    
    async def handle_text(self, text: str) -> bool:
        """处理文本输入"""
        if not self.is_enabled or not self.enable_keyboard:
            return False
        
        control_data = {
            "type": "keyboard",
            "action": ControlAction.TEXT.value,
            "text": text,
            "timestamp": time.time()
        }
        
        return await self._execute_control(control_data)
    
    async def handle_gesture(self, gesture: GestureEvent) -> bool:
        """处理手势事件"""
        if not self.is_enabled or not self.enable_gestures:
            return False
        
        # 映射手势点坐标
        mapped_points = [self._map_coordinates(x, y) for x, y in gesture.points]
        
        control_data = {
            "type": "gesture",
            "action": gesture.action.value,
            "points": mapped_points,
            "duration": gesture.duration,
            "timestamp": gesture.timestamp
        }
        
        return await self._execute_control(control_data)
    
    async def handle_system_action(self, action: ControlAction) -> bool:
        """处理系统动作"""
        control_data = {
            "type": "system",
            "action": action.value,
            "timestamp": time.time()
        }
        
        return await self._execute_control(control_data)
    
    async def _execute_control(self, control_data: Dict[str, Any]) -> bool:
        """执行控制指令"""
        try:
            # 更新统计
            self.stats["total_controls"] += 1
            self.stats["last_activity"] = time.time()
            
            if control_data["type"] == "touch":
                self.stats["touch_events"] += 1
            elif control_data["type"] == "keyboard":
                self.stats["key_events"] += 1
            elif control_data["type"] == "gesture":
                self.stats["gesture_events"] += 1
            
            # 调用所有回调函数
            for callback in self.control_callbacks:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(control_data)
                    else:
                        callback(control_data)
                except Exception as e:
                    logger.error(f"Error in control callback: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error executing control: {e}")
            self.stats["errors"] += 1
            return False
    
    def _map_coordinates(self, x: float, y: float) -> Tuple[float, float]:
        """坐标映射"""
        mapping = self.coordinate_mapping
        
        # 计算缩放比例
        scale_x = mapping["touch_width"] / mapping["screen_width"]
        scale_y = mapping["touch_height"] / mapping["screen_height"]
        
        # 应用映射
        mapped_x = x * scale_x
        mapped_y = y * scale_y
        
        return mapped_x, mapped_y
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def reset_stats(self):
        """重置统计信息"""
        self.stats.update({
            "total_controls": 0,
            "touch_events": 0,
            "key_events": 0,
            "gesture_events": 0,
            "errors": 0
        })

class GestureDetector:
    """手势识别器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.threshold = config.get("threshold", 50)  # 移动阈值
        self.time_threshold = config.get("time_threshold", 500)  # 时间阈值(ms)
        self.points: List[Tuple[float, float]] = []
        self.start_time = 0
        
        # 手势模式
        self.gesture_modes = config.get("modes", {
            "single_finger": True,
            "multi_finger": True,
            "pinch_zoom": True,
            "rotation": True
        })
    
    def start_gesture(self, x: float, y: float):
        """开始手势识别"""
        self.points = [(x, y)]
        self.start_time = time.time()
    
    def add_point(self, x: float, y: float):
        """添加触摸点"""
        self.points.append((x, y))
    
    def end_gesture(self) -> Optional[GestureEvent]:
        """结束手势识别并返回手势事件"""
        if len(self.points) < 2:
            return None
        
        duration = int((time.time() - self.start_time) * 1000)
        
        # 分析手势类型
        gesture_type = self._analyze_gesture()
        
        if gesture_type:
            return GestureEvent(
                points=self.points,
                action=gesture_type,
                duration=duration
            )
        
        return None
    
    def _analyze_gesture(self) -> Optional[ControlAction]:
        """分析手势类型"""
        if len(self.points) < 2:
            return None
        
        # 计算总位移
        start_x, start_y = self.points[0]
        end_x, end_y = self.points[-1]
        delta_x = end_x - start_x
        delta_y = end_y - start_y
        distance = (delta_x ** 2 + delta_y ** 2) ** 0.5
        
        # 判断手势类型
        if distance < self.threshold:
            return ControlAction.CLICK
        elif distance > self.threshold and duration < self.time_threshold:
            return ControlAction.SWIPE
        elif len(self.points) > 2:
            return ControlAction.GESTURE
        
        return None
    
    def is_pinch(self, points1: List[Tuple[float, float]], 
                 points2: List[Tuple[float, float]]) -> bool:
        """检测捏合手势"""
        if len(points1) < 2 or len(points2) < 2:
            return False
        
        # 计算初始距离和最终距离
        init_dist = ((points1[0][0] - points1[1][0]) ** 2 + 
                    (points1[0][1] - points1[1][1]) ** 2) ** 0.5
        final_dist = ((points2[0][0] - points2[1][0]) ** 2 + 
                    (points2[0][1] - points2[1][1]) ** 2) ** 0.5
        
        # 判断是放大还是缩小
        return abs(final_dist - init_dist) > self.threshold

# 便捷函数
def create_touch_event(x: float, y: float, pressure: float = 1.0) -> TouchEvent:
    """创建触摸事件"""
    return TouchEvent(x, y, pressure)

def create_key_event(key_code: int, meta_state: int = 0) -> KeyEvent:
    """创建按键事件"""
    return KeyEvent(key_code, meta_state)

def create_gesture_event(points: List[Tuple[float, float]], 
                        action: ControlAction, 
                        duration: int = 300) -> GestureEvent:
    """创建手势事件"""
    return GestureEvent(points, action, duration)

# 预定义的按键码
class KeyCode:
    """Android按键码常量"""
    KEYCODE_HOME = 3
    KEYCODE_BACK = 4
    KEYCODE_MENU = 82
    KEYCODE_VOLUME_UP = 24
    KEYCODE_VOLUME_DOWN = 25
    KEYCODE_POWER = 26
    KEYCODE_ENTER = 66
    KEYCODE_DEL = 67
    KEYCODE_SPACE = 62
    KEYCODE_TAB = 61
    
    @staticmethod
    def char_to_keycode(char: str) -> int:
        """将字符转换为按键码"""
        if len(char) != 1:
            return 0
        
        # 简化实现，实际应该使用完整的按键映射表
        if char.isalpha():
            return ord(char.upper()) - ord('A') + 29
        elif char.isdigit():
            return ord(char) - ord('0') + 7
        elif char == ' ':
            return KeyCode.KEYCODE_SPACE
        else:
            return ord(char)