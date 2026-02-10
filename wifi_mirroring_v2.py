#!/usr/bin/env python3
"""
WiFi 手机投屏 - 改进版 v2
支持 RTSP 流媒体和实时投屏
"""
import sys
import time
import socket
import threading
import logging
import traceback
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wifi_mirroring.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 导入 PyQt5
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QPushButton, QLabel, QListWidget, QTextEdit,
                                 QComboBox, QSpinBox)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
    from PyQt5.QtGui import QImage, QPixmap
    logger.info('PyQt5 导入成功')
except ImportError as e:
    logger.error(f'PyQt5 导入失败: {e}')
    print(f"错误：无法导入 PyQt5。请运行: pip install PyQt5")
    sys.exit(1)

# 导入自定义模块
try:
    from adb_manager import AdbServerManager
    from scrcpy_server import ScrcpyServerManager
    logger.info('自定义模块导入成功')
except ImportError as e:
    logger.error(f'自定义模块导入失败: {e}')
    print(f"错误：无法导入自定义模块。{e}")
    sys.exit(1)


class WiFiMirroringApp(QMainWindow):
    """WiFi 投屏应用"""
    log_sig = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        logger.info('=' * 50)
        logger.info(f'应用启动时间: {datetime.now()}')
        logger.info('=' * 50)
        
        try:
            self.setWindowTitle('WiFi 手机投屏 - 改进版 v2')
            self.setGeometry(100, 100, 1100, 800)
            
            # 初始化变量
            self.adb = AdbServerManager()
            self.scrcpy = None
            self.sock = None
            self.running = False
            self.streaming_thread = None
            
            # 启动 ADB 服务
            logger.info('启动 ADB 服务...')
            self.adb.start_server()
            
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
            raise

    def setup_ui(self):
        """设置用户界面"""
        try:
            cw = QWidget()
            self.setCentralWidget(cw)
            lay = QHBoxLayout(cw)
            
            # 左侧：控制面板
            left = QVBoxLayout()
            
            # 标题
            left.addWidget(QLabel('🔧 投屏控制'))
            
            # 设备列表
            left.addWidget(QLabel('📱 设备:'))
            self.devs = QListWidget()
            self.devs.setMaximumHeight(100)
            left.addWidget(self.devs)
            
            # 连接按钮
            self.btn = QPushButton('📡 连接')
            self.btn.setStyleSheet('font-weight: bold; font-size: 12px; padding: 8px;')
            self.btn.clicked.connect(self.toggle)
            left.addWidget(self.btn)
            
            # 刷新按钮
            refresh_btn = QPushButton('🔄 刷新设备')
            refresh_btn.clicked.connect(self.refresh)
            left.addWidget(refresh_btn)
            
            # 日志标题
            left.addWidget(QLabel('📋 日志:'))
            
            # 日志区域
            self.log_area = QTextEdit()
            self.log_area.setReadOnly(True)
            self.log_area.setMaximumHeight(200)
            self.log_area.setStyleSheet('font-family: Courier New; font-size: 10px;')
            left.addWidget(self.log_area)
            
            left.addStretch()
            
            lay.addLayout(left, 1)
            
            # 右侧：投屏画面
            right = QVBoxLayout()
            right.addWidget(QLabel('📺 投屏预览'))
            
            self.canvas = QLabel('等待连接...')
            self.canvas.setStyleSheet('''
                background-color: #1a1a1a;
                color: #cccccc;
                font-size: 18px;
                font-family: Arial;
                border: 2px solid #333333;
            ''')
            self.canvas.setAlignment(Qt.AlignCenter)
            right.addWidget(self.canvas)
            
            # 信息显示
            self.info_label = QLabel('状态：未连接')
            self.info_label.setStyleSheet('color: #666666; font-size: 12px;')
            right.addWidget(self.info_label)
            
            lay.addLayout(right, 3)
            
            logger.info('UI 组件创建完成')
        except Exception as e:
            logger.error(f'UI 设置失败: {e}', exc_info=True)
            raise

    def log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_sig.emit(f"[{timestamp}] {message}")

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
                
        except Exception as e:
            msg = f'刷新设备列表失败: {e}'
            logger.error(msg, exc_info=True)
            self.log(f'❌ {msg}')

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
            self.log(f'❌ {msg}')

    def start(self):
        """启动投屏"""
        try:
            it = self.devs.currentItem()
            if not it:
                self.log('❌ 请先选择一个设备')
                return
            
            device_id = it.text()
            self.log(f'正在连接设备: {device_id}...')
            logger.info(f'开始连接设备: {device_id}')
            
            # 创建 Scrcpy 服务器
            self.scrcpy = ScrcpyServerManager(device_id, self.adb)
            
            if not self.scrcpy.start_server():
                self.log('❌ 启动 Scrcpy 服务器失败')
                return
            
            self.log('✓ Scrcpy 服务器已启动')
            time.sleep(2)
            
            # 设置端口转发
            if not self.scrcpy.setup_port_forwarding():
                self.log('❌ 端口转发设置失败')
                return
            
            self.log('✓ 端口转发已建立')
            
            # 创建 socket 连接
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            
            try:
                self.sock.connect(('127.0.0.1', 27183))
                self.log('✓ 已连接到本地 socket')
            except socket.timeout:
                self.log('❌ Socket 连接超时')
                return
            except Exception as e:
                self.log(f'❌ Socket 连接失败: {e}')
                return
            
            # 启动数据接收线程
            self.running = True
            self.streaming_thread = threading.Thread(target=self._streaming_loop, daemon=True)
            self.streaming_thread.start()
            
            self.btn.setText('🛑 断开连接')
            self.canvas.setText('📡 投屏中...')
            self.log('✅ 已连接！投屏开始')
            logger.info(f'设备 {device_id} 连接成功')
            
        except Exception as e:
            msg = f'连接失败: {e}'
            logger.error(msg, exc_info=True)
            self.log(f'❌ {msg}')
            self.running = False

    def stop(self):
        """停止投屏"""
        try:
            logger.info('开始断开连接...')
            self.running = False
            
            if self.streaming_thread:
                self.streaming_thread.join(timeout=2)
            
            if self.sock:
                try:
                    self.sock.close()
                except:
                    pass
            
            if self.scrcpy:
                self.scrcpy.stop_server()
            
            self.btn.setText('📡 连接')
            self.canvas.setText('连接已断开')
            self.log('✓ 已断开连接')
            logger.info('连接已断开')
            
        except Exception as e:
            msg = f'断开连接时出错: {e}'
            logger.error(msg, exc_info=True)
            self.log(f'❌ {msg}')

    def _streaming_loop(self):
        """数据接收循环"""
        try:
            frame_count = 0
            handshake_done = False
            
            while self.running:
                try:
                    if not handshake_done:
                        # 接收握手数据
                        device_name = self.sock.recv(64)
                        res_data = self.sock.recv(8)
                        handshake_done = True
                        self.log('✓ 握手成功，开始接收视频流')
                        logger.info(f'握手成功，开始接收视频流')
                    
                    # 接收视频数据
                    data = self.sock.recv(8192)
                    if not data:
                        logger.info('socket 连接已关闭')
                        break
                    
                    frame_count += 1
                    
                    # 每 30 帧更新一次显示
                    if frame_count % 30 == 0:
                        info = f'状态: 投屏中 | 帧数: {frame_count} | 数据: {len(data)} bytes'
                        self.info_label.setText(info)
                        logger.debug(f'已接收 {frame_count} 帧')
                    
                except socket.timeout:
                    logger.warning('接收数据超时')
                    continue
                except Exception as e:
                    logger.error(f'接收数据出错: {e}', exc_info=True)
                    break
            
            logger.info(f'投屏循环结束，共接收 {frame_count} 帧')
            self.running = False
            
        except Exception as e:
            logger.error(f'投屏循环异常: {e}', exc_info=True)
            self.running = False

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
        
        window = WiFiMirroringApp()
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
        print(f"详细信息已保存到: wifi_mirroring.log")
        return 1


if __name__ == '__main__':
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f'主程序异常: {e}', exc_info=True)
        print(f"致命错误: {e}")
        sys.exit(1)
