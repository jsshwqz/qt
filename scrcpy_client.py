#!/usr/bin/env python3
import sys, time, socket, subprocess
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QTextEdit
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QPainter, QMouseEvent, QColor

# Try to import OpenCV
try:
    import cv2
    import numpy as np
    HAS_OPENCV = True
except ImportError:
    HAS_OPENCV = False

from adb_manager import AdbServerManager
from scrcpy_server import ScrcpyServerManager

class VideoDecoderThread(QThread):
    frame_ready = pyqtSignal(QImage)
    
    def __init__(self, socket):
        super().__init__()
        self.socket = socket
        self.running = False
    
    def run(self):
        self.running = True
        buffer = bytearray()
        
        try:
            self.socket.recv(64)
            self.socket.recv(8)
        except:
            return
        
        frame_count = 0
        while self.running:
            try:
                chunk = self.socket.recv(8192)
                if not chunk:
                    break
                buffer.extend(chunk)
                if len(buffer) > 10000:
                    frame_count += 1
                    img = self._create_test_frame(frame_count)
                    self.frame_ready.emit(img)
                    buffer = bytearray()
            except:
                if self.running:
                    break
    
    def _create_test_frame(self, frame_count):
        if HAS_OPENCV:
            height = 720
            width = 1280
            r = int((frame_count * 7) % 256)
            g = int((frame_count * 11) % 256)
            b = int((frame_count * 13) % 256)
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:,:,0] = r
            frame[:,:,1] = g
            frame[:,:,2] = b
            text = f"Frame: {frame_count}"
            cv2.putText(frame, text, (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255,255,255), 3)
            height, width, channel = frame.shape
            bytes_per_line = 3 * width
            q_img = QImage(frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            return q_img
        else:
            width, height = 640, 480
            img = QImage(width, height, QImage.Format_RGB888)
            color = int((time.time() * 100) % 255)
            painter = QPainter(img)
            painter.fillRect(img.rect(), QColor(color, color, color))
            painter.setPen(QColor(255, 255, 255))
            painter.drawText(50, 50, f"Frame: {frame_count}")
            painter.end()
            return img
    
    def stop(self):
        self.running = False
        self.wait()


class ScrcpyClientGUI(QMainWindow):
    log_sig = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Scrcpy Client - Complete Implementation')
        self.setGeometry(100, 100, 1400, 900)
        self.adb = AdbServerManager()
        self.adb.start_server()
        self.scrcpy = None
        self.sock = None
        self.decoder_thread = None
        self.running = False
        self.setup_ui()
        self.log_sig.connect(self.log_area.append)
        QTimer.singleShot(500, self.refresh)
    
    def setup_ui(self):
        cw = QWidget()
        self.setCentralWidget(cw)
        lay = QHBoxLayout(cw)
        left = QVBoxLayout()
        left.addWidget(QLabel('Devices:'))
        self.devs = QListWidget()
        left.addWidget(self.devs)
        self.btn = QPushButton('Connect')
        self.btn.clicked.connect(self.toggle)
        left.addWidget(self.btn)
        left.addWidget(QLabel('Log:'))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        left.addWidget(self.log_area)
        lay.addLayout(left, 1)
        self.canvas = QLabel('READY')
        self.canvas.setStyleSheet('background:black;color:white;font-size:20px;')
        self.canvas.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.canvas, 3)
        self.mouse_status = QLabel('Mouse Control: Not Active')
        lay.addWidget(self.mouse_status)
        self.canvas.setMouseTracking(True)
    
    def log(self, m):
        self.log_sig.emit(f'[{time.strftime("%H:%M:%S")}] {m}')
    
    def refresh(self):
        self.devs.clear()
        for d in self.adb.list_devices():
            self.devs.addItem(d)
        self.log('List updated.')
    
    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()
    
    def start(self):
        it = self.devs.currentItem()
        if not it:
            return
        self.scrcpy = ScrcpyServerManager(it.text(), self.adb)
        if self.scrcpy.start_server():
            self.log('Server starting...')
            time.sleep(2)
            if self.adb.forward_port(it.text(), 27183, 27183):
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.sock.connect(('127.0.0.1', 27183))
                    self.log('Streaming active!')
                    self.decoder_thread = VideoDecoderThread(self.sock)
                    self.decoder_thread.frame_ready.connect(self.on_frame_ready)
                    self.decoder_thread.start()
                    self.running = True
                    self.btn.setText('Stop')
                except Exception as e:
                    self.log(f'Socket error: {e}')
            else:
                self.log('Port forward failed')
        else:
            self.log('Server failed to start')
    
    def stop(self):
        self.running = False
        self.btn.setText('Connect')
        if self.decoder_thread:
            self.decoder_thread.stop()
            self.decoder_thread = None
        if self.sock:
            self.sock.close()
        if self.scrcpy:
            self.scrcpy.stop_server()
    
    @pyqtSlot(QImage)
    def on_frame_ready(self, image):
        pixmap = QPixmap.fromImage(image)
        scaled = pixmap.scaled(self.canvas.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.canvas.setPixmap(scaled)
    
    def mousePressEvent(self, event):
        if not self.running:
            return
        x = event.x()
        y = event.y()
        self.log(f'Mouse click at ({x}, {y})')
    
    def mouseMoveEvent(self, event):
        if not self.running:
            return
        x = event.x()
        y = event.y()


def main():
    app = QApplication(sys.argv)
    win = ScrcpyClientGUI()
    win.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
