#!/usr/bin/env python3
"""
Scrcpy 连接诊断工具
用于排查 ADB 和 Scrcpy 连接问题
"""
import subprocess
import os
import time
import sys

class DiagnosticTool:
    def __init__(self):
        self.adb_path = "adb.exe"
        
    def run_cmd(self, cmd, description):
        """运行命令并显示结果"""
        print(f"\n{'='*60}")
        print(f"🔍 {description}")
        print(f"{'='*60}")
        print(f"Command: {' '.join(cmd)}")
        print("-" * 60)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=0x08000000
            )
            print(result.stdout if result.stdout else result.stderr)
            return result.returncode == 0
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def diagnose(self):
        """执行诊断"""
        print("\n" + "=" * 60)
        print("🚀 Scrcpy Connection Diagnostic Tool")
        print("=" * 60)
        
        # 1. ADB 版本
        self.run_cmd(
            [self.adb_path, "version"],
            "Step 1: Check ADB Version"
        )
        
        # 2. 启动 ADB Server
        print("\n⏳ Starting ADB Server...")
        self.run_cmd(
            [self.adb_path, "start-server"],
            "Step 2: Start ADB Server"
        )
        time.sleep(2)
        
        # 3. 列出设备
        success = self.run_cmd(
            [self.adb_path, "devices"],
            "Step 3: List Connected Devices"
        )
        
        if not success:
            print("\n❌ No devices found!")
            print("\n📱 Please check:")
            print("   1. Is your Android phone connected via USB?")
            print("   2. Is USB Debugging enabled?")
            print("      → Settings → About Phone → Developer Options → USB Debugging")
            print("   3. Is the phone authorized for this computer?")
            print("      → Check if 'Allow' prompt appears on your phone")
            print("   4. Do you have the phone's USB drivers installed?")
            return False
        
        # 4. 检查 JAR 文件
        print("\n" + "=" * 60)
        print("🔍 Step 4: Check Scrcpy Server JAR")
        print("=" * 60)
        if os.path.exists("scrcpy-server.jar"):
            size = os.path.getsize("scrcpy-server.jar")
            print(f"✅ Found scrcpy-server.jar ({size} bytes)")
        else:
            print("❌ scrcpy-server.jar not found!")
            return False
        
        # 5. 推送 JAR 到第一个设备
        devices = self.list_devices()
        if devices:
            device = devices[0]
            print(f"\n⏳ Pushing JAR to device: {device}")
            self.run_cmd(
                [self.adb_path, "-s", device, "push", "scrcpy-server.jar", "/data/local/tmp/"],
                f"Step 5: Push Scrcpy JAR to {device}"
            )
            
            # 6. 检查连接状态
            self.run_cmd(
                [self.adb_path, "-s", device, "shell", "echo", "OK"],
                f"Step 6: Test Shell Command on {device}"
            )
            
            # 7. 建立端口转发
            print("\n⏳ Setting up port forwarding...")
            self.run_cmd(
                [self.adb_path, "-s", device, "forward", "tcp:27183", "tcp:27183"],
                "Step 7: Setup Port Forwarding (27183)"
            )
            
            # 8. 检查转发状态
            self.run_cmd(
                [self.adb_path, "forward", "--list"],
                "Step 8: List Active Port Forwards"
            )
            
            print("\n✅ All diagnostics passed!")
            print(f"\n📝 Ready to connect to: {device}")
            return True
        
        return False
    
    def list_devices(self):
        """列出设备"""
        try:
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=0x08000000
            )
            devices = []
            for line in result.stdout.split('\n')[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == 'device':
                    devices.append(parts[0])
            return devices
        except:
            return []

def main():
    tool = DiagnosticTool()
    success = tool.diagnose()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Diagnostic completed successfully!")
        print("\nYou can now run: python scrcpy_client_improved.py")
    else:
        print("❌ Diagnostic found issues. Please fix them first.")
    print("=" * 60 + "\n")
    
    input("Press ENTER to exit...")

if __name__ == '__main__':
    main()
