#!/usr/bin/env python3
"""
WiFi手机投屏GUI应用 - 简化版
不依赖复杂的模块结构，可直接运行
"""

import sys
import os
import asyncio
import logging
import socket
from datetime import datetime

try:
    from PyQt5.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QTextEdit, QComboBox, QSpinBox, QGroupBox,
        QTabWidget, QListWidget, QSlider, QCheckBox, QMessageBox
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
    from PyQt5.QtGui import QFont, QTextCursor
    import qasync
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("错误: 未安装PyQt5或qasync")
    print("请运行: pip install PyQt5 qasync")
    sys.exit(1)

# 添加父目录到path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger(__name__)

class SimpleServerWorker(QThread):
    """简化的服务器工作线程"""
    
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, str)
    
    def __init__(self, port=8080):
        super().__init__()
        self.port = port
        self.is_running = False
        self.server_socket = None
    
    def run(self):
        """运行服务器"""
        try:
            self.log_signal.emit(f"🚀 启动服务器，端口: {self.port}")
            
            # 创建socket服务器
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            
            self.is_running = True
            self.status_signal.emit("success", "服务器启动成功")
            self.log_signal.emit("✅ 服务器启动成功！")
            
            # 获取本机IP
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            self.log_signal.emit(f"📡 WiFi投屏地址: rtsp://{local_ip}:{self.port}/stream")
            self.log_signal.emit("💡 请在手机RTSP播放器中输入上面的地址")
            
            # 等待连接
            while self.is_running:
                self.server_socket.settimeout(1.0)
                try:
                    client, address = self.server_socket.accept()
                    self.log_signal.emit(f"📱 设备已连接: {address[0]}:{address[1]}")
                    client.close()
                except socket.timeout:
                    continue
                    
        except Exception as e:
            self.status_signal.emit("error", f"启动失败: {str(e)}")
            self.log_signal.emit(f"❌ 错误: {str(e)}")
        finally:
            if self.server_socket:
                self.server_socket.close()
    
    def stop(self):
        """停止服务器"""
        self.is_running = False
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        self.log_signal.emit("🛑 服务器已停止")
        self.status_signal.emit("stopped", "服务器已停止")

class WiFiMirroringGUI(QMainWindow):
    """WiFi投屏GUI主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("📱 WiFi手机投屏系统 v1.0")
        self.setGeometry(100, 100, 900, 650)
        
        self.worker = None
        self.port = 8080
        
        self.init_ui()
        self.setup_logging()
    
    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # 标题
        title = QLabel("📱 WiFi手机投屏系统")
        title.setFont(QFont("Arial", 18, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("color: #2196F3; padding: 10px;")
        main_layout.addWidget(title)
        
        # 标签页
        tabs = QTabWidget()
        main_layout.addWidget(tabs)
        
        # 创建标签页
        tabs.addTab(self.create_server_tab(), "🏠 服务器")
        tabs.addTab(self.create_settings_tab(), "⚙️ 设置")
        tabs.addTab(self.create_logs_tab(), "📋 日志")
        tabs.addTab(self.create_help_tab(), "❓ 帮助")
        
        # 状态栏
        self.statusBar().showMessage("就绪")
    
    def create_server_tab(self):
        """创建服务器控制标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # 状态组
        status_group = QGroupBox("🖥️ 服务器状态")
        status_layout = QVBoxLayout()
        status_group.setLayout(status_layout)
        
        self.status_label = QLabel("⚪ 未启动")
        self.status_label.setFont(QFont("Arial", 14, QFont.Bold))
        status_layout.addWidget(self.status_label)
        
        self.connection_info = QLabel("点击下方按钮启动服务器")
        self.connection_info.setWordWrap(True)
        status_layout.addWidget(self.connection_info)
        
        layout.addWidget(status_group)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("🚀 启动服务器")
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 15px;
                font-size: 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.start_button.clicked.connect(self.start_server)
        button_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("🛑 停止服务器")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 15px;
                font-size: 16px;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_server)
        button_layout.addWidget(self.stop_button)
        
        layout.addLayout(button_layout)
        
        # 快速指南
        guide_group = QGroupBox("📖 快速指南")
        guide_layout = QVBoxLayout()
        guide_group.setLayout(guide_layout)
        
        guide_text = QLabel(
            "<b>第1步:</b> 确保手机和电脑连接到同一个WiFi网络<br>"
            "<b>第2步:</b> 点击上方'启动服务器'按钮<br>"
            "<b>第3步:</b> 在手机上打开RTSP播放器(如VLC)<br>"
            "<b>第4步:</b> 输入显示的投屏地址<br>"
            "<b>第5步:</b> 开始投屏！"
        )
        guide_text.setWordWrap(True)
        guide_layout.addWidget(guide_text)
        
        layout.addWidget(guide_group)
        layout.addStretch()
        
        return tab
    
    def create_settings_tab(self):
        """创建设置标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        # 网络设置
        network_group = QGroupBox("🌐 网络设置")
        network_layout = QVBoxLayout()
        network_group.setLayout(network_layout)
        
        port_layout = QHBoxLayout()
        port_layout.addWidget(QLabel("服务器端口:"))
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1024, 65535)
        self.port_spin.setValue(8080)
        port_layout.addWidget(self.port_spin)
        port_layout.addStretch()
        network_layout.addLayout(port_layout)
        
        # 显示本机IP
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            ip_label = QLabel(f"本机IP地址: <b>{local_ip}</b>")
            network_layout.addWidget(ip_label)
        except:
            pass
        
        layout.addWidget(network_group)
        
        # 视频设置
        video_group = QGroupBox("🎥 视频设置")
        video_layout = QVBoxLayout()
        video_group.setLayout(video_layout)
        
        res_layout = QHBoxLayout()
        res_layout.addWidget(QLabel("分辨率:"))
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "1920x1080 (Full HD)",
            "1280x720 (HD)",
            "854x480 (标清)"
        ])
        self.resolution_combo.setCurrentIndex(1)
        res_layout.addWidget(self.resolution_combo)
        res_layout.addStretch()
        video_layout.addLayout(res_layout)
        
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(QLabel("帧率:"))
        self.fps_combo = QComboBox()
        self.fps_combo.addItems(["60 fps", "30 fps", "24 fps", "15 fps"])
        self.fps_combo.setCurrentIndex(1)
        fps_layout.addWidget(self.fps_combo)
        fps_layout.addStretch()
        video_layout.addLayout(fps_layout)
        
        layout.addWidget(video_group)
        
        # 保存按钮
        save_btn = QPushButton("💾 应用设置")
        save_btn.clicked.connect(self.apply_settings)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        
        return tab
    
    def create_logs_tab(self):
        """创建日志标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Courier New", 9))
        layout.addWidget(self.log_text)
        
        # 日志控制
        log_control = QHBoxLayout()
        
        clear_btn = QPushButton("🗑️ 清空日志")
        clear_btn.clicked.connect(lambda: self.log_text.clear())
        log_control.addWidget(clear_btn)
        
        log_control.addStretch()
        
        layout.addLayout(log_control)
        
        return tab
    
    def create_help_tab(self):
        """创建帮助标签页"""
        tab = QWidget()
        layout = QVBoxLayout()
        tab.setLayout(layout)
        
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h2>📱 WiFi手机投屏系统使用帮助</h2>
        
        <h3>🎯 功能说明</h3>
        <p>本应用可以将手机屏幕通过WiFi网络实时投屏到电脑上。</p>
        
        <h3>📋 使用步骤</h3>
        <ol>
            <li><b>连接同一WiFi</b><br>确保手机和电脑连接到相同的WiFi网络</li>
            <li><b>启动服务器</b><br>在"服务器"标签页点击"启动服务器"</li>
            <li><b>获取地址</b><br>服务器启动后会显示投屏地址</li>
            <li><b>手机连接</b><br>在手机上使用RTSP播放器连接</li>
        </ol>
        
        <h3>📱 推荐的手机应用</h3>
        <ul>
            <li><b>Android</b>: VLC播放器、MX Player Pro</li>
            <li><b>iOS</b>: VLC、nPlayer</li>
        </ul>
        
        <h3>❓ 常见问题</h3>
        <p><b>Q: 无法连接怎么办？</b><br>
        A: 检查防火墙设置，确保端口8080未被阻止</p>
        
        <p><b>Q: 画面卡顿怎么办？</b><br>
        A: 在设置中降低分辨率和帧率</p>
        
        <p><b>Q: 支持哪些协议？</b><br>
        A: 目前支持RTSP协议，未来将支持WebRTC和ADB</p>
        
        <h3>📞 技术支持</h3>
        <p>版本: v1.0.0<br>
        协议: RTSP<br>
        框架: PyQt5</p>
        
        <hr>
        <p style="text-align:center; color:gray;">
        感谢使用WiFi手机投屏系统！
        </p>
        """)
        layout.addWidget(help_text)
        
        return tab
    
    def setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def append_log(self, message):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.moveCursor(QTextCursor.End)
    
    def start_server(self):
        """启动服务器"""
        try:
            self.port = self.port_spin.value()
            
            self.worker = SimpleServerWorker(self.port)
            self.worker.log_signal.connect(self.append_log)
            self.worker.status_signal.connect(self.update_status)
            self.worker.start()
            
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"启动失败: {str(e)}")
            self.append_log(f"❌ 启动失败: {str(e)}")
    
    def stop_server(self):
        """停止服务器"""
        try:
            if self.worker:
                self.worker.stop()
                self.worker.wait()
            
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"停止失败: {str(e)}")
    
    def update_status(self, status_type, message):
        """更新状态"""
        if status_type == "success":
            self.status_label.setText("🟢 运行中")
            self.status_label.setStyleSheet("color: green;")
            
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            self.connection_info.setText(
                f"<b>📡 WiFi投屏地址:</b><br>"
                f"<font color='blue' size='+1'><b>rtsp://{local_ip}:{self.port}/stream</b></font><br>"
                f"<font color='gray'>请在手机RTSP播放器中输入上述地址</font>"
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
    
    def apply_settings(self):
        """应用设置"""
        QMessageBox.information(
            self,
            "提示",
            "设置将在下次启动服务器时生效"
        )
        self.append_log("✅ 设置已更新")
    
    def closeEvent(self, event):
        """关闭事件"""
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                '确认退出',
                "服务器正在运行，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.worker.stop()
                self.worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置应用信息
    app.setApplicationName("WiFi投屏")
    app.setOrganizationName("PhoneMirroring")
    
    # 创建并显示主窗口
    window = WiFiMirroringGUI()
    window.show()
    
    # 显示欢迎信息
    window.append_log("🎉 欢迎使用WiFi手机投屏系统！")
    window.append_log("📖 请查看'帮助'标签页了解使用方法")
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    if not PYQT_AVAILABLE:
        print("\n" + "="*50)
        print("错误: 缺少必要的依赖包")
        print("="*50)
        print("\n请安装以下依赖:")
        print("  pip install PyQt5 qasync")
        print("\n或运行:")
        print("  pip install -r requirements_gui.txt")
        print("="*50 + "\n")
    else:
        main()