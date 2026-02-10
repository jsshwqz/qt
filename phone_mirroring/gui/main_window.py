"""
WiFi投屏GUI应用 - 主窗口
使用PyQt5构建的图形界面
"""

import sys
import asyncio
import logging
from typing import Optional
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextEdit, QComboBox, QSpinBox, QGroupBox,
    QTabWidget, QListWidget, QSlider, QCheckBox, QMessageBox,
    QSystemTrayIcon, QMenu, QAction, QStatusBar
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QIcon, QFont, QTextCursor
import qasync

# 导入投屏核心模块
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from phone_mirroring import Config
from phone_mirroring.server import MirroringServer
from phone_mirroring.error_handling import ErrorHandler, ErrorInfo
from phone_mirroring.performance import PerformanceOptimizer

logger = logging.getLogger(__name__)

class MirroringWorker(QThread):
    """投屏服务工作线程"""
    
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, str)  # (status_type, message)
    stats_signal = pyqtSignal(dict)
    client_connected_signal = pyqtSignal(str, str)
    client_disconnected_signal = pyqtSignal(str)
    
    def __init__(self, config: Config):
        super().__init__()
        self.config = config
        self.server: Optional[MirroringServer] = None
        self.is_running = False
    
    async def start_server(self):
        """启动服务器"""
        try:
            self.log_signal.emit("🚀 正在启动投屏服务器...")
            
            self.server = MirroringServer(self.config)
            
            # 注册回调
            self.server.register_callback("server_started", self.on_server_started)
            self.server.register_callback("client_connected", self.on_client_connected)
            self.server.register_callback("client_disconnected", self.on_client_disconnected)
            
            success = await self.server.start()
            
            if success:
                self.is_running = True
                self.status_signal.emit("success", "服务器启动成功")
                self.log_signal.emit(f"✅ 服务器启动成功！")
                self.log_signal.emit(f"📡 WiFi投屏地址: 在同一WiFi下连接到本机IP")
                self.log_signal.emit(f"🎮 支持的协议: {', '.join(self.server.get_active_protocols())}")
                
                # 启动统计更新
                while self.is_running:
                    await asyncio.sleep(2)
                    if self.server and self.server.is_running:
                        stats = self.server.get_stats()
                        self.stats_signal.emit(stats)
            else:
                self.status_signal.emit("error", "服务器启动失败")
                self.log_signal.emit("❌ 服务器启动失败！")
                
        except Exception as e:
            self.status_signal.emit("error", f"启动错误: {str(e)}")
            self.log_signal.emit(f"❌ 启动错误: {str(e)}")
            logger.exception("Server start error")
    
    async def stop_server(self):
        """停止服务器"""
        try:
            self.is_running = False
            if self.server:
                self.log_signal.emit("🛑 正在停止服务器...")
                await self.server.stop()
                self.server = None
                self.status_signal.emit("stopped", "服务器已停止")
                self.log_signal.emit("✅ 服务器已停止")
        except Exception as e:
            self.log_signal.emit(f"❌ 停止错误: {str(e)}")
    
    def on_server_started(self):
        """服务器启动回调"""
        self.log_signal.emit("📢 服务器已启动")
    
    def on_client_connected(self, client_id: str, address: tuple):
        """客户端连接回调"""
        addr_str = f"{address[0]}:{address[1]}" if isinstance(address, tuple) else str(address)
        self.log_signal.emit(f"📱 设备已连接: {addr_str}")
        self.client_connected_signal.emit(client_id, addr_str)
    
    def on_client_disconnected(self, client_id: str):
        """客户端断开回调"""
        self.log_signal.emit(f"❌ 设备已断开: {client_id}")
        self.client_disconnected_signal.emit(client_id)

class WiFiMirroringApp(QMainWindow):
    """WiFi投屏主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📱 WiFi手机投屏系统 v1.0")
        self.setGeometry(100, 100, 900, 700)
        
        # 配置
        self.config = Config()
        self.config.enabled_protocols = ["RTSP", "ADB", "WebRTC"]
        
        # 工作线程
        self.worker: Optional[MirroringWorker] = None
        self.loop = None
        
        # 连接的设备列表
        self.connected_devices = {}
        
        # 初始化UI
        self.init_ui()
        
        # 配置日志
        self.setup_logging()
    
    def init_ui(self):
        """初始化UI"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 标题
        title = QLabel("📱 WiFi手机投屏系统")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # 创建各个标签页
        self.create_server_tab()
        self.create_devices_tab()
        self.create_settings_tab()
        self.create_logs_tab()
        
        # 底部状态栏
        self.create_status_bar()
    
    def create_server_tab(self):
        """创建服务器控制标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # 服务器状态组
        status_group = QGroupBox("🖥️ 服务器状态")
        status_layout = QVBoxLayout()
        status_group.setLayout(status_layout)
        
        self.status_label = QLabel("⚪ 未启动")
        self.status_label.setFont(QFont("Arial", 14))
        status_layout.addWidget(self.status_label)
        
        # 连接信息
        self.connection_info = QLabel("等待启动...")
        status_layout.addWidget(self.connection_info)
        
        layout.addWidget(status_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 启动服务器")
        self.start_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 10px; font-size: 14px; }")
        self.start_button.clicked.connect(self.start_server)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("🛑 停止服务器")
        self.stop_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 10px; font-size: 14px; }")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_server)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)
        
        # 统计信息组
        stats_group = QGroupBox("📊 统计信息")
        stats_layout = QVBoxLayout()
        stats_group.setLayout(stats_layout)
        
        self.stats_label = QLabel("等待数据...")
        self.stats_label.setFont(QFont("Courier", 10))
        stats_layout.addWidget(self.stats_label)
        
        layout.addWidget(stats_group)
        
        # 使用说明
        help_group = QGroupBox("📖 使用说明")
        help_layout = QVBoxLayout()
        help_group.setLayout(help_layout)
        
        help_text = QLabel(
            "1. 确保手机和电脑连接到同一个WiFi网络\n"
            "2. 点击'启动服务器'按钮\n"
            "3. Android手机: 使用支持RTSP的播放器连接\n"
            "   - 或使用ADB通过USB连接后自动投屏\n"
            "4. iOS手机: 使用AirPlay功能连接\n"
            "5. 在'设备'标签页查看已连接设备"
        )
        help_text.setWordWrap(True)
        help_layout.addWidget(help_text)
        
        layout.addWidget(help_group)
        layout.addStretch()
        
        self.tabs.addTab(tab, "🏠 服务器")
    
    def create_devices_tab(self):
        """创建设备管理标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # 设备列表
        devices_group = QGroupBox("📱 已连接设备")
        devices_layout = QVBoxLayout()
        devices_group.setLayout(devices_layout)
        
        self.devices_list = QListWidget()
        devices_layout.addWidget(self.devices_list)
        
        # 设备控制按钮
        control_layout = QHBoxLayout()
        
        disconnect_btn = QPushButton("断开选中设备")
        disconnect_btn.clicked.connect(self.disconnect_selected_device)
        control_layout.addWidget(disconnect_btn)
        
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_devices)
        control_layout.addWidget(refresh_btn)
        
        devices_layout.addLayout(control_layout)
        
        layout.addWidget(devices_group)
        
        self.tabs.addTab(tab, "📱 设备")
    
    def create_settings_tab(self):
        """创建设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # 视频设置
        video_group = QGroupBox("🎥 视频设置")
        video_layout = QVBoxLayout()
        video_group.setLayout(video_layout)
        
        # 分辨率
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("分辨率:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["1920x1080", "1280x720", "854x480"])
        self.resolution_combo.currentTextChanged.connect(self.update_config)
        res_layout.addWidget(self.resolution_combo)
        video_layout.addLayout(res_layout)
        
        # 帧率
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("帧率:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(15, 60)
        self.fps_spin.setValue(30)
        self.fps_spin.setSuffix(" fps")
        self.fps_spin.valueChanged.connect(self.update_config)
        fps_layout.addWidget(self.fps_spin)
        video_layout.addLayout(fps_layout)
        
        # 码率
        bitrate_layout = QHBoxLayout()
        bitrate_layout.addWidget(QLabel("码率:"))
        self.bitrate_slider = QSlider(Qt.Horizontal)
        self.bitrate_slider.setRange(500000, 8000000)
        self.bitrate_slider.setValue(2000000)
        self.bitrate_slider.setTickInterval(500000)
        self.bitrate_slider.valueChanged.connect(self.update_bitrate_label)
        bitrate_layout.addWidget(self.bitrate_slider)
        self.bitrate_label = QLabel("2.0 Mbps")
        bitrate_layout.addWidget(self.bitrate_label)
        video_layout.addLayout(bitrate_layout)
        
        layout.addWidget(video_group)
        
        # 网络设置
        network_group = QGroupBox("🌐 网络设置")
        network_layout = QVBoxLayout()
        network_group.setLayout(network_layout)
        
        # 端口
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("RTSP端口:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8080)
        self.port_spin.valueChanged.connect(self.update_config)
        port_layout.addWidget(self.port_spin)
        network_layout.addLayout(port_layout)
        
        layout.addWidget(network_group)
        
        # 协议设置
        protocol_group = QGroupBox("🔧 启用的协议")
        protocol_layout = QVBoxLayout()
        protocol_group.setLayout(protocol_layout)
        
        self.rtsp_check = QCheckBox("RTSP (推荐)")
        self.rtsp_check.setChecked(True)
        self.rtsp_check.stateChanged.connect(self.update_protocols)
        protocol_layout.addWidget(self.rtsp_check)
        
        self.adb_check = QCheckBox("ADB (Android USB)")
        self.adb_check.setChecked(True)
        self.adb_check.stateChanged.connect(self.update_protocols)
        protocol_layout.addWidget(self.adb_check)
        
        self.webrtc_check = QCheckBox("WebRTC (实验性)")
        self.webrtc_check.setChecked(False)
        self.webrtc_check.stateChanged.connect(self.update_protocols)
        protocol_layout.addWidget(self.webrtc_check)
        
        layout.addWidget(protocol_group)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存设置")
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        self.tabs.addTab(tab, "⚙️ 设置")
    
    def create_logs_tab(self):
        """创建日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier", 9))
        layout.addWidget(self.log_text)
        
        # 日志控制按钮
        log_control = QHBoxLayout()
        
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.clear_logs)
        log_control.addWidget(clear_btn)
        
        save_log_btn = QPushButton("保存日志")
        save_log_btn.clicked.connect(self.save_logs)
        log_control.addWidget(save_log_btn)
        
        layout.addLayout(log_control)
        
        self.tabs.addTab(tab, "📋 日志")
    
    def create_status_bar(self):
        """创建状态栏"""
        self.statusBar().showMessage("就绪")
    
    def setup_logging(self):
        """设置日志系统"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                LogHandler(self.append_log)
            ]
        )
    
    def append_log(self, message: str):
        """添加日志"""
        self.log_text.append(message)
        self.log_text.moveCursor(QTextCursor.End)
    
    def start_server(self):
        """启动服务器"""
        try:
            self.update_config()
            
            self.worker = MirroringWorker(self.config)
            self.worker.log_signal.connect(self.append_log)
            self.worker.status_signal.connect(self.update_status)
            self.worker.stats_signal.connect(self.update_stats)
            self.worker.client_connected_signal.connect(self.add_device)
            self.worker.client_disconnected_signal.connect(self.remove_device)
            
            # 使用qasync运行异步任务
            asyncio.ensure_future(self.worker.start_server())
            
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动失败: {str(e)}")
            logger.exception("Start server error")
    
    def stop_server(self):
        """停止服务器"""
        try:
            if self.worker:
                asyncio.ensure_future(self.worker.stop_server())
            
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止失败: {str(e)}")
    
    def update_status(self, status_type: str, message: str):
        """更新状态"""
        if status_type == "success":
            self.status_label.setText("🟢 运行中")
            self.status_label.setStyleSheet("color: green;")
            
            # 获取本机IP
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            self.connection_info.setText(
                f"📡 WiFi投屏地址:\n"
                f"RTSP: rtsp://{local_ip}:{self.config.network.port}/stream\n"
                f"确保手机和电脑在同一WiFi网络"
            )
            
        elif status_type == "error":
            self.status_label.setText("🔴 错误")
            self.status_label.setStyleSheet("color: red;")
            self.connection_info.setText(f"错误: {message}")
            
        elif status_type == "stopped":
            self.status_label.setText("⚪ 已停止")
            self.status_label.setStyleSheet("color: gray;")
            self.connection_info.setText("服务器已停止")
        
        self.statusBar().showMessage(message)
    
    def update_stats(self, stats: dict):
        """更新统计信息"""
        uptime = stats.get('uptime', 0)
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        
        stats_text = (
            f"运行时间: {hours:02d}:{minutes:02d}:{seconds:02d}\n"
            f"连接设备: {len(self.connected_devices)}\n"
            f"总帧数: {stats.get('total_frames', 0)}\n"
            f"发送字节: {stats.get('total_bytes_sent', 0) / 1024:.1f} KB\n"
            f"接收字节: {stats.get('total_bytes_received', 0) / 1024:.1f} KB"
        )
        
        self.stats_label.setText(stats_text)
    
    def add_device(self, client_id: str, address: str):
        """添加设备"""
        self.connected_devices[client_id] = address
        self.devices_list.addItem(f"📱 {address} ({client_id})")
    
    def remove_device(self, client_id: str):
        """移除设备"""
        if client_id in self.connected_devices:
            address = self.connected_devices[client_id]
            del self.connected_devices[client_id]
            
            # 从列表中移除
            for i in range(self.devices_list.count()):
                if client_id in self.devices_list.item(i).text():
                    self.devices_list.takeItem(i)
                    break
    
    def disconnect_selected_device(self):
        """断开选中的设备"""
        current_item = self.devices_list.currentItem()
        if current_item:
            QMessageBox.information(self, "提示", "设备断开功能待实现")
    
    def refresh_devices(self):
        """刷新设备列表"""
        self.devices_list.clear()
        for client_id, address in self.connected_devices.items():
            self.devices_list.addItem(f"📱 {address} ({client_id})")
    
    def update_config(self):
        """更新配置"""
        # 更新分辨率
        res = self.resolution_combo.currentText().split('x')
        self.config.video.width = int(res[0])
        self.config.video.height = int(res[1])
        
        # 更新帧率
        self.config.video.fps = self.fps_spin.value()
        
        # 更新码率
        self.config.video.bitrate = self.bitrate_slider.value()
        
        # 更新端口
        self.config.network.port = self.port_spin.value()
    
    def update_bitrate_label(self, value):
        """更新码率标签"""
        mbps = value / 1000000
        self.bitrate_label.setText(f"{mbps:.1f} Mbps")
        self.update_config()
    
    def update_protocols(self):
        """更新协议配置"""
        protocols = []
        if self.rtsp_check.isChecked():
            protocols.append("RTSP")
        if self.adb_check.isChecked():
            protocols.append("ADB")
        if self.webrtc_check.isChecked():
            protocols.append("WebRTC")
        
        self.config.enabled_protocols = protocols
    
    def save_settings(self):
        """保存设置"""
        try:
            self.update_config()
            self.config.save_to_file("phone_mirroring/config.json")
            QMessageBox.information(self, "成功", "设置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def clear_logs(self):
        """清空日志"""
        self.log_text.clear()
    
    def save_logs(self):
        """保存日志"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self, "保存日志", "", "文本文件 (*.txt)"
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, "成功", "日志已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
    
    def closeEvent(self, event):
        """关闭事件"""
        reply = QMessageBox.question(
            self, '确认退出',
            "确定要退出吗？这将停止所有投屏连接。",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.worker:
                asyncio.ensure_future(self.worker.stop_server())
            event.accept()
        else:
            event.ignore()

class LogHandler(logging.Handler):
    """自定义日志处理器"""
    
    def __init__(self, callback):
        super().__init__()
        self.callback = callback
    
    def emit(self, record):
        msg = self.format(record)
        self.callback(msg)

async def main_async():
    """异步主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = WiFiMirroringApp()
    window.show()
    
    await qasync.QEventLoop().run_forever()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 使用qasync事件循环
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    window = WiFiMirroringApp()
    window.show()
    
    with loop:
        sys.exit(loop.run_forever())

if __name__ == "__main__":
    main()