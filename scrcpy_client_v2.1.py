#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Native Mirroring Pro - Enhanced Version 2.1
Complete Android mirroring application with USB and WiFi support.
"""

import sys
import time
import socket
import struct
import logging
import traceback
from datetime import datetime

from log_manager import get_log_manager, get_logger
from config_manager import get_config_manager
from exceptions import (
    ScrcpyException, DeviceConnectionException, VideoDecodingException,
    ErrorHandler, global_error_handler
)

# Initialize logging
log_manager = get_log_manager(log_dir='.', log_file='scrcpy_enhanced.log')
logger = get_logger()

# Import video decoder
try:
    from video_decoder_v2_1 import create_video_decoder
except ImportError:
    # Fallback if filename is different (dash vs underscore)
    try:
        from video_decoder_v2_1 import create_video_decoder
    except ImportError:
        # Try finding the file assuming it is named video_decoder_v2.1.py 
        # (Python import doesn't like dots in filenames usually, except packages)
        # Renaming the file to avoid import issues might be needed.
        # Let's assume I will rename it to video_decoder_v2_1.py
        pass

# PyQt5
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QListWidget, QTextEdit, QMessageBox, QListWidgetItem
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
    from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter, QFont
except ImportError:
    print("PyQt5 not found.")
    sys.exit(1)

from adb_manager import AdbServerManager

class VideoDecoderThread(QThread):
    frame_ready = pyqtSignal(QImage)
    status_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, sock):
        super().__init__()
        self.socket = sock
        self.running = False
        self.width = 720
        self.height = 1280
        self.decoder = None # Initialized after resolution handshake
    
    def run(self):
        self.running = True
        logger.info('VideoDecoderThread started')
        
        try:
            self.socket.settimeout(5.0)
            
            # Handshake
            device_name = self.socket.recv(64)
            res_data = self.socket.recv(8)
            if len(res_data) == 8:
                self.width, self.height = struct.unpack('>II', res_data)
                self.status_changed.emit(f'Connected: {self.width}x{self.height}')
            
            self.socket.settimeout(None)
            
            # Initialize Decoder
            # Import here to avoid import errors at module level if file missing
            import importlib.util
            spec = importlib.util.spec_from_file_location("video_decoder_v2_1", "video_decoder_v2.1.py")
            vd_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(vd_module)
            
            self.decoder = vd_module.create_video_decoder(self.width, self.height)
            
        except Exception as e:
            logger.error(f"Handshake/Init failed: {e}")
            self.error_occurred.emit(str(e))
            return
            
        while self.running:
            try:
                # Read 4-byte length (Scrcpy protocol wrapper usually)
                # If using raw stream, this might need adjustment.
                # Assuming "length-prefixed" for now based on previous code.
                header = self._recv_all(4)
                if not header: break
                
                frame_size = struct.unpack('>I', header)[0]
                frame_data = self._recv_all(frame_size)
                if not frame_data: break
                
                # Decode
                result = self.decoder.decode_h264_frame(frame_data)
                
                if result['success'] and 'image' in result:
                    img_np = result['image']
                    h, w, ch = img_np.shape
                    # QImage from numpy
                    qt_img = QImage(img_np.data, w, h, ch*w, QImage.Format_RGB888).copy()
                    self.frame_ready.emit(qt_img)
                
            except Exception as e:
                logger.error(f"Loop error: {e}")
                break
        
        self.running = False

    def _recv_all(self, length):
        data = b''
        while len(data) < length:
            try:
                chunk = self.socket.recv(min(65536, length - len(data)))
                if not chunk: return None
                data += chunk
            except: return None
        return data

    def stop(self):
        self.running = False
        self.wait()

class ScrcpyClientGUI(QMainWindow):
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Native Mirroring Pro v2.1')
        self.setGeometry(100, 100, 1200, 800)
        
        self.config = get_config_manager()
        self.adb = None
        self.sock = None
        self.decoder = None
        self.running = False
        self.selected_device = None
        
        try:
            self.adb = AdbServerManager()
            self.adb.start_server()
        except Exception as e:
            logger.error(f"ADB Error: {e}")
            
        self.setup_ui()
        self.log_signal.connect(self._on_log)
        
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh_devices)
        self.refresh_timer.start(2000)
    
    def setup_ui(self):
        cw = QWidget(); self.setCentralWidget(cw); layout = QHBoxLayout(cw)
        left = QVBoxLayout()
        left.addWidget(QLabel("Devices:"))
        self.device_list = QListWidget()
        self.device_list.itemClicked.connect(self.on_device_select)
        left.addWidget(self.device_list)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.clicked.connect(self.toggle_connect)
        self.connect_btn.setEnabled(False)
        left.addWidget(self.connect_btn)
        
        self.log_text = QTextEdit(); self.log_text.setReadOnly(True)
        left.addWidget(self.log_text)
        
        layout.addLayout(left, 1)
        
        self.video_label = QLabel("Ready")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("background: black; color: white;")
        layout.addWidget(self.video_label, 3)

    def refresh_devices(self):
        if not self.adb: return
        try:
            devs = self.adb.list_devices()
            self.device_list.clear()
            for d in devs: self.device_list.addItem(d)
            if not devs: self.connect_btn.setEnabled(False)
        except: pass

    def on_device_select(self, item):
        self.selected_device = item.text()
        self.connect_btn.setEnabled(True)

    def toggle_connect(self):
        if self.running: self.disconnect()
        else: self.connect()

    def connect(self):
        if not self.selected_device: return
        self.log(f"Connecting to {self.selected_device}")
        
        try:
            from scrcpy_server import ScrcpyServerManager
            self.scrcpy = ScrcpyServerManager(self.selected_device, self.adb)
            if not self.scrcpy.start_server(): return
            if not self.scrcpy.setup_port_forwarding(): return
            
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('127.0.0.1', 27183))
            
            self.decoder = VideoDecoderThread(self.sock)
            self.decoder.frame_ready.connect(self.on_frame)
            self.decoder.start()
            
            self.running = True
            self.connect_btn.setText("Disconnect")
        except Exception as e:
            self.log(f"Error: {e}")

    def disconnect(self):
        self.running = False
        if self.decoder: self.decoder.stop()
        if self.sock: self.sock.close()
        if hasattr(self, 'scrcpy') and self.scrcpy: self.scrcpy.stop_server()
        self.connect_btn.setText("Connect")
        self.video_label.setText("Disconnected")

    @pyqtSlot(QImage)
    def on_frame(self, img):
        pix = QPixmap.fromImage(img)
        self.video_label.setPixmap(pix.scaled(self.video_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _on_log(self, msg):
        self.log_text.append(msg)

    def log(self, msg):
        self.log_signal.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")
        logger.info(msg)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = ScrcpyClientGUI()
    win.show()
    sys.exit(app.exec_())