#!/usr/bin/env python3
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
        self.setWindowTitle('Native Mirroring Pro - FINAL FIX')
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
    def log(self, m): self.log_sig.emit(f'[{time.strftime("%H:%M:%S")}] {m}')
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
