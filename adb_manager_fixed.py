#!/usr/bin/env python3
import subprocess
import os
import sys

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class AdbServerManager:
    def __init__(self):
        # Look for adb.exe in current directory (next to EXE) or in bundle
        # First try: next to EXE
        if os.path.exists("adb.exe"):
            self.adb_path = os.path.abspath("adb.exe")
        else:
            # Fallback: use hardcoded path from QtScrcpy-Release
            self.adb_path = r'E:\Program Files\qt\QtScrcpy-Release\QtScrcpy-win-x64-v3.3.3\adb.exe'
    
    def start_server(self):
        try: subprocess.run([self.adb_path, 'start-server'], capture_output=True, creationflags=0x08000000); return True
        except: return False
    def list_devices(self):
        try:
            res = subprocess.run([self.adb_path, 'devices'], capture_output=True, text=True, creationflags=0x08000000)
            return [l.split()[0] for l in res.stdout.strip().split('\n')[1:] if 'device' in l]
        except: return []
    def forward_port(self, serial, local, remote):
        try: return subprocess.run([self.adb_path, '-s', serial, 'forward', f'tcp:{local}', f'tcp:{remote}'], capture_output=True, creationflags=0x08000000).returncode == 0
        except: return False
    @property
    def path(self): return self.adb_path
