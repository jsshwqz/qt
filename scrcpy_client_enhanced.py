#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Native Mirroring Pro - Enhanced Version
修复了异常处理和启动问题的增强版本
"""

import sys
import os
import time
import socket
import struct
import logging
import traceback
from datetime import datetime

# 设置日志
LOG_FILE = os.path.join(os.path.dirname(__file__), 'scrcpy_enhanced.log')
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# PyQt5 导入
try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QListWidget, QTextEdit, QMessageBox, QListWidgetItem
    )
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
    from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter, QFont
    logger.info('PyQt5 imported successfully')
except ImportError as e:
    logger.error(f'Failed to import PyQt5: {e}')
    sys.exit(1)

# 可选依赖
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
    logger.info('OpenCV available')
except ImportError:
    HAS_CV2 = False
    logger.warning('OpenCV not available - will use fallback rendering')

# 项目模块
try:
    from adb_manager import AdbServerManager
    from scrcpy_server import ScrcpyServerManager
    logger.info('Project modules imported successfully')
except ImportError as e:
    logger.error(f'Failed to import project modules: {e}')
    logger.warning('Using fallback implementations')
    AdbServerManager = None
    ScrcpyServerManager = None


class VideoDecoderThread(QThread):
    """视频解码线程"""
    frame_ready = pyqtSignal(QImage)
    status_changed = pyqtSignal(str)
    
    def __init__(self, sock):
        super().__init__()
        self.socket = sock
        self.running = False
        self.width = 720
        self.height = 1280
        self.frame_count = 0
        logger.info('VideoDecoderThread initialized')
    
    def run(self):
        """运行解码线程"""
        logger.info('VideoDecoderThread started')
        self.running = True
        self.frame_count = 0
        
        try:
            # 设置超时
            self.socket.settimeout(5.0)
            
            # Scrcpy 握手：64字节设备名 + 4字节宽 + 4字节高
            logger.info('Waiting for handshake...')
            device_name = self.socket.recv(64)
            logger.info(f'Received device name: {device_name}')
            
            res_data = self.socket.recv(8)
            if len(res_data) == 8:
                self.width, self.height = struct.unpack('>II', res_data)
                logger.info(f'Handshake success: Resolution={self.width}x{self.height}')
                self.status_changed.emit(f'Connected: {self.width}x{self.height}')
            else:
                logger.warning(f'Incomplete resolution data: {len(res_data)} bytes')
            
            # 移除超时限制以支持实时流
            self.socket.settimeout(None)
            self.socket.setblocking(False)
            
        except Exception as e:
            logger.error(f'Handshake failed: {e}')
            logger.error(traceback.format_exc())
            self.status_changed.emit(f'Handshake Error: {str(e)}')
            return
        
        # 主循环
        while self.running:
            try:
                data = self.socket.recv(65536)
                if not data:
                    logger.warning('Socket closed by server')
                    break
                
                # 渲染帧
                img = self._render_frame()
                self.frame_ready.emit(img)
                time.sleep(0.033)  # ~30fps
                
            except BlockingIOError:
                # 非阻塞模式下无数据可读，稍微等待
                time.sleep(0.01)
            except Exception as e:
                logger.error(f'Frame processing error: {e}')
                logger.debug(traceback.format_exc())
                break
        
        logger.info('VideoDecoderThread stopped')
        self.running = False
    
    def _render_frame(self):
        """渲染测试帧"""
        self.frame_count += 1
        
        img = QImage(self.width, self.height, QImage.Format_RGB888)
        
        # 渐变背景
        color_val = int((time.time() * 50) % 255)
        img.fill(QColor(color_val, 100 + (self.frame_count % 155), 200))
        
        # 绘制文字
        painter = QPainter(img)
        painter.setPen(QColor(255, 255, 255))
        font = QFont('Arial', 32, QFont.Bold)
        painter.setFont(font)
        
        text = f'Frame: {self.frame_count}\n{self.width}x{self.height}'
        painter.drawText(50, 100, 600, 200, Qt.AlignLeft, text)
        painter.end()
        
        return img
    
    def stop(self):
        """停止解码线程"""
        logger.info('Stopping VideoDecoderThread')
        self.running = False
        self.wait()


class ScrcpyClientGUI(QMainWindow):
    """主界面类"""
    log_signal = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        logger.info('Initializing ScrcpyClientGUI')
        
        try:
            self.setWindowTitle('Native Mirroring Pro - Enhanced v1.0')
            self.setGeometry(100, 100, 1200, 800)
            
            # 初始化变量
            self.adb = None
            self.scrcpy = None
            self.sock = None
            self.decoder = None
            self.running = False
            
            # 初始化 ADB
            if AdbServerManager:
                try:
                    self.adb = AdbServerManager()
                    self.adb.start_server()
                    logger.info('ADB Server started')
                except Exception as e:
                    logger.error(f'Failed to start ADB: {e}')
                    self.adb = None
            
            # 设置 UI
            self.setup_ui()
            self.log_signal.connect(self._on_log)
            
            # 启动设备刷新
            self.refresh_timer = QTimer()
            self.refresh_timer.timeout.connect(self.refresh)
            self.refresh_timer.start(2000)  # 每 2 秒刷新一次
            
            # 初始刷新
            QTimer.singleShot(500, self.refresh)
            
            self.log('GUI initialized successfully')
            
        except Exception as e:
            logger.error(f'Failed to initialize GUI: {e}')
            logger.error(traceback.format_exc())
            self.show_error_dialog('Initialization Error', str(e))
    
    def setup_ui(self):
        """设置用户界面"""
        try:
            # 主容器
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QHBoxLayout(central_widget)
            
            # 左侧面板
            left_layout = QVBoxLayout()
            
            # 设备列表
            left_layout.addWidget(QLabel('Devices:'))
            self.device_list = QListWidget()
            self.device_list.itemClicked.connect(self.on_device_selected)
            left_layout.addWidget(self.device_list)
            
            # 连接按钮
            self.connect_button = QPushButton('Connect')
            self.connect_button.clicked.connect(self.toggle_connection)
            self.connect_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px;
                    border-radius: 5px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
            """)
            left_layout.addWidget(self.connect_button)
            
            # 日志区域
            left_layout.addWidget(QLabel('Logs:'))
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            self.log_area.setStyleSheet('background-color: #1e1e1e; color: #00ff00; font-family: monospace;')
            left_layout.addWidget(self.log_area)
            
            main_layout.addLayout(left_layout, 1)
            
            # 右侧画布
            self.canvas = QLabel('READY')
            self.canvas.setStyleSheet('''
                background-color: #000000;
                color: #ffffff;
                font-size: 24px;
                border: 2px solid #333333;
            ''')
            self.canvas.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(self.canvas, 3)
            
            logger.info('UI setup completed')
            
        except Exception as e:
            logger.error(f'Failed to setup UI: {e}')
            logger.error(traceback.format_exc())
            raise
    
    def log(self, message):
        """记录日志"""
        timestamp = datetime.now().strftime('%H:%M:%S')
        log_msg = f'[{timestamp}] {message}'
        logger.info(log_msg)
        self.log_signal.emit(log_msg)
    
    def _on_log(self, message):
        """处理日志信号"""
        self.log_area.append(message)
        # 自动滚动到底部
        scrollbar = self.log_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def show_error_dialog(self, title, message):
        """显示错误对话框"""
        logger.error(f'{title}: {message}')
        try:
            QMessageBox.critical(self, title, message)
        except:
            logger.error(f'Could not show error dialog: {title} - {message}')
    
    def refresh(self):
        """刷新设备列表"""
        try:
            if not self.adb:
                self.log('ADB not available')
                return
            
            devices = self.adb.list_devices()
            
            # 检查列表是否改变
            current_items = [self.device_list.item(i).text() for i in range(self.device_list.count())]
            
            if current_items != devices:
                self.device_list.clear()
                for device in devices:
                    item = QListWidgetItem(device)
                    self.device_list.addItem(item)
                
                if devices:
                    self.log(f'Found {len(devices)} device(s)')
                else:
                    self.log('No devices found')
        except Exception as e:
            logger.error(f'Failed to refresh devices: {e}')
            self.log(f'Error refreshing devices: {str(e)}')
    
    def on_device_selected(self):
        """设备被选择"""
        item = self.device_list.currentItem()
        if item:
            self.log(f'Selected device: {item.text()}')
    
    def toggle_connection(self):
        """切换连接状态"""
        if self.running:
            self.stop_connection()
        else:
            self.start_connection()
    
    def start_connection(self):
        """启动连接"""
        try:
            item = self.device_list.currentItem()
            if not item:
                self.log('Please select a device first')
                return
            
            device = item.text()
            self.log(f'Connecting to {device}...')
            
            if not ScrcpyServerManager:
                self.log('ScrcpyServerManager not available')
                return
            
            # 启动 Scrcpy 服务器
            self.scrcpy = ScrcpyServerManager(device, self.adb)
            if not self.scrcpy.start_server():
                self.log('Failed to start Scrcpy server')
                return
            
            self.log('Scrcpy server started')
            time.sleep(2)
            
            # 设置端口转发
            if not self.scrcpy.setup_port_forwarding():
                self.log('Failed to setup port forwarding')
                return
            
            self.log('Port forwarding setup')
            
            # 连接到 Socket
            try:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.sock.connect(('127.0.0.1', 27183))
                
                # 启动解码线程
                self.decoder = VideoDecoderThread(self.sock)
                self.decoder.frame_ready.connect(self.on_frame)
                self.decoder.status_changed.connect(self.on_decoder_status)
                self.decoder.start()
                
                self.running = True
                self.connect_button.setText('Disconnect')
                self.canvas.setText('')
                self.log('Connected successfully!')
                
            except Exception as e:
                logger.error(f'Socket connection error: {e}')
                self.log(f'Connection error: {str(e)}')
                self.stop_connection()
        
        except Exception as e:
            logger.error(f'Start connection error: {e}')
            logger.error(traceback.format_exc())
            self.log(f'Error: {str(e)}')
            self.show_error_dialog('Connection Error', str(e))
    
    def stop_connection(self):
        """停止连接"""
        try:
            self.log('Disconnecting...')
            
            self.running = False
            
            if self.decoder:
                try:
                    self.decoder.stop()
                except Exception as e:
                    logger.error(f'Error stopping decoder: {e}')
            
            if self.sock:
                try:
                    self.sock.close()
                except Exception as e:
                    logger.error(f'Error closing socket: {e}')
            
            if self.scrcpy:
                try:
                    self.scrcpy.stop_server()
                except Exception as e:
                    logger.error(f'Error stopping server: {e}')
            
            self.connect_button.setText('Connect')
            self.canvas.setText('READY')
            self.log('Disconnected')
            
        except Exception as e:
            logger.error(f'Stop connection error: {e}')
            logger.error(traceback.format_exc())
    
    def on_decoder_status(self, status):
        """处理解码器状态变化"""
        self.log(f'Status: {status}')
    
    @pyqtSlot(QImage)
    def on_frame(self, img):
        """处理新帧"""
        try:
            pixmap = QPixmap.fromImage(img)
            scaled_pixmap = pixmap.scaled(
                self.canvas.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.canvas.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f'Error displaying frame: {e}')
    
    def closeEvent(self, event):
        """关闭事件"""
        logger.info('Closing application')
        try:
            self.refresh_timer.stop()
            if self.running:
                self.stop_connection()
        except Exception as e:
            logger.error(f'Error during closeEvent: {e}')
        event.accept()


def main():
    """主函数"""
    try:
        logger.info('=' * 50)
        logger.info('Native Mirroring Pro - Enhanced v1.0')
        logger.info(f'Start time: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
        logger.info('=' * 50)
        
        app = QApplication(sys.argv)
        window = ScrcpyClientGUI()
        window.show()
        
        exit_code = app.exec_()
        logger.info(f'Application exited with code: {exit_code}')
        return exit_code
        
    except Exception as e:
        logger.error(f'Fatal error in main: {e}')
        logger.error(traceback.format_exc())
        
        # 尝试显示错误对话框
        try:
            app = QApplication(sys.argv)
            QMessageBox.critical(None, 'Fatal Error', str(e))
        except:
            print(f'Fatal error: {e}')
        
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
