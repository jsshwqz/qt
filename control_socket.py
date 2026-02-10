#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import struct
import threading
from typing import Optional, Tuple, List
from coordinate_transformer import CoordinateTransformer


class ControlEvent:
    """Represents a control event to be sent to the device."""
    
    # Event types
    TYPE_KEYCODE = 0
    TYPE_TEXT = 1
    TYPE_TOUCH = 2
    TYPE_SCROLL = 3
    
    # Action types for touch events
    ACTION_DOWN = 0
    ACTION_UP = 1
    ACTION_MOVE = 2
    
    def __init__(self, event_type: int, action: int, **kwargs):
        self.event_type = event_type
        self.action = action
        self.x = kwargs.get('x', 0)
        self.y = kwargs.get('y', 0)
        self.buttons = kwargs.get('buttons', 0)
        self.keycode = kwargs.get('keycode', 0)
        self.text = kwargs.get('text', '')
        self.timestamp = kwargs.get('timestamp', 0)


class ControlSocketManager:
    """Manages control socket connection and sends control events to device."""
    
    def __init__(self, device_id: str, adb_manager):
        self.device_id = device_id
        self.adb_manager = adb_manager
        self.control_socket: Optional[socket.socket] = None
        self.connected = False
        self._lock = threading.Lock()
        self.control_port = 27184
        
        # Scrcpy control protocol constants
        self.CONTROL_MSG_TYPE_INJECT_KEYCODE = 0
        self.CONTROL_MSG_TYPE_INJECT_TEXT = 1
        self.CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT = 2
        self.CONTROL_MSG_TYPE_INJECT_SCROLL_EVENT = 3
        self.CONTROL_MSG_TYPE_BACK_OR_SCREEN_ON = 4
        self.CONTROL_MSG_TYPE_EXPAND_NOTIFICATION_PANEL = 5
        self.CONTROL_MSG_TYPE_COLLAPSE_NOTIFICATION_PANEL = 6
        self.CONTROL_MSG_TYPE_GET_CLIPBOARD = 7
        self.CONTROL_MSG_TYPE_SET_CLIPBOARD = 8
        self.CONTROL_MSG_TYPE_SET_SCREEN_POWER_MODE = 9
        self.CONTROL_MSG_TYPE_ROTATE_DEVICE = 10
        
        # Touch action constants
        self.ACTION_DOWN = 0
        self.ACTION_UP = 1
        self.ACTION_MOVE = 2
        
        # Android keycodes
        self.KEYCODE_BACK = 4
        self.KEYCODE_HOME = 3
        self.KEYCODE_MENU = 82
        self.KEYCODE_APP_SWITCH = 187
        
    def connect(self) -> bool:
        """Connect to control socket."""
        with self._lock:
            try:
                # Forward control port
                if not self.adb_manager.forward_port(
                    self.device_id, 
                    self.control_port, 
                    self.control_port
                ):
                    print(f"Failed to forward control port {self.control_port}")
                    return False
                
                # Connect to local port
                self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.control_socket.connect(('127.0.0.1', self.control_port))
                self.connected = True
                
                print(f"Control socket connected on port {self.control_port}")
                return True
                
            except Exception as e:
                print(f"Failed to connect control socket: {e}")
                self.connected = False
                return False
    
    def disconnect(self):
        """Disconnect from control socket."""
        with self._lock:
            self.connected = False
            if self.control_socket:
                try:
                    self.control_socket.close()
                except:
                    pass
                self.control_socket = None
            
            # Remove port forwarding
            self.adb_manager.remove_forward(self.device_id, self.control_port)
    
    def is_connected(self) -> bool:
        """Check if control socket is connected."""
        return self.connected and self.control_socket is not None
    
    def _send_control_packet(self, packet_type: int, *args) -> bool:
        """Send a control packet to the device."""
        if not self.is_connected():
            return False
        
        try:
            # Build packet based on type
            if packet_type == self.CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT:
                # Packet: type(1) + action(1) + buttons(4) + position(4+4) + pressure(4) + buttons(4)
                data = struct.pack(
                    '>BBIIIIII',
                    packet_type,
                    args[0],  # action
                    0,  # buttons
                    args[1],  # x
                    args[2],  # y
                    0xFFFF,  # pressure (max)
                    0,  # buttons
                )
            elif packet_type == self.CONTROL_MSG_TYPE_INJECT_KEYCODE:
                # Packet: type(1) + action(1) + keycode(4) + metastate(4) + repeat(4)
                data = struct.pack(
                    '>BBIII',
                    packet_type,
                    args[0],  # action (0=down, 1=up, 2=repeat)
                    args[1],  # keycode
                    0,  # metastate
                    0   # repeat
                )
            elif packet_type == self.CONTROL_MSG_TYPE_INJECT_TEXT:
                # Packet: type(1) + text_length(2) + text
                text = args[0].encode('utf-8')
                data = struct.pack('>BH', packet_type, len(text)) + text
            else:
                print(f"Unsupported control packet type: {packet_type}")
                return False
            
            # Send packet
            self.control_socket.send(data)
            return True
            
        except Exception as e:
            print(f"Failed to send control packet: {e}")
            self.connected = False
            return False
    
    def send_touch_down(self, x: int, y: int) -> bool:
        """Send touch down event."""
        return self._send_control_packet(
            self.CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT,
            self.ACTION_DOWN,
            x, y
        )
    
    def send_touch_up(self, x: int, y: int) -> bool:
        """Send touch up event."""
        return self._send_control_packet(
            self.CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT,
            self.ACTION_UP,
            x, y
        )
    
    def send_touch_move(self, x: int, y: int) -> bool:
        """Send touch move event."""
        return self._send_control_packet(
            self.CONTROL_MSG_TYPE_INJECT_TOUCH_EVENT,
            self.ACTION_MOVE,
            x, y
        )
    
    def send_click(self, x: int, y: int) -> bool:
        """Send a click event (down + up)."""
        if not self.send_touch_down(x, y):
            return False
        # Small delay between down and up
        import time
        time.sleep(0.01)
        return self.send_touch_up(x, y)
    
    def send_swipe(self, x1: int, y1: int, x2: int, y2: int, duration: float = 0.3) -> bool:
        """Send a swipe gesture."""
        import time
        
        if not self.send_touch_down(x1, y1):
            return False
        
        # Calculate intermediate points for smooth swipe
        steps = int(duration * 60)  # 60 steps per second
        for i in range(1, steps + 1):
            t = i / steps
            x = int(x1 + (x2 - x1) * t)
            y = int(y1 + (y2 - y1) * t)
            
            if not self.send_touch_move(x, y):
                return False
            
            time.sleep(duration / steps)
        
        return self.send_touch_up(x2, y2)
    
    def send_keycode(self, keycode: int, action: int = 0) -> bool:
        """Send a keycode event."""
        return self._send_control_packet(
            self.CONTROL_MSG_TYPE_INJECT_KEYCODE,
            action,
            keycode
        )
    
    def send_back_key(self) -> bool:
        """Send back key press."""
        return self.send_keycode(self.KEYCODE_BACK)
    
    def send_home_key(self) -> bool:
        """Send home key press."""
        return self.send_keycode(self.KEYCODE_HOME)
    
    def send_text(self, text: str) -> bool:
        """Send text injection."""
        return self._send_control_packet(
            self.CONTROL_MSG_TYPE_INJECT_TEXT,
            text
        )
    
    def send_power_on(self) -> bool:
        """Turn screen on or wake device."""
        return self._send_control_packet(
            self.CONTROL_MSG_TYPE_BACK_OR_SCREEN_ON
        )
    
    def send_expand_notifications(self) -> bool:
        """Expand notification panel."""
        return self._send_control_packet(
            self.CONTROL_MSG_TYPE_EXPAND_NOTIFICATION_PANEL
        )
    
    def send_collapse_notifications(self) -> bool:
        """Collapse notification panel."""
        return self._send_control_packet(
            self.CONTROL_MSG_TYPE_COLLAPSE_NOTIFICATION_PANEL
        )