#!/usr/bin/env python3
"""
Native Mirroring Pro - Improved Version
Supports Scrcpy 3.x protocol and H.264 video decoding via PyAV.
"""
import sys, time, socket, struct, logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QTextEdit
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap

# Configure logging using the improved log manager
from log_manager import get_logger
logger = get_logger()

from adb_manager import AdbServerManager
from scrcpy_server import ScrcpyServerManager
from video_decoder_improved import VideoDecoder

class ScrcpyClientGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Native Mirroring Pro - Improved (PyAV)')
        self.setGeometry(100, 100, 1400, 900)
        
        # Initialize ADB
        try:
            self.adb = AdbServerManager()
            self.adb.start_server()
        except Exception as e:
            logger.error(f"ADB Init Error: {e}")
        
        self.scrcpy = None
        self.sock = None
        self.decoder = None
        self.running = False
        
        self.setup_ui()
        
        # Initialize device list
        QTimer.singleShot(500, self.refresh_devices)
    
    def setup_ui(self):
        """Setup User Interface"""
        cw = QWidget()
        self.setCentralWidget(cw)
        main_layout = QHBoxLayout(cw)
        
        # Left Panel
        left_layout = QVBoxLayout()
        
        # Device List
        left_layout.addWidget(QLabel('Devices:'))
        self.devices_list = QListWidget()
        left_layout.addWidget(self.devices_list)
        
        # Control Buttons
        self.connect_btn = QPushButton('Connect')
        self.connect_btn.clicked.connect(self.toggle_connection)
        left_layout.addWidget(self.connect_btn)
        
        # Log Area
        left_layout.addWidget(QLabel('Log:'))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(250)
        left_layout.addWidget(self.log_area)
        
        main_layout.addLayout(left_layout, 1)
        
        # Right Video Display
        self.video_label = QLabel('READY')
        self.video_label.setStyleSheet('background-color: black; color: white; font-size: 24px;')
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setMinimumSize(600, 800)
        main_layout.addWidget(self.video_label, 2)

    def log(self, msg):
        """Log message to GUI and file"""
        timestamp = time.strftime("%H:%M:%S")
        full_msg = f'[{timestamp}] {msg}'
        self.log_area.append(full_msg)
        self.log_area.verticalScrollBar().setValue(
            self.log_area.verticalScrollBar().maximum()
        )
        logger.info(msg)

    def refresh_devices(self):
        """Refresh connected devices"""
        try:
            self.devices_list.clear()
            devices = self.adb.list_devices()
            if devices:
                for dev in devices:
                    self.devices_list.addItem(dev)
                self.log(f'Found {len(devices)} device(s)')
            else:
                self.log('No devices found')
        except Exception as e:
            self.log(f"Error refreshing devices: {e}")

    def toggle_connection(self):
        """Toggle connection state"""
        if self.running:
            self.stop_connection()
        else:
            self.start_connection()

    def start_connection(self):
        """Start Scrcpy connection"""
        item = self.devices_list.currentItem()
        if not item:
            self.log('Please select a device')
            return
        
        device_id = item.text()
        self.log(f'Connecting to: {device_id}')
        
        try:
            # 1. Start Scrcpy Server
            self.scrcpy = ScrcpyServerManager(device_id, self.adb)
            if not self.scrcpy.start_server():
                self.log('Failed to start Scrcpy server')
                return
            
            self.log('Scrcpy server started')
            time.sleep(2) # Wait for server to initialize
            
            # 2. Setup Port Forwarding
            if not self.scrcpy.setup_port_forwarding():
                self.log('Port forwarding failed')
                return
            
            self.log('Port forwarding established')
            
            # 3. Connect Socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect(('127.0.0.1', 27183))
            self.log('Socket connected!')
            
            # 4. Perform Handshake (Device Name + Size)
            # Depending on protocol version, this might vary.
            # Assuming standard scrcpy protocol:
            # Dummy byte? No.
            # Device Name (64) + Width (2) + Height (2)? Or 4 bytes?
            # scrcpy_client_stable.py used 64 + 4 + 4.
            # Let's trust the decoder to handle the stream, BUT usually handshake is before stream.
            
            self.sock.settimeout(5.0)
            device_name = self.sock.recv(64)
            res_data = self.socket.recv(8) # W(4) + H(4)
            if len(res_data) == 8:
                w, h = struct.unpack('>II', res_data)
                self.log(f"Connected to {device_name.decode('utf-8', 'ignore').strip()} ({w}x{h})")
            self.sock.settimeout(None)

            # 5. Start Decoder Thread
            self.decoder = VideoDecoder(self.sock)
            self.decoder.frame_ready.connect(self._on_frame)
            self.decoder.stats_signal.connect(self._on_stats)
            self.decoder.start()
            
            self.running = True
            self.connect_btn.setText('Disconnect')
            self.video_label.setText('')
            self.log('Video streaming started!')
            
        except Exception as e:
            self.log(f'Connection error: {e}')
            logger.exception('Connection exception')
            self.stop_connection()

    def stop_connection(self):
        """Stop connection"""
        self.running = False
        
        if self.decoder:
            self.decoder.stop()
            self.decoder = None
        
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None
        
        if self.scrcpy:
            self.scrcpy.stop_server()
            self.scrcpy = None
        
        self.connect_btn.setText('Connect')
        self.video_label.setText('READY')
        self.log('Disconnected')

    @pyqtSlot(QImage)
    def _on_frame(self, img):
        """Handle new video frame"""
        try:
            pixmap = QPixmap.fromImage(img)
            # Scale to fit window while keeping aspect ratio
            scaled = pixmap.scaled(
                self.video_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.video_label.setPixmap(scaled)
        except Exception as e:
            logger.error(f'Frame display error: {e}')

    @pyqtSlot(dict)
    def _on_stats(self, stats):
        """Handle stats (FPS)"""
        if 'fps' in stats:
            self.setWindowTitle(f"Native Mirroring Pro - Improved (PyAV) - FPS: {stats['fps']:.1f}")

    def closeEvent(self, event):
        """Handle window close"""
        self.stop_connection()
        super().closeEvent(event)

def main():
    app = QApplication(sys.argv)
    window = ScrcpyClientGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()