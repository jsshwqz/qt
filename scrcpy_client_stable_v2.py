#!/usr/bin/env python3
"""
Scrcpy Client - Stable Version v2 (增强稳定性)
修复了闪退问题，添加了完整的异常捕获和日志系统
"""
import sys
import time
import socket
import subprocess
import threading
import os
import struct
import logging
import traceback
from datetime import datetime

# 配置日志系统
log_file = 'scrcpy_startup.log'
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 导入 PyQt5
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QPushButton, QLabel, QListWidget, QTextEdit)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
    from PyQt5.QtGui import QImage, QPixmap, QColor, QPainter
    logger.info('PyQt5 导入成功')
except ImportError as e:
    logger.error(f'PyQt5 导入失败: {e}')
    print(f"错误：无法导入 PyQt5。请运行: pip install PyQt5")
    sys.exit(1)

# 尝试导入 OpenCV（可选）
try:
    import cv2
    import numpy as np
    HAS_CV2 = True
    logger.info('OpenCV 导入成功')
except ImportError:
    HAS_CV2 = False
    logger.warning('OpenCV 未安装，某些功能可能不可用')

# 导入自定义模块
try:
    from adb_manager import AdbServerManager
    from scrcpy_server import ScrcpyServerManager
    logger.info('自定义模块导入成功')
except ImportError as e:
    logger.error(f'自定义模块导入失败: {e}')
    print(f"错误：无法导入自定义模块。{e}")
    sys.exit(1)


class VideoDecoderThread(QThread):
    """视频解码线程"""
    frame_ready = pyqtSignal(QImage)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, sock):
        super().__init__()
        self.socket = sock
        self.running = False
        self.frame_count = 0
        logger.info('VideoDecoderThread 初始化')
    
    def run(self):
        """运行解码线程"""
        logger.info('VideoDecoderThread 启动')
        self.running = True
        
        try:
            # Scrcpy 握手：64字节设备名 + 4字节宽 + 4字节高
            self.socket.settimeout(5.0)
            device_name = self.socket.recv(64)
            res_data = self.socket.recv(8)
            
            if len(res_data) == 8:
                w, h = struct.unpack('>II', res_data)
                logger.info(f'握手成功: 分辨率={w}x{h}, 设备={device_name.decode().strip()}')
                self.error_occurred.emit(f'连接成功！分辨率: {w}x{h}')
            else:
                logger.warning(f'握手数据长度异常: {len(res_data)}')
            
            self.socket.settimeout(30.0)
        except socket.timeout:
            msg = '握手超时'
            logger.error(msg)
            self.error_occurred.emit(msg)
            return
        except Exception as e:
            msg = f'握手失败: {e}'
            logger.error(msg, exc_info=True)
            self.error_occurred.emit(msg)
            return

        # 主接收循环
        while self.running:
            try:
                data = self.socket.recv(65536)
                if not data:
                    logger.info('socket 连接已关闭')
                    break
                
                # 生成测试帧
                img = self._render_test_frame()
                self.frame_ready.emit(img)
                time.sleep(0.033)  # 约 30 fps
                
            except socket.timeout:
                logger.warning('接收数据超时')
                continue
            except Exception as e:
                logger.error(f'接收数据出错: {e}', exc_info=True)
                break
        
        self.running = False
        logger.info(f'VideoDecoderThread 退出 (共 {self.frame_count} 帧)')

    def _render_test_frame(self):
        """生成测试帧"""
        width, height = 720, 1280
        self.frame_count += 1
        
        try:
            img = QImage(width, height, QImage.Format_RGB888)
            
            # 彩色渐变背景
            color_value = int((self.frame_count % 256))
            img.fill(QColor(color_value, 150, 255 - color_value))
            
            # 添加文字
            painter = QPainter(img)
            painter.setPen(Qt.white)
            from PyQt5.QtGui import QFont
            font = QFont('Arial', 24)
            font.setBold(True)
            painter.setFont(font)
            
            text = f'Frame: {self.frame_count}'
            painter.drawText(width // 2 - 100, height // 2, 200, 50, Qt.AlignCenter, text)
            painter.end()
            
            return img
        except Exception as e:
            logger.error(f'生成测试帧失败: {e}', exc_info=True)
            return QImage(width, height, QImage.Format_RGB888)

    def stop(self):
        """停止线程"""
        logger.info('VideoDecoderThread 停止中...')
        self.running = False
        self.wait()
        logger.info('VideoDecoderThread 已停止')


class ScrcpyClientGUI(QMainWindow):
    """主 GUI 类"""
    log_sig = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        logger.info('=' * 50)
        logger.info(f'应用启动时间: {datetime.now()}')
        logger.info('=' * 50)
        
        try:
            self.setWindowTitle('Scrcpy Client - Stable v2 (增强稳定版)')
            self.setGeometry(100, 100, 1100, 800)
            
            # 初始化 ADB
            logger.info('初始化 ADB 管理器...')
            self.adb = AdbServerManager()
            logger.info(f'ADB 路径: {self.adb.path}')
            
            if not self.adb.start_server():
                logger.warning('ADB 服务器启动失败')
            else:
                logger.info('ADB 服务器启动成功')
            
            # 初始化状态
            self.scrcpy = None
            self.sock = None
            self.decoder = None
            self.running = False
            
            # 设置 UI
            self.setup_ui()
            logger.info('UI 设置完成')
            
            # 连接信号
            self.log_sig.connect(self.log_area.append)
            
            # 延迟刷新设备列表
            QTimer.singleShot(500, self.refresh)
            
            logger.info('应用初始化完成')
            
        except Exception as e:
            logger.error(f'应用初始化失败: {e}', exc_info=True)
            self.show_error(f'初始化错误: {e}')
            raise

    def setup_ui(self):
        """设置用户界面"""
        try:
            cw = QWidget()
            self.setCentralWidget(cw)
            lay = QHBoxLayout(cw)
            
            # 左侧：设备列表和控制
            left = QVBoxLayout()
            left.addWidget(QLabel('设备列表:'))
            
            self.devs = QListWidget()
            left.addWidget(self.devs)
            
            self.btn = QPushButton('连接')
            self.btn.clicked.connect(self.toggle)
            left.addWidget(self.btn)
            
            left.addWidget(QLabel('日志:'))
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            self.log_area.setMaximumHeight(150)
            left.addWidget(self.log_area)
            
            lay.addLayout(left, 1)
            
            # 右侧：投屏画面
            self.canvas = QLabel('等待连接...')
            self.canvas.setStyleSheet('background-color: black; color: white; font-size: 20px; font-family: Arial;')
            self.canvas.setAlignment(Qt.AlignCenter)
            lay.addWidget(self.canvas, 3)
            
            logger.info('UI 组件创建完成')
        except Exception as e:
            logger.error(f'UI 设置失败: {e}', exc_info=True)
            raise

    def log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_sig.emit(f"[{timestamp}] {message}")

    def show_error(self, message):
        """显示错误消息"""
        logger.error(message)
        self.log(f"❌ 错误: {message}")

    def refresh(self):
        """刷新设备列表"""
        try:
            self.devs.clear()
            devices = self.adb.list_devices()
            
            if devices:
                for d in devices:
                    self.devs.addItem(d)
                self.log(f'✓ 找到 {len(devices)} 个设备')
                logger.info(f'设备列表: {devices}')
            else:
                self.log('⚠ 未找到连接的设备')
                logger.warning('未找到连接的设备')
            
            # 30 秒后自动刷新
            QTimer.singleShot(30000, self.refresh)
        except Exception as e:
            msg = f'刷新设备列表失败: {e}'
            logger.error(msg, exc_info=True)
            self.show_error(msg)

    def toggle(self):
        """切换连接状态"""
        try:
            if self.running:
                self.stop()
            else:
                self.start()
        except Exception as e:
            msg = f'操作失败: {e}'
            logger.error(msg, exc_info=True)
            self.show_error(msg)

    def start(self):
        """启动连接"""
        try:
            it = self.devs.currentItem()
            if not it:
                self.show_error('请先选择一个设备')
                return
            
            device_id = it.text()
            self.log(f'正在连接设备: {device_id}...')
            logger.info(f'开始连接设备: {device_id}')
            
            # 创建 Scrcpy 服务器
            self.scrcpy = ScrcpyServerManager(device_id, self.adb)
            
            if not self.scrcpy.start_server():
                self.show_error('启动 Scrcpy 服务器失败')
                return
            
            self.log('✓ Scrcpy 服务器已启动')
            time.sleep(2)
            
            # 设置端口转发
            if not self.scrcpy.setup_port_forwarding():
                self.show_error('端口转发设置失败')
                return
            
            self.log('✓ 端口转发已建立')
            
            # 创建 socket 连接
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            
            try:
                self.sock.connect(('127.0.0.1', 27183))
                self.log('✓ 已连接到本地 socket')
            except socket.timeout:
                self.show_error('Socket 连接超时')
                return
            except Exception as e:
                self.show_error(f'Socket 连接失败: {e}')
                return
            
            # 启动解码线程
            self.decoder = VideoDecoderThread(self.sock)
            self.decoder.frame_ready.connect(self.on_frame)
            self.decoder.error_occurred.connect(self.log)
            self.decoder.start()
            
            self.running = True
            self.btn.setText('断开连接')
            self.log('✅ 已连接！')
            logger.info(f'设备 {device_id} 连接成功')
            
        except Exception as e:
            msg = f'连接失败: {e}'
            logger.error(msg, exc_info=True)
            self.show_error(msg)
            self.running = False

    def stop(self):
        """停止连接"""
        try:
            logger.info('开始断开连接...')
            self.running = False
            
            if self.decoder:
                self.log('正在关闭解码线程...')
                self.decoder.stop()
            
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            
            if self.scrcpy:
                self.log('正在停止 Scrcpy 服务器...')
                self.scrcpy.stop_server()
            
            self.btn.setText('连接')
            self.canvas.setText('连接已断开')
            self.log('✓ 已断开连接')
            logger.info('连接已断开')
            
        except Exception as e:
            msg = f'断开连接时出错: {e}'
            logger.error(msg, exc_info=True)
            self.show_error(msg)

    @pyqtSlot(QImage)
    def on_frame(self, img):
        """处理新帧"""
        try:
            if img and self.running:
                pix = QPixmap.fromImage(img)
                scaled_pix = pix.scaledToWidth(self.canvas.width(), Qt.SmoothTransformation)
                self.canvas.setPixmap(scaled_pix)
        except Exception as e:
            logger.error(f'帧处理失败: {e}', exc_info=True)

    def closeEvent(self, event):
        """关闭事件"""
        logger.info('应用正在关闭...')
        try:
            self.stop()
        except:
            pass
        logger.info('=' * 50)
        logger.info(f'应用关闭时间: {datetime.now()}')
        logger.info('=' * 50)
        event.accept()


def main():
    """应用入口"""
    logger.info('开始初始化应用...')
    
    try:
        app = QApplication(sys.argv)
        logger.info('QApplication 创建成功')
        
        window = ScrcpyClientGUI()
        logger.info('主窗口创建成功')
        
        window.show()
        logger.info('主窗口显示成功')
        
        logger.info('进入事件循环...')
        exit_code = app.exec_()
        
        logger.info(f'应用退出，代码: {exit_code}')
        return exit_code
        
    except Exception as e:
        logger.critical(f'应用启动失败: {e}', exc_info=True)
        print(f"\n致命错误: {e}")
        print(f"详细信息已保存到: {log_file}")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f'主程序异常: {e}', exc_info=True)
        print(f"致命错误: {e}")
        sys.exit(1)
