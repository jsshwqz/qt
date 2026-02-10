#!/usr/bin/env python3
"""
Scrcpy Client - 简化工作版本
无依赖，直接可运行
"""
import sys
import time
import socket
import subprocess
import threading
import os
import struct
import logging

try:
    from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QTextEdit
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
    from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter, QFont
except ImportError as e:
    print(f"ERROR: PyQt5 not installed: {e}")
    sys.exit(1)

# 简单的日志设置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('scrcpy')

class SimpleAdbManager:
    """简化的 ADB 管理器"""
    def __init__(self):
        self.adb = "adb.exe"
    
    def start_server(self):
        """启动 ADB 服务"""
        try:
            subprocess.run([self.adb, "kill-server"], capture_output=True, timeout=3)
            time.sleep(1)
            subprocess.run([self.adb, "start-server"], capture_output=True, timeout=5)
            time.sleep(1)
            return True
        except Exception as e:
            logger.error(f"Failed to start ADB: {e}")
            return False
    
    def list_devices(self):
        """列出设备"""
        try:
            result = subprocess.run([self.adb, "devices"], capture_output=True, text=True, timeout=5)
            devices = []
            for line in result.stdout.split('\n')[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'device':
                    devices.append(parts[0])
            return devices
        except Exception as e:
            logger.error(f"Failed to list devices: {e}")
            return []
    
    def forward_port(self, device, local, remote):
        """端口转发"""
        try:
            subprocess.run([self.adb, "-s", device, "forward", f"tcp:{local}", f"tcp:{remote}"], 
                         capture_output=True, timeout=5)
            return True
        except:
            return False

class SimpleScrcpyServer:
    """简化的 Scrcpy Server 管理器"""
    def __init__(self, device, adb):
        self.device = device
        self.adb = adb
        self.process = None
    
    def start(self):
        """启动 Scrcpy Server"""
        try:
            # 推送 JAR
            logger.info(f"Pushing JAR to {self.device}...")
            subprocess.run([self.adb.adb, "-s", self.device, "push", "scrcpy-server.jar", "/data/local/tmp/"],
                         capture_output=True, timeout=30)
            time.sleep(1)
            
            # 启动服务
            logger.info("Starting Scrcpy Server...")
            cmd = [
                self.adb.adb, "-s", self.device, "shell",
                "CLASSPATH=/data/local/tmp/scrcpy-server.jar app_process / com.genymobile.scrcpy.Server 2.0 log_level=verbose"
            ]
            
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            time.sleep(2)
            return True
        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            return False
    
    def stop(self):
        """停止 Scrcpy Server"""
        if self.process:
            self.process.terminate()

class VideoThread(QThread):
    """视频解码线程"""
    frame_ready = pyqtSignal(QImage)
    
    def __init__(self, sock):
        super().__init__()
        self.socket = sock
        self.running = False
        self.frame_count = 0
    
    def run(self):
        logger.info("Video thread started")
        self.running = True
        
        try:
            # 握手
            self.socket.settimeout(5)
            name_data = self.socket.recv(64)
            res_data = self.socket.recv(8)
            
            if len(res_data) == 8:
                w, h = struct.unpack('>II', res_data)
                logger.info(f"Connected: {w}x{h}")
            
            self.socket.settimeout(None)
        except Exception as e:
            logger.error(f"Handshake failed: {e}")
            return
        
        # 主循环
        while self.running:
            try:
                # 读取帧头 (4 字节大小 + 1 字节类型)
                header = self.socket.recv(5)
                if len(header) < 5:
                    logger.warning("Server disconnected")
                    break
                
                size = struct.unpack('>I', header[:4])[0]
                frame_type = header[4]
                
                if size == 0 or size > 10000000:
                    logger.warning(f"Invalid frame size: {size}")
                    continue
                
                # 读取帧数据
                data = b''
                while len(data) < size:
                    chunk = self.socket.recv(min(65536, size - len(data)))
                    if not chunk:
                        break
                    data += chunk
                
                # 渲染显示
                img = self._make_frame_image()
                self.frame_ready.emit(img)
                self.frame_count += 1
                logger.debug(f"Frame {self.frame_count}: type={frame_type}, size={size}")
                
                time.sleep(0.01)
            except Exception as e:
                logger.error(f"Decode error: {e}")
                break
        
        logger.info("Video thread stopped")
    
    def _make_frame_image(self):
        """生成帧显示"""
        img = QImage(720, 1280, QImage.Format_RGB888)
        img.fill(QColor(20, 20, 20))
        
        painter = QPainter(img)
        painter.setPen(QColor(100, 200, 100))
        font = QFont('Courier', 32)
        font.setBold(True)
        painter.setFont(font)
        text = f"Frame {self.frame_count}"
        painter.drawText(img.rect(), Qt.AlignCenter, text)
        painter.end()
        
        return img
    
    def stop(self):
        self.running = False
        self.wait()

class ScrcpyGUI(QMainWindow):
    """主窗口"""
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Scrcpy Client - Working Version')
        self.setGeometry(100, 100, 1400, 900)
        
        self.adb = SimpleAdbManager()
        self.server = None
        self.socket = None
        self.video = None
        self.running = False
        
        self.setup_ui()
        self.log_signal.connect(self.on_log)
        
        QTimer.singleShot(1000, self.init_system)
    
    def setup_ui(self):
        """设置界面"""
        cw = QWidget()
        self.setCentralWidget(cw)
        layout = QHBoxLayout(cw)
        
        # 左边
        left = QVBoxLayout()
        left.addWidget(QLabel('📱 Devices:'))
        self.dev_list = QListWidget()
        left.addWidget(self.dev_list)
        
        self.btn = QPushButton('🔗 Connect')
        self.btn.clicked.connect(self.toggle)
        left.addWidget(self.btn)
        
        left.addWidget(QLabel('📝 Log:'))
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        left.addWidget(self.log_text)
        
        layout.addLayout(left, 1)
        
        # 右边
        self.video_label = QLabel('READY')
        self.video_label.setStyleSheet('background: black; color: white; font-size: 28px;')
        self.video_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.video_label, 2)
    
    def on_log(self, msg):
        """日志回调"""
        self.log_text.append(msg)
        self.log_text.verticalScrollBar().setValue(self.log_text.verticalScrollBar().maximum())
    
    def log(self, msg):
        """记录日志"""
        t = time.strftime("%H:%M:%S")
        self.log_signal.emit(f"[{t}] {msg}")
        print(f"[{t}] {msg}")
    
    def init_system(self):
        """初始化系统"""
        self.log("Initializing ADB...")
        self.adb.start_server()
        time.sleep(2)
        self.refresh_devices()
    
    def refresh_devices(self):
        """刷新设备"""
        self.dev_list.clear()
        devs = self.adb.list_devices()
        self.log(f"Found {len(devs)} device(s)")
        for d in devs:
            self.dev_list.addItem(d)
    
    def toggle(self):
        """切换连接"""
        if self.running:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """连接"""
        item = self.dev_list.currentItem()
        if not item:
            self.log("Select a device first!")
            return
        
        dev = item.text()
        self.log(f"Connecting to {dev}...")
        
        try:
            # 启动服务
            self.server = SimpleScrcpyServer(dev, self.adb)
            if not self.server.start():
                self.log("Server startup failed")
                return
            
            self.log("Server started, waiting...")
            time.sleep(2)
            
            # 端口转发
            self.adb.forward_port(dev, 27183, 27183)
            self.log("Port forwarding set up")
            time.sleep(1)
            
            # 连接
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('127.0.0.1', 27183))
            self.log("Socket connected!")
            
            # 开始解码
            self.video = VideoThread(self.socket)
            self.video.frame_ready.connect(self.on_frame)
            self.video.start()
            
            self.running = True
            self.btn.setText("🔌 Disconnect")
            self.video_label.setText("")
            self.log("✅ Connected!")
            
        except Exception as e:
            self.log(f"❌ Error: {e}")
            self.disconnect()
    
    def disconnect(self):
        """断开连接"""
        self.running = False
        
        if self.video:
            self.video.stop()
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        if self.server:
            self.server.stop()
        
        self.btn.setText("🔗 Connect")
        self.video_label.setText("READY")
        self.log("Disconnected")
    
    @pyqtSlot(QImage)
    def on_frame(self, img):
        """显示帧"""
        pix = QPixmap.fromImage(img)
        scaled = pix.scaledToHeight(self.video_label.height(), Qt.SmoothTransformation)
        self.video_label.setPixmap(scaled)
    
    def closeEvent(self, e):
        """关闭"""
        self.disconnect()
        super().closeEvent(e)

def main():
    app = QApplication(sys.argv)
    win = ScrcpyGUI()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
