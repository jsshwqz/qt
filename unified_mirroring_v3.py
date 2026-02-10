#!/usr/bin/env python3
"""
统一投屏主应用 v3
整合 Scrcpy、WiFi 和桌面投屏功能
"""
import sys
import time
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('unified_mirroring.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 导入 PyQt5
try:
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                 QHBoxLayout, QPushButton, QLabel, QListWidget, QTextEdit,
                                 QTabWidget, QListWidgetItem, QSplitter, QStatusBar)
    from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
    from PyQt5.QtGui import QImage, QPixmap, QFont, QIcon, QColor
    logger.info('PyQt5 导入成功')
except ImportError as e:
    logger.error(f'PyQt5 导入失败: {e}')
    print(f"错误：无法导入 PyQt5")
    sys.exit(1)

try:
    from adb_manager_enhanced import AdbServerManager, DeviceMonitor
    from scrcpy_server import ScrcpyServerManager
    logger.info('自定义模块导入成功')
except ImportError as e:
    logger.error(f'自定义模块导入失败: {e}')
    print(f"错误：无法导入自定义模块")
    sys.exit(1)


class ScrcpyTab(QWidget):
    """Scrcpy USB 投屏标签页"""
    
    def __init__(self, adb_manager):
        super().__init__()
        self.adb = adb_manager
        self.scrcpy = None
        self.sock = None
        self.running = False
        self.setup_ui()
        logger.info('ScrcpyTab 初始化完成')
    
    def setup_ui(self):
        """设置 UI"""
        layout = QHBoxLayout(self)
        
        # 左侧控制面板
        left = QVBoxLayout()
        left.addWidget(QLabel('📱 USB 设备'))
        
        self.device_list = QListWidget()
        left.addWidget(self.device_list)
        
        self.connect_btn = QPushButton('📡 连接')
        self.connect_btn.clicked.connect(self.toggle_connection)
        left.addWidget(self.connect_btn)
        
        refresh_btn = QPushButton('🔄 刷新')
        refresh_btn.clicked.connect(self.refresh_devices)
        left.addWidget(refresh_btn)
        
        left.addWidget(QLabel('📋 日志'))
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        left.addWidget(self.log_area)
        left.addStretch()
        
        layout.addLayout(left, 1)
        
        # 右侧显示区域
        self.canvas = QLabel('等待连接...')
        self.canvas.setStyleSheet('background-color: black; color: white;')
        self.canvas.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.canvas, 3)
    
    def log(self, message):
        """添加日志"""
        timestamp = time.strftime("%H:%M:%S")
        self.log_area.append(f"[{timestamp}] {message}")
    
    def refresh_devices(self):
        """刷新设备列表"""
        try:
            self.device_list.clear()
            devices = self.adb.list_devices()
            for d in devices:
                self.device_list.addItem(d)
            self.log(f'✓ 找到 {len(devices)} 个设备')
        except Exception as e:
            self.log(f'❌ {e}')
    
    def toggle_connection(self):
        """切换连接"""
        if self.running:
            self.disconnect()
        else:
            self.connect()
    
    def connect(self):
        """连接设备"""
        try:
            item = self.device_list.currentItem()
            if not item:
                self.log('❌ 请选择设备')
                return
            
            device_id = item.text()
            self.log(f'正在连接 {device_id}...')
            
            self.scrcpy = ScrcpyServerManager(device_id, self.adb)
            if self.scrcpy.start_server():
                self.log('✓ 服务器已启动')
                time.sleep(2)
                
                if self.scrcpy.setup_port_forwarding():
                    self.log('✓ 端口转发成功')
                    self.running = True
                    self.connect_btn.setText('🛑 断开')
                    self.canvas.setText('✓ 已连接')
                else:
                    self.log('❌ 端口转发失败')
            else:
                self.log('❌ 服务器启动失败')
        except Exception as e:
            self.log(f'❌ {e}')
    
    def disconnect(self):
        """断开连接"""
        try:
            self.running = False
            if self.scrcpy:
                self.scrcpy.stop_server()
            self.connect_btn.setText('📡 连接')
            self.canvas.setText('已断开')
            self.log('✓ 已断开连接')
        except Exception as e:
            self.log(f'❌ {e}')


class WiFiTab(QWidget):
    """WiFi 投屏标签页"""
    
    def __init__(self, adb_manager):
        super().__init__()
        self.adb = adb_manager
        self.setup_ui()
        logger.info('WiFiTab 初始化完成')
    
    def setup_ui(self):
        """设置 UI"""
        layout = QHBoxLayout(self)
        
        # 左侧控制面板
        left = QVBoxLayout()
        left.addWidget(QLabel('📡 WiFi 投屏'))
        
        info_text = QTextEdit()
        info_text.setText("""
功能说明:
• 通过 WiFi 连接手机
• 支持 RTSP 流媒体
• 实时投屏显示

使用步骤:
1. 手机和电脑连接同一 WiFi
2. 确保手机开启 ADB over Network
3. 点击连接按钮

注意:
• 需要较好的网络环境
• 延迟可能较大
""")
        info_text.setReadOnly(True)
        left.addWidget(info_text)
        
        self.wifi_btn = QPushButton('🌐 启动 WiFi 投屏')
        self.wifi_btn.setStyleSheet('font-weight: bold; padding: 10px;')
        left.addWidget(self.wifi_btn)
        
        left.addStretch()
        
        layout.addLayout(left, 1)
        
        # 右侧显示区域
        self.canvas = QLabel('WiFi 投屏预览')
        self.canvas.setStyleSheet('background-color: #1a1a1a; color: white;')
        self.canvas.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.canvas, 3)


class DesktopTab(QWidget):
    """桌面投屏标签页"""
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        logger.info('DesktopTab 初始化完成')
    
    def setup_ui(self):
        """设置 UI"""
        layout = QHBoxLayout(self)
        
        # 左侧控制面板
        left = QVBoxLayout()
        left.addWidget(QLabel('💻 桌面投屏'))
        
        info_text = QTextEdit()
        info_text.setText("""
功能说明:
• 投屏电脑桌面
• 支持录屏功能
• 支持实时编码

使用步骤:
1. 点击启动按钮
2. 选择投屏区域
3. 开始投屏

特性:
• 高帧率投屏
• 支持多显示器
• 支持屏幕区域选择
""")
        info_text.setReadOnly(True)
        left.addWidget(info_text)
        
        self.desktop_btn = QPushButton('🎬 启动桌面投屏')
        self.desktop_btn.setStyleSheet('font-weight: bold; padding: 10px;')
        left.addWidget(self.desktop_btn)
        
        left.addStretch()
        
        layout.addLayout(left, 1)
        
        # 右侧显示区域
        self.canvas = QLabel('桌面投屏预览')
        self.canvas.setStyleSheet('background-color: #1a1a1a; color: white;')
        self.canvas.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.canvas, 3)


class UnifiedMirroringApp(QMainWindow):
    """统一投屏主应用"""
    
    def __init__(self):
        super().__init__()
        logger.info('='*50)
        logger.info(f'应用启动: {datetime.now()}')
        logger.info('='*50)
        
        try:
            self.setWindowTitle('投屏大师 - 统一投屏应用 v3')
            self.setGeometry(50, 50, 1200, 800)
            
            # 初始化 ADB
            self.adb = AdbServerManager()
            self.adb.start_server()
            
            # 创建标签页
            self.tabs = QTabWidget()
            self.scrcpy_tab = ScrcpyTab(self.adb)
            self.wifi_tab = WiFiTab(self.adb)
            self.desktop_tab = DesktopTab()
            
            self.tabs.addTab(self.scrcpy_tab, '📱 USB 投屏')
            self.tabs.addTab(self.wifi_tab, '📡 WiFi 投屏')
            self.tabs.addTab(self.desktop_tab, '💻 桌面投屏')
            
            self.setCentralWidget(self.tabs)
            
            # 状态栏
            self.statusBar().showMessage('就绪')
            
            # 初始化
            QTimer.singleShot(500, self.scrcpy_tab.refresh_devices)
            
            logger.info('应用初始化完成')
            
        except Exception as e:
            logger.error(f'应用初始化失败: {e}', exc_info=True)
            raise
    
    def closeEvent(self, event):
        """关闭事件"""
        logger.info('应用关闭中...')
        try:
            self.scrcpy_tab.disconnect()
        except:
            pass
        logger.info(f'应用关闭: {datetime.now()}')
        event.accept()


def main():
    """应用入口"""
    try:
        app = QApplication(sys.argv)
        logger.info('QApplication 创建成功')
        
        window = UnifiedMirroringApp()
        window.show()
        logger.info('主窗口显示成功')
        
        exit_code = app.exec_()
        logger.info(f'应用退出，代码: {exit_code}')
        return exit_code
        
    except Exception as e:
        logger.critical(f'应用启动失败: {e}', exc_info=True)
        return 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        logger.critical(f'主程序异常: {e}', exc_info=True)
        sys.exit(1)
