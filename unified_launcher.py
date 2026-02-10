#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unified Launcher for Native Mirroring Pro
"""

import sys
import os
import subprocess
from pathlib import Path
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel, QMessageBox
from PyQt5.QtCore import Qt

# Ensure local path is in sys.path
PROJECT_ROOT = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, str(PROJECT_ROOT))

class LauncherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Native Mirroring Pro Launcher")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        title = QLabel("Native Mirroring Pro v2.1")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 20px;")
        layout.addWidget(title)
        
        btn_usb = QPushButton("Launch USB Mirroring (Scrcpy)")
        btn_usb.clicked.connect(self.launch_usb)
        layout.addWidget(btn_usb)
        
        btn_wifi = QPushButton("Launch WiFi Mirroring")
        btn_wifi.clicked.connect(self.launch_wifi)
        layout.addWidget(btn_wifi)
        
        btn_validate = QPushButton("Run Project Validation")
        btn_validate.clicked.connect(self.run_validation)
        layout.addWidget(btn_validate)
        
        btn_exit = QPushButton("Exit")
        btn_exit.clicked.connect(self.close)
        layout.addWidget(btn_exit)
        
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def _launch_script(self, script_name: str) -> bool:
        """Launch child app in a subprocess to avoid nested Qt event loops."""
        script_path = PROJECT_ROOT / script_name
        if not script_path.exists():
            return False

        try:
            subprocess.Popen([sys.executable, str(script_path)], cwd=str(PROJECT_ROOT))
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch {script_name}: {e}")
            return False

    def launch_usb(self):
        # Prefer v2.1 client, fallback to enhanced client.
        for candidate in ("scrcpy_client_v2.1.py", "scrcpy_client_enhanced.py"):
            if self._launch_script(candidate):
                return
        QMessageBox.critical(self, "Error", "No USB mirroring client entrypoint found.")

    def launch_wifi(self):
        for candidate in ("wifi_mirroring_v2.py", "wifi_mirroring_final.py"):
            if self._launch_script(candidate):
                return
        QMessageBox.information(self, "Info", "No WiFi mirroring entrypoint found.")

    def run_validation(self):
        try:
            python_exe = sys.executable
            result = subprocess.run(
                [python_exe, "project_validator.py"],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True
            )
            QMessageBox.information(self, "Validation Result", result.stdout if result.returncode == 0 else result.stderr)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to run validation: {e}")

def main():
    app = QApplication(sys.argv)
    gui = LauncherGUI()
    gui.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
