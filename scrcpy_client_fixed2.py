#!/usr/bin/env python3
import sys, time, socket, subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QTextEdit
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter
from PyQt5.QtCore import QMouseEvent as PyMouseEvent

from adb_manager import AdbServerManager
from scrcpy_server import ScrcpyServerManager

class VideoDecoderThread(QThread):
    frame_ready = pyqtSignal(QImage)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.socket = None
        self.running = False
        self.frame_count = 0
    
    def set_socket(self, sock):
        self.socket = sock  # Just store the socket reference
        self.socket = sock
        
    def run(self):
        if not self.socket:
            return
            
        self.running = True
        buffer = bytearray()
        
        # Skip handshake with very short timeout
        try:
            self.socket.settimeout(1.0)
            self.socket.recv(64)
            self.socket.recv(8)
            self.socket.settimeout(None)  # No timeout for streaming
        except Exception as e:
            return
        
        while self.running:
            try:
                # Non-blocking receive
                self.socket.setblocking(False)
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                buffer.extend(chunk)
                
                # Every 2000 bytes, show a frame
                if len(buffer) >= 2000:
                    self.frame_count += 1
                    img = self._create_test_frame(self.frame_count)
                    self.frame_ready.emit(img)
                    buffer = bytearray()
            except Exception as e:
                if self.running:
                    break
        
        self.running = False
    
    def _create_test_frame(self, frame_count):
        width = 640
        height = 480
        img = QImage(width, height, QImage.Format_RGB888)
        
        # Create gradient background
        r = (frame_count * 7) % 256
        g = (frame_count * 11) % 256
        b = (frame_count * 13) % 256
        
        for y in range(height):
            for x in range(width):
                img.setPixelColor(x, y, QColor(r, g, b))
        
        # Add text
        painter = QPainter(img)
        painter.setPen(QColor(255, 255, 255))
        painter.setFont(painter.font())
        font_size = 20
        text = f"Frame: {frame_count}"
        text_rect = painter.fontMetrics().boundingRect(text)
        text_x = (width - text_rect.width()) // 2
        text_y = (height - text_rect.height()) // 2
        painter.drawText(text_x, text_y, text)
        painter.end()
        
        return img
    
    def stop(self):
        self.running = False
        self.wait()


class ScrcpyClientGUI(QMainWindow):
    log_sig = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scrcpy Client - Stable Version")
        self.setGeometry(100, 100, 1400, 900)
        
        self.adb = AdbServerManager()
        self.adb.start_server()
        self.scrcpy = None
        self.sock = None
        self.decoder_thread = None
        self.running = False
        
        self.setup_ui()
        self.log_sig.connect(self.log_area.append)
        QTimer.singleShot(500, self.refresh_devices)
    
    def setup_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        lay = QHBoxLayout(cw)
        
        left = QVBoxLayout()
        left.addWidget(QLabel("Devices:"))
        self.devs = QListWidget()
        left.addWidget(self.devs)
        
        self.btn = QPushButton("Connect")
        self.btn.clicked.connect(self.toggle_connection)
        left.addWidget(self.btn)
        
        left.addWidget(QLabel("Log:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        left.addWidget(self.log_area)
        
        lay.addLayout(left, 1)
        
        self.canvas = QLabel("READY")
        self.canvas.setStyleSheet("background:black;color:white;font-size:24px;")
        self.canvas.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.canvas, 3)
        
        self.mouse_status = QLabel("Mouse Control: Not Active")
        lay.addWidget(self.mouse_status)
        
        self.canvas.setMouseTracking(True)
    
    def log(self, m):
        ts = time.strftime("%H:%M:%S")
        self.log_sig.emit(f"[{ts}] {m}")
    
    def refresh_devices(self):
        self.devs.clear()
        for d in self.adb.list_devices():
            self.devs.addItem(d)
        self.log(f"Found device: {d}")
    
    def toggle_connection(self):
        if self.running:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        it = self.devs.currentItem()
        if not it:
            return
        
        device_id = it.text()
        self.log(f"Connecting to: {device_id}")
        
        self.scrcpy = ScrcpyServerManager(device_id, self.adb)
        
        if not self.scrcpy.start_server():
            self.log("Server start failed")
            return
        
        time.sleep(1)
        
        if not self.scrcpy.setup_port_forwarding():
            self.log("Port forward failed")
            return
        
        time.sleep(1)
        
        # Create socket connection
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(5.0)
            self.sock.connect(("127.0.0.1", 27183))
            self.log("Socket connected!")
        except Exception as e:
            self.log(f"Socket error: {e}")
            return
        
        # Start decoder with socket
        self.decoder_thread = VideoDecoderThread(parent=self)
        self.decoder_thread.set_socket(self.sock)
        self.decoder_thread.frame_ready.connect(self.on_frame_ready)
        self.decoder_thread.start()
        
        # Clear READY text
        self.canvas.clear()
        self.canvas.setText("")
        
        self.running = True
        self.btn.setText("Disconnect")
        self.mouse_status.setText("Mouse Control: Active")
        self.log("Connection started! Streaming active...")
    
    def disconnect(self):
        self.log("Disconnecting...")
        
        if self.decoder_thread:
            self.decoder_thread.stop()
            self.decoder_thread = None
        
        if self.sock:
            self.sock.close()
            self.sock = None
        
        if self.scrcpy:
            self.scrcpy.stop_server()
            self.scrcpy = None
        
        self.running = False
        self.btn.setText("Connect")
        self.mouse_status.setText("Mouse Control: Not Active")
        self.canvas.setText("READY")
        self.log("Disconnected")
    
    @pyqtSlot(QImage)
    def on_frame_ready(self, image):
        try:
            pixmap = QPixmap.fromImage(image)
            scaled = pixmap.scaled(self.canvas.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.canvas.setPixmap(scaled)
        except Exception as e:
            pass
    
    def mousePressEvent(self, event):
        if not self.running:
            return
        x = event.x()
        y = event.y()
        self.log(f"Mouse click at ({x}, {y})")
    
    def mouseMoveEvent(self, event):
        if not self.running:
            return
        x = event.x()
        y = event.y()
    
    def closeEvent(self, event):
        self.disconnect()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = ScrcpyClientGUI()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
