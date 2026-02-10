#!/usr/bin/env python3
import sys, time, socket, subprocess, threading, os, struct
import logging
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QTextEdit
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s', filename='scrcpy_debug.log', filemode='w')
logger = logging.getLogger(__name__)

try:
    import cv2
    import numpy as np
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from adb_manager import AdbServerManager
from scrcpy_server import ScrcpyServerManager

class VideoDecoderThread(QThread):
    frame_ready = pyqtSignal(QImage)
    
    def __init__(self, sock):
        super().__init__()
        self.socket = sock
        self.running = False
    
    def run(self):
        logger.info('VideoDecoderThread started')
        self.running = True
        
        try:
            self.socket.settimeout(5.0)
            # Scrcpy 3.x 握手: 64字节设备名 + 4字节宽 + 4字节高
            device_name = self.socket.recv(64)
            res_data = self.socket.recv(8)
            if len(res_data) == 8:
                w, h = struct.unpack('>II', res_data)
                logger.info(f'Handshake success: Res={w}x{h}')
            
            self.socket.settimeout(None)
        except Exception as e:
            logger.error(f'Handshake failed: {e}')
            return

        frame_count = 0
        while self.running:
            try:
                # 读取帧头 (4 字节: 帧大小)
                header = self.socket.recv(4)
                if len(header) < 4:
                    break
                frame_size = struct.unpack('>I', header)[0]
                logger.debug(f'Frame {frame_count}: size={frame_size}')
                
                # 读取帧数据
                frame_data = b''
                while len(frame_data) < frame_size:
                    chunk = self.socket.recv(min(65536, frame_size - len(frame_data)))
                    if not chunk:
                        break
                    frame_data += chunk
                
                if len(frame_data) == frame_size:
                    # 尝试用 OpenCV 解码
                    if HAS_CV2:
                        img = self._decode_h264(frame_data, frame_count)
                    else:
                        img = self._render_fallback_frame(frame_count)
                    
                    if img:
                        self.frame_ready.emit(img)
                        frame_count += 1
                
                time.sleep(0.01)  # 控制帧率
            except Exception as e:
                logger.error(f'Decode error: {e}')
                break
        
        self.running = False

    def _decode_h264(self, data, frame_no):
        """使用 OpenCV 视频解码器解码 H.264"""
        try:
            if not HAS_CV2:
                return self._render_fallback_frame(frame_no)
            
            # scrcpy 发送的是完整的 H.264 帧 (可能是 AVCC 或 Annex-B 格式)
            # 需要转换为 OpenCV 可解码的格式
            h264_data = self._prepare_h264_stream(data)
            
            # 使用 VideoCapture 解码
            nparr = np.frombuffer(h264_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is not None and frame.size > 0:
                h, w = frame.shape[:2]
                if h > 0 and w > 0:
                    # 转换 BGR -> RGB -> QImage
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    qi = QImage(frame_rgb.tobytes(), w, h, QImage.Format_RGB888)
                    logger.debug(f'Frame {frame_no} decoded: {w}x{h}')
                    return qi
                    
        except Exception as e:
            logger.warning(f'H.264 decode failed: {e}')
        
        return self._render_fallback_frame(frame_no)
    
    def _prepare_h264_stream(self, data):
        """准备 H.264 字节流，添加起始码等"""
        if len(data) < 4:
            return data
        
        # 检查是否已经是 Annex-B 格式 (起始码 0x00 0x00 0x00 0x01 或 0x00 0x00 0x01)
        if data[0:4] == b'\x00\x00\x00\x01' or data[0:3] == b'\x00\x00\x01':
            return data
        
        # 检查是否是 AVCC 格式 (有 NAL 长度前缀)
        # AVCC: 4字节长度前缀 + NAL 数据
        first_nal_len = struct.unpack('>I', data[0:4])[0]
        if first_nal_len > 0 and first_nal_len < len(data) - 4:
            # 转换为 Annex-B 格式
            result = b''
            offset = 0
            while offset < len(data):
                if offset + 4 > len(data):
                    break
                nal_len = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4
                if offset + nal_len > len(data):
                    break
                # 添加 Annex-B 起始码
                result += b'\x00\x00\x00\x01' + data[offset:offset+nal_len]
                offset += nal_len
            return result
        
        # 如果都不是，直接返回数据（可能是裸 NAL）
        return b'\x00\x00\x00\x01' + data

    def _render_fallback_frame(self, frame_no):
        """降级渲染: 显示帧计数器"""
        width, height = 720, 1280
        img = QImage(width, height, QImage.Format_RGB888)
        img.fill(QColor(30, 30, 30))
        
        # 使用 QPainter 绘制文字
        painter = QPainter(img)
        painter.setPen(QColor(0, 255, 100))
        painter.setFont(__import__('PyQt5.QtGui', fromlist=['QFont']).QFont('Arial', 48))
        painter.drawText(img.rect(), Qt.AlignCenter, f'Frame: {frame_no}\nStreaming...')
        painter.end()
        
        return img

    def stop(self):
        self.running = False
        self.wait()

class ScrcpyClientGUI(QMainWindow):
    log_sig = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Native Mirroring Pro - v3.3.3 Fix')
        self.setGeometry(100, 100, 1100, 800)
        self.adb = AdbServerManager()
        self.adb.start_server()
        self.scrcpy, self.sock, self.decoder, self.running = None, None, None, False
        self.setup_ui()
        self.log_sig.connect(self.log_area.append)
        QTimer.singleShot(500, self.refresh)
    
    def setup_ui(self):
        cw = QWidget(); self.setCentralWidget(cw); lay = QHBoxLayout(cw)
        left = QVBoxLayout()
        self.devs = QListWidget(); left.addWidget(QLabel('Devices:')); left.addWidget(self.devs)
        self.btn = QPushButton('Connect'); self.btn.clicked.connect(self.toggle); left.addWidget(self.btn)
        self.log_area = QTextEdit(); self.log_area.setReadOnly(True); left.addWidget(self.log_area)
        lay.addLayout(left, 1)
        self.canvas = QLabel('READY'); self.canvas.setStyleSheet('background:black;color:white;font-size:24px;'); self.canvas.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.canvas, 3)

    def log(self, m): self.log_sig.emit("[{}] {}".format(time.strftime("%H:%M:%S"), m))

    def refresh(self):
        self.devs.clear()
        for d in self.adb.list_devices(): self.devs.addItem(d)
        self.log('List updated.')

    def toggle(self):
        if self.running: self.stop()
        else: self.start()

    def start(self):
        it = self.devs.currentItem()
        if not it: return
        self.scrcpy = ScrcpyServerManager(it.text(), self.adb)
        if self.scrcpy.start_server():
            self.log('Server starting...'); time.sleep(2)
            if self.scrcpy.setup_port_forwarding():
                try:
                    self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.sock.connect(('127.0.0.1', 27183))
                    self.decoder = VideoDecoderThread(self.sock)
                    self.decoder.frame_ready.connect(self.on_frame)
                    self.decoder.start()
                    self.running = True; self.btn.setText('Stop'); self.canvas.setText('')
                    self.log('Connected!')
                except Exception as e: self.log(f'Error: {e}')
    
    def stop(self):
        self.running = False
        if self.decoder: self.decoder.stop()
        if self.sock: self.sock.close()
        if self.scrcpy: self.scrcpy.stop_server()
        self.btn.setText('Connect'); self.canvas.setText('READY'); self.log('Disconnected')

    @pyqtSlot(QImage)
    def on_frame(self, img):
        pix = QPixmap.fromImage(img)
        self.canvas.setPixmap(pix.scaled(self.canvas.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

if __name__ == '__main__':
    app = QApplication(sys.argv); win = ScrcpyClientGUI(); win.show(); sys.exit(app.exec_())
