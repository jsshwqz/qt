#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from typing import Tuple, Optional


class CoordinateTransformer:
    """Transforms coordinates between GUI window and phone screen."""
    
    def __init__(self):
        self.window_size: Optional[Tuple[int, int]] = None
        self.phone_size: Optional[Tuple[int, int]] = None
        self.scale: float = 1.0
        self.scale_x: float = 1.0
        self.scale_y: float = 1.0
        self.offset_x: int = 0
        self.offset_y: int = 0
    
    def set_window_size(self, width: int, height: int):
        """Set the GUI window/display size."""
        self.window_size = (width, height)
        self._recalculate()
    
    def set_phone_size(self, width: int, height: int):
        """Set the phone screen resolution."""
        self.phone_size = (width, height)
        self._recalculate()
    
    def set_sizes(self, window_width: int, window_height: int, 
                  phone_width: int, phone_height: int):
        """Set both window and phone sizes at once."""
        self.window_size = (window_width, window_height)
        self.phone_size = (phone_width, phone_height)
        self._recalculate()
    
    def _recalculate(self):
        """Recalculate transformation matrix."""
        if not self.window_size or not self.phone_size:
            return
        
        window_w, window_h = self.window_size
        phone_w, phone_h = self.phone_size
        
        # Calculate scaling to fit phone screen in window
        scale_x = window_w / phone_w
        scale_y = window_h / phone_h
        
        # Use uniform scaling to maintain aspect ratio
        self.scale = min(scale_x, scale_y)
        
        # Calculate offsets to center the image
        scaled_phone_w = phone_w * self.scale
        scaled_phone_h = phone_h * self.scale
        
        self.offset_x = (window_w - scaled_phone_w) // 2
        self.offset_y = (window_h - scaled_phone_h) // 2
    
    def window_to_phone(self, window_x: int, window_y: int) -> Optional[Tuple[int, int]]:
        """Transform window coordinates to phone coordinates."""
        if not self.window_size or not self.phone_size:
            return None
        
        # Check if point is within the scaled phone area
        if (window_x < self.offset_x or 
            window_x >= self.offset_x + self.phone_size[0] * self.scale or
            window_y < self.offset_y or 
            window_y >= self.offset_y + self.phone_size[1] * self.scale):
            return None
        
        # Transform to phone coordinates
        phone_x = int((window_x - self.offset_x) / self.scale)
        phone_y = int((window_y - self.offset_y) / self.scale)
        
        # Clamp to phone screen bounds
        phone_x = max(0, min(phone_x, self.phone_size[0] - 1))
        phone_y = max(0, min(phone_y, self.phone_size[1] - 1))
        
        return phone_x, phone_y
    
    def phone_to_window(self, phone_x: int, phone_y: int) -> Optional[Tuple[int, int]]:
        """Transform phone coordinates to window coordinates."""
        if not self.window_size or not self.phone_size:
            return None
        
        # Transform to window coordinates
        window_x = int(phone_x * self.scale + self.offset_x)
        window_y = int(phone_y * self.scale + self.offset_y)
        
        return window_x, window_y
    
    def get_scale_factor(self) -> float:
        """Get the current scale factor."""
        return self.scale if hasattr(self, 'scale') else 1.0
    
    def is_point_in_display(self, x: int, y: int) -> bool:
        """Check if a window coordinate is within the phone display area."""
        if not self.window_size or not self.phone_size:
            return False
        
        return (self.offset_x <= x < self.offset_x + self.phone_size[0] * self.scale and
                self.offset_y <= y < self.offset_y + self.phone_size[1] * self.scale)
    
    def get_display_rect(self) -> Tuple[int, int, int, int]:
        """Get the display rectangle (x, y, width, height) in window coordinates."""
        if not self.window_size or not self.phone_size:
            return 0, 0, 0, 0
        
        width = int(self.phone_size[0] * self.scale)
        height = int(self.phone_size[1] * self.scale)
        
        return self.offset_x, self.offset_y, width, height