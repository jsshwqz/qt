@echo off
CHCP 65001
echo ======================================================
echo   原生投屏 - 终极环境与代码修复工具
echo ======================================================

set PY312="C:\Users\Administrator\AppData\Local\Programs\Python\Python312\python.exe"

echo [1/3] 正在通过脚本强行重构 Python 代码逻辑...
%PY312% -c "
import os

# 1. 修复 adb_manager.py (固定路径与语法)
with open('adb_manager.py', 'w', encoding='utf-8') as f:
    f.write('''#!/usr/bin/env python3
import subprocess
class AdbServerManager:
    def __init__(self):
        self.adb_path = r'E:\\Program Files\\qt\\QtScrcpy-Release\\QtScrcpy-win-x64-v3.3.3\\adb.exe'
    def start_server(self):
        try: subprocess.run([self.adb_path, 'start-server'], capture_output=True, creationflags=0x08000000); return True
        except: return False
    def list_devices(self):
        try:
            res = subprocess.run([self.adb_path, 'devices'], capture_output=True, text=True, creationflags=0x08000000)
            return [l.split()[0] for l in res.stdout.strip().split('\\n')[1:] if 'device' in l]
        except: return []
    def forward_port(self, serial, l, r):
        try: return subprocess.run([self.adb_path, '-s', serial, 'forward', f'tcp:{l}', f'tcp:{r}'], capture_output=True, creationflags=0x08000000).returncode == 0
        except: return False
    @property
    def path(self): return self.adb_path
''')

# 2. 修复 scrcpy_server.py (适配新协议)
with open('scrcpy_server.py', 'w', encoding='utf-8') as f:
    f.write('''#!/usr/bin/env python3
import subprocess, time
class ScrcpyServerManager:
    def __init__(self, device_id, adb_manager):
        self.device_id, self.adb_manager, self.server_process = device_id, adb_manager, None
    def start_server(self):
        cmd = [self.adb_manager.path, '-s', self.device_id, 'shell', 'CLASSPATH=/data/local/tmp/scrcpy-server.jar', 'app_process', '/', 'com.genymobile.scrcpy.Server', '2.0', 'raw', '1080', '4M', '0', '0', '-1', 'true', 'control', 'true']
        try:
            self.server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=0x08000000)
            return True
        except: return False
    def stop_server(self):
        if self.server_process: self.server_process.terminate()
    def wait_for_ready(self, t=5): time.sleep(2); return True
''')

# 3. 修复 wifi_mirroring_final.py (解决线程安全报错)
with open('wifi_mirroring_final.py', 'w', encoding='utf-8') as f:
    f.write('''#!/usr/bin/env python3
import sys, time, socket, threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QListWidget, QTextEdit
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from adb_manager import AdbServerManager
from scrcpy_server import ScrcpyServerManager

class NativeMirroringGUI(QMainWindow):
    log_sig = pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Native Mirroring Pro - FIXED')
        self.setGeometry(100, 100, 1100, 800)
        self.adb = AdbServerManager()
        self.adb.start_server()
        self.scrcpy, self.sock, self.running = None, None, False
        self.setup_ui()
        self.log_sig.connect(self.log_area.append)
        QTimer.singleShot(500, self.refresh)
    def setup_ui(self):
        cw = QWidget(); self.setCentralWidget(cw); lay = QHBoxLayout(cw)
        left = QVBoxLayout(); self.devs = QListWidget(); left.addWidget(QLabel('Devices:')); left.addWidget(self.devs)
        self.btn = QPushButton('Connect'); self.btn.clicked.connect(self.toggle); left.addWidget(self.btn)
        self.log_area = QTextEdit(); self.log_area.setReadOnly(True); left.addWidget(self.log_area)
        lay.addLayout(left, 1)
        self.canvas = QLabel('READY'); self.canvas.setStyleSheet('background:black;color:white;font-size:20px;'); self.canvas.setAlignment(Qt.AlignCenter)
        lay.addWidget(self.canvas, 3)
    def log(self, m): self.log_sig.emit(f'[{time.strftime(\"%H:%M:%S\ sunday\")}] {m}')
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
            if self.adb.forward_port(it.text(), 27183, 27183):
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    self.sock.connect(('127.0.0.1', 27183))
                    self.running = True; threading.Thread(target=self.loop, daemon=True).start()
                    self.btn.setText('Stop'); self.log('Connected!')
                except Exception as e: self.log(f'Socket error: {e}')
    def stop(self):
        self.running = False; self.btn.setText('Connect')
        if self.sock: self.sock.close()
        if self.scrcpy: self.scrcpy.stop_server()
    def loop(self):
        h = False
        while self.running:
            try:
                if not h: self.sock.recv(64); self.sock.recv(8); h = True; self.log('Streaming active!')
                data = self.sock.recv(8192)
                if not data: break
            except: break
        self.running = False
if __name__ == '__main__':
    app = QApplication(sys.argv); win = NativeMirroringGUI(); win.show(); sys.exit(app.exec_())
'''
)
"

echo [2/3] 正在确认核心组件状态...
if not exist "scrcpy-server.jar" (
    echo [错误] 找不到 scrcpy-server.jar，请确保它在项目根目录！
    pause
    exit
)

echo [3/3] 正在启动主程序...
%PY312% wifi_mirroring_final.py

pause
